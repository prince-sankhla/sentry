from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.connectors.world_bank.mapper import map_notice_file
from app.connectors.world_bank.models import MappedCompany, MappedNotice
from app.models import Award, Company, Tender

logger = logging.getLogger(__name__)


@dataclass
class WorldBankImportStats:
    imported_tenders: int = 0
    imported_companies: int = 0
    imported_awards: int = 0
    skipped: int = 0
    files_processed: int = 0
    duration_seconds: float = 0.0


class WorldBankProcurementImporter:
    def __init__(self, session: Session, batch_size: int = 100) -> None:
        self.session = session
        self.batch_size = batch_size

    def import_directory(self, directory: Path) -> WorldBankImportStats:
        files = sorted(directory.glob("*.json"))
        logger.info("Found %s World Bank JSON files in %s", len(files), directory)
        return self.import_files(files)

    def import_files(self, files: list[Path]) -> WorldBankImportStats:
        started_at = time.monotonic()
        stats = WorldBankImportStats()
        batch: list[MappedNotice] = []
        for path in files:
            try:
                batch.append(map_notice_file(path))
                stats.files_processed += 1
            except Exception:
                stats.skipped += 1
                logger.exception("Skipping invalid World Bank notice file: %s", path)
                continue

            if len(batch) >= self.batch_size:
                self._import_batch(batch, stats)
                batch.clear()

        if batch:
            self._import_batch(batch, stats)

        stats.duration_seconds = time.monotonic() - started_at
        self._log_database_summary(stats)
        return stats

    def _import_batch(self, notices: list[MappedNotice], stats: WorldBankImportStats) -> None:
        try:
            self._import_batch_inner(notices, stats)
            self.session.commit()
        except Exception:
            self.session.rollback()
            if len(notices) == 1:
                stats.skipped += 1
                logger.exception(
                    "Failed to import World Bank notice %s; skipped.",
                    notices[0].tender.metadata.source_record_id,
                )
                return

            logger.exception(
                "Failed to import World Bank batch; retrying records individually batch_size=%s",
                len(notices),
            )
            for notice in notices:
                self._import_batch([notice], stats)

    def _import_batch_inner(self, notices: list[MappedNotice], stats: WorldBankImportStats) -> None:
        references = {notice.tender.reference_number for notice in notices}
        source_ids = {notice.tender.metadata.source_record_id for notice in notices}
        existing_tenders_by_reference: dict[str, Tender] = {}
        existing_source_ids: set[str] = set()
        for tender in self.session.scalars(
            select(Tender).where(
                (Tender.reference_number.in_(references))
                | (
                    (Tender.source_name == "world_bank")
                    & (Tender.source_record_id.in_(source_ids))
                )
            )
        ):
            existing_tenders_by_reference[tender.reference_number] = tender
            if tender.source_name == "world_bank" and tender.source_record_id:
                existing_source_ids.add(tender.source_record_id)

        new_tenders = []
        seen_references = set(existing_tenders_by_reference)
        seen_source_ids = set(existing_source_ids)
        for notice in notices:
            if (
                notice.tender.reference_number in seen_references
                or notice.tender.metadata.source_record_id in seen_source_ids
            ):
                stats.skipped += 1
                logger.info("Skipping duplicate World Bank tender %s", notice.tender.reference_number)
                continue
            seen_references.add(notice.tender.reference_number)
            seen_source_ids.add(notice.tender.metadata.source_record_id)
            new_tenders.append(
                Tender(
                    reference_number=notice.tender.reference_number,
                    title=notice.tender.title,
                    description=notice.tender.description,
                    procuring_entity=notice.tender.procuring_entity,
                    published_date=notice.tender.published_date,
                    closing_date=notice.tender.closing_date,
                    estimated_value=notice.tender.estimated_value,
                    currency=notice.tender.currency,
                    source_name=notice.tender.metadata.source_name,
                    source_record_id=notice.tender.metadata.source_record_id,
                    source_url=notice.tender.metadata.source_url,
                    retrieved_at=notice.tender.metadata.retrieved_at,
                )
            )

        self.session.add_all(new_tenders)
        self.session.flush()
        stats.imported_tenders += len(new_tenders)
        for tender in new_tenders:
            existing_tenders_by_reference[tender.reference_number] = tender

        parsed_companies = _dedupe_companies(
            company for notice in notices for company in notice.companies
        )
        existing_companies = self._get_existing_companies(parsed_companies)
        new_companies = [
            Company(
                name=company.name,
                registration_number=company.registration_number,
                source_name=company.metadata.source_name,
                source_record_id=company.metadata.source_record_id,
                source_url=company.metadata.source_url,
                retrieved_at=company.metadata.retrieved_at,
            )
            for key, company in parsed_companies.items()
            if key not in existing_companies
        ]

        self.session.add_all(new_companies)
        self.session.flush()
        stats.imported_companies += len(new_companies)
        for company in new_companies:
            existing_companies[_company_key(company.name, company.registration_number)] = company

        award_pairs = []
        for notice in notices:
            tender = existing_tenders_by_reference.get(notice.tender.reference_number)
            if tender is None:
                continue
            for award in notice.awards:
                company = existing_companies.get(_company_key(award.company_name, award.company_registration_number))
                if company is not None:
                    award_pairs.append((tender.id, company.id))

        existing_award_pairs = set()
        if award_pairs:
            existing_award_pairs = set(
                self.session.execute(
                    select(Award.tender_id, Award.company_id).where(
                        tuple_(Award.tender_id, Award.company_id).in_(award_pairs)
                    )
                ).all()
            )

        new_awards: list[Award] = []
        seen_pairs = set(existing_award_pairs)
        for notice in notices:
            tender = existing_tenders_by_reference.get(notice.tender.reference_number)
            if tender is None:
                continue
            for award in notice.awards:
                company = existing_companies.get(_company_key(award.company_name, award.company_registration_number))
                if company is None:
                    stats.skipped += 1
                    logger.warning("Skipping World Bank award with missing company: %s", award.metadata.source_record_id)
                    continue

                pair = (tender.id, company.id)
                if pair in seen_pairs:
                    stats.skipped += 1
                    logger.info("Skipping duplicate World Bank award: %s", award.metadata.source_record_id)
                    continue

                seen_pairs.add(pair)
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
        logger.info(
            "Imported World Bank batch: tenders=%s companies=%s awards=%s skipped=%s",
            len(new_tenders),
            len(new_companies),
            len(new_awards),
            stats.skipped,
        )

    def _get_existing_companies(self, companies: dict[tuple[str, str | None], MappedCompany]) -> dict[tuple[str, str | None], Company]:
        existing_by_registration: dict[str, Company] = {}
        existing_by_name: dict[str, Company] = {}
        registration_numbers = {
            company.registration_number for company in companies.values() if company.registration_number
        }
        names = {company.name for company in companies.values()}

        if registration_numbers:
            for company in self.session.scalars(
                select(Company).where(Company.registration_number.in_(registration_numbers))
            ):
                if company.registration_number:
                    existing_by_registration[company.registration_number] = company

        if names:
            for company in self.session.scalars(select(Company).where(Company.name.in_(names))):
                existing_by_name[company.name] = company

        existing: dict[tuple[str, str | None], Company] = {}
        for key, company in companies.items():
            matched = None
            if company.registration_number:
                matched = existing_by_registration.get(company.registration_number)
            if matched is None:
                matched = existing_by_name.get(company.name)
            if matched is not None:
                existing[key] = matched
        return existing

    def _log_database_summary(self, stats: WorldBankImportStats) -> None:
        total_tenders = self.session.scalar(select(func.count()).select_from(Tender)) or 0
        total_companies = self.session.scalar(select(func.count()).select_from(Company)) or 0
        total_awards = self.session.scalar(select(func.count()).select_from(Award)) or 0
        logger.info(
            "World Bank import complete: total_tenders=%s total_companies=%s total_awards=%s duration_seconds=%.2f skipped=%s",
            total_tenders,
            total_companies,
            total_awards,
            stats.duration_seconds,
            stats.skipped,
        )


def _dedupe_companies(companies: object) -> dict[tuple[str, str | None], MappedCompany]:
    deduped: dict[tuple[str, str | None], MappedCompany] = {}
    for company in companies:  # type: ignore[union-attr]
        deduped.setdefault(_company_key(company.name, company.registration_number), company)
    return deduped


def _company_key(name: str, registration_number: str | None) -> tuple[str, str | None]:
    return (name.strip(), registration_number.strip() if registration_number else None)
