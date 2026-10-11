"""Search layer: Tavily (primary) -> Brave -> Serper, with timeouts, retries, rate limiting and caching."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional

import requests

from .config import Settings, get_settings
from .utils import Budget, iso_date


class SearchError(RuntimeError):
    pass


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    date: Optional[str] = None
    provider: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class Provider:
    name = "base"

    def __init__(self, key: str, timeout: int = 20):
        self.key = key
        self.timeout = timeout

    def search(self, query: str, max_results: int, topic: str) -> list[SearchResult]:  # pragma: no cover
        raise NotImplementedError


class Tavily(Provider):
    name = "tavily"

    def search(self, query, max_results, topic):
        body = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "topic": "news" if topic == "news" else "general",
            "include_answer": False,
        }
        if topic == "news":
            body["days"] = 540  # ~18 months
        r = requests.post(
            "https://api.tavily.com/search",
            json=body,
            headers={"Authorization": f"Bearer {self.key}"},
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise SearchError(f"tavily {r.status_code}: {r.text[:120]}")
        out = []
        for it in r.json().get("results", []):
            out.append(SearchResult(
                title=it.get("title") or "",
                url=it.get("url") or "",
                content=it.get("content") or "",
                date=iso_date(it.get("published_date")),
                provider=self.name,
            ))
        return out


class Brave(Provider):
    name = "brave"

    def search(self, query, max_results, topic):
        path = "news/search" if topic == "news" else "web/search"
        r = requests.get(
            f"https://api.search.brave.com/res/v1/{path}",
            params={"q": query, "count": max_results},
            headers={"X-Subscription-Token": self.key, "Accept": "application/json"},
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise SearchError(f"brave {r.status_code}: {r.text[:120]}")
        data = r.json()
        items = data.get("results") if topic == "news" else (data.get("web") or {}).get("results", [])
        out = []
        for it in items or []:
            out.append(SearchResult(
                title=it.get("title") or "",
                url=it.get("url") or "",
                content=it.get("description") or "",
                date=iso_date(it.get("page_age") or it.get("age")),
                provider=self.name,
            ))
        return out


class Serper(Provider):
    name = "serper"

    def search(self, query, max_results, topic):
        endpoint = "news" if topic == "news" else "search"
        r = requests.post(
            f"https://google.serper.dev/{endpoint}",
            json={"q": query, "num": max_results},
            headers={"X-API-KEY": self.key, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise SearchError(f"serper {r.status_code}: {r.text[:120]}")
        data = r.json()
        items = data.get("news") if topic == "news" else data.get("organic")
        out = []
        for it in items or []:
            out.append(SearchResult(
                title=it.get("title") or "",
                url=it.get("link") or "",
                content=it.get("snippet") or "",
                date=iso_date(it.get("date")),
                provider=self.name,
            ))
        return out


class MultiSearch:
    """Tries providers in order; remembers which ones are failing so a dead API doesn't slow every query."""

    def __init__(self, providers: list[Provider], budget: Budget | None = None,
                 min_interval: float = 0.12, retries: int = 1):
        if not providers:
            raise SearchError("No search provider configured (set TAVILY_API_KEY, BRAVE_API_KEY or SERPER_API_KEY).")
        self.providers = providers
        self.budget = budget or Budget()
        self.min_interval = min_interval
        self.retries = retries
        self._cache: dict[tuple, list[SearchResult]] = {}
        self._lock = threading.Lock()
        self._last = 0.0
        self._failures: dict[str, int] = {}
        self.errors: list[str] = []

    @classmethod
    def from_settings(cls, s: Settings | None = None, budget: Budget | None = None) -> "MultiSearch":
        s = s or get_settings()
        providers: list[Provider] = []
        if s.tavily_api_key:
            providers.append(Tavily(s.tavily_api_key, s.search_timeout))
        if s.brave_api_key:
            providers.append(Brave(s.brave_api_key, s.search_timeout))
        if s.serper_api_key:
            providers.append(Serper(s.serper_api_key, s.search_timeout))
        return cls(providers, budget or Budget(s.max_llm_calls, s.max_search_calls))

    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()

    def search(self, query: str, *, topic: str = "general", max_results: int = 6, hint: str = "") -> list[SearchResult]:
        key = (query.lower().strip(), topic, max_results)
        if key in self._cache:
            return self._cache[key]
        self.budget.use_search()
        last_err = None
        for p in self.providers:
            if self._failures.get(p.name, 0) >= 3:   # circuit breaker
                continue
            for attempt in range(self.retries + 1):
                try:
                    self._throttle()
                    res = [r for r in p.search(query, max_results, topic) if r.url]
                    self._failures[p.name] = 0
                    if res:
                        self._cache[key] = res
                        return res
                    break  # empty result: try next provider
                except (requests.RequestException, SearchError, ValueError) as e:
                    last_err = f"{p.name}: {e}"
                    self._failures[p.name] = self._failures.get(p.name, 0) + 1
                    time.sleep(0.6 * (attempt + 1))
        if last_err:
            self.errors.append(last_err)
        self._cache[key] = []
        return []
