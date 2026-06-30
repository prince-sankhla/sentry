from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.connectors.world_bank import WorldBankProcurementDownloader  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download World Bank procurement notices.")
    parser.add_argument("--limit", type=int, default=100, help="Total notices to have in the raw directory.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data" / "raw" / "world_bank",
        help="Directory where World Bank notice JSON files will be written.",
    )
    parser.add_argument("--rows", type=int, default=100, help="World Bank API page size.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    stats = WorldBankProcurementDownloader(
        output_dir=args.output_dir,
        rows=args.rows,
        timeout=args.timeout,
    ).download(limit=args.limit)

    print(f"Downloaded: {stats.downloaded_notices}")
    print(f"Skipped Existing: {stats.skipped_existing}")
    print(f"Failed: {stats.failed}")
    print(f"Pages: {stats.pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
