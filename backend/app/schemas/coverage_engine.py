"""Schemas for multi-dimensional procurement coverage reports.

See :mod:`app.services.coverage_engine`. Every count is a real aggregate from
the ingestion tables; buckets are produced by the deterministic classifiers in
:mod:`app.services.procurement_taxonomy`.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class CoverageBucket(BaseModel):
    key: str
    tenders: int = 0
    awards: int = 0
    companies: int = 0
    documents: int = 0
    total_value: Decimal = Decimal("0")
    share: float = 0.0


class CoverageDimension(BaseModel):
    dimension: str
    label: str
    distinct_buckets: int
    attributed_tenders: int
    unattributed_tenders: int
    coverage_ratio: float          # attributed / total tenders
    buckets: list[CoverageBucket]


class CoverageEngineReport(BaseModel):
    generated_at: str
    total_tenders: int
    total_awards: int
    total_companies: int
    total_documents: int
    dimensions: list[CoverageDimension]
