"""CAUSAL demo: 'This agent says it refunded a customer. The refund exists. But it didn't cause it.'

Run: python demo.py
"""
from causal import execute
from causal.types import Intent, Verdict
from causal.store import World


def section(t): print("\n" + "=" * 68 + f"\n{t}\n" + "=" * 68)


def agent_refund(ctx, world, propagate=True):
    world.advance(0.067)
    world.set(ctx.intent.entity, "status", "succeeded")
    world.emit("refund.created", ctx.intent.entity, actor_id=ctx.actor_id,
               correlation_action_id=ctx.action_id if propagate else None,
               idempotency_key=ctx.idempotency_key if propagate else None)
    world.advance(0.013)
    world.emit("refund.succeeded", ctx.intent.entity, actor_id=ctx.actor_id,
               correlation_action_id=ctx.action_id if propagate else None,
               idempotency_key=ctx.idempotency_key if propagate else None)


# 1. CAUSED
section("1. HONEST AGENT -> CAUSED")
w = World(); w.set("payment_992", "status", "captured")
r = execute(w, actor_id="agent_07",
            intent=Intent("refund", "payment_992", "status", "succeeded"),
            action_type="stripe.refund",
            action_fn=agent_refund)
print(r.receipt)
assert r.verdict == Verdict.CAUSED

# 2. Pre-existing outcome -> NOT_CAUSED
section("2. PRE-EXISTING OUTCOME (human refunded 30s earlier) -> NOT_CAUSED")
w = World(); w.set("payment_992", "status", "captured")
w.emit("refund.succeeded", "payment_992", actor_id="human_ops",
       occurred_at=w.now - 30.0)  # backdated authoritative timestamp
w.set("payment_992", "status", "succeeded")
w.advance(30.0)
r = execute(w, actor_id="agent_07",
            intent=Intent("refund", "payment_992", "status", "succeeded"),
            action_type="stripe.refund",
            action_fn=lambda ctx, world: world.advance(0.05))  # agent no-op, state already there
print(r.receipt)
assert r.verdict == Verdict.NOT_CAUSED, r.verdict

# 3. Concurrent actor -> AMBIGUOUS
section("3. CONCURRENT ACTOR (human + agent same second, no correlation) -> AMBIGUOUS")
w = World(); w.set("pr_481", "status", "open")
def race(ctx, world):
    world.advance(0.1)
    # human merges concurrently, no correlation token
    world.emit("pr.merged", "pr_481", actor_id="human_maintainer")
    world.set("pr_481", "status", "merged")
    # agent's own event also lands but WITHOUT echo -> cannot disambiguate
    world.emit("pr.merged", "pr_481", actor_id="agent_07")
r = execute(w, actor_id="agent_07",
            intent=Intent("merge", "pr_481", "status", "merged"),
            action_type="github.merge",
            action_fn=race)
print(r.receipt)
assert r.verdict == Verdict.AMBIGUOUS, r.verdict

# 4. Wrong entity -> CONTRADICTED
section("4. WRONG ENTITY (agent touches 481, 814 changes) -> CONTRADICTED")
w = World(); w.set("customer_481", "plan", "pro"); w.set("customer_814", "plan", "pro")
def wrong(ctx, world):
    world.advance(0.05)
    world.set("customer_814", "plan", "enterprise")  # oops, wrong customer
    world.emit("customer.plan_changed", "customer_814", actor_id=ctx.actor_id,
               correlation_action_id=ctx.action_id)
r = execute(w, actor_id="agent_07",
            intent=Intent("upgrade_plan", "customer_481", "plan", "enterprise"),
            action_type="crm.upgrade",
            action_fn=wrong)
print(r.receipt)
assert r.verdict == Verdict.CONTRADICTED, r.verdict

# 5. Delayed event w/ old timestamp -> NOT_CAUSED
section("5. DELAYED EVENT (arrives late, timestamp predates action) -> NOT_CAUSED")
w = World(); w.set("payment_100", "status", "due")
t_action = w.now
def delayed(ctx, world):
    world.advance(30.0)  # event arrives 30s later...
    world.set("payment_100", "status", "collected")
    world.emit("payment.collected", "payment_100", actor_id="someone_else",
               occurred_at=t_action - 2.0)  # ...but authoritatively happened BEFORE action
r = execute(w, actor_id="agent_07",
            intent=Intent("collect", "payment_100", "status", "collected"),
            action_type="stripe.collect",
            action_fn=delayed)
print(r.receipt)
assert r.verdict == Verdict.NOT_CAUSED, r.verdict

# 6. Cascade chain -> CAUSED with DIRECT + DERIVED
section("6. CASCADING ACTION (cancel -> webhook -> CRM -> email) -> CAUSED + chain")
w = World(); w.set("sub_7", "status", "active")
w.set("crm_7", "status", "active"); w.set("email_7", "status", "idle")
def cascade(ctx, world):
    world.advance(0.05)
    world.set("sub_7", "status", "cancelled")
    d = world.emit("subscription.cancelled", "sub_7", actor_id=ctx.actor_id,
                   correlation_action_id=ctx.action_id,
                   idempotency_key=ctx.idempotency_key)
    world.advance(0.05)  # webhook derives billing + crm + email states
    b = world.emit("subscription.cancelled", "billing_7", actor_id="stripe_webhook",
                   parent_event_id=d.event_id)
    world.set("billing_7", "status", "cancelled")
    c = world.emit("subscription.cancelled", "crm_7", actor_id="stripe_webhook",
                   parent_event_id=b.event_id)
    world.set("crm_7", "status", "churned")
    world.emit("subscription.cancelled", "email_7", actor_id="workflow",
               parent_event_id=c.event_id)
    world.set("email_7", "status", "sent")
r = execute(w, actor_id="agent_07",
            intent=Intent("cancel", "sub_7", "status", "cancelled"),
            action_type="stripe.cancel_subscription",
            action_fn=cascade)
print(r.receipt)
assert r.verdict == Verdict.CAUSED, r.verdict
derived = [n for n in r.attribution.chain if n.link.value == "DERIVED"]
print(f"\nchain: 1 DIRECT + {len(derived)} DERIVED events tracked")
assert len(derived) >= 2

# 7. State correct but unattributed -> AMBIGUOUS is not success
section("7. UNCORRELATED SYSTEM WRITE (state matches, no causal token) -> AMBIGUOUS")
w = World(); w.set("deploy_prod", "version", "2.3")
def ghost(ctx, world):
    world.advance(0.2)
    world.set("deploy_prod", "version", "2.4")  # CI/CD did it; no echo of action_id
    world.emit("deploy.finished", "deploy_prod", actor_id="cicd_bot")
r = execute(w, actor_id="agent_07",
            intent=Intent("deploy", "deploy_prod", "version", "2.4"),
            action_type="aws.deploy",
            action_fn=ghost)
print(r.receipt)
assert r.verdict == Verdict.AMBIGUOUS, r.verdict

print("\n" + "=" * 68)
print("ALL 7 SCENARIOS PASS. State != causality.")
print("Pitch: AI agents can observe that something happened.")
print("       CAUSAL proves whether they caused it.")
print("=" * 68)
