"""Greenhouse public job boards: boards-api.greenhouse.io/v1/boards/<board>/jobs"""
from __future__ import annotations

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource


def parse(payload, board: str) -> list[Job]:
    jobs = []
    for x in payload.get("jobs", []):
        jobs.append(
            Job(
                source="Greenhouse",
                source_id=f"{board}-{x.get('id')}",
                title=x.get("title", ""),
                company=x.get("company_name") or board.replace("-", " ").title(),
                url=x.get("absolute_url", ""),
                locations=[(x.get("location") or {}).get("name", "")],
                description=clean_text(x.get("content")),
                posted_at=parse_dt(x.get("first_published") or x.get("updated_at")),
                extra={"direct": True},
            )
        )
    return jobs


def fetch(session, cfg) -> list[Job]:
    boards = cfg["sources"].get("greenhouse") or []
    if not boards:
        raise SkipSource("no boards listed")
    jobs: list[Job] = []
    failures = attempts = 0
    for board in boards:
        attempts += 1
        r = session.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", params={"content": "true"}, timeout=30)
        if r.status_code != 200:
            log.warning("Greenhouse board %r → HTTP %s", board, r.status_code)
            failures += 1
            continue
        jobs += parse(r.json(), board)
    if attempts and failures == attempts:
        raise RuntimeError(f"all {attempts} requests failed")
    return jobs
