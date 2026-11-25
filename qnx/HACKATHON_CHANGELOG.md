# RIFT-QNX — Hackathon Changelog

## Branch Isolation

All QNX-specific development occurs on `qnx/resource-manager-assurance`, branched from `origin/main`. The original RIFT branch (`main`) remains completely untouched.

---

## Changes Since Fork (Nov 24, 2026)

### Core Architecture

| Component | Status |
|-----------|--------|
| `qnx/target/` | QNX C source (resource manager, clients, scenarios) |
| `qnx/host/rift_qnx/` | Host-side Python analyzer (trace adapter, contracts, replay, reports) |
| `qnx/tests/fixtures/` | Sample QNX traceprinter fixtures for testing |
| `qnx/docs/` | PRD.md, AGENTS.md, demo.py, architecture.md |

### New Files (QNX Target)

- `qnx/target/resource_manager/src/resmgr_main.c` — Dual-mode resource manager (blocking + deferred)
- `qnx/target/resource_manager/include/resmgr_main.h`
- `qnx/target/resource_manager/Makefile` — QNX SDP 8.0 x86_64 build
- `qnx/target/clients/src/load_client.c` — Concurrent workload client
- `qnx/target/clients/include/load_client.h`
- `qnx/target/clients/Makefile`
- `qnx/target/scenarios/blocking-handler.yaml` — Scenario definition
- `qnx/target/scenarios/deferred-reply.yaml` — Corrected scenario
- `qnx/target/scripts/capture_trace.sh` — Trace capture script
- `qnx/target/scripts/run_qemu.sh` — QEMU boot script

### New Files (Host Python)

- `qnx/host/rift_qnx/__init__.py` — Package init
- `qnx/host/rift_qnx/adapters/traceprinter.py` — Parse real QNX `traceprinter` output
- `qnx/host/rift_qnx/analysis/receive_reserve.py` — Receive-reserve contract detector
- `qnx/host/rift_qnx/capture/target_manifest.py` — Target manifest recorder
- `qnx/host/rift_qnx/capture/incident_bundle.py` — Frozen incident assembler
- `qnx/host/rift_qnx/replay/qemu_replay.py` — QEMU replay orchestrator
- `qnx/host/rift_qnx/replay/workload_replay.py` — Workload replay runner
- `qnx/host/rift_qnx/replay/verify_fix.py` — Deterministic remediation engine
- `qnx/host/rift_qnx/reports/html_report.py` — Interactive HTML incident report
- `qnx/host/rift_qnx/reports/junit_report.py` — CI JUnit XML report
- `qnx/host/rift_qnx/cli.py` — Host CLI (`rift-qnx doctor`, `build`, `run`, etc.)

### New Files (Tests)

- `qnx/tests/fixtures/sample_blocking.traceprinter.txt` — Sample trace fixture
- `qnx/tests/test_trace_parser.py` — Parse + identity preservation tests
- `qnx/tests/test_receive_reserve.py` — Contract detection tests

### Documentation

- `qnx/docs/PRD.md` — Build-against product requirements
- `qnx/docs/AGENTS.md` — Agent instructions (invariants, honesty rules)
- `qnx/docs/demo.py` — Hero demo script
- `qnx/docs/architecture.md` — Architecture document (pending)

---

## Preserved Files (Unmodified)

The following RIFT 2.0 files remain unchanged under `rift/`:

- `rift/` — incident reconstruction engine (sim, recorder, miner, engine, llm, board)
- `delta/` — side-effect firewall
- `demo_rift.py` — RIFT demo script
- `test_rift.py`, `test_delta.py` — existing tests
- `README.md` — project README (unchanged at root)

---

## Git Status

```
$ git branch -a
* qnx/resource-manager-assurance
  remotes/origin/main
```

The `main` branch receives no QNX commits. All changes exist on the dedicated branch.