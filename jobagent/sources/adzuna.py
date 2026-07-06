"""Adzuna — free job-listings API covering many countries.

Get a free app_id / app_key at https://developer.adzuna.com and put them in
.env (ADZUNA_APP_ID, ADZUNA_APP_KEY). Without them this source disables itself.
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource

BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


class AdzunaSource(JobSource):
    name = "adzuna"

    @property
    def enabled(self) -> bool:
        return bool(
            self.config.get("enabled", True)
            and self.secrets.get("adzuna_app_id")
            and self.secrets.get("adzuna_app_key")
        )

    def search(self, query, location=None, remote=None, limit=25) -> list[Job]:
        if not self.enabled:
            return []
        country = self.config.get("country", "gb")
        params = {
            "app_id": self.secrets["adzuna_app_id"],
            "app_key": self.secrets["adzuna_app_key"],
            "results_per_page": max(1, min(limit, 50)),
            "what": query,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location
        try:
            resp = requests.get(BASE.format(country=country), params=params, timeout=30)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except (requests.RequestException, ValueError):
            return []

        jobs: list[Job] = []
        for r in results:
            jobs.append(
                Job(
                    title=r.get("title", "").strip(),
                    company=(r.get("company") or {}).get("display_name", "").strip(),
                    url=r.get("redirect_url", ""),
                    source=self.name,
                    description=r.get("description", ""),
                    location=(r.get("location") or {}).get("display_name", ""),
                    salary_min=r.get("salary_min"),
                    salary_max=r.get("salary_max"),
                    posted_at=r.get("created"),
                )
            )
        return jobs
