# RIFT-QNX — Agent Instructions

**Invariant**: The receive-reserve must never hit zero during active request load. Evidence verifies this, not model inference.

---

## Honesty

### Honesty Table: Real / Real but simplified / Fixture / Not built

| Component | Status | Evidence |
|---|---|---|
| Trace parser | **Real** | Parses QNX `traceprinter` output (fixture: `qnx/tests/fixtures/sample_blocking.traceprinter.txt`) |
| Violation detection | **Real** | `test_receive_reserve.py` passes 5/5 tests |
| Frozen bundle | **Real** | Manifest hash over artifact hashes; integrity verified |
| Reproduction | **Real but simplified** | Uses fixture trace (live QNX would require dev host + QEMU target) |
| Fix verification | **Fixture** | "After" metrics simulated; would be real QNX trace in production |
| Video demo | **Fixture** | Demo scenes in `demo.py`; real video requires QNX target |

### Known Limits

1. **QEMU replay not exercised**: Full cycle requires QNX SDP 8.0 dev host (x86_64 Linux/Windows). The tool detects QNX toolchain absence and exits gracefully.

2. **Fixture trace**: The demo uses a synthetic QNX trace. In production, `tracelogger` captures real `.kev` files from QNX 8.0 targets.

3. **Video not recorded**: A 3-minute narrated video would require running the actual QNX target. The `demo.py` script demonstrates all 6 scenes programmatically.

4. **No live mainnet**: This is a dev-tool, not a production deployment. No transaction hashes to display.

### Real / Real but simplified / Fixture / Not built

- **Real**: Trace parser, invariant detector, hash-sealing, deterministic verification
- **Real but simplified**: End-to-end replay (would be real with QNX dev host)
- **Fixture**: "After" metrics (would be real with second trace capture)
- **Not built**: QEMU boot orchestration, automated video generation, continuous integration

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