"""Workday career sites (used by many large employers, e.g. Nelnet).

Uses the JSON endpoint behind every *.myworkdayjobs.com site:
  POST https://<host>/wday/cxs/<tenant>/<site>/jobs        (search)
  GET  https://<host>/wday/cxs/<tenant>/<site><path>       (job detail)
Details are only fetched for titles that already look like a match.
"""
from __future__ import annotations

from ..models import Job
from ..utils import clean_text, log, parse_dt, parse_posted_ago
from . import SkipSource

PAGE = 20


def parse_listing(payload, site_cfg) -> list[Job]:
    host, site, name = site_cfg["host"], site_cfg["site"], site_cfg["name"]
    jobs = []
    for x in payload.get("jobPostings", []):
        path = x.get("externalPath", "")
        if not path:
            continue
        jobs.append(
            Job(
                source="Workday",
                source_id=f"{site_cfg['tenant']}-{path.rsplit('_', 1)[-1]}",
                title=x.get("title", ""),
                company=name,
                url=f"https://{host}/{site}{path}",
                locations=[x.get("locationsText", "")],
                posted_at=parse_posted_ago(x.get("postedOn", "")),
                has_description=False,
                extra={"direct": True, "wd_path": path},
            )
        )
    return jobs


def apply_detail(job: Job, payload) -> None:
    info = payload.get("jobPostingInfo") or {}
    job.description = clean_text(info.get("jobDescription"))
    job.has_description = bool(job.description)
    locs = [info.get("location")] + list(info.get("additionalLocations") or [])
    job.locations = [loc for loc in locs if loc] or job.locations
    job.posted_at = parse_dt(info.get("startDate")) or job.posted_at
    job.employment_type = (info.get("timeType") or "").upper()
    job.url = info.get("externalUrl") or job.url


def fetch(session, cfg) -> list[Job]:
    from ..filters import title_weight  # local import avoids a cycle

    sites = cfg["sources"].get("workday") or []
    if not sites:
        raise SkipSource("no sites listed")
    out: list[Job] = []
    for sc in sites:
        base = f"https://{sc['host']}/wday/cxs/{sc['tenant']}/{sc['site']}"
        found: dict[str, Job] = {}
        for q in cfg["search"]["queries"]:
            for offset in range(0, PAGE * 3, PAGE):
                body = {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": q}
                r = session.post(f"{base}/jobs", json=body, timeout=30, headers={"Accept": "application/json"})
                if r.status_code != 200:
                    log.warning("Workday %s %r → HTTP %s", sc["name"], q, r.status_code)
                    break
                page = parse_listing(r.json(), sc)
                for j in page:
                    found.setdefault(j.source_id, j)
                if len(page) < PAGE:
                    break
        for j in found.values():
            if title_weight(j.title, cfg)[0] <= 0:
                continue
            d = session.get(f"{base}{j.extra['wd_path']}", timeout=30, headers={"Accept": "application/json"})
            if d.status_code == 200:
                apply_detail(j, d.json())
            out.append(j)
    return out
