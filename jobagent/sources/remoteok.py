"""RemoteOK — public remote-jobs feed, no API key required.

Endpoint returns a JSON list whose first element is a legal/attribution notice;
we skip it. We fetch once and filter locally by the query terms.
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource

FEED = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    name = "remoteok"

    def search(self, query, location=None, remote=None, limit=25) -> list[Job]:
        if not self.enabled:
            return []
        try:
            resp = requests.get(
                FEED, headers={"User-Agent": "optimo (open source)"}, timeout=30
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError):
            return []

        terms = [t for t in query.lower().split() if t]
        jobs: list[Job] = []
        for r in payload:
            if not isinstance(r, dict) or "position" not in r:
                continue  # skips the leading legal-notice element
            haystack = " ".join(
                str(r.get(k, "")) for k in ("position", "company", "tags", "description")
            ).lower()
            if terms and not any(t in haystack for t in terms):
                continue
            jobs.append(
                Job(
                    title=r.get("position", "").strip(),
                    company=r.get("company", "").strip(),
                    url=r.get("url", ""),
                    source=self.name,
                    description=r.get("description", ""),
                    location=r.get("location") or "Remote",
                    remote=True,
                    salary_min=r.get("salary_min"),
                    salary_max=r.get("salary_max"),
                    posted_at=r.get("date"),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs
