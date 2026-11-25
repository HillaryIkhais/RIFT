"""Deterministic remediation engine.

Distinguishes Cause A (pool capacity) from Cause B (blocking handler
architecture), tests bounded candidate configurations, and verifies each
candidate against the same workload contract.

Verdicts are deterministic: no LLM decides whether a QNX invariant passed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..analysis.receive_reserve import ReceiveReserveContract


@dataclass
class CandidateResult:
    name: str
    kind: str                     # "pool_config" | "handler_design"
    parameters: Dict[str, Any]
    passed: bool
    violations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    trace_path: Optional[str] = None


@dataclass
class VerificationDecision:
    incident_id: str
    cause: Optional[str]          # "A" | "B" | None
    candidates_tested: List[CandidateResult] = field(default_factory=list)
    verified: bool = False
    verdict: str = "NO_VERIFIED_FIX"   # FIX_VERIFIED | NO_VERIFIED_FIX | INCONCLUSIVE
    best_candidate: Optional[CandidateResult] = None
    details: Dict[str, Any] = field(default_factory=dict)


class RemediationEngine:
    """Tests candidate corrections deterministically against the baseline contract."""

    def __init__(
        self,
        target_pid: int,
        worker_tids: List[int],
        client_tids: List[int],
        client_pids: Optional[List[int]] = None,
        pool_maximum: Optional[int] = None,
        response_budget_ns: Optional[int] = None,
        diagnostic_budget_us: int = 50_000_000,
    ):
        self.target_pid = target_pid
        self.worker_tids = list(worker_tids)
        self.client_tids = list(client_tids)
        self.client_pids = list(client_pids or [])
        self.pool_maximum = pool_maximum
        self.response_budget_ns = response_budget_ns
        self.diagnostic_budget_us = diagnostic_budget_us

    def _evaluate_trace(
        self, trace, pool_config: Optional[Dict[str, int]] = None
    ) -> Any:
        contract = ReceiveReserveContract(
            target_pid=self.target_pid,
            worker_tids=self.worker_tids,
            client_tids=self.client_tids,
            client_pids=self.client_pids,
            pool_maximum=(pool_config or {}).get("maximum") or self.pool_maximum,
            diagnostic_budget_us=self.diagnostic_budget_us,
            response_budget_ns=self.response_budget_ns,
        )
        return contract.evaluate(trace)

    def classify_cause(self, baseline_result: Any) -> str:
        """Classify the baseline failure as Cause A (capacity) or Cause B (blocking handler).

        Cause B takes precedence when handler-blocking evidence is present:
        workers occupied in blocking states inside the handler.
        Otherwise Cause A: pool cannot sustain concurrency with a receive reserve.
        """
        classifications = [v.classification for v in baseline_result.violations]
        if "HANDLER_BLOCKING" in classifications:
            return "B"
        if "RECEIVE_RESERVE_EXHAUSTED" in classifications or "POOL_MAX_EXHAUSTED" in classifications:
            return "A"
        if "CLIENT_SEND_BLOCKING" in classifications:
            # Could be either; default to A unless handler evidence exists.
            return "A"
        return "A"

    def test_pool_candidates(
        self,
        baseline_result: Any,
        get_trace_for_config: callable,
    ) -> List[CandidateResult]:
        """Cause A: test a bounded set of pool configurations.

        Selects the smallest configuration satisfying latency + receive-reserve
        requirements while respecting the worker/thread budget. Does not
        blindly recommend the highest maximum.
        """
        results: List[CandidateResult] = []

        base = dict(self._baseline_pool())
        candidate_configs = self._bounded_pool_configs(base)

        for cfg in candidate_configs:
            trace = get_trace_for_config(cfg)
            result = self._evaluate_trace(trace, pool_config=cfg)
            passed = result.passed
            metrics = {
                "min_reserve": result.min_reserve,
                "max_workers_observed": result.max_workers_observed,
                "violation_count": len(result.violations),
                "classification": result.classification,
            }
            results.append(CandidateResult(
                name=f"pool_lo{cfg.get('lo_water')}_inc{cfg.get('increment')}_hi{cfg.get('hi_water')}_max{cfg.get('maximum')}",
                kind="pool_config",
                parameters=cfg,
                passed=passed,
                violations=[v.classification for v in result.violations],
                metrics=metrics,
            ))

        # Sort: passing candidates first, then by smallest maximum, then smallest total.
        passing = [r for r in results if r.passed]
        if passing:
            passing.sort(key=lambda r: (
                r.parameters.get("maximum", 0),
                r.parameters.get("hi_water", 0),
                r.parameters.get("lo_water", 0),
                r.parameters.get("increment", 0),
            ))
            best = passing[0]
        else:
            best = None

        # Attach decision-level best.
        return results, best

    def test_handler_redesign(
        self,
        get_deferred_trace: callable,
    ) -> CandidateResult:
        """Cause B: test the deferred-completion handler design.

        The corrected design: rcvid -> queue -> _RESMGR_NOREPLY -> completion
        worker -> MsgReply. Expects receive reserve retained, no SEND
        starvation, expected REPLY waiting, latency within budget.
        """
        trace = get_deferred_trace()
        result = self._evaluate_trace(trace)
        params = {
            "type": "handler_design",
            "description": "Convert blocking I/O to deferred reply (rcvid + _RESMGR_NOREPLY + MsgReply)",
        }
        return CandidateResult(
            name="deferred_handler",
            kind="handler_design",
            parameters=params,
            passed=result.passed,
            violations=[v.classification for v in result.violations],
            metrics={
                "classification": result.classification,
                "min_reserve": result.min_reserve,
                "send_blocked_clients": result.send_blocked_clients,
                "violation_count": len(result.violations),
            },
            trace_path=getattr(trace, "source_file", None),
        )

    def verify(
        self,
        baseline_trace,
        cause: str,
        get_trace_for_config: callable,
        get_deferred_trace: Optional[callable] = None,
    ) -> VerificationDecision:
        """Run the full candidate verification and return a deterministic decision."""
        baseline_result = self._evaluate_trace(baseline_trace)
        decision = VerificationDecision(
            incident_id=getattr(baseline_trace, "source_file", "incident"),
            cause=cause or self.classify_cause(baseline_result),
        )

        if decision.cause == "B" and get_deferred_trace is not None:
            cand = self.test_handler_redesign(get_deferred_trace)
            decision.candidates_tested.append(cand)
            if cand.passed:
                decision.verified = True
                decision.verdict = "FIX_VERIFIED"
                decision.best_candidate = cand
            else:
                decision.verdict = "NO_VERIFIED_FIX"
        else:
            results, best = self.test_pool_candidates(baseline_result, get_trace_for_config)
            decision.candidates_tested = results
            if best and best.passed:
                decision.verified = True
                decision.verdict = "FIX_VERIFIED"
                decision.best_candidate = best
            else:
                decision.verdict = "NO_VERIFIED_FIX"

        decision.details = {
            "baseline_passed": baseline_result.passed,
            "baseline_classification": baseline_result.classification,
            "baseline_violations": [v.classification for v in baseline_result.violations],
        }
        return decision

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _baseline_pool(self) -> Dict[str, int]:
        return {
            "lo_water": 1,
            "increment": 1,
            "hi_water": self.pool_maximum or 4,
            "maximum": self.pool_maximum or 4,
        }

    def _bounded_pool_configs(self, base: Dict[str, int]) -> List[Dict[str, int]]:
        """Bounded candidate pool configurations around the baseline.

        Small set; not an unbounded search. Respects the worker budget.
        """
        maximum = base.get("maximum", 4)
        configs: List[Dict[str, int]] = []
        # Keep hi_water <= maximum, lo_water <= hi_water, increment >= 1.
        for max_val in (maximum, max(maximum - 1, 1), max(maximum + 1, 1)):
            for hi in (min(max_val, 4), max_val):
                for lo in (1, min(hi, 2)):
                    for inc in (1, 2):
                        cfg = {
                            "lo_water": lo,
                            "increment": inc,
                            "hi_water": hi,
                            "maximum": max_val,
                        }
                        if cfg["lo_water"] <= cfg["hi_water"] <= cfg["maximum"]:
                            if cfg not in configs:
                                configs.append(cfg)
        return configs[:12]
