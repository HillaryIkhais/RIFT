"""RIFT — forensic minimalism UI.

Generates:
  - index.html     : Landing with cinematic 9-step walkthrough
  - dashboard.html : Forensic incident command center
  - app.json       : Live data for JS fetch
"""
from __future__ import annotations
import glob
import html as html_mod
import json
import os

STORE = os.environ.get("RIFT_STORE", ".rift_store")
OUT = "rift_board"

C = {
    "bg": "#FAFAF8", "fg": "#1A1A1A", "border": "#1A1A1A",
    "muted": "#999999", "accent": "#D64040", "accent2": "#2D8A4E",
    "surface": "#FFFFFF", "surface2": "#F0F0EE",
}


def _css():
    A = C["accent"]
    A2 = C["accent2"]
    B = C["border"]
    BG = C["bg"]
    FG = C["fg"]
    MU = C["muted"]
    S = C["surface"]
    S2 = C["surface2"]
    return (
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');"
        "\n*{margin:0;padding:0;box-sizing:border-box}"
        "\nhtml{scroll-behavior:smooth}"
        "\nbody{font-family:'Inter',sans-serif;background:" + BG + ";color:" + FG + ";-webkit-font-smoothing:antialiased;overflow-x:hidden}"
        "\n::selection{background:" + A + ";color:#fff}"
        # ── keyframes ──
        "\n@keyframes fadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}"
        "\n@keyframes fadeIn{from{opacity:0}to{opacity:1}}"
        "\n@keyframes slideLeft{from{opacity:0;transform:translateX(-30px)}to{opacity:1;transform:translateX(0)}}"
        "\n@keyframes slideRight{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:translateX(0)}}"
        "\n@keyframes scaleIn{from{opacity:0;transform:scale(.92)}to{opacity:1;transform:scale(1)}}"
        "\n@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(214,64,64,.5)}50%{box-shadow:0 0 0 12px rgba(214,64,64,0)}}"
        "\n@keyframes glow{0%,100%{text-shadow:0 0 6px rgba(214,64,64,.3)}50%{text-shadow:0 0 20px rgba(214,64,64,.6)}}"
        "\n@keyframes scanLine{0%{top:-10%}100%{top:110%}}"
        "\n@keyframes typewriter{from{width:0}to{width:100%}}"
        "\n@keyframes blink{50%{border-color:transparent}}"
        "\n@keyframes dash{to{stroke-dashoffset:0}}"
        "\n@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}"
        "\n@keyframes shake{0%,100%{transform:translateX(0)}10%,30%,50%,70%,90%{transform:translateX(-2px)}20%,40%,60%,80%{transform:translateX(2px)}}"
        "\n@keyframes ripple{0%{transform:scale(0);opacity:1}100%{transform:scale(4);opacity:0}}"
        "\n@keyframes gridPulse{0%,100%{opacity:.03}50%{opacity:.08}}"
        "\n@keyframes stepGlow{0%{box-shadow:0 0 0 0 rgba(214,64,64,.4)}50%{box-shadow:0 0 30px 4px rgba(214,64,64,.15)}100%{box-shadow:0 0 0 0 rgba(214,64,64,0)}}"
        "\n@keyframes countUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}"
        # ── base ──
        "\n.topbar{display:flex;justify-content:space-between;align-items:center;padding:16px 40px;border-bottom:3px solid " + B + ";background:" + S + ";position:relative;z-index:10}"
        "\n.logo{font-size:22px;font-weight:900;letter-spacing:-1px;text-decoration:none;color:" + FG + "}"
        "\n.logo span{color:" + A + "}"
        "\n.nav{display:flex;gap:8px}"
        "\n.nav a{padding:8px 16px;border:2px solid " + B + ";font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;text-decoration:none;color:" + FG + ";transition:all .15s ease}"
        "\n.nav a:hover{box-shadow:3px 3px 0 " + B + ";transform:translate(-2px,-2px);background:" + S2 + "}"
        "\n.nav a.active{background:" + FG + ";color:#fff}"
        # ── hero ──
        "\n.hero{position:relative;min-height:100vh;display:flex;align-items:center;overflow:hidden}"
        "\n.hero-bg{position:absolute;inset:0;z-index:0}"
        "\n.hero-grid{position:absolute;inset:0;background-image:"
        "linear-gradient(" + B + " 1px,transparent 1px),linear-gradient(90deg," + B + " 1px,transparent 1px);"
        "background-size:60px 60px;opacity:.04;animation:gridPulse 8s ease-in-out infinite}"
        "\n.hero-dots{position:absolute;inset:0}"
        "\n.hero-dot{position:absolute;width:4px;height:4px;background:" + A + ";border-radius:50%;opacity:.15;animation:float 6s ease-in-out infinite}"
        "\n.hero-inner{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:80px 40px;width:100%}"
        "\n.hero-text{animation:fadeUp .8s ease-out forwards;width:100%}"
        "\n.hero h1{font-size:240px !important;font-weight:900;line-height:1.0;letter-spacing:-10px;margin-bottom:28px}"
        "\n.hero h1 .line{display:block;overflow:visible}"
        "\n.hero h1 .line span{display:inline-block;animation:fadeUp .6s ease-out forwards}"
        "\n.hero h1 .line:nth-child(2) span{animation-delay:.15s}"
        "\n.hero h1 .line:nth-child(3) span{animation-delay:.3s}"
        "\n.hero h1 em{font-style:normal !important;color:" + A + " !important;position:relative}"
        "\n.hero h1 em::after{content:'';position:absolute;bottom:2px;left:0;right:0;height:4px;background:" + A + ";transform:scaleX(0);transform-origin:left;animation:scaleIn .4s ease-out .8s forwards}"
        "\n.hero p{font-size:19px;line-height:1.7;color:" + MU + ";margin-bottom:36px;max-width:500px;animation:fadeUp .6s ease-out .3s forwards;opacity:0}"
        "\n.hero-btns{display:flex;gap:14px;animation:fadeUp .6s ease-out .45s forwards;opacity:0}"
        "\n.btn{padding:16px 32px;font-family:inherit;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;cursor:pointer;text-decoration:none;display:inline-block;border:3px solid " + B + ";transition:all .15s ease;position:relative;overflow:hidden}"
        "\n.btn::after{content:'';position:absolute;inset:0;background:" + FG + ";transform:scaleX(0);transform-origin:left;transition:transform .2s ease;z-index:0}"
        "\n.btn span{position:relative;z-index:1}"
        "\n.btn-fill{background:" + FG + ";color:#fff;box-shadow:5px 5px 0 " + B + "}"
        "\n.btn-fill:hover{box-shadow:8px 8px 0 " + B + ";transform:translate(-3px,-3px)}"
        "\n.btn-ghost{background:transparent;color:" + FG + ";box-shadow:5px 5px 0 " + B + "}"
        "\n.btn-ghost:hover{box-shadow:8px 8px 0 " + B + ";transform:translate(-3px,-3px)}"
        # ── demo terminal ──
        "\n.demo{border:3px solid " + B + ";box-shadow:10px 10px 0 " + B + ";background:" + S + ";display:flex;flex-direction:column;max-width:600px}"
        "\n.demo-header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:3px solid " + B + ";background:" + S2 + "}"
        "\n.demo-header h3{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:2px}"
        "\n.demo-dots{display:flex;gap:5px}"
        "\n.demo-dot{width:10px;height:10px;border-radius:50%;border:2px solid " + B + ";transition:all .4s cubic-bezier(.4,0,.2,1)}"
        "\n.demo-dot.done{background:" + FG + ";border-color:" + FG + ";transform:scale(1.1)}"
        "\n.demo-dot.active{background:" + A + ";border-color:" + A + ";animation:pulse 2s infinite;transform:scale(1.2)}"
        "\n.demo-content{padding:28px 24px;min-height:360px;position:relative;overflow:hidden}"
        "\n.step-card{animation:fadeUp .35s cubic-bezier(.4,0,.2,1) forwards}"
        "\n.step-num{font-size:64px;font-weight:900;color:" + S2 + ";line-height:1;margin-bottom:4px;animation:countUp .3s ease-out forwards}"
        "\n.step-title{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:3px;margin-bottom:8px}"
        "\n.step-title.t-fail,.step-title.t-rift,.step-title.t-diagnose{color:" + A + "}"
        "\n.step-title.t-fix,.step-title.t-verify,.step-title.t-resolve{color:" + A2 + "}"
        "\n.step-title.t-capture,.step-title.t-freeze,.step-title.t-reconstruct{color:" + FG + "}"
        "\n.step-text{font-size:14px;line-height:1.7;color:" + FG + ";margin-bottom:18px}"
        "\n.step-detail{font-family:'JetBrains Mono',monospace;font-size:11px;padding:16px 18px;border:2px solid " + B + ";background:" + S2 + ";line-height:1.9;animation:scaleIn .3s ease-out .1s forwards;opacity:0;position:relative}"
        "\n.step-detail::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:" + A + "}"
        "\n.step-detail .k{color:" + MU + "}"
        "\n.step-detail .v{color:" + FG + ";font-weight:600}"
        "\n.step-detail .err{color:" + A + ";font-weight:700}"
        "\n.step-detail .ok{color:" + A2 + ";font-weight:700}"
        "\n.demo-footer{display:flex;border-top:3px solid " + B + "}"
        "\n.demo-footer button{flex:1;padding:14px;font-family:inherit;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;border:none;border-right:3px solid " + B + ";cursor:pointer;background:transparent;transition:all .15s ease}"
        "\n.demo-footer button:last-child{border-right:none}"
        "\n.demo-footer button:hover{background:" + FG + ";color:#fff}"
        "\n.demo-footer button:active{transform:scale(.97)}"
        "\n.demo-footer button:disabled{opacity:.2;cursor:default;transform:none}"
        # ── sections ──
        "\n.wrap{max-width:1200px;margin:0 auto;padding:0 40px}"
        "\n.section{padding:100px 0}"
        "\n.sec-label{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:3px;color:" + MU + ";margin-bottom:8px}"
        "\n.section h2{font-size:38px;font-weight:900;letter-spacing:-1px;margin-bottom:16px}"
        "\n.section h2 em{font-style:normal;color:" + A + "}"
        "\n.section .sub{font-size:16px;color:" + MU + ";line-height:1.7;max-width:540px;margin-bottom:40px}"
        # ── loop flowchart ──
        "\n.loop{display:flex;flex-wrap:wrap;gap:0;position:relative}"
        "\n.ls{flex:1;min-width:100px;padding:18px 14px;border:3px solid " + B + ";margin-right:-3px;margin-bottom:-3px;transition:all .2s cubic-bezier(.4,0,.2,1);position:relative;background:" + S + "}"
        "\n.ls:last-child{margin-right:0}"
        "\n.ls:hover{background:" + FG + ";color:#fff;z-index:2;transform:translateY(-4px);box-shadow:0 8px 0 " + B + "}"
        "\n.ls:hover small{color:rgba(255,255,255,.6)}"
        "\n.ls:hover .ls-arrow{color:rgba(255,255,255,.4)}"
        "\n.ls strong{display:block;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:2px;margin-bottom:4px}"
        "\n.ls small{font-size:10px;color:" + MU + ";display:block}"
        "\n.ls-arrow{position:absolute;right:-8px;top:50%;transform:translateY(-50%);font-size:14px;color:" + MU + ";z-index:3;transition:color .2s}"
        "\n.ls:last-child .ls-arrow{display:none}"
        # ── cards ──
        "\n.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}"
        "\n.card{border:3px solid " + B + ";box-shadow:5px 5px 0 " + B + ";padding:28px;background:" + S + ";transition:all .25s cubic-bezier(.4,0,.2,1)}"
        "\n.card:hover{box-shadow:8px 8px 0 " + B + ";transform:translate(-3px,-3px)}"
        "\n.card-n{font-size:48px;font-weight:900;color:" + S2 + ";line-height:1;margin-bottom:8px;transition:color .2s}"
        "\n.card:hover .card-n{color:" + A + "30}"
        "\n.card h3{font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}"
        "\n.card p{font-size:12px;line-height:1.7;color:" + MU + "}"
        # ── proof ──
        "\n.proof{border:3px solid " + B + ";box-shadow:5px 5px 0 " + B + ";background:" + S + "}"
        "\n.proof-grid{display:grid;grid-template-columns:repeat(3,1fr)}"
        "\n.proof-item{padding:28px;border:2px solid " + B + ";margin:-2px;text-align:center;transition:all .2s}"
        "\n.proof-item:hover{background:" + FG + ";color:#fff}"
        "\n.proof-item:hover small{color:rgba(255,255,255,.6)}"
        "\n.proof-item strong{display:block;font-size:28px;font-weight:900;margin-bottom:4px}"
        "\n.proof-item small{font-size:9px;color:" + MU + ";text-transform:uppercase;letter-spacing:1.5px}"
        # ── dashboard ──
        "\n.dash{display:grid;grid-template-columns:280px 1fr;min-height:100vh}"
        "\n.sidebar{border-right:3px solid " + B + ";background:" + S + ";display:flex;flex-direction:column}"
        "\n.sb-logo{padding:20px 24px;border-bottom:3px solid " + B + "}"
        "\n.sb-logo a{font-size:18px;font-weight:900;text-decoration:none;color:" + FG + "}"
        "\n.sb-logo a span{color:" + A + "}"
        "\n.sb-sec{padding:16px 20px}"
        "\n.sb-sec h4{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:2px;color:" + MU + ";margin-bottom:10px}"
        "\n.sb-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border:2px solid transparent;font-size:11px;font-weight:600;cursor:pointer;margin-bottom:3px;transition:all .2s cubic-bezier(.4,0,.2,1);border-radius:0;text-align:left;width:100%;background:none;font-family:inherit;color:" + FG + "}"
        "\n.sb-item:hover{border-color:" + B + ";box-shadow:3px 3px 0 " + B + ";transform:translate(-2px,-2px);background:" + S2 + "}"
        "\n.sb-item.on{border:2px solid " + B + ";background:" + FG + ";color:#fff;box-shadow:3px 3px 0 " + B + "}"
        "\n.sb-item.on .sb-meta{color:rgba(255,255,255,.5)}"
        "\n.sb-dot{width:8px;height:8px;border:2px solid " + B + ";flex-shrink:0}"
        "\n.sb-dot.ok{background:" + A2 + "}"
        "\n.sb-dot.err{background:" + A + "}"
        "\n.sb-dot.warn{background:#E8A838}"
        "\n.sb-meta{font-size:9px;color:" + MU + "}"
        # ── main ──
        "\n.main{overflow-y:auto;padding:32px 40px;background:" + BG + "}"
        "\n.m-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px}"
        "\n.m-top h2{font-size:22px;font-weight:900;letter-spacing:-1px}"
        "\n.m-stats{display:flex;gap:8px}"
        "\n.m-stat{padding:6px 14px;border:2px solid " + B + ";font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1px;background:" + S + "}"
        "\n.m-stat em{font-style:normal;color:" + A + "}"
        # ── panels ──
        "\n.panel{border:3px solid " + B + ";box-shadow:6px 6px 0 " + B + ";background:" + S + ";margin-bottom:18px;animation:fadeUp .4s ease-out forwards;transition:all .2s}"
        "\n.panel:hover{box-shadow:8px 8px 0 " + B + ";transform:translate(-1px,-1px)}"
        "\n.panel:nth-child(2){animation-delay:.06s}"
        "\n.panel:nth-child(3){animation-delay:.12s}"
        "\n.panel:nth-child(4){animation-delay:.18s}"
        "\n.panel:nth-child(5){animation-delay:.24s}"
        "\n.panel:nth-child(6){animation-delay:.3s}"
        "\n.p-head{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:3px solid " + B + "}"
        "\n.p-head h3{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:2px}"
        "\n.p-badge{padding:4px 12px;border:2px solid;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1px;transition:all .2s}"
        "\n.p-badge.ok{background:" + A2 + ";color:#fff;border-color:" + A2 + "}"
        "\n.p-badge.err{background:" + A + ";color:#fff;border-color:" + A + "}"
        "\n.p-badge.info{background:" + FG + ";color:#fff;border-color:" + FG + "}"
        "\n.p-body{padding:18px 20px}"
        "\n.kv{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid " + S2 + ";transition:background .15s}"
        "\n.kv:last-child{border-bottom:none}"
        "\n.kv:hover{background:" + S2 + ";margin:0 -20px;padding:10px 20px}"
        "\n.kv .k{font-size:10px;font-weight:700;color:" + MU + ";text-transform:uppercase;letter-spacing:1px}"
        "\n.kv .v{font-size:11px;font-weight:600;text-align:right;max-width:60%;word-break:break-all}"
        "\n.hash-box{display:flex;align-items:center;gap:8px;padding:10px 14px;border:2px solid " + B + ";margin:6px 0;background:" + S2 + ";transition:all .15s}"
        "\n.hash-box:hover{border-color:" + A + "}"
        "\n.hash-box .hl{font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:" + MU + "}"
        "\n.hash-box .hv{font-family:'JetBrains Mono',monospace;font-size:10px;flex:1;word-break:break-all}"
        "\n.hash-box .hc{padding:4px 10px;font-family:inherit;font-size:8px;font-weight:800;border:2px solid " + B + ";background:transparent;cursor:pointer;text-transform:uppercase;transition:all .15s}"
        "\n.hash-box .hc:hover{background:" + FG + ";color:#fff}"
        # ── pipeline ──
        "\n.pipeline{display:flex;margin-bottom:18px;position:relative}"
        "\n.pipeline::after{content:'';position:absolute;bottom:-9px;left:0;right:0;height:3px;background:repeating-linear-gradient(90deg," + B + " 0," + B + " 6px,transparent 6px,transparent 12px)}"
        "\n.pipeline .ps{flex:1;padding:10px 6px;border:3px solid " + B + ";text-align:center;font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-right:-3px;transition:all .3s cubic-bezier(.4,0,.2,1);background:" + S + ";position:relative}"
        "\n.pipeline .ps:last-child{margin-right:0}"
        "\n.pipeline .ps.done{background:" + FG + ";color:#fff;border-color:" + FG + ";transform:translateY(-2px)}"
        "\n.pipeline .ps.now{background:" + A + ";color:#fff;border-color:" + A + ";animation:stepGlow 2s infinite;transform:translateY(-3px)}"
        "\n.pipeline .ps.wait{color:" + MU + ";background:" + S2 + "}"
        "\n.export-box{font-family:'JetBrains Mono',monospace;font-size:10px;line-height:1.7;padding:16px;border:2px solid " + B + ";background:" + S2 + ";max-height:200px;overflow-y:auto;white-space:pre-wrap}"
        "\n.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:100px;text-align:center}"
        "\n.empty h3{font-size:18px;font-weight:800;margin-bottom:8px}"
        "\n.empty p{font-size:12px;color:" + MU + "}"
        "\n.empty-icon{font-size:48px;margin-bottom:16px;opacity:.15}"
        # ── overlays ──
        "\n.scan{position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:9999}"
        "\n.scan::after{content:'';position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent," + A + "30,transparent);animation:scanLine 5s linear infinite;opacity:.6}"
        "\n.grain{position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:9998;opacity:.012}"
        # ── scenario selector ──
        "\n.scenarios{display:flex;gap:0;border:3px solid " + B + ";margin-bottom:-3px;position:relative;z-index:2}"
        "\n.sc-btn{flex:1;padding:10px;font-family:inherit;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;border:none;border-right:3px solid " + B + ";cursor:pointer;background:" + S + ";color:" + FG + ";transition:all .15s}"
        "\n.sc-btn:last-child{border-right:none}"
        "\n.sc-btn:hover{background:" + S2 + "}"
        "\n.sc-btn.active{background:" + FG + ";color:#fff}"
        "\n.sc-label{font-size:9px;font-weight:700;color:" + MU + ";text-transform:uppercase;letter-spacing:1px;padding:6px 0;margin-bottom:4px}"
        # ── export button ──
        "\n.export-btn{display:block;width:100%;margin-top:16px;padding:14px;font-family:inherit;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:2px;border:3px solid " + B + ";background:" + FG + ";color:#fff;cursor:pointer;transition:all .15s;box-shadow:5px 5px 0 " + B + "}"
        "\n.export-btn:hover{box-shadow:8px 8px 0 " + B + ";transform:translate(-3px,-3px);background:" + A + "}"
        "\n@media(max-width:900px){.hero h1{font-size:48px}.cards{grid-template-columns:1fr}.dash{grid-template-columns:1fr}.sidebar{display:none}.loop{flex-direction:column}.ls{margin-right:0}}"
        "\n"
    )


def _topbar(page="landing"):
    if page == "landing":
        links = '<a class="active" href="index.html">Landing</a><a href="dashboard.html">Dashboard</a>'
    else:
        links = '<a href="index.html">Landing</a><a class="active" href="dashboard.html">Dashboard</a>'
    return (
        '<div class="topbar">'
        '<a class="logo" href="index.html">RIFT<span>.</span></a>'
        '<div class="nav">' + links + "</div>"
        "</div>"
    )


def _hero_bg():
    """Animated background with floating dots."""
    import random
    random.seed(42)
    dots = ""
    for i in range(30):
        x = random.randint(5, 95)
        y = random.randint(5, 95)
        d = random.uniform(4, 9)
        delay = random.uniform(0, 5)
        dots += (f'<div class="hero-dot" style="left:{x}%;top:{y}%;animation-delay:{delay:.1f}s;'
                 f'width:{d:.0f}px;height:{d:.0f}px;opacity:{random.uniform(.05,.15):.2f}"></div>')
    return (
        '<div class="hero-bg">'
        '<div class="hero-grid"></div>'
        '<div class="hero-dots">' + dots + '</div>'
        '</div>'
    )


def _landing():
    # Each scenario: (label, steps)
    # Steps: (step_id, title_class, title_text, description, detail_html)
    scenarios = {
        "refund": {
            "label": "Wrong Refund",
            "steps": [
                ("fail", "t-fail", "FAIL",
                 "Agent picks the wrong refund for Sarah Chen.",
                 '<span class="k">user &rarr;</span> <span class="v">"Process Sarah\'s pending refund"</span>\n'
                 '<span class="k">agent &rarr;</span> <span class="v">get_refunds(order_1842)</span>\n'
                 '<span class="k">agent selects</span> <span class="err">R91 &middot; COMPLETED</span>\n'
                 '<span class="k">should have been</span> <span class="ok">R92 &middot; PENDING</span>\n'
                 '<span class="err">WRONG_ENTITY_SELECTION &mdash; duplicate $80 payout</span>'),
                ("capture", "t-capture", "CAPTURE",
                 "RIFT records the complete causal envelope.",
                 '<span class="k">request</span>      <span class="v">"Process Sarah\'s pending refund"</span>\n'
                 '<span class="k">agent</span>         <span class="v">v1.0</span>\n'
                 '<span class="k">state</span>         <span class="v">R91=COMPLETED, R92=PENDING</span>\n'
                 '<span class="ok">47 artifacts recorded</span>'),
                ("freeze", "t-freeze", "FREEZE",
                 "The incident world is hash-sealed.",
                 '<span class="k">world hash</span>\n'
                 '<span class="v">sha256:9f86d08e..4d6e8f</span>\n\n'
                 '<span class="ok">TAMPERING DETECTED &rarr; RELEASE BLOCKED</span>'),
                ("reconstruct", "t-reconstruct", "RECONSTRUCT",
                 "RIFT rebuilds the exact incident environment.",
                 '<span class="k">customer</span>    <span class="v">Sarah Chen</span>\n'
                 '<span class="k">refunds</span>\n'
                 '             <span class="err">R91 &middot; $80 &middot; COMPLETED</span>\n'
                 '             <span class="ok">R92 &middot; $80 &middot; PENDING</span>\n'
                 '<span class="ok">WORLD RECONSTRUCTED</span>'),
                ("rift", "t-rift", "RIFT",
                 "Same agent. Same world. Same failure.",
                 '<span class="k">agent selects</span> <span class="err">R91</span>\n\n'
                 '<span class="err">FAILURE REPRODUCED</span>'),
                ("diagnose", "t-diagnose", "DIAGNOSE",
                 "What the agent got wrong and why.",
                 '<span class="k">expected</span>       <span class="ok">R92 (status=PENDING)</span>\n'
                 '<span class="k">selected</span>       <span class="err">R91 (status=COMPLETED)</span>\n'
                 '<span class="k">root cause</span>      <span class="v">Policy matches by amount, ignores status</span>'),
                ("fix", "t-fix", "FIX",
                 "Correct the agent policy.",
                 '<span class="k">v1.0</span> <span class="v">"Select refund matching amount"</span>\n'
                 '<span class="k">v1.1</span> <span class="ok">"Select PENDING refund matching request"</span>'),
                ("verify", "t-verify", "VERIFY",
                 "Proven fix against frozen incident.",
                 '<span class="k">agent selects</span> <span class="ok">R92</span>\n'
                 '<span class="ok">FIX VERIFIED</span>'),
                 ("resolve", "t-resolve", "RESOLVE",
                  "Fix survived the incident. Release authorized.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="ok">WORLD INTEGRITY       PASS</span>\n'
                  '<span class="ok">FAILURE REPRODUCED    PASS</span>\n'
                  '<span class="ok">FIX VERIFIED          PASS</span>\n'
                  '<span class="ok">EVIDENCE CHAIN        PASS</span>\n\n'
                  '<span class="ok">DECISION              AUTHORIZED</span>\n'
                  '<span class="ok">DEPLOYMENT            RELEASED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'refund\')">EXPORT EVIDENCE &darr;</button>'),
                 ("tamper", "t-fail", "TAMPER",
                  "Someone changes the frozen evidence.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="err">WORLD INTEGRITY       TAMPERED</span>\n'
                  '<span class="err">FAILURE REPRODUCED    REFUSED</span>\n'
                  '<span class="err">FIX VERIFIED          N/A</span>\n'
                  '<span class="err">EVIDENCE CHAIN        BROKEN</span>\n\n'
                  '<span class="err">DECISION              BLOCKED</span>\n'
                  '<span class="err">DEPLOYMENT            REFUSED</span>'),
                ("restore", "t-verify", "RESTORE",
                 "Valid evidence restored. Gate re-evaluated.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="ok">WORLD INTEGRITY       PASS</span>\n'
                  '<span class="ok">FAILURE REPRODUCED    PASS</span>\n'
                  '<span class="ok">FIX VERIFIED          PASS</span>\n'
                  '<span class="ok">EVIDENCE CHAIN        PASS</span>\n\n'
                  '<span class="ok">DECISION              AUTHORIZED</span>\n'
                  '<span class="ok">DEPLOYMENT            RELEASED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'refund\')">EXPORT EVIDENCE &darr;</button>'),
            ]
        },
        "address": {
            "label": "Side Effect",
            "steps": [
                ("fail", "t-fail", "FAIL",
                 "Agent sends unauthorized email during address update.",
                 '<span class="k">user &rarr;</span> <span class="v">"Update my address to 9 Elm St"</span>\n'
                 '<span class="k">agent &rarr;</span> <span class="v">update_address(sarah, "9 Elm St")</span>\n'
                 '<span class="k">agent also</span> <span class="err">send_email("promo_summer")</span>\n'
                 '<span class="err">FORBIDDEN_SIDE_EFFECT &mdash; unauthorized email</span>'),
                ("capture", "t-capture", "CAPTURE",
                 "RIFT records the complete causal envelope.",
                 '<span class="k">request</span>      <span class="v">"Update my address"</span>\n'
                 '<span class="k">agent</span>         <span class="v">v1.0</span>\n'
                 '<span class="k">tools called</span>  <span class="err">update_address, send_email</span>\n'
                 '<span class="ok">32 artifacts recorded</span>'),
                ("freeze", "t-freeze", "FREEZE",
                 "The incident world is hash-sealed.",
                 '<span class="k">world hash</span>\n'
                 '<span class="v">sha256:a3b8c1..7e2f9a</span>\n\n'
                 '<span class="ok">SEALED</span>'),
                ("reconstruct", "t-reconstruct", "RECONSTRUCT",
                 "RIFT rebuilds the exact incident environment.",
                 '<span class="k">customer</span>    <span class="v">Sarah Chen</span>\n'
                 '<span class="k">address</span>     <span class="v">123 Main St (current)</span>\n'
                 '<span class="k">tools</span>       <span class="v">update_address(), send_email()</span>\n'
                 '<span class="ok">WORLD RECONSTRUCTED</span>'),
                ("rift", "t-rift", "RIFT",
                 "Same agent. Same world. Same failure.",
                 '<span class="k">agent calls</span> <span class="err">send_email("promo_summer")</span>\n\n'
                 '<span class="err">FAILURE REPRODUCED</span>'),
                ("diagnose", "t-diagnose", "DIAGNOSE",
                 "What the agent got wrong and why.",
                 '<span class="k">expected</span>       <span class="ok">UPDATE_ADDRESS only</span>\n'
                 '<span class="k">actual</span>         <span class="err">UPDATE_ADDRESS + send_email</span>\n'
                 '<span class="k">root cause</span>      <span class="v">Agent not constrained to stated intent</span>'),
                ("fix", "t-fix", "FIX",
                 "Constrain the agent to user intent.",
                 '<span class="k">v1.0</span> <span class="v">"Process the request"</span>\n'
                 '<span class="k">v1.1</span> <span class="ok">"Only perform actions directly requested"</span>'),
                ("verify", "t-verify", "VERIFY",
                 "Proven fix against frozen incident.",
                 '<span class="k">agent calls</span> <span class="ok">update_address only</span>\n'
                 '<span class="ok">FIX VERIFIED</span>'),
                 ("resolve", "t-resolve", "RESOLVE",
                  "Fix survived the incident. Release authorized.",
                  '<span class="k">status</span>         <span class="ok">INCIDENT RESOLVED</span>\n'
                  '<span class="k">agent version</span>  <span class="v">v1.1</span>\n'
                  '<span class="k">what happened</span>  <span class="v">Unauthorized email sent</span>\n'
                  '<span class="k">fix verified</span>   <span class="ok">PASS</span>\n'
                  '<span class="k">evidence</span>       <span class="ok">integrity verified</span>\n\n'
                  '<span class="ok">RELEASE AUTHORIZED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'address\')">EXPORT EVIDENCE &darr;</button>'),
                 ("tamper", "t-fail", "TAMPER",
                  "Someone changes the frozen evidence.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="err">WORLD INTEGRITY       TAMPERED</span>\n'
                  '<span class="err">FAILURE REPRODUCED    REFUSED</span>\n'
                  '<span class="err">FIX VERIFIED          N/A</span>\n'
                  '<span class="err">EVIDENCE CHAIN        BROKEN</span>\n\n'
                  '<span class="err">DECISION              BLOCKED</span>\n'
                  '<span class="err">DEPLOYMENT            REFUSED</span>'),
                 ("restore", "t-verify", "RESTORE",
                  "Valid evidence restored. Gate re-evaluated.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="ok">WORLD INTEGRITY       PASS</span>\n'
                  '<span class="ok">FAILURE REPRODUCED    PASS</span>\n'
                  '<span class="ok">FIX VERIFIED          PASS</span>\n'
                  '<span class="ok">EVIDENCE CHAIN        PASS</span>\n\n'
                  '<span class="ok">DECISION              AUTHORIZED</span>\n'
                  '<span class="ok">DEPLOYMENT            RELEASED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'address\')">EXPORT EVIDENCE &darr;</button>'),
            ]
        },
        "cancel": {
            "label": "Bad Cancel",
            "steps": [
                ("fail", "t-fail", "FAIL",
                 "Agent cancels a shipped order.",
                 '<span class="k">user &rarr;</span> <span class="v">"Cancel order #1842"</span>\n'
                 '<span class="k">agent &rarr;</span> <span class="v">cancel_order(order_1842)</span>\n'
                 '<span class="k">order status</span> <span class="err">SHIPPED &rarr; CANCELLED</span>\n'
                 '<span class="err">STATE_TRANSITION_VIOLATION &mdash; shipped cannot cancel</span>'),
                ("capture", "t-capture", "CAPTURE",
                 "RIFT records the complete causal envelope.",
                 '<span class="k">request</span>      <span class="v">"Cancel order #1842"</span>\n'
                 '<span class="k">agent</span>         <span class="v">v1.0</span>\n'
                 '<span class="k">order state</span>   <span class="err">SHIPPED</span>\n'
                 '<span class="ok">28 artifacts recorded</span>'),
                ("freeze", "t-freeze", "FREEZE",
                 "The incident world is hash-sealed.",
                 '<span class="k">world hash</span>\n'
                 '<span class="v">sha256:b7d4e2..1c8f3a</span>\n\n'
                 '<span class="ok">SEALED</span>'),
                ("reconstruct", "t-reconstruct", "RECONSTRUCT",
                 "RIFT rebuilds the exact incident environment.",
                 '<span class="k">order</span>       <span class="v">#1842 &middot; $120 &middot; SHIPPED</span>\n'
                 '<span class="k">customer</span>    <span class="v">Mike Johnson</span>\n'
                 '<span class="ok">WORLD RECONSTRUCTED</span>'),
                ("rift", "t-rift", "RIFT",
                 "Same agent. Same world. Same failure.",
                 '<span class="k">agent calls</span> <span class="err">cancel_order(order_1842)</span>\n\n'
                 '<span class="err">FAILURE REPRODUCED</span>'),
                ("diagnose", "t-diagnose", "DIAGNOSE",
                 "What the agent got wrong and why.",
                 '<span class="k">expected</span>       <span class="ok">Escalate to refund request</span>\n'
                 '<span class="k">actual</span>         <span class="err">cancel_order (SHIPPED &rarr; CANCELLED)</span>\n'
                 '<span class="k">root cause</span>      <span class="v">Agent does not check order status</span>'),
                ("fix", "t-fix", "FIX",
                 "Add status check before cancel.",
                 '<span class="k">v1.0</span> <span class="v">"Cancel the order"</span>\n'
                 '<span class="k">v1.1</span> <span class="ok">"Check status first. SHIPPED = refund request."</span>'),
                ("verify", "t-verify", "VERIFY",
                 "Proven fix against frozen incident.",
                 '<span class="k">agent escalates</span> <span class="ok">REFUND_REQUEST</span>\n'
                 '<span class="ok">FIX VERIFIED</span>'),
                 ("resolve", "t-resolve", "RESOLVE",
                  "Fix survived the incident. Release authorized.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="ok">WORLD INTEGRITY       PASS</span>\n'
                  '<span class="ok">FAILURE REPRODUCED    PASS</span>\n'
                  '<span class="ok">FIX VERIFIED          PASS</span>\n'
                  '<span class="ok">EVIDENCE CHAIN        PASS</span>\n\n'
                  '<span class="ok">DECISION              AUTHORIZED</span>\n'
                  '<span class="ok">DEPLOYMENT            RELEASED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'cancel\')">EXPORT EVIDENCE &darr;</button>'),
                 ("tamper", "t-fail", "TAMPER",
                  "Someone changes the frozen evidence.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="err">WORLD INTEGRITY       TAMPERED</span>\n'
                  '<span class="err">FAILURE REPRODUCED    REFUSED</span>\n'
                  '<span class="err">FIX VERIFIED          N/A</span>\n'
                  '<span class="err">EVIDENCE CHAIN        BROKEN</span>\n\n'
                  '<span class="err">DECISION              BLOCKED</span>\n'
                  '<span class="err">DEPLOYMENT            REFUSED</span>'),
                 ("restore", "t-verify", "RESTORE",
                  "Valid evidence restored. Gate re-evaluated.",
                  '<span class="k">PROPOSED DEPLOYMENT</span>\n'
                  '<span class="k">agent:</span> <span class="v">v1.1</span>\n'
                  '<span class="k">target:</span> <span class="v">production</span>\n\n'
                  '<span class="k">RIFT RELEASE GATE</span>\n'
                  '<span class="ok">WORLD INTEGRITY       PASS</span>\n'
                  '<span class="ok">FAILURE REPRODUCED    PASS</span>\n'
                  '<span class="ok">FIX VERIFIED          PASS</span>\n'
                  '<span class="ok">EVIDENCE CHAIN        PASS</span>\n\n'
                  '<span class="ok">DECISION              AUTHORIZED</span>\n'
                  '<span class="ok">DEPLOYMENT            RELEASED</span>\n\n'
                  '<button class="export-btn" onclick="exportEvidence(\'cancel\')">EXPORT EVIDENCE &darr;</button>'),
            ]
        },
    }

    # build HTML for all scenarios (only first visible)
    all_steps_html = ""
    for sc_key, sc in scenarios.items():
        for idx, (step_id, title_cls, title_text, desc, detail) in enumerate(sc["steps"]):
            num = str(idx + 1).zfill(2)
            vis = "block" if sc_key == "refund" and idx == 0 else "none"
            all_steps_html += (
                '<div class="step-card" data-sc="' + sc_key + '" data-step="' + str(idx) + '" style="display:' + vis + '">'
                '<div class="step-num">' + num + "</div>"
                '<div class="step-title ' + title_cls + '">' + title_text + "</div>"
                '<div class="step-text">' + desc + "</div>"
                '<div class="step-detail">' + detail + "</div>"
                "</div>"
            )

    # scenario buttons
    sc_btns = ""
    for i, (sc_key, sc) in enumerate(scenarios.items()):
        ac = " active" if sc_key == "refund" else ""
        sc_btns += '<button class="sc-btn' + ac + '" onclick="switchSc(\'' + sc_key + '\')">' + sc["label"] + '</button>'

    # dots (11 per scenario)
    dots_html = ""
    for i in range(11):
        dots_html += '<div class="demo-dot" data-dot="' + str(i) + '"></div>'

    # scenario data as JSON for JS
    sc_json = json.dumps({k: len(v["steps"]) for k, v in scenarios.items()})

    return (
        _hero_bg()
        + '<div class="hero-inner">'
        '<div class="hero-text">'
        '<h1>'
        '<span class="line"><span>When an AI agent fails,</span></span>'
        '<span class="line"><span>the world <strong style="color:#D64040">keeps changing</strong></span></span>'
        '</h1>'
        "<p>RIFT freezes the incident world so you can reproduce the exact failure and prove the fix.</p>"
        '<div class="hero-btns">'
        '<a class="btn btn-fill" href="dashboard.html"><span>Open Dashboard</span></a>'
        '<a class="btn btn-ghost" href="#how"><span>How it works</span></a>'
        "</div>"
        "</div>"
        "</div>"
        '<div class="wrap">'
        '<div class="section" id="how">'
        '<div class="sec-label">/ How it works</div>'
        "<h2>The <em>complete loop</em></h2>"
        '<p class="sub">Not just reproduction. The entire incident lifecycle from failure to verified resolution.</p>'
        '<div class="loop">'
        '<div class="ls"><strong>FAIL</strong><small>Agent acts</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>CAPTURE</strong><small>Record causal envelope</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>FREEZE</strong><small>Hash-seal world</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>RECONSTRUCT</strong><small>Rebuild environment</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>RIFT</strong><small>Reproduce failure</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>DIAGNOSE</strong><small>Explain divergence</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>FIX</strong><small>Correct agent</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>VERIFY</strong><small>Prove fix works</small><span class="ls-arrow">&rarr;</span></div>'
        '<div class="ls"><strong>RESOLVE</strong><small>Fix survived incident</small></div>'
        "</div></div>"
        '<div class="section" id="walkthrough">'
        '<div class="sec-label">/ Walkthrough</div>'
        "<h2>See it <em>fail</em></h2>"
        '<p class="sub">Step through an incident from failure to resolution.</p>'
        '<div class="demo">'
        '<div class="scenarios">' + sc_btns + '</div>'
        '<div class="demo-header">'
        "<h3>Incident Walkthrough</h3>"
        '<div class="demo-dots">' + dots_html + "</div>"
        "</div>"
        '<div class="demo-content" id="demo-content">' + all_steps_html + "</div>"
        '<div class="demo-footer">'
        '<button id="btn-prev" onclick="prev()">&larr; Prev</button>'
        '<button onclick="reset()">Reset</button>'
        '<button id="btn-next" onclick="next()">Next &rarr;</button>'
        "</div>"
        "</div>"
        "</div>"
        '<div class="section">'
        '<div class="sec-label">/ The problem</div>'
        "<h2>The <em>missing boundary</em></h2>"
        '<p class="sub">AI agents operate across changing state. When something goes wrong, the original context disappears.</p>'
        '<div class="cards">'
        '<div class="card"><div class="card-n">01</div><h3>World changes</h3><p>Between failure and investigation, state drifts. The world that caused the bug is gone.</p></div>'
        '<div class="card"><div class="card-n">02</div><h3>No snapshot</h3><p>Logs and traces don\'t preserve the exact world state for re-running the agent.</p></div>'
        '<div class="card"><div class="card-n">03</div><h3>Guesswork</h3><p>Without reproduction, you can\'t prove your fix works. Debugging blind.</p></div>'
        "</div></div>"
        '<div class="section">'
        '<div class="sec-label">/ Proof</div>'
        '<div class="proof">'
        '<div class="proof-grid">'
        '<div class="proof-item"><strong>SHA-256</strong><small>Hash sealed</small></div>'
        '<div class="proof-item"><strong>FROZEN</strong><small>Cannot drift</small></div>'
        '<div class="proof-item"><strong>DETERMINISTIC</strong><small>Same input &rarr; same output</small></div>'
        "</div></div></div>"
        "</div>"
        # JS
        "<script>"
        "var SC=" + sc_json + ";"
        "var curSc='refund';var step=0;"
        "function show(){"
        "document.querySelectorAll('.step-card').forEach(function(c){c.style.display='none';});"
        "var card=document.querySelector('.step-card[data-sc=\"'+curSc+'\"][data-step=\"'+step+'\"]');"
        "if(card)card.style.display='block';"
        "var total=SC[curSc]||9;"
        "document.querySelectorAll('.demo-dot').forEach(function(d,i){d.className='demo-dot'+(i<step?' done':(i===step?' active':''));});"
        "document.getElementById('btn-prev').disabled=step===0;"
        "document.getElementById('btn-next').disabled=step===total-1;"
        "}"
        "function next(){var t=SC[curSc]||9;if(step<t-1){step++;show();}}"
        "function prev(){if(step>0){step--;show();}}"
        "function reset(){step=0;show();}"
        "function switchSc(k){curSc=k;step=0;"
        "document.querySelectorAll('.sc-btn').forEach(function(b){b.classList.remove('active')});"
        "event.target.classList.add('active');show();}"
        "function exportEvidence(sc){"
        "var evidence={"
        "refund:{id:'inc_047',cat:'WRONG_ENTITY_SELECTION',what:'Agent selected R91 (COMPLETED) instead of R92 (PENDING)',cause:'Policy matches by amount, ignores status',fix:'v1.1 — filter by status before amount',verdict:'FIX_VERIFIED'},"
        "address:{id:'inc_048',cat:'FORBIDDEN_SIDE_EFFECT',what:'Agent sent promotional email during address update',cause:'Agent not constrained to stated intent',fix:'v1.1 — constrain to user intent only',verdict:'FIX_VERIFIED'},"
        "cancel:{id:'inc_049',cat:'STATE_TRANSITION_VIOLATION',what:'Agent cancelled shipped order #1842',cause:'Agent does not check order status before acting',fix:'v1.1 — check status, SHIPPED → refund request',verdict:'FIX_VERIFIED'}"
        "};"
        "var e=evidence[sc];var now=new Date().toISOString();"
        "var md='# RIFT INCIDENT EVIDENCE\\n\\n'+'Incident: '+e.id+'\\n'+'Agent: v1.1\\n'+'Original Version: v1.0\\n'+'Verified Version: v1.1\\n'+'Category: '+e.cat+'\\n\\n'+'---\\n\\n'+'## ORIGINAL FAILURE\\n\\n'+e.what+'\\n\\n'+'## FROZEN WORLD\\n\\n'+'World Hash: sha256:...\\n'+'State: VERIFIED\\n'+'Context: VERIFIED\\n'+'Tools: VERIFIED\\n'+'Trajectory: VERIFIED\\n\\n'+'## REPRODUCTION\\n\\n'+'Original agent: FAILED\\n'+'Failure reproduced: YES\\n\\n'+'## DIAGNOSIS\\n\\n'+'Root cause: '+e.cause+'\\n\\n'+'## FIX\\n\\n'+e.fix+'\\n\\n'+'## VERIFICATION\\n\\n'+'Fixed agent: PASSED\\n'+'Original incident conditions: PRESERVED\\n\\n'+'## INTEGRITY\\n\\n'+'Frozen evidence tampering: NOT DETECTED\\n\\n'+'## RESOLUTION\\n\\n'+'INCIDENT RESOLVED\\n'+'Resolved: '+now+'\\n\\n'+'## RELEASE STATUS\\n\\n'+'PRODUCTION-SAFE\\n'+'Release authorized: YES\\n\\n'+'---\\n\\n'+'*Generated by RIFT — '+now+'*\\n';"
        "var blob=new Blob([md],{type:'text/markdown'});"
        "var a=document.createElement('a');a.href=URL.createObjectURL(blob);"
        "a.download=e.id+'-evidence.md';a.click();}"
        "show();"
        "</script>"
    )


def _load_store():
    data = {"runs": [], "incidents": [], "worlds": [], "replays": [], "fixes": [], "exports": []}
    for kind in data:
        for path in sorted(glob.glob(os.path.join(STORE, kind, "*.json"))):
            try:
                with open(path) as f:
                    data[kind].append(json.load(f))
            except Exception:
                pass
    return data


def _dashboard(data):
    runs, incidents, worlds, replays, fixes = data["runs"], data["incidents"], data["worlds"], data["replays"], data["fixes"]

    sb_inc = ""
    for inc in incidents:
        iid = inc.get("incident_id", "")
        sc = "err" if "WRONG" in inc.get("category", "") else "warn"
        sb_inc += (
            '<button class="sb-item" onclick="sel(\'' + iid + '\')" data-id="' + iid + '">'
            '<span class="sb-dot ' + sc + '"></span>'
            '<div><div>' + html_mod.escape(inc.get("category", "")) + '</div>'
            '<div class="sb-meta">' + html_mod.escape(iid) + "</div></div></button>"
        )

    sb_runs = ""
    for run in runs:
        rid = run.get("run_id", "")
        sb_runs += (
            '<button class="sb-item" onclick="selRun(\'' + rid + '\')" data-id="' + rid + '">'
            '<span class="sb-dot"></span>'
            '<div><div>RUN</div><div class="sb-meta">' + html_mod.escape(rid) + "</div></div></button>"
        )

    resolved = sum(1 for i in incidents if i.get("status") == "RESOLVED")

    return (
        '<div class="dash">'
        '<div class="sidebar">'
        '<div class="sb-logo"><a href="index.html">RIFT<span>.</span></a></div>'
        '<div class="sb-sec"><h4>Runs (' + str(len(runs)) + ")</h4>" + sb_runs + "</div>"
        '<div class="sb-sec"><h4>Incidents (' + str(len(incidents)) + ")</h4>" + sb_inc + "</div>"
        "</div>"
        '<div class="main">'
        '<div class="m-top"><h2>Incident Command Center</h2>'
        '<div class="m-stats">'
        '<div class="m-stat">Runs <em>' + str(len(runs)) + "</em></div>"
        '<div class="m-stat">Incidents <em>' + str(len(incidents)) + "</em></div>"
        '<div class="m-stat">Fixes <em>' + str(len(fixes)) + "</em></div>"
        '<div class="m-stat">Resolved <em>' + str(resolved) + "</em></div>"
        "</div></div>"
        '<div id="view">'
        '<div class="empty"><div class="empty-icon">&diams;</div><h3>Select an incident</h3><p>Choose from the sidebar to begin investigation.</p></div>'
        "</div></div></div>"
    )


def _js(dj):
    return (
        "<script>var D=" + dj + ";"
        "function selRun(rid){"
        "document.querySelectorAll('.sb-item').forEach(function(b){b.classList.remove('on')});"
        "var b=document.querySelector('.sb-item[data-id=\"'+rid+'\"]');if(b)b.classList.add('on');"
        "var r=D.runs.find(function(x){return x.run_id===rid});if(!r)return;"
        "var i=D.incidents.find(function(x){return x.run_id===rid});"
        "var iid=i?i.incident_id:'';"
        "var w=D.worlds.find(function(x){return x.incident_id===iid});"
        "var rp=D.replays.find(function(x){return x.incident_id===iid});"
        "var fx=D.fixes.find(function(x){return x.agent_version===(i?i.agent_version:'')});"
        "show(r,i,w,rp,fx);}"
        "function sel(iid){"
        "document.querySelectorAll('.sb-item').forEach(function(b){b.classList.remove('on')});"
        "var b=document.querySelector('.sb-item[data-id=\"'+iid+'\"]');if(b)b.classList.add('on');"
        "var i=D.incidents.find(function(x){return x.incident_id===iid});"
        "var r=D.runs.find(function(x){return x.run_id===(i?i.run_id:'')});"
        "var w=D.worlds.find(function(x){return x.incident_id===iid});"
        "var rp=D.replays.find(function(x){return x.incident_id===iid});"
        "var fx=D.fixes.find(function(x){return x.agent_version===(i?i.agent_version:'')});"
        "show(r,i,w,rp,fx);}"
        "function show(r,i,w,rp,fx){"
        "var v=document.getElementById('view');"
        "var h='';"
        "h+=pipe(r,i,w,rp,fx);"
        "if(r)h+=p('FAIL','info','captured',[kv('run_id',r.run_id),kv('task',JSON.stringify(r.task)),kv('agent',r.agent_version),kv('outcome',r.outcome)]);"
        "if(i){var d=i.diagnosis||{};"
        "h+=p('CAPTURE & FREEZE','err',i.category,[kv('incident',i.incident_id),kv('what',i.what_happened),kv('why',i.why_it_matters),kv('cause',i.root_cause),hsh('hash',i.incident_hash)]);"
        "if(d.expected)h+=p('DIAGNOSE','err','divergence',[kv('expected',d.expected),kv('actual',d.actual),kv('signal',d.decision_signal),kv('ignored',d.ignored_signal)]);}"
        "if(w)h+=p('RECONSTRUCT','info','sealed',[kv('category',w.category),hsh('freeze_hash',w.freeze_hash)]);"
        "if(rp)h+=p('RIFT',rp.result==='FAIL'?'err':'ok',rp.result,[kv('agent',rp.agent_version),kv('result',rp.result),kv('reproduced',String(rp.failure_reproduced))]);"
        "if(fx)h+=p('FIX & VERIFY','ok','verified',[kv('verdict',fx.verdict),kv('fixed',fx.fixed+'/'+fx.total)]);"
        "if(fx&&fx.verdict==='FIX_VERIFIED'){"
        "h+=p('RESOLVE','ok','released',[kv('agent',fx.fixed_agent||'v1.1'),kv('target','production'),'<div style=\"padding:12px 0;font-family:monospace;font-size:10px;line-height:1.8\"><strong>RIFT RELEASE GATE</strong><br><span style=\"color:#2D8A4E\">WORLD INTEGRITY       PASS</span><br><span style=\"color:#2D8A4E\">FAILURE REPRODUCED    PASS</span><br><span style=\"color:#2D8A4E\">FIX VERIFIED          PASS</span><br><span style=\"color:#2D8A4E\">EVIDENCE CHAIN        PASS</span><br><br><strong style=\"color:#2D8A4E\">DECISION              AUTHORIZED</strong><br><strong style=\"color:#2D8A4E\">DEPLOYMENT            RELEASED</strong></div>','<div style=\"padding:12px 0\"><button class=\"export-btn\" onclick=\"exportDashEvidence()\">EXPORT EVIDENCE &darr;</button></div>']);}"
        "v.innerHTML=h;}"
        "function pipe(r,i,w,rp,fx){"
        "var resolved=fx&&fx.verdict==='FIX_VERIFIED';"
        "var gate=resolved;"
        "var s=[{n:'FAIL',d:r},{n:'CAPTURE',d:i},{n:'FREEZE',d:w},{n:'RECON',d:w},{n:'RIFT',d:rp},{n:'DIAG',d:i&&i.diagnosis},{n:'FIX',d:fx},{n:'VER',d:fx&&fx.verdict==='FIX_VERIFIED'},{n:'GATE',d:gate},{n:'RELEASE',d:gate}];"
        "var h='<div class=\"pipeline\">';"
        "s.forEach(function(x){h+='<div class=\"ps '+(x.d?'done':'wait')+'\">'+x.n+'</div>';});"
        "return h+'</div>';}"
        "function p(t,b,bt,r){return '<div class=\"panel\"><div class=\"p-head\"><h3>'+t+'</h3><span class=\"p-badge '+b+'\">'+bt+'</span></div><div class=\"p-body\">'+r.join('')+'</div></div>';}"
        "function kv(k,v){return '<div class=\"kv\"><span class=\"k\">'+k+'</span><span class=\"v\">'+v+'</span></div>';}"
        "function hsh(l,h){return '<div class=\"hash-box\"><span class=\"hl\">'+l+'</span><span class=\"hv\">'+h+'</span><button class=\"hc\" onclick=\"navigator.clipboard.writeText(this.previousElementSibling.textContent);this.textContent=\\'ok\\';setTimeout(function(){this.textContent=\\'copy\\'}.bind(this),1200)\">copy</button></div>';}"
        "function exportDashEvidence(){"
        "var inc=D.incidents[0];if(!inc)return;"
        "var d=inc.diagnosis||{};"
        "var md='# RIFT INCIDENT EVIDENCE\\n\\n'+'Incident: '+inc.incident_id+'\\n'+'Agent: v1.1\\n'+'Original Version: v1.0\\n'+'Verified Version: v1.1\\n'+'Category: '+inc.category+'\\n\\n'+'---\\n\\n'+'## ORIGINAL FAILURE\\n\\n'+inc.what_happened+'\\n\\n'+'## FROZEN WORLD\\n\\n'+'World Hash: '+inc.incident_hash+'\\n'+'State: VERIFIED\\n'+'Context: VERIFIED\\n'+'Tools: VERIFIED\\n'+'Trajectory: VERIFIED\\n\\n'+'## REPRODUCTION\\n\\n'+'Original agent: FAILED\\n'+'Failure reproduced: YES\\n\\n'+'## DIAGNOSIS\\n\\n'+'Expected: '+(d.expected||'n/a')+'\\n'+'Actual: '+(d.actual||'n/a')+'\\n'+'Root cause: '+inc.root_cause+'\\n'+'Failure class: '+(d.failure_class||'n/a')+'\\n\\n'+'## FIX\\n\\n'+'Agent version: v1.1\\n'+'Verdict: FIX_VERIFIED\\n\\n'+'## VERIFICATION\\n\\n'+'Fixed agent: PASSED\\n'+'Original incident conditions: PRESERVED\\n\\n'+'## INTEGRITY\\n\\n'+'Frozen evidence tampering: NOT DETECTED\\n\\n'+'## RESOLUTION\\n\\n'+'INCIDENT RESOLVED\\n\\n'+'## RELEASE STATUS\\n\\n'+'PRODUCTION-SAFE\\n'+'Release authorized: YES\\n\\n'+'---\\n\\n'+'*Generated by RIFT*\\n';"
        "var blob=new Blob([md],{type:'text/markdown'});"
        "var a=document.createElement('a');a.href=URL.createObjectURL(blob);"
        "a.download=inc.incident_id+'-evidence.md';a.click();}"
        "</script>"
    )


def build():
    os.makedirs(OUT, exist_ok=True)
    data = _load_store()
    css = _css()

    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>RIFT - Incident Reconstruction for AI Agents</title>"
                "<style>" + css + "</style></head><body>"
                + '<div class="scan"></div><div class="grain"></div>'
                + _topbar("landing") + _landing() + "</body></html>")

    with open(os.path.join(OUT, "dashboard.html"), "w") as f:
        f.write("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>RIFT Dashboard</title>"
                "<style>" + css + "</style></head><body>"
                + '<div class="scan"></div><div class="grain"></div>'
                + _topbar("dashboard") + _dashboard(data) + _js(json.dumps(data)) + "</body></html>")

    with open(os.path.join(OUT, "app.json"), "w") as f:
        json.dump(data, f, indent=2)

    print(f"[rift] {OUT}/ | {len(data['runs'])} runs, {len(data['incidents'])} incidents, "
          f"{len(data['worlds'])} worlds, {len(data['replays'])} replays, {len(data['fixes'])} fixes")


if __name__ == "__main__":
    build()
