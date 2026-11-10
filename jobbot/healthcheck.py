"""Check that one job source still responds and parses: `python -m jobbot.healthcheck "The Muse"`.
Prints a GitHub Actions annotation with the count; exits 1 if the source errors."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .sources import SkipSource, registry
from .utils import make_session

ROOT = Path(__file__).resolve().parent.parent


def main(name: str) -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    fn = registry()[name]
    try:
        jobs = fn(make_session(), cfg)
    except SkipSource as e:
        print(f"::notice title={name}::skipped ({e})")
        return 0
    except Exception as e:
        print(f"::error title={name}::{type(e).__name__}: {e}")
        return 1
    sample = "; ".join(f"{j.title} @ {j.company}" for j in jobs[:3])
    print(f"::notice title={name}::{len(jobs)} postings. e.g. {sample}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
