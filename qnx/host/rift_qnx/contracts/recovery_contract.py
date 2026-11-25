"""Recovery contract: real QNX test metadata generated before a candidate fix is tested.

The contract is deterministic test metadata, not an LLM decision. It records
the incident, baseline binary/config, proposed change, preconditions, expected
invariants, rollback plan, and approval gate.

No consequential change is automatically approved. The contract must be tested
in a disposable QEMU environment; a live physical QNX device is never altered.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from typing import Any, Dict, List, Optional


def _sha_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class RecoveryContract:
    def __init__(
        self,
        incident_id: str,
        target_image_hash: str,
        baseline_binary_hash: str,
        baseline_pool_configuration: Dict[str, int],
        proposed_change: Dict[str, str],
        preconditions: List[str],
        expected_invariants: List[str],
        rollback: Dict[str, bool],
        approval_required: bool = True,
        target_os: str = "QNX SDP 8.0",
        target_arch: str = "x86_64",
        environment: str = "QEMU",
    ):
        self.incident_id = incident_id
        self.target_os = target_os
        self.target_arch = target_arch
        self.environment = environment
        self.target_image_hash = target_image_hash
        self.baseline_binary_hash = baseline_binary_hash
        self.baseline_pool_configuration = dict(baseline_pool_configuration)
        self.proposed_change = dict(proposed_change)
        self.preconditions = list(preconditions)
        self.expected_invariants = list(expected_invariants)
        self.rollback = dict(rollback)
        self.approval_required = bool(approval_required)
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.contract_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "target_os": self.target_os,
            "target_arch": self.target_arch,
            "environment": self.environment,
            "target_image_hash": self.target_image_hash,
            "baseline_binary_hash": self.baseline_binary_hash,
            "baseline_pool_configuration": self.baseline_pool_configuration,
            "proposed_change": self.proposed_change,
            "preconditions": self.preconditions,
            "expected_invariants": self.expected_invariants,
            "rollback": self.rollback,
            "approval_required": self.approval_required,
            "created_at": self.created_at,
            "contract_hash": self.contract_hash,
        }

    def seal(self) -> str:
        """Compute and store the manifest hash over contract fields."""
        payload = {
            k: self.to_dict()[k]
            for k in (
                "incident_id", "target_os", "target_arch", "environment",
                "target_image_hash", "baseline_binary_hash",
                "baseline_pool_configuration", "proposed_change",
                "preconditions", "expected_invariants", "rollback",
                "approval_required", "created_at",
            )
        }
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.contract_hash = hashlib.sha256(canon.encode()).hexdigest()
        return self.contract_hash

    def save(self, path: str) -> str:
        self.seal()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2, default=str)
        return self.contract_hash

    @classmethod
    def load(cls, path: str) -> "RecoveryContract":
        with open(path) as fh:
            data = json.load(fh)
        obj = cls(
            incident_id=data["incident_id"],
            target_image_hash=data["target_image_hash"],
            baseline_binary_hash=data["baseline_binary_hash"],
            baseline_pool_configuration=data["baseline_pool_configuration"],
            proposed_change=data["proposed_change"],
            preconditions=data["preconditions"],
            expected_invariants=data["expected_invariants"],
            rollback=data["rollback"],
            approval_required=data.get("approval_required", True),
            target_os=data.get("target_os", "QNX SDP 8.0"),
            target_arch=data.get("target_arch", "x86_64"),
            environment=data.get("environment", "QEMU"),
        )
        obj.created_at = data.get("created_at", obj.created_at)
        obj.contract_hash = data.get("contract_hash")
        return obj

    def verify_integrity(self) -> bool:
        """Recompute the contract hash and compare to the sealed value."""
        current = self.seal()
        return self.contract_hash is not None and current == self.contract_hash


def build_contract_from_incident(
    incident_id: str,
    incident_dir: str,
    target_image_path: str,
    baseline_binary_path: str,
    pool_configuration: Dict[str, int],
    proposed_change_type: str,
    proposed_description: str,
    expected_invariants: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> RecoveryContract:
    """Convenience: build a RecoveryContract from an incident bundle directory."""
    if expected_invariants is None:
        expected_invariants = [
            "receive reserve remains at least 1 during active load",
            "no corresponding client SEND-blocking violation",
            "client completion latency remains within budget",
        ]

    contract = RecoveryContract(
        incident_id=incident_id,
        target_image_hash=_sha_file(target_image_path) if os.path.exists(target_image_path) else "",
        baseline_binary_hash=_sha_file(baseline_binary_path) if os.path.exists(baseline_binary_path) else "",
        baseline_pool_configuration=pool_configuration,
        proposed_change={
            "type": proposed_change_type,
            "description": proposed_description,
        },
        preconditions=[
            "QNX 8.0 target boots",
            "Baseline workload reproduces the incident",
            "Original binary is preserved",
        ],
        expected_invariants=expected_invariants,
        rollback={
            "restore_baseline_binary": True,
            "restore_baseline_configuration": True,
            "restart_test_resource_manager": True,
        },
        approval_required=True,
    )
    if output_path:
        contract.save(output_path)
    return contract
