from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.clients.prozorro import ProzorroClient

logger = logging.getLogger(__name__)


@dataclass
class ProzorroDownloadStats:
    downloaded: int = 0
    skipped_existing: int = 0
    failed: int = 0
    pages: int = 0
    last_offset: str | None = None


class ProzorroHistoricalDownloader:
    def __init__(self, output_dir: Path, timeout: float = 20.0, page_size: int = 100) -> None:
        self.output_dir = output_dir
        self.client = ProzorroClient(timeout=timeout)
        self.page_size = min(max(page_size, 1), 100)

    def download(self, limit: int = 1000, offset: str | None = None) -> ProzorroDownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = ProzorroDownloadStats(last_offset=offset)
        downloaded_or_existing = self._downloaded_count()

        while downloaded_or_existing < limit:
            payload = self.client.fetch_tender_list(
                limit=min(self.page_size, limit - downloaded_or_existing),
                offset=stats.last_offset,
                descending=True,
            )
            tenders = payload.get("data")
            if not isinstance(tenders, list) or not tenders:
                break

            stats.pages += 1
            for row in tenders:
                tender_id = row.get("id") if isinstance(row, dict) else None
                if not isinstance(tender_id, str) or not tender_id:
                    stats.failed += 1
                    continue

                output_path = self.output_dir / f"{tender_id}.json"
                if output_path.exists():
                    stats.skipped_existing += 1
                    downloaded_or_existing += 1
                    continue

                try:
                    tender = self.client.fetch_tender(tender_id)
                    self._save_tender(output_path, tender_id, tender)
                    stats.downloaded += 1
                    downloaded_or_existing += 1
                except Exception:
                    stats.failed += 1
                    logger.exception("Failed to download Prozorro tender %s", tender_id)

            next_page = payload.get("next_page")
            next_offset = next_page.get("offset") if isinstance(next_page, dict) else None
            if not next_offset:
                break
            stats.last_offset = str(next_offset)

        return stats

    def _downloaded_count(self) -> int:
        return sum(1 for _ in self.output_dir.glob("*.json")) if self.output_dir.exists() else 0

    def _save_tender(self, output_path: Path, tender_id: str, tender: dict[str, Any]) -> None:
        envelope = {
            "source_name": "prozorro",
            "source_record_id": tender_id,
            "source_url": f"https://prozorro.gov.ua/tender/{tender.get('tenderID') or tender_id}",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "data": tender,
        }
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(envelope, file, ensure_ascii=False, indent=2)
            file.write("\n")
