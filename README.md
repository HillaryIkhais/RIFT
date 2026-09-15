# RIFT — incident reconstruction for AI agents

When an AI agent breaks in the real world, the world keeps moving. By the time
an engineer investigates, state has drifted, tool responses have changed, and the
exact conditions that produced the failure are gone. The engineer cannot reproduce
the incident. If they cannot reproduce it, they cannot reliably prove the fix.

**RIFT reconstructs the exact world an AI agent saw when it failed, so the
failure can be reproduced, investigated, and killed.**

```
FAIL -> CAPTURE -> FREEZE -> REPRODUCE -> DIAGNOSE -> FIX -> VERIFY -> RESOLVE
```

RIFT doesn't stop when the failure is reproduced.
**It stops when the fix survives the incident that caused it.**

```
python3 demo_rift.py       # deterministic full loop
python3 demo_llm.py          # real-model loop (keys optional)
python3 test_rift.py       # 8 tests
python3 test_llm_adapter.py  # 3 tests
python3 -m rift.board      # rift_board/: dashboard + incident walkthrough
```

Model keys (optional; everything works offline without them):
`RIFT_LLM_PROVIDER=anthropic|openai`, `RIFT_LLM_MODEL=...`,
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` (+ `OPENAI_BASE_URL` for gateways).

## Architecture

```
LLM -> Policy(shop, task, rec) -> tool decisions -> trajectory
-> investigate() (deterministic rules over trajectory + state diff)
-> freeze_incident() (world + incident analysis + fix verification, hash-sealed)
-> replay_incident() (reconstruct frozen world, run agent, evaluate invariant)
-> verify_fix() (prove the fix or reproduce the failure)
-> resolve_incident() (mark resolved + export evidence)
```

Model proposes. RIFT decides. Hashes verify. No model in the verdict path.

## The product loop

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
MARK INCIDENT RESOLVED + EXPORT EVIDENCE
    |
BACK TO PRODUCTION
```

The verified fix becomes the resolution record for the production incident.
The next time this agent encounters the same class of failure, the incident
doesn't disappear into a trace. It already has a world, a diagnosis, a
verified fix, and proof.

## Core primitive

**The frozen incident world**: a hash-sealed artifact capturing the exact
environment in which the agent failed — world state + trajectory + agent
context. It does not merely record what happened; it reconstructs the world
so the same failure can be rifted and killed.

## Limitations

- Incident classes (refund/address/cancel) are deterministic scripted
  environments; production incident capture needs a runtime adapter.
- The recorder currently captures tool calls and DB state; full production
  incident capture would also need to freeze prompt, model weights snapshot,
  retrieved documents, and external API responses.
- Rift against the same agent reproduces the failure; rift against a
  fixed agent verifies the fix; neither guarantees the fix generalizes to
  other scenarios. That's what the incident library compounds over time.

# DELTA — the side-effect firewall for autonomous AI

**An agent shouldn't merely prove it achieved its goal. It must prove it
changed nothing else.**

```
INTENT -> EFFECT CONTRACT -> AGENT -> EXECUTION -> OBSERVE
-> COMPUTE DELTA -> ACCOUNT FOR EVERY EFFECT -> COMMIT / HOLD
```

`ActualDelta ⊆ AuthorizedDelta`. Every mutation must be accounted for.
Unknown = fail closed. No LLM in the verdict path.

```
python3 demo_delta.py   # 10-attack lab
python3 test_delta.py   # 11 tests
```

## Files

- `rift/` — incident reconstruction engine (sim, recorder, miner, engine, llm adapter, board)
- `delta/` — side-effect firewall (contract, world, engine, SDK)
- `demo_rift.py`, `demo_llm.py`, `demo_delta.py` — demos
- `test_rift.py`, `test_llm_adapter.py`, `test_delta.py` — tests
- `cli.py`, `mcp.py` — DELTA surface
- `SUBMISSION.md` — submission copy
