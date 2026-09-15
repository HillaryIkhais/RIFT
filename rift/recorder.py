"""Immutable run recorder. Every execution becomes a sealed trajectory:
task + agent_version + initial snapshot + ordered events + final snapshot.
Hash covers all of it; replay refuses tampered evidence.
"""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
import os
from typing import Any, Dict, List

STORE = os.environ.get("RIFT_STORE", ".rift_store")
_ids = itertools.count(1)


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


class Recorder:
    def __init__(self, task: Dict[str, Any], agent_version: str, shop):
        self.run_id = f"run_{next(_ids):03d}"
        self.task = task
        self.agent_version = agent_version
        self.events: List[Dict[str, Any]] = []
        self.initial = shop.snapshot()

    def tool_call(self, tool: str, args: dict) -> None:
        self.events.append({"seq": len(self.events) + 1, "type": "tool_call",
                            "tool": tool, "args": args})

    def tool_result(self, tool: str, result: Any) -> None:
        self.events.append({"seq": len(self.events) + 1, "type": "tool_result",
                            "tool": tool, "result": result})

    def finish(self, shop, outcome: str) -> Dict[str, Any]:
        run = {"run_id": self.run_id, "task": self.task,
               "agent_version": self.agent_version, "initial": self.initial,
               "events": self.events, "final": shop.snapshot(), "outcome": outcome}
        run["hash"] = sha({k: run[k] for k in ("task", "agent_version", "initial", "events", "final")})
        os.makedirs(f"{STORE}/runs", exist_ok=True)
        with open(f"{STORE}/runs/{self.run_id}.json", "w") as fh:
            json.dump(run, fh, indent=2, default=str)
        return run


def verify_run(run: Dict[str, Any]) -> bool:
    expect = run["hash"]
    return sha({k: run[k] for k in ("task", "agent_version", "initial", "events", "final")}) == expect
