from __future__ import annotations

import html
import re
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import urlparse


class BudgetExceeded(RuntimeError):
    """Raised when a run hits its LLM/search call ceiling (runaway-loop protection)."""


class Budget:
    def __init__(self, max_llm: int = 40, max_search: int = 60):
        self.max_llm = max_llm
        self.max_search = max_search
        self.llm = 0
        self.search = 0
        self._lock = threading.Lock()

    def use_llm(self) -> None:
        with self._lock:
            if self.llm >= self.max_llm:
                raise BudgetExceeded(f"LLM call budget reached ({self.max_llm}).")
            self.llm += 1

    def use_search(self) -> None:
        with self._lock:
            if self.search >= self.max_search:
                raise BudgetExceeded(f"Search call budget reached ({self.max_search}).")
            self.search += 1


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


_DATE_FORMATS = [
    ("%Y-%m-%d", "day"),
    ("%Y-%m-%dT%H:%M:%S", "day"),
    ("%Y/%m/%d", "day"),
    ("%B %d, %Y", "day"),
    ("%b %d, %Y", "day"),
    ("%d %B %Y", "day"),
    ("%d %b %Y", "day"),
    ("%Y-%m", "month"),
    ("%B %Y", "month"),
    ("%b %Y", "month"),
    ("%Y", "year"),
]


def parse_date(value) -> Optional[tuple[datetime, str]]:
    """Best-effort parse. Returns (naive datetime, precision) or None."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt, "day"
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt, "day"
    except (TypeError, ValueError, IndexError):
        pass
    for fmt, prec in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt), prec
        except ValueError:
            continue
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3])), "day"
        except ValueError:
            return None
    return None


def iso_date(value) -> Optional[str]:
    parsed = parse_date(value)
    if not parsed:
        return None
    dt, prec = parsed
    if prec == "year":
        return dt.strftime("%Y")
    if prec == "month":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y-%m-%d")


def months_ago(value) -> Optional[float]:
    parsed = parse_date(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc).replace(tzinfo=None) - parsed[0]).days / 30.4


def esc(text) -> str:
    """HTML-escape for st.markdown(unsafe_allow_html=True); also neutralises `$` (LaTeX)."""
    return html.escape(str(text if text is not None else ""), quote=True).replace("$", "&#36;")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "report"
