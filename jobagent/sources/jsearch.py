"""JSearch (RapidAPI) — an aggregator that reads Google for Jobs.

This is the legitimate way to pull listings that originate on LinkedIn, Indeed,
Glassdoor, ZipRecruiter, and company career pages: JSearch does the collection
on its side and returns clean JSON. You bring your own RapidAPI key, so there's
no scraping from your machine and nothing that breaks LinkedIn's terms.

Setup:
  1. Sign up at https://rapidapi.com and subscribe to the "JSearch" API
     (there's a free Basic plan).
  2. Put the key in .env as RAPIDAPI_KEY.
  3. Enable this source in config.yaml.

Note: which publishers show up (and how many) varies over time and by plan;
each result records its origin in `job.source` (e.g. "jsearch:LinkedIn").
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource

# JSearch moved job search to /search-v2 (the old /search is gone on current
# plans). Results now come back nested under data.jobs instead of data.
ENDPOINT = "https://jsearch.p.rapidapi.com/search-v2"
HOST = "jsearch.p.rapidapi.com"


class JSearchSource(JobSource):
    name = "jsearch"

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True) and self.secrets.get("rapidapi_key"))

    def search(self, query, location=None, remote=None, limit=25) -> list[Job]:
        if not self.enabled:
            return []
        # JSearch reads location best when it's part of the query string.
        q = f"{query} in {location}" if location else query
        params = {
            "query": q,
            "num_pages": str(self.config.get("num_pages", 1)),
            "date_posted": self.config.get("date_posted", "all"),
        }
        if self.config.get("country"):
            params["country"] = self.config["country"]
        if remote:
            params["work_from_home"] = "true"

        headers = {
            "X-RapidAPI-Key": self.secrets["rapidapi_key"],
            "X-RapidAPI-Host": HOST,
        }
        try:
            resp = requests.get(ENDPOINT, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            # /search-v2 nests jobs under data.jobs; older /search returned a list.
            rows = data.get("jobs", []) if isinstance(data, dict) else (data or [])
        except (requests.RequestException, ValueError, AttributeError):
            return []

        jobs: list[Job] = []
        for r in rows[:limit]:
            publisher = (r.get("job_publisher") or "").strip()
            loc = ", ".join(
                p for p in (r.get("job_city"), r.get("job_state"), r.get("job_country")) if p
            )
            jobs.append(
                Job(
                    title=(r.get("job_title") or "").strip(),
                    company=(r.get("employer_name") or "").strip(),
                    url=r.get("job_apply_link", ""),
                    source=f"jsearch:{publisher}" if publisher else "jsearch",
                    description=r.get("job_description", "") or "",
                    location=loc,
                    remote=bool(r.get("job_is_remote")),
                    salary_min=r.get("job_min_salary"),
                    salary_max=r.get("job_max_salary"),
                    posted_at=r.get("job_posted_at_datetime_utc"),
                )
            )
        return jobs
