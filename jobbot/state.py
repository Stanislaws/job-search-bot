"""Memory between runs, stored in the repo itself (state/seen.json) and committed
back by the GitHub Action. Guarantees you never get the same job twice, and that
the scheduled run sends exactly one email per day."""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from .models import Job

KEEP_DAYS = 120
LOG_FIELDS = [
    "date", "section", "title", "company", "locations", "source", "url", "fit", "legitimacy",
    "verdict", "work_auth", "pay", "posted", "reasons",
]


class State:
    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text()) if path.exists() else {}
        self.last_sent_date: str | None = data.get("last_sent_date")
        self.seen: dict[str, str] = data.get("seen", {})

    def is_seen(self, job: Job) -> bool:
        return job.uid in self.seen or job.dedupe_key in self.seen

    def mark(self, job: Job, today: date) -> None:
        for k in (job.uid, job.dedupe_key):
            self.seen.setdefault(k, today.isoformat())

    def save(self, today: date) -> None:
        cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"last_sent_date": self.last_sent_date, "seen": dict(sorted(self.seen.items()))}
        self.path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")


def append_log(path: Path, rows: list[tuple[str, Job]], today: date) -> None:
    """One row per emailed job → a dataset you can analyse later (Excel, pandas, Tableau)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        for section, j in rows:
            w.writerow(
                {
                    "date": today.isoformat(),
                    "section": section,
                    "title": j.title,
                    "company": j.company,
                    "locations": "; ".join(j.locations),
                    "source": j.source,
                    "url": j.url,
                    "fit": j.fit_score,
                    "legitimacy": j.legit_score,
                    "verdict": j.verdict,
                    "work_auth": j.auth_status,
                    "pay": j.pay_label(),
                    "posted": j.posted_at.date().isoformat() if j.posted_at else "",
                    "reasons": " | ".join(j.legit_reasons),
                }
            )
