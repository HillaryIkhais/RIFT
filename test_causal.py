"""Deterministic tests for CAUSAL verdicts."""
from causal import execute
from causal.types import Intent, Verdict
from causal.store import World


def test_caused():
    w = World(); w.set("e", "s", "a")
    def fn(ctx, world):
        world.set("e", "s", "b")
        world.emit("refund.succeeded", "e", actor_id=ctx.actor_id,
                   correlation_action_id=ctx.action_id,
                   idempotency_key=ctx.idempotency_key)
    r = execute(w, actor_id="a", intent=Intent("refund", "e", "s", "b"),
                action_type="t", action_fn=fn)
    assert r.verdict == Verdict.CAUSED


def test_not_caused_preexisting():
    w = World(); w.set("e", "s", "b")  # already there
    r = execute(w, actor_id="a", intent=Intent("refund", "e", "s", "b"),
                action_type="t", action_fn=lambda c, wl: None)
    assert r.verdict == Verdict.NOT_CAUSED


def test_contradicted():
    w = World(); w.set("e", "s", "a")
    r = execute(w, actor_id="a", intent=Intent("refund", "e", "s", "b"),
                action_type="t", action_fn=lambda c, wl: None)
    assert r.verdict == Verdict.CONTRADICTED


def test_ambiguous_no_correlation():
    w = World(); w.set("e", "s", "a")
    def fn(ctx, world):
        world.set("e", "s", "b")
        world.emit("refund.succeeded", "e", actor_id="other")  # no echo
    r = execute(w, actor_id="a", intent=Intent("refund", "e", "s", "b"),
                action_type="t", action_fn=fn)
    assert r.verdict == Verdict.AMBIGUOUS


def test_partial():
    w = World(); w.set("e", "f1", "x"); w.set("e", "f2", "x")
    intent = Intent("refund", "e", "", None,
                    parts=[{"field": "f1", "expected": "y"},
                           {"field": "f2", "expected": "y"}])
    def fn(ctx, world):
        world.set("e", "f1", "y")  # only one part
        world.emit("refund.succeeded", "e", actor_id=ctx.actor_id,
                   correlation_action_id=ctx.action_id,
                   idempotency_key=ctx.idempotency_key)
    # after-state has f1=y, f2=x -> partial path triggers via evaluate directly
    from causal.types import ActionRecord
    from causal.engine import evaluate
    before = {"f1": "x", "f2": "x"}
    after = {"f1": "y", "f2": "x"}
    act = ActionRecord("a1", "a", "t", intent, 1000.0, before, "k1")
    from causal.types import EventRecord
    evs = [EventRecord("e1", "refund.succeeded", "e", 1000.1, 1000.1, "a", "a1", "k1")]
    attr = evaluate(act, before, after, evs)
    assert attr.verdict == Verdict.PARTIAL


if __name__ == "__main__":
    test_caused(); test_not_caused_preexisting(); test_contradicted()
    test_ambiguous_no_correlation(); test_partial()
    print("tests pass: 5/5")
