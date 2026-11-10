"""Ashby public job boards: api.ashbyhq.com/posting-api/job-board/<board>"""
from __future__ import annotations

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource


def parse(payload, board: str) -> list[Job]:
    jobs = []
    for x in payload.get("jobs", []):
        if x.get("isListed") is False:
            continue
        locs = [x.get("location", "")] + [s.get("location", "") for s in x.get("secondaryLocations") or []]
        comp = (x.get("compensation") or {}).get("compensationTierSummary") or ""
        jobs.append(
            Job(
                source="Ashby",
                source_id=f"{board}-{x.get('id')}",
                title=x.get("title", ""),
                company=board.replace("-", " ").title(),
                url=x.get("jobUrl") or x.get("applyUrl") or "",
                locations=[loc for loc in locs if loc],
                description=clean_text(x.get("descriptionPlain") or x.get("descriptionHtml")),
                posted_at=parse_dt(x.get("publishedAt")),
                employment_type=(x.get("employmentType") or "").upper(),
                is_remote=x.get("isRemote"),
                extra={"direct": True, "pay_text": comp},
            )
        )
    return jobs


def fetch(session, cfg) -> list[Job]:
    boards = cfg["sources"].get("ashby") or []
    if not boards:
        raise SkipSource("no boards listed")
    jobs: list[Job] = []
    for b in boards:
        r = session.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{b}", params={"includeCompensation": "true"}, timeout=30
        )
        if r.status_code != 200:
            log.warning("Ashby %r → HTTP %s", b, r.status_code)
            continue
        jobs += parse(r.json(), b)
    return jobs
