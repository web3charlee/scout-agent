from __future__ import annotations

import re

from ..llm import BaseLLM, LLMError
from ..schemas import ROLES, Plan, Question
from ..utils import domain_of
from .prompts import PLANNER_SYSTEM


def normalize_target(query: str) -> tuple[str, str]:
    """Turn a name / website / LinkedIn URL into (company name, domain)."""
    q = (query or "").strip()
    looks_like_url = bool(re.match(r"^(https?://|www\.)", q, re.I)) or bool(re.match(r"^[\w-]+(\.[\w-]+)+(/.*)?$", q))
    if not looks_like_url:
        return q, ""
    url = q if q.lower().startswith("http") else "https://" + q
    host = domain_of(url)
    if "linkedin.com" in host:
        m = re.search(r"/company/([^/?#]+)", url)
        name = m.group(1).replace("-", " ").title() if m else host
        return name, ""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac"}:
        label = parts[-3]
    elif len(parts) >= 2:
        label = parts[-2]
    else:
        label = host
    return label.replace("-", " ").title(), host


def fallback_questions(company: str) -> list[Question]:
    c = company
    spec = [
        ("news", f"What have been {c}'s most significant announcements, partnerships or acquisitions in the last 18 months?", 1),
        ("news", f"What legal, regulatory or reputational events have affected {c} recently?", 3),
        ("company", f"How much funding has {c} raised, from whom, and when?", 1),
        ("company", f"What do {c}'s job postings and leadership changes reveal about its priorities?", 2),
        ("product", f"What has {c} shipped recently (launches, changelog, releases) and what direction do they signal?", 1),
        ("product", f"What is {c}'s technology stack and developer-facing footprint?", 3),
        ("social", f"How do customers and the community perceive {c}, and what do they complain about?", 2),
        ("news", f"Who are {c}'s main competitors and how are they positioned against {c}?", 1),
    ]
    return [Question(id=f"q{i+1}", question=t, role=r, priority=p) for i, (r, t, p) in enumerate(spec)]


def make_plan(query: str, llm: BaseLLM) -> tuple[Plan, bool]:
    """Returns (plan, used_fallback)."""
    company, domain = normalize_target(query)
    used_fallback = False
    questions: list[Question] = []
    try:
        data = llm.complete_json(
            task="plan", system=PLANNER_SYSTEM, fast=True, max_tokens=1500,
            user=f"Company input: {query}\nResolved name: {company}\nWebsite: {domain or 'unknown'}",
        )
        company = (data.get("company") or company).strip() or company
        for i, q in enumerate(data.get("questions", [])[:8]):
            role = str(q.get("role", "")).lower()
            text = str(q.get("question", "")).strip()
            if role in ROLES and text:
                questions.append(Question(id=f"q{i+1}", question=text, role=role,
                                          priority=int(q.get("priority", 2) or 2)))
    except (LLMError, ValueError, TypeError, AttributeError):
        used_fallback = True

    if len(questions) < 5:
        used_fallback = True
        questions = fallback_questions(company)
    else:
        covered = {q.role for q in questions}
        for fq in fallback_questions(company):
            if fq.role not in covered and len(questions) < 8:
                questions.append(Question(id=f"q{len(questions)+1}", question=fq.question,
                                          role=fq.role, priority=fq.priority))
                covered.add(fq.role)
    return Plan(company=company, domain=domain, questions=questions), used_fallback
