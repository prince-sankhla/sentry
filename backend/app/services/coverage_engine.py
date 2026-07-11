"""Multi-dimensional procurement coverage engine (Phase 2).

Answers "how is the imported dataset distributed?" across every reporting
dimension: source, state, ministry, buyer, supplier, category, procurement
method, year, currency and organisation. Each dimension yields per-bucket
tender / award / company / document counts and value totals, plus an honest
attributed-vs-unattributed coverage ratio.

All aggregation is deterministic: SQL group-bys for stored columns, and the
pure classifiers in :mod:`app.services.procurement_taxonomy` for derived
buckets (state / ministry / category / method). No AI, no fabricated numbers.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.common.source_priority import source_rank
from app.models import Award, Company, Document, Tender
from app.schemas.coverage_engine import (
    CoverageBucket,
    CoverageDimension,
    CoverageEngineReport,
)
from app.services import procurement_taxonomy as tax

_TOP_BUCKETS = 25


def build_coverage_engine_report(db: Session) -> CoverageEngineReport:
    total_tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    total_awards = int(db.scalar(select(func.count(Award.id))) or 0)
    total_companies = int(db.scalar(select(func.count(Company.id))) or 0)
    total_documents = int(db.scalar(select(func.count(Document.id))) or 0)

    # Pull the per-tender fields once; derive taxonomy buckets in Python.
    tender_rows = db.execute(
        select(
            Tender.id,
            Tender.source_name,
            Tender.procuring_entity,
            Tender.title,
            Tender.description,
            Tender.published_date,
            Tender.currency,
            Tender.estimated_value,
        )
    ).all()
    awards_per_tender = _awards_per_tender(db)
    docs_per_tender = _docs_per_tender(db)

    dimensions = [
        _derived_dimension(
            "source", "Coverage by source connector", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: r.source_name or "unknown", unattributed_key="unknown",
        ),
        _derived_dimension(
            "state", "Coverage by Indian state", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.state_of(r.procuring_entity, r.title), unattributed_key=tax.UNATTRIBUTED,
        ),
        _derived_dimension(
            "ministry", "Coverage by ministry / department", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.ministry_of(r.procuring_entity), unattributed_key=tax.UNATTRIBUTED,
        ),
        _derived_dimension(
            "buyer", "Coverage by buyer / procuring entity", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: r.procuring_entity or tax.UNATTRIBUTED, unattributed_key=tax.UNATTRIBUTED,
        ),
        _derived_dimension(
            "category", "Coverage by spend category", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.category_of(r.title, r.description), unattributed_key=tax.OTHER,
        ),
        _derived_dimension(
            "procurement_method", "Coverage by procurement method", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.procurement_method_of(r.title, r.description), unattributed_key=tax.UNSPECIFIED,
        ),
        _derived_dimension(
            "year", "Coverage by publication year", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.year_of(r.published_date), unattributed_key=tax.UNSPECIFIED,
        ),
        _derived_dimension(
            "currency", "Coverage by currency", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: r.currency or tax.UNSPECIFIED, unattributed_key=tax.UNSPECIFIED,
        ),
        _derived_dimension(
            "department", "Coverage by department", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.department_of(r.procuring_entity), unattributed_key=tax.UNATTRIBUTED,
        ),
        _derived_dimension(
            "authority", "Coverage by authority type", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.authority_of(r.procuring_entity), unattributed_key=tax.OTHER,
        ),
        _derived_dimension(
            "sector", "Coverage by sector", tender_rows, awards_per_tender, docs_per_tender,
            lambda r: tax.category_of(r.title, r.description), unattributed_key=tax.OTHER,
        ),
        _award_status_dimension(tender_rows, awards_per_tender),
        _supplier_dimension(db, total_tenders),
        _document_type_dimension(db),
        _organization_dimension(db),
    ]

    return CoverageEngineReport(
        generated_at=now_utc().isoformat(),
        total_tenders=total_tenders,
        total_awards=total_awards,
        total_companies=total_companies,
        total_documents=total_documents,
        dimensions=dimensions,
    )


def _awards_per_tender(db: Session) -> dict:
    return {
        tid: int(count)
        for tid, count in db.execute(
            select(Award.tender_id, func.count(Award.id)).group_by(Award.tender_id)
        ).all()
    }


def _docs_per_tender(db: Session) -> dict:
    return {
        tid: int(count)
        for tid, count in db.execute(
            select(Document.tender_id, func.count(Document.id))
            .where(Document.tender_id.is_not(None))
            .group_by(Document.tender_id)
        ).all()
    }


def _derived_dimension(
    dimension: str,
    label: str,
    tender_rows,
    awards_per_tender: dict,
    docs_per_tender: dict,
    key_func,
    *,
    unattributed_key: str,
) -> CoverageDimension:
    tenders: dict[str, int] = defaultdict(int)
    awards: dict[str, int] = defaultdict(int)
    documents: dict[str, int] = defaultdict(int)
    values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for row in tender_rows:
        key = key_func(row) or unattributed_key
        tenders[key] += 1
        awards[key] += awards_per_tender.get(row.id, 0)
        documents[key] += docs_per_tender.get(row.id, 0)
        values[key] += row.estimated_value or Decimal("0")

    total = sum(tenders.values())
    unattributed = tenders.get(unattributed_key, 0)
    buckets = [
        CoverageBucket(
            key=key,
            tenders=count,
            awards=awards[key],
            documents=documents[key],
            total_value=values[key],
            share=round(count / total, 4) if total else 0.0,
        )
        for key, count in tenders.items()
    ]
    buckets.sort(key=lambda b: (-b.tenders, b.key))
    return CoverageDimension(
        dimension=dimension,
        label=label,
        distinct_buckets=len([k for k in tenders if k != unattributed_key]),
        attributed_tenders=total - unattributed,
        unattributed_tenders=unattributed,
        coverage_ratio=round((total - unattributed) / total, 4) if total else 0.0,
        buckets=buckets[:_TOP_BUCKETS],
    )


def _supplier_dimension(db: Session, total_tenders: int) -> CoverageDimension:
    rows = db.execute(
        select(
            Company.name,
            func.count(func.distinct(Award.tender_id)),
            func.count(Award.id),
            func.coalesce(func.sum(Award.award_value), 0),
        )
        .select_from(Award)
        .join(Company, Award.company_id == Company.id)
        .group_by(Company.name)
        .order_by(func.count(Award.id).desc())
    ).all()
    total_awarded_tenders = int(
        db.scalar(select(func.count(func.distinct(Award.tender_id)))) or 0
    )
    buckets = [
        CoverageBucket(
            key=name,
            tenders=int(tenders),
            awards=int(awards),
            companies=1,
            total_value=Decimal(value),
            share=round(int(awards) / max(sum(int(r[2]) for r in rows), 1), 4),
        )
        for name, tenders, awards, value in rows[:_TOP_BUCKETS]
    ]
    return CoverageDimension(
        dimension="supplier",
        label="Coverage by supplier",
        distinct_buckets=len(rows),
        attributed_tenders=total_awarded_tenders,
        unattributed_tenders=max(total_tenders - total_awarded_tenders, 0),
        coverage_ratio=round(total_awarded_tenders / total_tenders, 4) if total_tenders else 0.0,
        buckets=buckets,
    )


def _award_status_dimension(tender_rows, awards_per_tender: dict) -> CoverageDimension:
    tenders = {"Awarded": 0, "Not Awarded": 0}
    awards = {"Awarded": 0, "Not Awarded": 0}
    values = {"Awarded": Decimal("0"), "Not Awarded": Decimal("0")}
    for row in tender_rows:
        key = "Awarded" if awards_per_tender.get(row.id, 0) > 0 else "Not Awarded"
        tenders[key] += 1
        awards[key] += awards_per_tender.get(row.id, 0)
        values[key] += row.estimated_value or Decimal("0")
    total = sum(tenders.values())
    buckets = [
        CoverageBucket(
            key=key, tenders=count, awards=awards[key], total_value=values[key],
            share=round(count / total, 4) if total else 0.0,
        )
        for key, count in tenders.items()
    ]
    return CoverageDimension(
        dimension="award_status", label="Coverage by award status",
        distinct_buckets=2, attributed_tenders=tenders["Awarded"],
        unattributed_tenders=tenders["Not Awarded"],
        coverage_ratio=round(tenders["Awarded"] / total, 4) if total else 0.0,
        buckets=buckets,
    )


def _document_type_dimension(db: Session) -> CoverageDimension:
    rows = db.execute(
        select(Document.document_type, func.count(Document.id)).group_by(Document.document_type)
    ).all()
    total = sum(int(c) for _, c in rows)
    buckets = [
        CoverageBucket(key=dtype or "unknown", documents=int(count), share=round(int(count) / total, 4) if total else 0.0)
        for dtype, count in rows
    ]
    buckets.sort(key=lambda b: -b.documents)
    return CoverageDimension(
        dimension="document_type", label="Coverage by document type",
        distinct_buckets=len(rows), attributed_tenders=total, unattributed_tenders=0,
        coverage_ratio=1.0 if total else 0.0, buckets=buckets,
    )


def _organization_dimension(db: Session) -> CoverageDimension:
    """Organisations = every distinct legal entity we hold (companies), by source."""
    rows = db.execute(
        select(Company.source_name, func.count(Company.id)).group_by(Company.source_name)
    ).all()
    total = sum(int(count) for _, count in rows)
    buckets = [
        CoverageBucket(
            key=source or "unknown",
            companies=int(count),
            share=round(int(count) / total, 4) if total else 0.0,
        )
        for source, count in rows
    ]
    buckets.sort(key=lambda b: (source_rank(b.key), -b.companies))
    return CoverageDimension(
        dimension="organization",
        label="Coverage by organisation source",
        distinct_buckets=len(rows),
        attributed_tenders=total,
        unattributed_tenders=0,
        coverage_ratio=1.0 if total else 0.0,
        buckets=buckets,
    )
