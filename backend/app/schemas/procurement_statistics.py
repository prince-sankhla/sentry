"""Schemas for platform-wide procurement statistics.

Every field is a real aggregate computed from the imported database — no
placeholder or demo values. See :mod:`app.services.procurement_statistics`.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class BuyerRanking(BaseModel):
    rank: int
    buyer: str
    tenders: int
    awards: int
    total_value: Decimal
    distinct_suppliers: int
    top_supplier: str | None = None
    top_supplier_share: float = 0.0


class SupplierRanking(BaseModel):
    rank: int
    company_id: UUID
    name: str
    awards: int
    total_value: Decimal
    distinct_buyers: int


class ConcentrationMetrics(BaseModel):
    """Award concentration across the whole dataset."""

    total_awards: int
    total_value: Decimal
    top_supplier_share: float          # share of value held by the single top supplier
    top5_supplier_share: float         # share of value held by the top 5 suppliers
    hhi: float                         # Herfindahl-Hirschman Index over supplier value (0-1)
    interpretation: str


class SupplierDiversity(BaseModel):
    distinct_suppliers: int
    distinct_buyers: int
    suppliers_per_buyer: float
    single_buyer_suppliers: int        # suppliers dependent on exactly one buyer
    single_supplier_buyers: int        # buyers relying on exactly one supplier


class CompetitionMetrics(BaseModel):
    total_tenders: int
    tenders_with_awards: int
    single_bidder_tenders: int
    single_bidder_rate: float
    multi_bidder_tenders: int
    average_bidders_per_tender: float
    tender_success_rate: float         # closed tenders that resulted in an award


class TrendPoint(BaseModel):
    period: str                        # YYYY-MM
    tenders: int
    awards: int
    value: Decimal


class CategoryTrend(BaseModel):
    category: str
    tenders: int
    value: Decimal


class StateTrend(BaseModel):
    state: str
    tenders: int
    awards: int
    value: Decimal


class SourceCoverage(BaseModel):
    source_name: str
    label: str
    tenders: int
    is_indian: bool
    priority_rank: int


class ProcurementStatistics(BaseModel):
    top_buyers: list[BuyerRanking]
    top_suppliers: list[SupplierRanking]
    award_concentration: ConcentrationMetrics
    supplier_diversity: SupplierDiversity
    competition: CompetitionMetrics
    procurement_trends: list[TrendPoint]
    category_trends: list[CategoryTrend]
    state_trends: list[StateTrend]
    source_coverage: list[SourceCoverage]
