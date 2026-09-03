from datetime import date
from decimal import Decimal

from app.schemas.phase6_benchmark import BenchmarkStats
from app.services.phase6_benchmark import MIN_SAMPLE_SIZE, _percentile, _stats, _value_band


def test_value_band_boundaries() -> None:
    assert _value_band(Decimal("999999.99")) == "0-1M"
    assert _value_band(Decimal("1000000")) == "1M-10M"
    assert _value_band(Decimal("10000000")) == "10M-100M"
    assert _value_band(Decimal("100000000")) == "100M+"
    assert _value_band(None) is None


def test_percentile_midpoint_and_duplicates() -> None:
    values = [Decimal("10"), Decimal("20"), Decimal("20"), Decimal("30")]
    assert _percentile(values, Decimal("20")) == 50
    assert _percentile(values, Decimal("40")) == 100


def test_insufficient_sample_does_not_create_inferential_statistics() -> None:
    values = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40")]
    stats = _stats(values, Decimal("50"))
    assert len(values) == MIN_SAMPLE_SIZE - 1
    assert stats.median is None
    assert stats.p25 is None
    assert stats.p75 is None
    assert stats.mean is None
    assert stats.minimum == Decimal("10")
    assert stats.maximum == Decimal("40")


def test_sufficient_sample_uses_inclusive_quartiles() -> None:
    values = [Decimal(str(v)) for v in [10, 20, 30, 40, 50, 60, 70, 80]]
    stats = _stats(values, Decimal("80"))
    assert isinstance(stats, BenchmarkStats)
    assert stats.median == Decimal("45")
    assert stats.p25 == Decimal("27.5")
    assert stats.p75 == Decimal("62.5")
    assert stats.iqr == Decimal("35")
    assert stats.percentile == 94


def test_schema_imports_without_extra_dependencies() -> None:
    assert date(2026, 1, 1).isoformat() == "2026-01-01"
