"""Runs a Scout investigation in a worker thread and streams progress events (used by the UI and CLI)."""
from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Optional

from .config import get_settings
from .demo import COMPANY as DEMO_COMPANY, DemoLLM, DemoSearch
from .graph import build_graph
from .llm import FallbackLLM
from .search import MultiSearch
from .utils import Budget, slugify

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class ConfigError(RuntimeError):
    pass


def make_clients(mode: str):
    """Returns (llm, search). Live mode requires at least one LLM key and one search key."""
    if mode == "demo":
        return DemoLLM(), DemoSearch()
    s = get_settings()
    if not s.has_llm:
        raise ConfigError("Add ANTHROPIC_API_KEY or OPENAI_API_KEY to run live investigations.")
    if not s.has_search:
        raise ConfigError("Add TAVILY_API_KEY (or BRAVE_API_KEY / SERPER_API_KEY) to run live investigations.")
    budget = Budget(s.max_llm_calls, s.max_search_calls)
    return FallbackLLM.from_settings(s, budget), MultiSearch.from_settings(s, budget)


def save_report(report: dict) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = REPORTS_DIR / f"{slugify(report['company'])}-{report['mode']}-{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def list_reports() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def load_report(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ScoutRunner:
    def __init__(self, query: str, mode: str = "live", depth: str = "standard", persist: bool = True):
        self.query = DEMO_COMPANY if mode == "demo" else query.strip()
        self.mode, self.depth, self.persist = mode, depth, persist
        self.events: "queue.Queue[dict]" = queue.Queue()
        self.report: Optional[dict] = None
        self.error: Optional[str] = None
        self.saved_path: Optional[Path] = None
        self._thread: Optional[threading.Thread] = None
        self._done = threading.Event()

    def emit(self, ev: dict) -> None:
        ev.setdefault("t", time.time())
        self.events.put(ev)

    @property
    def finished(self) -> bool:
        return self._done.is_set()

    def start(self) -> "ScoutRunner":
        self._thread = threading.Thread(target=self._work, daemon=True)
        self._thread.start()
        return self

    def run_blocking(self) -> dict:
        self._work()
        if self.error:
            raise RuntimeError(self.error)
        return self.report  # type: ignore[return-value]

    def _work(self) -> None:
        try:
            llm, search = make_clients(self.mode)
            graph = build_graph(llm, search, self.emit, self.depth, self.mode)
            state = graph.invoke({"query": self.query, "findings": [], "gaps": [], "dropped": 0})
            self.report = state["report"]
            if getattr(search, "errors", None):
                self.report.setdefault("gaps", []).append(
                    "Search provider errors during the run: " + "; ".join(sorted(set(search.errors))[:3]))
            if self.persist:
                self.saved_path = save_report(self.report)
        except Exception as e:
            self.error = f"{type(e).__name__}: {e}"
            self.emit({"node": "system", "status": "error", "msg": self.error})
        finally:
            self.emit({"node": "system", "status": "finished", "msg": "done"})
            self._done.set()
