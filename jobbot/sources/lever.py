"""Lever public postings: api.lever.co/v0/postings/<company>?mode=json"""
from __future__ import annotations

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource


def parse(payload, company: str) -> list[Job]:
    jobs = []
    for x in payload or []:
        cats = x.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location", "")]
        sal = x.get("salaryRange") or {}
        lists = " ".join(f"{li.get('text', '')}: {clean_text(li.get('content'))}" for li in x.get("lists") or [])
        desc = " ".join(filter(None, [x.get("descriptionPlain"), lists, x.get("additionalPlain")]))
        interval = (sal.get("interval") or "").lower()
        jobs.append(
            Job(
                source="Lever",
                source_id=f"{company}-{x.get('id')}",
                title=x.get("text", ""),
                company=company.replace("-", " ").title(),
                url=x.get("hostedUrl", ""),
                locations=[loc for loc in locs if loc],
                description=clean_text(desc),
                posted_at=parse_dt(x.get("createdAt")),
                pay_min=sal.get("min"),
                pay_max=sal.get("max"),
                pay_period="hour" if "hour" in interval else "month" if "month" in interval else "year" if sal else None,
                employment_type=(cats.get("commitment") or "").upper(),
                is_remote=(x.get("workplaceType") == "remote") or None,
                extra={"direct": True},
            )
        )
    if attempts and failures == attempts:
        raise RuntimeError(f"all {attempts} requests failed")
    return jobs


def fetch(session, cfg) -> list[Job]:
    companies = cfg["sources"].get("lever") or []
    if not companies:
        raise SkipSource("no companies listed")
    jobs: list[Job] = []
    failures = attempts = 0
    for c in companies:
        attempts += 1
        r = session.get(f"https://api.lever.co/v0/postings/{c}", params={"mode": "json"}, timeout=30)
        if r.status_code != 200:
            log.warning("Lever %r → HTTP %s", c, r.status_code)
            failures += 1
            continue
        jobs += parse(r.json(), c)
    if attempts and failures == attempts:
        raise RuntimeError(f"all {attempts} requests failed")
    return jobs
