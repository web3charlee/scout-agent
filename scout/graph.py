"""LangGraph pipeline: Planner -> (parallel) Researchers -> Critic/Synthesizer."""
from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agents.critic import build_stats, synthesize
from .agents.planner import make_plan
from .agents.researchers import research
from .llm import BaseLLM
from .schemas import ROLES, Question
from .search import MultiSearch


class ScoutState(TypedDict, total=False):
    query: str
    plan: dict
    findings: Annotated[list, operator.add]
    gaps: Annotated[list, operator.add]
    dropped: Annotated[int, operator.add]
    report: dict


def build_graph(llm: BaseLLM, search: MultiSearch, emit: Callable[[dict], None] | None = None,
                depth: str = "standard", mode: str = "live"):
    emit = emit or (lambda e: None)

    def planner_node(state: ScoutState) -> dict:
        emit({"node": "planner", "status": "start", "msg": "Decomposing the question into a research plan"})
        plan, fallback = make_plan(state["query"], llm)
        emit({"node": "planner", "status": "done",
              "msg": f"{len(plan.questions)} research questions for {plan.company}" + (" (template plan)" if fallback else "")})
        return {"plan": plan.model_dump()}

    def fan_out(state: ScoutState):
        plan = state["plan"]
        sends = []
        for role in ROLES:
            qs = [q for q in plan["questions"] if q["role"] == role]
            if qs:
                sends.append(Send("research", {"role": role, "company": plan["company"], "domain": plan["domain"],
                                               "questions": qs}))
        return sends

    def research_node(payload: dict) -> dict:
        role = payload["role"]
        try:
            return research(role, payload["company"], payload["domain"],
                            [Question(**q) for q in payload["questions"]], llm, search, depth, emit)
        except Exception as e:  # one failing researcher must never sink the run
            emit({"node": role, "status": "error", "msg": f"{type(e).__name__}: {str(e)[:140]}"})
            return {"findings": [], "dropped": 0,
                    "gaps": [f"[{role}] researcher failed ({type(e).__name__}); its questions are unanswered."]}

    def critic_node(state: ScoutState) -> dict:
        findings = state.get("findings", [])
        plan = state["plan"]
        report = synthesize(plan["company"], findings, state.get("gaps", []), state.get("dropped", 0), llm, emit)
        report.update(
            company=plan["company"], domain=plan["domain"], query=state["query"],
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            mode=mode, depth=depth, llm=getattr(llm, "name", "llm"),
            plan=plan["questions"],
            findings=sorted(findings, key=lambda f: (f["role"], f["id"])),
        )
        report["stats"] = build_stats(findings, report)
        return {"report": report}

    g = StateGraph(ScoutState)
    g.add_node("planner", planner_node)
    g.add_node("research", research_node)
    g.add_node("critic", critic_node)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", fan_out, ["research"])
    g.add_edge("research", "critic")
    g.add_edge("critic", END)
    return g.compile()
