from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable

from ..llm import BaseLLM, LLMError
from ..scoring import item_score
from ..utils import domain_of, parse_date
from .prompts import CRITIC_SYSTEM

Emit = Callable[[dict], None]

_ROUND = re.compile(r"(pre-seed|seed|series\s+[a-f])", re.I)
_MONEY = re.compile(r"\$\s?(\d+(?:\.\d+)?)\s?(billion|million|thousand|bn|m|b|k)\b", re.I)
_MULT = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}


def _ids(raw, fmap) -> list[str]:
    seen, out = set(), []
    for i in raw or []:
        i = str(i).strip()
        if i in fmap and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _sort_key(item: dict):
    p = parse_date(item.get("date"))
    return (0, p[0]) if p else (1, datetime(2100, 1, 1))


def detect_numeric_conflicts(findings: list[dict]) -> list[dict]:
    """Safety net: same funding round reported with different amounts by different sources."""
    out = []
    funding = [f for f in findings if f["category"] == "funding"]
    for i, a in enumerate(funding):
        for b in funding[i + 1:]:
            ra, rb = _ROUND.search(a["claim"]), _ROUND.search(b["claim"])
            ma, mb = _MONEY.search(a["claim"]), _MONEY.search(b["claim"])
            if not (ra and rb and ma and mb):
                continue
            if ra.group(1).lower() != rb.group(1).lower() or domain_of(a["source_url"]) == domain_of(b["source_url"]):
                continue
            va = float(ma.group(1)) * _MULT[ma.group(2).lower()]
            vb = float(mb.group(1)) * _MULT[mb.group(2).lower()]
            if abs(va - vb) / max(va, vb) > 0.05:
                out.append({
                    "topic": f"{ra.group(1).title()} amount differs between sources",
                    "evidence_ids": [a["id"], b["id"]],
                    "claims": [{"evidence_id": a["id"], "claim": a["claim"]},
                               {"evidence_id": b["id"], "claim": b["claim"]}],
                    "resolution": "Auto-detected numeric mismatch. Prefer the primary source and verify manually.",
                    "status": "unresolved",
                })
    return out


def _format_findings(findings: list[dict]) -> str:
    lines = []
    for f in sorted(findings, key=lambda x: x["id"]):
        lines.append(
            f"[{f['id']}] ({f['confidence']}, {f['date'] or 'undated'}, {f['category']}, {domain_of(f['source_url'])}) "
            f"{f['claim']} — quote: \"{f['snippet']}\""
        )
    return "\n".join(lines)


def _fallback_report(findings: list[dict]) -> dict:
    """Deterministic report if the Critic LLM fails — still evidence-only, never invented."""
    fm = {f["id"]: f for f in findings}
    tl = [{"date": f["date"], "title": f["claim"], "description": f["snippet"], "category": f["category"],
           "evidence_ids": [f["id"]]} for f in findings if f["date"]]
    return {
        "executive_summary": "The synthesis step was unavailable, so this report lists verified findings without inference. "
                             "Review the timeline and the Evidence tab.",
        "timeline": tl, "strategy": [], "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "competitors": [], "contradictions": [], "gaps": ["Synthesis (Critic) step failed; strategy and SWOT were not generated."],
    }


def synthesize(company: str, findings: list[dict], gaps: list[str], dropped: int, llm: BaseLLM, emit: Emit) -> dict:
    emit({"node": "critic", "status": "start", "msg": f"Cross-checking {len(findings)} findings"})
    fmap = {f["id"]: f for f in findings}
    nested = {i: [f] for i, f in fmap.items()}   # for item_score(fmap[i] for i in ids) -> list of findings
    removed = 0

    if not findings:
        raw = {"executive_summary": f"Scout could not retrieve enough reliable public evidence about {company} to report on. "
                                    "No claims were made.", "gaps": ["No verifiable findings were produced."]}
    else:
        try:
            raw = llm.complete_json(task="critic", system=CRITIC_SYSTEM, max_tokens=6000,
                                    user=f"Company: {company}\n\nFindings:\n{_format_findings(findings)}\n\n"
                                         f"Known gaps from researchers:\n" + ("\n".join(f"- {g}" for g in gaps) or "- none"))
        except LLMError as e:
            emit({"node": "critic", "status": "warn", "msg": f"Synthesis failed, using evidence-only report ({e})"})
            raw = _fallback_report(findings)

    def attach_all(items, key="evidence_ids"):
        nonlocal removed
        out = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            it = dict(it)
            ids = _ids(it.get(key), fmap)
            if not ids:
                removed += 1
                continue
            score, label = item_score(nested[i][0] for i in ids)
            it.update(evidence_ids=ids, score=score, confidence=label)
            out.append(it)
        return out

    timeline = sorted(attach_all(raw.get("timeline")), key=_sort_key)
    strategy = attach_all(raw.get("strategy"))
    swot_raw = raw.get("swot") or {}
    swot = {k: attach_all(swot_raw.get(k)) for k in ("strengths", "weaknesses", "opportunities", "threats")}
    competitors = attach_all(raw.get("competitors"))

    contradictions = []
    for c in raw.get("contradictions") or []:
        if not isinstance(c, dict):
            continue
        claims = [x for x in (c.get("claims") or []) if isinstance(x, dict) and x.get("evidence_id") in fmap]
        ids = _ids(list(c.get("evidence_ids") or []) + [x["evidence_id"] for x in claims], fmap)
        if len(ids) < 2:
            removed += 1
            continue
        contradictions.append({
            "topic": str(c.get("topic") or "Conflicting evidence"), "evidence_ids": ids,
            "claims": claims or [{"evidence_id": i, "claim": fmap[i]["claim"]} for i in ids],
            "resolution": str(c.get("resolution") or ""),
            "status": "resolved" if str(c.get("status", "")).lower() == "resolved" else "unresolved",
        })
    covered = {frozenset(c["evidence_ids"]) for c in contradictions}
    for auto in detect_numeric_conflicts(findings):
        if not any(set(auto["evidence_ids"]) <= set(c) for c in covered):
            contradictions.append(auto)

    all_gaps = [str(g) for g in (raw.get("gaps") or []) if g] + [g for g in gaps if g]
    seen, uniq_gaps = set(), []
    for g in all_gaps:
        if g.lower() not in seen:
            seen.add(g.lower())
            uniq_gaps.append(g)

    report = {
        "executive_summary": str(raw.get("executive_summary") or "").strip(),
        "timeline": timeline, "strategy": strategy, "swot": swot, "competitors": competitors,
        "contradictions": contradictions, "gaps": uniq_gaps,
        "audit": {"rejected_at_retrieval": dropped, "removed_unsupported": removed},
    }
    emit({"node": "critic", "status": "done",
          "msg": f"Report ready · {len(contradictions)} conflicts flagged · {removed} unsupported claims removed"})
    return report


def build_stats(findings: list[dict], report: dict) -> dict:
    n = len(findings)
    by_role: dict[str, int] = {}
    for f in findings:
        by_role[f["role"]] = by_role.get(f["role"], 0) + 1
    return {
        "findings": n,
        "sources": len({f["source_url"] for f in findings}),
        "grounded_pct": round(100 * sum(1 for f in findings if f["grounding"] >= 0.8) / n) if n else 0,
        "avg_confidence": round(100 * sum(f["score"] for f in findings) / n) if n else 0,
        "contradictions": len(report.get("contradictions", [])),
        "by_role": by_role,
    }
