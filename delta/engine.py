"""DELTA engine: ACTUAL EFFECTS ⊆ AUTHORIZED EFFECTS. No LLM in the verdict path.

Classification lattice (first match wins):
  FORBIDDEN   — matches a negative assertion. Vetoes even allowed shapes.
  AMBIGUOUS   — exact field also written by an external actor.
  AUTHORIZED  — matches an approved effect.
  DERIVED     — system-generated field on an in-scope entity.
  UNACCOUNTED — everything else, including out-of-scope entities. Fail closed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import fnmatch
from .contract import Contract, SYSTEM_FIELDS
from .world import World


class Verdict(str, Enum):
    COMMITTED = "COMMITTED"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"
    UNACCOUNTED = "UNACCOUNTED"
    AMBIGUOUS = "AMBIGUOUS"
    COMPENSATED = "COMPENSATED"
    HUMAN_HOLD = "HUMAN_HOLD"


@dataclass(frozen=True)
class Mutation:
    entity: str
    field: str
    old: Any
    new: Any
    op: str  # CREATE | SET | DELETE


@dataclass
class Classified:
    mutation: Mutation
    cls: str  # AUTHORIZED | DERIVED | FORBIDDEN | UNACCOUNTED | AMBIGUOUS
    note: str
    parent: Optional[str] = None  # effect-graph edge: what authorizes this


@dataclass
class Evaluation:
    verdict: Verdict
    goal_met: bool
    classified: List[Classified]
    evidence: List[str]
    authorized_count: int
    bad: List[Classified]  # FORBIDDEN + UNACCOUNTED
    missing_required: List[str] = field(default_factory=list)

    @property
    def commit(self) -> bool:
        return self.verdict == Verdict.COMMITTED


def diff_states(before: Dict[str, Dict[str, Any]],
                after: Dict[str, Dict[str, Any]]) -> List[Mutation]:
    muts: List[Mutation] = []
    for ent in sorted(set(before) | set(after)):
        b, a = before.get(ent, {}), after.get(ent, {})
        for f in sorted(set(b) | set(a)):
            o, n = b.get(f), a.get(f)
            if o == n:
                continue
            op = "CREATE" if f not in b else ("DELETE" if f not in a else "SET")
            muts.append(Mutation(ent, f, o, n, op))
    return muts


def _human_review(contract: Contract, m: Mutation) -> bool:
    """True if this mutation's shape carries a non-auto recovery class."""
    for e in contract.effects:
        if fnmatch.fnmatch(m.entity, e.entity) and (
                e.field == "*" or fnmatch.fnmatch(m.field, e.field)):
            if e.recovery != "REVERSIBLE":
                return True
    return False


def evaluate(world: World, contract: Contract,
             before: Dict[str, Dict[str, Any]],
             after: Dict[str, Dict[str, Any]]) -> Evaluation:
    ev: List[str] = []

    # 0a. Unobserved boundary: something changed where DELTA cannot see.
    if world.unobserved_writes > 0:
        ev.append(f"HOLD: {world.unobserved_writes} write(s) outside the observed "
                  f"boundary -> UNACCOUNTED unknown effect. Never assume success.")
        return Evaluation(Verdict.HUMAN_HOLD, False, [], ev, 0, [])

    # 0b. Idempotency: operation already committed.
    if contract.operation_id and contract.operation_id in world.committed_ops:
        ev.append(f"BLOCKED: operation_id={contract.operation_id!r} already committed "
                  f"-> duplicate/replay rejected, no second mutation.")
        return Evaluation(Verdict.BLOCKED, False, [], ev, 0, [])

    # 0c. Staleness: external versions moved under us (concurrent modification).
    for ent, pin in contract.pinned_versions.items():
        if world.ext_versions.get(ent, 0) != pin:
            ev.append(f"HOLD: {ent} externally modified during execution "
                      f"(stale read) -> cannot commit on moved state.")
            return Evaluation(Verdict.HUMAN_HOLD, False, [], ev, 0, [])

    muts = diff_states(before, after)
    ev.append(f"OBSERVED {len(muts)} mutation(s) across "
              f"{len(set(m.entity for m in muts)) or 0} entit(ies)")

    goal_now = after.get(contract.goal_entity, {}).get(contract.goal_field)
    goal_met = goal_now == contract.goal_value
    ev.append(f"GOAL {contract.goal_entity}.{contract.goal_field}={goal_now!r} "
              f"(want {contract.goal_value!r}) -> {'MET' if goal_met else 'NOT MET'}")

    classified: List[Classified] = []
    auth_mutations: List[Mutation] = []
    for m in muts:
        fb = contract.forbids(m.entity, m.field)
        if fb is not None:
            classified.append(Classified(m, "FORBIDDEN",
                f"MUST NOT change: {fb.reason or fb.entity + '.' + fb.field}",
                parent=None))
            continue
        if not contract.in_scope(m.entity):
            classified.append(Classified(m, "UNACCOUNTED",
                f"entity {m.entity} outside scope {contract.scope_entities}",
                parent=None))
            continue
        if (m.entity, m.field) in world.concurrent_touched:
            classified.append(Classified(m, "AMBIGUOUS",
                f"{m.entity}.{m.field} also written by external actor",
                parent=None))
            continue
        hit = contract.allows(m.entity, m.field, m.old, m.new)
        if hit is not None:
            classified.append(Classified(
                m, "DERIVED" if hit.derived else "AUTHORIZED",
                f"matches effect {hit.entity}.{hit.field}",
                parent=f"contract:{hit.entity}.{hit.field}"))
            auth_mutations.append(m)
            continue
        if m.field in SYSTEM_FIELDS:
            # derived edge: caused by an authorized mutation on the same entity
            sibs = [a for a in auth_mutations if a.entity == m.entity]
            parent = (f"mutation:{sibs[0].entity}.{sibs[0].field}"
                      if sibs else f"scope:{m.entity}")
            classified.append(Classified(m, "DERIVED",
                f"system field {m.field} on in-scope entity", parent=parent))
            continue
        classified.append(Classified(m, "UNACCOUNTED", "no matching authorized effect",
                                     parent=None))

    bad = [c for c in classified if c.cls in ("FORBIDDEN", "UNACCOUNTED")]
    ambig = [c for c in classified if c.cls == "AMBIGUOUS"]
    auth = [c for c in classified if c.cls in ("AUTHORIZED", "DERIVED")]

    if not goal_met and bad:
        ev.append(f"BLOCKED: goal not met + {len(bad)} forbidden/unaccounted mutation(s)")
        return Evaluation(Verdict.BLOCKED, goal_met, classified, ev, len(auth), bad)
    if not goal_met:
        ev.append("BLOCKED: goal not met (tool lied or no-op)")
        return Evaluation(Verdict.BLOCKED, goal_met, classified, ev, len(auth), bad)
    if bad:
        kinds = {}
        for c in bad:
            kinds[c.cls] = kinds.get(c.cls, 0) + 1
        ev.append(f"BLOCKED: goal succeeded BUT {len(bad)} {kinds} "
                  f"-> ActualDelta ⊄ AuthorizedDelta")
        for c in bad:
            m = c.mutation
            ev.append(f"  {c.cls}: {m.entity}.{m.field}: {m.old!r} -> {m.new!r} "
                      f"(NO AUTHORIZED PARENT)")
        return Evaluation(Verdict.BLOCKED, goal_met, classified, ev, len(auth), bad)
    if ambig:
        ev.append(f"HOLD: {len(ambig)} mutation(s) with unattributable origin -> HUMAN_HOLD")
        return Evaluation(Verdict.HUMAN_HOLD, goal_met, classified, ev, len(auth), bad)

    # Required-effect coverage -> PARTIAL, not silent success.
    missing = []
    for e in contract.effects:
        if not e.required:
            continue
        seen = any(c.mutation.entity == e.entity or
                   (fnmatch.fnmatch(c.mutation.entity, e.entity))
                   for c in auth if c.parent == f"contract:{e.entity}.{e.field}")
        if not seen:
            missing.append(f"{e.entity}.{e.field}")
    if missing:
        ev.append(f"PARTIAL: goal met, 0 unaccounted, but required effects missing: {missing}")
        return Evaluation(Verdict.PARTIAL, goal_met, classified, ev, len(auth), bad,
                          missing_required=missing)

    ev.append(f"COMMITTED: goal met, {len(auth)}/{len(muts)} accounted, 0 unaccounted")
    if contract.operation_id:
        world.committed_ops.add(contract.operation_id)
    return Evaluation(Verdict.COMMITTED, goal_met, classified, ev, len(auth), bad)


def auto_targets(contract: Contract, bad: List[Classified]) -> Tuple[List[Tuple[str, str]], List[Classified]]:
    """Split violations into auto-compensatable vs human-review by recovery class."""
    auto, hold = [], []
    for c in bad:
        (hold if _human_review(contract, c.mutation) else auto).append(c)
    return ([(c.mutation.entity, c.mutation.field) for c in auto], hold)


def compensate(world: World, before: Dict[str, Dict[str, Any]],
               targets: List[Tuple[str, str]]) -> List[str]:
    log = []
    for ent, f in targets:
        old = before.get(ent, {}).get(f)
        cur = world.state.get(ent, {}).get(f)
        world.compensate(ent, f, old)
        log.append(f"compensate {ent}.{f}: {cur!r} -> {old!r}")
    return log
