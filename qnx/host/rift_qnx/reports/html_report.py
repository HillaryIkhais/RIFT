"""Interactive HTML incident report for RIFT-QNX.

Generates a polished, local, per-incident report: overview, trace evidence
timeline (implicated threads only), root-cause panel, before-and-after view,
and evidence receipt with hashes.
"""
from __future__ import annotations

import html as html_mod
import json
import os
from typing import Any, Dict, List, Optional

C = {
    "bg": "#F5F5F0", "fg": "#1A1A1A", "border": "#1A1A1A",
    "muted": "#666666", "accent": "#D64040", "accent2": "#2D8A4E",
    "surface": "#FFFFFF", "surface2": "#EAEAE2",
    "warn": "#E8A838",
}


def _css() -> str:
    A, A2, B = C["accent"], C["accent2"], C["border"]
    BG, FG, MU = C["bg"], C["fg"], C["muted"]
    S, S2 = C["surface"], C["surface2"]
    W = C["warn"]
    return (
        "*{margin:0;padding:0;box-sizing:border-box}"
        "html{scroll-behavior:smooth}"
        f"body{{font-family:'Inter',system-ui,sans-serif;background:{BG};color:{FG};-webkit-font-smoothing:antialiased}}"
        f"::selection{{background:{A};color:#fff}}"
        f".topbar{{display:flex;justify-content:space-between;align-items:center;padding:16px 40px;border-bottom:3px solid {B};background:{S};position:sticky;top:0;z-index:20}}"
        f".logo{{font-size:20px;font-weight:900;letter-spacing:-1px;text-decoration:none;color:{FG}}}"
        f".logo span{{color:{A}}}"
        f".nav a{{padding:8px 14px;border:2px solid {B};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;text-decoration:none;color:{FG};margin-left:6px}}"
        f".nav a:hover{{background:{S2}}}"
        f".hero{{padding:48px 40px;background:{S};border-bottom:3px solid {B}}}"
        f".hero h1{{font-size:34px;font-weight:900;letter-spacing:-0.5px;margin-bottom:8px}}"
        f".hero .tag{{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:2px;color:{A};margin-top:10px}}"
        f".hero p{{font-size:15px;color:{MU};margin-top:10px;max-width:700px}}"
        ".grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 40px}}"
        f".card{{border:3px solid {B};box-shadow:5px 5px 0 {B};background:{S};padding:22px}}"
        f".card h3{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;color:{MU}}}"
        f".card .v{{font-size:20px;font-weight:700}}"
        f".card .small{{font-size:12px;color:{MU};margin-top:4px}}"
        f".section{{margin:0 40px 30px}}"
        f".sec-label{{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:3px;color:{MU};margin-bottom:6px}}"
        f".section h2{{font-size:26px;font-weight:900;margin-bottom:12px}}"
        f".section h2 em{{font-style:normal;color:{A}}}"
        f".panel{{border:3px solid {B};box-shadow:6px 6px 0 {B};background:{S};margin-bottom:16px}}"
        f".p-head{{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:3px solid {B}}}"
        f".p-head h3{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:2px}}"
        f".p-badge{{padding:4px 12px;border:2px solid;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1px}}"
        f".p-badge.ok{{background:{A2};color:#fff;border-color:{A2}}}"
        f".p-badge.err{{background:{A};color:#fff;border-color:{A}}}"
        f".p-badge.info{{background:{FG};color:#fff;border-color:{FG}}}"
        f".p-badge.warn{{background:{W};color:#1a1a1a;border-color:{W}}}"
        f".p-body{{padding:18px 20px}}"
        f".kv{{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid {S2}}}"
        f".kv:last-child{{border-bottom:none}}"
        f".kv .k{{font-size:11px;font-weight:700;color:{MU};text-transform:uppercase;letter-spacing:1px}}"
        f".kv .v{{font-size:12px;font-weight:600;text-align:right;max-width:60%;word-break:break-all}}"
        ".timeline{{position:relative;padding:20px 0}}"
        ".timeline::after{{content:'';position:absolute;left:28px;top:0;bottom:0;width:2px;background:#ccc}}"
        f".t-event{{position:relative;padding-left:60px;margin-bottom:22px}}"
        f".t-dot{{position:absolute;left:22px;top:2px;width:12px;height:12px;border-radius:50%;border:3px solid {B};background:{S}}}"
        f".t-time{{position:absolute;left:-10px;top:0;font-size:10px;font-weight:700;color:{MU};font-family:'JetBrains Mono',monospace}}"
        f".t-body{{font-size:12px;line-height:1.5}}"
        f".t-label{{font-weight:700;text-transform:uppercase;letter-spacing:0.5px;font-size:10px;color:{A}}}"
        ".hashbox{{display:flex;align-items:center;gap:10px;padding:10px 14px;border:2px solid "+B+";background:"+S2+";margin-top:10px}}"
        ".hashbox .hl{{font-size:8px;font-weight:800;text-transform:uppercase;color:"+MU+";width:140px}}"
        ".hashbox .hv{{font-family:'JetBrains Mono',monospace;font-size:10px;flex:1;word-break:break-all}}"
        ".notice{{border-left:4px solid "+W+";background:"+S2+";padding:12px 16px;margin:16px 0;font-size:12px;color:{FG}}}"
        ".footer{{margin:40px;padding:24px;border-top:3px solid "+B+";background:"+S+";font-size:11px;color:"+MU+";}}"
    )


def _badge(status: str) -> str:
    if status in ("PASS", "FIX_VERIFIED"):
        cls, txt = "ok", "PASS"
    elif status in ("FAIL", "NO_VERIFIED_FIX", "VIOLATION"):
        cls, txt = "err", "FAIL"
    elif status == "INSUFFICIENT_TRACE":
        cls, txt = "warn", "INSUFFICIENT"
    else:
        cls, txt = "info", status
    return f'<span class="p-badge {cls}">{txt}</span>'


def build_report(
    incident_id: str,
    manifest: Dict[str, Any],
    diagnosis: Dict[str, Any],
    measured: Dict[str, Any],
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    seal_hash: Optional[str] = None,
) -> str:
    """Return a complete HTML document string for one incident."""

    rm = manifest.get("resource_manager", {})
    workload = manifest.get("workload", {})
    trace_cap = manifest.get("trace_capture", {})

    esc = html_mod.escape

    # ---- Overview cards ----
    overview = (
        f'<div class="grid3">'
        f'<div class="card"><h3>Incident ID</h3><div class="v">{esc(incident_id)}</div>'
        f'<div class="small">QNX SDP 8.0 &middot; x86_64 QEMU</div></div>'
        f'<div class="card"><h3>Failure Classification</h3><div class="v">{esc(diagnosis.get("classification","INSUFFICIENT_TRACE"))}</div>'
        f'<div class="small">{_badge(diagnosis.get("classification","INSUFFICIENT_TRACE"))}</div></div>'
        f'<div class="card"><h3>Verification Status</h3><div class="v">{esc(verification.get("verdict","—") if verification else "—")}</div>'
        f'<div class="small">{_badge(verification.get("verdict","—") if verification else "—")}</div></div>'
        f'</div>'
    )

    # ---- Target info panel ----
    target_panel = (
        '<div class="panel"><div class="p-head"><h3>Target &amp; Environment</h3>'
        f'{_badge("trace")}</div><div class="p-body">'
        f'<div class="kv"><span class="k">QNX version</span><span class="v">{esc(manifest.get("qnx_version",""))}</span></div>'
        f'<div class="kv"><span class="k">Architecture</span><span class="v">{esc(manifest.get("target_arch",""))}</span></div>'
        f'<div class="kv"><span class="k">QEMU version</span><span class="v">{esc(manifest.get("qemu_version",""))}</span></div>'
        f'<div class="kv"><span class="k">Target image hash</span><span class="v">{esc(manifest.get("target_image_hash",""))[:16]}…</span></div>'
        f'<div class="kv"><span class="k">Kernel</span><span class="v">{esc(manifest.get("instrumented_kernel_id",""))}</span></div>'
        f'<div class="kv"><span class="k">Captured</span><span class="v">{esc(manifest.get("captured_at",""))}</span></div>'
        f'</div></div>'
    )

    # ---- Resource manager config panel ----
    rm_panel = (
        '<div class="panel"><div class="p-head"><h3>Resource Manager Configuration</h3>'
        f'{_badge("config")}</div><div class="p-body">'
        f'<div class="kv"><span class="k">Process</span><span class="v">{esc(rm.get("process_name",""))}</span></div>'
        f'<div class="kv"><span class="k">PID</span><span class="v">{esc(str(rm.get("pid","")))}</span></div>'
        f'<div class="kv"><span class="k">Worker TIDs</span><span class="v">{esc(", ".join(str(t) for t in rm.get("worker_tids",[])))}</span></div>'
        f'<div class="kv"><span class="k">lo_water</span><span class="v">{esc(str(rm.get("lo_water","")))}</span></div>'
        f'<div class="kv"><span class="k">increment</span><span class="v">{esc(str(rm.get("increment","")))}</span></div>'
        f'<div class="kv"><span class="k">hi_water</span><span class="v">{esc(str(rm.get("hi_water","")))}</span></div>'
        f'<div class="kv"><span class="k">maximum</span><span class="v">{esc(str(rm.get("maximum","")))}</span></div>'
        f'<div class="kv"><span class="k">Handler mode</span><span class="v">{esc(rm.get("handler_mode",""))}</span></div>'
        f'</div></div>'
    )

    # ---- Workload panel ----
    wl_panel = (
        '<div class="panel"><div class="p-head"><h3>Workload</h3>'
        f'{_badge("load")}</div><div class="p-body">'
        f'<div class="kv"><span class="k">Scenario</span><span class="v">{esc(workload.get("scenario_id",""))}</span></div>'
        f'<div class="kv"><span class="k">Clients</span><span class="v">{esc(str(workload.get("clients","")))}</span></div>'
        f'<div class="kv"><span class="k">Requests/client</span><span class="v">{esc(str(workload.get("requests_per_client","")))}</span></div>'
        f'<div class="kv"><span class="k">Concurrency</span><span class="v">{esc(str(workload.get("concurrency","")))}</span></div>'
        f'<div class="kv"><span class="k">Response budget (ns)</span><span class="v">{esc(str(workload.get("response_budget_ns","")))}</span></div>'
        f'<div class="kv"><span class="k">Seed</span><span class="v">{esc(str(workload.get("deterministic_seed","")))}</span></div>'
        f'</div></div>'
    )

    # ---- Root cause panel ----
    root_cause = diagnosis.get("root_cause", "undetermined")
    rc_panel = (
        '<div class="panel"><div class="p-head"><h3>Root-Cause Panel</h3>'
        f'{_badge("diagnosis")}</div><div class="p-body">'
        f'<div class="kv"><span class="k">Classification</span><span class="v">{esc(diagnosis.get("classification","INSUFFICIENT_TRACE"))}</span></div>'
        f'<div class="kv"><span class="k">Root cause</span><span class="v">{esc(root_cause)}</span></div>'
        f'<div class="kv"><span class="k">Violated invariant</span><span class="v">{esc(diagnosis.get("violated_invariant","receive reserve &gt;= 1 during active load"))}</span></div>'
        f'<div class="kv"><span class="k">Priority-inversion claim</span><span class="v">{esc("not supported unless trace confirms")}</span></div>'
        f'<div class="notice"><b>Evidence:</b> {esc(diagnosis.get("description","Trace-derived diagnosis."))}</div>'
        f'</div></div>'
    )

    # ---- Trace evidence timeline ----
    timeline_events = diagnosis.get("timeline_events", []) or []
    tl_rows = ""
    for ev in timeline_events:
        tl_rows += (
            '<div class="t-event">'
            f'<div class="t-dot"></div><div class="t-time">{esc(ev.get("time_us",""))}</div>'
            f'<div class="t-body"><span class="t-label">{esc(ev.get("event",""))}</span> '
            f'{esc(ev.get("detail",""))}</div></div>'
        )
    if not tl_rows:
        tl_rows = '<div class="notice">No focused timeline events available (trace may be insufficient).</div>'
    tl_panel = (
        '<div class="panel"><div class="p-head"><h3>Trace Evidence (implicated threads only)</h3>'
        f'{_badge("trace")}</div><div class="p-body">'
        '<div class="timeline">' + tl_rows + '</div>'
        f'<div class="hashbox"><span class="hl">Raw trace (.kev)</span>'
        f'<span class="hv">{esc(measured.get("raw_trace_sha",""))}</span></div>'
        f'<div class="hashbox"><span class="hl">Normalized trace</span>'
        f'<span class="hv">{esc(measured.get("normalized_trace_sha",""))}</span></div>'
        f'</div></div>'
    )

    # ---- Before-and-after ----
    ba_panel = ""
    if before or after:
        b = before or {}
        a = after or {}
        ba_panel = (
            '<div class="panel"><div class="p-head"><h3>Before &amp; After (same workload)</h3>'
            f'{_badge("verify")}</div><div class="p-body">'
            f'<div class="kv"><span class="k">Baseline min receive reserve</span><span class="v">{esc(str(b.get("min_reserve","—")))}</span></div>'
            f'<div class="kv"><span class="k">Corrected min receive reserve</span><span class="v">{esc(str(a.get("min_reserve","—")))}</span></div>'
            f'<div class="kv"><span class="k">Baseline SEND-blocked clients</span><span class="v">{esc(str(b.get("send_blocked_count","—")))}</span></div>'
            f'<div class="kv"><span class="k">Corrected SEND-blocked clients</span><span class="v">{esc(str(a.get("send_blocked_count","—")))}</span></div>'
            f'<div class="kv"><span class="k">Baseline max latency (ms)</span><span class="v">{esc(str(b.get("max_latency_ms","—")))}</span></div>'
            f'<div class="kv"><span class="k">Corrected max latency (ms)</span><span class="v">{esc(str(a.get("max_latency_ms","—")))}</span></div>'
            f'</div></div>'
        )

    # ---- Evidence receipt ----
    receipt = (
        '<div class="panel"><div class="p-head"><h3>Evidence Receipt</h3>'
        f'{_badge("receipt")}</div><div class="p-body">'
        f'<div class="kv"><span class="k">Incident bundle</span><span class="v">{esc(incident_id)}</span></div>'
        f'<div class="kv"><span class="k">Manifest hash</span><span class="v">{esc(seal_hash or "—")}</span></div>'
        f'<div class="kv"><span class="k">Original trace</span><span class="v">{esc("retained (raw .kev)")}</span></div>'
        f'<div class="kv"><span class="k">Diagnosis</span><span class="v">{esc("hash-linked")}</span></div>'
        f'<div class="kv"><span class="k">Candidate changes</span><span class="v">{esc("verification-engine determined")}</span></div>'
        f'<div class="kv"><span class="k">Replay results</span><span class="v">{esc("same-workload contract")}</span></div>'
        f'<div class="kv"><span class="k">Verification decision</span><span class="v">{esc(verification.get("verdict","—") if verification else "—")}</span></div>'
        f'<div class="kv"><span class="k">Rollback</span><span class="v">{esc("verified or incident unresolved")}</span></div>'
        f'</div></div>'
    )

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>RIFT-QNX Incident "
        + esc(incident_id) + "</title><style>" + _css() + "</style></head><body>"
        '<div class="topbar"><div class="logo">RIFT<span>-QNX</span></div>'
        '<div class="nav"><a href="#">Overview</a><a href="#">Evidence</a><a href="#">Report</a></div></div>'
        '<div class="hero"><h1>RIFT-QNX Incident '
        + esc(incident_id) + "</h1>"
        '<div class="tag">Resource Manager Incident Replay &amp; Assurance</div>'
        "<p>Don't just inspect the trace. Reproduce the stall. Prove the fix.</p></div>"
        + overview + target_panel + rm_panel + wl_panel + rc_panel
        + tl_panel + ba_panel + receipt
        + '<div class="footer">Generated by RIFT-QNX — deterministic evidence. '
        'Model proposes. RIFT decides. Evidence verifies. Not production-certified.</div>'
        "</body></html>"
    )
    return html


def write_report(path: str, html: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(html)
    return path
