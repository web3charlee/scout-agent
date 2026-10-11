from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional .env support
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    openai_api_key: str
    tavily_api_key: str
    brave_api_key: str
    serper_api_key: str
    model: str
    fast_model: str
    openai_model: str
    max_llm_calls: int
    max_search_calls: int
    search_timeout: int = 20
    llm_timeout: int = 90

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def has_search(self) -> bool:
        return bool(self.tavily_api_key or self.brave_api_key or self.serper_api_key)

    @property
    def live_ready(self) -> bool:
        return self.has_llm and self.has_search


def get_settings() -> Settings:
    """Read settings at call time so Streamlit secrets copied into env are honoured."""
    g = os.environ.get
    return Settings(
        anthropic_api_key=g("ANTHROPIC_API_KEY", "").strip(),
        openai_api_key=g("OPENAI_API_KEY", "").strip(),
        tavily_api_key=g("TAVILY_API_KEY", "").strip(),
        brave_api_key=g("BRAVE_API_KEY", "").strip(),
        serper_api_key=g("SERPER_API_KEY", "").strip(),
        model=g("SCOUT_MODEL", "claude-sonnet-5-5").strip(),
        fast_model=g("SCOUT_FAST_MODEL", "claude-haiku-4-5-20251001").strip(),
        openai_model=g("SCOUT_OPENAI_MODEL", "gpt-4o").strip(),
        max_llm_calls=_int("SCOUT_MAX_LLM_CALLS", 40),
        max_search_calls=_int("SCOUT_MAX_SEARCH_CALLS", 60),
    )
