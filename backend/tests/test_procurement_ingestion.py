"""Procurement ingestion-layer tests.

Covers the deterministic normalizers, connector metadata contract, the generic
importer (insert / update / document preservation / version history / resumable
skip / checkpoints) and the data-quality + coverage reports. Database-backed
tests use the rolled-back ``db_session`` fixture, so nothing is persisted.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

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
from app.connectors.registry import discover_connectors, register_connector
from app.importers.generic import GenericConnectorImporter, _record_content_hash
from app.models import Award, Company, Document, ImportCheckpoint, SourceRecordVersion, Tender
from app.normalization import (
    normalize_currency,
    normalize_org_name,
    normalize_reference,
    normalize_registration,
    org_match_key,
)
from app.services.coverage_report import build_coverage_report
from app.services.data_quality import build_data_quality_report

TEST_SOURCE = "test_ingest_source"


# --------------------------------------------------------------------- normalization


class TestNormalization:
    def test_org_display_strips_honorific_and_collapses(self) -> None:
        assert normalize_org_name("  M/s  ACME   Traders ") == "ACME Traders"
        assert normalize_org_name("Messrs. Foo & Bar") == "Foo & Bar"
        assert normalize_org_name("   ") is None

    def test_org_match_key_unifies_legal_suffixes(self) -> None:
        assert org_match_key("ACME Traders Pvt Ltd") == org_match_key("Acme Traders Private Limited")
        assert org_match_key("Foo Corp.") == org_match_key("FOO Corporation")
        assert org_match_key("The Bar & Co") == "bar"

    def test_registration_normalisation(self) -> None:
        assert normalize_registration("29-abcde 1234 f1z5") == "29ABCDE1234F1Z5"
        assert normalize_registration("  ") is None
        assert normalize_registration(None) is None

    def test_reference_normalisation(self) -> None:
        assert normalize_reference("  cppp / 123 ") == "CPPP/123"

    def test_currency_mapping(self) -> None:
        assert normalize_currency("Rs.") == "INR"
        assert normalize_currency("₹") == "INR"
        assert normalize_currency("usd") == "USD"
        assert normalize_currency(None) == "INR"
        assert normalize_currency("uah") == "UAH"


# --------------------------------------------------------------------- connector metadata


class TestConnectorMetadata:
    def test_every_registered_connector_has_complete_metadata(self) -> None:
        registry = discover_connectors()
        names = registry.names()
        assert names, "no connectors registered"
        for connector in registry.all():
            meta = connector.metadata
            assert isinstance(meta, SourceConnectorMetadata)
            assert meta.name and meta.label
            assert meta.name in names
            # The expanded contract fields must be present and non-empty.
            assert meta.supported_entities
            assert meta.last_update_capability
            assert meta.import_mechanism
            assert meta.normalization_quality

    def test_core_sources_are_registered(self) -> None:
        names = set(discover_connectors().names())
        for expected in ["cppp", "gem", "world_bank", "adb", "cag", "datagovin", "un_procurement", "prozorro"]:
            assert expected in names, f"{expected} connector not registered"


# --------------------------------------------------------------------- test connector


class _TestFlatConnector(FileBackedSourceConnector):
    """Deterministic connector used only by the importer tests.

    Reads a simple envelope shape so tests can craft unchanged / changed records
    precisely without depending on any production mapper's quirks.
    """

    metadata = SourceConnectorMetadata(
        name=TEST_SOURCE,
        label="Test Ingest Source",
        raw_directory="test_ingest_source",
    )

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        data = raw_record["data"]
        meta = NormalizedSourceMetadata(
            source_name=TEST_SOURCE,
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
        companies = []
        awards = []
        if data.get("supplier"):
            companies.append(
                NormalizedCompany(
                    name=data["supplier"],
                    registration_number=data.get("supplier_reg"),
                    metadata=meta,
                )
            )
            awards.append(
                NormalizedAward(
                    tender_reference_number=tender.reference_number,
                    company_name=data["supplier"],
                    company_registration_number=data.get("supplier_reg"),
                    award_date=parse_date(data.get("award_date")),
                    award_value=Decimal(str(data["award_value"])) if data.get("award_value") is not None else None,
                    currency=data.get("currency", "INR"),
                    metadata=meta,
                )
            )
        documents = [
            NormalizedDocument(title=doc["title"], url=doc["url"], document_type="attachment", metadata=meta)
            for doc in data.get("documents", [])
        ]
        return NormalizedProcurementRecord(
            tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record
        )


# Register once at import time so the generic importer can discover it.
register_connector(_TestFlatConnector)


def _write_envelope(directory: Path, data: dict[str, Any]) -> None:
    envelope = {"source_name": TEST_SOURCE, "source_record_id": str(data["id"]), "source_url": f"https://x/{data['id']}", "data": data}
    (directory / f"{data['id']}.json").write_text(json.dumps(envelope), encoding="utf-8")


def _base_record(idx: int) -> dict[str, Any]:
    return {
        "id": f"REC-{idx}",
        "reference": f"TESTREF-{idx}",
        "title": f"Supply of item {idx}",
        "buyer": "Public Works Department Pvt Ltd",
        "published": "2026-01-01",
        "closing": "2026-02-01",
        "estimate": "100000",
        "currency": "INR",
        "supplier": "ACME Traders Pvt Ltd",
        "supplier_reg": "REG-100",
        "award_value": "90000",
        "award_date": "2026-01-15",
        "documents": [{"title": "Tender notice", "url": f"https://x/{idx}/notice.pdf"}],
    }


# --------------------------------------------------------------------- importer


class TestGenericImporter:
    def test_content_hash_is_stable_and_sensitive(self) -> None:
        conn = _TestFlatConnector()
        rec = conn.normalize({"source_url": "u", "data": _base_record(1)})
        rec_same = conn.normalize({"source_url": "u", "data": _base_record(1)})
        changed = dict(_base_record(1), title="Different title")
        rec_changed = conn.normalize({"source_url": "u", "data": changed})
        assert _record_content_hash(rec) == _record_content_hash(rec_same)
        assert _record_content_hash(rec) != _record_content_hash(rec_changed)

    def test_import_inserts_tenders_companies_awards_documents(self, db_session, tmp_path: Path) -> None:
        for i in range(3):
            _write_envelope(tmp_path, _base_record(i))
        stats = GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)

        assert stats.imported_tenders == 3
        assert stats.imported_companies == 1  # all share one canonical supplier
        assert stats.imported_awards == 3
        assert stats.imported_documents == 3
        assert stats.versions_recorded == 3
        assert db_session.query(Tender).filter(Tender.source_name == TEST_SOURCE).count() == 3
        assert db_session.query(Document).count() >= 3

    def test_reimport_is_unchanged_and_resumable(self, db_session, tmp_path: Path) -> None:
        for i in range(2):
            _write_envelope(tmp_path, _base_record(i))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        stats2 = GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        # Second run recognises identical content hashes and skips everything.
        assert stats2.unchanged_records == 2
        assert stats2.imported_tenders == 0
        assert stats2.updated_tenders == 0
        assert stats2.versions_recorded == 0

    def test_changed_record_updates_in_place_and_versions(self, db_session, tmp_path: Path) -> None:
        _write_envelope(tmp_path, _base_record(0))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)

        updated = dict(_base_record(0), title="Revised title", estimate="250000")
        _write_envelope(tmp_path, updated)
        stats = GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)

        assert stats.updated_tenders == 1
        assert stats.imported_tenders == 0
        tender = db_session.query(Tender).filter(Tender.reference_number == "TESTREF-0").one()
        assert tender.title == "Revised title"
        assert tender.estimated_value == Decimal("250000")
        # Two versions recorded for the same source record: imported + updated.
        versions = (
            db_session.query(SourceRecordVersion)
            .filter(SourceRecordVersion.source_record_id == "REC-0")
            .all()
        )
        assert {v.action for v in versions} == {"imported", "updated"}

    def test_checkpoint_is_recorded(self, db_session, tmp_path: Path) -> None:
        _write_envelope(tmp_path, _base_record(0))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        checkpoint = (
            db_session.query(ImportCheckpoint).filter(ImportCheckpoint.source == TEST_SOURCE).one_or_none()
        )
        assert checkpoint is not None
        assert checkpoint.last_processed_record
        assert checkpoint.last_successful_import_at is not None

    def test_documents_are_deduplicated_on_reimport(self, db_session, tmp_path: Path) -> None:
        _write_envelope(tmp_path, _base_record(0))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        before = db_session.query(Document).count()
        # Change only the title -> record re-processed, but the same document URL/title
        # must not create a duplicate row.
        _write_envelope(tmp_path, dict(_base_record(0), title="New"))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        after = db_session.query(Document).count()
        assert after == before


# --------------------------------------------------------------------- reports


class TestReports:
    def _seed(self, db_session, tmp_path: Path, count: int = 3) -> None:
        for i in range(count):
            _write_envelope(tmp_path, _base_record(i))
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)

    def test_data_quality_report_structure(self, db_session, tmp_path: Path) -> None:
        self._seed(db_session, tmp_path)
        report = build_data_quality_report(db_session)
        codes = {issue.code for issue in report.issues}
        assert {
            "duplicate_companies",
            "missing_evidence",
            "broken_tender_dates",
            "invalid_award_values",
            "missing_identifiers",
            "currency_inconsistencies",
        } <= codes
        assert report.total_tenders >= 3
        for metric in report.normalization_coverage + report.evidence_completeness:
            assert 0.0 <= metric.ratio <= 1.0

    def test_data_quality_flags_duplicate_companies(self, db_session, tmp_path: Path) -> None:
        # Two suppliers that differ only by legal suffix/case -> one canonical dup.
        rec_a = dict(_base_record(0), supplier="Globex Pvt Ltd", supplier_reg=None)
        rec_b = dict(_base_record(1), supplier="GLOBEX Private Limited", supplier_reg=None)
        _write_envelope(tmp_path, rec_a)
        _write_envelope(tmp_path, rec_b)
        GenericConnectorImporter(db_session, TEST_SOURCE).import_directory(tmp_path)
        report = build_data_quality_report(db_session)
        dup = next(i for i in report.issues if i.code == "duplicate_companies")
        # Both should have merged to a single company via the match key -> 0 dupes.
        globex = [c for c in db_session.query(Company).all() if org_match_key(c.name) == "globex"]
        assert len(globex) == 1
        assert dup.count == 0

    def test_coverage_report_reflects_imports(self, db_session, tmp_path: Path) -> None:
        self._seed(db_session, tmp_path)
        report = build_coverage_report(db_session)
        assert report.totals.connectors_registered >= 8
        entry = next((c for c in report.connectors if c.name == TEST_SOURCE), None)
        assert entry is not None
        assert entry.tenders == 3
        assert entry.versions == 3
        assert entry.health == "active"
        assert report.provenance.source_record_versions >= 3
