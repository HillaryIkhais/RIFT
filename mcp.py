"""DELTA MCP surface (tool schemas for agent runtimes).

Tools: delta_execute | delta_inspect | delta_explain | delta_replay | delta_compensate
These wrap delta.execute / inspect_exec / explain_exec / replay_exec; the verdict
path stays deterministic — the model proposes contracts, the runtime disposes.
"""
from __future__ import annotations
from typing import Any, Dict

TOOLS = [
    {"name": "delta_execute",
     "description": "Run an agent inside the side-effect firewall. Commits only if "
                    "every observed mutation is accounted for by the effect contract.",
     "input": {"intent": "str", "contract": "EffectContract JSON", "operation_id": "str?"}},
    {"name": "delta_inspect",
     "description": "Show verdict + evidence for a stored execution.",
     "input": {"execution_id": "str"}},
    {"name": "delta_explain",
     "description": "Explain why an execution got its verdict, mutation by mutation.",
     "input": {"execution_id": "str"}},
    {"name": "delta_replay",
     "description": "Re-verify a stored receipt; fails if any event was modified.",
     "input": {"execution_id": "str"}},
    {"name": "delta_compensate",
     "description": "Restore auto-recoverable violations and re-verify. "
                    "Non-recoverable violations go to human hold.",
     "input": {"execution_id": "str"}},
]


def dispatch(name: str, args: Dict[str, Any]) -> str:
    from delta import explain_exec, inspect_exec, replay_exec
    if name == "delta_inspect":
        return inspect_exec(args["execution_id"])
    if name == "delta_explain":
        return explain_exec(args["execution_id"])
    if name == "delta_replay":
        ev = replay_exec(args["execution_id"])
        return f"REPLAY -> {ev.verdict.value}"
    if name in ("delta_execute", "delta_compensate"):
        return ("Use delta.execute(world, contract, agent_fn) in-process; "
                "the runtime owns commit, never the model.")
    raise KeyError(f"unknown tool {name}")
