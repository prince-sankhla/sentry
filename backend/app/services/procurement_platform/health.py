"""Connector health dashboard engine (Phase 5).

Deterministic per-connector monitoring computed from ``import_runs``,
``import_checkpoints`` and the imported rows: success/failure rates, average
import time, retry counts, freshness, checkpoint status, normalization/evidence
coverage, a per-source data-quality score and a composite health score.

All aggregates are bulk group-bys (no per-connector query fan-out), so the
dashboard scales to hundreds of connectors.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.common.source_priority import is_indian_source, source_rank
from app.connectors.registry import discover_connectors
from app.models import Award, Company, Document, ImportCheckpoint, ImportRun, Tender
from app.normalization import normalize_org_name
from app.schemas.connector_dashboard import ConnectorDashboard, ConnectorDashboardEntry
from app.services.procurement_platform.utils import iso, ratio

_STALE_DAYS = 30


def build_connector_dashboard(db: Session) -> ConnectorDashboard:
    now = now_utc()
    registry = discover_connectors()
    meta = {c.metadata.name: c.metadata for c in registry.all()}

    tenders = _count(db, Tender.source_name, Tender.id)
    awards = _count(db, Award.source_name, Award.id)
    companies = _count(db, Company.source_name, Company.id)
    docs_by_tender_source = _tenders_with_docs(db)
    freshness = _freshness(db)
    runs = _run_stats(db)
    checkpoints = _checkpoints(db)
    quality = _quality_by_source(db, tenders)
    norm = _normalization_by_source(db)

    entries: list[ConnectorDashboardEntry] = []
    for name, m in sorted(meta.items(), key=lambda kv: source_rank(kv[0])):
        count = tenders.get(name, 0)
        retrieved = freshness.get(name)
        freshness_days = (now - retrieved).days if retrieved else None
        run = runs.get(name, _EMPTY_RUN)
        if count == 0:
            status = "no_data"
        elif freshness_days is not None and freshness_days > _STALE_DAYS:
            status = "stale"
        else:
            status = "active"

        q = quality.get(name, (0, 0.0, 0.0))  # missing_required, duplicate_rate, quality_score
        checkpoint = checkpoints.get(name)
        evidence_cov = ratio(docs_by_tender_source.get(name, 0), count) if count else 0.0
        norm_cov = norm.get(name, 0.0)

        health = _health_score(
            status=status,
            success_rate=run["success_rate"],
            quality_score=q[2],
            evidence_coverage=evidence_cov,
            normalization=norm_cov,
            freshness_days=freshness_days,
        )

        entries.append(
            ConnectorDashboardEntry(
                name=name,
                label=m.label,
                status=status,
                is_indian=is_indian_source(name),
                record_count=count,
                total_runs=run["total"],
                import_success_rate=run["success_rate"],
                failure_rate=run["failure_rate"],
                average_import_time_seconds=run["avg_import_time"],
                average_download_time_seconds=run["avg_download_time"],
                retry_count=run["retry_count"],
                freshness_days=freshness_days,
                last_successful_sync=iso(run["last_success"]),
                last_failed_sync=iso(run["last_failure"]),
                checkpoint_status="tracked" if checkpoint else "none",
                last_checkpoint_record=checkpoint,
                incremental_support=m.raw_directory is not None,
                normalization_coverage=norm_cov,
                data_quality_score=q[2],
                evidence_coverage=evidence_cov,
                missing_required_fields=q[0],
                duplicate_rate=q[1],
                health_score=health,
            )
        )

    active = sum(1 for e in entries if e.status == "active")
    stale = sum(1 for e in entries if e.status == "stale")
    no_data = sum(1 for e in entries if e.status == "no_data")
    avg_health = round(sum(e.health_score for e in entries) / len(entries), 4) if entries else 0.0

    return ConnectorDashboard(
        generated_at=now.isoformat(),
        connectors_total=len(meta),
        connectors_active=active,
        connectors_stale=stale,
        connectors_no_data=no_data,
        average_health_score=avg_health,
        entries=entries,
    )


_EMPTY_RUN = {
    "total": 0, "success_rate": 0.0, "failure_rate": 0.0, "avg_import_time": 0.0,
    "avg_download_time": 0.0, "retry_count": 0, "last_success": None, "last_failure": None,
}


def _count(db, source_column, id_column) -> dict[str, int]:
    return {
        name: int(count)
        for name, count in db.execute(
            select(source_column, func.count(id_column)).where(source_column.is_not(None)).group_by(source_column)
        ).all()
    }


def _tenders_with_docs(db) -> dict[str, int]:
    rows = db.execute(
        select(Tender.source_name, func.count(func.distinct(Tender.id)))
        .join(Document, Document.tender_id == Tender.id)
        .where(Tender.source_name.is_not(None))
        .group_by(Tender.source_name)
    ).all()
    return {name: int(count) for name, count in rows}


def _freshness(db) -> dict:
    rows = db.execute(
        select(Tender.source_name, func.max(Tender.retrieved_at))
        .where(Tender.source_name.is_not(None), Tender.retrieved_at.is_not(None))
        .group_by(Tender.source_name)
    ).all()
    return {name: r for name, r in rows if r is not None}


def _run_stats(db) -> dict[str, dict]:
    rows = db.execute(
        select(
            ImportRun.source, ImportRun.status, ImportRun.started_at, ImportRun.finished_at,
            ImportRun.failed_imports, ImportRun.downloaded_records, ImportRun.metadata_json,
        )
    ).all()
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row.source].append(row)

    stats: dict[str, dict] = {}
    for source, source_rows in grouped.items():
        total = len(source_rows)
        completed = sum(1 for r in source_rows if r.status == "completed")
        failed = sum(1 for r in source_rows if r.status == "failed")
        durations = [
            (r.finished_at - r.started_at).total_seconds()
            for r in source_rows if r.started_at and r.finished_at
        ]
        retry_count = sum(int(r.failed_imports or 0) for r in source_rows)
        successes = [r.finished_at or r.started_at for r in source_rows if r.status == "completed"]
        failures = [r.finished_at or r.started_at for r in source_rows if r.status == "failed"]
        stats[source] = {
            "total": total,
            "success_rate": ratio(completed, total),
            "failure_rate": ratio(failed, total),
            "avg_import_time": round(sum(durations) / len(durations), 3) if durations else 0.0,
            "avg_download_time": 0.0,  # download timing is not recorded per run
            "retry_count": retry_count,
            "last_success": max(successes) if successes else None,
            "last_failure": max(failures) if failures else None,
        }
    return stats


def _checkpoints(db) -> dict[str, str | None]:
    rows = db.execute(select(ImportCheckpoint.source, ImportCheckpoint.last_processed_record)).all()
    return {source: record for source, record in rows}


def _quality_by_source(db, tenders: dict[str, int]) -> dict[str, tuple[int, float, float]]:
    """(missing_required_fields, duplicate_rate, quality_score) per source."""
    missing = _count_where(db, Tender.source_name, (Tender.procuring_entity.is_(None)) | (Tender.estimated_value.is_(None)))
    # duplicate companies per source (canonical-key collisions).
    company_rows = db.execute(select(Company.source_name, Company.name)).all()
    keys: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for source_name, name in company_rows:
        from app.normalization import org_match_key

        key = org_match_key(name)
        if source_name and key:
            keys[source_name][key] += 1
    result: dict[str, tuple[int, float, float]] = {}
    for source, total in tenders.items():
        miss = missing.get(source, 0)
        dup_extra = sum(c - 1 for c in keys.get(source, {}).values() if c > 1)
        company_total = sum(keys.get(source, {}).values()) or 1
        dup_rate = ratio(dup_extra, company_total)
        # simple deterministic quality: penalise missing required fields + dupes.
        score = round(max(0.0, 1.0 - (ratio(miss, total) * 0.6 + dup_rate * 0.4)), 4)
        result[source] = (miss, dup_rate, score)
    return result


def _count_where(db, source_column, condition) -> dict[str, int]:
    rows = db.execute(
        select(source_column, func.count()).where(source_column.is_not(None), condition).group_by(source_column)
    ).all()
    return {name: int(count) for name, count in rows}


def _normalization_by_source(db) -> dict[str, float]:
    buyer_rows = db.execute(
        select(Tender.source_name, Tender.procuring_entity).where(Tender.procuring_entity.is_not(None))
    ).all()
    company_rows = db.execute(select(Company.source_name, Company.name)).all()
    totals: dict[str, int] = defaultdict(int)
    normalized: dict[str, int] = defaultdict(int)
    for source, value in list(buyer_rows) + list(company_rows):
        if not source:
            continue
        totals[source] += 1
        if value and normalize_org_name(value) == value:
            normalized[source] += 1
    return {source: ratio(normalized[source], totals[source]) for source in totals}


def _health_score(*, status, success_rate, quality_score, evidence_coverage, normalization, freshness_days) -> float:
    if status == "no_data":
        return 0.0
    freshness_factor = 1.0 if (freshness_days is not None and freshness_days <= _STALE_DAYS) else 0.5
    score = (
        0.30 * success_rate
        + 0.25 * quality_score
        + 0.20 * evidence_coverage
        + 0.15 * normalization
        + 0.10 * freshness_factor
    )
    return round(score, 4)
