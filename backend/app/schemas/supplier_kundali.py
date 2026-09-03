from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


DataAvailability = Literal["available", "insufficient_data", "not_indexed"]


class SupplierKundaliProfile(BaseModel):
    id: UUID
    name: str
    registration_number: str | None
    source_name: str | None
    source_record_id: str | None
    source_url: str | None
    retrieved_at: datetime | None


class SupplierKundaliMetric(BaseModel):
    label: str
    value: str
    detail: str | None = None
    availability: DataAvailability = "available"


class SupplierConcentration(BaseModel):
    dimension: str
    name: str
    count: int
    share: Decimal
    value: Decimal
    rank: int
    population_count: int


class SupplierValueBenchmark(BaseModel):
    sample_size: int
    minimum: Decimal | None
    p25: Decimal | None
    median: Decimal | None
    p75: Decimal | None
    maximum: Decimal | None
    currency: str | None
    method: str


class SupplierTimelinePoint(BaseModel):
    period: str
    awards: int
    value: Decimal


class SupplierSignal(BaseModel):
    type: str
    severity: Literal["low", "medium", "high", "informational"]
    title: str
    summary: str
    evidence: list[str]
    confidence: Literal["high", "moderate", "low", "unknown"]
    review_required: bool


class SupplierDataQuality(BaseModel):
    award_records: int
    tender_records: int
    sourced_records: int
    records_with_source_url: int
    records_with_retrieval_timestamp: int
    participation_status: DataAvailability
    bidder_level_status: DataAvailability
    debarment_status: DataAvailability
    notes: list[str]


class SupplierKundaliResponse(BaseModel):
    profile: SupplierKundaliProfile
    metrics: list[SupplierKundaliMetric]
    buyer_concentration: list[SupplierConcentration]
    category_concentration: list[SupplierConcentration]
    geography_concentration: list[SupplierConcentration]
    method_concentration: list[SupplierConcentration]
    value_benchmark: SupplierValueBenchmark
    timeline: list[SupplierTimelinePoint]
    buyer_relationships: list[dict[str, object]]
    repeat_winner: dict[str, object]
    signals: list[SupplierSignal]
    data_quality: SupplierDataQuality
    limitations: list[str]
    generated_at: datetime
