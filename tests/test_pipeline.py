import pytest

import scout.demo as demo
from scout.agents.critic import detect_numeric_conflicts
from scout.agents.planner import make_plan, normalize_target
from scout.export import to_markdown
from scout.graph import build_graph
from scout.llm import BaseLLM, LLMError, parse_json
from scout.runner import ScoutRunner
from scout.scoring import grounding
from scout.utils import Budget, BudgetExceeded, iso_date


@pytest.fixture(autouse=True)
def fast_demo(monkeypatch):
    monkeypatch.setattr(demo, "_sleep", lambda a: None)


def run_demo():
    return ScoutRunner("x", "demo", persist=False).run_blocking()


def test_demo_report_has_all_sections():
    r = run_demo()
    for k in ("executive_summary", "timeline", "strategy", "swot", "competitors", "contradictions", "gaps"):
        assert r[k]
    assert set(r["swot"]) == {"strengths", "weaknesses", "opportunities", "threats"}


def test_every_claim_cites_real_evidence():
    r = run_demo()
    ids = {f["id"] for f in r["findings"]}
    items = r["timeline"] + r["strategy"] + r["competitors"] + [x for v in r["swot"].values() for x in v]
    for it in items:
        assert it["evidence_ids"] and set(it["evidence_ids"]) <= ids
        assert 0 < it["score"] <= 1 and it["confidence"] in ("high", "medium", "low")
    for f in r["findings"]:
        assert f["source_url"] and f["snippet"] and f["confidence"] and f["grounding"] >= 0.8


def test_funding_conflict_is_flagged():
    r = run_demo()
    assert any({"N1", "C1"} <= set(c["evidence_ids"]) for c in r["contradictions"])


def test_numeric_conflict_safety_net():
    fs = [
        {"id": "A1", "category": "funding", "claim": "Raised a $15M Series A", "source_url": "https://a.example/x"},
        {"id": "B1", "category": "funding", "claim": "Closed an $18 million Series A", "source_url": "https://b.example/y"},
    ]
    assert detect_numeric_conflicts(fs)


class HallucinatingLLM(BaseLLM):
    """Researcher invents a quote and a source; critic cites an unknown ID. Scout must reject both."""
    name = "bad"

    def complete_json(self, *, task, system, user, fast=False, max_tokens=4000):
        if task.startswith("research:"):
            return {"findings": [
                {"source": 1, "claim": "Raised $500M", "snippet": "raised five hundred million dollars from sovereign funds",
                 "date": "2026-01-01", "confidence": "high", "category": "funding"},
                {"source": 99, "claim": "Ghost source", "snippet": "x", "confidence": "high", "category": "other"},
            ], "gaps": []}
        if task == "critic":
            return {"executive_summary": "s", "timeline": [{"date": "2026-01", "title": "t", "description": "d",
                    "category": "other", "evidence_ids": ["Z99"]}], "strategy": [], "swot": {}, "competitors": [],
                    "contradictions": [], "gaps": []}
        return demo.PLAN


def test_hallucinated_quotes_and_ids_are_rejected():
    llm = HallucinatingLLM()
    g = build_graph(llm, demo.DemoSearch(), None, "quick", "demo")
    r = g.invoke({"query": "x", "findings": [], "gaps": [], "dropped": 0})["report"]
    assert r["findings"] == []
    assert r["audit"]["rejected_at_retrieval"] >= 4
    assert r["timeline"] == []


class FailingLLM(BaseLLM):
    name = "fail"

    def complete_json(self, *, task, **kw):
        raise LLMError("boom")


def test_total_llm_outage_degrades_gracefully():
    g = build_graph(FailingLLM(), demo.DemoSearch(), None, "quick", "demo")
    r = g.invoke({"query": "Acme", "findings": [], "gaps": [], "dropped": 0})["report"]
    assert r["findings"] == [] and "could not retrieve" in r["executive_summary"].lower()
    assert any("failed" in g for g in r["gaps"])


def test_planner_fallback_covers_all_roles():
    plan, used = make_plan("Acme", FailingLLM())
    assert used and {q.role for q in plan.questions} == {"news", "company", "product", "social"}
    assert 5 <= len(plan.questions) <= 8


def test_normalize_target():
    assert normalize_target("https://www.stripe.com/pricing") == ("Stripe", "stripe.com")
    assert normalize_target("https://www.linkedin.com/company/acme-inc/")[0] == "Acme Inc"
    assert normalize_target("Open AI") == ("Open AI", "")


def test_grounding_and_parsing_helpers():
    assert grounding("raised a $15 million Series A", "Acme raised a $15 million series a round") == 1.0
    assert grounding("totally invented sentence here", "Acme raised money") < 0.5
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert iso_date("Mon, 02 Mar 2026 10:00:00 GMT") == "2026-03-02"


def test_budget_guard():
    b = Budget(max_llm=1, max_search=1)
    b.use_llm()
    with pytest.raises(BudgetExceeded):
        b.use_llm()


def test_markdown_export():
    md = to_markdown(run_demo())
    assert "## Executive summary" in md and "Synthetic demo" in md and "[N1]" in md


class BadCriticLLM(demo.DemoLLM):
    """Valid researchers, but the critic cites a non-existent ID and a one-sided 'contradiction'."""

    def complete_json(self, *, task, **kw):
        if task == "critic":
            return {"executive_summary": "ok",
                    "timeline": [{"date": "2026-01", "title": "ghost", "description": "d", "category": "other", "evidence_ids": ["Z99"]},
                                 {"date": "2026-02", "title": "real", "description": "d", "category": "other", "evidence_ids": ["N1", "Z99"]}],
                    "strategy": [], "swot": {}, "competitors": [],
                    "contradictions": [{"topic": "t", "evidence_ids": ["N1"], "claims": [], "resolution": "", "status": "resolved"}],
                    "gaps": []}
        return super().complete_json(task=task, **kw)


def test_critic_drops_unsupported_items():
    g = build_graph(BadCriticLLM(delay=0), demo.DemoSearch(delay=0), None, "quick", "demo")
    r = g.invoke({"query": "x", "findings": [], "gaps": [], "dropped": 0})["report"]
    assert [t["title"] for t in r["timeline"]] == ["real"] and r["timeline"][0]["evidence_ids"] == ["N1"]
    assert r["audit"]["removed_unsupported"] == 2
    assert any({"N1", "C1"} <= set(c["evidence_ids"]) for c in r["contradictions"])  # safety net still catches $15M vs $18M
