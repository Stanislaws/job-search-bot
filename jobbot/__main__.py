"""Command line entry point.

  python -m jobbot --dry-run          # build the digest, save output/digest.html, send nothing
  python -m jobbot                    # build + email + remember what was sent
  python -m jobbot --scheduled        # same, but only once per day after `send_hour` (used by GitHub Actions)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import digest, mailer, pipeline
from .state import State, append_log
from .utils import log

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jobbot")
    ap.add_argument("--config", default=ROOT / "config.yaml", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="don't email or update state; write output/digest.html")
    ap.add_argument("--scheduled", action="store_true", help="send at most once per local day, after send_hour")
    ap.add_argument("--ignore-seen", action="store_true", help="include jobs already emailed before (for previews)")
    ap.add_argument("--only", help="comma-separated source names to run, e.g. 'simplify,muse'")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = yaml.safe_load(args.config.read_text())
    tz = ZoneInfo(cfg["schedule"]["timezone"])
    now = datetime.now(timezone.utc)
    local = now.astimezone(tz)
    today = local.date()
    state = State(ROOT / "state" / "seen.json")

    if args.scheduled:
        if local.hour < cfg["schedule"]["send_hour"]:
            log.info("It's %s in %s — before send_hour; nothing to do.", local.strftime("%H:%M"), tz.key)
            return 0
        if state.last_sent_date == today.isoformat():
            log.info("Digest for %s already sent; nothing to do.", today)
            return 0

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    raw, source_status = pipeline.collect(cfg, only)
    kept, dropped = pipeline.evaluate(raw, cfg, now)
    merged = pipeline.merge_duplicates(kept)
    fresh = merged if args.ignore_seen else [j for j in merged if not state.is_seen(j)]
    sections = pipeline.build_sections(fresh, cfg)
    log.info("scanned=%d kept=%d unique=%d new=%d dropped=%s", len(raw), len(kept), len(merged), len(fresh), dropped)

    stats = {
        "scanned": len(raw),
        "matched": len(merged),
        "new": len(fresh),
        "sources": source_status,
        "local_date": local.strftime("%A, %B %-d"),
    }
    repo = os.getenv("GITHUB_REPOSITORY")
    repo_url = f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{repo}" if repo else cfg.get("repo_url", "")
    html_body, text_body = digest.render(sections, stats, now, repo_url)

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    (out / "digest.html").write_text(html_body, encoding="utf-8")
    (out / "digest.txt").write_text(text_body, encoding="utf-8")
    log.info("Wrote %s", out / "digest.html")

    shown = len(sections["internships"]) + len(sections["entry"])
    if args.dry_run:
        log.info("Dry run: %d jobs would be emailed (%d flagged).", shown, len(sections["flagged"]))
        return 0
    if shown == 0 and not cfg["email"].get("send_when_empty", True):
        log.info("Nothing new and send_when_empty is off.")
    else:
        subject = cfg["email"]["subject"].format(count=shown, date=local.strftime("%b %-d"))
        to = mailer.send(subject, html_body, text_body)
        log.info("Emailed %d jobs to %s", shown, to)

    rows = [(name, j) for name in ("internships", "entry", "flagged") for j in sections[name]]
    for _, j in rows:
        state.mark(j, today)
    state.last_sent_date = today.isoformat()
    state.save(today)
    append_log(ROOT / "data" / "jobs_log.csv", rows, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
