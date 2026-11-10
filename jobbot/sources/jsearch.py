"""JSearch (RapidAPI) — Google-for-Jobs results: LinkedIn, Indeed, Glassdoor, ZipRecruiter…
Free "Basic" plan on rapidapi.com (search "JSearch")."""
from __future__ import annotations

import os

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource

URL = "https://jsearch.p.rapidapi.com/search"


def parse(payload) -> list[Job]:
    jobs = []
    for x in payload.get("data") or []:
        city, state = x.get("job_city"), x.get("job_state")
        loc = ", ".join(p for p in (city, state) if p) or x.get("job_location") or ""
        if x.get("job_is_remote"):
            loc = f"Remote ({x.get('job_country') or 'US'})" if not loc else f"{loc} (Remote)"
        if x.get("job_country") and x.get("job_country") != "US":
            loc = f"{loc}, {x['job_country']}"
        jobs.append(
            Job(
                source="JSearch",
                source_id=str(x.get("job_id")),
                title=x.get("job_title", ""),
                company=x.get("employer_name") or "",
                url=x.get("job_apply_link") or x.get("job_google_link") or "",
                locations=[loc] if loc else [],
                description=clean_text(x.get("job_description")),
                posted_at=parse_dt(x.get("job_posted_at_timestamp") or x.get("job_posted_at_datetime_utc")),
                pay_min=x.get("job_min_salary"),
                pay_max=x.get("job_max_salary"),
                pay_period=(x.get("job_salary_period") or "").lower() or None,
                employment_type=(x.get("job_employment_type") or "").upper(),
                is_remote=x.get("job_is_remote"),
                country_scoped=(x.get("job_country") in (None, "", "US")),
                extra={
                    "publisher": x.get("job_publisher"),
                    "apply_is_direct": x.get("job_apply_is_direct"),
                    "employer_website": x.get("employer_website"),
                },
            )
        )
    return jobs


def fetch(session, cfg) -> list[Job]:
    src = cfg["sources"].get("jsearch") or {}
    key = os.getenv("RAPIDAPI_KEY")
    if not src.get("enabled"):
        raise SkipSource("disabled")
    if not key:
        raise SkipSource("no RAPIDAPI_KEY secret")
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    jobs: list[Job] = []
    for q in cfg["search"]["queries"][: src.get("max_requests_per_run", 6)]:
        params = {
            "query": f"{q} in United States",
            "page": 1,
            "num_pages": 1,
            "country": "us",
            "date_posted": src.get("date_posted", "3days"),
        }
        if "intern" in q:
            params["employment_types"] = "INTERN"
        r = session.get(URL, headers=headers, params=params, timeout=40)
        if r.status_code == 429:
            log.warning("JSearch monthly quota reached; skipping remaining queries")
            break
        if r.status_code != 200:
            log.warning("JSearch %r → HTTP %s", q, r.status_code)
            continue
        jobs += parse(r.json())
    return jobs
