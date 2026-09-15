"""DELTA effect contracts: what the agent is allowed to CHANGE (not just call).

The LLM may PROPOSE a contract. The policy/runtime decides whether it is
acceptable. Authorization lives here, not in the model.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import fnmatch


# Recovery classification per effect: how a violation of this shape recovers.
# REVERSIBLE -> auto-compensate by restoring before-value, then re-verify.
# COMPENSATABLE -> compensate via a registered inverse action (not raw restore).
# IRREVERSIBLE -> no technical recovery; HUMAN_REVIEW / HUMAN_HOLD.
RECOVERY = ("REVERSIBLE", "COMPENSATABLE", "IRREVERSIBLE", "HUMAN_REVIEW")


@dataclass(frozen=True)
class Effect:
    """One authorized mutation. entity/field support glob patterns."""
    entity: str          # e.g. "customer:alice" or "audit:*" or "refund:*"
    field: str           # e.g. "email" or "*" (CREATE allowed)
    expected: Any = "*"  # exact new value, ("delta", -100), or "*" any
    op: str = "SET"      # SET | CREATE | DELTA
    derived: bool = False
    required: bool = False   # must be observed, else PARTIAL (not silent success)
    recovery: str = "REVERSIBLE"


@dataclass(frozen=True)
class Forbidden:
    """Negative assertion: this shape MUST NOT change. Beats any Effect."""
    entity: str
    field: str = "*"
    reason: str = ""


@dataclass
class Contract:
    intent_text: str
    goal_entity: str
    goal_field: str
    goal_value: Any
    effects: List[Effect] = field(default_factory=list)
    forbidden: List[Forbidden] = field(default_factory=list)
    scope_entities: List[str] = field(default_factory=list)
    max_amount_cents: Optional[int] = None
    operation_id: Optional[str] = None          # idempotency key for the tx
    pinned_versions: Dict[str, int] = field(default_factory=dict)  # stale-read guard

    def forbids(self, entity: str, fld: str) -> Optional[Forbidden]:
        for f in self.forbidden:
            if fnmatch.fnmatch(entity, f.entity) and (
                    f.field == "*" or fnmatch.fnmatch(fld, f.field)):
                return f
        return None

    def allows(self, entity: str, fld: str, old: Any, new: Any) -> Optional[Effect]:
        for e in self.effects:
            if not fnmatch.fnmatch(entity, e.entity):
                continue
            if e.field != "*" and not fnmatch.fnmatch(fld, e.field):
                continue
            if e.op == "CREATE" and old is not None:
                continue
            if e.op == "DELTA" and isinstance(e.expected, (tuple, list)) \
                    and len(e.expected) == 2 and e.expected[0] == "delta":
                # op=DELTA budget, e.g. ("delta", -100); lists accepted because
                # JSON registry round-trips tuples -> lists on replay.
                try:
                    if new - old != e.expected[1]:
                        continue
                except TypeError:
                    continue
            elif e.expected != "*" and e.expected != new:
                continue
            return e
        return None

    def in_scope(self, entity: str) -> bool:
        if not self.scope_entities:
            return True
        return any(fnmatch.fnmatch(entity, p) for p in self.scope_entities)


# System-generated fields: auto-classified DERIVED (allowed) iff entity is in scope.
SYSTEM_FIELDS = {"updated_at", "profile_version", "event_id", "version", "observed_at"}


def compile_refund(customer: str, amount_cents: int, refund_id: str,
                   operation_id: Optional[str] = None) -> Contract:
    return Contract(
        intent_text=f"Refund {customer} ${amount_cents/100:.2f}",
        goal_entity=f"refund:{refund_id}", goal_field="status", goal_value="succeeded",
        effects=[
            Effect(f"refund:{refund_id}", "status", "succeeded", required=True),
            Effect(f"refund:{refund_id}", "*", "*", op="CREATE"),
            Effect(customer, "balance", ("delta", -amount_cents), op="DELTA",
                   required=True, recovery="REVERSIBLE"),
            Effect("audit:*", "*", "*", op="CREATE", required=True),
        ],
        forbidden=[
            Forbidden(customer, "sub", "subscription change not authorized by a refund"),
            Forbidden(customer, "risk", "risk score must never move on a refund"),
            Forbidden(customer, "email", "identity fields frozen for this intent"),
            Forbidden(customer, "plan", "tier change requires its own intent"),
            # NOTE: other accounts are contained by scope_entities, not by a
            # customer:* glob here — such a glob would also match the subject
            # itself and veto its own authorized move. Out-of-scope mutations
            # fail closed as UNACCOUNTED.
            Forbidden("repo:*", "*", "code state out of scope for a refund"),
        ],
        scope_entities=[f"refund:{refund_id}", customer, "audit:*"],
        max_amount_cents=amount_cents,
        operation_id=operation_id,
    )


def compile_update_email(customer: str, new_email: str,
                         operation_id: Optional[str] = None) -> Contract:
    return Contract(
        intent_text=f"Update {customer} email to {new_email}",
        goal_entity=customer, goal_field="email", goal_value=new_email,
        effects=[
            Effect(customer, "email", new_email, required=True,
                   recovery="HUMAN_REVIEW"),  # identity write: no silent auto-restore
            Effect("audit:*", "*", "*", op="CREATE", required=True),
        ],
        forbidden=[
            Forbidden(customer, "balance", "email change must not move money"),
            Forbidden(customer, "plan", "tier change requires its own intent"),
            Forbidden(customer, "risk", "risk score frozen for this intent"),
            # Other identities contained by scope (see note above).
        ],
        scope_entities=[customer, "audit:*"],
        operation_id=operation_id,
    )
