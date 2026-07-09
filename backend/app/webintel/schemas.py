from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    source: str
    provider: str
    domain: str
    published_date: datetime | None = None


class CrawledPage(BaseModel):
    url: str
    title: str | None = None
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)
    source: str
    retrieved_at: datetime
    content_hash: str


class ExtractedEvidence(BaseModel):
    company_mentions: list[str] = Field(default_factory=list)
    organization_names: list[str] = Field(default_factory=list)
    government_entities: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)


class ProcurementEvidence(BaseModel):
    id: str
    web_evidence_id: str
    tender_id: str | None = None
    company_id: str | None = None
    award_id: str | None = None
    company_name: str | None = None
    normalized_company_name: str | None = None
    government_buyer: str | None = None
    tender_title: str | None = None
    contract_title: str | None = None
    contract_value: str | None = None
    currency: str | None = None
    tender_category: str | None = None
    procurement_sector: str | None = None
    country: str | None = None
    publication_date: str | None = None
    award_date: str | None = None
    contract_number: str | None = None
    tender_number: str | None = None
    organization: str | None = None
    people_mentioned: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    raw_signals: dict = Field(default_factory=dict)


class StoredPage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    url: str
    title: str | None
    source: str
    retrieved_at: datetime
    content_hash: str
    extraction: ExtractedEvidence
    procurement_evidence: ProcurementEvidence | None = None


class WebSearchResponse(BaseModel):
    search_results: list[SearchResult]
    downloaded_pages: int
    stored_pages: list[StoredPage]
    duplicates_skipped: int
    rejected_non_procurement: int = 0


class ProcurementEvidenceResponse(BaseModel):
    items: list[StoredPage]


# --------------------------------------------------------------------------- intelligence

class ProcurementIntelligenceItem(BaseModel):
    """One analyst-grade evidence item with full provenance and linkage.

    Every field the Procurement Intelligence Engine promises for a result lives
    here: the source, what kind of evidence it is, how confident we are, when it
    was published, its original URL, a ready-to-paste citation, a summary, and
    every entity/tender/contract/organization/investigation it relates to.
    """

    id: str
    # provenance
    source: str
    source_type: str
    evidence_type: str
    cluster: str
    confidence: float = Field(ge=0, le=1)
    confidence_tier: str
    publication_date: str | None = None
    url: str
    citation: str
    evidence_summary: str
    # linkage
    related_entities: list[str] = Field(default_factory=list)
    related_tenders: list[str] = Field(default_factory=list)
    related_contracts: list[str] = Field(default_factory=list)
    related_organizations: list[str] = Field(default_factory=list)
    related_investigations: list[str] = Field(default_factory=list)
    # audit trail for the classification
    matched_terms: list[str] = Field(default_factory=list)
    retrieved_at: datetime


class EvidenceCluster(BaseModel):
    """A group of evidence items under one of the seven investigation buckets."""

    cluster: str
    label: str
    count: int
    items: list[ProcurementIntelligenceItem] = Field(default_factory=list)


class ProcurementIntelligenceResponse(BaseModel):
    """Clustered, analyst-grade procurement intelligence for a subject."""

    query: str
    total_items: int
    clusters: list[EvidenceCluster] = Field(default_factory=list)
