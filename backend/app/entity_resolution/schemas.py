from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class LinkedSource(BaseModel):
    source_type: str
    source_id: str
    alias: str
    confidence: Decimal
    match_reason: str


class LinkedProcurementCompany(BaseModel):
    id: UUID
    name: str
    registration_number: str | None
    source_name: str | None
    source_record_id: str | None


class LinkedTender(BaseModel):
    id: UUID
    reference_number: str
    title: str
    procuring_entity: str | None
    published_date: date | None
    estimated_value: Decimal | None
    currency: str


class LinkedAward(BaseModel):
    id: UUID
    tender_id: UUID
    company_id: UUID
    award_date: date | None
    award_value: Decimal | None
    currency: str


class LinkedWebEvidence(BaseModel):
    id: UUID
    url: str
    title: str | None
    source: str
    retrieved_at: datetime
    company_name: str | None
    tender_id: UUID | None
    award_id: UUID | None


class CanonicalCompanyResponse(BaseModel):
    id: UUID
    canonical_name: str
    aliases: list[str]
    matched_sources: list[LinkedSource]
    confidence: Decimal
    linked_company_ids: list[UUID]
    linked_procurement_companies: list[LinkedProcurementCompany]
    linked_web_evidence: list[LinkedWebEvidence]
    linked_tenders: list[LinkedTender]
    linked_awards: list[LinkedAward]
