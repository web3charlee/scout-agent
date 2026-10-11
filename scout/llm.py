"""LLM layer: provider-agnostic JSON completions with retries, budget guard and automatic fallback."""
from __future__ import annotations

import json
import re
import time
from typing import Optional

from .config import Settings, get_settings
from .utils import Budget, BudgetExceeded


class LLMError(RuntimeError):
    pass


JSON_RULE = (
    "\n\nRespond with ONE valid JSON object and nothing else: no prose, no markdown fences."
)


def parse_json(text: str) -> dict:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(t[a : b + 1])
        except json.JSONDecodeError:
            pass
    raise LLMError("Model did not return valid JSON.")


class BaseLLM:
    name = "base"

    def complete_json(self, *, task: str, system: str, user: str, fast: bool = False,
                      max_tokens: int = 4000) -> dict:  # pragma: no cover
        raise NotImplementedError


class AnthropicLLM(BaseLLM):
    name = "anthropic"

    def __init__(self, s: Settings, budget: Budget):
        import anthropic

        self.client = anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=s.llm_timeout, max_retries=1)
        self.model, self.fast_model = s.model, s.fast_model
        self.budget = budget

    def complete_json(self, *, task, system, user, fast=False, max_tokens=4000):
        model = self.fast_model if fast else self.model
        last: Optional[Exception] = None
        for attempt in range(3):
            self.budget.use_llm()
            try:
                msg = self.client.messages.create(
                    model=model, max_tokens=max_tokens,
                    system=system + JSON_RULE,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(getattr(b, "text", "") for b in msg.content)
                return parse_json(text)
            except BudgetExceeded:
                raise
            except Exception as e:  # network, rate limit, bad JSON
                last = e
                time.sleep(1.2 * (attempt + 1))
        raise LLMError(f"anthropic[{task}] failed: {last}")


class OpenAILLM(BaseLLM):
    name = "openai"

    def __init__(self, s: Settings, budget: Budget):
        from openai import OpenAI

        self.client = OpenAI(api_key=s.openai_api_key, timeout=s.llm_timeout, max_retries=1)
        self.model = s.openai_model
        self.budget = budget

    def complete_json(self, *, task, system, user, fast=False, max_tokens=4000):
        last: Optional[Exception] = None
        for attempt in range(3):
            self.budget.use_llm()
            try:
                r = self.client.chat.completions.create(
                    model=self.model, temperature=0.1, max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system + JSON_RULE},
                              {"role": "user", "content": user}],
                )
                return parse_json(r.choices[0].message.content or "")
            except BudgetExceeded:
                raise
            except Exception as e:
                last = e
                time.sleep(1.2 * (attempt + 1))
        raise LLMError(f"openai[{task}] failed: {last}")


class FallbackLLM(BaseLLM):
    """Primary provider first; if it fails after retries, transparently try the next."""

    name = "fallback"

    def __init__(self, chain: list[BaseLLM]):
        if not chain:
            raise LLMError("No LLM provider configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY).")
        self.chain = chain
        self.name = "+".join(c.name for c in chain)

    def complete_json(self, **kw):
        errs = []
        for c in self.chain:
            try:
                return c.complete_json(**kw)
            except BudgetExceeded:
                raise
            except LLMError as e:
                errs.append(str(e))
        raise LLMError(" | ".join(errs))

    @classmethod
    def from_settings(cls, s: Settings | None = None, budget: Budget | None = None) -> "FallbackLLM":
        s = s or get_settings()
        budget = budget or Budget(s.max_llm_calls, s.max_search_calls)
        chain: list[BaseLLM] = []
        if s.anthropic_api_key:
            chain.append(AnthropicLLM(s, budget))
        if s.openai_api_key:
            chain.append(OpenAILLM(s, budget))
        return cls(chain)
