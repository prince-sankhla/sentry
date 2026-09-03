"""Tests for COMP-001 Competition Anomaly Detector.

Current implementation returns empty list due to missing Bid model.
Tests verify honest INSUFFICIENT_DATA behavior.
"""

import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.investigation_executor import (
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationTenderResult,
    InvestigationAwardResult,
    InvestigationSourceMetadata,
)
from app.services.comp001_detector import (
    detect_comp001_competition_anomaly,
    detect_comp001_with_bid_data,
)


def test_comp001_returns_empty_without_bid_data(db_session: Session):
    """COMP-001 returns empty list when Bid model doesn't exist."""
    tender = InvestigationTenderResult(
        reference_number="TEST-001",
        title="Test Tender",
        description=None,
        procuring_entity="Test Buyer",
        published_date=date(2025, 1, 1),
        closing_date=date(2025, 2, 1),
        estimated_value=Decimal("1000000"),
        currency="INR",
        procurement_method="Open Tender",
        geography="Maharashtra",
        category="Construction & Roads",
        metadata=InvestigationSourceMetadata(
            source_name="test",
            source_record_id="001",
            source_url=None,
            retrieved_at=None,
        ),
    )

    award = InvestigationAwardResult(
        tender_reference_number="TEST-001",
        company_name="Winner Corp",
        company_registration_number=None,
        award_date=date(2025, 3, 1),
        award_value=Decimal("950000"),
        currency="INR",
        metadata=InvestigationSourceMetadata(
            source_name="test",
            source_record_id="001-award",
            source_url=None,
            retrieved_at=None,
        ),
    )

    record = InvestigationProcurementRecord(
        tender=tender,
        awards=[award],
        companies=[],
        documents=[],
    )

    pkg = InvestigationPackage(
        subject="Test",
        investigation_type="tender",
        records=[record],
        indicators=[],
        plan=None,  # Required field
    )

    indicators = detect_comp001_competition_anomaly(pkg, db_session)

    # Honest behavior: return empty list, don't fabricate signals
    assert indicators == []


def test_comp001_does_not_fabricate_from_award_count(db_session: Session):
    """COMP-001 does NOT use award count as bidder count proxy."""
    tender = InvestigationTenderResult(
        reference_number="TEST-002",
        title="Single Award Tender",
        description=None,
        procuring_entity="Test Buyer",
        published_date=date(2025, 1, 1),
        closing_date=None,
        estimated_value=Decimal("500000"),
        currency="INR",
        metadata=InvestigationSourceMetadata(
            source_name="test",
            source_record_id="002",
            source_url=None,
            retrieved_at=None,
        ),
    )

    # Single award - but we DON'T know if this was 1 bidder or 10 bidders
    award = InvestigationAwardResult(
        tender_reference_number="TEST-002",
        company_name="Winner",
        company_registration_number=None,
        award_date=date(2025, 3, 1),
        award_value=Decimal("450000"),
        currency="INR",
        metadata=InvestigationSourceMetadata(
            source_name="test",
            source_record_id="002-award",
            source_url=None,
            retrieved_at=None,
        ),
    )

    record = InvestigationProcurementRecord(
        tender=tender,
        awards=[award],
        companies=[],
        documents=[],
    )

    pkg = InvestigationPackage(
        subject="Test",
        investigation_type="tender",
        records=[record],
        indicators=[],
        plan=None,  # Required field
    )

    indicators = detect_comp001_competition_anomaly(pkg, db_session)

    # Should NOT flag as competition anomaly (we don't have bidder data)
    assert indicators == []


def test_comp001_future_implementation_not_callable():
    """Future Bid-based detector raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as exc_info:
        detect_comp001_with_bid_data(None, None)

    assert "Bid model does not exist" in str(exc_info.value)
    assert "Implement P1 Bid ingestion" in str(exc_info.value)
