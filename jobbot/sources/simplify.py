"""SimplifyJobs community-curated listings (Summer internships + New Grad repos on GitHub).

Titles only (no description), but every entry links to the company's own
application page and carries a sponsorship tag such as
"U.S. Citizenship is Required" or "Does Not Offer Sponsorship".
"""
from __future__ import annotations

from ..models import Job
from ..utils import parse_dt
from . import SkipSource


def parse(rows, label: str, employment_type: str) -> list[Job]:
    jobs = []
    for x in rows:
        if not x.get("active") or not x.get("is_visible", True):
            continue
        jobs.append(
            Job(
                source=label,
                source_id=str(x.get("id")),
                title=x.get("title", ""),
                company=x.get("company_name", ""),
                url=x.get("url", ""),
                locations=list(x.get("locations") or []),
                posted_at=parse_dt(x.get("date_posted")),
                employment_type=employment_type,
                sponsorship_hint=x.get("sponsorship"),
                has_description=False,
                extra={
                    "curated": True,
                    "degrees": x.get("degrees") or [],
                    "terms": x.get("terms") or [],
                },
            )
        )
    return jobs


def fetch(session, cfg, key: str, employment_type: str) -> list[Job]:
    src = cfg["sources"].get(key) or {}
    if not src.get("enabled"):
        raise SkipSource("disabled")
    r = session.get(src["url"], timeout=90)
    r.raise_for_status()
    label = "Simplify (internships)" if employment_type == "INTERN" else "Simplify (new grad)"
    return parse(r.json(), label, employment_type)
