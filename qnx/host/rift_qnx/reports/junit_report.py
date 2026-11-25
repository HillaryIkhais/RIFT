"""JUnit XML report: machine-readable CI result for RIFT-QNX incidents.

Exit codes:
  0: all configured invariants passed
  1: a verified violation was detected
  2: evidence/trace insufficient to make a decision
  3: tool execution or environment failure

Missing evidence is never converted into PASS.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Any, Dict, List, Optional


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_junit(
    incident_id: str,
    verdict: str,
    tests: List[Dict[str, Any]],
    system_out: Optional[str] = None,
) -> str:
    """Build a JUnit XML document.

    Each test is one invariant check (receive reserve, send blocking, pool max,
    response budget, fix verification). A test with insufficient evidence is
    reported as a skipped/error, never a pass.
    """
    suite = ET.Element("testsuite")
    suite.set("name", "RIFT-QNX")
    suite.set("incident_id", incident_id)
    suite.set("verdict", verdict)

    passed = failed = skipped = errors = 0
    for t in tests:
        tc = ET.SubElement(suite, "testcase")
        tc.set("name", t.get("name", "unnamed"))
        tc.set("classname", "rift_qnx.analysis")
        tc.set("time", str(t.get("time", 0)))

        status = t.get("status", "unknown")  # pass | fail | insufficient | error
        if status == "pass":
            passed += 1
        elif status == "fail":
            failed += 1
            failure = ET.SubElement(tc, "failure")
            failure.set("message", t.get("classification", "invariant violated"))
            failure.text = _escape(t.get("description", ""))
        elif status == "insufficient":
            skipped += 1
            sk = ET.SubElement(tc, "skipped")
            sk.set("message", "INSUFFICIENT_TRACE")
            sk.text = _escape(t.get("reason", "trace cannot establish required identities/states"))
        elif status == "error":
            errors += 1
            err = ET.SubElement(tc, "error")
            err.set("message", "environment or tool failure")
            err.text = _escape(t.get("reason", ""))

    suite.set("tests", str(passed + failed + skipped + errors))
    suite.set("passed", str(passed))
    suite.set("failed", str(failed))
    suite.set("skipped", str(skipped))
    suite.set("errors", str(errors))

    if system_out:
        so = ET.SubElement(suite, "system-out")
        so.text = _escape(system_out)

    rough = ET.tostring(suite, encoding="unicode")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def exit_code_for(verdict: str, insufficient: bool, environment_failure: bool) -> int:
    """Map a RIFT-QNX verdict to a CI exit code."""
    if environment_failure:
        return 3
    if insufficient:
        return 2
    if verdict == "FIX_VERIFIED" or verdict == "PASS":
        return 0
    if verdict in ("NO_VERIFIED_FIX", "FAIL"):
        return 1
    return 2
