"""Schemas for procurement import statistics (Phase 3)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class EntityTotals(BaseModel):
    total_records: int          # tenders + awards + companies + documents
    tenders: int
    awards: int
    contracts: int              # awarded contracts == Award rows
    buyers: int                 # distinct procuring entities
    suppliers: int              # distinct companies that hold >= 1 award
    companies: int              # all company rows
    directors: int              # not modelled in the ingestion layer (see notes)
    documents: int
    evidence_records: int       # preserved document + source-version snapshots
    source_versions: int
    total_award_value: Decimal


class RateMetric(BaseModel):
    code: str
    label: str
    numerator: int
    denominator: int
    rate: float


class ImportDurationStats(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    total_duration_seconds: float
    average_duration_seconds: float
    last_run_at: str | None = None
    records_per_second: float = 0.0


class ImportStatisticsReport(BaseModel):
    generated_at: str
    totals: EntityTotals
    coverage_percentages: list[RateMetric]
    duplicate_rates: list[RateMetric]
    normalization_rates: list[RateMetric]
    durations: ImportDurationStats
    notes: list[str]
