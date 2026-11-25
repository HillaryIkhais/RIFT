"""Tests for the Receive Reserve Contract analysis."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "host"))

from rift_qnx.adapters.traceprinter import TraceEvent, NormalizedTrace
from rift_qnx.analysis.receive_reserve import ReceiveReserveContract


def _trace(events):
    return NormalizedTrace(
        events=sorted(events, key=lambda e: e.timestamp_us),
        source_file="<test>",
    )


def test_detects_receive_reserve_exhaustion_under_active_load():
    # Workers all in RECEIVE initially, then all leave to RUNNING/NANOSLEEP
    # while clients are SEND-blocked during an active request window.
    events = [
        # Workers enter RECEIVE.
        # Timestamps in microseconds spanning milliseconds so the budget is real.
        TraceEvent(1, 1_000_000, "THRECEIVE", 100, 10, "rift_resmgr", state="RECEIVE"),
        TraceEvent(2, 1_000_000, "THRECEIVE", 100, 11, "rift_resmgr", state="RECEIVE"),
        # Clients actively sending.
        TraceEvent(3, 1_001_000, "SND_MESSAGE", 200, 20, "load_client", rcvid=1),
        TraceEvent(4, 1_001_000, "SND_MESSAGE", 200, 21, "load_client", rcvid=2),
        # Workers leave RECEIVE -> reserve hits zero under active load.
        TraceEvent(5, 1_002_000, "THRUNNING", 100, 10, "rift_resmgr", state="RUNNING"),
        TraceEvent(6, 1_002_000, "THRUNNING", 100, 11, "rift_resmgr", state="RUNNING"),
        TraceEvent(7, 1_002_000, "THNANOSLEEP", 100, 10, "rift_resmgr", state="NANOSLEEP"),
        TraceEvent(8, 1_002_000, "THNANOSLEEP", 100, 11, "rift_resmgr", state="NANOSLEEP"),
        # Clients blocked in SEND (within the active window).
        TraceEvent(9, 1_003_000, "THSEND", 200, 20, "load_client", state="SEND"),
        TraceEvent(10, 1_003_000, "THSEND", 200, 21, "load_client", state="SEND"),
        # Replies close the window.
        TraceEvent(11, 1_004_000, "REPLY_MESSAGE", 200, 20, "load_client", rcvid=1),
        TraceEvent(12, 1_004_000, "REPLY_MESSAGE", 200, 21, "load_client", rcvid=2),
    ]
    trace = _trace(events)
    contract = ReceiveReserveContract(
        target_pid=100,
        worker_tids=[10, 11],
        client_tids=[20, 21],
        client_pids=[200],
        pool_maximum=4,
        diagnostic_budget_us=1000,  # 1 ms; zero reserve lasts 2 ms
    )
    result = contract.evaluate(trace)
    assert result.passed is False
    assert any(v.classification == "RECEIVE_RESERVE_EXHAUSTED" for v in result.violations), result.violations
    assert any(v.classification == "CLIENT_SEND_BLOCKING" for v in result.violations), result.violations
    assert result.min_reserve == 0


def test_idle_system_zero_reserve_is_not_a_violation():
    # Zero receive workers but NO active request window -> not a violation by itself.
    events = [
        TraceEvent(1, 1000, "THRUNNING", 100, 10, "rift_resmgr", state="RUNNING"),
        TraceEvent(2, 1000, "THRUNNING", 100, 11, "rift_resmgr", state="RUNNING"),
    ]
    trace = _trace(events)
    contract = ReceiveReserveContract(
        target_pid=100, worker_tids=[10, 11],
        client_tids=[20], client_pids=[200],
    )
    result = contract.evaluate(trace)
    # No active window, no SEND-blocking, so no violation.
    assert result.passed is True or result.classification == "PASS", result.violations


def test_does_not_attribute_another_process_threads_to_target():
    events = [
        TraceEvent(1, 1000, "THRECEIVE", 999, 10, "other", state="RECEIVE"),
        TraceEvent(2, 1000, "THSEND", 999, 10, "other", state="SEND"),
    ]
    trace = _trace(events)
    contract = ReceiveReserveContract(
        target_pid=100, worker_tids=[10], client_tids=[20], client_pids=[200],
    )
    result = contract.evaluate(trace)
    assert result.insufficient is True
    assert result.classification == "INSUFFICIENT_TRACE"


def test_insufficient_trace_never_silently_passes():
    events = []
    trace = _trace(events)
    contract = ReceiveReserveContract(
        target_pid=100, worker_tids=[10], client_tids=[20], client_pids=[200],
    )
    result = contract.evaluate(trace)
    assert result.insufficient is True
    assert result.classification == "INSUFFICIENT_TRACE"
    assert result.passed is False


def test_reserve_retained_passes():
    events = [
        TraceEvent(1, 1000, "THRECEIVE", 100, 10, "rift_resmgr", state="RECEIVE"),
        TraceEvent(2, 1000, "THRECEIVE", 100, 11, "rift_resmgr", state="RECEIVE"),
        TraceEvent(3, 1001, "SND_MESSAGE", 200, 20, "load_client", rcvid=1),
        TraceEvent(4, 1002, "THRUNNING", 100, 10, "rift_resmgr", state="RUNNING"),
        # Worker 11 stays in RECEIVE -> reserve retained.
        TraceEvent(5, 1003, "REPLY_MESSAGE", 200, 20, "load_client", rcvid=1),
    ]
    trace = _trace(events)
    contract = ReceiveReserveContract(
        target_pid=100, worker_tids=[10, 11],
        client_tids=[20], client_pids=[200],
    )
    result = contract.evaluate(trace)
    assert result.passed is True, result.violations
    assert result.classification == "PASS"


if __name__ == "__main__":
    test_detects_receive_reserve_exhaustion_under_active_load()
    test_idle_system_zero_reserve_is_not_a_violation()
    test_does_not_attribute_another_process_threads_to_target()
    test_insufficient_trace_never_silently_passes()
    test_reserve_retained_passes()
    print("test_receive_reserve: 5/5 pass")
