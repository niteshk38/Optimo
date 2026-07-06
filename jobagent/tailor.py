"""Capability 2: tailor an application to a specific job.

These require an LLM (local Ollama is fine). Both functions ground the model in
the candidate's real resume and the actual job text, and instruct it not to
fabricate experience — the point is to reframe what's true, not invent.
"""

from __future__ import annotations

from .llm import LLMClient
from .models import Job, Profile

_COVER_SYSTEM = (
    "You write concise, specific cover letters. Use only facts present in the "
    "candidate's resume; never invent employers, titles, or achievements. Keep it "
    "under 250 words, warm but professional, and tie concrete resume points to the "
    "job's stated needs. No cliches like 'I am writing to express'."
)

_BULLETS_SYSTEM = (
    "You rewrite resume bullet points to target a specific job. Return JSON with a "
    "single key 'bullets' whose value is an array of <=5 rewritten bullet strings. "
    "Each starts with a strong verb, quantifies impact where the resume supports it, "
    "and mirrors the job's language. Do not invent metrics or responsibilities."
)


def cover_letter(profile: Profile, job: Job, llm: LLMClient) -> str:
    user = (
        f"JOB\nTitle: {job.title}\nCompany: {job.company}\n"
        f"Description:\n{job.description[:2500]}\n\n"
        f"CANDIDATE RESUME\n{profile.raw_text[:4000] or profile.summary}"
    )
    return llm.chat(_COVER_SYSTEM, user, temperature=0.5).strip()


def tailored_bullets(profile: Profile, job: Job, llm: LLMClient) -> list[str]:
    user = (
        f"JOB\nTitle: {job.title}\nDescription:\n{job.description[:2000]}\n\n"
        f"CANDIDATE RESUME\n{profile.raw_text[:4000] or profile.summary}"
    )
    data = llm.chat_json(_BULLETS_SYSTEM, user, temperature=0.4)
    return [str(b).strip() for b in data.get("bullets", []) if str(b).strip()]
