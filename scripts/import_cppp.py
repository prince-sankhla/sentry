from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import func, select


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.connectors.cppp import CPPPImporter  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Award, Company, Tender  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import raw CPPP procurement notice JSON files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT_DIR / "data" / "raw" / "cppp",
        help="Directory containing raw CPPP notice JSON files.",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Number of files to import per batch.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    with SessionLocal() as session:
        stats = CPPPImporter(session=session, batch_size=args.batch_size).import_directory(args.input_dir)
        tender_count = session.scalar(select(func.count()).select_from(Tender)) or 0
        company_count = session.scalar(select(func.count()).select_from(Company)) or 0
        award_count = session.scalar(select(func.count()).select_from(Award)) or 0

    print(f"Imported Tenders: {stats.imported_tenders}")
    print(f"Imported Companies: {stats.imported_companies}")
    print(f"Imported Awards: {stats.imported_awards}")
    print(f"Skipped: {stats.skipped}")
    print(f"Database Tenders: {tender_count}")
    print(f"Database Companies: {company_count}")
    print(f"Database Awards: {award_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
