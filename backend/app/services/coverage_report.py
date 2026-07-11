"""Procurement ingestion coverage & connector-health reporting.

Answers "what have we actually ingested, from where, how fresh is it, and which
connectors are healthy?" by joining the connector *registry* against the
imported rows and the provenance tables (ImportRun / SourceRecordVersion /
ImportCheckpoint). Every statistic is real; connectors with no data are
reported honestly as ``no_data`` rather than hidden.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.common.source_priority import is_indian_source, source_rank
from app.connectors.registry import discover_connectors
from app.entity_resolution.models import CanonicalCompany
from app.models import (
    Award,
    Company,
    Document,
    ImportCheckpoint,
    ImportRun,
    SourceRecordVersion,
    Tender,
)
from app.schemas.coverage import (
    ConnectorHealth,
    CoverageReport,
    CoverageTotals,
    ProvenanceStats,
)

_STALE_DAYS = 30


def build_coverage_report(db: Session) -> CoverageReport:
    now = now_utc()
    registry = discover_connectors()
    connector_meta = {c.metadata.name: c.metadata for c in registry.all()}

    tenders_by_source = _count_by_source(db, Tender.source_name, Tender.id)
    companies_by_source = _count_by_source(db, Company.source_name, Company.id)
    awards_by_source = _count_by_source(db, Award.source_name, Award.id)
    documents_by_source = _count_by_source(db, Document.source_name, Document.id)
    versions_by_source = _count_by_source(db, SourceRecordVersion.source_name, SourceRecordVersion.id)
    freshness_by_source = _freshness_by_source(db)
    last_runs = _last_runs(db)

    connectors: list[ConnectorHealth] = []
    unsupported: list[str] = []
    for name, meta in sorted(connector_meta.items(), key=lambda item: source_rank(item[0])):
        tenders = tenders_by_source.get(name, 0)
        last_run = last_runs.get(name)
        retrieved_at = freshness_by_source.get(name)
        freshness_days = (now - retrieved_at).days if retrieved_at else None
        if tenders == 0:
            health = "no_data"
            unsupported.append(name)
        elif freshness_days is not None and freshness_days > _STALE_DAYS:
            health = "stale"
        else:
            health = "active"
        connectors.append(
            ConnectorHealth(
                name=name,
                label=meta.label,
                registered=True,
                has_raw_directory=meta.raw_directory is not None,
                is_indian=is_indian_source(name),
                priority_rank=source_rank(name),
                tenders=tenders,
                companies=companies_by_source.get(name, 0),
                awards=awards_by_source.get(name, 0),
                documents=documents_by_source.get(name, 0),
                versions=versions_by_source.get(name, 0),
                last_import_status=last_run[0] if last_run else None,
                last_import_at=_iso(last_run[1]) if last_run else None,
                last_retrieved_at=_iso(retrieved_at),
                freshness_days=freshness_days,
                health=health,
            )
        )

    totals = CoverageTotals(
        connectors_registered=len(connector_meta),
        connectors_active=sum(1 for c in connectors if c.health == "active"),
        tenders=int(db.scalar(select(func.count(Tender.id))) or 0),
        companies=int(db.scalar(select(func.count(Company.id))) or 0),
        awards=int(db.scalar(select(func.count(Award.id))) or 0),
        documents=int(db.scalar(select(func.count(Document.id))) or 0),
        distinct_buyers=int(
            db.scalar(
                select(func.count(func.distinct(Tender.procuring_entity))).where(
                    Tender.procuring_entity.is_not(None)
                )
            )
            or 0
        ),
        mapped_canonical_companies=int(db.scalar(select(func.count(CanonicalCompany.id))) or 0),
    )

    return CoverageReport(
        generated_at=now.isoformat(),
        totals=totals,
        provenance=_provenance(db),
        connectors=connectors,
        unsupported_portals=unsupported,
    )


def _count_by_source(db: Session, source_column, id_column) -> dict[str, int]:
    rows = db.execute(
        select(source_column, func.count(id_column))
        .where(source_column.is_not(None))
        .group_by(source_column)
    ).all()
    return {name: int(count) for name, count in rows}


def _freshness_by_source(db: Session) -> dict[str, datetime]:
    rows = db.execute(
        select(Tender.source_name, func.max(Tender.retrieved_at))
        .where(Tender.source_name.is_not(None), Tender.retrieved_at.is_not(None))
        .group_by(Tender.source_name)
    ).all()
    return {name: retrieved for name, retrieved in rows if retrieved is not None}


def _last_runs(db: Session) -> dict[str, tuple[str, datetime | None]]:
    runs: dict[str, tuple[str, datetime | None]] = {}
    rows = db.execute(
        select(ImportRun.source, ImportRun.status, ImportRun.started_at, ImportRun.finished_at)
        .order_by(ImportRun.started_at.desc())
    ).all()
    for source, status, started_at, finished_at in rows:
        if source not in runs:
            runs[source] = (status, finished_at or started_at)
    return runs


def _provenance(db: Session) -> ProvenanceStats:
    return ProvenanceStats(
        import_runs=int(db.scalar(select(func.count(ImportRun.id))) or 0),
        completed_runs=int(
            db.scalar(select(func.count(ImportRun.id)).where(ImportRun.status == "completed")) or 0
        ),
        failed_runs=int(
            db.scalar(select(func.count(ImportRun.id)).where(ImportRun.status == "failed")) or 0
        ),
        source_record_versions=int(db.scalar(select(func.count(SourceRecordVersion.id))) or 0),
        checkpoints=int(db.scalar(select(func.count(ImportCheckpoint.id))) or 0),
        imported_action_versions=int(
            db.scalar(
                select(func.count(SourceRecordVersion.id)).where(SourceRecordVersion.action == "imported")
            )
            or 0
        ),
        updated_action_versions=int(
            db.scalar(
                select(func.count(SourceRecordVersion.id)).where(SourceRecordVersion.action == "updated")
            )
            or 0
        ),
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
