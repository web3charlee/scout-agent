from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Role = Literal["news", "company", "product", "social"]
Confidence = Literal["high", "medium", "low"]

ROLES: list[str] = ["news", "company", "product", "social"]
CATEGORIES = [
    "funding", "product", "hiring", "partnership", "acquisition", "leadership",
    "pricing", "market", "sentiment", "legal", "other",
]


class Question(BaseModel):
    id: str
    question: str
    role: Role
    priority: int = 2


class Plan(BaseModel):
    company: str
    domain: str = ""
    questions: list[Question]


class Finding(BaseModel):
    id: str
    role: str
    question_id: str = ""
    claim: str
    source_url: str
    source_title: str = ""
    snippet: str
    date: Optional[str] = None
    confidence: Confidence = "medium"
    category: str = "other"
    grounding: float = 0.0   # share of snippet that is literally present in the fetched source
    score: float = 0.0       # 0..1 numeric confidence after scoring

    @property
    def grounded(self) -> bool:
        return self.grounding >= 0.8
