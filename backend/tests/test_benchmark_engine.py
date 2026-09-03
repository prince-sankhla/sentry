"""Tests for BenchmarkEngine — contextual procurement benchmarking.

Tests verify:
- Correct statistics computation (median, P25, P75, IQR)
- Sample size handling (sufficient vs insufficient)
- NULL/invalid value filtering
- Deterministic benchmark key generation
- Caching and refresh behavior
- Dimension filtering
- Metric separation
- Reproducibility
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.models.award import Award
from app.models.company import Company
from app.schemas.benchmark import BenchmarkDimensions
from app.services.benchmark_engine import (
    get_benchmark,
    build_benchmark,
    compare_to_benchmark,
    refresh_stale_benchmarks,
    _classify_value_band,
    _build_benchmark_key,
    MIN_SAMPLE_SIZE,
)


@pytest.fixture
def seed_tenders(db_session: Session):
    """Seed tenders with varying values for benchmark testing."""
    tenders = []
    # Create 10 tenders with estimated values: 10k, 20k, ..., 100k
    for i in range(1, 11):
        tender = Tender(
            reference_number=f"TEST-{i:03d}",
            title=f"Test Tender {i}",
            procuring_entity="Test Buyer A",
            published_date=date(2025, 1, 1),
            closing_date=date(2025, 2, 1),
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
        tenders.append(tender)
    db_session.commit()
    return tenders


@pytest.fixture
def seed_awards(db_session: Session, seed_tenders):
    """Seed awards with varying values."""
    company = Company(name="Test Supplier", source_name="test")
    db_session.add(company)
    db_session.flush()

    awards = []
    for i, tender in enumerate(seed_tenders, 1):
        award = Award(
            tender_id=tender.id,
            company_id=company.id,
            award_value=Decimal(i * 15000),  # Different from tender values
            award_date=date(2025, 3, 1),
            currency="INR",
            source_name="test",
        )
        db_session.add(award)
        awards.append(award)
    db_session.commit()
    return awards


def test_build_benchmark_sufficient_sample(db_session: Session, seed_tenders):
    """With 10 tenders in population, benchmark computes correctly."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 10
    assert result.sufficient_sample is True
    assert result.median == Decimal("55000")  # Median of 10k..100k
    assert result.p25 == Decimal("27500")  # 25th percentile (statistics.quantiles)
    assert result.p75 == Decimal("82500")  # 75th percentile
    assert result.iqr == Decimal("55000")  # 82.5k - 27.5k
    assert result.min_value == Decimal("10000")
    assert result.max_value == Decimal("100000")
    assert len(result.sample_tender_ids) == 10


def test_build_benchmark_insufficient_sample(db_session: Session):
    """With 3 tenders in population, benchmark flags insufficient sample."""
    # Seed only 3 tenders
    for i in range(1, 4):
        tender = Tender(
            reference_number=f"SMALL-{i}",
            title=f"Small Sample {i}",
            procuring_entity="Test Buyer B",
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    dimensions = BenchmarkDimensions(buyer="Test Buyer B")
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 3
    assert result.sufficient_sample is False  # Below MIN_SAMPLE_SIZE=5
    assert result.median is None  # Statistics not computed for insufficient sample
    assert result.p25 is None
    assert result.p75 is None


def test_get_benchmark_cache_hit(db_session: Session, seed_tenders):
    """Second call to get_benchmark returns cached result."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")

    # First call builds benchmark
    result1 = get_benchmark(db_session, dimensions, "estimated_value")
    assert result1 is not None
    created_at_1 = result1.created_at

    # Second call should return cached benchmark (same created_at)
    result2 = get_benchmark(db_session, dimensions, "estimated_value")
    assert result2 is not None
    assert result2.created_at == created_at_1
    assert result2.benchmark_key == result1.benchmark_key


def test_get_benchmark_cache_miss_builds_new(db_session: Session, seed_tenders):
    """First call to get_benchmark builds and caches."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")
    result = get_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 10
    # Verify benchmark was stored in DB
    from app.models.benchmark import Benchmark
    from sqlalchemy import select
    cached = db_session.scalar(select(Benchmark).where(Benchmark.benchmark_key == result.benchmark_key))
    assert cached is not None
    assert cached.sample_size == 10


def test_benchmark_refresh_stale(db_session: Session, seed_tenders):
    """Stale benchmark (>7 days old) is recomputed on next get_benchmark."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")

    # Build initial benchmark
    result1 = build_benchmark(db_session, dimensions, "estimated_value")
    assert result1 is not None
    initial_refresh_at = result1.refresh_at

    # Manually mark benchmark as stale (refresh_at in past)
    from app.models.benchmark import Benchmark
    from sqlalchemy import select
    benchmark = db_session.scalar(select(Benchmark).where(Benchmark.benchmark_key == result1.benchmark_key))
    benchmark.refresh_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    # get_benchmark should rebuild (since stale)
    result2 = get_benchmark(db_session, dimensions, "estimated_value")
    assert result2 is not None
    # Verify benchmark was refreshed (refresh_at updated to future)
    assert result2.refresh_at > initial_refresh_at
    assert result2.refresh_at > datetime.now(timezone.utc)


def test_benchmark_deviation_calculation(db_session: Session, seed_tenders):
    """Deviation is (observed - median) / IQR."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")
    benchmark = build_benchmark(db_session, dimensions, "estimated_value")

    # observed=100k, median=55k, IQR=55k → deviation = (100-55)/55 = 0.82
    comparison = compare_to_benchmark(Decimal("100000"), benchmark)
    assert abs(comparison.deviation - Decimal("0.82")) < Decimal("0.01")
    assert comparison.severity == "normal"  # abs(deviation) < 1.0

    # observed=200k, median=55k, IQR=55k → deviation = (200-55)/55 = 2.64
    comparison2 = compare_to_benchmark(Decimal("200000"), benchmark)
    assert abs(comparison2.deviation - Decimal("2.64")) < Decimal("0.01")
    assert comparison2.severity == "high"  # 2.0 <= abs(deviation) < 3.0


def test_benchmark_percentile_calculation(db_session: Session, seed_tenders):
    """Percentile ranks observed value in population."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")
    benchmark = build_benchmark(db_session, dimensions, "estimated_value")

    # observed=35k (between 27.5k P25 and 55k median) → percentile ~25-40
    comparison = compare_to_benchmark(Decimal("35000"), benchmark)
    assert comparison.percentile is not None
    assert 20 <= comparison.percentile <= 40  # Approximate due to linear interpolation


def test_value_band_classification():
    """Value bands partition tenders into comparable groups."""
    assert _classify_value_band(Decimal("500000")) == "0-1M"
    assert _classify_value_band(Decimal("5000000")) == "1M-10M"
    assert _classify_value_band(Decimal("50000000")) == "10M-100M"
    assert _classify_value_band(Decimal("500000000")) == "100M+"
    assert _classify_value_band(Decimal("999999")) == "0-1M"  # Just below 1M
    assert _classify_value_band(Decimal("1000000")) == "1M-10M"  # Exactly 1M (inclusive lower)
    assert _classify_value_band(None) is None
    assert _classify_value_band(Decimal("-100")) is None  # Negative


def test_benchmark_excludes_null_values(db_session: Session):
    """NULL values excluded from benchmark calculation."""
    # Seed 10 tenders: 5 with values, 5 with NULL
    for i in range(1, 6):
        tender = Tender(
            reference_number=f"VALID-{i}",
            title=f"Valid {i}",
            procuring_entity="Test Buyer C",
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    for i in range(6, 11):
        tender = Tender(
            reference_number=f"NULL-{i}",
            title=f"Null {i}",
            procuring_entity="Test Buyer C",
            estimated_value=None,  # NULL
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    dimensions = BenchmarkDimensions(buyer="Test Buyer C")
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 5  # Only non-NULL values counted
    assert result.median == Decimal("30000")  # Median of 10k, 20k, 30k, 40k, 50k


def test_benchmark_excludes_soft_deleted(db_session: Session):
    """Soft-deleted tenders excluded from benchmark."""
    # Seed 10 tenders: 5 active, 5 soft-deleted
    for i in range(1, 6):
        tender = Tender(
            reference_number=f"ACTIVE-{i}",
            title=f"Active {i}",
            procuring_entity="Test Buyer D",
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    for i in range(6, 11):
        tender = Tender(
            reference_number=f"DELETED-{i}",
            title=f"Deleted {i}",
            procuring_entity="Test Buyer D",
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=datetime.now(timezone.utc),  # Soft-deleted
        )
        db_session.add(tender)
    db_session.commit()

    dimensions = BenchmarkDimensions(buyer="Test Buyer D")
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 5  # Only active tenders
    assert result.median == Decimal("30000")


def test_deterministic_benchmark_key():
    """Same dimensions + metric produce same benchmark_key."""
    dim1 = BenchmarkDimensions(buyer="Buyer A", category="Construction")
    dim2 = BenchmarkDimensions(buyer="Buyer A", category="Construction")
    dim3 = BenchmarkDimensions(buyer="Buyer A", category="Roads")

    key1 = _build_benchmark_key(dim1, "estimated_value")
    key2 = _build_benchmark_key(dim2, "estimated_value")
    key3 = _build_benchmark_key(dim3, "estimated_value")

    assert key1 == key2  # Same dimensions → same key
    assert key1 != key3  # Different dimensions → different key


def test_repeated_build_produces_equivalent_result(db_session: Session, seed_tenders):
    """Building same benchmark twice produces same statistics."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")

    result1 = build_benchmark(db_session, dimensions, "estimated_value")
    result2 = build_benchmark(db_session, dimensions, "estimated_value")

    assert result1.median == result2.median
    assert result1.p25 == result2.p25
    assert result1.p75 == result2.p75
    assert result1.iqr == result2.iqr
    assert result1.sample_size == result2.sample_size


def test_metric_separation(db_session: Session, seed_tenders, seed_awards):
    """estimated_value and award_value metrics produce separate benchmarks."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")

    tender_benchmark = build_benchmark(db_session, dimensions, "estimated_value")
    award_benchmark = build_benchmark(db_session, dimensions, "award_value")

    assert tender_benchmark is not None
    assert award_benchmark is not None
    assert tender_benchmark.benchmark_key != award_benchmark.benchmark_key
    assert tender_benchmark.median != award_benchmark.median  # Different values
    # Tender median: 55k, Award median: 82.5k (15k steps)
    assert tender_benchmark.median == Decimal("55000")
    assert award_benchmark.median == Decimal("82500")


def test_dimension_separation(db_session: Session):
    """Different buyers produce separate benchmarks."""
    # Seed tenders for two different buyers
    for buyer, prefix in [("Buyer A", "A"), ("Buyer B", "B")]:
        for i in range(1, 6):
            tender = Tender(
                reference_number=f"{prefix}-{i}",
                title=f"{buyer} Tender {i}",
                procuring_entity=buyer,
                estimated_value=Decimal(i * 10000),
                currency="INR",
                source_name="test",
                deleted_at=None,
            )
            db_session.add(tender)
    db_session.commit()

    dim_a = BenchmarkDimensions(buyer="Buyer A")
    dim_b = BenchmarkDimensions(buyer="Buyer B")

    benchmark_a = build_benchmark(db_session, dim_a, "estimated_value")
    benchmark_b = build_benchmark(db_session, dim_b, "estimated_value")

    assert benchmark_a is not None
    assert benchmark_b is not None
    assert benchmark_a.benchmark_key != benchmark_b.benchmark_key
    assert benchmark_a.sample_size == 5
    assert benchmark_b.sample_size == 5


def test_empty_population_returns_none(db_session: Session):
    """Empty population (no matching tenders) returns None."""
    dimensions = BenchmarkDimensions(buyer="Nonexistent Buyer")
    result = build_benchmark(db_session, dimensions, "estimated_value")
    assert result is None


def test_zero_negative_values_excluded(db_session: Session):
    """Zero and negative values excluded from benchmark."""
    for i, val in enumerate([Decimal("-1000"), Decimal("0"), Decimal("10000"), Decimal("20000"), Decimal("30000")]):
        tender = Tender(
            reference_number=f"VAL-{i}",
            title=f"Value {i}",
            procuring_entity="Test Buyer E",
            estimated_value=val,
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    dimensions = BenchmarkDimensions(buyer="Test Buyer E")
    result = build_benchmark(db_session, dimensions, "estimated_value")

    assert result is not None
    assert result.sample_size == 3  # Only positive values
    assert result.min_value == Decimal("10000")


def test_compare_insufficient_sample(db_session: Session):
    """Comparison against insufficient-sample benchmark explains limitation."""
    # Create insufficient sample benchmark (3 tenders)
    for i in range(1, 4):
        tender = Tender(
            reference_number=f"INS-{i}",
            title=f"Insufficient {i}",
            procuring_entity="Test Buyer F",
            estimated_value=Decimal(i * 10000),
            currency="INR",
            source_name="test",
            deleted_at=None,
        )
        db_session.add(tender)
    db_session.commit()

    dimensions = BenchmarkDimensions(buyer="Test Buyer F")
    benchmark = build_benchmark(db_session, dimensions, "estimated_value")

    comparison = compare_to_benchmark(Decimal("50000"), benchmark)
    assert comparison.deviation is None
    assert comparison.percentile is None
    assert comparison.severity is None
    assert "Insufficient benchmark sample" in comparison.explanation


def test_refresh_stale_benchmarks(db_session: Session, seed_tenders):
    """refresh_stale_benchmarks rebuilds benchmarks past refresh_at."""
    dimensions = BenchmarkDimensions(buyer="Test Buyer A")
    build_benchmark(db_session, dimensions, "estimated_value")

    # Mark as stale
    from app.models.benchmark import Benchmark
    from sqlalchemy import select, update
    db_session.execute(
        update(Benchmark).values(refresh_at=datetime.now(timezone.utc) - timedelta(days=1))
    )
    db_session.commit()

    # Refresh stale benchmarks
    count = refresh_stale_benchmarks(db_session, limit=10)
    assert count == 1  # One benchmark refreshed

    # Verify benchmark now has future refresh_at
    benchmark = db_session.scalar(select(Benchmark))
    assert benchmark.refresh_at > datetime.now(timezone.utc)
