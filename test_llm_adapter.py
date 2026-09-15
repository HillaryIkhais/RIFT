"""Adapter tests (offline): the model path feeds the identical pipeline."""
import shutil
import rift.recorder as R
import rift.miner as M
import rift.engine as E
R.STORE = M.STORE = E.STORE = ".replay_test_llm"
shutil.rmtree(".replay_test_llm", ignore_errors=True)
from rift import (Shop, Recorder, investigate, freeze_incident, replay_incident,
                    verify_fix, seed_sarah, llm_policy, FakeClient, PROMPTS)

TASK = {"kind": "refund", "customer": "Sarah Chen",
        "requested_status": "PENDING", "ticket_id": 7}

BUGGY = [
    '{"tool": "lookup_customer", "args": {"name": "Sarah Chen"}}',
    '```json\n{"tool": "lookup_order", "args": {"customer_id": 42}}\n```',
    '{"tool": "lookup_refunds", "args": {"order_id": 1842}}',
    '{"tool": "issue_refund", "args": {"refund_id": "R91"}}',
    '{"tool": "finish", "args": {}}',
]
FIXED = [r.replace("R91", "R92") for r in BUGGY]


def run_with(replies, prompt):
    shop = Shop()
    shop.restore(seed_sarah())
    rec = Recorder(TASK, "t", shop)
    llm_policy(prompt)(shop, TASK, rec, client=FakeClient(replies))
    return rec.finish(shop, "done")


def test_adapter_mistake_frozen():
    run = run_with(BUGGY, PROMPTS["refund_buggy"])
    f = investigate(run)
    assert f["category"] == "WRONG_ENTITY_SELECTION" and f["bad_selection"] == "R91"
    frozen = freeze_incident(run, f)
    assert replay_incident(frozen, lambda s, t, r: llm_policy(PROMPTS["refund_buggy"])(
        s, t, r, client=FakeClient(BUGGY)), "v")["failure_reproduced"]

def test_adapter_fix_verified():
    run = run_with(BUGGY, PROMPTS["refund_buggy"])
    frozen = freeze_incident(run, investigate(run))
    fixed = lambda s, t, r: llm_policy(PROMPTS["refund_fixed"])(
        s, t, r, client=FakeClient(FIXED))
    assert verify_fix("fixed", {"refund": fixed}, [frozen])["verdict"] == "FIX_VERIFIED"

def test_garbage_output_safe():
    run = run_with(["totally not json {{{", "also garbage"], PROMPTS["refund_buggy"])
    assert run["events"] == []
    assert investigate(run) is None


if __name__ == "__main__":
    test_adapter_mistake_frozen()
    test_adapter_fix_verified()
    test_garbage_output_safe()
    print("tests pass: 3/3")
