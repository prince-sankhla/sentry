"""Tests for tender enrichment — procurement_method, geography, category fields.

Tests verify:
- Enrichment fields persist to database
- Taxonomy classifiers correctly derive values
- NULL/unknown handling
- Benchmark dimension filtering by enrichment fields
- Regression: existing BenchmarkEngine tests still pass
"""

import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.connectors.base import (
    NormalizedSourceMetadata,
    NormalizedTender,
    NormalizedProcurementRecord,
)
from app.connectors.enrichment import enrich_tender
from app.models.tender import Tender
from app.schemas.benchmark import BenchmarkDimensions
from app.services.benchmark_engine import build_benchmark
from app.services.procurement_taxonomy import UNATTRIBUTED, UNSPECIFIED, OTHER


def test_enrich_tender_derives_procurement_method():
    """Enrichment derives procurement_method from title/description."""
    tender = NormalizedTender(
        reference_number="TEST-001",
        title="Open Tender for Road Construction",
        description="Competitive bidding process",
        procuring_entity="Test PWD",
        published_date=date(2025, 1, 1),
        closing_date=date(2025, 2, 1),
        estimated_value=Decimal("1000000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="001",
            source_url=None,
            retrieved_at=None,
        ),
    )

    enriched = enrich_tender(tender)
    assert enriched.procurement_method == "Open Tender"


def test_enrich_tender_derives_geography():
    """Enrichment derives geography from procuring_entity."""
    tender = NormalizedTender(
        reference_number="TEST-002",
        title="Construction Project",
        description=None,
        procuring_entity="Maharashtra Public Works Department",
        published_date=date(2025, 1, 1),
        closing_date=None,
        estimated_value=Decimal("500000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="002",
            source_url=None,
            retrieved_at=None,
        ),
    )

    enriched = enrich_tender(tender)
    assert enriched.geography == "Maharashtra"


def test_enrich_tender_derives_category():
    """Enrichment derives category from title/description."""
    tender = NormalizedTender(
        reference_number="TEST-003",
        title="Supply of Medical Equipment for Hospital",
        description="Healthcare procurement medical supplies",
        procuring_entity="Test Hospital",
        published_date=date(2025, 1, 1),
        closing_date=None,
        estimated_value=Decimal("200000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="003",
            source_url=None,
            retrieved_at=None,
        ),
    )

    enriched = enrich_tender(tender)
    # Taxonomy returns "Medical & Health" for medical/hospital keywords
    assert enriched.category == "Medical & Health"


def test_enrich_tender_null_when_unspecified():
    """Enrichment returns None for UNSPECIFIED/OTHER/UNATTRIBUTED."""
    tender = NormalizedTender(
        reference_number="TEST-004",
        title="Generic Project XYZ",
        description=None,
        procuring_entity="Unknown Entity",
        published_date=date(2025, 1, 1),
        closing_date=None,
        estimated_value=Decimal("100000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="004",
            source_url=None,
            retrieved_at=None,
        ),
    )

    enriched = enrich_tender(tender)
    # Unrecognized values should become None
    assert enriched.procurement_method is None
    assert enriched.geography is None
    assert enriched.category is None


def test_enrich_tender_preserves_existing():
    """Enrichment preserves already-set fields."""
    tender = NormalizedTender(
        reference_number="TEST-005",
        title="Test",
        description=None,
        procuring_entity="Test",
        published_date=date(2025, 1, 1),
        closing_date=None,
        estimated_value=Decimal("100000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="005",
            source_url=None,
            retrieved_at=None,
        ),
        procurement_method="Custom Method",
        geography="Custom State",
        category="Custom Category",
    )

    enriched = enrich_tender(tender)
    # Should return original tender unchanged
    assert enriched.procurement_method == "Custom Method"
    assert enriched.geography == "Custom State"
    assert enriched.category == "Custom Category"


def test_tender_enrichment_persists_to_database(db_session: Session):
    """Enriched fields persist when tender imported to database."""
    # Create tender directly in DB to test enrichment persistence
    from app.connectors.enrichment import enrich_tender

    tender_data = NormalizedTender(
        reference_number="PERSIST-001",
        title="Open Tender for Road Construction in Kerala",
        description="Highway construction project",
        procuring_entity="Kerala Public Works Department",
        published_date=date(2025, 1, 1),
        closing_date=date(2025, 2, 1),
        estimated_value=Decimal("5000000"),
        currency="INR",
        metadata=NormalizedSourceMetadata(
            source_name="test",
            source_record_id="persist001",
            source_url=None,
            retrieved_at=None,
        ),
    )

    # Enrich and create tender
    enriched = enrich_tender(tender_data)
    tender = Tender(
        reference_number=enriched.reference_number,
        title=enriched.title,
        description=enriched.description,
        procuring_entity=enriched.procuring_entity,
        published_date=enriched.published_date,
        closing_date=enriched.closing_date,
        estimated_value=enriched.estimated_value,
        currency=enriched.currency,
        procurement_method=enriched.procurement_method,
        geography=enriched.geography,
        category=enriched.category,
        source_name=enriched.metadata.source_name,
        deleted_at=None,
    )
    db_session.add(tender)
    db_session.commit()

    # Fetch from DB and verify enrichment fields persisted
    from sqlalchemy import select
    fetched = db_session.scalar(select(Tender).where(Tender.reference_number == "PERSIST-001"))
    assert fetched is not None
    assert fetched.procurement_method == "Open Tender"
    assert fetched.geography == "Kerala"
    assert fetched.category is not None  # Category derived from construction/road keywords


def test_benchmark_filters_by_procurement_method(db_session: Session):
    """Benchmark correctly filters by procurement_method dimension."""
    # Seed tenders with different methods (sufficient sample)
    for i in range(1, 11):
        method = "Open Tender" if i <= 7 else "Limited Tender"
        tender = Tender(
            reference_number=f"METHOD-{i}",
            title=f"Tender {i}",
            procuring_entity="Test Buyer",
            estimated_value=Decimal(i * 100000),
            currency="INR",
            procurement_method=method,
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    # Benchmark only "Open Tender" methods
    dimensions = BenchmarkDimensions(
        buyer="Test Buyer",
        procurement_method="Open Tender",
    )
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 7  # 7 "Open Tender" tenders
    assert result.sufficient_sample is True
    assert result.median == Decimal("400000")  # Median of 100k..700k


def test_benchmark_filters_by_geography(db_session: Session):
    """Benchmark correctly filters by geography dimension."""
    # Seed tenders in different states (sufficient sample)
    for i in range(1, 11):
        state = "Maharashtra" if i <= 7 else "Kerala"
        tender = Tender(
            reference_number=f"GEO-{i}",
            title=f"Tender {i}",
            procuring_entity="Test Buyer",
            estimated_value=Decimal(i * 100000),
            currency="INR",
            geography=state,
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    # Benchmark only Maharashtra tenders
    dimensions = BenchmarkDimensions(
        buyer="Test Buyer",
        geography="Maharashtra",
    )
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 7  # 7 Maharashtra tenders
    assert result.sufficient_sample is True
    assert result.median == Decimal("400000")  # Median of 100k..700k


def test_benchmark_filters_by_category(db_session: Session):
    """Benchmark correctly filters by category dimension."""
    # Seed tenders in different categories (sufficient sample)
    for i in range(1, 11):
        cat = "Construction & Roads" if i <= 7 else "Healthcare & Medical"
        tender = Tender(
            reference_number=f"CAT-{i}",
            title=f"Tender {i}",
            procuring_entity="Test Buyer",
            estimated_value=Decimal(i * 100000),
            currency="INR",
            category=cat,
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    # Benchmark only Construction tenders
    dimensions = BenchmarkDimensions(
        buyer="Test Buyer",
        category="Construction & Roads",
    )
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 7  # 7 Construction tenders
    assert result.sufficient_sample is True
    assert result.median == Decimal("400000")  # Median of 100k..700k


def test_benchmark_combines_multiple_enrichment_dimensions(db_session: Session):
    """Benchmark correctly filters by multiple enrichment dimensions simultaneously."""
    # Seed tenders with various enrichment combinations (sufficient sample for target)
    tenders_data = [
        # Target: Open + Maharashtra + Construction (5 tenders for sufficient sample)
        ("MULTI-1", "Open Tender", "Maharashtra", "Construction & Roads", Decimal("100000")),
        ("MULTI-2", "Open Tender", "Maharashtra", "Construction & Roads", Decimal("200000")),
        ("MULTI-3", "Open Tender", "Maharashtra", "Construction & Roads", Decimal("300000")),
        ("MULTI-4", "Open Tender", "Maharashtra", "Construction & Roads", Decimal("400000")),
        ("MULTI-5", "Open Tender", "Maharashtra", "Construction & Roads", Decimal("500000")),
        # Other combinations
        ("MULTI-6", "Open Tender", "Maharashtra", "Healthcare & Medical", Decimal("600000")),
        ("MULTI-7", "Open Tender", "Kerala", "Construction & Roads", Decimal("700000")),
        ("MULTI-8", "Limited Tender", "Maharashtra", "Construction & Roads", Decimal("800000")),
    ]
    for ref, method, geo, cat, value in tenders_data:
        tender = Tender(
            reference_number=ref,
            title=f"Tender {ref}",
            procuring_entity="Test Buyer",
            estimated_value=value,
            currency="INR",
            procurement_method=method,
            geography=geo,
            category=cat,
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    # Benchmark: Open Tender + Maharashtra + Construction
    dimensions = BenchmarkDimensions(
        buyer="Test Buyer",
        procurement_method="Open Tender",
        geography="Maharashtra",
        category="Construction & Roads",
    )
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 5  # MULTI-1 through MULTI-5
    assert result.sufficient_sample is True
    assert result.median == Decimal("300000")  # Median of 100k, 200k, 300k, 400k, 500k


def test_benchmark_null_enrichment_fields_excluded(db_session: Session):
    """Tenders with NULL enrichment fields excluded when dimension specified."""
    # Seed tenders: some with method, some without (sufficient sample)
    for i in range(1, 11):
        tender = Tender(
            reference_number=f"NULL-{i}",
            title=f"Tender {i}",
            procuring_entity="Test Buyer",
            estimated_value=Decimal(i * 100000),
            currency="INR",
            procurement_method="Open Tender" if i <= 7 else None,
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    # Benchmark with procurement_method dimension
    dimensions = BenchmarkDimensions(
        buyer="Test Buyer",
        procurement_method="Open Tender",
    )
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 7  # Only non-NULL method tenders
    assert result.sufficient_sample is True
