"""DELTA SDK: delta.execute() / delta.transaction() + receipts + replay.

Pipeline:
  INTENT -> EFFECT CONTRACT -> AGENT -> EXECUTION -> OBSERVE
  -> COMPUTE DELTA -> ACCOUNT FOR EVERY EFFECT -> COMMIT / HOLD
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generator, List, Optional
import copy
import json
import os
import uuid
from .contract import Contract
from .engine import Evaluation, Verdict, auto_targets, compensate, evaluate
from .world import World


REGISTRY = os.environ.get("DELTA_REGISTRY", ".delta_runs")


@dataclass
class DeltaResult:
    verdict: Verdict
    evaluation: Evaluation
    execution_id: str
    before: Dict[str, Dict[str, Any]]
    after: Dict[str, Dict[str, Any]]   # observed, pre-recovery
    final: Dict[str, Dict[str, Any]]   # post-recovery (== after if no compensation)
    compensation_log: List[str]
    receipt: str


def _graph_lines(ev: Evaluation) -> List[str]:
    L = ["EFFECT GRAPH:"]
    for c in ev.classified:
        m = c.mutation
        if c.cls in ("AUTHORIZED", "DERIVED"):
            L.append(f"  {m.entity}.{m.field}: {m.old!r} -> {m.new!r}\n"
                     f"    ↑ {c.parent}")
        else:
            L.append(f"  {m.entity}.{m.field}: {m.old!r} -> {m.new!r}\n"
                     f"    ↑ NO AUTHORIZED PARENT [{c.cls}]")
    if not ev.classified:
        L.append("  (no mutations)")
    return L


def format_receipt(contract: Contract, ev: Evaluation, exec_id: str,
                   before: Dict, after: Dict, comp_log: List[str]) -> str:
    auth = [c for c in ev.classified if c.cls in ("AUTHORIZED", "DERIVED")]
    bad = [c for c in ev.classified if c.cls in ("FORBIDDEN", "UNACCOUNTED")]
    L = ["DELTA RECEIPT", "─" * 24, "",
         f"Intent:\n{contract.intent_text}", "",
         "AUTHORIZED", "──────────"]
    for e in contract.effects:
        flag = " (required)" if e.required else ""
        L.append(f"{e.entity}.{e.field} op={e.op} expect={e.expected!r}{flag}")
    if contract.forbidden:
        L.append("")
        L.append("MUST NOT CHANGE")
        for f in contract.forbidden:
            L.append(f"{f.entity}.{f.field} — {f.reason}")
    L += ["", "OBSERVED", "────────"]
    if not ev.classified:
        L.append("(no state transitions)")
    for c in ev.classified:
        m = c.mutation
        mark = "✓" if c.cls in ("AUTHORIZED", "DERIVED") else "✗"
        L.append(f"{mark} {m.entity}.{m.field}: {m.old!r} → {m.new!r} [{c.cls}]")
    L += ["", *_graph_lines(ev), "", "EVIDENCE"]
    for line in ev.evidence:
        L.append(f"  - {line}")
    L += ["",
          f"Accounted: {len(auth)}",
          f"Unaccounted: {len(bad)}"]
    for c in bad:
        m = c.mutation
        L.append(f"  UNACCOUNTED EFFECT: {m.entity}.{m.field}: {m.old!r} → {m.new!r}")
    if ev.missing_required:
        L.append(f"  MISSING REQUIRED: {ev.missing_required}")
    L.append("")
    L.append(f"Compensation:\n" + ("\n".join(f"  {x}" for x in comp_log)
                                  if comp_log else "  NOT ATTEMPTED"))
    L += ["", f"Verdict:\n{ev.verdict.value}", "",
          f"Execution ID:\n{exec_id}", "",
          f"State commitment:\n"
          f"{'COMMITTED' if ev.verdict == Verdict.COMMITTED else 'NOT COMMITTED'}"]
    return "\n".join(L)


def _store(exec_id: str, contract: Contract, result: DeltaResult, world: World) -> None:
    os.makedirs(REGISTRY, exist_ok=True)
    with open(os.path.join(REGISTRY, f"{exec_id}.json"), "w") as fh:
        json.dump({"execution_id": exec_id, "intent": contract.intent_text,
                   "verdict": result.verdict.value,
                   "goal": [contract.goal_entity, contract.goal_field, contract.goal_value],
                   "contract": {
                       "effects": [vars(e) for e in contract.effects],
                       "forbidden": [vars(f) for f in contract.forbidden],
                       "scope": contract.scope_entities,
                       "max_amount_cents": contract.max_amount_cents,
                       "operation_id": contract.operation_id,
                       "pinned": contract.pinned_versions},
                   "seed": {"committed_ops": sorted(world.committed_ops),
                            "unobserved": world.unobserved_writes,
                            "concurrent": sorted(world.concurrent_touched)},
                   "before": result.before, "after": result.after,
                   "final": result.final,
                   "evidence": result.evaluation.evidence,
                   "compensation": result.compensation_log}, fh, indent=2, default=str)


def execute(world: World, contract: Contract,
            agent_fn: Callable[[World], None],
            compensate_targets: Optional[List[tuple]] = None,
            auto_compensate: bool = True) -> DeltaResult:
    """Run agent_fn inside the firewall. Deterministic; no model in verdict path."""
    exec_id = f"exec_{uuid.uuid4().hex[:8]}"  # unique across processes; registry files must never collide
    before = world.snapshot_all()
    world.concurrent_touched.clear()
    # pin EXTERNAL versions for stale-read detection (agent's own writes don't count)
    contract.pinned_versions = {e: world.ext_versions.get(e, 0) for e in before}
    agent_fn(world)
    after = world.snapshot_all()
    ev = evaluate(world, contract, before, after)

    comp_log: List[str] = []
    if ev.verdict == Verdict.BLOCKED and ev.bad:
        if compensate_targets is None and auto_compensate:
            auto, hold = auto_targets(contract, ev.bad)
            if hold and not auto:
                ev.evidence.append(
                    f"HUMAN HOLD: {len(hold)} violation(s) non-auto-recoverable "
                    f"({[(c.mutation.entity, c.mutation.field) for c in hold]}) — no silent restore")
                ev = Evaluation(Verdict.HUMAN_HOLD, ev.goal_met, ev.classified,
                                ev.evidence, ev.authorized_count, ev.bad,
                                ev.missing_required)
            else:
                comp_log = compensate(world, before, auto)
                if hold:
                    ev.evidence.append(
                        f"HOLD REMAINS: {len(hold)} violation(s) need human review; "
                        f"{len(auto)} auto-restored")
                    ev = Evaluation(Verdict.HUMAN_HOLD, ev.goal_met, ev.classified,
                                    ev.evidence, ev.authorized_count, ev.bad,
                                    ev.missing_required)
                else:
                    post = world.snapshot_all()
                    re = evaluate(world, contract, before, post)
                    still = [c for c in re.classified
                             if c.cls in ("FORBIDDEN", "UNACCOUNTED")]
                    if not still and re.goal_met:
                        ev = Evaluation(Verdict.COMPENSATED, True, re.classified,
                                        ev.evidence + [f"COMPENSATED: {len(comp_log)} restored, "
                                                       f"re-verify clean, goal still met"],
                                        re.authorized_count, [])
                    elif not still:
                        ev = Evaluation(Verdict.COMPENSATED, False, re.classified,
                                        ev.evidence + [f"COMPENSATED: violations restored but "
                                                       f"goal not met -> HOLD for review"],
                                        re.authorized_count, [])
                    else:
                        ev.evidence.append("COMPENSATION INCOMPLETE: violations remain")
        elif compensate_targets:
            comp_log = compensate(world, before, compensate_targets)
            post = world.snapshot_all()
            re = evaluate(world, contract, before, post)
            still = [c for c in re.classified if c.cls in ("FORBIDDEN", "UNACCOUNTED")]
            if not still:
                ev = Evaluation(Verdict.COMPENSATED, re.goal_met, re.classified,
                                ev.evidence + [f"COMPENSATED: {len(comp_log)} restored, "
                                               f"unaccounted=0 on re-verify"],
                                re.authorized_count, [])

    receipt = format_receipt(contract, ev, exec_id, before, after, comp_log)
    final = world.snapshot_all()
    result = DeltaResult(ev.verdict, ev, exec_id, before, after, final, comp_log, receipt)
    _store(exec_id, contract, result, world)
    return result


@contextmanager
def transaction(world: World, contract: Contract, **kw) -> Generator[Dict[str, Any], None, None]:
    """with delta.transaction(world, contract) as tx: agent.run(world)"""
    box: Dict[str, Any] = {}
    yield box
    # agent is expected to have run inside the block; evaluate on exit
    box["result"] = execute(world, contract, lambda w: None, **kw)


def replay(contract: Contract, before: Dict, after: Dict,
           tamper: Optional[Callable[[Dict], None]] = None) -> Evaluation:
    """Re-verify a before/after pair under a contract (harness helper)."""
    a2 = copy.deepcopy(after)
    if tamper:
        tamper(a2)
    w = World()
    w.state = copy.deepcopy(before)
    c = copy.copy(contract)
    c.pinned_versions = {}
    return evaluate(w, c, before, a2)


def _load(exec_id: str) -> Dict[str, Any]:
    with open(os.path.join(REGISTRY, f"{exec_id}.json")) as fh:
        return json.load(fh)


def inspect_exec(exec_id: str) -> str:
    d = _load(exec_id)
    return (f"Execution {d['execution_id']}\nIntent: {d['intent']}\n"
            f"Verdict: {d['verdict']}\nEvidence:\n" +
            "\n".join(f"  - {x}" for x in d["evidence"]))


def replay_exec(exec_id: str, tamper: Optional[Callable[[Dict], None]] = None) -> Evaluation:
    """Re-verify a stored receipt; optional tamper() proves invalidation."""
    from .contract import Contract as C, Effect as E, Forbidden as F
    d = _load(exec_id)
    goal_ent, goal_fld, goal_val = d["goal"]
    cd = d["contract"]
    c = C(intent_text=d["intent"], goal_entity=goal_ent,
          goal_field=goal_fld, goal_value=goal_val,
          effects=[E(**e) for e in cd["effects"]],
          forbidden=[F(**f) for f in cd["forbidden"]],
          scope_entities=cd["scope"],
          max_amount_cents=cd["max_amount_cents"],
          operation_id=cd["operation_id"],
          pinned_versions={k: int(v) for k, v in cd["pinned"].items()})
    w = World()
    w.state = copy.deepcopy(d["before"])
    # reseed boundary facts (incl. pre-tx committed ops, WITHOUT this tx's own
    # commit unless it was already committed before execution started)
    seed = d["seed"]
    w.committed_ops = set(seed["committed_ops"])
    if c.operation_id in w.committed_ops and d["verdict"] == "COMMITTED":
        # this very execution performed the commit; replay must not treat the
        # stored post-state as a duplicate of itself
        w.committed_ops.discard(c.operation_id)
    w.unobserved_writes = seed["unobserved"]
    w.concurrent_touched = {tuple(x) for x in seed["concurrent"]}
    # rebuild external-version history consistent with seeds (pins compare equal
    # on clean replay; any tamper shows up in the diff instead)
    for ent in c.pinned_versions:
        w.ext_versions[ent] = 0
    a2 = copy.deepcopy(d.get("final", d["after"]))
    if tamper:
        tamper(a2)
    return evaluate(w, c, d["before"], a2)


def explain_exec(exec_id: str) -> str:
    d = _load(exec_id)
    before, after = d["before"], d["after"]
    lines = [f"Why {d['execution_id']} -> {d['verdict']}:"]
    for ent in sorted(set(before) | set(after)):
        for f in sorted(set(before.get(ent, {})) | set(after.get(ent, {}))):
            o, n = before.get(ent, {}).get(f), after.get(ent, {}).get(f)
            if o != n:
                lines.append(f"  {ent}.{f}: {o!r} -> {n!r}")
    if len(lines) == 1:
        lines.append("  (no state transitions observed)")
    return "\n".join(lines)
