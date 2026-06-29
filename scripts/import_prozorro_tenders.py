from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.db.session import SessionLocal  # noqa: E402
from app.importers.prozorro import ProzorroImporter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import raw Prozorro tender JSON files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT_DIR / "data" / "raw" / "prozorro",
        help="Directory containing raw Prozorro tender JSON files.",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Number of files to import per batch.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    with SessionLocal() as session:
        stats = ProzorroImporter(session=session, batch_size=args.batch_size).import_directory(args.input_dir)

    print(f"Tenders imported: {stats.tenders_imported}")
    print(f"Companies imported: {stats.companies_imported}")
    print(f"Awards imported: {stats.awards_imported}")
    print(f"Records skipped: {stats.records_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
