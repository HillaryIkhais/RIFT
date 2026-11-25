# RIFT-QNX — Product Requirements Document

**Wedge**: QNX resource-manager receive-reserve exhaustion

**Invariant**: During active request load, the resource manager must retain at least one worker in RECEIVE-blocked state. When no worker is available, clients SEND-block and the system exhibits tail-latency violations.

---

## Mechanism

QNX resource managers receive client requests via message passing. A multithreaded resource manager uses a thread pool:

- `lo_water`: minimum blocked workers
- `increment`: threads to restore lo_water  
- `hi_water`: upper limit for blocked workers
- `maximum`: max total threads

The problem: QNX recommends maintaining at least one worker `RECEIVE`-blocked. When the pool is exhausted and no worker is in RECEIVE, clients become `SEND`-blocked.

RIFT-QNX's job: capture this failure in real QNX traces, freeze the causal conditions, reproduce the failure, and verify the fix.

---

## Attack Vectors

1. **Pool capacity exhaustion**: Worker threads blocked inside handlers; pool size inadequate.
2. **Blocking handler design**: Synchronous I/O or slow operations inside handlers prevents worker return to RECEIVE.
3. **Incorrect configuration**: lo_water=0, or hi_water < required concurrency.

---

## Real Integration

- **Target**: QNX SDP 8.0, x86_64, in QEMU.
- **Trace source**: `tracelogger` capturing THREAD + COMMUNICATION classes, exported to `.kev` files, normalized by `traceprinter`.
- **Resource manager**: Two implementations: a faulty blocking-handler version (baseline) and a corrected deferred-reply version.
- **Workload**: Concurrent load_client processes submitting requests to the RM.

---

## State Machine

```
[FAIL] -> [CAPTURE trace] -> [FREEZE incident bundle] -> [REPRODUCE] -> [DIAGNOSE] -> [FIX] -> [VERIFY] -> [RESOLVED / REJECT]
```

---

## Vocabulary

| Term | Definition |
|------|------------|
| Receive Reserve | Count of workers in RECEIVE-blocked state |
| SEND-blocking | Client waiting for a worker to receive its message |
| Deferred Completion | Handler saves rcvid, returns _RESMGR_NOREPLY, completion worker replies later |
| Frozen Incident | Hash-sealed bundle containing raw trace, manifest, diagnosis, test conditions |
| Verified Fix | Candidate code survives the same workload against which the original failure reproduced |

---

## Scope (P0)

- Parse real QNX `traceprinter` output (fixture: `qnx/tests/fixtures/sample_blocking.traceprinter.txt`)
- Detect RECEIVE_RESERVE_EXHAUSTED when reserve hits zero during active load
- Detect CLIENT_SEND_BLOCKING when clients enter SEND state during active window
- Freeze incident bundle with manifest hash over artifact hashes
- Replay same workload against corrected handler design
- Verify receive reserve retained; no SEND-blocking; latency within budget

## Scope (P1)

- Pool-configuration candidate testing
- Recovery contract and rollback workflow
- Interactive incident board
- JSON + JUnit CI reports
- Library of frozen QNX test incidents

## Never (out of scope)

- Replacement for QNX System Profiler
- Generic AI debugging chatbot
- Fabricated or synthetic trace data
- Increased thread counts as primary solution
- Production safety certification claims

---

## Binary Definition of Done (M0)

The demo must show:

1. A genuine QNX 8.0 resource manager fails under controlled workload
2. RIFT captures the actual failure evidence in a real trace
3. RIFT freezes the conditions needed to reproduce the failure
4. RIFT replays the workload and verifies the invariant is violated
5. A correction is applied
6. RIFT runs the same workload and actual QNX evidence shows failure removed
7. RIFT exports verifiable resolution record

---

## 20 Judge Answers (extract from rubric)

1. What failed? → Resource manager's receive reserve exhausted.
2. Which threads/processes were involved? → RM workers TIDs, client TIDs from trace.
3. What invariant was violated? → minimum_receive_blocked_workers >= 1 during active load.
4. What is the defensible correction? → Deferred-completion pattern with rcvid + _RESMGR_NOREPLY + MsgReply.
5. Does the correction pass against the same workload? → Verified by actual QNX trace evidence.
6-20. See HACKATHON_CHANGELOG.md.

---

## Internal Cutoff

Substantial feature freeze: November 30, 2026, 23:59 UTC. No commits after submission deadline without explicit hold.

## Honesty

Known limits: QEMU scheduling does not guarantee identical schedule reproduction. The invariant violation is reproduced, not the exact nanosecond sequence. The verdict is based on deterministic code, not model inference.