"""Generic importer that works for *any* registered source connector.

Instead of a bespoke importer per source, this reads the raw envelopes a
connector's downloader produced, runs them through that connector's
``normalize()`` and upserts the resulting Tender/Company/Award rows. It is the
single reuse point for: incremental updates, resume-after-interruption,
duplicate detection and provenance tracking (via ImportRun / ImportCheckpoint).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.connectors.base import NormalizedProcurementRecord
from app.connectors.registry import discover_connectors
from app.connectors.common.parse import now_utc
from app.models import Award, Company, ImportCheckpoint, ImportRun, Tender

logger = logging.getLogger(__name__)


@dataclass
class GenericImportStats:
    imported_tenders: int = 0
    imported_companies: int = 0
    imported_awards: int = 0
    duplicates_skipped: int = 0
    failed: int = 0
    files_processed: int = 0
    documents_preserved: int = 0
    duration_seconds: float = 0.0


class GenericConnectorImporter:
    def __init__(self, session: Session, source_name: str, batch_size: int = 100) -> None:
        self.session = session
        self.source_name = source_name
        self.batch_size = batch_size
        connector = discover_connectors().get(source_name)
        if connector is None:
            raise ValueError(f"No connector registered for source '{source_name}'.")
        self.connector = connector

    # -- public ------------------------------------------------------------
    def import_directory(self, directory: Path) -> GenericImportStats:
        files = sorted(directory.glob("*.json"))
        logger.info("Found %s %s envelopes in %s", len(files), self.source_name, directory)
        return self.import_files(files)

    def import_files(self, files: list[Path]) -> GenericImportStats:
        started_at = time.monotonic()
        stats = GenericImportStats()
        run = self._start_run(len(files))
        already = self._already_imported_source_ids()

        batch: list[NormalizedProcurementRecord] = []
        for path in files:
            record = self._load_record(path, stats)
            if record is None:
                continue
            if record.tender.metadata.source_record_id in already:
                stats.duplicates_skipped += 1
                continue
            stats.files_processed += 1
            stats.documents_preserved += len(record.documents)
            batch.append(record)
            if len(batch) >= self.batch_size:
                self._import_batch(batch, stats)
                self._checkpoint(record.tender.metadata.source_record_id, stats)
                batch.clear()

        if batch:
            self._import_batch(batch, stats)
            self._checkpoint(batch[-1].tender.metadata.source_record_id, stats)

        stats.duration_seconds = time.monotonic() - started_at
        self._finish_run(run, stats)
        self._log_summary(stats)
        return stats

    # -- loading -----------------------------------------------------------
    def _load_record(self, path: Path, stats: GenericImportStats) -> NormalizedProcurementRecord | None:
        try:
            with path.open("r", encoding="utf-8") as file:
                envelope = json.load(file)
            if not isinstance(envelope, dict):
                raise ValueError("envelope root is not an object")
            return self.connector.normalize(envelope)
        except Exception:
            stats.failed += 1
            logger.exception("Skipping invalid %s envelope: %s", self.source_name, path)
            return None

    def _already_imported_source_ids(self) -> set[str]:
        rows = self.session.scalars(
            select(Tender.source_record_id).where(
                (Tender.source_name == self.source_name) & (Tender.source_record_id.is_not(None))
            )
        )
        return {value for value in rows if value}

    # -- batch upsert (dedup on reference / source id / company / award pair)
    def _import_batch(self, records: list[NormalizedProcurementRecord], stats: GenericImportStats) -> None:
        try:
            self._import_batch_inner(records, stats)
            self.session.commit()
        except Exception:
            self.session.rollback()
            if len(records) == 1:
                stats.failed += 1
                logger.exception(
                    "Failed to import %s record %s; skipped.",
                    self.source_name,
                    records[0].tender.reference_number,
                )
                return
            logger.exception("Failed %s batch (size=%s); retrying individually.", self.source_name, len(records))
            for record in records:
                self._import_batch([record], stats)

    def _import_batch_inner(self, records: list[NormalizedProcurementRecord], stats: GenericImportStats) -> None:
        references = {record.tender.reference_number for record in records}
        source_ids = {record.tender.metadata.source_record_id for record in records}
        tenders_by_reference: dict[str, Tender] = {}
        seen_source_ids: set[str] = set()
        for tender in self.session.scalars(
            select(Tender).where(
                Tender.reference_number.in_(references)
                | ((Tender.source_name == self.source_name) & (Tender.source_record_id.in_(source_ids)))
            )
        ):
            tenders_by_reference[tender.reference_number] = tender
            if tender.source_record_id:
                seen_source_ids.add(tender.source_record_id)

        new_tenders: list[Tender] = []
        seen_references = set(tenders_by_reference)
        for record in records:
            meta = record.tender.metadata
            if record.tender.reference_number in seen_references or meta.source_record_id in seen_source_ids:
                stats.duplicates_skipped += 1
                continue
            seen_references.add(record.tender.reference_number)
            seen_source_ids.add(meta.source_record_id)
            new_tenders.append(
                Tender(
                    reference_number=record.tender.reference_number,
                    title=record.tender.title,
                    description=record.tender.description,
                    procuring_entity=record.tender.procuring_entity,
                    published_date=record.tender.published_date,
                    closing_date=record.tender.closing_date,
                    estimated_value=record.tender.estimated_value,
                    currency=record.tender.currency,
                    source_name=meta.source_name,
                    source_record_id=meta.source_record_id,
                    source_url=meta.source_url,
                    retrieved_at=meta.retrieved_at,
                )
            )
        self.session.add_all(new_tenders)
        self.session.flush()
        stats.imported_tenders += len(new_tenders)
        for tender in new_tenders:
            tenders_by_reference[tender.reference_number] = tender

        companies_by_key = self._upsert_companies(records, stats)
        self._upsert_awards(records, tenders_by_reference, companies_by_key, stats)

    def _upsert_companies(
        self, records: list[NormalizedProcurementRecord], stats: GenericImportStats
    ) -> dict[tuple[str, str | None], Company]:
        wanted: dict[tuple[str, str | None], object] = {}
        for record in records:
            for company in record.companies:
                wanted.setdefault(_company_key(company.name, company.registration_number), company)

        existing = self._existing_companies(wanted)
        new_companies = [
            Company(
                name=company.name,
                registration_number=company.registration_number,
                source_name=company.metadata.source_name,
                source_record_id=company.metadata.source_record_id,
                source_url=company.metadata.source_url,
                retrieved_at=company.metadata.retrieved_at,
            )
            for key, company in wanted.items()
            if key not in existing
        ]
        self.session.add_all(new_companies)
        self.session.flush()
        stats.imported_companies += len(new_companies)
        for company in new_companies:
            existing[_company_key(company.name, company.registration_number)] = company
        return existing

    def _existing_companies(self, wanted: dict) -> dict[tuple[str, str | None], Company]:
        registration_numbers = {c.registration_number for c in wanted.values() if c.registration_number}
        names = {c.name for c in wanted.values()}
        by_registration: dict[str, Company] = {}
        by_name: dict[str, Company] = {}
        if registration_numbers:
            for company in self.session.scalars(
                select(Company).where(Company.registration_number.in_(registration_numbers))
            ):
                if company.registration_number:
                    by_registration[company.registration_number] = company
        if names:
            for company in self.session.scalars(select(Company).where(Company.name.in_(names))):
                by_name[company.name] = company
        matched: dict[tuple[str, str | None], Company] = {}
        for key, company in wanted.items():
            found = by_registration.get(company.registration_number) if company.registration_number else None
            found = found or by_name.get(company.name)
            if found is not None:
                matched[key] = found
        return matched

    def _upsert_awards(
        self,
        records: list[NormalizedProcurementRecord],
        tenders_by_reference: dict[str, Tender],
        companies_by_key: dict[tuple[str, str | None], Company],
        stats: GenericImportStats,
    ) -> None:
        candidate_pairs = []
        for record in records:
            tender = tenders_by_reference.get(record.tender.reference_number)
            if tender is None:
                continue
            for award in record.awards:
                company = companies_by_key.get(_company_key(award.company_name, award.company_registration_number))
                if company is not None:
                    candidate_pairs.append((tender.id, company.id))

        existing_pairs: set[tuple] = set()
        if candidate_pairs:
            existing_pairs = set(
                self.session.execute(
                    select(Award.tender_id, Award.company_id).where(
                        tuple_(Award.tender_id, Award.company_id).in_(candidate_pairs)
                    )
                ).all()
            )

        new_awards: list[Award] = []
        seen = set(existing_pairs)
        for record in records:
            tender = tenders_by_reference.get(record.tender.reference_number)
            if tender is None:
                continue
            for award in record.awards:
                company = companies_by_key.get(_company_key(award.company_name, award.company_registration_number))
                if company is None:
                    stats.duplicates_skipped += 1
                    continue
                pair = (tender.id, company.id)
                if pair in seen:
                    stats.duplicates_skipped += 1
                    continue
                seen.add(pair)
                new_awards.append(
                    Award(
                        tender_id=tender.id,
                        company_id=company.id,
                        award_date=award.award_date,
                        award_value=award.award_value,
                        currency=award.currency,
                        source_name=award.metadata.source_name,
                        source_record_id=award.metadata.source_record_id,
                        source_url=award.metadata.source_url,
                        retrieved_at=award.metadata.retrieved_at,
                    )
                )
        self.session.add_all(new_awards)
        stats.imported_awards += len(new_awards)

    # -- provenance / checkpoints -----------------------------------------
    def _start_run(self, total: int) -> ImportRun:
        run = ImportRun(source=self.source_name, status="running", total_records=total)
        self.session.add(run)
        self.session.commit()
        return run

    def _finish_run(self, run: ImportRun, stats: GenericImportStats) -> None:
        run.status = "failed" if stats.failed and not stats.imported_tenders else "completed"
        run.processed_records = stats.files_processed
        run.imported_tenders = stats.imported_tenders
        run.imported_companies = stats.imported_companies
        run.imported_awards = stats.imported_awards
        run.duplicates_skipped = stats.duplicates_skipped
        run.failed_imports = stats.failed
        run.finished_at = now_utc()
        run.metadata_json = {"documents_preserved": stats.documents_preserved}
        self.session.commit()

    def _checkpoint(self, last_record: str, stats: GenericImportStats) -> None:
        checkpoint = self.session.scalar(
            select(ImportCheckpoint).where(ImportCheckpoint.source == self.source_name)
        )
        if checkpoint is None:
            checkpoint = ImportCheckpoint(source=self.source_name)
            self.session.add(checkpoint)
        checkpoint.last_processed_record = last_record[:500]
        checkpoint.last_successful_import_at = now_utc()
        checkpoint.records_imported = stats.imported_tenders
        checkpoint.duplicates_skipped = stats.duplicates_skipped
        checkpoint.failed_imports = stats.failed
        self.session.commit()

    def _log_summary(self, stats: GenericImportStats) -> None:
        totals = self.session.scalar(select(func.count()).select_from(Tender)) or 0
        logger.info(
            "%s import complete: tenders=%s companies=%s awards=%s duplicates=%s failed=%s docs=%s total_tenders=%s duration=%.2fs",
            self.source_name,
            stats.imported_tenders,
            stats.imported_companies,
            stats.imported_awards,
            stats.duplicates_skipped,
            stats.failed,
            stats.documents_preserved,
            totals,
            stats.duration_seconds,
        )


def _company_key(name: str, registration_number: str | None) -> tuple[str, str | None]:
    return (name.strip(), registration_number.strip() if registration_number else None)
