from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BenchmarkPopulation(BaseModel):
    level: str
    dimensions: dict[str, str]
    sample_size: int
    sufficient_sample: bool
    source_scope: str = "Indian procurement sources only"


class BenchmarkStats(BaseModel):
    minimum: Decimal | None = None
    p25: Decimal | None = None
    median: Decimal | None = None
    mean: Decimal | None = None
    p75: Decimal | None = None
    maximum: Decimal | None = None
    iqr: Decimal | None = None
    percentile: int | None = None
    deviation_iqr: Decimal | None = None


class TenderBenchmarkComparison(BaseModel):
    tender_id: str
    reference_number: str
    metric: str
    observed_value: Decimal | None
    currency: str | None
    benchmark_available: bool
    population: BenchmarkPopulation
    statistics: BenchmarkStats
    interpretation: str
    generated_at: datetime
    methodology: list[str] = Field(default_factory=list)
