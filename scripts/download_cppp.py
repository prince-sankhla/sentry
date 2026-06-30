from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.connectors.cppp import CPPPDownloader  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download CPPP procurement notices.")
    parser.add_argument("--limit", type=int, default=100, help="Total CPPP notices to have in the raw directory.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data" / "raw" / "cppp",
        help="Directory where CPPP notice JSON files will be written.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds.")
    parser.add_argument("--max-list-pages", type=int, default=20, help="Maximum CPPP list pages to traverse.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    stats = CPPPDownloader(
        output_dir=args.output_dir,
        timeout=args.timeout,
        max_list_pages=args.max_list_pages,
    ).download(limit=args.limit)

    print(f"Downloaded: {stats.downloaded}")
    print(f"Skipped Existing: {stats.skipped_existing}")
    print(f"Failed: {stats.failed}")
    print(f"List Pages: {stats.list_pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
