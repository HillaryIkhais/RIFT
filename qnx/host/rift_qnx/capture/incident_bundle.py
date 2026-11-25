"""Frozen QNX incident bundle assembly.

A frozen incident contains the target manifest, raw + normalized trace,
measured results, and a manifest hash over all artifact hashes. The original
raw .kev trace is always retained; normalized output is an additional
representation, not a replacement.

Replay/verification refuses to run if required files are missing or integrity
checks fail.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import shutil
from typing import Any, Dict, List, Optional

from ..adapters.traceprinter import parse_traceprinter, TraceprinterParseError
from .target_manifest import TargetManifest


def _sha_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class IncidentBundle:
    """A frozen QNX incident, on disk under an incident directory."""

    REQUIRED_ARTIFACTS = ("manifest.json", "trace.kev")

    def __init__(self, incident_id: str, bundle_dir: str):
        self.incident_id = incident_id
        self.bundle_dir = bundle_dir
        self.manifest: Optional[TargetManifest] = None
        self.trace_raw_path: Optional[str] = None
        self.trace_normalized_path: Optional[str] = None
        self.measured_results: Dict[str, Any] = {}
        self.diagnosis: Dict[str, Any] = {}
        self.manifest_hash: Optional[str] = None
        self.created_at: Optional[str] = None

    # ---- paths ----
    def _path(self, name: str) -> str:
        return os.path.join(self.bundle_dir, name)

    def manifest_path(self) -> str:
        return self._path("manifest.json")

    # ---- assembly ----
    def set_manifest(self, manifest: TargetManifest) -> None:
        self.manifest = manifest

    def add_trace_raw(self, src_path: str) -> str:
        """Copy the raw .kev trace into the bundle and record its hash."""
        os.makedirs(self.bundle_dir, exist_ok=True)
        dst = self._path("trace.kev")
        shutil.copyfile(src_path, dst)
        self.trace_raw_path = dst
        return dst

    def add_trace_normalized(self, traceprinter_text: str, src_label: str = "") -> str:
        """Write normalized traceprinter output into the bundle."""
        os.makedirs(self.bundle_dir, exist_ok=True)
        dst = self._path("trace.traceprinter.txt")
        with open(dst, "w") as fh:
            fh.write(traceprinter_text)
        self.trace_normalized_path = dst
        return dst

    def parse_normalized_trace(self) -> Any:
        """Parse the bundled normalized trace (returns NormalizedTrace)."""
        if not self.trace_normalized_path or not os.path.exists(self.trace_normalized_path):
            raise FileNotFoundError("normalized trace not present in bundle")
        with open(self.trace_normalized_path) as fh:
            text = fh.read()
        return parse_traceprinter(text, source_file=self.trace_normalized_path)

    def set_measured_results(self, results: Dict[str, Any]) -> None:
        self.measured_results = dict(results)

    def set_diagnosis(self, diagnosis: Dict[str, Any]) -> None:
        self.diagnosis = dict(diagnosis)

    def seal(self) -> str:
        """Compute manifest hash over incident metadata and artifact hashes."""
        artifacts: Dict[str, str] = {}
        for name in ("trace.kev", "trace.traceprinter.txt", "manifest.json"):
            p = self._path(name)
            artifacts[name] = _sha_file(p) if os.path.exists(p) else ""

        payload = {
            "incident_id": self.incident_id,
            "created_at": self.created_at,
            "manifest": self.manifest.to_dict() if self.manifest else {},
            "artifacts": artifacts,
            "measured_results": self.measured_results,
            "diagnosis": self.diagnosis,
        }
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.manifest_hash = hashlib.sha256(canon.encode()).hexdigest()
        return self.manifest_hash

    def save(self) -> str:
        """Persist manifest + seal. Returns manifest hash."""
        os.makedirs(self.bundle_dir, exist_ok=True)
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if self.manifest:
            self.manifest.save(self.manifest_path())
        self.measured_results_path = self._path("measured_results.json")
        with open(self.measured_results_path, "w") as fh:
            json.dump(self.measured_results, fh, indent=2, default=str)
        self.diagnosis_path = self._path("diagnosis.json")
        with open(self.diagnosis_path, "w") as fh:
            json.dump(self.diagnosis, fh, indent=2, default=str)
        h = self.seal()
        # Persist the seal itself.
        with open(self._path("seal.json"), "w") as fh:
            json.dump({"incident_id": self.incident_id, "manifest_hash": h, "sealed_at": self.created_at}, fh, indent=2)
        return h

    # ---- integrity verification ----
    def verify_integrity(self) -> List[str]:
        """Return list of integrity problems (empty = OK)."""
        problems: List[str] = []
        for name in self.REQUIRED_ARTIFACTS:
            if not os.path.exists(self._path(name)):
                problems.append(f"missing required artifact: {name}")
        if self.trace_raw_path and not os.path.exists(self.trace_raw_path):
            problems.append("missing raw trace file")
        seal_path = self._path("seal.json")
        if os.path.exists(seal_path):
            with open(seal_path) as fh:
                seal = json.load(fh)
            stored = seal.get("manifest_hash")
            # Recompute current hash of artifacts + manifest.
            artifacts = {}
            for name in ("trace.kev", "trace.traceprinter.txt", "manifest.json"):
                p = self._path(name)
                artifacts[name] = _sha_file(p) if os.path.exists(p) else ""
            payload = {
                "incident_id": self.incident_id,
                "created_at": self.created_at,
                "manifest": self.manifest.to_dict() if self.manifest else {},
                "artifacts": artifacts,
                "measured_results": self.measured_results,
                "diagnosis": self.diagnosis,
            }
            canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            current = hashlib.sha256(canon.encode()).hexdigest()
            if stored != current:
                problems.append("manifest hash mismatch — evidence tampered")
        else:
            problems.append("missing seal.json — bundle not sealed")
        return problems

    def refuse_unless_intact(self) -> None:
        """Raise if the bundle is not intact; replay/verification must not proceed."""
        problems = self.verify_integrity()
        if problems:
            raise ValueError(
                f"Incident {self.incident_id} failed integrity check: " + "; ".join(problems)
            )


def freeze_incident(
    incident_id: str,
    bundle_dir: str,
    manifest: TargetManifest,
    raw_trace_path: str,
    traceprinter_text: str,
    measured_results: Dict[str, Any],
    diagnosis: Dict[str, Any],
) -> IncidentBundle:
    """Convenience: assemble, seal, and persist a frozen QNX incident bundle."""
    bundle = IncidentBundle(incident_id, bundle_dir)
    bundle.set_manifest(manifest)
    bundle.add_trace_raw(raw_trace_path)
    bundle.add_trace_normalized(traceprinter_text)
    bundle.set_measured_results(measured_results)
    bundle.set_diagnosis(diagnosis)
    bundle.save()
    return bundle
