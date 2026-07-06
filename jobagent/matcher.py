"""Rank jobs against a profile.

Every job gets a fast keyword-overlap score (works with zero LLM). If an LLM is
reachable, the top candidates are re-scored with reasoning and the two scores
are blended. This means the ranker degrades gracefully: no model, no problem —
you just lose the natural-language "why".
"""

from __future__ import annotations

from .llm import LLMClient, LLMError
from .models import Job, MatchResult, Profile

_RERANK_SYSTEM = (
    "You are a career coach scoring how well a candidate fits a job. Given the "
    "candidate profile and a job description, return JSON with: score (0-100 "
    "integer), reasons (array of <=3 short strings on why it fits), concerns "
    "(array of <=3 short strings on gaps or risks). Be honest, not flattering."
)


def keyword_score(profile: Profile, job: Job) -> float:
    terms = profile.search_terms()
    if not terms:
        return 0.0
    haystack = f"{job.title} {job.description} {job.location}".lower()
    hits = sum(1 for t in terms if t in haystack)
    # Title matches are worth extra.
    title = job.title.lower()
    title_hits = sum(1 for t in terms if t in title)
    raw = (hits / len(terms)) * 80 + min(title_hits, 3) / 3 * 20
    return round(min(raw, 100.0), 1)


def rank(
    profile: Profile,
    jobs: list[Job],
    llm: LLMClient | None = None,
    llm_weight: float = 0.7,
    rerank_k: int = 8,
) -> list[MatchResult]:
    """Return jobs sorted best-first as MatchResult objects."""
    results = [
        MatchResult(job=j, score=keyword_score(profile, j), method="keyword") for j in jobs
    ]
    results.sort(key=lambda r: r.score, reverse=True)

    use_llm = llm is not None and llm.available
    if use_llm:
        for r in results[:rerank_k]:
            try:
                verdict = llm.chat_json(_RERANK_SYSTEM, _rerank_prompt(profile, r.job))
            except LLMError:
                continue
            llm_val = _clamp(verdict.get("score", r.score))
            r.score = round(llm_weight * llm_val + (1 - llm_weight) * r.score, 1)
            r.reasons = [str(x) for x in verdict.get("reasons", [])][:3]
            r.concerns = [str(x) for x in verdict.get("concerns", [])][:3]
            r.method = "keyword+llm"
        results.sort(key=lambda r: r.score, reverse=True)

    return results


def _rerank_prompt(profile: Profile, job: Job) -> str:
    return (
        f"CANDIDATE\nHeadline: {profile.headline}\n"
        f"Skills: {', '.join(profile.skills) or 'n/a'}\n"
        f"Years: {profile.years_experience}\nSummary: {profile.summary[:600]}\n\n"
        f"JOB\nTitle: {job.title}\nCompany: {job.company}\n"
        f"Location: {job.location}\nDescription: {job.description[:1500]}"
    )


def _clamp(value) -> float:
    try:
        return max(0.0, min(float(value), 100.0))
    except (TypeError, ValueError):
        return 0.0
