"""Procurement reporting-engine tests (Phases 3-6) + incremental import
validation (Phase 5).

Uses a dedicated deterministic connector so scenarios (defects, updates,
resumes) can be crafted precisely, and the rolled-back ``db_session`` fixture so
nothing is persisted.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import app.models  # noqa: F401  (resolve model cycle)
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
from app.models import Award, Company, Document, ImportCheckpoint, SourceRecordVersion, Tender
from app.services.connector_validation import build_connector_health_report
from app.services.coverage_engine import build_coverage_engine_report
from app.services.data_quality import build_data_quality_report
from app.services.evidence_integrity import build_evidence_integrity_report
from app.services.import_statistics import build_import_statistics

ENGINE_SOURCE = "test_engine_source"


class _EngineConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(
        name=ENGINE_SOURCE,
        label="Test Engine Source",
        raw_directory="test_engine_source",
    )

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        data = raw_record["data"]
        meta = NormalizedSourceMetadata(
            source_name=ENGINE_SOURCE,
            source_record_id=str(data["id"]),
            source_url=raw_record.get("source_url"),
            retrieved_at=now_utc(),
        )
        tender = NormalizedTender(
            reference_number=str(data["reference"]),
            title=data["title"],
            description=data.get("description"),
            procuring_entity=data.get("buyer"),
            published_date=parse_date(data.get("published")),
            closing_date=parse_date(data.get("closing")),
            estimated_value=Decimal(str(data["estimate"])) if data.get("estimate") is not None else None,
            currency=data.get("currency", "INR"),
            metadata=meta,
        )
        companies, awards = [], []
        if data.get("supplier"):
            companies.append(NormalizedCompany(name=data["supplier"], registration_number=data.get("supplier_reg"), metadata=meta))
            awards.append(
                NormalizedAward(
                    tender_reference_number=tender.reference_number,
                    company_name=data["supplier"],
                    company_registration_number=data.get("supplier_reg"),
                    award_date=parse_date(data.get("award_date")),
                    award_value=Decimal(str(data["award_value"])) if data.get("award_value") is not None else None,
                    currency=data.get("award_currency", data.get("currency", "INR")),
                    metadata=meta,
                )
            )
        documents = [
            NormalizedDocument(title=d["title"], url=d["url"], document_type="attachment", metadata=meta)
            for d in data.get("documents", [])
        ]
        return NormalizedProcurementRecord(tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record)


register_connector(_EngineConnector)


def _write(directory: Path, data: dict[str, Any]) -> None:
    envelope = {"source_name": ENGINE_SOURCE, "source_record_id": str(data["id"]), "source_url": f"https://src/{data['id']}", "data": data}
    (directory / f"{data['id']}.json").write_text(json.dumps(envelope), encoding="utf-8")


def _record(idx: int, **overrides: Any) -> dict[str, Any]:
    base = {
        "id": f"E-{idx}",
        "reference": f"ENGREF-{idx}",
        "title": f"Construction of road segment {idx}",
        "buyer": "Public Works Department, Government of Kerala",
        "published": "2025-01-10",
        "closing": "2025-02-10",
        "estimate": "1000000",
        "currency": "INR",
        "supplier": "ACME Infra Pvt Ltd",
        "supplier_reg": "REG-1",
        "award_value": "950000",
        "award_date": "2025-03-01",
        "documents": [{"title": "Notice", "url": f"https://src/{idx}/notice.pdf"}],
    }
    base.update(overrides)
    return base


def _seed(db_session, tmp_path: Path, count: int = 4) -> None:
    for i in range(count):
        _write(tmp_path, _record(i))
    GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)


# --------------------------------------------------------------------- Phase 5


class TestIncrementalValidation:
    def test_resume_and_checkpoint_recovery(self, db_session, tmp_path: Path) -> None:
        _write(tmp_path, _record(0))
        GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        checkpoint = db_session.query(ImportCheckpoint).filter(ImportCheckpoint.source == ENGINE_SOURCE).one()
        assert checkpoint.last_processed_record == "E-0"
        # Add more files and resume: only the new records import; the first is skipped.
        for i in range(1, 3):
            _write(tmp_path, _record(i))
        stats = GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        assert stats.imported_tenders == 2
        assert stats.unchanged_records == 1

    def test_duplicate_handling(self, db_session, tmp_path: Path) -> None:
        _write(tmp_path, _record(0))
        GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        stats = GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        assert stats.imported_tenders == 0 and stats.unchanged_records == 1

    def test_update_and_history_preservation(self, db_session, tmp_path: Path) -> None:
        _write(tmp_path, _record(0))
        GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        tender_id = db_session.query(Tender).filter(Tender.reference_number == "ENGREF-0").one().id
        _write(tmp_path, _record(0, title="Revised road segment 0", estimate="2000000"))
        stats = GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)
        assert stats.updated_tenders == 1
        # Same row updated in place (id preserved), not duplicated.
        same = db_session.query(Tender).filter(Tender.reference_number == "ENGREF-0").one()
        assert same.id == tender_id
        assert same.estimated_value == Decimal("2000000")
        versions = db_session.query(SourceRecordVersion).filter(SourceRecordVersion.source_record_id == "E-0").all()
        assert sorted(v.action for v in versions) == ["imported", "updated"]
        # Both historical content hashes are retained.
        assert len({v.content_hash for v in versions}) == 2


# --------------------------------------------------------------------- Phase 1 (engine, crafted defects)


class TestDataQualityEngine:
    def test_detects_crafted_defects(self, db_session, tmp_path: Path) -> None:
        # Broken dates + invalid value + currency mismatch + missing docs.
        _write(tmp_path, _record(0, closing="2024-12-01", published="2025-01-10"))  # closing before publish
        _write(tmp_path, _record(1, award_date="2024-01-01"))  # award before publication
        _write(tmp_path, _record(2, award_value="-5"))  # invalid award value
        _write(tmp_path, _record(3, award_currency="USD"))  # currency mismatch
        _write(tmp_path, _record(4, documents=[]))  # missing evidence
        GenericConnectorImporter(db_session, ENGINE_SOURCE).import_directory(tmp_path)

        report = build_data_quality_report(db_session)
        by_code = {i.code: i for i in report.issues}
        assert by_code["broken_tender_dates"].count >= 1
        assert by_code["award_before_publication"].count >= 1
        assert by_code["invalid_award_values"].count >= 1
        assert by_code["currency_inconsistencies"].count >= 1
        assert by_code["missing_evidence"].count >= 1
        assert 0.0 <= report.quality_score <= 1.0
        # every check present
        expected = {
            "missing_titles", "missing_buyers", "duplicate_tenders", "duplicate_companies",
            "duplicate_awards", "broken_tender_dates", "award_before_publication",
            "award_before_closing", "invalid_award_values", "currency_inconsistencies",
            "entity_inconsistencies", "broken_references", "missing_source_urls",
            "missing_document_urls", "missing_evidence", "corrupted_awards",
        }
        assert expected <= set(by_code)


# --------------------------------------------------------------------- Phase 2


class TestCoverageEngine:
    def test_dimensions_and_attribution(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        report = build_coverage_engine_report(db_session)
        dims = {d.dimension for d in report.dimensions}
        assert {
            "source", "state", "ministry", "buyer", "supplier",
            "category", "procurement_method", "year", "currency", "organization",
        } <= dims
        state_dim = next(d for d in report.dimensions if d.dimension == "state")
        assert any(b.key == "Kerala" for b in state_dim.buckets)
        category_dim = next(d for d in report.dimensions if d.dimension == "category")
        assert any(b.key == "Construction & Roads" for b in category_dim.buckets)


# --------------------------------------------------------------------- Phase 3


class TestStatisticsEngine:
    def test_totals_and_rates(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        report = build_import_statistics(db_session)
        t = report.totals
        assert t.tenders >= 4
        assert t.contracts == t.awards
        assert t.directors == 0
        assert t.total_records == t.tenders + t.awards + t.companies + t.documents
        assert report.durations.total_runs >= 1
        assert any(m.code == "companies_normalized" for m in report.normalization_rates)
        assert report.notes  # director note present


# --------------------------------------------------------------------- Phase 4


class TestEvidenceIntegrity:
    def test_freshly_imported_records_are_traceable(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        report = build_evidence_integrity_report(db_session)
        by_code = {c.code: c for c in report.provenance_checks}
        # The importer stamps a content hash + URL on every seeded document, and
        # full provenance on every seeded tender, so they count as traceable.
        # (Ratios are over the whole DB, which may contain older hash-less rows.)
        assert by_code["evidence_hash"].present >= 4
        assert by_code["document_url"].present >= 4
        assert report.fully_traceable_tenders >= 4
        assert 0.0 <= report.integrity_score <= 1.0


# --------------------------------------------------------------------- Phase 6


class TestConnectorValidation:
    def test_test_source_is_verified(self, db_session, tmp_path: Path) -> None:
        _seed(db_session, tmp_path)
        report = build_connector_health_report(db_session)
        entry = next((c for c in report.connectors if c.name == ENGINE_SOURCE), None)
        assert entry is not None
        assert entry.import_capability == "verified"
        assert entry.tenders >= 4
        assert entry.award_coverage > 0
        assert entry.document_coverage > 0
        assert entry.normalization_score >= 0.0
        assert report.connectors_registered >= 8
