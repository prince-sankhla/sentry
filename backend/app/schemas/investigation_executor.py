from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.investigation_planner import InvestigationPlan


class InvestigationExecutionRequest(BaseModel):
    plan: InvestigationPlan
    limit_per_connector: int = Field(default=25, ge=1, le=100)
    package: InvestigationPackage | None = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class InvestigationSourceMetadata(BaseModel):
    source_name: str
    source_record_id: str
    source_url: str | None
    retrieved_at: datetime | None


class InvestigationTenderResult(BaseModel):
    reference_number: str
    title: str
    description: str | None
    procuring_entity: str | None
    published_date: date | None
    closing_date: date | None
    estimated_value: Decimal | None
    currency: str
    metadata: InvestigationSourceMetadata


class InvestigationCompanyResult(BaseModel):
    name: str
    registration_number: str | None
    tax_id: str | None = None
    company_identifier: str | None = None
    address: str | None = None
    website: str | None = None
    canonical_company_id: str | None = None
    metadata: InvestigationSourceMetadata


class InvestigationAwardResult(BaseModel):
    tender_reference_number: str
    company_name: str
    company_registration_number: str | None
    company_tax_id: str | None = None
    company_identifier: str | None = None
    company_address: str | None = None
    company_website: str | None = None
    canonical_company_id: str | None = None
    award_date: date | None
    award_value: Decimal | None
    currency: str
    metadata: InvestigationSourceMetadata


class InvestigationDocumentResult(BaseModel):
    title: str
    url: str | None
    document_type: str
    metadata: InvestigationSourceMetadata


class InvestigationProcurementRecord(BaseModel):
    tender: InvestigationTenderResult
    companies: list[InvestigationCompanyResult] = Field(default_factory=list)
    awards: list[InvestigationAwardResult] = Field(default_factory=list)
    documents: list[InvestigationDocumentResult] = Field(default_factory=list)
    canonical_company_ids: list[str] = Field(default_factory=list)


class CanonicalCompanyMatchedSource(BaseModel):
    source_type: str
    source_id: str
    source_name: str
    source_record_id: str
    alias: str
    confidence: float
    match_reason: str
    tender_reference_number: str | None = None


class CanonicalCompany(BaseModel):
    id: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    matched_sources: list[CanonicalCompanyMatchedSource] = Field(default_factory=list)
    matched_procurement_records: list[str] = Field(default_factory=list)


class InvestigationEntity(BaseModel):
    name: str
    entity_type: str
    registration_number: str | None = None
    source_record_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class InvestigationEvidence(BaseModel):
    evidence_type: str
    title: str
    source_name: str
    source_record_id: str
    source_url: str | None = None
    related_tender: str | None = None
    related_entity: str | None = None


class InvestigationTimelineEvent(BaseModel):
    label: str
    event_date: date | datetime
    source_name: str
    source_record_id: str
    related_tender: str | None = None
    related_entity: str | None = None


class InvestigationGraphSeed(BaseModel):
    source: str
    target: str
    relationship: str
    source_name: str
    source_record_id: str


class InvestigationStepResult(BaseModel):
    order: int
    module: str
    action: str
    connectors: list[str] = Field(default_factory=list)
    records_added: int = 0
    entities_added: int = 0
    evidence_added: int = 0
    status: str = "completed"


class InvestigationPackage(BaseModel):
    plan: InvestigationPlan
    records: list[InvestigationProcurementRecord] = Field(default_factory=list)
    canonical_companies: list[CanonicalCompany] = Field(default_factory=list)
    entities: list[InvestigationEntity] = Field(default_factory=list)
    evidence: list[InvestigationEvidence] = Field(default_factory=list)
    timeline: list[InvestigationTimelineEvent] = Field(default_factory=list)
    graph_seeds: list[InvestigationGraphSeed] = Field(default_factory=list)
    step_results: list[InvestigationStepResult] = Field(default_factory=list)

    class Config:
        from_attributes = True
