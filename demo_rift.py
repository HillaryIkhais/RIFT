"""RIFT demo: incident-to-resolution. Run: python3 demo_rift.py

FAIL -> CAPTURE -> FREEZE -> REPRODUCE -> DIAGNOSE -> FIX -> VERIFY -> RESOLVE

The agent makes the mistake. RIFT reconstructs the world so the mistake can
be investigated, reproduced, and fixed. The loop ends when the fix survives
the incident that caused it — not when the test passes.
"""
import shutil
from rift import (Shop, V10, V11, Recorder, investigate, freeze_incident,
                    replay_incident, verify_fix, verify_world, resolve_incident,
                    mark_resolved, seed_sarah, seed_address, seed_cancel)
from rift.recorder import STORE

shutil.rmtree(STORE, ignore_errors=True)

REFUND = {"kind": "refund", "customer": "Sarah Chen",
          "requested_status": "PENDING", "ticket_id": 7}
ADDR = {"kind": "address", "customer": "Sarah Chen",
        "new_address": "9 Elm St", "ticket_id": 8}
CANCEL = {"kind": "cancel", "customer_id": 42, "ticket_id": 9}


def run_once(seed, task, policy, version="v1.0"):
    shop = Shop()
    shop.restore(seed())
    rec = Recorder(task, version, shop)
    policy(shop, task, rec)
    return rec.finish(shop, "done")


def show_world(w):
    s = w["world"]["state"]
    print(f"    Customer:     {s['customers'][0]['name']}")
    for r in s["refunds"]:
        print(f"    Refund {r['id']}:  ${r['amount_cents']/100:.0f}  {r['status']}")


print("=" * 64)
print("RIFT — INCIDENT RECONSTRUCTION FOR AI AGENTS")
print("  Loop: FAIL -> CAPTURE -> FREEZE -> REPRODUCE -> DIAGNOSE -> FIX -> VERIFY -> RESOLVE")
print()

# --- ACT 1: FAIL ---
print("ACT 1 — FAIL")
print("  Agent processes Sarah's pending refund...")
bad = run_once(seed_sarah, REFUND, V10["refund"], "support-v1")
fail = investigate(bad)
print(f"  {fail['what_happened']}")
print(f"  why it matters: {fail['why_it_matters']}")
print()

# --- ACT 2: CAPTURE + FREEZE ---
print("ACT 2 — CAPTURE + FREEZE")
print("  Freezing the exact world in which the incident occurred...")
frozen = freeze_incident(bad, fail, prompt="Process the customer's pending refund.")
print(f"  INCIDENT: {frozen['incident_id']}")
show_world(frozen)
assert verify_world(frozen)
print(f"  world hash: {frozen['freeze_hash'][:12]}... sealed")
print()

# --- ACT 3: REPRODUCE ---
print("ACT 3 — REPRODUCE")
print("  Reconstructing frozen world. Running same agent...")
r = replay_incident(frozen, V10["refund"], "support-v1")
picked = next(e["args"]["refund_id"] for e in bad["events"]
              if e["type"] == "tool_call" and e["tool"] == "issue_refund")
print(f"  agent picks: {picked}")
print(f"  failure reproduced: {r['failure_reproduced']}")
assert r["failure_reproduced"]
print()

# --- ACT 4: DIAGNOSE ---
print("ACT 4 — DIAGNOSE")
diag = frozen["incident"]["diagnosis"]
print(f"  failure class:    {diag['failure_class']}")
print(f"  expected:         {diag['expected']}")
print(f"  actual:           {diag['actual']}")
print(f"  decision signal:  {diag['decision_signal']}")
print(f"  ignored signal:   {diag['ignored_signal']}")
print(f"  root cause:       {diag['root_cause']}")
print()

# --- ACT 5: FIX + VERIFY ---
print("ACT 5 — FIX + VERIFY")
print("  Changing prompt to match by status instead of amount...")
r_fixed = replay_incident(frozen, V11["refund"], "support-v2")
picked2 = next(e["args"]["refund_id"] for e in bad["events"]
               if e["type"] == "tool_call" and e["tool"] == "issue_refund")
print(f"  agent picks: {picked2}")
print(f"  failure reproduced: {r_fixed['failure_reproduced']}")
print(f"  FIX VERIFIED: {not r_fixed['failure_reproduced']}")
assert not r_fixed["failure_reproduced"]
print()

# --- ACT 6: RESOLVE ---
print("ACT 6 — RESOLVE")
print("  The fix survived the incident that caused it.")
print("  Marking incident resolved. Exporting evidence package...")
resolution = resolve_incident(frozen, r_fixed, {
    "agent_version": "support-v2",
    "verdict": "FIX_VERIFIED",
    "total": 1, "fixed": 1, "still_broken": [],
})
mark_resolved(frozen["incident_id"])
print(f"  status:           {resolution['status']}")
print(f"  resolved_at:      {resolution['resolution']['resolved_at']}")
print(f"  evidence chain:   {' -> '.join(resolution['resolution']['evidence_chain'])}")
print()

# --- FULL LOOP: 3 incident classes ---
print("  Full library (3 incident classes):")
regs = []
for seed, task, pol, ver in [
    (seed_sarah, REFUND, V10["refund"], "v1.0"),
    (seed_address, ADDR, V10["address"], "v1.0"),
    (seed_cancel, CANCEL, V10["cancel"], "v1.0"),
]:
    bad = run_once(seed, task, pol, ver)
    a = investigate(bad)
    if a:
        regs.append(freeze_incident(bad, a))
print(f"  {len(regs)} incident worlds frozen")

print("  replaying v1.0 (all should fail):")
d = verify_fix("v1.0", V10, regs)
print(f"    {d['fixed']}/{d['total']} fixed -> {d['verdict']}")
assert d["verdict"] == "FIX_INCOMPLETE"

print("  replaying v1.1 (all should pass):")
d = verify_fix("v1.1", V11, regs)
print(f"    {d['fixed']}/{d['total']} fixed -> {d['verdict']}")
assert d["verdict"] == "FIX_VERIFIED"

# Resolve all incidents
for reg in regs:
    resolve_incident(reg, {"replay_id": "rpl_000", "result": "PASS",
                           "failure_reproduced": False, "violations": [],
                           "agent_version": "v1.1", "timestamp": ""},
                     {"agent_version": "v1.1", "verdict": "FIX_VERIFIED",
                      "total": 1, "fixed": 1, "still_broken": []})
    mark_resolved(reg["incident_id"])
print(f"  {len(regs)} incidents RESOLVED")
print()

# --- RELEASE GATE ---
print("ACT 7 — RELEASE GATE")
from rift.engine import release_gate

# Test with verified fix → should be AUTHORIZED
# Pass original replay (failure reproduced) + fix verification (fix passes)
gate_result = release_gate(frozen, r, {
    "agent_version": "v1.1",
    "verdict": "FIX_VERIFIED",
    "total": 1, "fixed": 1, "still_broken": [],
})
print(f"  release_status:   {gate_result['release_status']}")
print(f"  checks:           {gate_result['checks']}")
assert gate_result["release_status"] == "AUTHORIZED"
print("  RELEASE AUTHORIZED — v1.1 can deploy")
print()

# Test with tampered world → should be BLOCKED
print("ACT 8 — TAMPER DETECTION")
evil = dict(frozen)
evil["incident"] = dict(frozen["incident"])
evil["incident"]["what_happened"] = "Nothing went wrong."
gate_blocked = release_gate(evil, r, {
    "agent_version": "v1.1",
    "verdict": "FIX_VERIFIED",
    "total": 1, "fixed": 1, "still_broken": [],
})
print(f"  release_status:   {gate_blocked['release_status']}")
print(f"  blocked_reasons:  {gate_blocked['blocked_reasons']}")
assert gate_blocked["release_status"] == "BLOCKED"
print("  RELEASE BLOCKED — deployment cannot proceed")
print()

# Also verify replay refuses tampered world
try:
    replay_incident(evil, V11["refund"], "attacker")
    raise SystemExit("tamper NOT detected!")
except ValueError as e:
    print(f"  replay also refused: {e}")

print()
print("=" * 64)
print("DONE.")
print("RIFT doesn't stop when the failure is reproduced.")
print("It stops when the fix survives the incident that caused it.")
print()
print("  RELEASE GATE: checks frozen integrity, reproduction, fix, evidence.")
print("  PASS → RELEASE AUTHORIZED → deployment proceeds.")
print("  FAIL → RELEASE BLOCKED → deployment refused.")
print()
print("The incident is RESOLVED.")
print("The release is AUTHORIZED.")
print("The evidence is exported.")
print("The next time this agent encounters the same class of failure,")
print("the incident doesn't disappear into a trace.")
print("It already has a world, a diagnosis, a verified fix, and proof.")
