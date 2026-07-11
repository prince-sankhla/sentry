"""Tests for the procurement_platform package (Phases 4-6, 9, 10, X).

Reuses the deterministic engine connector + rolled-back ``db_session`` fixture,
so nothing is persisted. Network / real downloads are NOT exercised here
(``download=False`` / no probe URL), keeping tests hermetic.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import app.models  # noqa: F401
from app.connectors.base import (
    FileBackedSourceConnector,
    NormalizedAward,
    NormalizedCompany,
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedSourceMetadata,
    NormalizedTender,
    SourceConnectorMetadata,
)
from app.connectors.common.parse import now_utc, parse_date
from app.connectors.registry import register_connector
from app.importers.generic import GenericConnectorImporter
from app.models import Document, SourceRecordVersion, Tender
from app.services.procurement_platform import (
    RetryQueue,
    acquire,
    backfill_evidence,
    batched,
    build_connector_dashboard,
    build_platform_report,
    evidence_scores,
    parallel_import,
    plan_delta,
    resolve_conflict,
    rollback_to_version,
    run_validation,
    stream_envelopes,
    synchronize_deletions,
)

PLAT_SOURCE = "test_platform_source"


class _PlatformConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(name=PLAT_SOURCE, label="Test Platform Source", version="2.0", raw_directory="test_platform_source")

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        data = raw_record["data"]
        meta = NormalizedSourceMetadata(
            source_name=PLAT_SOURCE, source_record_id=str(data["id"]),
            source_url=raw_record.get("source_url"), retrieved_at=now_utc(),
        )
        tender = NormalizedTender(
            reference_number=str(data["reference"]), title=data["title"], description=None,
            procuring_entity=data.get("buyer", "Public Works Department"),
            published_date=parse_date(data.get("published", "2025-01-01")),
            closing_date=parse_date(data.get("closing", "2025-02-01")),
            estimated_value=Decimal("1000000"), currency="INR", metadata=meta,
        )
        companies = [NormalizedCompany(name="ACME Infra Pvt Ltd", registration_number="REG-1", metadata=meta)]
        awards = [NormalizedAward(
            tender_reference_number=tender.reference_number, company_name="ACME Infra Pvt Ltd",
            company_registration_number="REG-1", award_date=parse_date("2025-03-01"),
            award_value=Decimal("950000"), currency="INR", metadata=meta,
        )]
        documents = [NormalizedDocument(title="Notice", url=f"https://src/{data['id']}/n.pdf", document_type="attachment", metadata=meta)]
        return NormalizedProcurementRecord(tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record)


register_connector(_PlatformConnector)


def _write(directory: Path, idx: int, **ov: Any) -> None:
    data = {"id": f"P-{idx}", "reference": f"PLATREF-{idx}", "title": f"Road works {idx}"}
    data.update(ov)
    envelope = {"source_name": PLAT_SOURCE, "source_record_id": data["id"], "source_url": f"https://src/{data['id']}", "data": data}
    (directory / f"{data['id']}.json").write_text(json.dumps(envelope), encoding="utf-8")


def _seed(db_session, tmp_path: Path, count: int = 3) -> None:
    for i in range(count):
        _write(tmp_path, i)
    GenericConnectorImporter(db_session, PLAT_SOURCE).import_directory(tmp_path)


# --------------------------------------------------------------------- evidence


class TestEvidenceEngine:
    def test_importer_populates_evidence_columns(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        docs = db_session.query(Document).filter(Document.connector_name == PLAT_SOURCE).all()
        assert docs
        for d in docs:
            assert d.evidence_hash is not None
            assert d.connector_version == "2.0"
            assert d.import_run_id is not None
            assert d.verified_at is not None

    def test_backfill_is_idempotent(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        first = backfill_evidence(db_session, commit=False)
        second = backfill_evidence(db_session, commit=False)
        assert second <= first  # nothing left to backfill the second time for freshly imported rows
        scores = evidence_scores(db_session)
        assert 0.0 <= scores.completeness <= 1.0
        assert 0.0 <= scores.integrity <= 1.0


# --------------------------------------------------------------------- incremental


class TestIncrementalEngine:
    def test_plan_delta_classifies(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path, count=3)
        # add one new file, change one existing.
        _write(tmp_path, 3)
        _write(tmp_path, 0, title="Changed title 0")
        plan = plan_delta(db_session, PLAT_SOURCE, tmp_path)
        s = plan.summary()
        assert s["new"] == 1
        assert s["updated"] == 1
        assert s["unchanged"] == 2

    def test_soft_delete_and_restore(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path, count=3)
        # only P-0 and P-1 present now -> P-2 should be soft-deleted.
        res = synchronize_deletions(db_session, PLAT_SOURCE, {"P-0", "P-1"})
        assert res["soft_deleted"] == 1
        deleted = db_session.query(Tender).filter(Tender.source_record_id == "P-2").one()
        assert deleted.deleted_at is not None
        # P-2 returns -> restored.
        res2 = synchronize_deletions(db_session, PLAT_SOURCE, {"P-0", "P-1", "P-2"})
        assert res2["restored"] == 1
        assert db_session.query(Tender).filter(Tender.source_record_id == "P-2").one().deleted_at is None

    def test_rollback_to_version(self, db_session, tmp_path: Path) -> None:
        _write(tmp_path, 0, title="Original")
        GenericConnectorImporter(db_session, PLAT_SOURCE).import_directory(tmp_path)
        _write(tmp_path, 0, title="Updated")
        GenericConnectorImporter(db_session, PLAT_SOURCE).import_directory(tmp_path)
        first_version = (
            db_session.query(SourceRecordVersion)
            .filter(SourceRecordVersion.source_record_id == "P-0", SourceRecordVersion.action == "imported")
            .one()
        )
        assert rollback_to_version(db_session, first_version.id) is True
        assert db_session.query(Tender).filter(Tender.source_record_id == "P-0").one().title == "Original"

    def test_retry_queue_bounded(self) -> None:
        q = RetryQueue(max_retries=3)
        q.add("x")
        assert q.mark_failed("x") is True
        assert q.mark_failed("x") is True
        assert q.mark_failed("x") is False
        assert "x" in q.dropped

    def test_conflict_resolution_deterministic(self) -> None:
        from datetime import datetime, UTC

        older = datetime(2025, 1, 1, tzinfo=UTC)
        newer = datetime(2025, 6, 1, tzinfo=UTC)
        assert resolve_conflict(older, newer) == "incoming"
        assert resolve_conflict(newer, older) == "existing"


# --------------------------------------------------------------------- performance


class TestPerformance:
    def test_batched(self) -> None:
        assert list(batched(range(5), 2)) == [[0, 1], [2, 3], [4]]

    def test_stream_envelopes(self, tmp_path: Path) -> None:
        _write(tmp_path, 0)
        _write(tmp_path, 1)
        assert len(list(stream_envelopes(tmp_path))) == 2

    def test_parallel_import_empty_and_aggregation(self) -> None:
        # Hermetic: no sources -> empty result; aggregation is deterministic.
        from app.importers.generic import GenericImportStats
        from app.services.procurement_platform import ParallelImportResult

        result = parallel_import([], Path("."), max_workers=2)
        assert result.stats_by_source == {}
        agg = ParallelImportResult(
            stats_by_source={
                "a": GenericImportStats(imported_tenders=2, imported_documents=3, versions_recorded=2),
                "b": GenericImportStats(imported_tenders=1, updated_tenders=1, versions_recorded=2),
            }
        )
        totals = agg.totals()
        assert totals["new"] == 3 and totals["updated"] == 1 and totals["documents"] == 3 and totals["versions"] == 4


# --------------------------------------------------------------------- acquisition


class TestAcquisition:
    def test_acquire_import_on_disk(self, db_session, tmp_path: Path) -> None:
        (tmp_path / PLAT_SOURCE).mkdir()
        for i in range(3):
            _write(tmp_path / PLAT_SOURCE, i)
        result = acquire(db_session, PLAT_SOURCE, tmp_path, download=False)
        assert result.outcome in {"acquired", "already_imported"}
        assert result.imported_new + result.imported_updated + result.unchanged_on_disk >= 3
        assert result.delta["total_files"] == 3

    def test_acquire_unavailable_when_no_data(self, db_session, tmp_path: Path) -> None:
        result = acquire(db_session, PLAT_SOURCE, tmp_path, download=False)  # empty root
        assert result.outcome == "unavailable"
        assert result.blocker


# --------------------------------------------------------------------- health / validators / reports


class TestPlatformReports:
    def test_dashboard(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        d = build_connector_dashboard(db_session)
        entry = next((e for e in d.entries if e.name == PLAT_SOURCE), None)
        assert entry is not None
        assert 0.0 <= entry.health_score <= 1.0
        assert entry.incremental_support is True

    def test_validation_passes(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        result = run_validation(db_session)
        assert result.passed, [vars(c) for c in result.checks if not c.passed]

    def test_platform_report_has_all_sections(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        report = build_platform_report(db_session)
        assert {
            "statistics", "data_quality", "coverage_dimensions",
            "coverage_connectors", "evidence_integrity", "connector_dashboard",
        } <= set(report)
