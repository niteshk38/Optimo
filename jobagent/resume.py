"""Turn a resume (plain text or PDF) into a Profile.

With an LLM configured, we extract a clean headline / skills / experience.
Without one, we fall back to a simple keyword heuristic so the ranker still has
signal to work with. Either way, explicit preferences from config are merged in.
"""

from __future__ import annotations

import re
from pathlib import Path

from .llm import LLMClient, LLMError
from .models import Profile

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "was", "were", "has",
    "have", "will", "from", "this", "that", "they", "their", "not", "but", "all",
    "who", "how", "why", "job", "role", "work", "team", "years", "experience",
}

_EXTRACT_SYSTEM = (
    "You extract structured data from resumes. Given the resume text, produce a "
    "JSON object with keys: headline (string, e.g. 'Senior Backend Engineer'), "
    "summary (2-sentence string), skills (array of concise skill strings), and "
    "years_experience (number). Be faithful to the resume; do not invent skills."
)


def read_resume(path: str | Path) -> str:
    """Read resume text from .txt/.md directly, or extract text from a .pdf."""
    path = Path(path)
    return read_resume_bytes(path.name, path.read_bytes())


def read_resume_bytes(filename: str, data: bytes) -> str:
    """Extract resume text from an uploaded file's bytes (.txt/.md/.pdf).

    Used by the web UI's file-attach widget, which hands us bytes rather than a
    path on disk.
    """
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install pypdf to read PDF resumes: pip install pypdf") from exc
        import io

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


def build_profile(
    raw_text: str = "",
    preferences: dict | None = None,
    llm: LLMClient | None = None,
) -> Profile:
    preferences = preferences or {}
    profile = Profile(raw_text=raw_text, preferences=preferences)

    if raw_text and llm is not None:
        try:
            data = llm.chat_json(_EXTRACT_SYSTEM, raw_text[:8000])
            profile.headline = str(data.get("headline", "")).strip()
            profile.summary = str(data.get("summary", "")).strip()
            profile.skills = [str(s).strip() for s in data.get("skills", []) if str(s).strip()]
            profile.years_experience = float(data.get("years_experience", 0) or 0)
            return profile
        except (LLMError, ValueError, TypeError):
            pass  # fall through to the heuristic

    if raw_text:
        profile.skills = _keyword_fallback(raw_text)
        profile.summary = raw_text.strip()[:280]
    return profile


def _keyword_fallback(text: str, top_n: int = 40) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}", text.lower())
    counts: dict[str, int] = {}
    for tok in tokens:
        if tok in _STOPWORDS:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]
