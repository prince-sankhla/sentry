from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Pagination
from app.schemas.pdf_intelligence import TenderDocumentExtraction
from app.schemas.procurement_intelligence import ProcurementIntelligence


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
    intelligence: ProcurementIntelligence
    # Deterministic, provenanced structured extraction from the tender document
    # text (see services/pdf_intelligence.py). ``None`` / ``empty`` when the
    # stored text yielded no structured procurement signal.
    pdf_intelligence: TenderDocumentExtraction | None = None
