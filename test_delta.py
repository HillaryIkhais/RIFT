"""DELTA tests: ACTUAL ⊆ AUTHORIZED, fail-closed, recovery-aware."""
import os
os.environ["DELTA_REGISTRY"] = ".delta_test_runs"  # never clobber the demo lab registry
from delta import execute, replay
from delta.contract import compile_refund
from delta.engine import Verdict
from delta.world import World


def fresh():
    w = World()
    w.state = {"customer:alice": {"balance": 1000, "plan": "basic", "risk": 21}}
    return w

C = lambda **kw: compile_refund("customer:alice", 100, "r1", **kw)

def good(w):
    w.set("refund:r1", "status", "succeeded", actor="agent")
    w.set("customer:alice", "balance", 900, actor="agent")
    w.create("audit:e1", {"kind": "refund"}, actor="agent")


def test_commit():
    assert execute(fresh(), C(), good).verdict == Verdict.COMMITTED

def test_hidden_blocked_forbidden():
    def f(w):
        good(w); w.set("customer:alice", "risk", 91, actor="tool")
    r = execute(fresh(), C(), f, auto_compensate=False)
    assert r.verdict == Verdict.BLOCKED
    assert any(c.cls == "FORBIDDEN" for c in r.evaluation.classified)

def test_cross_account_blocked():
    def f(w):
        good(w)
        w.state.setdefault("customer:bob", {})["balance"] = 400  # out of scope
    r = execute(fresh(), C(), f, auto_compensate=False)
    assert r.verdict == Verdict.BLOCKED

def test_tool_lie_blocked():
    assert execute(fresh(), C(), lambda w: None).verdict == Verdict.BLOCKED

def test_auto_compensated():
    def f(w):
        good(w); w.set("customer:alice", "plan", "enterprise", actor="agent")
    # plan shape is auto-recoverable -> restored + re-verified
    r = execute(fresh(), C(), f)
    assert r.verdict == Verdict.COMPENSATED, r.verdict

def test_explicit_targets_compensated():
    def f(w):
        good(w); w.set("customer:alice", "sub", "cancelled", actor="webhook")
    r = execute(fresh(), C(), f, compensate_targets=[("customer:alice", "sub")])
    assert r.verdict == Verdict.COMPENSATED, r.verdict

def test_partial_missing_required():
    def f(w):
        w.set("refund:r1", "status", "succeeded", actor="agent")
        w.set("customer:alice", "balance", 900, actor="agent")
    assert execute(fresh(), C(), f).verdict == Verdict.PARTIAL

def test_idempotent_replay():
    w = fresh()
    assert execute(w, C(operation_id="op-1"), good).verdict == Verdict.COMMITTED
    assert execute(w, C(operation_id="op-1"), good).verdict == Verdict.BLOCKED

def test_stale_hold():
    def f(w):
        w.set("customer:alice", "balance", 950, actor="x", external=True)
        good(w)
    assert execute(fresh(), C(), f).verdict == Verdict.HUMAN_HOLD

def test_unobserved_hold():
    def f(w):
        good(w); w.write_unobserved("snowflake", "x")
    assert execute(fresh(), C(), f).verdict == Verdict.HUMAN_HOLD

def test_replay_tamper():
    r = execute(fresh(), C(), good)
    assert replay(C(), r.before, r.after).verdict == Verdict.COMMITTED
    assert replay(C(), r.before, r.after,
                 tamper=lambda a: a["customer:alice"].__setitem__("risk", 91)
                 ).verdict == Verdict.BLOCKED


if __name__ == "__main__":
    test_commit(); test_hidden_blocked_forbidden(); test_cross_account_blocked()
    test_tool_lie_blocked(); test_auto_compensated(); test_explicit_targets_compensated()
    test_partial_missing_required(); test_idempotent_replay(); test_stale_hold()
    test_unobserved_hold(); test_replay_tamper()
    print("tests pass: 11/11")
