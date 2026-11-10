"""Adzuna job-search API (aggregates many US job boards). Free key: developer.adzuna.com"""
from __future__ import annotations

import os

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource

URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"


def parse(payload) -> list[Job]:
    jobs = []
    for x in payload.get("results", []):
        loc = (x.get("location") or {}).get("display_name") or ""
        estimated = str(x.get("salary_is_predicted", "0")) == "1"
        jobs.append(
            Job(
                source="Adzuna",
                source_id=str(x.get("id")),
                title=clean_text(x.get("title")),
                company=(x.get("company") or {}).get("display_name", ""),
                url=x.get("redirect_url", ""),
                locations=[loc] if loc else [],
                description=clean_text(x.get("description")),
                posted_at=parse_dt(x.get("created")),
                pay_min=x.get("salary_min"),
                pay_max=x.get("salary_max"),
                pay_period="year",
                pay_estimated=estimated,
                employment_type=(x.get("contract_time") or "").upper(),
                country_scoped=True,
                extra={"snippet_only": True},
            )
        )
    if attempts and failures == attempts:
        raise RuntimeError(f"all {attempts} requests failed")
    return jobs


def fetch(session, cfg) -> list[Job]:
    src = cfg["sources"].get("adzuna") or {}
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not src.get("enabled"):
        raise SkipSource("disabled")
    if not (app_id and app_key):
        raise SkipSource("no ADZUNA_APP_ID / ADZUNA_APP_KEY secret")
    jobs: list[Job] = []
    failures = attempts = 0
    for q in cfg["search"]["queries"]:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": q,
            "results_per_page": src.get("results_per_query", 50),
            "max_days_old": cfg["search"]["max_age_days"],
            "sort_by": "date",
            "content-type": "application/json",
        }
        attempts += 1
        r = session.get(URL, params=params, timeout=30)
        if r.status_code != 200:
            log.warning("Adzuna %r → HTTP %s", q, r.status_code)
            failures += 1
            continue
        jobs += parse(r.json())
    if attempts and failures == attempts:
        raise RuntimeError(f"all {attempts} requests failed")
    return jobs
