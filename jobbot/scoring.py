"""Two scores per job:

* fit (0–100): how well the posting matches what you're looking for.
* legitimacy (0–100): how much it looks like a real job vs. a scam/ghost post.
  Mapped to a traffic light: 🟢 green / 🟡 yellow / 🔴 red.

Every point added or removed comes with a human-readable reason that is shown
in the email, so you can see *why* and tune config.yaml accordingly.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .filters import any_match, rx, title_weight
from .models import Job
from .utils import domain_matches, domain_of

PERSONAL_EMAIL = re.compile(
    r"[\w.+-]+@(gmail|yahoo|outlook|hotmail|aol|icloud|proton|protonmail|gmx|zoho|yandex)\.(com|me|net)", re.I
)
GENERIC_COMPANY = re.compile(
    r"^\s*$|confidential|undisclosed|hiring (company|team|manager)|^company$|private (company|employer)|"
    r"^n/?a$|our client|leading company|^employer$",
    re.I,
)


def score_fit(job: Job, cfg, now: datetime | None = None) -> None:
    fit = cfg["fit"]
    reasons: list[str] = []
    w, label = title_weight(job.title, cfg)
    score = w
    reasons.append(label)

    if job.is_internship:
        score += fit["internship_bonus"]
        reasons.append("internship")
    elif job.is_entry:
        score += fit["entry_bonus"]
        reasons.append("entry level")
    else:
        score += fit["unspecified_level_bonus"]

    text = job.text
    skills = [s for s in fit.get("skills", []) if rx(s).search(text)]
    if skills:
        score += min(len(skills) * fit["skill_points"], fit["skill_cap"])
        pretty = [re.sub(r"\\b", "", s) for s in skills[:5]]
        reasons.append("skills: " + ", ".join(pretty))

    bonus = 0
    for item in fit.get("bonus_keywords", []):
        if rx(item["pattern"]).search(text):
            bonus += item["bonus"]
            reasons.append(item["label"])
    score += min(bonus, fit.get("bonus_cap", 12))

    for item in fit.get("penalties", []):
        if rx(item["pattern"]).search(text):
            score -= item["penalty"]
            reasons.append(f"−{item['label']}")

    loc_text = " | ".join(job.locations) + (" remote" if job.is_remote else "")
    for item in cfg["location"].get("preferred", []):
        if rx(item["pattern"]).search(loc_text):
            score += item["bonus"]
            reasons.append(item["label"])
            break

    if job.posted_at:
        days = ((now or datetime.now(timezone.utc)) - job.posted_at).days
        if days <= 2:
            score += 5
            reasons.append("posted in the last 2 days")
        elif days <= 7:
            score += 3

    if job.auth_status == "positive":
        score += cfg["work_authorization"].get("positive_bonus", 5)

    job.fit_score = max(0, min(100, score))
    job.fit_reasons = reasons


def score_legitimacy(job: Job, cfg, now: datetime | None = None) -> None:
    lg = cfg["legitimacy"]
    score = lg["baseline"]
    good: list[str] = []
    bad: list[str] = []
    host = domain_of(job.url)
    text = job.text

    # Positive evidence
    if job.extra.get("curated"):
        score += lg["curated_bonus"]
        good.append("listed on a human-curated board")
    if job.extra.get("direct") or domain_matches(host, lg["trusted_ats_domains"]):
        score += lg["direct_ats_bonus"]
        good.append("applies through the company's own hiring system")
    elif job.extra.get("apply_is_direct"):
        score += lg["direct_ats_bonus"] // 2
        good.append("direct apply link")
    site = domain_of(job.extra.get("employer_website") or "")
    if site and host and site.replace("www.", "") in host:
        score += 5
        good.append("link matches the company's website")

    # Red flags in the posting text
    for flag in lg.get("red_flags", []):
        if rx(flag["pattern"]).search(text):
            score -= flag["weight"]
            bad.append(flag["reason"])
    if PERSONAL_EMAIL.search(text):
        score -= lg["personal_email_penalty"]
        bad.append("contact is a personal email address (gmail/yahoo/…)")
    if GENERIC_COMPANY.search(job.company or ""):
        score -= lg["generic_company_penalty"]
        bad.append("company name hidden or generic")
    if job.has_description and not job.extra.get("snippet_only"):
        if len(job.description) < lg["vague_description_chars"]:
            score -= lg["vague_description_penalty"]
            bad.append("very short / vague description")
    if host and domain_matches(host, lg.get("shortener_domains", [])):
        score -= 20
        bad.append("link goes through a URL shortener")
    if job.url.startswith("http://"):
        score -= 5
        bad.append("link is not https")

    # Pay that is too good to be true
    hourly = job.hourly_pay()
    exempt = rx(lg["pay_anomaly_exempt_companies"]).search(job.company or "")
    if hourly and not job.pay_estimated and hourly > lg["max_plausible_hourly"] and not exempt:
        score -= lg["pay_anomaly_penalty"]
        bad.append(f"pay (~${hourly:.0f}/hr) is unusually high for an entry-level role")

    # Training-for-hire programs
    if rx(lg["training_programs"]).search(f"{job.company} {text}"):
        score -= lg["training_penalty"]
        bad.append("training-for-hire program — check the contract for commitments or repayment terms")

    # Possible ghost job
    if job.posted_at:
        days = ((now or datetime.now(timezone.utc)) - job.posted_at).days
        if days > lg["stale_days"]:
            score -= lg["stale_penalty"]
            bad.append(f"posted {days} days ago — may be a ghost job")

    job.legit_score = max(0, min(100, score))
    job.legit_reasons = bad + good
    job.verdict = "green" if job.legit_score >= lg["green_at"] else "yellow" if job.legit_score >= lg["yellow_at"] else "red"


def rank_key(job: Job) -> tuple:
    verdict_order = {"green": 0, "yellow": 1, "red": 2}[job.verdict]
    return (verdict_order > 0, -job.fit_score, -job.legit_score, job.company.lower())
