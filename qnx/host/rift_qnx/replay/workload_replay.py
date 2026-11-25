"""Workload replay: re-execute the same controlled client workload against a
QNX target (baseline or corrected build) and capture a fresh trace for
comparison against the frozen incident.

Used by both the baseline reproduction check and the candidate fix verification.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, Optional


class WorkloadReplay:
    def __init__(
        self,
        qnxrun_binary: str = "qnxrun",
        target_binary: str = "",
        client_binary: str = "",
        target_ip: str = "127.0.0.1",
        workdir: str = ".rift_qnx_workload",
    ):
        self.qnxrun_binary = qnxrun_binary
        self.target_binary = target_binary
        self.client_binary = client_binary
        self.target_ip = target_ip
        self.workdir = workdir

    def available(self) -> bool:
        return shutil.which(self.qnxrun_binary) is not None

    def run_baseline(
        self,
        pool_config: Dict[str, int],
        workload_cfg: Dict[str, int],
        trace_out: Optional[str] = None,
        timeout_s: int = 300,
    ) -> Dict[str, Any]:
        """Run the baseline (blocking-handler) resource manager + workload."""
        return self._run(target_binary=self.target_binary, pool_config=pool_config,
                         workload_cfg=workload_cfg, trace_out=trace_out,
                         timeout_s=timeout_s, mode="blocking")

    def run_corrected(
        self,
        pool_config: Dict[str, int],
        workload_cfg: Dict[str, int],
        trace_out: Optional[str] = None,
        timeout_s: int = 300,
    ) -> Dict[str, Any]:
        """Run the corrected (deferred-reply) resource manager + workload."""
        return self._run(target_binary=self.target_binary, pool_config=pool_config,
                         workload_cfg=workload_cfg, trace_out=trace_out,
                         timeout_s=timeout_s, mode="deferred")

    def _run(
        self,
        target_binary: str,
        pool_config: Dict[str, int],
        workload_cfg: Dict[str, int],
        trace_out: Optional[str],
        mode: str,
        timeout_s: int,
    ) -> Dict[str, Any]:
        os.makedirs(self.workdir, exist_ok=True)
        result: Dict[str, Any] = {
            "mode": mode,
            "ran": False,
            "exit_code": None,
            "output": "",
            "error": None,
            "trace_out": trace_out,
        }

        if not self.available():
            result["error"] = "qnxrun not found on host (QNX dev host required)"
            return result

        # Build the resource-manager command line overrides.
        rm_args = [
            target_binary,
            "-m", "1" if mode == "deferred" else "0",
            "-l", str(pool_config.get("lo_water", 1)),
            "-i", str(pool_config.get("increment", 1)),
            "-h", str(pool_config.get("hi_water", 4)),
            "-x", str(pool_config.get("maximum", 4)),
        ]

        try:
            # Start resource manager on the target.
            rm_proc = subprocess.run(
                [self.qnxrun_binary, "-t", "ntox86"] + rm_args,
                capture_output=True, text=True, timeout=timeout_s,
            )
            result["exit_code"] = rm_proc.returncode
            result["output"] = rm_proc.stdout
            if rm_proc.stderr:
                result["output"] += "\n--- RM STDERR ---\n" + rm_proc.stderr
            result["ran"] = True

            # Then run the concurrent client workload.
            client_args = [
                self.client_binary,
                "-n", str(workload_cfg.get("requests_per_client", 40)),
                "-l", str(workload_cfg.get("op_len", 256)),
                "-b", str(workload_cfg.get("response_budget_ns", 100000000)),
            ]
            cl_proc = subprocess.run(
                [self.qnxrun_binary, "-t", "ntox86"] + client_args,
                capture_output=True, text=True, timeout=timeout_s,
            )
            result["client_exit_code"] = cl_proc.returncode
            result["client_output"] = cl_proc.stdout
        except subprocess.TimeoutExpired as exc:
            result["error"] = f"workload replay timed out after {timeout_s}s"
        except Exception as exc:  # pragma: no cover
            result["error"] = str(exc)

        return result
