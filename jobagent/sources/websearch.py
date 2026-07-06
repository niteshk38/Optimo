"""Web search for job links from sites like Instahyre, LinkedIn, Naukri.

This replicates typing "role instahyre" into Google and collecting the links.
It uses a sanctioned search API — not scraping — so it's legitimate and works
for anyone who clones the repo. Two backends are supported, picked automatically:

  1. Serper (https://serper.dev) — a Google-search API with a free tier and a
     single key (SERPER_API_KEY). Preferred: no Google Cloud setup.
  2. Google Programmable Search / Custom Search JSON API — needs GOOGLE_CSE_KEY
     and GOOGLE_CSE_CX. Used only if no Serper key is set.

What you get back is what a search result gives you: a title, a link, and a
short snippet — no full job description or salary (that lives on the page, and
for LinkedIn often behind a login). So ranking on fit is weaker than for the
API sources; think of this as "the right links, by role."
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from ..models import Job
from .base import JobSource

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
SERPER_ENDPOINT = "https://google.serper.dev/search"


class WebSearchSource(JobSource):
    name = "websearch"

    @property
    def _has_serper(self) -> bool:
        return bool(self.secrets.get("serper_api_key"))

    @property
    def _has_cse(self) -> bool:
        return bool(self.secrets.get("google_cse_key") and self.secrets.get("google_cse_cx"))

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True) and (self._has_serper or self._has_cse))

    def search(self, query, location=None, remote=None, limit=25) -> list[Job]:
        if not self.enabled:
            return []
        # One query per configured site, using Google's `site:` operator so paths
        # like "linkedin.com/jobs" work. No sites -> a plain whole-web search.
        sites = self.config.get("sites") or [None]
        num = min(int(self.config.get("num", 10)), 10)
        loc = f" {location}" if location else ""

        jobs: list[Job] = []
        for site in sites:
            q = f"{query}{loc} site:{site}" if site else f"{query}{loc}"
            results = self._serper(q, num) if self._has_serper else self._cse(q, num)
            for title, link, snippet in results:
                domain = urlparse(link).netloc.replace("www.", "") if link else ""
                jobs.append(
                    Job(
                        title=title.strip(),
                        company="",  # not reliably available from a search snippet
                        url=link,
                        source=f"web:{domain}" if domain else "web",
                        description=snippet or "",
                        location=location or "",
                    )
                )
                if len(jobs) >= limit:
                    return jobs
        return jobs

    def _serper(self, q: str, num: int) -> list[tuple[str, str, str]]:
        """Serper.dev — POST with an X-API-KEY header. Returns (title, link, snippet)."""
        headers = {
            "X-API-KEY": self.secrets["serper_api_key"],
            "Content-Type": "application/json",
        }
        payload = {"q": q, "num": num}
        if self.config.get("gl"):
            payload["gl"] = self.config["gl"]  # country code, e.g. "in"
        try:
            resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            organic = resp.json().get("organic", []) or []
        except (requests.RequestException, ValueError):
            return []
        return [
            (it.get("title") or "", it.get("link") or "", it.get("snippet") or "")
            for it in organic
        ]

    def _cse(self, q: str, num: int) -> list[tuple[str, str, str]]:
        """Google Custom Search JSON API — GET with key + cx."""
        params = {
            "key": self.secrets["google_cse_key"],
            "cx": self.secrets["google_cse_cx"],
            "q": q,
            "num": num,
        }
        try:
            resp = requests.get(CSE_ENDPOINT, params=params, timeout=30)
            resp.raise_for_status()
            items = resp.json().get("items", []) or []
        except (requests.RequestException, ValueError):
            return []
        return [
            (it.get("title") or "", it.get("link") or "", it.get("snippet") or "")
            for it in items
        ]
