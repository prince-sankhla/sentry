from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BenchmarkDimensions(BaseModel):
    """Dimensions that define a benchmark comparison population.

    All dimensions are optional; a benchmark can be dimensioned by any subset.
    Dimensions are matched exactly (buyer name must match exactly, etc.).
    """

    buyer: str | None = None
    category: str | None = None
    procurement_method: str | None = None
    geography: str | None = None
    value_band: str | None = None  # e.g., "0-1M", "1M-10M", "10M+"
    date_range: tuple[date, date] | None = None


class BenchmarkResult(BaseModel):
    """Result of a benchmark computation over a tender population."""

    benchmark_key: str
    dimensions: BenchmarkDimensions
    metric: str
    sample_size: int
    sufficient_sample: bool

    # Statistics (None if insufficient sample or metric not applicable)
    median: Decimal | None = None
    p25: Decimal | None = None
    p75: Decimal | None = None
    iqr: Decimal | None = None
    mean: Decimal | None = None
    stddev: Decimal | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None

    # Provenance
    sample_tender_ids: list[str] = Field(default_factory=list)
    source_query_hash: str

    # Freshness
    created_at: datetime
    refresh_at: datetime


class BenchmarkComparison(BaseModel):
    """Result of comparing an observed value against a benchmark.

    Provides deviation (in IQR units), percentile rank, and contextual severity.
    """

    observed_value: Decimal
    benchmark: BenchmarkResult
    deviation: Decimal | None = None  # (observed - median) / IQR, None if IQR=0
    percentile: int | None = None  # 0-100, None if insufficient sample
    severity: str | None = None  # "normal", "moderate", "high", "critical", or None
    explanation: str
