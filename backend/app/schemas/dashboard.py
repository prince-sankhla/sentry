from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    total_tenders: int
    total_companies: int
    total_awards: int
    total_procurement_value: Decimal
    average_tender_value: Decimal
    latest_import_date: datetime | None


class DashboardTender(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    title: str
    procuring_entity: str | None
    published_date: date | None
    estimated_value: Decimal | None
    currency: str
    created_at: datetime


class DashboardCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None
    created_at: datetime


class DashboardAwardCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None


class DashboardAwardTender(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    title: str


class DashboardAward(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    award_date: date | None
    award_value: Decimal | None
    currency: str
    created_at: datetime
    company: DashboardAwardCompany
    tender: DashboardAwardTender


class DashboardRecent(BaseModel):
    latest_tenders: list[DashboardTender]
    latest_awarded_companies: list[DashboardCompany]
    latest_awards: list[DashboardAward]
