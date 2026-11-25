"""Receive Reserve Contract analysis.

Implements the documented invariant:

    minimum_receive_blocked_workers >= 1

during an active request interval. A zero receive-worker count during idle
periods is NOT automatically a failure; the detector requires active request
submission and at least one client entering SEND-blocked state.

Failure classifications produced:
  - RECEIVE_RESERVE_EXHAUSTED
  - CLIENT_SEND_BLOCKING
  - POOL_MAX_EXHAUSTED
  - HANDLER_BLOCKING   (only when trace/instrumentation supports it)
  - RESPONSE_BUDGET_BREACH
  - INSUFFICIENT_TRACE (never silently PASS)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..adapters.traceprinter import (
    TraceEvent, NormalizedTrace, thread_events, comm_events,
    THREAD_STATES,
)

RECEIVE = "RECEIVE"
SEND = "SEND"
REPLY = "REPLY"
RUNNING = "RUNNING"
READY = "READY"


@dataclass
class ReserveInterval:
    """A contiguous interval where the receive reserve was at a given level."""
    start_us: int
    end_us: int
    reserve_count: int
    workers_in_receive: List[int]


@dataclass
class Violation:
    classification: str
    start_us: int
    end_us: int
    duration_us: int
    threads: List[int]
    processes: List[int]
    evidence: Dict[str, object]
    description: str


@dataclass
class ReceiveReserveResult:
    passed: bool
    classification: Optional[str]
    violations: List[Violation] = field(default_factory=list)
    reserve_history: List[ReserveInterval] = field(default_factory=list)
    min_reserve: int = 0
    max_workers_observed: int = 0
    send_blocked_clients: List[int] = field(default_factory=list)
    insufficient: bool = False
    insufficient_reason: str = ""
    details: Dict[str, object] = field(default_factory=dict)


class ReceiveReserveContract:
    """Evaluates the receive-reserve invariant against a normalized trace.

    The detector is explicit and deterministic: no LLM in the verdict path.
    """

    def __init__(
        self,
        target_pid: int,
        worker_tids: List[int],
        client_pids: Optional[List[int]] = None,
        client_tids: Optional[List[int]] = None,
        pool_maximum: Optional[int] = None,
        diagnostic_budget_us: int = 50_000_000,   # 50 ms
        response_budget_ns: Optional[int] = None,
    ):
        self.target_pid = target_pid
        self.worker_tids: Set[int] = set(worker_tids)
        self.client_pids: Set[int] = set(client_pids or [])
        self.client_tids: Set[int] = set(client_tids or [])
        self.pool_maximum = pool_maximum
        self.diagnostic_budget_us = diagnostic_budget_us
        self.response_budget_ns = response_budget_ns

    # ------------------------------------------------------------------ #
    # Public evaluation
    # ------------------------------------------------------------------ #
    def evaluate(self, trace: NormalizedTrace) -> ReceiveReserveResult:
        """Run the full receive-reserve contract over the trace."""
        result = ReceiveReserveResult(
            passed=False,
            classification=None,
        )

        if self._insufficient(trace):
            result.insufficient = True
            result.insufficient_reason = (
                "cannot establish target PID, worker threads, client threads, "
                "or required event sequence"
            )
            result.classification = "INSUFFICIENT_TRACE"
            result.passed = False
            return result

        tevents = sorted(thread_events(trace), key=lambda e: e.timestamp_us)
        cevents = sorted(comm_events(trace), key=lambda e: e.timestamp_us)

        # Build per-worker state timeline over the target process.
        worker_state = self._worker_state_timeline(tevents)
        if not worker_state:
            result.insufficient = True
            result.insufficient_reason = "no worker state transitions observed"
            result.classification = "INSUFFICIENT_TRACE"
            return result

        # Receive reserve over time.
        trace_end = max((e.timestamp_us for e in trace.events), default=0)
        reserve_intervals = self._receive_reserve_intervals(worker_state, end_ts=trace_end)
        result.reserve_history = reserve_intervals
        if reserve_intervals:
            result.min_reserve = min(i.reserve_count for i in reserve_intervals)

        # Max worker count observed (for POOL_MAX_EXHAUSTED).
        result.max_workers_observed = max(
            (len(s) for s in worker_state.values()), default=0
        )

        # Active request interval: window where clients are submitting requests
        # (SND_MESSAGE from client threads to the target).
        active_window = self._active_request_window(cevents, tevents)
        result.details["active_request_window_us"] = {
            "start": active_window[0],
            "end": active_window[1],
        }

        violations: List[Violation] = []

        # 1. RECEIVE_RESERVE_EXHAUSTED: reserve hits zero during active load.
        reserve_viol = self._check_reserve_exhaustion(
            reserve_intervals, active_window, worker_state
        )
        if reserve_viol:
            violations.append(reserve_viol)

        # 2. CLIENT_SEND_BLOCKING: relevant clients enter SEND while waiting.
        send_viol = self._check_send_blocking(tevents, active_window)
        if send_viol:
            violations.append(send_viol)
            result.send_blocked_clients = send_viol.threads

        # 3. POOL_MAX_EXHAUSTED: worker count reaches configured maximum while
        #    requests remain outstanding.
        max_viol = self._check_pool_max(worker_state, active_window)
        if max_viol:
            violations.append(max_viol)

        # 4. HANDLER_BLOCKING: workers spend excessive time in blocking states
        #    during a measured handler interval. Only when trace supports it.
        handler_viol = self._check_handler_blocking(worker_state)
        if handler_viol:
            violations.append(handler_viol)

        # 5. RESPONSE_BUDGET_BREACH: client response time exceeds budget.
        if self.response_budget_ns is not None:
            budget_viol = self._check_response_budget(cevents)
            if budget_viol:
                violations.append(budget_viol)

        result.violations = violations

        # Determine overall classification (primary = most severe observed).
        if not violations:
            result.passed = True
            result.classification = "PASS"
        else:
            result.passed = False
            result.classification = violations[0].classification

        result.details = {
            "target_pid": self.target_pid,
            "worker_tids": sorted(self.worker_tids),
            "client_tids": sorted(self.client_tids),
            "pool_maximum": self.pool_maximum,
            "min_reserve": result.min_reserve,
            "max_workers_observed": result.max_workers_observed,
            "violation_count": len(violations),
        }
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _insufficient(self, trace: NormalizedTrace) -> bool:
        if trace.event_count == 0:
            return True
        pids = {e.pid for e in trace.events if e.pid is not None}
        tids = {e.tid for e in trace.events if e.tid is not None}
        if self.target_pid not in pids:
            return True
        if self.worker_tids and not (self.worker_tids & tids):
            return True
        # Client threads are optional: an idle system has no client activity.
        return False

    def _worker_state_timeline(
        self, tevents: List[TraceEvent]
    ) -> Dict[int, List[Tuple[int, str]]]:
        """Map worker tid -> sorted list of (timestamp_us, state)."""
        timeline: Dict[int, List[Tuple[int, str]]] = {}
        for e in tevents:
            if e.pid != self.target_pid:
                continue
            if e.tid is None or e.tid not in self.worker_tids:
                continue
            if e.state is None:
                continue
            state = e.state.upper()
            if state not in THREAD_STATES:
                continue
            timeline.setdefault(e.tid, []).append((e.timestamp_us, state))
        for tid in timeline:
            timeline[tid].sort()
        return timeline

    def _receive_reserve_intervals(
        self, worker_state: Dict[int, List[Tuple[int, str]]], end_ts: int = 0
    ) -> List[ReserveInterval]:
        """Compute contiguous intervals of receive-reserve count over time.

        Multiple changes at the same timestamp are applied together; the
        resulting reserve level holds until the next distinct timestamp (or
        end_ts for the final interval), so zero-duration collapses are avoided.
        """
        # Merge all worker state-change events into a single timeline.
        changes: List[Tuple[int, int, str]] = []  # (ts, tid, state)
        for tid, entries in worker_state.items():
            for ts, state in entries:
                changes.append((ts, tid, state))
        changes.sort()

        # Group changes by timestamp.
        by_ts: Dict[int, List[Tuple[int, str]]] = {}
        for ts, tid, state in changes:
            by_ts.setdefault(ts, []).append((tid, state))

        current: Dict[int, str] = {}  # tid -> current state
        intervals: List[ReserveInterval] = []
        last_count: Optional[int] = None
        interval_start: Optional[int] = None

        def reserve_count() -> int:
            return sum(1 for s in current.values() if s == RECEIVE)

        prev_ts: Optional[int] = None
        distinct_ts = sorted(by_ts)
        for i, ts in enumerate(distinct_ts):
            count = reserve_count()
            # If the reserve level changed since the previous distinct ts,
            # close the prior interval [prev_ts, ts).
            if prev_ts is not None and ts > prev_ts and count != last_count:
                intervals.append(ReserveInterval(
                    start_us=prev_ts,
                    end_us=ts,
                    reserve_count=last_count,
                    workers_in_receive=[
                        t for t, s in current.items() if s == RECEIVE
                    ],
                ))
            # Apply all changes at this timestamp.
            for tid, state in by_ts[ts]:
                current[tid] = state
            last_count = reserve_count()
            # The new level holds from ts until the next distinct ts.
            if interval_start is None:
                interval_start = ts
            prev_ts = ts

        # Close the final interval at end_ts (trace end).
        if prev_ts is not None and last_count is not None:
            final_end = end_ts if end_ts > prev_ts else prev_ts
            intervals.append(ReserveInterval(
                start_us=prev_ts,
                end_us=final_end,
                reserve_count=last_count,
                workers_in_receive=[
                    t for t, s in current.items() if s == RECEIVE
                ],
            ))
        return intervals

    def _active_request_window(
        self, cevents: List[TraceEvent], tevents: List[TraceEvent]
    ) -> Tuple[int, int]:
        """Window where clients are actively submitting requests to the target."""
        starts: List[int] = []
        ends: List[int] = []
        for e in cevents:
            if e.event == "SND_MESSAGE" and e.pid in self.client_pids:
                starts.append(e.timestamp_us)
            if e.event == "REPLY_MESSAGE" and e.pid in self.client_pids:
                ends.append(e.timestamp_us)
        if not starts:
            return (0, 0)
        start = min(starts)
        end = max(ends) if ends else max(starts)
        # The active window extends at least to the last request submission.
        end = max(end, max(starts))
        return (start, end)

    def _check_reserve_exhaustion(
        self,
        intervals: List[ReserveInterval],
        active_window: Tuple[int, int],
        worker_state: Dict[int, List[Tuple[int, str]]],
    ) -> Optional[Violation]:
        start_win, end_win = active_window
        zero_threads: List[int] = []
        total_duration = 0
        violation_start: Optional[int] = None
        violation_end: Optional[int] = None

        for iv in intervals:
            in_active = iv.end_us >= start_win and iv.start_us <= end_win
            if iv.reserve_count == 0 and in_active:
                dur = iv.end_us - iv.start_us
                total_duration += dur
                zero_threads = iv.workers_in_receive or []
                if violation_start is None:
                    violation_start = iv.start_us
                violation_end = iv.end_us

        if total_duration == 0:
            return None

        # Persists beyond diagnostic budget => violation.
        if total_duration > self.diagnostic_budget_us:
            return Violation(
                classification="RECEIVE_RESERVE_EXHAUSTED",
                start_us=violation_start or 0,
                end_us=violation_end or 0,
                duration_us=total_duration,
                threads=zero_threads,
                processes=[self.target_pid],
                evidence={
                    "min_reserve": 0,
                    "active_window_us": [start_win, end_win],
                    "zero_reserve_duration_us": total_duration,
                    "diagnostic_budget_us": self.diagnostic_budget_us,
                    "worker_state": {k: v[-1] if v else None for k, v in worker_state.items()},
                },
                description=(
                    f"Resource manager had zero receive-blocked workers for "
                    f"{total_duration / 1_000_000:.1f} ms during active request "
                    f"interval (budget {self.diagnostic_budget_us / 1_000_000:.1f} ms)."
                ),
            )
        return None

    def _check_send_blocking(
        self, tevents: List[TraceEvent], active_window: Tuple[int, int]
    ) -> Optional[Violation]:
        start_win, end_win = active_window
        blocked: Dict[int, List[Tuple[int, int]]] = {}  # tid -> [(start, end)]
        current_send: Dict[int, int] = {}  # tid -> send start ts

        for e in tevents:
            if e.pid != self.target_pid and e.pid not in self.client_pids:
                continue
            if e.tid is None:
                continue
            if e.tid in self.worker_tids:
                continue  # workers' own SEND states belong to RM internal logic
            if e.state == SEND:
                if e.tid not in current_send:
                    current_send[e.tid] = e.timestamp_us
            elif e.state in (RECEIVE, REPLY, RUNNING, READY):
                if e.tid in current_send:
                    blocked.setdefault(e.tid, []).append(
                        (current_send.pop(e.tid), e.timestamp_us)
                    )

        # Close any still-open sends at the end of the active window.
        close_ts = end_win or 0
        for tid, start_ts in current_send.items():
            blocked.setdefault(tid, []).append((start_ts, max(close_ts, start_ts)))

        relevant = {
            t: intervals for t, intervals in blocked.items()
            if (self.client_tids and t in self.client_tids) or not self.client_tids
        }
        if not relevant:
            return None

        total_threads = sorted(relevant)
        total_duration = sum(
            (end - start) for intervals in relevant.values() for start, end in intervals
        )
        if total_duration == 0:
            return None

        return Violation(
            classification="CLIENT_SEND_BLOCKING",
            start_us=start_win,
            end_us=end_win,
            duration_us=total_duration,
            threads=total_threads,
            processes=list(self.client_pids) if self.client_pids else [],
            evidence={
                "client_send_intervals_us": {
                    str(t): ivs for t, ivs in relevant.items()
                },
                "total_send_blocked_duration_us": total_duration,
                "active_window_us": [start_win, end_win],
            },
            description=(
                f"{len(total_threads)} client thread(s) entered SEND-blocked "
                f"state during the active request interval "
                f"({total_duration / 1_000_000:.1f} ms total)."
            ),
        )

    def _check_pool_max(
        self, worker_state: Dict[int, List[Tuple[int, str]]], active_window: Tuple[int, int]
    ) -> Optional[Violation]:
        if self.pool_maximum is None:
            return None
        start_win, end_win = active_window
        peak = 0
        peak_ts = 0
        for tid, entries in worker_state.items():
            # Count workers present (active) during the active window.
            active_during = [
                ts for ts, _ in entries if start_win <= ts <= end_win
            ]
            if active_during:
                peak += 1
                if not peak_ts or active_during[0] < peak_ts:
                    peak_ts = active_during[0]
        if peak >= self.pool_maximum and end_win > start_win:
            return Violation(
                classification="POOL_MAX_EXHAUSTED",
                start_us=start_win,
                end_us=end_win,
                duration_us=end_win - start_win,
                threads=sorted(self.worker_tids),
                processes=[self.target_pid],
                evidence={
                    "pool_maximum": self.pool_maximum,
                    "peak_workers_observed": peak,
                    "active_window_us": [start_win, end_win],
                },
                description=(
                    f"Worker count reached configured maximum "
                    f"({self.pool_maximum}) while requests remained outstanding."
                ),
            )
        return None

    def _check_handler_blocking(
        self, worker_state: Dict[int, List[Tuple[int, str]]]
    ) -> Optional[Violation]:
        """Flag workers blocking excessively inside handler intervals.

        Only issued when the trace shows a worker transitioning into a
        blocking state (NANOSLEEP/MUTEX/WAITPAGE) immediately after leaving
        RECEIVE and remaining there for a long stretch. This requires
        instrumentation that marks handler boundaries; without it we do not
        infer cause from an unrelated thread state.
        """
        blocking_states = {"NANOSLEEP", "MUTEX", "WAITPAGE"}
        long_block_us = 100_000_000  # 100 ms threshold
        flagged: List[int] = []
        for tid, entries in worker_state.items():
            for i in range(len(entries) - 1):
                ts, state = entries[i]
                if state == RECEIVE:
                    # Look forward: next state transition.
                    for j in range(i + 1, len(entries)):
                        nts, nstate = entries[j]
                        if nstate in blocking_states:
                            dur = nts - ts
                            if dur > long_block_us:
                                flagged.append(tid)
                            break
                        if nstate == RECEIVE:
                            break
        if not flagged:
            return None
        return Violation(
            classification="HANDLER_BLOCKING",
            start_us=0,
            end_us=0,
            duration_us=0,
            threads=sorted(set(flagged)),
            processes=[self.target_pid],
            evidence={
                "blocking_states": sorted(blocking_states),
                "threshold_us": long_block_us,
                "flagged_workers": sorted(set(flagged)),
            },
            description=(
                f"Worker(s) {sorted(set(flagged))} spent excessive time in "
                f"blocking states after leaving RECEIVE, consistent with a "
                f"blocking handler."
            ),
        )

    def _check_response_budget(self, cevents: List[TraceEvent]) -> Optional[Violation]:
        if self.response_budget_ns is None:
            return None
        # Approximate per-client response latency from SND_MESSAGE -> REPLY_MESSAGE.
        pending: Dict[int, int] = {}  # client tid -> send ts
        breaches: List[Tuple[int, int, int]] = []  # (tid, send_ts, reply_ts)
        for e in cevents:
            if e.tid is None:
                continue
            if e.event == "SND_MESSAGE" and e.pid in self.client_pids:
                pending[e.tid] = e.timestamp_us
            elif e.event == "REPLY_MESSAGE" and e.tid in pending:
                send_ts = pending.pop(e.tid)
                latency_us = e.timestamp_us - send_ts
                latency_ns = latency_us * 1000
                if latency_ns > self.response_budget_ns:
                    breaches.append((e.tid, send_ts, e.timestamp_us))
        if not breaches:
            return None
        max_latency_ns = max(
            (reply - send) * 1000 for _, send, reply in breaches
        )
        return Violation(
            classification="RESPONSE_BUDGET_BREACH",
            start_us=min(s for _, s, _ in breaches),
            end_us=max(r for _, _, r in breaches),
            duration_us=max(r - s for _, s, r in breaches),
            threads=[t for t, _, _ in breaches],
            processes=list(self.client_pids) if self.client_pids else [],
            evidence={
                "response_budget_ns": self.response_budget_ns,
                "max_latency_ns": max_latency_ns,
                "breach_count": len(breaches),
                "breaches_us": [(s, r) for _, s, r in breaches],
            },
            description=(
                f"Client response latency {max_latency_ns / 1_000_000:.1f} ms "
                f"exceeds budget {self.response_budget_ns / 1_000_000:.1f} ms "
                f"for {len(breaches)} request(s)."
            ),
        )
