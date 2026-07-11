from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models import Award, Company, Tender

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedTender:
    reference_number: str
    title: str
    description: str | None
    procuring_entity: str | None
    published_date: date | None
    estimated_value: Decimal | None
    currency: str
    closing_date: date | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class ParsedCompany:
    name: str
    registration_number: str | None
    source_name: str | None = None
    source_record_id: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class ParsedAward:
    tender_reference_number: str
    company_registration_number: str | None
    company_name: str
    award_date: date | None
    award_value: Decimal | None
    currency: str
    source_name: str | None = None
    source_record_id: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class ParsedProzorroTender:
    tender: ParsedTender
    companies: list[ParsedCompany]
    awards: list[ParsedAward]


@dataclass
class ImportStats:
    tenders_imported: int = 0
    companies_imported: int = 0
    awards_imported: int = 0
    records_skipped: int = 0


class ProzorroImportError(ValueError):
    """Raised when a Prozorro tender file cannot be mapped to import entities."""


class ProzorroImporter:
    def __init__(self, session: Session, batch_size: int = 100) -> None:
        self.session = session
        self.batch_size = batch_size

    def import_directory(self, directory: Path) -> ImportStats:
        files = sorted(directory.glob("*.json"))
        logger.info("Found %s Prozorro JSON files in %s", len(files), directory)
        return self.import_files(files)

    def import_files(self, files: list[Path]) -> ImportStats:
        stats = ImportStats()
        batch: list[ParsedProzorroTender] = []
        for path in files:
            try:
                batch.append(parse_tender_file(path))
            except Exception:
                stats.records_skipped += 1
                logger.exception("Skipping invalid Prozorro tender file: %s", path)
                continue

            if len(batch) >= self.batch_size:
                self._import_batch(batch, stats)
                batch.clear()

        if batch:
            self._import_batch(batch, stats)

        return stats

    def _import_batch(self, tenders: list[ParsedProzorroTender], stats: ImportStats) -> None:
        references = {parsed.tender.reference_number for parsed in tenders}
        existing_tenders = {
            tender.reference_number: tender
            for tender in self.session.scalars(
                select(Tender).where(Tender.reference_number.in_(references))
            )
        }

        new_tenders = [
            Tender(
                reference_number=parsed.tender.reference_number,
                title=parsed.tender.title,
                description=parsed.tender.description,
                procuring_entity=parsed.tender.procuring_entity,
                published_date=parsed.tender.published_date,
                estimated_value=parsed.tender.estimated_value,
                currency=parsed.tender.currency,
                source_name=parsed.tender.source_name,
                source_record_id=parsed.tender.source_record_id,
                source_url=parsed.tender.source_url,
                retrieved_at=parsed.tender.retrieved_at,
            )
            for parsed in tenders
            if parsed.tender.reference_number not in existing_tenders
        ]
        self.session.add_all(new_tenders)
        self.session.flush()
        stats.tenders_imported += len(new_tenders)

        for tender in new_tenders:
            existing_tenders[tender.reference_number] = tender

        parsed_companies = _dedupe_companies(
            company for parsed in tenders for company in parsed.companies
        )
        existing_companies = self._get_existing_companies(parsed_companies)

        new_companies = [
            Company(
                name=company.name,
                registration_number=company.registration_number,
                source_name=company.source_name,
                source_record_id=company.source_record_id,
                source_url=company.source_url,
                retrieved_at=company.retrieved_at,
            )
            for key, company in parsed_companies.items()
            if key not in existing_companies
        ]
        self.session.add_all(new_companies)
        self.session.flush()
        stats.companies_imported += len(new_companies)

        for company in new_companies:
            existing_companies[_company_key(company.name, company.registration_number)] = company

        award_pairs = [
            (
                existing_tenders[award.tender_reference_number].id,
                existing_companies[_company_key(award.company_name, award.company_registration_number)].id,
            )
            for parsed in tenders
            for award in parsed.awards
            if award.tender_reference_number in existing_tenders
            and _company_key(award.company_name, award.company_registration_number) in existing_companies
        ]
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
        seen_award_pairs = set(existing_award_pairs)
        for parsed in tenders:
            for award in parsed.awards:
                tender = existing_tenders.get(award.tender_reference_number)
                company = existing_companies.get(
                    _company_key(award.company_name, award.company_registration_number)
                )
                if tender is None or company is None:
                    stats.records_skipped += 1
                    logger.warning("Skipping award with missing tender/company relationship.")
                    continue

                pair = (tender.id, company.id)
                if pair in seen_award_pairs:
                    continue

                seen_award_pairs.add(pair)
                new_awards.append(
                    Award(
                        tender_id=tender.id,
                        company_id=company.id,
                        award_date=award.award_date,
                        award_value=award.award_value,
                        currency=award.currency,
                        source_name=award.source_name,
                        source_record_id=award.source_record_id,
                        source_url=award.source_url,
                        retrieved_at=award.retrieved_at,
                    )
                )

        self.session.add_all(new_awards)
        self.session.commit()
        stats.awards_imported += len(new_awards)
        logger.info(
            "Imported batch: tenders=%s companies=%s awards=%s",
            len(new_tenders),
            len(new_companies),
            len(new_awards),
        )

    def _get_existing_companies(self, companies: dict[tuple[str, str | None], ParsedCompany]) -> dict[tuple[str, str | None], Company]:
        existing_by_registration: dict[str, Company] = {}
        existing_by_name: dict[str, Company] = {}
        registration_numbers = {
            company.registration_number
            for company in companies.values()
            if company.registration_number
        }
        names = {company.name for company in companies.values()}

        if registration_numbers:
            for company in self.session.scalars(
                select(Company).where(Company.registration_number.in_(registration_numbers))
            ):
                if company.registration_number:
                    existing_by_registration[company.registration_number] = company

        if names:
            for company in self.session.scalars(
                select(Company).where(Company.name.in_(names))
            ):
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


def parse_tender_file(path: Path) -> ParsedProzorroTender:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ProzorroImportError("Tender JSON root must be an object.")

    source_url = _optional_string(payload.get("source_url")) if isinstance(payload, dict) else None
    retrieved_at = _parse_datetime(payload.get("retrieved_at")) if isinstance(payload, dict) else None
    if isinstance(payload.get("data"), dict):
        envelope = payload
        payload = envelope["data"]
        source_url = _optional_string(envelope.get("source_url")) or source_url
        retrieved_at = _parse_datetime(envelope.get("retrieved_at")) or retrieved_at

    return parse_tender(payload, source_url=source_url, retrieved_at=retrieved_at)


def parse_tender(payload: dict[str, Any], source_url: str | None = None, retrieved_at: datetime | None = None) -> ParsedProzorroTender:
    reference_number = _required_string(payload, "tenderID")
    tender_id = _optional_string(payload.get("id")) or reference_number
    title = _required_string(payload, "title")
    value = _object(payload.get("value"))
    procuring_entity = _object(payload.get("procuringEntity"))

    tender = ParsedTender(
        reference_number=reference_number,
        title=title,
        description=_optional_string(payload.get("description")),
        procuring_entity=_optional_string(procuring_entity.get("name")),
        published_date=_parse_date(payload.get("date") or payload.get("dateCreated")),
        closing_date=_parse_date(_object(payload.get("tenderPeriod")).get("endDate")),
        estimated_value=_parse_decimal(value.get("amount")),
        currency=_currency(value.get("currency")),
        source_name="prozorro",
        source_record_id=tender_id,
        source_url=source_url or f"https://prozorro.gov.ua/tender/{reference_number}",
        retrieved_at=retrieved_at,
    )

    companies: list[ParsedCompany] = []
    awards: list[ParsedAward] = []
    for award in _list(payload.get("awards")):
        if not isinstance(award, dict):
            logger.warning("Skipping non-object award for tender %s", reference_number)
            continue

        award_value = _object(award.get("value"))
        for supplier in _list(award.get("suppliers")):
            try:
                supplier_object = _object(supplier)
                identifier = _object(supplier_object.get("identifier"))
                company = ParsedCompany(
                    name=_required_string(supplier_object, "name"),
                    registration_number=_optional_string(identifier.get("id")),
                    source_name="prozorro",
                    source_record_id=_optional_string(identifier.get("id")),
                    source_url=source_url,
                    retrieved_at=retrieved_at,
                )
                companies.append(company)
                awards.append(
                    ParsedAward(
                        tender_reference_number=reference_number,
                        company_registration_number=company.registration_number,
                        company_name=company.name,
                        award_date=_parse_date(award.get("date")),
                        award_value=_parse_decimal(award_value.get("amount")),
                        currency=_currency(award_value.get("currency")),
                        source_name="prozorro",
                        source_record_id=_optional_string(award.get("id")) or f"{tender_id}:award:{company.registration_number or company.name}",
                        source_url=source_url,
                        retrieved_at=retrieved_at,
                    )
                )
            except Exception:
                logger.exception("Skipping invalid supplier award for tender %s", reference_number)

    return ParsedProzorroTender(
        tender=tender,
        companies=list(_dedupe_companies(companies).values()),
        awards=awards,
    )


def _dedupe_companies(companies: Any) -> dict[tuple[str, str | None], ParsedCompany]:
    deduped: dict[tuple[str, str | None], ParsedCompany] = {}
    for company in companies:
        deduped.setdefault(_company_key(company.name, company.registration_number), company)
    return deduped


def _company_key(name: str, registration_number: str | None) -> tuple[str, str | None]:
    return (name.strip(), registration_number.strip() if registration_number else None)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProzorroImportError(f"Missing required string field: {key}")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _currency(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()[:3].upper()
    return "UAH"
