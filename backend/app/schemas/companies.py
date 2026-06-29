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
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    items: list[CompanySummary]
    pagination: Pagination


class RelatedTender(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    title: str
    procuring_entity: str | None
    published_date: date | None
    estimated_value: Decimal | None
    currency: str


class CompanyAward(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    award_date: date | None
    award_value: Decimal | None
    currency: str
    tender: RelatedTender


class CompanyDetail(CompanySummary):
    related_tenders: list[RelatedTender]
    awards_won: list[CompanyAward]


class CompanyProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime


class CompanyOverview(BaseModel):
    company: CompanyProfile
    registration_identifier: str | None
    address: str | None
    total_tenders: int
    total_awards_won: int
    total_procurement_value: Decimal
    average_award_value: Decimal
    first_procurement_date: date | None
    latest_procurement_date: date | None


class CompanyTenderHistoryItem(BaseModel):
    id: UUID
    reference_number: str
    title: str
    tender_value: Decimal | None
    currency: str
    publication_date: date | None
    procurement_status: str | None
    buyer: str | None
    award_amount: Decimal | None
    award_date: date | None


class CompanyTenderHistoryResponse(BaseModel):
    items: list[CompanyTenderHistoryItem]
    pagination: Pagination


class CompanyAwardHistoryItem(BaseModel):
    id: UUID
    award_amount: Decimal | None
    award_date: date | None
    currency: str
    tender_id: UUID
    tender_title: str
    tender_reference_number: str


class CompanyAwardHistoryResponse(BaseModel):
    items: list[CompanyAwardHistoryItem]
    pagination: Pagination
