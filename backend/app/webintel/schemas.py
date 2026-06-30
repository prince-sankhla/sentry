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


class ProcurementEvidenceResponse(BaseModel):
    items: list[StoredPage]
