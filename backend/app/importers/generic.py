"""Generic importer that works for *any* registered source connector.

Instead of a bespoke importer per source, this reads the raw envelopes a
connector's downloader produced, runs them through that connector's
``normalize()`` and upserts the resulting Tender/Company/Award/Document rows.
It is the single reuse point for:

* **incremental updates** — an existing tender is *updated in place* (not
  skipped) when its normalized content changed;
* **resume-after-interruption** — every processed record writes a
  ``SourceRecordVersion`` row (committed per batch), so re-running the same
  directory skips everything already imported at the same content hash;
* **document preservation** — every ``NormalizedDocument`` is upserted into the
  ``documents`` table so attachment evidence is never lost;
* **version history** — each import/update records an immutable snapshot in
  ``source_record_versions`` keyed by ``(source, record id, content hash)``;
* **provenance / checkpoints** — ``ImportRun`` and ``ImportCheckpoint`` track
  progress so an interrupted run can be observed and resumed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.connectors.base import NormalizedProcurementRecord
from app.connectors.common.envelope import content_hash
from app.connectors.common.parse import now_utc
from app.connectors.registry import discover_connectors
from app.models import (
    Award,
    Company,
    Document,
    ImportCheckpoint,
    ImportRun,
    SourceRecordVersion,
    Tender,
)
from app.normalization import (
    normalize_currency,
    normalize_document_title,
    normalize_org_name,
    normalize_reference,
    normalize_registration,
    org_match_key,
)
import json

logger = logging.getLogger(__name__)


@dataclass
class GenericImportStats:
    imported_tenders: int = 0
    updated_tenders: int = 0
    imported_companies: int = 0
    imported_awards: int = 0
    imported_documents: int = 0
    duplicates_skipped: int = 0
    unchanged_records: int = 0
    failed: int = 0
    files_processed: int = 0
    documents_preserved: int = 0
    versions_recorded: int = 0
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
        self.connector_version = getattr(connector.metadata, "version", "1.0")
        self._run: ImportRun | None = None

    # -- public ------------------------------------------------------------
    def import_directory(self, directory: Path) -> GenericImportStats:
        files = sorted(directory.glob("*.json"))
        logger.info("Found %s %s envelopes in %s", len(files), self.source_name, directory)
        return self.import_files(files)

    def import_files(self, files: list[Path]) -> GenericImportStats:
        started_at = time.monotonic()
        stats = GenericImportStats()
        run = self._start_run(len(files))
        self._run = run

        batch: list[tuple[NormalizedProcurementRecord, str]] = []
        try:
            for path in files:
                record = self._load_record(path, stats)
                if record is None:
                    continue
                record_hash = _record_content_hash(record)
                # Resume / idempotency: an identical content hash was already
                # imported for this source record -> nothing changed, skip.
                if self._version_exists(record, record_hash):
                    stats.unchanged_records += 1
                    continue
                stats.files_processed += 1
                stats.documents_preserved += len(record.documents)
                batch.append((record, record_hash))
                if len(batch) >= self.batch_size:
                    self._import_batch(batch, stats)
                    self._checkpoint(batch[-1][0].tender.metadata.source_record_id, stats)
                    batch.clear()

            if batch:
                self._import_batch(batch, stats)
                self._checkpoint(batch[-1][0].tender.metadata.source_record_id, stats)
        finally:
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

    def _version_exists(self, record: NormalizedProcurementRecord, record_hash: str) -> bool:
        meta = record.tender.metadata
        return (
            self.session.scalar(
                select(SourceRecordVersion.id).where(
                    SourceRecordVersion.source_name == meta.source_name,
                    SourceRecordVersion.source_record_id == meta.source_record_id,
                    SourceRecordVersion.content_hash == record_hash,
                )
            )
            is not None
        )

    # -- batch upsert ------------------------------------------------------
    def _import_batch(
        self, records: list[tuple[NormalizedProcurementRecord, str]], stats: GenericImportStats
    ) -> None:
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
                    records[0][0].tender.reference_number,
                )
                return
            logger.exception("Failed %s batch (size=%s); retrying individually.", self.source_name, len(records))
            for record in records:
                self._import_batch([record], stats)

    def _import_batch_inner(
        self, records: list[tuple[NormalizedProcurementRecord, str]], stats: GenericImportStats
    ) -> None:
        existing = self._load_existing_tenders([record for record, _ in records])
        tenders_by_reference: dict[str, Tender] = {}
        for record, record_hash in records:
            meta = record.tender.metadata
            # Identity uses the connector's verbatim reference so re-imports match
            # rows written by earlier importers; normalization is reserved for
            # de-duplication keys and content hashing, never the stored identity.
            reference = record.tender.reference_number
            tender = existing.get(reference) or existing.get(_source_key(meta.source_name, meta.source_record_id))
            if tender is None:
                tender = self._insert_tender(record, reference)
                stats.imported_tenders += 1
                action = "imported"
            else:
                changed = self._update_tender(tender, record)
                action = "updated" if changed else "unchanged"
                if changed:
                    stats.updated_tenders += 1
                else:
                    stats.unchanged_records += 1
            tenders_by_reference[reference] = tender
            existing[reference] = tender
            if meta.source_record_id:
                existing[_source_key(meta.source_name, meta.source_record_id)] = tender
            self._record_version(record, record_hash, action)
            stats.versions_recorded += 1

        self.session.flush()

        companies_by_key = self._upsert_companies([r for r, _ in records], stats)
        self._upsert_awards([r for r, _ in records], tenders_by_reference, companies_by_key, stats)
        self._upsert_documents([r for r, _ in records], tenders_by_reference, stats)

    def _load_existing_tenders(self, records: list[NormalizedProcurementRecord]) -> dict[str, Tender]:
        references = {r.tender.reference_number for r in records}
        source_ids = {r.tender.metadata.source_record_id for r in records if r.tender.metadata.source_record_id}
        found: dict[str, Tender] = {}
        for tender in self.session.scalars(
            select(Tender).where(
                Tender.reference_number.in_(references)
                | ((Tender.source_name == self.source_name) & (Tender.source_record_id.in_(source_ids)))
            )
        ):
            found[tender.reference_number] = tender
            if tender.source_record_id:
                found[_source_key(tender.source_name, tender.source_record_id)] = tender
        return found

    def _insert_tender(self, record: NormalizedProcurementRecord, reference: str) -> Tender:
        meta = record.tender.metadata
        tender = Tender(
            reference_number=reference,
            title=record.tender.title,
            description=record.tender.description,
            procuring_entity=normalize_org_name(record.tender.procuring_entity),
            published_date=record.tender.published_date,
            closing_date=record.tender.closing_date,
            estimated_value=record.tender.estimated_value,
            currency=normalize_currency(record.tender.currency),
            source_name=meta.source_name,
            source_record_id=meta.source_record_id,
            source_url=meta.source_url,
            retrieved_at=meta.retrieved_at,
        )
        self.session.add(tender)
        return tender

    def _update_tender(self, tender: Tender, record: NormalizedProcurementRecord) -> bool:
        """Update an existing tender in place; return True if any field changed."""
        meta = record.tender.metadata
        updates = {
            "title": record.tender.title,
            "description": record.tender.description,
            "procuring_entity": normalize_org_name(record.tender.procuring_entity),
            "published_date": record.tender.published_date,
            "closing_date": record.tender.closing_date,
            "estimated_value": record.tender.estimated_value,
            "currency": normalize_currency(record.tender.currency),
            "source_url": meta.source_url,
            "retrieved_at": meta.retrieved_at,
        }
        changed = False
        for field, value in updates.items():
            # Never overwrite a present value with a null/empty one.
            if value in (None, "") and getattr(tender, field) is not None:
                continue
            if getattr(tender, field) != value:
                setattr(tender, field, value)
                changed = True
        return changed

    def _upsert_companies(
        self, records: list[NormalizedProcurementRecord], stats: GenericImportStats
    ) -> dict[tuple[str, str | None], Company]:
        wanted: dict[tuple[str, str | None], object] = {}
        for record in records:
            for company in record.companies:
                wanted.setdefault(_company_key(company.name, company.registration_number), company)

        existing = self._existing_companies(wanted)
        new_companies: list[Company] = []
        for key, company in wanted.items():
            if key in existing:
                continue
            row = Company(
                name=normalize_org_name(company.name) or company.name,
                registration_number=normalize_registration(company.registration_number),
                source_name=company.metadata.source_name,
                source_record_id=company.metadata.source_record_id,
                source_url=company.metadata.source_url,
                retrieved_at=company.metadata.retrieved_at,
            )
            existing[key] = row
            new_companies.append(row)
        self.session.add_all(new_companies)
        self.session.flush()
        stats.imported_companies += len(new_companies)
        return existing

    def _existing_companies(self, wanted: dict) -> dict[tuple[str, str | None], Company]:
        registration_numbers = {
            normalize_registration(c.registration_number)
            for c in wanted.values()
            if c.registration_number
        }
        registration_numbers.discard(None)
        names = {normalize_org_name(c.name) or c.name for c in wanted.values()}
        by_registration: dict[str, Company] = {}
        by_name_key: dict[str | None, Company] = {}
        if registration_numbers:
            for company in self.session.scalars(
                select(Company).where(Company.registration_number.in_(registration_numbers))
            ):
                if company.registration_number:
                    by_registration[company.registration_number] = company
        if names:
            for company in self.session.scalars(select(Company).where(Company.name.in_(names))):
                by_name_key[org_match_key(company.name)] = company
        matched: dict[tuple[str, str | None], Company] = {}
        for key, company in wanted.items():
            registration = normalize_registration(company.registration_number)
            found = by_registration.get(registration) if registration else None
            found = found or by_name_key.get(org_match_key(company.name))
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
            tender = self._tender_for(record, tenders_by_reference)
            if tender is None or tender.id is None:
                continue
            for award in record.awards:
                company = companies_by_key.get(_company_key(award.company_name, award.company_registration_number))
                if company is not None and company.id is not None:
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
            tender = self._tender_for(record, tenders_by_reference)
            if tender is None:
                continue
            for award in record.awards:
                company = companies_by_key.get(_company_key(award.company_name, award.company_registration_number))
                if company is None:
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
                        currency=normalize_currency(award.currency),
                        source_name=award.metadata.source_name,
                        source_record_id=award.metadata.source_record_id,
                        source_url=award.metadata.source_url,
                        retrieved_at=award.metadata.retrieved_at,
                    )
                )
        self.session.add_all(new_awards)
        stats.imported_awards += len(new_awards)

    def _upsert_documents(
        self,
        records: list[NormalizedProcurementRecord],
        tenders_by_reference: dict[str, Tender],
        stats: GenericImportStats,
    ) -> None:
        """Preserve every document/attachment as a ``documents`` row.

        Deduplicated on the ``(tender_id, title)`` unique constraint so re-imports
        never duplicate evidence; the content hash of the URL is stored so future
        OCR/RAG layers can detect changed attachments.
        """
        wanted: dict[tuple, dict] = {}
        for record in records:
            tender = self._tender_for(record, tenders_by_reference)
            if tender is None or tender.id is None:
                continue
            for document in record.documents:
                title = normalize_document_title(document.title)
                key = (tender.id, title)
                doc_type = document.document_type or "attachment"
                wanted.setdefault(
                    key,
                    {
                        "tender_id": tender.id,
                        "title": title,
                        "document_type": doc_type,
                        "url": document.url,
                        "content_hash": content_hash(document.url) if document.url else None,
                        "source_name": document.metadata.source_name,
                        "source_record_id": document.metadata.source_record_id,
                        "retrieved_at": document.metadata.retrieved_at,
                        # -- evidence provenance (Phase 4) -----------------
                        "connector_name": self.source_name,
                        "connector_version": self.connector_version,
                        "source_url": document.metadata.source_url,
                        "evidence_hash": _evidence_hash(document),
                        "evidence_version": 1,
                        "import_run_id": self._run.id if self._run is not None else None,
                        "verified_at": now_utc(),
                    },
                )

        if not wanted:
            return

        existing_pairs = set(
            self.session.execute(
                select(Document.tender_id, Document.title).where(
                    tuple_(Document.tender_id, Document.title).in_(list(wanted.keys()))
                )
            ).all()
        )
        new_documents = [
            Document(**payload) for key, payload in wanted.items() if key not in existing_pairs
        ]
        self.session.add_all(new_documents)
        stats.imported_documents += len(new_documents)

    def _tender_for(
        self, record: NormalizedProcurementRecord, tenders_by_reference: dict[str, Tender]
    ) -> Tender | None:
        return tenders_by_reference.get(record.tender.reference_number)

    def _record_version(
        self, record: NormalizedProcurementRecord, record_hash: str, action: str
    ) -> None:
        meta = record.tender.metadata
        self.session.add(
            SourceRecordVersion(
                source_name=meta.source_name,
                source_record_id=meta.source_record_id,
                reference_number=(normalize_reference(record.tender.reference_number) or record.tender.reference_number)[:100],
                content_hash=record_hash,
                source_url=meta.source_url,
                retrieved_at=meta.retrieved_at,
                action=action,
                snapshot_json=_record_snapshot(record),
            )
        )

    # -- provenance / checkpoints -----------------------------------------
    def _start_run(self, total: int) -> ImportRun:
        run = ImportRun(source=self.source_name, status="running", total_records=total)
        self.session.add(run)
        self.session.commit()
        return run

    def _finish_run(self, run: ImportRun, stats: GenericImportStats) -> None:
        run.status = "failed" if stats.failed and not stats.files_processed else "completed"
        run.processed_records = stats.files_processed
        run.imported_tenders = stats.imported_tenders
        run.imported_companies = stats.imported_companies
        run.imported_awards = stats.imported_awards
        run.duplicates_skipped = stats.duplicates_skipped
        run.failed_imports = stats.failed
        run.finished_at = now_utc()
        run.metadata_json = {
            "updated_tenders": stats.updated_tenders,
            "imported_documents": stats.imported_documents,
            "documents_preserved": stats.documents_preserved,
            "versions_recorded": stats.versions_recorded,
            "unchanged_records": stats.unchanged_records,
        }
        self.session.commit()

    def _checkpoint(self, last_record: str, stats: GenericImportStats) -> None:
        checkpoint = self.session.scalar(
            select(ImportCheckpoint).where(ImportCheckpoint.source == self.source_name)
        )
        if checkpoint is None:
            checkpoint = ImportCheckpoint(source=self.source_name)
            self.session.add(checkpoint)
        checkpoint.last_processed_record = (last_record or "")[:500]
        checkpoint.last_successful_import_at = now_utc()
        checkpoint.records_imported = stats.imported_tenders + stats.updated_tenders
        checkpoint.duplicates_skipped = stats.duplicates_skipped
        checkpoint.failed_imports = stats.failed
        self.session.commit()

    def _log_summary(self, stats: GenericImportStats) -> None:
        totals = self.session.scalar(select(func.count()).select_from(Tender)) or 0
        logger.info(
            "%s import complete: new=%s updated=%s companies=%s awards=%s docs=%s "
            "unchanged=%s dupes=%s failed=%s versions=%s total_tenders=%s duration=%.2fs",
            self.source_name,
            stats.imported_tenders,
            stats.updated_tenders,
            stats.imported_companies,
            stats.imported_awards,
            stats.imported_documents,
            stats.unchanged_records,
            stats.duplicates_skipped,
            stats.failed,
            stats.versions_recorded,
            totals,
            stats.duration_seconds,
        )


def _company_key(name: str, registration_number: str | None) -> tuple[str, str | None]:
    """Match key for company de-duplication: canonical org key + registration."""
    key = org_match_key(name) or (name or "").strip().casefold()
    return (key, normalize_registration(registration_number))


def _source_key(source_name: str | None, source_record_id: str | None) -> str:
    return f"{source_name or ''}::{source_record_id or ''}"


def _evidence_hash(document) -> str:
    """Deterministic SHA-256 over a document's provenance identity.

    Distinct from ``content_hash`` (URL only): folds in title, type, source and
    the source record id so an evidence row's integrity can be re-verified.
    """
    return content_hash(
        {
            "url": document.url,
            "title": document.title,
            "document_type": document.document_type,
            "source_name": document.metadata.source_name,
            "source_record_id": document.metadata.source_record_id,
        }
    )


def _record_content_hash(record: NormalizedProcurementRecord) -> str:
    """Stable SHA-256 over the *normalized* content of a record.

    Any change to tender fields, companies, awards or document URLs produces a
    new hash, which is what drives update-vs-skip and version history.
    """
    return content_hash(_record_snapshot(record))


def _record_snapshot(record: NormalizedProcurementRecord) -> dict:
    tender = record.tender
    return {
        "tender": {
            "reference": normalize_reference(tender.reference_number),
            "title": tender.title,
            "description": tender.description,
            "buyer": normalize_org_name(tender.procuring_entity),
            "published_date": _iso(tender.published_date),
            "closing_date": _iso(tender.closing_date),
            "estimated_value": _num(tender.estimated_value),
            "currency": normalize_currency(tender.currency),
        },
        "companies": sorted(
            [
                {
                    "name": normalize_org_name(c.name),
                    "registration": normalize_registration(c.registration_number),
                }
                for c in record.companies
            ],
            key=lambda item: (item["name"] or "", item["registration"] or ""),
        ),
        "awards": sorted(
            [
                {
                    "company": normalize_org_name(a.company_name),
                    "value": _num(a.award_value),
                    "currency": normalize_currency(a.currency),
                    "date": _iso(a.award_date),
                }
                for a in record.awards
            ],
            key=lambda item: (item["company"] or "", item["value"] or ""),
        ),
        "documents": sorted(d.url for d in record.documents if d.url),
    }


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _num(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
