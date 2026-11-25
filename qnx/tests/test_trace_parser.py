"""Tests for the QNX traceprinter parser adapter."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "host"))

from rift_qnx.adapters.traceprinter import (
    parse_traceprinter, TraceprinterParseError,
    thread_events, comm_events, events_by_process, events_by_thread,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_blocking.traceprinter.txt")


def test_parse_real_traceprinter_output():
    with open(FIXTURE) as fh:
        text = fh.read()
    trace = parse_traceprinter(text, source_file=FIXTURE)
    assert trace.event_count > 0
    assert trace.source_file == FIXTURE


def test_preserves_process_and_thread_identity():
    with open(FIXTURE) as fh:
        trace = parse_traceprinter(fh.read(), source_file=FIXTURE)
    rms = events_by_process(trace, 100)
    assert any(e.tid in (10, 11, 12, 13) for e in rms)
    clients = events_by_process(trace, 200)
    assert any(e.tid in (20, 21) for e in clients)


def test_identifies_thread_and_communication_events():
    with open(FIXTURE) as fh:
        trace = parse_traceprinter(fh.read(), source_file=FIXTURE)
    te = thread_events(trace)
    ce = comm_events(trace)
    assert any(e.event == "THSEND" for e in te)
    assert any(e.event == "THRECEIVE" for e in te)
    assert any(e.event == "SND_MESSAGE" for e in ce)
    assert any(e.event == "REPLY_MESSAGE" for e in ce)


def test_rejects_empty_input():
    try:
        parse_traceprinter("", source_file="<empty>")
        assert False, "should have raised"
    except TraceprinterParseError:
        pass


def test_rejects_input_without_kernel_events():
    try:
        parse_traceprinter("just some random text\nno events here", source_file="<bad>")
        assert False, "should have raised"
    except TraceprinterParseError:
        pass


if __name__ == "__main__":
    test_parse_real_traceprinter_output()
    test_preserves_process_and_thread_identity()
    test_identifies_thread_and_communication_events()
    test_rejects_empty_input()
    test_rejects_input_without_kernel_events()
    print("test_trace_parser: 5/5 pass")
