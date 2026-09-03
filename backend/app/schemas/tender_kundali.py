from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class KundaliSourceSnapshot(BaseModel):
    source_name: str
    source_record_id: str
    source_url: str | None
    content_hash: str | None
    retrieved_at: datetime | None
    action: str | None


class KundaliDocument(BaseModel):
    id: str
    title: str
    document_type: str
    url: str | None
    retrieved_at: datetime | None
    content_hash: str | None
    evidence_hash: str | None
    available: bool


class KundaliAward(BaseModel):
    id: str
    supplier_id: str
    supplier_name: str
    award_date: date | None
    award_value: Decimal | None
    currency: str
    source_name: str | None
    source_url: str | None


class KundaliComparableTender(BaseModel):
    id: str
    reference_number: str
    title: str
    buyer: str | None
    category: str | None
    procurement_method: str | None
    published_date: date | None
    estimated_value: Decimal | None
    currency: str
    similarity_reasons: list[str] = Field(default_factory=list)
    award_supplier: str | None
    award_value: Decimal | None


class KundaliBenchmark(BaseModel):
    sample_size: int
    median: Decimal | None
    p25: Decimal | None
    p75: Decimal | None
    min_value: Decimal | None
    max_value: Decimal | None
    tender_percentile: float | None
    position: str
    basis: list[str] = Field(default_factory=list)


class KundaliSupplierHistory(BaseModel):
    supplier_id: str
    supplier_name: str
    award_count: int
    total_award_value: Decimal
    buyer_count: int
    buyer_names: list[str] = Field(default_factory=list)
    first_award_date: date | None
    latest_award_date: date | None
    tender_references: list[str] = Field(default_factory=list)


class KundaliSignal(BaseModel):
    type: str
    severity: str
    title: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    supported_by: list[str] = Field(default_factory=list)
    review_required: bool = True


class TenderKundaliResponse(BaseModel):
    tender_id: str
    reference_number: str
    title: str
    status: str
    as_of: datetime | None
    buyer: str | None
    procurement_method: str | None
    category: str | None
    geography: str | None
    estimated_value: Decimal | None
    currency: str
    published_date: date | None
    closing_date: date | None
    source: KundaliSourceSnapshot
    documents: list[KundaliDocument]
    document_summary: dict[str, int]
    awards: list[KundaliAward]
    comparable_tenders: list[KundaliComparableTender]
    benchmark: KundaliBenchmark
    supplier_history: list[KundaliSupplierHistory]
    signals: list[KundaliSignal]
    evidence_summary: dict[str, int]
    limitations: list[str] = Field(default_factory=list)
