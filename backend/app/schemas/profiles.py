from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.graph import GraphResponse
from app.schemas.investigation_executor import (
    CanonicalCompany,
    InvestigationEntity,
    InvestigationEvidence,
    InvestigationGraphSeed,
    InvestigationProcurementIndicator,
    InvestigationTimelineEvent,
)


class SearchHit(BaseModel):
    type: str  # tender | company | buyer
    id: str
    label: str
    sublabel: str | None = None


class SearchResponse(BaseModel):
    query: str
    tenders: list[SearchHit] = Field(default_factory=list)
    companies: list[SearchHit] = Field(default_factory=list)
    buyers: list[SearchHit] = Field(default_factory=list)
    total: int = 0


class AutocompleteResponse(BaseModel):
    query: str
    suggestions: list[SearchHit] = Field(default_factory=list)


class ProfileOverview(BaseModel):
    kind: str  # tender | company | buyer
    id: str
    title: str
    subtitle: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


class RelatedTender(BaseModel):
    reference_number: str
    title: str
    procuring_entity: str | None = None
    published_date: date | None = None
    estimated_value: Decimal | None = None
    currency: str = "INR"
    source_name: str | None = None


class RelatedAward(BaseModel):
    tender_reference_number: str
    company_name: str
    award_value: Decimal | None = None
    currency: str = "INR"
    award_date: date | None = None


class RelatedDocument(BaseModel):
    title: str
    url: str | None = None
    document_type: str
    related_tender: str | None = None


class ProfileResponse(BaseModel):
    overview: ProfileOverview
    indicators: list[InvestigationProcurementIndicator] = Field(default_factory=list)
    timeline: list[InvestigationTimelineEvent] = Field(default_factory=list)
    evidence: list[InvestigationEvidence] = Field(default_factory=list)
    relationships: list[InvestigationGraphSeed] = Field(default_factory=list)
    related_tenders: list[RelatedTender] = Field(default_factory=list)
    related_awards: list[RelatedAward] = Field(default_factory=list)
    related_documents: list[RelatedDocument] = Field(default_factory=list)
    graph: GraphResponse
    canonical_companies: list[CanonicalCompany] = Field(default_factory=list)
    entities: list[InvestigationEntity] = Field(default_factory=list)
