"""Incident analyst: observed violation -> frozen incident world.

Two-stage discipline (the hard gate in the loop):
  1. INVESTIGATE (deterministic rules over trajectory + state diff). No LLM vote.
  2. FREEZE (world + incident analysis + fix verification hashed into immutable artifact).

The frozen artifact reconstructs the exact environment in which the agent failed:
world state + trajectory + agent context. Hash-verified so it cannot silently drift.
An LLM may *propose* invariant wording; evaluation is always deterministic.
"""
from __future__ import annotations
import copy
import datetime
import itertools
import json
import os
from typing import Any, Dict, List, Optional
from .recorder import STORE, sha

_inc = itertools.count(47)  # first incident is #47, like the demo story


def _tools(run, name: str) -> List[Dict[str, Any]]:
    return [e for e in run["events"] if e["type"] == "tool_call" and e["tool"] == name]


def investigate(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Deterministic incident investigation. Returns analysis dict or None."""
    task, kind = run["task"], run["task"]["kind"]
    initial = {r["id"]: r for r in run["initial"].get("refunds", [])}

    if kind == "refund":
        for call in _tools(run, "issue_refund"):
            rid = call["args"]["refund_id"]
            prior = initial.get(rid, {}).get("status")
            if prior == "COMPLETED":
                good = next(r["id"] for r in run["initial"]["refunds"]
                            if r["status"] == task["requested_status"])
                amt = initial[rid]["amount_cents"] / 100
                return {"category": "WRONG_ENTITY_SELECTION",
                        "trigger": {"customer": task["customer"],
                                    "requested_status": task["requested_status"]},
                        "ambiguous_entities": sorted(initial),
                        "bad_selection": rid, "expected_selection": good,
                        "what_happened": f"Agent chose {rid} (already COMPLETED) instead of {good}",
                        "why_it_matters": f"Duplicate ${amt:.0f} payout to {task['customer']}",
                        "root_cause": "Policy matches by amount instead of status",
                        "violated_invariant": "refund.status must equal requested status",
                        "forbidden_action": f"issue_refund({rid})",
                        "invariant": {"check": "selected_initial_status",
                                      "requested": task["requested_status"]},
                        "expected": f"Select {good}.",
                        "actual": f"Selected {rid} (already COMPLETED) -> duplicate payout."}
        return None

    if kind == "address":
        mails = _tools(run, "send_email")
        if mails:
            tpl = mails[0]["args"].get("template", "")
            return {"category": "FORBIDDEN_SIDE_EFFECT",
                    "trigger": {"customer": task["customer"]},
                    "bad_selection": tpl, "expected_selection": "no email",
                    "what_happened": f"Agent sent promotional email '{tpl}' during address update",
                    "why_it_matters": "Customer only asked for address change; email is unauthorized",
                    "root_cause": "Agent is not constrained to the user's stated intent",
                    "violated_invariant": "address update must not send email",
                    "forbidden_action": "send_email(*)",
                    "invariant": {"check": "no_tool", "tool": "send_email"},
                    "expected": "UPDATE_ADDRESS only.",
                    "actual": f"Sent email '{tpl}'."}
        return None

    if kind == "cancel":
        orders0 = {o["id"]: o["status"] for o in run["initial"]["orders"]}
        orders1 = {o["id"]: o["status"] for o in run["final"]["orders"]}
        for oid, s0 in orders0.items():
            if s0 == "SHIPPED" and orders1.get(oid) == "CANCELLED":
                return {"category": "STATE_TRANSITION_VIOLATION",
                        "trigger": {"order_id": oid},
                        "bad_selection": f"cancel_order({oid})",
                        "expected_selection": "escalate to refund request",
                        "what_happened": f"Agent cancelled shipped order {oid}",
                        "why_it_matters": "Shipped orders cannot be cancelled; must go through refund",
                        "root_cause": "Agent does not check order status before acting",
                        "violated_invariant": "SHIPPED must never transition to CANCELLED",
                        "forbidden_action": f"cancel_order({oid})",
                        "invariant": {"check": "no_transition",
                                      "fro": "SHIPPED", "to": "CANCELLED"},
                        "expected": "SHIPPED -> REFUND_REQUEST.",
                        "actual": "SHIPPED -> CANCELLED."}
        return None

    return None


def _extract_signal(analysis: Dict[str, Any], run: Dict[str, Any]) -> str:
    """Extract what signal the agent used to make its decision."""
    cat = analysis["category"]
    if cat == "WRONG_ENTITY_SELECTION":
        initial = {r["id"]: r for r in run["initial"].get("refunds", [])}
        bad = initial.get(analysis.get("bad_selection", ""), {})
        return f"amount=${bad.get('amount_cents', 0) / 100:.0f} (matched by amount, ignored status)"
    if cat == "FORBIDDEN_SIDE_EFFECT":
        return "template=promotional (agent acted beyond stated intent)"
    if cat == "STATE_TRANSITION_VIOLATION":
        return "order exists (agent did not check status before cancel)"
    return "unknown"


def _extract_ignored(analysis: Dict[str, Any], run: Dict[str, Any]) -> str:
    """Extract what signal the agent should have used."""
    cat = analysis["category"]
    if cat == "WRONG_ENTITY_SELECTION":
        return f"status=PENDING (should have filtered to {analysis.get('expected_selection', 'n/a')})"
    if cat == "FORBIDDEN_SIDE_EFFECT":
        return "user_intent=address_update only (no email permitted)"
    if cat == "STATE_TRANSITION_VIOLATION":
        return "status=SHIPPED (cannot cancel, must refund)"
    return "unknown"


def freeze_incident(run: Dict[str, Any], analysis: Dict[str, Any],
                    prompt: str = "") -> Dict[str, Any]:
    """Freeze the exact world in which the incident occurred.

    The frozen artifact captures: world state + trajectory + agent context.
    So the incident can be reconstructed, replayed, and investigated later.
    Hash-verified so tampering is detected on reconstruction.
    """
    n = next(_inc)
    inc_id = f"inc_{n:03d}"

    diagnosis = {
        "expected": analysis["expected"],
        "actual": analysis["actual"],
        "expected_entity": analysis.get("expected_selection", "n/a"),
        "selected_entity": analysis.get("bad_selection", "n/a"),
        "decision_signal": _extract_signal(analysis, run),
        "ignored_signal": _extract_ignored(analysis, run),
        "failure_class": analysis["category"],
        "root_cause": analysis["root_cause"],
    }

    incident_record = {
        "incident_id": inc_id, "run_id": run["run_id"],
        "agent_version": run["agent_version"],
        "category": analysis["category"],
        "status": "OPEN",
        "what_happened": analysis["what_happened"],
        "why_it_matters": analysis["why_it_matters"],
        "root_cause": analysis["root_cause"],
        "violated_invariant": analysis["violated_invariant"],
        "diagnosis": diagnosis,
        "run_hash": run["hash"],
    }
    incident_record["incident_hash"] = sha(
        {k: incident_record[k] for k in
         ("run_id", "category", "what_happened", "why_it_matters",
          "root_cause", "violated_invariant", "run_hash")})

    world = {"state": copy.deepcopy(run["initial"]),
             "trajectory": copy.deepcopy(run["events"]),
             "agent_version": run["agent_version"],
             "task": run["task"], "prompt": prompt}

    fix_verification = {
        "expected_behavior": analysis["expected"],
        "forbidden": [analysis["forbidden_action"]],
        "invariant": analysis["invariant"],
        "reproduce_by": "Run same agent against reconstructed world"}

    frozen = {"incident_id": inc_id, "category": analysis["category"],
              "world": world,
              "incident": {"what_happened": analysis["what_happened"],
                           "why_it_matters": analysis["why_it_matters"],
                           "root_cause": analysis["root_cause"],
                           "violated_invariant": analysis["violated_invariant"],
                           "invariant": analysis["invariant"],
                           "diagnosis": diagnosis},
              "fix_verification": fix_verification,
              "source_run": run["run_id"], "source_hash": run["hash"]}
    frozen["freeze_hash"] = sha(
        {k: frozen[k] for k in ("world", "incident", "fix_verification")})

    os.makedirs(f"{STORE}/incidents", exist_ok=True)
    with open(f"{STORE}/incidents/{inc_id}.json", "w") as fh:
        json.dump(incident_record, fh, indent=2, default=str)

    os.makedirs(f"{STORE}/worlds", exist_ok=True)
    with open(f"{STORE}/worlds/{inc_id}.json", "w") as fh:
        json.dump(frozen, fh, indent=2, default=str)

    return frozen


def verify_world(frozen: Dict[str, Any]) -> bool:
    """Verify the frozen incident world hasn't been tampered with."""
    expect = frozen["freeze_hash"]
    return sha({k: frozen[k] for k in ("world", "incident", "fix_verification")}) == expect


def mark_resolved(incident_id: str) -> Dict[str, Any]:
    """Mark an incident as resolved in the incident record.

    This is the terminal state: the fix survived the incident that caused it.
    The incident record becomes the resolution evidence.
    """
    path = f"{STORE}/incidents/{incident_id}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Incident {incident_id} not found")
    with open(path) as fh:
        record = json.load(fh)
    record["status"] = "RESOLVED"
    record["resolved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2, default=str)
    return record


# backward aliases
detect = investigate
freeze = freeze_incident
verify_regression = verify_world
