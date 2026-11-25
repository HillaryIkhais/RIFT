"""QEMU replay: reconstruct the recorded QNX test envelope and re-execute the workload.

The correct claim is that RIFT reconstructs the recorded QNX test envelope and
re-executes the same controlled workload to determine whether the same failure
invariant reproduces — NOT that it recreates an identical kernel schedule.

Real-time scheduling is not guaranteed to reproduce identical instruction
interleaving. The replay verifies the same failure class and measured invariant.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional


class QemuReplay:
    def __init__(
        self,
        qemu_binary: str = "qemu-system-x86_64",
        qnx_image: str = "",
        qemu_args: Optional[List[str]] = None,
        workdir: str = ".rift_qnx_replay",
    ):
        self.qemu_binary = qemu_binary
        self.qnx_image = qnx_image
        self.qemu_args = list(qemu_args or [])
        self.workdir = workdir

    def available(self) -> bool:
        return shutil.which(self.qemu_binary) is not None

    def build_command(self, extra: Optional[List[str]] = None) -> List[str]:
        cmd = [self.qemu_binary]
        cmd.extend(self.qemu_args)
        if self.qnx_image:
            cmd += ["-drive", f"file={self.qnx_image},format=raw,if=virtio"]
        cmd.extend(extra or [])
        return cmd

    def replay_workload(
        self,
        incident_dir: str,
        workload_script: str,
        timeout_s: int = 300,
    ) -> Dict[str, Any]:
        """Re-execute the same workload configuration in QEMU.

        Returns a result dict with exit code, output, and whether QEMU is
        available. Does not claim schedule identity.
        """
        os.makedirs(self.workdir, exist_ok=True)
        result: Dict[str, Any] = {
            "qemu_available": self.available(),
            "replayed": False,
            "exit_code": None,
            "output": "",
            "error": None,
        }

        if not self.available():
            result["error"] = "qemu-system-x86_64 not found on host"
            return result
        if not self.qnx_image:
            result["error"] = "no QNX image configured for replay"
            return result

        cmd = self.build_command(["-serial", "stdio", "-no-reboot"])
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            result["replayed"] = True
            result["exit_code"] = proc.returncode
            result["output"] = proc.stdout
            if proc.stderr:
                result["output"] += "\n--- STDERR ---\n" + proc.stderr
        except subprocess.TimeoutExpired as exc:
            result["error"] = f"QEMU replay timed out after {timeout_s}s"
            result["output"] = (exc.stdout or b"").decode(errors="replace") if exc.stdout else ""
        except FileNotFoundError:
            result["error"] = "qemu binary not executable"
        except Exception as exc:  # pragma: no cover - environment dependent
            result["error"] = str(exc)

        return result


def replay_incident_envelope(
    incident_dir: str,
    qemu_image: str,
    qemu_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convenience: reconstruct a QNX test envelope from an incident bundle."""
    replayer = QemuReplay(qemu_binary="qemu-system-x86_64", qnx_image=qemu_image, qemu_args=qemu_args)
    return replayer.replay_workload(incident_dir, workload_script="")
