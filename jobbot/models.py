from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|plc|group|holdings|the|usa|us)\b\.?"
)
_TITLE_NOISE = re.compile(
    r"\b(summer|fall|winter|spring|20\d\d|remote|hybrid|onsite|on-site|internship|intern|program)\b"
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_company(name: str) -> str:
    s = (name or "").lower()
    s = _COMPANY_SUFFIXES.sub(" ", s)
    return _NON_ALNUM.sub(" ", s).strip()


def norm_title(title: str) -> str:
    s = (title or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = _TITLE_NOISE.sub(" ", s)
    return _NON_ALNUM.sub(" ", s).strip()


@dataclass
class Job:
    source: str
    source_id: str
    title: str
    company: str
    url: str
    locations: list[str] = field(default_factory=list)
    description: str = ""
    posted_at: datetime | None = None
    pay_min: float | None = None
    pay_max: float | None = None
    pay_period: str | None = None          # "hour" | "month" | "year"
    pay_estimated: bool = False
    employment_type: str = ""              # INTERN | FULLTIME | ...
    is_remote: bool | None = None
    sponsorship_hint: str | None = None    # e.g. Simplify's sponsorship field
    country_scoped: bool = False           # True when the source only returns US jobs
    has_description: bool = True           # False when the source gives titles only
    extra: dict[str, Any] = field(default_factory=dict)

    # Filled in by the pipeline
    is_internship: bool = False
    is_entry: bool = False
    fit_score: int = 0
    fit_reasons: list[str] = field(default_factory=list)
    legit_score: int = 0
    legit_reasons: list[str] = field(default_factory=list)
    verdict: str = ""                      # green | yellow | red
    auth_status: str = "ok"                # ok | caution | positive
    auth_note: str = ""
    also_on: list[str] = field(default_factory=list)

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.source_id}"

    @property
    def dedupe_key(self) -> str:
        return f"{norm_company(self.company)}|{norm_title(self.title)}"

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}"

    def hourly_pay(self) -> float | None:
        """Best-guess hourly equivalent of the top of the pay range."""
        top = self.pay_max or self.pay_min
        if not top:
            return None
        period = (self.pay_period or "").lower()
        if period.startswith("hour"):
            return top
        if period.startswith("month"):
            return top / 173
        if period.startswith("week"):
            return top / 40
        if period.startswith("year") or top > 1000:
            return top / 2080
        return top

    def pay_label(self) -> str:
        if not (self.pay_min or self.pay_max):
            return "Pay not listed"
        lo, hi = self.pay_min, self.pay_max
        period = (self.pay_period or ("year" if (hi or lo or 0) > 1000 else "hour")).lower()
        unit = next((u for p, u in (("hour", "/hr"), ("month", "/mo"), ("week", "/wk")) if period.startswith(p)), "/yr")

        def fmt(v: float) -> str:
            return f"${v:,.0f}" if v >= 100 else f"${v:,.2f}".rstrip("0").rstrip(".")

        txt = f"{fmt(lo)}–{fmt(hi)}{unit}" if lo and hi and lo != hi else f"{fmt(hi or lo)}{unit}"
        return txt + (" (est.)" if self.pay_estimated else "")
