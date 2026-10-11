from __future__ import annotations

import re
from typing import Iterable

from .utils import domain_of, months_ago

BASE = {"high": 0.85, "medium": 0.60, "low": 0.35}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9$%.]+", " ", (text or "").lower())).strip()


def grounding(snippet: str, source_text: str) -> float:
    """How much of the snippet literally appears in the retrieved source text (0..1).

    1.0 means the normalised snippet is a verbatim substring of the source.
    Otherwise falls back to the fraction of snippet tokens found in the source.
    This is Scout's citation check: the model may only cite text we actually retrieved.
    """
    ns, nt = _norm(snippet), _norm(source_text)
    if not ns or not nt:
        return 0.0
    if ns in nt:
        return 1.0
    toks = ns.split()
    src = set(nt.split())
    hit = sum(1 for t in toks if t in src)
    # Token overlap alone can be gamed by common words; require a contiguous 4-gram too.
    grams = {" ".join(toks[i : i + 4]) for i in range(max(len(toks) - 3, 1))}
    gram_hit = any(g in nt for g in grams)
    ratio = hit / len(toks)
    return round(ratio if gram_hit else min(ratio, 0.55), 3)


def finding_score(confidence: str, grounding_value: float, date: str | None) -> float:
    s = BASE.get(confidence, 0.6)
    if grounding_value >= 0.95:
        s += 0.05
    elif grounding_value < 0.8:
        s -= 0.25
    age = months_ago(date)
    if age is not None and age <= 18:
        s += 0.03
    elif age is not None and age > 36:
        s -= 0.05
    return round(max(0.05, min(0.98, s)), 3)


def item_score(findings: Iterable[dict]) -> tuple[float, str]:
    """Aggregate confidence for a claim backed by several findings."""
    fs = list(findings)
    if not fs:
        return 0.0, "low"
    mean = sum(f["score"] for f in fs) / len(fs)
    domains = {domain_of(f["source_url"]) for f in fs}
    if len(domains) >= 2:
        mean += min(0.04 * (len(domains) - 1), 0.10)   # corroboration across independent domains
    mean = round(max(0.05, min(0.98, mean)), 3)
    label = "high" if mean >= 0.75 else "medium" if mean >= 0.50 else "low"
    return mean, label
