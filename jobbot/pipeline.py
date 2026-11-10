"""collect → filter → score → dedupe → digest. Pure logic, no email or disk I/O,
so it can be unit-tested and previewed locally."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone

from . import filters
from .models import Job
from .scoring import rank_key, score_fit, score_legitimacy
from .sources import SkipSource, registry
from .utils import log, make_session


def collect(cfg, only: set[str] | None = None) -> tuple[list[Job], dict]:
    session = make_session()
    jobs: list[Job] = []
    status: dict[str, dict] = {}
    for name, fn in registry().items():
        if only and not any(o.lower() in name.lower() for o in only):
            continue
        try:
            got = fn(session, cfg)
            jobs += got
            status[name] = {"ok": True, "note": f"{len(got):,} postings"}
            log.info("%-22s %5d postings", name, len(got))
        except SkipSource as e:
            status[name] = {"ok": False, "note": f"skipped ({e})"}
            log.info("%-22s skipped: %s", name, e)
        except Exception as e:  # one broken source must never kill the email
            status[name] = {"ok": False, "note": f"error: {type(e).__name__}"}
            log.exception("%s failed", name)
    return jobs, status


def evaluate(jobs: list[Job], cfg, now: datetime | None = None) -> tuple[list[Job], dict[str, int]]:
    """Apply hard filters and scores. Returns (kept jobs, counter of drop reasons)."""
    now = now or datetime.now(timezone.utc)
    kept: list[Job] = []
    dropped: dict[str, int] = defaultdict(int)
    for j in jobs:
        if not j.title or not j.url:
            dropped["missing title/link"] += 1
            continue
        reason = (
            filters.age_reason(j, cfg, now)
            or filters.role_reason(j, cfg)
            or filters.location_reason(j, cfg)
        )
        if not reason:
            filters.classify_level(j, cfg)
            reason = filters.experience_reason(j, cfg) or filters.pay_reason(j, cfg)
        if not reason:
            status, note = filters.classify_auth(j, cfg)
            if status == "excluded":
                reason = "work authorization"
            else:
                j.auth_status, j.auth_note = status, note
        if reason:
            dropped[re.sub(r"\d+", "N", reason.split(' ("')[0])] += 1
            continue
        score_fit(j, cfg, now)
        if j.fit_score < cfg["fit"]["min_score"]:
            dropped["low fit score"] += 1
            continue
        score_legitimacy(j, cfg, now)
        kept.append(j)
    return kept, dict(dropped)


def merge_duplicates(jobs: list[Job]) -> list[Job]:
    """Same company + same title from several sources → keep the most trustworthy copy."""
    groups: dict[str, list[Job]] = defaultdict(list)
    for j in jobs:
        groups[j.dedupe_key].append(j)
    out = []
    for group in groups.values():
        group.sort(key=lambda j: (-j.legit_score, -j.fit_score, not j.extra.get("direct")))
        best = group[0]
        best.also_on = sorted({g.source for g in group[1:] if g.source != best.source})
        out.append(best)
    return out


def build_sections(jobs: list[Job], cfg) -> dict[str, list[Job]]:
    jobs = sorted(jobs, key=rank_key)
    flagged = [j for j in jobs if j.verdict == "red"][: cfg["email"].get("max_flagged", 8)]
    good = [j for j in jobs if j.verdict != "red"]
    interns = [j for j in good if j.is_internship]
    others = [j for j in good if not j.is_internship]
    cap = cfg["email"]["max_jobs"]
    # Internships get up to 2/3 of the space; unused space goes to the other section and vice versa.
    i_cap = max(cap * 2 // 3, cap - len(others))
    interns = interns[:i_cap]
    others = others[: cap - len(interns)]
    return {"internships": interns, "entry": others, "flagged": flagged}
