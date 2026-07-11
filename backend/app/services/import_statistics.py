"""Procurement import statistics engine (Phase 3).

Reports every headline total, coverage percentage, duplicate rate,
normalization rate and import-duration metric — all read live from the
ingestion and provenance tables. Nothing is fabricated: entities that the
ingestion layer does not model (e.g. company directors) are reported as ``0``
with an explicit note rather than invented.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.models import (
    Award,
    Company,
    Document,
    ImportRun,
    SourceRecordVersion,
    Tender,
)
from app.normalization import normalize_org_name, normalize_reference, org_match_key
from app.schemas.import_statistics import (
    EntityTotals,
    ImportDurationStats,
    ImportStatisticsReport,
    RateMetric,
)

_DIRECTORS_NOTE = (
    "Company directors are not modelled in the procurement ingestion layer "
    "(no directors table); reported as 0 rather than fabricated."
)


def build_import_statistics(db: Session) -> ImportStatisticsReport:
    tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    awards = int(db.scalar(select(func.count(Award.id))) or 0)
    companies = int(db.scalar(select(func.count(Company.id))) or 0)
    documents = int(db.scalar(select(func.count(Document.id))) or 0)
    source_versions = int(db.scalar(select(func.count(SourceRecordVersion.id))) or 0)
    buyers = int(
        db.scalar(
            select(func.count(func.distinct(Tender.procuring_entity))).where(
                Tender.procuring_entity.is_not(None)
            )
        )
        or 0
    )
    suppliers = int(db.scalar(select(func.count(func.distinct(Award.company_id)))) or 0)
    total_award_value = db.scalar(select(func.coalesce(func.sum(Award.award_value), 0))) or Decimal("0")

    totals = EntityTotals(
        total_records=tenders + awards + companies + documents,
        tenders=tenders,
        awards=awards,
        contracts=awards,
        buyers=buyers,
        suppliers=suppliers,
        companies=companies,
        directors=0,
        documents=documents,
        evidence_records=documents + source_versions,
        source_versions=source_versions,
        total_award_value=Decimal(total_award_value),
    )

    return ImportStatisticsReport(
        generated_at=now_utc().isoformat(),
        totals=totals,
        coverage_percentages=_coverage_percentages(db, tenders, awards, documents),
        duplicate_rates=_duplicate_rates(db, tenders, companies, awards),
        normalization_rates=_normalization_rates(db),
        durations=_durations(db, tenders + awards + companies),
        notes=[_DIRECTORS_NOTE],
    )


def _coverage_percentages(db: Session, tenders: int, awards: int, documents: int) -> list[RateMetric]:
    with_value = int(db.scalar(select(func.count(Tender.id)).where(Tender.estimated_value.is_not(None))) or 0)
    with_closing = int(db.scalar(select(func.count(Tender.id)).where(Tender.closing_date.is_not(None))) or 0)
    with_buyer = int(
        db.scalar(select(func.count(Tender.id)).where(Tender.procuring_entity.is_not(None))) or 0
    )
    with_docs = int(db.scalar(select(func.count(func.distinct(Document.tender_id)))) or 0)
    tenders_with_award = int(db.scalar(select(func.count(func.distinct(Award.tender_id)))) or 0)
    awards_with_value = int(db.scalar(select(func.count(Award.id)).where(Award.award_value.is_not(None))) or 0)
    docs_with_url = int(db.scalar(select(func.count(Document.id)).where(Document.url.is_not(None))) or 0)
    return [
        _rate("tenders_with_value", "Tenders with an estimated value", with_value, tenders),
        _rate("tenders_with_closing", "Tenders with a closing date", with_closing, tenders),
        _rate("tenders_with_buyer", "Tenders with a buyer", with_buyer, tenders),
        _rate("tenders_with_documents", "Tenders with document evidence", with_docs, tenders),
        _rate("tenders_with_award", "Tenders with at least one award", tenders_with_award, tenders),
        _rate("awards_with_value", "Awards with a value", awards_with_value, awards),
        _rate("documents_with_url", "Documents with a URL", docs_with_url, documents),
    ]


def _duplicate_rates(db: Session, tenders: int, companies: int, awards: int) -> list[RateMetric]:
    # Company duplicates by canonical key.
    company_names = [name for (name,) in db.execute(select(Company.name)).all()]
    keys: dict[str, int] = defaultdict(int)
    for name in company_names:
        key = org_match_key(name)
        if key:
            keys[key] += 1
    company_dupes = sum(count - 1 for count in keys.values() if count > 1)

    # Duplicate tenders (buyer + title + published).
    dup_tender_rows = db.execute(
        select(func.count(Tender.id))
        .group_by(Tender.procuring_entity, Tender.title, Tender.published_date)
        .having(func.count(Tender.id) > 1)
    ).all()
    tender_dupes = sum(int(r[0]) - 1 for r in dup_tender_rows)

    # Duplicate awards (tender + company).
    dup_award_rows = db.execute(
        select(func.count(Award.id))
        .group_by(Award.tender_id, Award.company_id)
        .having(func.count(Award.id) > 1)
    ).all()
    award_dupes = sum(int(r[0]) - 1 for r in dup_award_rows)

    return [
        _rate("duplicate_tenders", "Duplicate tender rate", tender_dupes, tenders),
        _rate("duplicate_companies", "Duplicate company rate", company_dupes, companies),
        _rate("duplicate_awards", "Duplicate award rate", award_dupes, awards),
    ]


def _normalization_rates(db: Session) -> list[RateMetric]:
    company_names = [name for (name,) in db.execute(select(Company.name)).all()]
    norm_companies = sum(1 for name in company_names if name and normalize_org_name(name) == name)

    buyers = [
        buyer
        for (buyer,) in db.execute(
            select(Tender.procuring_entity).where(Tender.procuring_entity.is_not(None)).distinct()
        ).all()
    ]
    norm_buyers = sum(1 for buyer in buyers if normalize_org_name(buyer) == buyer)

    references = [ref for (ref,) in db.execute(select(Tender.reference_number)).all()]
    norm_refs = sum(1 for ref in references if ref and normalize_reference(ref) == ref)

    return [
        _rate("companies_normalized", "Company names in canonical form", norm_companies, len(company_names)),
        _rate("buyers_normalized", "Buyer names in canonical form", norm_buyers, len(buyers)),
        _rate("references_normalized", "References in canonical form", norm_refs, len(references)),
    ]


def _durations(db: Session, total_records: int) -> ImportDurationStats:
    runs = db.execute(
        select(
            ImportRun.status,
            ImportRun.started_at,
            ImportRun.finished_at,
            ImportRun.processed_records,
        )
    ).all()
    total_runs = len(runs)
    completed = sum(1 for status, *_ in runs if status == "completed")
    failed = sum(1 for status, *_ in runs if status == "failed")

    durations: list[float] = []
    for _status, started_at, finished_at, _processed in runs:
        if started_at and finished_at:
            durations.append(max((finished_at - started_at).total_seconds(), 0.0))
    total_duration = round(sum(durations), 3)
    average = round(total_duration / len(durations), 3) if durations else 0.0

    last_run_at = None
    if runs:
        latest = max((r[1] for r in runs if r[1] is not None), default=None)
        last_run_at = latest.isoformat() if latest else None

    processed_total = sum(int(r[3] or 0) for r in runs)
    rps = round(processed_total / total_duration, 3) if total_duration > 0 else 0.0

    return ImportDurationStats(
        total_runs=total_runs,
        completed_runs=completed,
        failed_runs=failed,
        total_duration_seconds=total_duration,
        average_duration_seconds=average,
        last_run_at=last_run_at,
        records_per_second=rps,
    )


def _rate(code: str, label: str, numerator: int, denominator: int) -> RateMetric:
    return RateMetric(
        code=code,
        label=label,
        numerator=int(numerator),
        denominator=int(denominator),
        rate=round(numerator / denominator, 4) if denominator else 0.0,
    )
