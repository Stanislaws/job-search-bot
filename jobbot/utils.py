from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("jobbot")

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?i)<\s*(br|/p|/li|/div|/h\d)\s*/?>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n+")


def clean_text(value) -> str:
    """HTML (possibly entity-escaped twice, as Greenhouse does) → plain text."""
    if not value:
        return ""
    s = html.unescape(html.unescape(str(value)))
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = _WS.sub(" ", s)
    return _NL.sub("\n", s).strip()


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "job-search-bot/1.0 (personal daily job digest)"
    return s


def parse_dt(value) -> datetime | None:
    """Epoch seconds/milliseconds or ISO-8601 → aware UTC datetime."""
    if value in (None, "", 0):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            v = float(value)
            if v > 1e12:  # milliseconds
                v /= 1000
            return datetime.fromtimestamp(v, tz=timezone.utc)
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


_POSTED_AGO = re.compile(r"(\d+)\+?\s*day", re.I)


def parse_posted_ago(text: str, now: datetime | None = None) -> datetime | None:
    """Workday-style 'Posted Today' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago'."""
    now = now or datetime.now(timezone.utc)
    t = (text or "").lower()
    if "today" in t:
        return now
    if "yesterday" in t:
        return now - timedelta(days=1)
    m = _POSTED_AGO.search(t)
    return now - timedelta(days=int(m.group(1))) if m else None


def domain_of(url: str) -> str:
    m = re.match(r"https?://([^/:?#]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


def domain_matches(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)
