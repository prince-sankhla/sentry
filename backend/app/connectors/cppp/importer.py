from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.cppp.mapper import MappedNotice, map_notice_file
from app.models import Award, Company, Tender

logger = logging.getLogger(__name__)


@dataclass
class CPPPImportStats:
    imported_tenders: int = 0
    imported_companies: int = 0
    imported_awards: int = 0
    skipped: int = 0
    files_processed: int = 0
    duration_seconds: float = 0.0


class CPPPImporter:
    def __init__(self, session: Session, batch_size: int = 100) -> None:
        self.session = session
        self.batch_size = batch_size

    def import_directory(self, directory: Path) -> CPPPImportStats:
        files = sorted(directory.glob("*.json"))
        logger.info("Found %s CPPP JSON files in %s", len(files), directory)
        return self.import_files(files)

    def import_files(self, files: list[Path]) -> CPPPImportStats:
        started_at = time.monotonic()
        stats = CPPPImportStats()
        batch: list[MappedNotice] = []
        for path in files:
            try:
                batch.append(map_notice_file(path))
                stats.files_processed += 1
            except Exception:
                stats.skipped += 1
                logger.exception("Skipping invalid CPPP record file: %s", path)
                continue

            if len(batch) >= self.batch_size:
                self._import_batch(batch, stats)
                batch.clear()

        if batch:
            self._import_batch(batch, stats)

        stats.duration_seconds = time.monotonic() - started_at
        self._log_database_summary(stats)
        return stats

    def _import_batch(self, notices: list[MappedNotice], stats: CPPPImportStats) -> None:
        try:
            self._import_batch_inner(notices, stats)
            self.session.commit()
        except Exception:
            self.session.rollback()
            if len(notices) == 1:
                stats.skipped += 1
                logger.exception("Failed to import CPPP notice %s; skipped.", notices[0].tender.reference_number)
                return
            logger.exception("Failed to import CPPP batch; retrying records individually batch_size=%s", len(notices))
            for notice in notices:
                self._import_batch([notice], stats)

    def _import_batch_inner(self, notices: list[MappedNotice], stats: CPPPImportStats) -> None:
        references = {notice.tender.reference_number for notice in notices}
        source_ids = {notice.tender.metadata.source_record_id for notice in notices}
        existing_references: set[str] = set()
        existing_source_ids: set[str] = set()

        for tender in self.session.scalars(
            select(Tender).where(
                (Tender.reference_number.in_(references))
                | ((Tender.source_name == "cppp") & (Tender.source_record_id.in_(source_ids)))
            )
        ):
            existing_references.add(tender.reference_number)
            if tender.source_name == "cppp" and tender.source_record_id:
                existing_source_ids.add(tender.source_record_id)

        new_tenders: list[Tender] = []
        seen_references = set(existing_references)
        seen_source_ids = set(existing_source_ids)
        for notice in notices:
            tender = notice.tender
            if tender.reference_number in seen_references or tender.metadata.source_record_id in seen_source_ids:
                stats.skipped += 1
                logger.info("Skipping duplicate CPPP tender %s", tender.reference_number)
                continue
            seen_references.add(tender.reference_number)
            seen_source_ids.add(tender.metadata.source_record_id)
            new_tenders.append(
                Tender(
                    reference_number=tender.reference_number,
                    title=tender.title,
                    description=tender.description,
                    procuring_entity=tender.procuring_entity,
                    published_date=tender.published_date,
                    closing_date=tender.closing_date,
                    estimated_value=tender.estimated_value,
                    currency=tender.currency,
                    source_name=tender.metadata.source_name,
                    source_record_id=tender.metadata.source_record_id,
                    source_url=tender.metadata.source_url,
                    retrieved_at=tender.metadata.retrieved_at,
                )
            )

        self.session.add_all(new_tenders)
        self.session.flush()
        stats.imported_tenders += len(new_tenders)
        logger.info("Imported CPPP batch: tenders=%s companies=0 awards=0 skipped=%s", len(new_tenders), stats.skipped)

    def _log_database_summary(self, stats: CPPPImportStats) -> None:
        total_tenders = self.session.scalar(select(func.count()).select_from(Tender)) or 0
        total_companies = self.session.scalar(select(func.count()).select_from(Company)) or 0
        total_awards = self.session.scalar(select(func.count()).select_from(Award)) or 0
        logger.info(
            "CPPP import complete: total_tenders=%s total_companies=%s total_awards=%s duration_seconds=%.2f skipped=%s",
            total_tenders,
            total_companies,
            total_awards,
            stats.duration_seconds,
            stats.skipped,
        )
