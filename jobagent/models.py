"""Core data structures. Plain dataclasses to keep dependencies light."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    title: str
    company: str
    url: str
    source: str
    description: str = ""
    location: str = ""
    remote: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    posted_at: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.dedupe_key()

    def dedupe_key(self) -> str:
        """Stable id so the same posting from two runs collapses to one row."""
        basis = (self.url or f"{self.title}@{self.company}").strip().lower()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Profile:
    """The candidate. Built from a resume and/or explicit preferences."""

    name: str = ""
    headline: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    years_experience: float = 0.0
    raw_text: str = ""
    preferences: dict = field(default_factory=dict)

    def search_terms(self) -> list[str]:
        """Everything we can match a job against, lowercased and de-duplicated."""
        terms = list(self.skills) + list(self.preferences.get("keywords", []))
        return sorted({t.strip().lower() for t in terms if t and t.strip()})


@dataclass
class MatchResult:
    job: Job
    score: float  # 0..100
    reasons: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    method: str = "keyword"  # "keyword" or "keyword+llm"


@dataclass
class Application:
    job_id: str
    title: str
    company: str
    url: str
    status: str = "saved"  # saved -> applied -> interviewing -> offer / rejected
    notes: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    VALID_STATUSES = ("saved", "applied", "interviewing", "offer", "rejected")
