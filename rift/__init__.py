"""RIFT — incident reconstruction for AI agents.

When an AI agent breaks in the real world, RIFT reconstructs the exact world
it saw so the failure can be reproduced, investigated, and fixed.

Loop: FAIL -> CAPTURE -> FREEZE -> REPRODUCE -> DIAGNOSE -> FIX -> VERIFY -> RESOLVE
"""
from .sim import Shop, seed_sarah, seed_address, seed_cancel
from .agent import V10, V11
from .recorder import Recorder, verify_run
from .miner import investigate, freeze_incident, verify_world, mark_resolved, detect, freeze, verify_regression
from .engine import replay_incident, verify_fix, export_incident, resolve_incident, release_gate, export_evidence_md, replay, gate
from .llm import llm_policy, make_client, FakeClient, PROMPTS

__all__ = ["Shop", "seed_sarah", "seed_address", "seed_cancel", "V10", "V11",
           "Recorder", "verify_run", "investigate", "freeze_incident", "verify_world",
           "mark_resolved", "replay_incident", "verify_fix", "export_incident",
           "resolve_incident", "detect", "freeze", "verify_regression", "replay", "gate",
           "llm_policy", "make_client", "FakeClient", "PROMPTS"]
