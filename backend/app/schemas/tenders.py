from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Pagination


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None


class AwardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    award_date: date | None
    award_value: Decimal | None
    currency: str
    company: CompanySummary


class TenderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    title: str
    procuring_entity: str | None
    published_date: date | None
    closing_date: date | None
    estimated_value: Decimal | None
    currency: str
    created_at: datetime
    updated_at: datetime


class TenderListResponse(BaseModel):
    items: list[TenderSummary]
    pagination: Pagination


class BuyerInfo(BaseModel):
    name: str | None


class TenderDetail(TenderSummary):
    description: str | None
    buyer: BuyerInfo
    awards: list[AwardSummary]
    participating_companies: list[CompanySummary]
