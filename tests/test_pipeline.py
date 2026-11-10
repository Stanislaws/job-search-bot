from datetime import datetime, timezone

import pytest

from jobbot import digest, pipeline
from jobbot.filters import classify_location, years_required
from jobbot.models import Job, norm_company
from jobbot.sources import adzuna, ashby, greenhouse, jsearch, lever, simplify, themuse, workday

from . import samples

NOW = datetime.now(timezone.utc)


def run(jobs, cfg):
    kept, dropped = pipeline.evaluate(jobs, cfg, NOW)
    return {j.source_id: j for j in kept}, dropped


# ── Parsers ─────────────────────────────────────────────────────────────────
def test_parsers_produce_jobs():
    assert len(simplify.parse(samples.SIMPLIFY, "Simplify", "INTERN")) == 4  # inactive one skipped
    assert len(jsearch.parse(samples.JSEARCH)) == 7
    a = adzuna.parse(samples.ADZUNA)
    assert a[0].title == "Data Analyst Intern" and a[0].company == "Plains Insurance"
    m = themuse.parse(samples.MUSE)[0]
    assert m.employment_type == "INTERN" and "SQL" in m.description
    g = greenhouse.parse(samples.GREENHOUSE, "hudl")
    assert "<p>" not in g[0].description and "SQL" in g[0].description
    lv = lever.parse(samples.LEVER, "acme")[0]
    assert lv.pay_period == "hour" and lv.pay_label() == "$25–$30/hr"
    assert ashby.parse(samples.ASHBY, "acme")[0].locations == ["New York, NY"]
    site = {"name": "Nelnet", "host": "nelnet.wd1.myworkdayjobs.com", "tenant": "nelnet", "site": "MyNelnet"}
    wd = workday.parse_listing(samples.WORKDAY_LIST, site)
    assert wd[0].url == "https://nelnet.wd1.myworkdayjobs.com/MyNelnet/job/Lincoln-NE/Intern---Data-Analytics_R12345"
    workday.apply_detail(wd[0], samples.WORKDAY_DETAIL)
    assert "Power BI" in wd[0].description and wd[0].has_description


# ── Filters ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "loc,expected",
    [
        ("Lincoln, NE", "us"), ("Remote in USA", "us"), ("Tarzana, LA", "us"), ("New London, CT", "us"),
        ("Toronto, ON, Canada", "foreign"), ("London, UK", "foreign"), ("Barcelona, Spain", "foreign"),
        ("Mississauga, ON", "foreign"), ("Flexible / Remote", "remote"), ("Lincoln, Nebraska, United States", "us"),
    ],
)
def test_locations(loc, expected):
    assert classify_location(loc) == expected


def test_years_required():
    assert years_required("Requires 3+ years of relevant experience") == 3
    assert years_required("0-2 years of experience preferred") is None  # 0 ignored → nothing above 0
    assert years_required("minimum of 5 years in analytics") == 5
    assert years_required("$5 years") is None


def test_simplify_filters(cfg):
    kept, dropped = run(simplify.parse(samples.SIMPLIFY, "Simplify", "INTERN"), cfg)
    assert set(kept) == {"a1"}
    assert dropped["work authorization"] == 1 and dropped["outside the US"] == 1
    assert dropped["seniority / excluded title"] == 1
    j = kept["a1"]
    assert j.is_internship and j.verdict == "green" and "Lincoln" in j.fit_reasons


def test_scam_detection_and_auth(cfg):
    kept, dropped = run(jsearch.parse(samples.JSEARCH), cfg)
    assert kept["j1"].verdict == "green"
    assert kept["j2"].verdict == "red"
    r2 = " ".join(kept["j2"].legit_reasons)
    for phrase in ("check-deposit", "chat app", "personal email", "pay for training", "URL shortener", "generic"):
        assert phrase in r2, phrase
    assert kept["j3"].verdict == "red"
    assert any("unusually high" in r for r in kept["j3"].legit_reasons)
    assert "j4" not in kept and "j6" not in kept  # clearance / unpaid
    assert dropped["work authorization"] == 1 and dropped["unpaid"] == 1
    assert kept["j5"].auth_status == "caution" and kept["j5"].verdict == "green"
    assert kept["j7"].verdict == "yellow" and kept["j7"].auth_status == "positive"


def test_experience_filter(cfg):
    kept, dropped = run(adzuna.parse(samples.ADZUNA), cfg)
    assert set(kept) == {"z1"}  # "Data Analyst III" is dropped by title


def test_merge_and_sections(cfg):
    jobs = simplify.parse(samples.SIMPLIFY, "Simplify", "INTERN")
    dup = Job(source="Adzuna", source_id="dup", title="Data Analyst Intern (Summer 2027)", company="Acme Insurance Inc.",
              url="https://www.adzuna.com/land/ad/9", locations=["Lincoln, NE"], description="SQL " * 100,
              country_scoped=True)
    kept, _ = pipeline.evaluate(jobs + [dup] + jsearch.parse(samples.JSEARCH), cfg, NOW)
    merged = pipeline.merge_duplicates(kept)
    acme = [j for j in merged if norm_company(j.company) == "acme insurance"]
    assert len(acme) == 1 and acme[0].source == "Simplify" and acme[0].also_on == ["Adzuna"]
    sec = pipeline.build_sections(merged, cfg)
    assert all(j.verdict != "red" for j in sec["internships"] + sec["entry"])
    assert {j.source_id for j in sec["flagged"]} == {"j2", "j3"}
    html_body, text_body = digest.render(
        sec, {"scanned": 10, "matched": 5, "new": 5, "sources": {"Test": {"ok": True, "note": "5 postings"}}}, NOW
    )
    assert "Flagged as likely scams" in html_body and "bit.ly" not in html_body  # scam links are never rendered
    assert "Acme Insurance" in text_body
