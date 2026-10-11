from __future__ import annotations

from typing import Callable

from ..llm import BaseLLM
from ..schemas import CATEGORIES, Finding, Question
from ..scoring import finding_score, grounding
from ..search import MultiSearch, SearchResult
from ..utils import iso_date
from .prompts import RESEARCHER_SYSTEM

ROLE_META = {
    "news": {
        "label": "News & Web", "topic": "news",
        "extra": ["{c} announcement", "{c} partnership acquisition launch", "{c} competitors alternatives"],
    },
    "company": {
        "label": "Company Data", "topic": "general",
        "extra": ["{c} funding raised investors", "{c} jobs careers hiring", "{c} about team founders pricing"],
    },
    "product": {
        "label": "Product & Tech", "topic": "general",
        "extra": ["{c} changelog release notes", "{c} github releases", "{c} product hunt launch"],
    },
    "social": {
        "label": "Social & Sentiment", "topic": "general",
        "extra": ["{c} reddit discussion", "{c} reviews g2 trustpilot", "{c} twitter x.com opinion"],
    },
}
DEPTH = {"quick": 3, "standard": 5, "deep": 7}
MAX_DOCS = {"quick": 8, "standard": 12, "deep": 16}

Emit = Callable[[dict], None]


def build_queries(role: str, company: str, domain: str, questions: list[Question], depth: str) -> list[str]:
    limit = DEPTH.get(depth, 5)
    qs: list[str] = []
    for q in sorted(questions, key=lambda x: x.priority)[:3]:
        qs.append(f"{company} {q.question}"[:180])
    for tpl in ROLE_META[role]["extra"]:
        qs.append(tpl.format(c=company))
    if role == "company" and domain:
        qs.insert(1, f"site:{domain} about careers")
    seen, out = set(), []
    for q in qs:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out[:limit]


def research(role: str, company: str, domain: str, questions: list[Question], llm: BaseLLM,
             search: MultiSearch, depth: str, emit: Emit) -> dict:
    meta = ROLE_META[role]
    emit({"node": role, "status": "start", "msg": f"{meta['label']} researcher started ({len(questions)} questions)"})

    docs: dict[str, SearchResult] = {}
    for query in build_queries(role, company, domain, questions, depth):
        emit({"node": role, "status": "search", "msg": query})
        for r in search.search(query, topic=meta["topic"], max_results=6, hint=role):
            docs.setdefault(r.url, r)
        if len(docs) >= MAX_DOCS.get(depth, 12):
            break
    doc_list = list(docs.values())[: MAX_DOCS.get(depth, 12)]

    if not doc_list:
        emit({"node": role, "status": "done", "msg": "No sources found", "count": 0})
        return {"findings": [], "gaps": [f"[{meta['label']}] No sources retrieved for: " + "; ".join(q.question for q in questions)],
                "dropped": 0}

    sources_txt = "\n\n".join(
        f"[{i+1}] {d.title}\nURL: {d.url}\nDate: {d.date or 'unknown'}\nText: {d.content[:1200]}"
        for i, d in enumerate(doc_list)
    )
    qs_txt = "\n".join(f"- {q.id}: {q.question}" for q in questions)
    emit({"node": role, "status": "reading", "msg": f"Reading {len(doc_list)} sources"})
    data = llm.complete_json(
        task=f"research:{role}", system=RESEARCHER_SYSTEM, fast=True, max_tokens=3500,
        user=f"Company: {company}\n\nAssigned questions:\n{qs_txt}\n\nSources:\n{sources_txt}",
    )

    valid_q = {q.id for q in questions}
    findings: list[Finding] = []
    dropped = 0
    prefix = role[0].upper()
    for item in data.get("findings", []) or []:
        try:
            idx = int(item.get("source")) - 1
            doc = doc_list[idx]
        except (TypeError, ValueError, IndexError):
            dropped += 1
            continue
        claim = str(item.get("claim") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if not claim or not snippet:
            dropped += 1
            continue
        g = grounding(snippet, f"{doc.title} {doc.content}")
        if g < 0.5:                     # citation not found in retrieved text -> reject
            dropped += 1
            continue
        conf = str(item.get("confidence", "medium")).lower()
        conf = conf if conf in ("high", "medium", "low") else "medium"
        if g < 0.8:
            conf = "low"
        cat = str(item.get("category", "other")).lower()
        date = iso_date(item.get("date")) or doc.date
        qid = str(item.get("question_id") or "")
        findings.append(Finding(
            id=f"{prefix}{len(findings)+1}", role=role,
            question_id=qid if qid in valid_q else questions[0].id,
            claim=claim, source_url=doc.url, source_title=doc.title, snippet=snippet,
            date=date, confidence=conf, category=cat if cat in CATEGORIES else "other",
            grounding=g, score=finding_score(conf, g, date),
        ))

    gaps = [f"[{meta['label']}] {g}" for g in (data.get("gaps") or []) if isinstance(g, str)]
    emit({"node": role, "status": "done", "count": len(findings),
          "msg": f"{len(findings)} cited findings" + (f", {dropped} rejected (unverifiable)" if dropped else "")})
    return {"findings": [f.model_dump() for f in findings], "gaps": gaps, "dropped": dropped}
