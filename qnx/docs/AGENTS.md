# RIFT-QNX — Agent Instructions

**Invariant**: The receive-reserve must never hit zero during active request load. Evidence verifies this, not model inference.

---

## Honesty

- All measurements come from actual QNX traces (`tracelogger` + `traceprinter`).
- Missing evidence is NEVER converted into PASS.
- If the QNX toolchain is unavailable (macOS host), the tool must refuse gracefully.
- The model proposes fixes; deterministic code decides.

---

## Non-Discoverable Invariants

1. Raw trace file integrity (`trace.kev` SHA-256) must match the manifest.
2. Normalized trace events must preserve process and thread identity.
3. Receive-reserve violation duration exceeds diagnostic budget before classification.
4. No fake numbers, timers, or metrics in the verdict path.

---

## Task-Level Definition of Done

Each test under `qnx/tests/fixtures/` must:

1. Parse the fixture file without error
2. Preserve pid/tid identity
3. Emit events with correct ordering
4. Produce deterministic output on re-run

The full demo script under `qnx/docs/demo.py` must:

1. Build if QNX toolchain available (or skip gracefully)
2. Run each phase and record outcome
3. Produce exit codes: 0 = all invariants passed, 1 = verified violation, 2 = insufficient evidence, 3 = environment failure
4. Export JUnit XML and HTML report

---

## Environment

- Host: Any Python 3.10+ environment (for analysis/tools)
- Target: QNX SDP 8.0 x86_64 in QEMU (for full demonstration)
- QNX toolchain on host: Optional (demo will report unavailability but tests pass against fixtures)