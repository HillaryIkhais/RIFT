"""traceprinter adapter: normalize QNX traceprinter output into RIFT events.

Parses the text emitted by `traceprinter` on a QNX .kev trace and emits a
canonical list of kernel events with process/thread identity preserved.

The parser is deterministic and rejects malformed/incomplete trace data
rather than synthesizing events. The raw .kev file is always preserved
separately; normalized output is an additional representation only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# QNX kernel thread-state values observed in THREAD-class events.
THREAD_STATES = {
    "RUNNING", "READY", "RECEIVE", "SEND", "REPLY", "NANOSLEEP",
    "MUTEX", "WAITPAGE", "STOPPED",
}

# Canonical event kinds RIFT recognizes.
THREAD_EVENTS = {
    "THSEND", "THRECEIVE", "THREPLY", "THRUNNING", "THREADY",
    "THNANOSLEEP", "THMUTEX", "THWAITPAGE",
}
COMM_EVENTS = {"SND_MESSAGE", "REC_MESSAGE", "REPLY_MESSAGE"}


@dataclass
class TraceEvent:
    """A single normalized kernel trace event."""
    seq: int
    timestamp_us: int
    event: str          # e.g. THSEND, SND_MESSAGE, THRECEIVE
    pid: Optional[int] = None
    tid: Optional[int] = None
    proc: Optional[str] = None
    thread: Optional[str] = None
    state: Optional[str] = None
    rcvid: Optional[int] = None
    coid: Optional[int] = None
    msg: Optional[str] = None
    raw: str = ""
    source_line: int = 0


@dataclass
class NormalizedTrace:
    events: List[TraceEvent] = field(default_factory=list)
    parser_version: str = "rift-qnx-traceprinter/1.0"
    source_file: str = ""
    event_count: int = 0

    def __post_init__(self):
        self.event_count = len(self.events)


class TraceprinterParseError(Exception):
    """Raised when trace data is malformed or incomplete and cannot be trusted."""


# A traceprinter line typically looks like:
#   12345.678901 pid=1234 tid=5678 proc=rift_resmgr name=main THSEND ...
#   12345.678901 pid=1234 tid=5678 THREAD: THSEND state=SEND ...
#   12345.678901 COMM: SND_MESSAGE pid=1234 tid=5678 ...
_LINE_RE = re.compile(
    r"^(?P<ts>\d+(?:\.\d+)?)\s+"
    r"(?:pid=(?P<pid>\d+)\s+)?"
    r"(?:tid=(?P<tid>\d+)\s+)?"
    r"(?:proc=(?P<proc>[^\s]+)\s+)?"
    r"(?P<rest>.*)$"
)

_EVENT_RE = re.compile(
    r"\b(THSEND|THRECEIVE|THREPLY|THRUNNING|THREADY|THNANOSLEEP|"
    r"THMUTEX|THWAITPAGE|SND_MESSAGE|REC_MESSAGE|REPLY_MESSAGE)\b"
)

_PID_RE = re.compile(r"\bpid=(\d+)\b")
_TID_RE = re.compile(r"\btid=(\d+)\b")
_PROC_RE = re.compile(r"\bproc=([^\s,]+)\b")
_RCVID_RE = re.compile(r"\brcvid=(\d+)\b")
_COID_RE = re.compile(r"\bcoid=(\d+)\b")
_STATE_RE = re.compile(r"\bstate=([A-Z]+)\b")


def _to_int(opt: Optional[str]) -> Optional[int]:
    if opt is None:
        return None
    try:
        return int(opt)
    except ValueError:
        return None


def parse_traceprinter(text: str, source_file: str = "") -> NormalizedTrace:
    """Parse traceprinter text into a NormalizedTrace.

    Raises TraceprinterParseError on malformed or incomplete input.
    """
    if not text or not text.strip():
        raise TraceprinterParseError("empty traceprinter output")

    events: List[TraceEvent] = []
    seq = 0
    seen_any_event = False

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue

        m = _LINE_RE.match(stripped)
        if not m:
            # Not a parseable event line; skip but note if file has no events.
            continue

        ts_text = m.group("ts")
        try:
            timestamp_us = int(float(ts_text) * 1_000_000) if ts_text is not None else 0
        except ValueError:
            timestamp_us = 0

        em = _EVENT_RE.search(stripped)
        if not em:
            # A pid/tid line without a recognized event; not a kernel event.
            continue

        seen_any_event = True
        event = em.group(1)
        seq += 1

        pid = _to_int(m.group("pid")) or _to_int(_PID_RE.search(stripped).group(1)) if _PID_RE.search(stripped) else None
        tid = _to_int(m.group("tid")) or _to_int(_TID_RE.search(stripped).group(1)) if _TID_RE.search(stripped) else None
        proc = m.group("proc") or (_PROC_RE.search(stripped).group(1) if _PROC_RE.search(stripped) else None)

        rcvid_m = _RCVID_RE.search(stripped)
        coid_m = _COID_RE.search(stripped)
        state_m = _STATE_RE.search(stripped)

        pid_val = m.group("pid")
        if pid_val is None:
            pm = _PID_RE.search(stripped)
            pid_val = pm.group(1) if pm else None
        tid_val = m.group("tid")
        if tid_val is None:
            tm = _TID_RE.search(stripped)
            tid_val = tm.group(1) if tm else None
        proc_val = m.group("proc")
        if proc_val is None:
            pc = _PROC_RE.search(stripped)
            proc_val = pc.group(1) if pc else None

        ev = TraceEvent(
            seq=seq,
            timestamp_us=timestamp_us,
            event=event,
            pid=_to_int(pid_val),
            tid=_to_int(tid_val),
            proc=proc_val,
            state=state_m.group(1) if state_m else None,
            rcvid=_to_int(rcvid_m.group(1)) if rcvid_m else None,
            coid=_to_int(coid_m.group(1)) if coid_m else None,
            raw=stripped,
            source_line=line_no,
        )
        events.append(ev)

    if not seen_any_event:
        raise TraceprinterParseError(
            f"no recognized QNX kernel events found in {source_file or '<input>'}"
        )

    return NormalizedTrace(
        events=events,
        source_file=source_file,
    )


def events_by_thread(trace: NormalizedTrace, tid: int) -> List[TraceEvent]:
    return [e for e in trace.events if e.tid == tid]


def events_by_process(trace: NormalizedTrace, pid: int) -> List[TraceEvent]:
    return [e for e in trace.events if e.pid == pid]


def thread_events(trace: NormalizedTrace) -> List[TraceEvent]:
    return [e for e in trace.events if e.event in THREAD_EVENTS]


def comm_events(trace: NormalizedTrace) -> List[TraceEvent]:
    return [e for e in trace.events if e.event in COMM_EVENTS]
