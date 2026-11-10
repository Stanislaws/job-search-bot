"""The Muse public jobs API (no key needed). Filters by category + level, not keywords."""
from __future__ import annotations

from ..models import Job
from ..utils import clean_text, log, parse_dt
from . import SkipSource

URL = "https://www.themuse.com/api/public/jobs"


def parse(payload) -> list[Job]:
    jobs = []
    for x in payload.get("results", []):
        levels = [lv.get("name", "") for lv in x.get("levels") or []]
        jobs.append(
            Job(
                source="The Muse",
                source_id=str(x.get("id")),
                title=x.get("name", ""),
                company=(x.get("company") or {}).get("name", ""),
                url=(x.get("refs") or {}).get("landing_page", ""),
                locations=[loc.get("name", "") for loc in x.get("locations") or []],
                description=clean_text(x.get("contents")),
                posted_at=parse_dt(x.get("publication_date")),
                employment_type="INTERN" if "Internship" in levels else "",
                extra={"levels": levels},
            )
        )
    return jobs


def fetch(session, cfg) -> list[Job]:
    src = cfg["sources"].get("themuse") or {}
    if not src.get("enabled"):
        raise SkipSource("disabled")
    jobs: list[Job] = []
    seen: set[str] = set()
    for page in range(src.get("max_pages", 5)):
        params = [("page", page)] + [("category", c) for c in src.get("categories", [])]
        params += [("level", lv) for lv in src.get("levels", [])]
        r = session.get(URL, params=params, timeout=30)
        if r.status_code != 200:
            log.warning("The Muse page %s → HTTP %s", page, r.status_code)
            break
        payload = r.json()
        batch = [j for j in parse(payload) if j.source_id not in seen]
        seen.update(j.source_id for j in batch)
        jobs += batch
        if not batch or page + 1 >= int(payload.get("page_count") or 0):
            break
    return jobs
