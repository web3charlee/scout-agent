"""Scout: competitive intelligence agent. Run with: streamlit run app.py"""
from __future__ import annotations

import json
import os
import queue
import time

import streamlit as st

st.set_page_config(page_title="Scout · Competitive Intelligence", page_icon="assets/logo.jpg", layout="wide",
                   initial_sidebar_state="expanded")

# Streamlit Cloud: copy secrets into the environment so scout.config sees them.
try:
    for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TAVILY_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY",
               "SCOUT_MODEL", "SCOUT_FAST_MODEL", "SCOUT_OPENAI_MODEL"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

from scout import ui  # noqa: E402
from scout.config import get_settings  # noqa: E402
from scout.export import to_markdown  # noqa: E402
from scout.runner import ScoutRunner, list_reports, load_report  # noqa: E402

st.markdown(ui.css(), unsafe_allow_html=True)
S = get_settings()
EXAMPLES = ["Stripe", "Notion", "Perplexity", "Linear"]


def fresh_states() -> dict:
    return {k: {"state": "idle", "msg": ""} for k in ui.ROLE_INFO}


def apply_event(states: dict, ev: dict) -> None:
    node, status = ev["node"], ev["status"]
    if node not in states:
        return
    if status in ("start", "search", "reading"):
        states[node] = {"state": "run", "msg": ev["msg"][:46]}
    elif status == "done":
        states[node] = {"state": "done", "msg": ev["msg"][:46]}
    elif status == "error":
        states[node] = {"state": "error", "msg": ev["msg"][:46]}


def set_query(name: str) -> None:
    st.session_state["query_in"] = name
    st.session_state["autorun"] = True


# ───────────────────────── sidebar ─────────────────────────
with st.sidebar:
    st.markdown(ui.logo(ui.NAVY, 30, dot=ui.AMBER), unsafe_allow_html=True)
    st.caption("Investigate. Connect. Recommend.")
    default_mode = 0 if S.live_ready else 1
    mode_label = st.radio("Mode", ["Live research", "Offline demo"], index=default_mode,
                          help="Live uses your API keys. Offline demo replays a synthetic company and needs no keys.")
    mode = "live" if mode_label == "Live research" else "demo"
    depth = st.select_slider("Depth", ["quick", "standard", "deep"], value="standard",
                             help="More queries and sources per researcher. Deep takes longer and costs more.")
    st.markdown("**Connections**")
    for label, ok in [("LLM", S.has_llm), ("Search", S.has_search)]:
        st.markdown(f'{"🟢" if ok else "⚪"} {label}: {"ready" if ok else "not configured"}')
    if mode == "live" and not S.live_ready:
        st.warning("Add API keys in `.env` or Streamlit secrets to run live. See the README.")
    st.divider()
    saved = list_reports()
    if saved:
        st.markdown("**Saved reports**")
        pick = st.selectbox("Open a report", [p.name for p in saved], label_visibility="collapsed")
        if st.button("Open report", use_container_width=True):
            st.session_state["report"] = load_report(next(p for p in saved if p.name == pick))
            st.session_state.pop("run_states", None)
    st.divider()
    st.caption("Built for the Open Agent Hackathon 2026 · Autonomous Intelligence track")

# ───────────────────────── input ─────────────────────────
st.markdown(ui.hero(), unsafe_allow_html=True)
c1, c2 = st.columns([5, 1.1], vertical_alignment="bottom")
with c1:
    query = st.text_input("Company", key="query_in", placeholder="Company name, website, or LinkedIn URL",
                          label_visibility="collapsed")
with c2:
    go = st.button("Investigate", type="primary", use_container_width=True)
autorun = st.session_state.pop("autorun", False)

st.caption("Try one: ")
ex_cols = st.columns(len(EXAMPLES) + 3)
for col, name in zip(ex_cols, EXAMPLES):
    col.button(name, key=f"ex_{name}", on_click=set_query, args=(name,), use_container_width=True)

# ───────────────────────── run ─────────────────────────
if go or autorun:
    if mode == "live" and not query.strip():
        st.warning("Enter a company name or URL first.")
    elif mode == "live" and not S.live_ready:
        st.error("Live research needs an LLM key and a search key. Switch to Offline demo or add keys (see README).")
    else:
        runner = ScoutRunner(query, mode, depth).start()
        states, log = fresh_states(), []
        st.markdown("#### Investigation")
        pipe_ph, log_ph = st.empty(), st.empty()
        while True:
            finished = runner.finished
            try:
                while True:
                    ev = runner.events.get_nowait()
                    if ev["status"] == "finished":
                        continue
                    apply_event(states, ev)
                    log.append(ev)
            except queue.Empty:
                pass
            pipe_ph.markdown(ui.pipeline_html(states), unsafe_allow_html=True)
            log_ph.markdown(ui.log_html(log[-9:]), unsafe_allow_html=True)
            if finished:
                break
            time.sleep(0.2)
        if runner.error:
            st.error(f"The run failed: {runner.error}. Check your keys and network, then try again.")
        else:
            st.session_state["report"] = runner.report
            st.session_state["run_states"] = states

# ───────────────────────── report ─────────────────────────
r = st.session_state.get("report")
if not r:
    st.markdown("#### How a report is built")
    a, b, c = st.columns(3)
    for col, (t, d) in zip((a, b, c), [
        ("Plan", "A planner turns your company into 5–8 research questions and assigns each to a specialist."),
        ("Investigate in parallel", "Four researchers search news, company data, product releases and public sentiment at the same time."),
        ("Cross-check", "A critic compares findings, flags conflicts, drops anything without a source, and scores confidence."),
    ]):
        col.markdown(f'<div class="card"><div class="tl-title">{t}</div><div class="desc">{d}</div></div>', unsafe_allow_html=True)
    if saved:
        st.markdown("#### Example reports")
        for p in saved[:4]:
            rep = load_report(p)
            stt = rep.get("stats", {})
            st.markdown(f'<div class="sample"><b>{ui.esc(rep["company"])}</b> '
                        f'<span class="pill">{ui.esc(rep["mode"])}</span> '
                        f'<span class="date">{ui.esc(rep["generated_at"])} · {stt.get("findings", 0)} findings · '
                        f'{stt.get("contradictions", 0)} conflicts</span></div>', unsafe_allow_html=True)
    st.stop()

fmap = {f["id"]: f for f in r["findings"]}
st.markdown("---")
h1, h2, h3 = st.columns([4, 1.2, 1.2], vertical_alignment="center")
with h1:
    st.markdown(f"## {r['company']}")
    st.markdown(f'<span class="date">{ui.esc(r["generated_at"])} · {ui.esc(r["mode"])} mode · {ui.esc(r["depth"])} depth · '
                f'{ui.esc(r["llm"])}</span>', unsafe_allow_html=True)
with h2:
    st.download_button("Download .md", to_markdown(r), file_name=f"scout-{r['company'].lower().replace(' ', '-')}.md",
                       mime="text/markdown", use_container_width=True)
with h3:
    st.download_button("Download .json", json.dumps(r, indent=2, ensure_ascii=False),
                       file_name=f"scout-{r['company'].lower().replace(' ', '-')}.json", mime="application/json",
                       use_container_width=True)
if r["mode"] == "demo":
    st.markdown('<div class="demo-banner"><b>Synthetic demo.</b> Northwind Labs is a fictional company and every source is a made-up '
                '<code>.example</code> URL. Switch to Live research for real intelligence.</div>', unsafe_allow_html=True)

tabs = st.tabs(["Overview", "Timeline", "Strategy", "SWOT", "Landscape", "Conflicts", "Evidence"])

with tabs[0]:
    st.markdown(ui.brief_html(r["executive_summary"]), unsafe_allow_html=True)
    st.markdown(ui.stats_html(r["stats"]), unsafe_allow_html=True)
    aud = r.get("audit", {})
    st.markdown(f'<div class="card"><b>Evidence audit.</b> <span class="desc">{aud.get("rejected_at_retrieval", 0)} researcher claims were '
                f'rejected because their quote was not found in the retrieved source, and {aud.get("removed_unsupported", 0)} synthesized '
                f'statements were removed because they cited no valid evidence.</span></div>', unsafe_allow_html=True)
    if r.get("gaps"):
        st.markdown("**What Scout could not establish**")
        for g in r["gaps"]:
            st.markdown(f"- {g.replace('$', chr(92) + '$')}")
    st.markdown("**Research plan**")
    for q in r.get("plan", []):
        label = ui.ROLE_INFO[q["role"]][0]
        st.markdown(f'<span class="pill">{ui.esc(label)}</span> {ui.esc(q["question"])}', unsafe_allow_html=True)

with tabs[1]:
    st.markdown(ui.timeline_html(r["timeline"], fmap), unsafe_allow_html=True)
with tabs[2]:
    st.markdown(ui.strategy_html(r["strategy"], fmap), unsafe_allow_html=True)
with tabs[3]:
    sw = r["swot"]
    ca, cb = st.columns(2)
    with ca:
        st.markdown(ui.swot_html(sw["strengths"], "Strengths", "s", fmap), unsafe_allow_html=True)
        st.markdown(ui.swot_html(sw["opportunities"], "Opportunities", "o", fmap), unsafe_allow_html=True)
    with cb:
        st.markdown(ui.swot_html(sw["weaknesses"], "Weaknesses", "w", fmap), unsafe_allow_html=True)
        st.markdown(ui.swot_html(sw["threats"], "Threats", "t", fmap), unsafe_allow_html=True)
with tabs[4]:
    st.markdown(ui.competitors_html(r["competitors"], fmap), unsafe_allow_html=True)
with tabs[5]:
    st.markdown(ui.conflicts_html(r["contradictions"], fmap), unsafe_allow_html=True)
with tabs[6]:
    f1, f2, f3 = st.columns([2, 2, 3])
    roles = f1.multiselect("Researcher", sorted({f["role"] for f in r["findings"]}), default=[])
    confs = f2.multiselect("Confidence", ["high", "medium", "low"], default=[])
    text = f3.text_input("Search findings", placeholder="e.g. funding")
    shown = [f for f in r["findings"]
             if (not roles or f["role"] in roles) and (not confs or f["confidence"] in confs)
             and (not text or text.lower() in (f["claim"] + f["snippet"] + f["category"]).lower())]
    st.caption(f"{len(shown)} of {len(r['findings'])} findings")
    for f in shown:
        with st.expander(f"[{f['id']}] {f['claim']}".replace("$", "\\$")):
            st.markdown(ui.cites([f["id"]], fmap), unsafe_allow_html=True)
            st.markdown(f'<span class="pill">{ui.esc(f["category"])}</span> <span class="pill">{ui.esc(f["role"])}</span> '
                        f'<span class="date">grounding {round(f["grounding"]*100)}% · score {round(f["score"]*100)}%</span>',
                        unsafe_allow_html=True)
