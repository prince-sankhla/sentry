from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Pagination

Severity = Literal["low", "medium", "high"]


# --- /awards ---------------------------------------------------------------


class AwardCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None = None


class AwardTender(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    title: str
    procuring_entity: str | None = None


class AwardItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    award_value: Decimal | None = None
    currency: str
    award_date: date | None = None
    company: AwardCompany
    tender: AwardTender


class AwardStats(BaseModel):
    total_awards: int
    total_value: Decimal
    average_value: Decimal
    awarded_suppliers: int
    awarding_buyers: int


class AwardsResponse(BaseModel):
    items: list[AwardItem]
    pagination: Pagination
    stats: AwardStats


# --- /overview -------------------------------------------------------------


class OverviewTotals(BaseModel):
    tenders: int
    companies: int
    awards: int
    total_tender_value: Decimal
    total_awarded_value: Decimal
    average_tender_value: Decimal
    single_bidder_tenders: int
    buyers: int


class TopBuyer(BaseModel):
    buyer: str
    tenders: int
    awards: int
    total_value: Decimal


class TopSupplier(BaseModel):
    company_id: UUID
    name: str
    awards: int
    total_value: Decimal


class MonthlyPoint(BaseModel):
    month: str
    tenders: int
    value: Decimal


class SourceCount(BaseModel):
    source_name: str
    tenders: int


class OverviewResponse(BaseModel):
    totals: OverviewTotals
    top_buyers: list[TopBuyer]
    top_suppliers: list[TopSupplier]
    monthly: list[MonthlyPoint]
    sources: list[SourceCount]


# --- /risk -----------------------------------------------------------------


class RiskSignal(BaseModel):
    type: str
    severity: Severity
    title: str
    summary: str
    score: int
    buyer: str | None = None
    supplier_name: str | None = None
    supplier_id: UUID | None = None
    tender_id: UUID | None = None
    tender_reference: str | None = None
    evidence: list[str] = []


class RiskSummary(BaseModel):
    total: int
    high: int
    medium: int
    low: int
    single_bidder_tenders: int
    flagged_relationships: int


class PortfolioRisk(BaseModel):
    summary: RiskSummary
    signals: list[RiskSignal]


# --- /timeline -------------------------------------------------------------


class TimelineEvent(BaseModel):
    date: date | datetime
    kind: Literal["tender_published", "tender_closing", "award"]
    title: str
    subtitle: str | None = None
    reference: str | None = None
    entity_type: Literal["tender", "company"]
    entity_id: UUID | None = None


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]


# --- /geography ------------------------------------------------------------


class Region(BaseModel):
    region: str
    tenders: int
    value: Decimal
    awards: int


class GeographyResponse(BaseModel):
    regions: list[Region]
    matched: int
    unmatched: int
    total: int
