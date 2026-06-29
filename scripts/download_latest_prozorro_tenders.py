from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.clients.prozorro import ProzorroClient  # noqa: E402


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download latest tenders from Prozorro.")
    parser.add_argument("--limit", type=int, default=100, help="Number of latest tenders to download.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data" / "raw" / "prozorro",
        help="Directory where tender JSON files will be written.",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP request timeout in seconds.")
    return parser.parse_args()


def save_tender(output_dir: Path, tender_id: str, tender: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{tender_id}.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(tender, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return output_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()

    client = ProzorroClient(timeout=args.timeout)
    logger.info("Fetching latest %s tender IDs", args.limit)
    tender_ids = client.fetch_latest_tender_ids(limit=args.limit)
    logger.info("Found %s tender IDs", len(tender_ids))

    downloaded = 0
    failed = 0

    for index, tender_id in enumerate(tender_ids, start=1):
        logger.info("Downloading tender %s/%s: %s", index, len(tender_ids), tender_id)
        try:
            tender = client.fetch_tender(tender_id)
            output_path = save_tender(args.output_dir, tender_id, tender)
        except Exception:
            failed += 1
            logger.exception("Failed to download tender %s; skipping", tender_id)
            continue

        downloaded += 1
        logger.info("Saved tender %s to %s", tender_id, output_path)

    logger.info("Finished: downloaded=%s failed=%s output_dir=%s", downloaded, failed, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
