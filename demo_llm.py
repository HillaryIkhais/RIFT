"""REPLAY with a real model. Run: python3 demo_llm.py

Needs REPLAY_LLM_PROVIDER + key (anthropic: ANTHROPIC_API_KEY,
openai: OPENAI_API_KEY). Without a key it runs the OFFLINE FALLBACK: the same
adapter driven by queued model-style replies, proving the model path feeds the
identical immutable pipeline. Detector, freeze, replay, gate untouched.
"""
from rift import (Shop, Recorder, investigate, freeze_incident, replay_incident,
                    verify_fix, seed_sarah, llm_policy, make_client, FakeClient, PROMPTS)
import json
import os


class RecordingClient:
    """Wraps any client; saves raw model replies as live-path evidence.

    Run with a key, then attach
    .replay_store/llm_transcripts/<version>.json to the submission as proof
    the model path drives the identical pipeline.
    """
    def __init__(self, inner, log):
        self.inner, self.log = inner, log

    def chat(self, system, messages):
        reply = self.inner.chat(system, messages)
        self.log.append({"prompt": system, "reply": reply})
        return reply


TASK = {"kind": "refund", "customer": "Sarah Chen",
        "requested_status": "PENDING", "ticket_id": 7}

BUGGY_REPLIES = [
    '{"tool": "lookup_customer", "args": {"name": "Sarah Chen"}}',
    '{"tool": "lookup_order", "args": {"customer_id": 42}}',
    '{"tool": "lookup_refunds", "args": {"order_id": 1842}}',
    '{"tool": "issue_refund", "args": {"refund_id": "R91"}}',
    '{"tool": "update_ticket", "args": {"ticket_id": 7, "status": "RESOLVED"}}',
    '{"tool": "finish", "args": {}}',
]
FIXED_REPLIES = [r.replace("R91", "R92") for r in BUGGY_REPLIES]


def run_with(policy_fn, version):
    shop = Shop()
    shop.restore(seed_sarah())
    rec = Recorder(TASK, version, shop)
    policy_fn(shop, TASK, rec)
    return rec.finish(shop, "done")


try:
    client = make_client()
    mode = "LIVE MODEL"
    transcripts = {"buggy": [], "fixed": []}
    buggy = lambda s, t, r: llm_policy(PROMPTS["refund_buggy"])(
        s, t, r, client=RecordingClient(client, transcripts["buggy"]))
    fixed = lambda s, t, r: llm_policy(PROMPTS["refund_fixed"])(
        s, t, r, client=RecordingClient(client, transcripts["fixed"]))
except RuntimeError as e:
    print(f"(no model key: {e} -> OFFLINE FALLBACK through the same adapter)")
    mode = "OFFLINE FALLBACK"
    buggy = lambda s, t, r: llm_policy(PROMPTS["refund_buggy"])(
        s, t, r, client=FakeClient(BUGGY_REPLIES))
    fixed = lambda s, t, r: llm_policy(PROMPTS["refund_fixed"])(
        s, t, r, client=FakeClient(FIXED_REPLIES))

print(f"[{mode}] buggy-prompt run:")
bad = run_with(buggy, "llm-buggy")
fail = investigate(bad)
if fail is None:
    print("  model did NOT reproduce the failure -- don't fight reality.")
    print("  trajectory saved in .replay_store/runs/; use the deterministic")
    print("  demo_replay.py as the reliable take, this run as the honest one.")
    raise SystemExit(0)
print(f"  {fail['what_happened']}")
frozen = freeze_incident(bad, fail, prompt=PROMPTS["refund_buggy"])
print(f"  INCIDENT RECORDED: {frozen['incident_id']}")

d = verify_fix("llm-buggy", {"refund": buggy}, [frozen])
print(f"  verify_fix: {d['fixed']}/{d['total']} -> {d['verdict']}")
assert d["verdict"] == "FIX_INCOMPLETE"

print(f"[{mode}] fixed-prompt run:")
r = replay_incident(frozen, fixed, "llm-fixed")
print(f"  replay {frozen['incident_id']}: failure_reproduced={r['failure_reproduced']}")
d = verify_fix("llm-fixed", {"refund": fixed}, [frozen])
print(f"  verify_fix: {d['fixed']}/{d['total']} -> {d['verdict']}")
assert d["verdict"] == "FIX_VERIFIED"
if mode == "LIVE MODEL":
    os.makedirs(".replay_store/llm_transcripts", exist_ok=True)
    for name, log in transcripts.items():
        p = f".replay_store/llm_transcripts/llm-{name}.json"
        with open(p, "w") as fh:
            json.dump(log, fh, indent=2)
        print(f"  transcript evidence: {p} ({len(log)} model turns)")
print("model proposed. REPLAY disposed. Boundary holds.")
