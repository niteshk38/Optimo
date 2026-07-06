"""High-level orchestration shared by the CLI and the Streamlit app.

Nothing here is UI-specific: build sources from config, fetch, de-duplicate,
and rank. Keeping this layer thin and framework-free is what lets the same core
power both interfaces.
"""

from __future__ import annotations

import re

from .config import Config
from .llm import LLMClient
from .matcher import rank
from .models import Job, MatchResult, Profile
from .sources import REGISTRY, JobSource


def _dedup_key(job: Job) -> str:
    """Collapse the *same* role across portals. LinkedIn/Indeed/Instahyre give a
    job different URLs, so URL alone misses cross-source duplicates — key on the
    normalized title + company instead (falling back to URL when no company)."""
    title = re.sub(r"[^a-z0-9 ]", "", (job.title or "").lower())
    title = re.sub(r"\s+", " ", title).strip()
    if job.company:
        company = re.sub(r"\s+", " ", job.company.lower()).strip()
        return f"{title}@{company}"
    return (job.url or title).lower()


def build_llm(config: Config) -> LLMClient:
    return LLMClient(
        base_url=config.llm.get("base_url", "http://localhost:11434/v1"),
        model=config.llm.get("model", "llama3.1"),
        api_key=config.secrets.get("llm_api_key") or None,
    )


def build_sources(config: Config) -> list[JobSource]:
    sources: list[JobSource] = []
    for name, cls in REGISTRY.items():
        cfg = config.sources.get(name, {})
        src = cls(config=cfg, secrets=config.secrets)
        if src.enabled:
            sources.append(src)
    return sources


def fetch_jobs(
    config: Config,
    query: str,
    location: str | None = None,
    remote: bool | None = None,
    limit_per_source: int = 25,
) -> list[Job]:
    seen: set[str] = set()
    jobs: list[Job] = []
    for src in build_sources(config):
        try:
            found = src.search(query, location=location, remote=remote, limit=limit_per_source)
        except Exception:  # a flaky source should never sink the whole run
            found = []
        for job in found:
            key = _dedup_key(job)
            # Sources are fetched richest-first (jsearch before websearch), so
            # first-wins keeps the entry with a real description over a link-only one.
            if key not in seen and job.title:
                seen.add(key)
                jobs.append(job)
    return jobs


def search_and_rank(
    config: Config,
    profile: Profile,
    query: str,
    location: str | None = None,
    remote: bool | None = None,
    use_llm: bool = True,
    limit_per_source: int = 25,
) -> list[MatchResult]:
    jobs = fetch_jobs(config, query, location, remote, limit_per_source)
    llm = build_llm(config) if use_llm else None
    return rank(
        profile,
        jobs,
        llm=llm,
        llm_weight=float(config.matcher.get("llm_weight", 0.7)),
        rerank_k=int(config.matcher.get("rerank_k", 8)),
    )
