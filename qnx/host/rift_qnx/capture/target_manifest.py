"""Target manifest: records the frozen QNX runtime environment for an incident.

This is the "target information" section of the frozen QNX incident bundle.
It records OS version, architecture, QEMU version/launch args, image and
binary hashes, and resource-manager configuration — all sourced from the
actual target, never fabricated.
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


class TargetManifest:
    def __init__(
        self,
        qnx_version: str,
        target_arch: str,
        qemu_version: str,
        qemu_args: List[str],
        target_image_id: str,
        target_image_hash: str,
        instrumented_kernel_id: str,
        resource_manager: Dict[str, Any],
        workload: Dict[str, Any],
        trace_capture: Dict[str, Any],
    ):
        self.qnx_version = qnx_version
        self.target_arch = target_arch
        self.qemu_version = qemu_version
        self.qemu_args = list(qemu_args)
        self.target_image_id = target_image_id
        self.target_image_hash = target_image_hash
        self.instrumented_kernel_id = instrumented_kernel_id
        self.resource_manager = dict(resource_manager)
        self.workload = dict(workload)
        self.trace_capture = dict(trace_capture)
        self.captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "qnx_version": self.qnx_version,
            "target_arch": self.target_arch,
            "qemu_version": self.qemu_version,
            "qemu_args": self.qemu_args,
            "target_image_id": self.target_image_id,
            "target_image_hash": self.target_image_hash,
            "instrumented_kernel_id": self.instrumented_kernel_id,
            "captured_at": self.captured_at,
            "resource_manager": self.resource_manager,
            "workload": self.workload,
            "trace_capture": self.trace_capture,
        }

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "TargetManifest":
        with open(path) as fh:
            data = json.load(fh)
        return cls(
            qnx_version=data["qnx_version"],
            target_arch=data["target_arch"],
            qemu_version=data["qemu_version"],
            qemu_args=data["qemu_args"],
            target_image_id=data["target_image_id"],
            target_image_hash=data["target_image_hash"],
            instrumented_kernel_id=data["instrumented_kernel_id"],
            resource_manager=data["resource_manager"],
            workload=data["workload"],
            trace_capture=data["trace_capture"],
        )


def build_manifest(
    qnx_version: str,
    target_arch: str,
    qemu_version: str,
    qemu_args: List[str],
    target_image_path: str,
    instrumented_kernel_id: str,
    rm_process_name: str,
    rm_pid: int,
    worker_tids: List[int],
    pool_config: Dict[str, int],
    handler_mode: str,
    workload: Dict[str, Any],
    trace_config: Dict[str, Any],
) -> TargetManifest:
    return TargetManifest(
        qnx_version=qnx_version,
        target_arch=target_arch,
        qemu_version=qemu_version,
        qemu_args=list(qemu_args),
        target_image_id=os.path.basename(target_image_path),
        target_image_hash=_sha_file(target_image_path) if os.path.exists(target_image_path) else "",
        instrumented_kernel_id=instrumented_kernel_id,
        resource_manager={
            "process_name": rm_process_name,
            "pid": rm_pid,
            "worker_tids": list(worker_tids),
            "lo_water": pool_config.get("lo_water"),
            "increment": pool_config.get("increment"),
            "hi_water": pool_config.get("hi_water"),
            "maximum": pool_config.get("maximum"),
            "handler_mode": handler_mode,
        },
        workload=dict(workload),
        trace_capture=dict(trace_config),
    )
