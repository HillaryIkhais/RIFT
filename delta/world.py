"""DELTA world: authoritative state + event log + snapshots + rollback.

Security boundary (stated precisely, per §14 of the plan):
DELTA guarantees effect accounting WITHIN the declared and observed execution
boundary. Writes to systems DELTA cannot observe force a non-commit verdict —
never assumed success.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class WorldEvent:
    seq: int
    event_type: str
    entity: str
    actor: str
    detail: str = ""


class World:
    def __init__(self):
        self.state: Dict[str, Dict[str, Any]] = {}
        self.events: List[WorldEvent] = []
        self.versions: Dict[str, int] = {}          # per-entity write counter
        self.ext_versions: Dict[str, int] = {}      # moves by non-agent actors only
        self.committed_ops: set = set()             # operation_ids already committed
        self.unobserved_writes: int = 0             # touches outside the boundary
        self._seq = 0
        self.concurrent_touched: set = set()  # (entity, field) written by non-agent actors

    def _bump(self, entity: str) -> int:
        self.versions[entity] = self.versions.get(entity, 0) + 1
        return self.versions[entity]

    def set(self, entity: str, f: str, v: Any, actor: str = "agent",
            event: str = "", external: bool = False) -> None:
        self.state.setdefault(entity, {})[f] = v
        self._bump(entity)
        self._seq += 1
        if event:
            self.events.append(WorldEvent(self._seq, event, entity, actor, f"{f}={v!r}"))
        if external:
            self.concurrent_touched.add((entity, f))
            self.ext_versions[entity] = self.ext_versions.get(entity, 0) + 1

    def create(self, entity: str, fields: Dict[str, Any], actor: str = "agent",
               event: str = "", external: bool = False) -> None:
        self.state[entity] = dict(fields)
        self._bump(entity)
        self._seq += 1
        if event:
            self.events.append(WorldEvent(self._seq, event, entity, actor, "CREATE"))
        if external:
            for fld in fields:
                self.concurrent_touched.add((entity, fld))
            self.ext_versions[entity] = self.ext_versions.get(entity, 0) + 1

    def write_unobserved(self, system: str, detail: str = "") -> None:
        """Record a mutation DELTA cannot observe. Fails closed at verdict time."""
        self.unobserved_writes += 1
        self._seq += 1
        self.events.append(WorldEvent(self._seq, "unobserved.write", system,
                                      "unknown", detail))

    def snapshot_all(self) -> Dict[str, Dict[str, Any]]:
        return copy.deepcopy(self.state)

    def rollback(self, snap: Dict[str, Dict[str, Any]]) -> None:
        self.state = copy.deepcopy(snap)

    def compensate(self, entity: str, f: str, value: Any, actor: str = "delta") -> None:
        self.set(entity, f, value, actor=actor, event="compensate")
