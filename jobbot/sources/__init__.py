"""Job sources. Each module exposes `fetch(session, cfg) -> list[Job]`.

A source raises `SkipSource` when it is not configured (e.g. missing API key);
any other exception is caught by the pipeline so one broken source never
stops the daily email.
"""
from __future__ import annotations


class SkipSource(Exception):
    """Source intentionally skipped (disabled or missing credentials)."""


def registry():
    from . import adzuna, ashby, greenhouse, jsearch, lever, simplify, themuse, workday

    return {
        "Simplify internships": lambda s, c: simplify.fetch(s, c, "simplify_internships", "INTERN"),
        "Simplify new grad": lambda s, c: simplify.fetch(s, c, "simplify_newgrad", "FULLTIME"),
        "Adzuna": adzuna.fetch,
        "JSearch": jsearch.fetch,
        "The Muse": themuse.fetch,
        "Greenhouse watchlist": greenhouse.fetch,
        "Lever watchlist": lever.fetch,
        "Ashby watchlist": ashby.fetch,
        "Workday watchlist": workday.fetch,
    }
