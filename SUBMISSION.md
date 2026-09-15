# SUBMISSION — RIFT: Incident Reconstruction for AI Agents

## The missing boundary

AI agents operate across changing models, prompts, tools, data and state.
When something goes wrong, the original execution context disappears.
There is no reliable preserved boundary around **the world of the incident**.

> **When an AI agent fails, the world that caused the failure is already
> changing. State drifts. Tool responses change. The exact conditions that
> produced the failure are gone.**

## What RIFT does

> **RIFT freezes that incident world so you can reproduce the exact
> failure and prove the fix survived it.**

```
FAIL -> CAPTURE -> FREEZE -> REPRODUCE -> DIAGNOSE -> FIX -> VERIFY -> RESOLVE -> EXPORT
```

The frozen artifact is not a test. It is the incident environment:
world state + trajectory + agent context, hash-sealed so it cannot drift.

**Capability:** AI agents operate across changing models, prompts, tools, data and state.
**Failure:** When something goes wrong, the original execution context disappears.
**Missing boundary:** No reliable preserved boundary around the world of the incident.
**Mechanism:** Frozen incident world + reconstruction + rift.
**Outcome:** Engineers reproduce the actual failure and verify the fix.
**Deeper outcome:** The fix earns the right to go back toward production.

## The product loop

RIFT doesn't stop when the failure is reproduced.
**It stops when the fix survives the incident that caused it.**

```
PRODUCTION FAILURE
    |
RIFT CAPTURES THE INCIDENT
    |
RIFT FREEZES THE CAUSAL WORLD
    |
REPRODUCE
    |
DIAGNOSE
    |
FIX THE AGENT
    |
VERIFY AGAINST THE ORIGINAL INCIDENT
    |
INCIDENT RESOLVED -> RELEASE AUTHORIZED
    |
EXPORT EVIDENCE
    |
BACK TO PRODUCTION
```

The verified fix becomes the resolution record for the production incident.
The exported evidence is what goes with the release — proof that the fix
survived the exact failure that caused the incident.

## The release boundary

RIFT is not just a debugging tool. It sits at the boundary between
"I changed the AI" and "I have evidence this change is safe against
the failure that mattered."

The deeper invariant:

> **No verified fix, no resolution.
> No trustworthy evidence, no release proof.**

When tampering is detected on the frozen world:

> **RELEASE BLOCKED**

Not merely "replay failed." The production deployment is refused
because the evidence underneath the release decision has been compromised.

> **RIFT doesn't stop when the failure is reproduced. It stops when the fix
> survives the incident that caused it.**

## The CLASP-RIFT symmetry

| CLASP | RIFT |
|---|---|
| Pair | Capture |
| Review | Freeze |
| Approve | Reconstruct |
| Pay | Rift |
| Block | Diagnose |
| Revoke | Fix |
| Receipt | Verification |
| Statement | Incident artifact |
| SDK | Rift API/CLI |

CLASP controls **what an agent/app is allowed to do**.
RIFT controls **what happens after an agent does something wrong**.

## The complete loop

**FAIL → CAPTURE → FREEZE → REPRODUCE → DIAGNOSE → FIX → VERIFY → RESOLVE**

Not merely: failure → rift.

## Demo beats (9-step, ~4 min)

**Beat 1 — FAIL: "Watch this agent fail."**
Agent processes Sarah's pending refund. Picks R91 (already COMPLETED).
Duplicate $80 payout. WRONG_ENTITY_SELECTION.

**Beat 2 — CAPTURE: "Record the causal envelope."**
RIFT captures: request + prompt + tools + state + trajectory.
47 artifacts. The incident becomes a portable artifact.

**Beat 3 — FREEZE: "Seal the world."**
World hash: sha256:9f86d0..3a4c02. Frozen. Cannot drift.
Tamper detection active.

**Beat 4 — RECONSTRUCT: "Rebuild the incident environment."**
Sarah Chen. R91=COMPLETED. R92=PENDING. Agent v1.0.
Same tools. Same context. Same state. WORLD RECONSTRUCTED.

**Beat 5 — RIFT: "Run the agent against the frozen world."**
v1.0 selects R91 again. WRONG_ENTITY_SELECTION.
FAILURE REPRODUCED. Same failure, same world.

**Beat 6 — DIAGNOSE: "Explain the divergence."**
Expected: R92 (status=PENDING). Selected: R91 (status=COMPLETED).
Signal: amount=$80 matched, status=PENDING ignored.
The engineer knows exactly what went wrong.

**Beat 7 — FIX: "Correct the agent."**
v1.0: "Select refund matching amount."
v1.1: "Select PENDING refund matching request."

**Beat 8 — VERIFY: "Prove fix against frozen incident."**
Run v1.1 against the exact frozen world. R92 selected.
FIX VERIFIED. Same world + same incident + different agent = success.

**Beat 9 — RESOLVE: "Fix survived the incident that caused it."**
Status: RESOLVED. Evidence chain: frozen → reproduced → fixed → verified.
The incident is resolved. The evidence is exported.
The next time this agent encounters the same class of failure,
it already has a world, a diagnosis, a verified fix, and proof.

## Why this is different

| Existing product | What it does | What it misses |
|---|---|---|
| Agent eval frameworks | Ask if agent is good today | Don't preserve past failures |
| Regression testing | Encode failure as a test | Don't reconstruct the incident world |
| Observability | Record what happened | Don't let you re-run it |
| Behavioral contracts | Define allowed behavior | Don't capture the failure environment |
| Production rift | Rift traffic | Don't freeze the causal state |

RIFT's distinctive primitive:

> **Observed failure -> frozen incident world -> reproducible environment
> -> fix verification -> incident resolved**

## Architecture

```
LLM
 -> Recorder (tool calls + results + state)
 -> investigate() (deterministic rules)
 -> freeze_incident() (hash-sealed world)
 -> replay_incident() (reconstruct + run)
 -> verify_fix() (prove the fix)
 -> resolve_incident() (mark resolved + export evidence)
```

Model proposes. RIFT decides. Hash-verified. No model in the verdict path.

## Run it

```
python3 demo_rift.py       # deterministic full loop
python3 demo_llm.py          # real-model loop (keys optional)
python3 test_rift.py       # 8 tests
python3 test_llm_adapter.py  # 3 tests
python3 -m rift.board      # rift_board/
```
