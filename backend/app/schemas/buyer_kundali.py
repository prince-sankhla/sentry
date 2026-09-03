from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BuyerProfile(BaseModel):
    name: str
    normalized_name: str
    tender_count: int
    awarded_tender_count: int
    first_tender_date: str | None
    latest_tender_date: str | None


class BuyerDistributionRow(BaseModel):
    dimension: str
    name: str
    count: int
    share: Decimal
    value: Decimal
    rank: int
    population_count: int


class BuyerSupplierRow(BaseModel):
    supplier_id: str
    supplier_name: str
    award_count: int
    award_share: Decimal
    award_value: Decimal
    latest_award_date: str | None


class BuyerValueBenchmark(BaseModel):
    sample_size: int
    minimum: Decimal | None
    p25: Decimal | None
    median: Decimal | None
    p75: Decimal | None
    maximum: Decimal | None
    currency: str | None
    method: str


class BuyerSubmissionWindow(BaseModel):
    sample_size: int
    minimum_days: float | None
    median_days: float | None
    p75_days: float | None
    maximum_days: float | None
    unknown_count: int


class BuyerTimelinePoint(BaseModel):
    period: str
    tenders: int
    awards: int
    tender_value: Decimal
    award_value: Decimal


class BuyerSignal(BaseModel):
    type: str
    severity: str
    title: str
    summary: str
    evidence: list[str]
    confidence: str
    review_required: bool


class BuyerDataQuality(BaseModel):
    tender_records: int
    awarded_tenders: int
    records_with_method: int
    records_with_category: int
    records_with_geography: int
    records_with_deadline: int
    records_with_award_value: int
    records_with_source_url: int
    bidder_level_status: str
    cancellation_status: str
    corrigendum_status: str
    notes: list[str]


class BuyerKundaliResponse(BaseModel):
    profile: BuyerProfile
    metrics: list[dict[str, str]]
    supplier_concentration: list[BuyerDistributionRow]
    category_distribution: list[BuyerDistributionRow]
    geography_distribution: list[BuyerDistributionRow]
    method_distribution: list[BuyerDistributionRow]
    supplier_relationships: list[BuyerSupplierRow]
    value_benchmark: BuyerValueBenchmark
    submission_window: BuyerSubmissionWindow
    timeline: list[BuyerTimelinePoint]
    award_estimate_distribution: BuyerDistributionRow | None
    signals: list[BuyerSignal]
    data_quality: BuyerDataQuality
    limitations: list[str]
    generated_at: datetime
