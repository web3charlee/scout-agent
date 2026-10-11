"""HTML/CSS building blocks for the Streamlit UI.

Design: "survey sheet". Navy from the Scout mark, paper-white body, a contour-map hero (terrain = scouting),
amber beacon dot taken from the logo's dot to flag live activity and high-signal items.
Strings are built without blank lines or indentation so Streamlit's markdown never treats them as code.
"""
from __future__ import annotations

import base64
import math

from .utils import domain_of, esc

NAVY, INK, PAPER, BLUE, AMBER = "#0B2559", "#071A40", "#F4F7FD", "#2F5BFF", "#FFB020"

ROLE_INFO = {
    "planner": ("Planner", "◈", "Breaks the question into research tasks"),
    "news": ("News & Web", "◉", "Press, partnerships, deals"),
    "company": ("Company Data", "▣", "Funding, hiring, pricing"),
    "product": ("Product & Tech", "⬡", "Changelogs, releases, GitHub"),
    "social": ("Social & Sentiment", "◐", "Reddit, X, review sites"),
    "critic": ("Critic", "✦", "Cross-checks and writes the report"),
}


def _b64(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def mark_svg(color: str, dot: str | None = None) -> str:
    dot = dot or color
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 200">'
            f'<polygon points="5,155 113,7 220,155 195,187 113,75 30,187" fill="{color}"/>'
            f'<circle cx="114" cy="159" r="26" fill="{dot}"/></svg>')


def logo(color: str = NAVY, height: int = 34, dot: str | None = None, text_color: str | None = None) -> str:
    tc = text_color or color
    return (f'<span class="logo"><img src="{_b64(mark_svg(color, dot))}" style="height:{height}px"/>'
            f'<span class="logo-word" style="color:{tc};font-size:{round(height*0.78)}px">SCOUT</span></span>')


def contour_svg() -> str:
    """Concentric, noise-warped rings: a topographic map."""
    paths = []
    cx, cy = 820, 150
    for k in range(1, 15):
        r0 = 26 * k
        pts = []
        for i in range(0, 361, 6):
            a = math.radians(i)
            wob = 1 + 0.10 * math.sin(3 * a + k * 0.5) + 0.06 * math.sin(5 * a - k * 0.3)
            pts.append((cx + r0 * 1.7 * wob * math.cos(a), cy + r0 * 0.95 * wob * math.sin(a)))
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
        op = 0.10 + 0.012 * (15 - k)
        paths.append(f'<path d="{d}" fill="none" stroke="#9DB6FF" stroke-opacity="{op:.2f}" stroke-width="1"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300" preserveAspectRatio="xMaxYMid slice">{"".join(paths)}</svg>'


def css() -> str:
    bg = _b64(contour_svg())
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Newsreader:ital,wght@0,400;0,500;1,400&family=JetBrains+Mono:wght@500&display=swap');
:root{{--navy:{NAVY};--ink:{INK};--paper:{PAPER};--blue:{BLUE};--amber:{AMBER};--line:#D5DEF0;--mute:#5B6B93;--ok:#0E9F6E;--bad:#D6454B;--card:#FFFFFF;}}
html,body,.stApp,[class*="css"]{{font-family:'Manrope',system-ui,sans-serif;color:var(--navy);}}
.stApp{{background:var(--paper);}}
[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu{{display:none!important}}
header[data-testid="stHeader"]{{background:transparent}}
.block-container{{max-width:1160px;padding-top:1.2rem;padding-bottom:4rem}}
h1,h2,h3,h4{{font-family:'Manrope',sans-serif;letter-spacing:-.02em;color:var(--navy)}}
section[data-testid="stSidebar"]{{background:#fff;border-right:1px solid var(--line)}}
.logo{{display:inline-flex;align-items:center;gap:.55rem}}
.logo-word{{font-weight:800;letter-spacing:.01em;line-height:1}}
/* hero */
.hero{{position:relative;overflow:hidden;border-radius:22px;padding:2.4rem 2.6rem 2.2rem;margin-bottom:1.3rem;
background:linear-gradient(135deg,{INK} 0%,{NAVY} 55%,#143C8C 100%);color:#fff}}
.hero:before{{content:"";position:absolute;inset:0;background:url({bg}) right center/cover no-repeat;opacity:.9}}
.hero>*{{position:relative}}
.hero h1{{color:#fff;font-size:2.55rem;line-height:1.08;font-weight:800;margin:1.2rem 0 .7rem;max-width:720px}}
.hero p{{color:#C7D5FF;font-size:1.05rem;max-width:620px;margin:0 0 1.1rem;line-height:1.55}}
.chips{{display:flex;gap:.5rem;flex-wrap:wrap}}
.chip{{border:1px solid rgba(157,182,255,.35);border-radius:999px;padding:.28rem .8rem;font-size:.8rem;color:#DCE6FF;background:rgba(255,255,255,.06)}}
.beacon{{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--amber);margin-right:.45rem;box-shadow:0 0 0 0 rgba(255,176,32,.7);animation:ping 1.8s infinite}}
@keyframes ping{{70%{{box-shadow:0 0 0 9px rgba(255,176,32,0)}}100%{{box-shadow:0 0 0 0 rgba(255,176,32,0)}}}}
@media (prefers-reduced-motion:reduce){{.beacon,.pnode.run .pico{{animation:none}}}}
/* inputs */
.stTextInput input{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:.85rem 1rem;font-size:1.05rem;color:var(--navy)}}
.stTextInput input:focus{{border-color:var(--blue);box-shadow:0 0 0 3px rgba(47,91,255,.15)}}
.stButton>button,.stDownloadButton>button{{border-radius:12px;font-weight:700;border:1.5px solid var(--line);background:#fff;color:var(--navy);padding:.55rem 1.1rem}}
.stButton>button:hover,.stDownloadButton>button:hover{{border-color:var(--blue);color:var(--blue)}}
.stButton>button[kind="primary"]{{background:var(--navy);color:#fff;border-color:var(--navy);height:3.05rem;font-size:1rem}}
.stButton>button[kind="primary"]:hover{{background:var(--blue);border-color:var(--blue);color:#fff}}
/* tabs */
.stTabs [data-baseweb="tab-list"]{{gap:.25rem;border-bottom:1px solid var(--line)}}
.stTabs [data-baseweb="tab"]{{height:2.7rem;padding:0 1rem;font-weight:700;color:var(--mute);border-radius:10px 10px 0 0}}
.stTabs [aria-selected="true"]{{color:var(--navy);background:#fff;border:1px solid var(--line);border-bottom-color:#fff}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{display:none}}
/* pipeline */
.pipe{{display:grid;grid-template-columns:1fr 26px 1.6fr 26px 1fr;align-items:stretch;gap:.2rem;margin:.4rem 0 .8rem}}
.pgroup{{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}}
.parrow{{align-self:center;text-align:center;color:var(--mute);font-weight:700}}
.pnode{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:.75rem .85rem;transition:all .25s}}
.pico{{display:inline-flex;width:28px;height:28px;border-radius:9px;align-items:center;justify-content:center;background:#E9EFFB;color:var(--navy);font-size:.95rem;margin-bottom:.35rem}}
.pname{{font-weight:800;font-size:.9rem}}
.pstat{{font-size:.76rem;color:var(--mute);min-height:1.1rem;margin-top:.1rem}}
.pnode.run{{border-color:var(--blue);box-shadow:0 0 0 3px rgba(47,91,255,.12)}}
.pnode.run .pico{{background:var(--amber);color:var(--ink);animation:ping 1.6s infinite}}
.pnode.done{{border-color:#9ADBC2}}
.pnode.done .pico{{background:var(--ok);color:#fff}}
.pnode.error{{border-color:#F0A3A6}}
.pnode.error .pico{{background:var(--bad);color:#fff}}
.log{{background:{INK};color:#BFD0FF;border-radius:14px;padding:.8rem 1rem;font:500 .78rem/1.65 'JetBrains Mono',monospace;max-height:210px;overflow:hidden}}
.log b{{color:#fff}} .log .t-err{{color:#FF9DA1}} .log .t-ok{{color:#7CE0B8}}
/* cards */
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1.1rem 1.25rem;margin-bottom:.8rem}}
.brief{{background:#fff;border:1px solid var(--line);border-left:5px solid var(--navy);border-radius:6px 16px 16px 6px;padding:1.3rem 1.6rem}}
.brief p{{font-family:'Newsreader',Georgia,serif;font-size:1.22rem;line-height:1.6;margin:0;max-width:78ch;color:var(--ink)}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:.7rem;margin:.9rem 0}}
.stat{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem}}
.stat b{{display:block;font-size:1.65rem;font-weight:800;letter-spacing:-.03em}}
.stat span{{font-size:.78rem;color:var(--mute)}}
.demo-banner{{background:#FFF6E0;border:1px solid #F5D78A;color:#6B4A00;border-radius:12px;padding:.6rem 1rem;font-size:.88rem;margin-bottom:.8rem}}
.badge{{display:inline-flex;align-items:center;gap:.35rem;border-radius:999px;padding:.12rem .6rem;font-size:.74rem;font-weight:800;white-space:nowrap}}
.badge:before{{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}}
.b-high{{background:#DDF6EC;color:#0A7A55}} .b-medium{{background:#FFF1D1;color:#8A5A00}} .b-low{{background:#FDE3E4;color:#B3262D}}
.pill{{display:inline-block;border-radius:8px;padding:.1rem .5rem;font-size:.72rem;font-weight:700;background:#E9EFFB;color:var(--navy)}}
.mono{{font-family:'JetBrains Mono',monospace;font-size:.76rem}}
.date{{font:500 .78rem 'JetBrains Mono',monospace;color:var(--mute)}}
/* timeline */
.tl{{position:relative;margin:.4rem 0 0 .6rem;padding-left:1.6rem;border-left:2px solid var(--line)}}
.tl-item{{position:relative;margin-bottom:1rem}}
.tl-item:before{{content:"";position:absolute;left:-2.07rem;top:1.15rem;width:12px;height:12px;border-radius:50%;background:#fff;border:3px solid var(--navy)}}
.tl-item.hi:before{{border-color:var(--amber);background:var(--amber)}}
.tl-head{{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin-bottom:.25rem}}
.tl-title{{font-weight:800;font-size:1.02rem}}
.desc{{font-family:'Newsreader',Georgia,serif;font-size:1.05rem;line-height:1.5;color:#1A2F5E;margin:.2rem 0 .5rem}}
/* citations */
details.cite{{margin-top:.2rem}}
details.cite summary{{cursor:pointer;font-size:.8rem;font-weight:700;color:var(--blue);list-style:none}}
details.cite summary::-webkit-details-marker{{display:none}}
details.cite summary:before{{content:"▸ ";}}
details.cite[open] summary:before{{content:"▾ ";}}
.cite-list{{margin-top:.5rem;display:grid;gap:.5rem}}
.cite-item{{background:#F4F7FD;border:1px solid var(--line);border-radius:10px;padding:.55rem .75rem;font-size:.84rem}}
.cite-item a{{color:var(--navy);font-weight:700;text-decoration:underline;text-decoration-color:#9DB6FF}}
.cite-item q{{display:block;margin-top:.3rem;font-family:'Newsreader',Georgia,serif;font-size:.98rem;font-style:italic;color:#34487A;quotes:none}}
.cid{{font:500 .74rem 'JetBrains Mono',monospace;background:var(--navy);color:#fff;border-radius:6px;padding:.05rem .4rem;margin-right:.35rem}}
.meter{{height:6px;border-radius:99px;background:#E4EAF7;overflow:hidden;margin:.55rem 0 .3rem}}
.meter i{{display:block;height:100%;background:linear-gradient(90deg,var(--blue),#22B8F0)}}
/* swot */
.sw{{border-radius:16px;padding:1rem 1.15rem;margin-bottom:.8rem;border:1px solid var(--line);background:#fff;border-top:5px solid var(--navy)}}
.sw h4{{margin:.1rem 0 .6rem;font-size:1rem}}
.sw.s{{border-top-color:#0E9F6E}} .sw.w{{border-top-color:#D6454B}} .sw.o{{border-top-color:#2F5BFF}} .sw.t{{border-top-color:#FFB020}}
.sw li{{margin-bottom:.7rem;font-size:.95rem;line-height:1.45;list-style:none}}
.sw ul{{padding:0;margin:0}}
/* conflicts */
.conf{{background:#fff;border:1px solid #F0D9A8;border-left:5px solid var(--amber);border-radius:6px 16px 16px 6px;padding:1rem 1.2rem;margin-bottom:.8rem}}
.conf.ok{{border-color:#BFE6D5;border-left-color:var(--ok)}}
.vs{{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:.6rem 0}}
.vs div{{background:#F4F7FD;border-radius:10px;padding:.6rem .8rem;font-size:.9rem}}
.threat{{display:inline-block;border-radius:8px;padding:.1rem .55rem;font-size:.74rem;font-weight:800}}
.t-high{{background:#FDE3E4;color:#B3262D}} .t-medium{{background:#FFF1D1;color:#8A5A00}} .t-low{{background:#DDF6EC;color:#0A7A55}}
.sample{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;margin-bottom:.5rem}}
@media(max-width:820px){{.stats{{grid-template-columns:repeat(2,1fr)}}.pipe{{grid-template-columns:1fr}}.parrow{{display:none}}.vs{{grid-template-columns:1fr}}.hero{{padding:1.5rem}}.hero h1{{font-size:1.8rem}}}}
</style>"""


def hero(demo_hint: str = "") -> str:
    return (f'<div class="hero">{logo("#FFFFFF", 38, dot=AMBER)}'
            f'<h1>Know what your competitor is doing before they announce it.</h1>'
            f'<p>Enter a company. Scout sends four researchers across news, company data, product releases and public sentiment, '
            f'then a critic checks every claim against its source and flags where the evidence disagrees.</p>'
            f'<div class="chips"><span class="chip"><span class="beacon"></span>Every claim cited</span>'
            f'<span class="chip">Quotes verified against fetched pages</span><span class="chip">Conflicts flagged, not hidden</span></div></div>')


def badge(conf: str, score: float | None = None) -> str:
    txt = conf.capitalize() + (f" · {round(score*100)}%" if score is not None else "")
    return f'<span class="badge b-{esc(conf)}">{esc(txt)}</span>'


def cites(ids: list[str], fmap: dict) -> str:
    items = []
    for i in ids:
        f = fmap.get(i)
        if not f:
            continue
        title = f.get("source_title") or domain_of(f["source_url"])
        flag = "" if f.get("grounding", 0) >= 0.8 else ' <span class="badge b-low">quote not fully verified</span>'
        items.append(
            f'<div class="cite-item"><span class="cid">{esc(i)}</span>'
            f'<a href="{esc(f["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(title)}</a> '
            f'<span class="date">{esc(domain_of(f["source_url"]))} · {esc(f.get("date") or "undated")}</span> '
            f'{badge(f["confidence"], f.get("score"))}{flag}<q>“{esc(f["snippet"])}”</q></div>')
    if not items:
        return ""
    n = len(items)
    return f'<details class="cite"><summary>{n} source{"s" if n != 1 else ""}</summary><div class="cite-list">{"".join(items)}</div></details>'


def pipeline_html(states: dict) -> str:
    def node(k: str) -> str:
        label, icon, tip = ROLE_INFO[k]
        s = states[k]
        return (f'<div class="pnode {s["state"]}"><div class="pico">{icon}</div><div class="pname">{esc(label)}</div>'
                f'<div class="pstat">{esc(s["msg"] or tip)}</div></div>')
    return (f'<div class="pipe">{node("planner")}<div class="parrow">→</div>'
            f'<div class="pgroup">{"".join(node(k) for k in ("news","company","product","social"))}</div>'
            f'<div class="parrow">→</div>{node("critic")}</div>')


def log_html(lines: list[dict]) -> str:
    out = []
    for ev in lines:
        cls = "t-err" if ev["status"] in ("error", "warn") else "t-ok" if ev["status"] == "done" else ""
        out.append(f'<div class="{cls}"><b>{esc(ev["node"])}</b> › {esc(ev["msg"])}</div>')
    return f'<div class="log">{"".join(out) or "<div>waiting…</div>"}</div>'


def stats_html(s: dict) -> str:
    cells = [(s["findings"], "cited findings"), (s["sources"], "distinct sources"),
             (f'{s["grounded_pct"]}%', "quotes verified in source"), (f'{s["avg_confidence"]}%', "average confidence"),
             (s["contradictions"], "conflicts flagged")]
    return '<div class="stats">' + "".join(f'<div class="stat"><b>{esc(v)}</b><span>{esc(l)}</span></div>' for v, l in cells) + "</div>"


def brief_html(text: str) -> str:
    return f'<div class="brief"><p>{esc(text)}</p></div>'


def timeline_html(items: list[dict], fmap: dict) -> str:
    if not items:
        return '<div class="card">No dated moves with verified evidence were found.</div>'
    out = []
    for t in items:
        hi = " hi" if t.get("confidence") == "high" and t.get("category") in ("funding", "acquisition", "partnership") else ""
        out.append(
            f'<div class="tl-item{hi}"><div class="card"><div class="tl-head"><span class="date">{esc(t.get("date") or "undated")}</span>'
            f'<span class="tl-title">{esc(t["title"])}</span><span class="pill">{esc(t.get("category", "other"))}</span>'
            f'{badge(t["confidence"], t["score"])}</div><div class="desc">{esc(t.get("description", ""))}</div>'
            f'{cites(t["evidence_ids"], fmap)}</div></div>')
    return f'<div class="tl">{"".join(out)}</div>'


def strategy_html(items: list[dict], fmap: dict) -> str:
    if not items:
        return '<div class="card">Evidence was not strong enough to infer a strategy.</div>'
    out = []
    for x in items:
        out.append(
            f'<div class="card"><div class="tl-head">{badge(x["confidence"], x["score"])}</div>'
            f'<div class="tl-title" style="font-weight:700;font-size:1.05rem">{esc(x["statement"])}</div>'
            f'<div class="meter"><i style="width:{round(x["score"]*100)}%"></i></div>{cites(x["evidence_ids"], fmap)}</div>')
    return "".join(out)


def swot_html(items: list[dict], title: str, cls: str, fmap: dict) -> str:
    lis = "".join(f'<li><div>{esc(x["point"])}</div><div>{badge(x["confidence"])}</div>{cites(x["evidence_ids"], fmap)}</li>' for x in items)
    return f'<div class="sw {cls}"><h4>{esc(title)}</h4><ul>{lis or "<li>No supported points.</li>"}</ul></div>'


def competitors_html(items: list[dict], fmap: dict) -> str:
    if not items:
        return '<div class="card">No competitors were named in the evidence.</div>'
    out = []
    for c in items:
        lvl = str(c.get("threat_level", "medium")).lower()
        lvl = lvl if lvl in ("high", "medium", "low") else "medium"
        out.append(f'<div class="card"><div class="tl-head"><span class="tl-title">{esc(c["name"])}</span>'
                   f'<span class="threat t-{lvl}">{lvl} threat</span>{badge(c["confidence"], c["score"])}</div>'
                   f'<div class="desc">{esc(c.get("rationale", ""))}</div>{cites(c["evidence_ids"], fmap)}</div>')
    return "".join(out)


def conflicts_html(items: list[dict], fmap: dict) -> str:
    if not items:
        return '<div class="card">No conflicting evidence was detected across sources.</div>'
    out = []
    for c in items:
        ok = c["status"] == "resolved"
        vs = "".join(f'<div><span class="cid">{esc(x["evidence_id"])}</span>{esc(x["claim"])}</div>' for x in c["claims"][:4])
        out.append(f'<div class="conf {"ok" if ok else ""}"><div class="tl-head"><span class="tl-title">{esc(c["topic"])}</span>'
                   f'<span class="badge {"b-high" if ok else "b-medium"}">{"Resolved" if ok else "Unresolved"}</span></div>'
                   f'<div class="vs">{vs}</div><div class="desc"><b>Assessment.</b> {esc(c.get("resolution", ""))}</div>'
                   f'{cites(c["evidence_ids"], fmap)}</div>')
    return "".join(out)
