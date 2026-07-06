"""Greenhouse — many companies expose their careers page as a public JSON board.

Configure a list of board tokens (the slug in boards.greenhouse.io/<token>) in
config.yaml. We pull each board and filter locally by the query terms. Great for
targeting a shortlist of companies you actually want to work at.
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource

BOARD = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


class GreenhouseSource(JobSource):
    name = "greenhouse"

    def search(self, query, location=None, remote=None, limit=25) -> list[Job]:
        if not self.enabled:
            return []
        terms = [t for t in query.lower().split() if t]
        jobs: list[Job] = []
        for token in self.config.get("boards", []):
            try:
                resp = requests.get(BOARD.format(token=token), timeout=30)
                resp.raise_for_status()
                listings = resp.json().get("jobs", [])
            except (requests.RequestException, ValueError):
                continue
            for r in listings:
                haystack = f"{r.get('title', '')} {r.get('content', '')}".lower()
                if terms and not any(t in haystack for t in terms):
                    continue
                loc = (r.get("location") or {}).get("name", "")
                jobs.append(
                    Job(
                        title=r.get("title", "").strip(),
                        company=token,
                        url=r.get("absolute_url", ""),
                        source=self.name,
                        description=r.get("content", ""),
                        location=loc,
                        remote="remote" in loc.lower(),
                        posted_at=r.get("updated_at"),
                    )
                )
                if len(jobs) >= limit:
                    return jobs
        return jobs
