"""Large-scale procurement data acquisition (Phase X).

Runs the acquisition pipeline for the priority connectors: probe -> download
(paginated, resumable, retried) -> import (idempotent) -> delta report. Only
legally/publicly accessible data is fetched; blocked sources are reported with
their concrete blocker. Never fabricates data.

    python scripts/acquire_procurement.py                       # all priority sources
    python scripts/acquire_procurement.py --source world_bank   # one source
    python scripts/acquire_procurement.py --limit 50            # cap new downloads/source
    python scripts/acquire_procurement.py --no-download         # import-on-disk only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

import app.models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.services.procurement_platform.acquisition import PRIORITY_SOURCES, acquire, acquire_all  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire public procurement data.")
    parser.add_argument("--source", help="Acquire a single source (default: all priority sources).")
    parser.add_argument("--limit", type=int, default=25, help="Max new downloads per source.")
    parser.add_argument("--data-root", type=Path, default=ROOT_DIR.parent / "data" / "raw")
    parser.add_argument("--no-download", action="store_true", help="Import on-disk envelopes only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    download = not args.no_download
    with SessionLocal() as session:
        if args.source:
            results = [acquire(session, args.source, args.data_root, limit=args.limit, download=download)]
        else:
            results = acquire_all(session, args.data_root, limit=args.limit, download=download)
    payload = [vars(r) for r in results]
    print(json.dumps({"priority_sources": PRIORITY_SOURCES, "results": payload}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
