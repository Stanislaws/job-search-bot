"""Hard filters: things that remove a job entirely (wrong country, wrong role,
too senior, needs citizenship, unpaid…). Each returns a reason string or None."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from .models import Job


@lru_cache(maxsize=None)
def rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


def any_match(patterns, text: str) -> re.Match | None:
    for p in patterns or []:
        m = rx(p).search(text)
        if m:
            return m
    return None


# ── Location ────────────────────────────────────────────────────────────────
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
    "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND",
    "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR",
}
STATE_NAMES = (
    "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|"
    "illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    "mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|"
    "north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|"
    "utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|district of columbia|puerto rico"
)
FOREIGN = re.compile(
    r"\b(canada|mexico|united kingdom|\buk\b|england|scotland|ireland|india|germany|france|spain|portugal|italy|"
    r"netherlands|belgium|poland|romania|switzerland|sweden|denmark|norway|finland|austria|czech|hungary|israel|"
    r"singapore|australia|new zealand|japan|china|hong kong|taiwan|korea|philippines|vietnam|thailand|malaysia|"
    r"indonesia|brazil|argentina|chile|colombia|peru|costa rica|uae|dubai|saudi|egypt|nigeria|south africa|kenya|"
    r"emea|apac|latam)\b",
    re.I,
)
# City names only count as foreign when no US state is present ("New London, CT" stays US).
FOREIGN_CITY = re.compile(
    r"\b(toronto|vancouver|montreal|london|bangalore|bengaluru|hyderabad|pune|mumbai|dublin|berlin|paris|"
    r"barcelona|madrid|amsterdam|warsaw|krakow|tel aviv|sydney|melbourne|tokyo|manila)\b",
    re.I,
)
CA_PROVINCE = re.compile(r",\s*(ON|BC|QC|AB|MB|SK|NS|NB|NL|PE)\b")
US_WORD = re.compile(r"\b(usa|u\.s\.a?\.?|united states|us|nationwide)\b", re.I)
STATE_CODE = re.compile(r"(?:,|\s-)\s*([A-Z]{2})\b")
STATE_NAME = re.compile(rf"\b({STATE_NAMES})\b", re.I)
REMOTE = re.compile(r"\b(remote|anywhere|flexible|virtual|work from home|wfh)\b", re.I)


def classify_location(loc: str) -> str:
    """'us' | 'foreign' | 'remote' (country unknown) | 'unknown'"""
    if not loc:
        return "unknown"
    if FOREIGN.search(loc) or CA_PROVINCE.search(loc):
        return "foreign"
    if US_WORD.search(loc):
        return "us"
    m = STATE_CODE.search(loc)
    if m and m.group(1) in US_STATES:
        return "us"
    if STATE_NAME.search(loc):
        return "us"
    if FOREIGN_CITY.search(loc):
        return "foreign"
    if REMOTE.search(loc):
        return "remote"
    return "unknown"


def location_reason(job: Job, cfg) -> str | None:
    kinds = {classify_location(loc) for loc in job.locations if loc} or {"unknown"}
    if "us" in kinds:
        return None
    if kinds == {"foreign"}:
        return "outside the US"
    if job.country_scoped or cfg["search"].get("keep_unknown_locations", True):
        return None
    return "location unclear"


# ── Role / seniority ────────────────────────────────────────────────────────
def title_weight(title: str, cfg) -> tuple[int, str]:
    """Return (weight, matched text) for the strongest role pattern, or (0, '') if none / excluded."""
    role = cfg["role"]
    if any_match(role.get("title_exclude"), title):
        return 0, ""
    for item in role["title_patterns"]:  # ordered strongest first
        if rx(item["pattern"]).search(title):
            return int(item["weight"]), item.get("label", "role match")
    return 0, ""


def sentence_around(text: str, m: re.Match, limit: int = 160) -> str:
    """The sentence containing a regex match, trimmed for display."""
    start = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
    ends = [i for i in (text.find(".", m.end()), text.find("\n", m.end())) if i != -1]
    sentence = text[start : (min(ends) + 1 if ends else len(text))].strip()
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def role_reason(job: Job, cfg) -> str | None:
    if any_match(cfg["role"].get("title_exclude"), job.title):
        return "seniority / excluded title"
    if title_weight(job.title, cfg)[0] <= 0:
        return "not a data/analyst role"
    degrees = [d.lower() for d in job.extra.get("degrees") or []]
    if degrees and all("phd" in d for d in degrees):
        return "PhD only"
    return None


_YEARS = re.compile(
    r"(?<![\d$])(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d{1,2}\s*)?\+?\s*years?\b[^.;\n]{0,40}?experience",
    re.I,
)
_MIN_YEARS = re.compile(r"(?:minimum|at least)(?: of)?\s+(\d{1,2})\s+years?", re.I)


def years_required(text: str) -> int | None:
    nums = [int(m.group(1)) for m in _YEARS.finditer(text)] + [int(m.group(1)) for m in _MIN_YEARS.finditer(text)]
    nums = [n for n in nums if 0 < n < 30]
    return min(nums) if nums else None


def classify_level(job: Job, cfg) -> None:
    role = cfg["role"]
    levels = " ".join(job.extra.get("levels") or [])
    job.is_internship = bool(
        rx(role["internship_pattern"]).search(job.title)
        or job.employment_type == "INTERN"
        or "Internship" in levels
    )
    job.is_entry = not job.is_internship and bool(
        rx(role["entry_pattern"]).search(job.title) or "new grad" in job.source.lower() or "Entry Level" in levels
    )


def experience_reason(job: Job, cfg) -> str | None:
    if job.is_internship:
        return None
    yrs = years_required(job.description)
    if yrs is not None and yrs > cfg["role"].get("max_years_experience", 2):
        return f"asks for {yrs}+ years of experience"
    return None


# ── Work authorization (CPT) ────────────────────────────────────────────────
def classify_auth(job: Job, cfg) -> tuple[str, str]:
    """Return (status, note). status ∈ excluded | caution | positive | ok."""
    wa = cfg["work_authorization"]
    hint = (job.sponsorship_hint or "").lower()
    if "citizenship is required" in hint:
        return "excluded", "U.S. citizenship required"
    m = any_match(wa.get("exclude"), job.text)
    if m:
        return "excluded", f'says "{m.group(0).strip()}"'
    if "does not offer sponsorship" in hint:
        return "caution", "Says no sponsorship — CPT doesn't need it, but confirm with the recruiter"
    m = any_match(wa.get("caution"), job.text)
    if m:
        return "caution", f'Sponsorship note: "{sentence_around(job.text, m)}" CPT doesn\'t need sponsorship, so ask the recruiter.'
    if "offers sponsorship" in hint:
        return "positive", "Offers sponsorship"
    m = any_match(wa.get("positive"), job.text)
    if m:
        return "positive", f'"{sentence_around(job.text, m, 120)}"'
    return "ok", ""


# ── Pay ─────────────────────────────────────────────────────────────────────
def pay_reason(job: Job, cfg) -> str | None:
    pay = cfg["pay"]
    m = any_match(pay.get("unpaid_patterns"), job.text)
    if m:
        return f'unpaid ("{m.group(0)}")'
    hourly = job.hourly_pay()
    if hourly is not None and not job.pay_estimated and hourly < pay.get("min_hourly", 0):
        return f"pays about ${hourly:.0f}/hr"
    return None


# ── Age ─────────────────────────────────────────────────────────────────────
def age_reason(job: Job, cfg, now: datetime | None = None) -> str | None:
    if not job.posted_at:
        return None
    now = now or datetime.now(timezone.utc)
    if now - job.posted_at > timedelta(days=cfg["search"]["max_age_days"]):
        return "posted too long ago"
    return None
