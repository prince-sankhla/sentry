"""Schemas for PDF / tender-document intelligence.

Structured extraction is deterministic and grounded: every extracted field keeps
the exact source span it came from and a confidence, so nothing is asserted that
is not literally present in the document text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    """A single structured value pulled from a document, with provenance."""

    name: str
    value: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    # The literal text span the value was extracted from — the proof.
    source_span: str
    method: str = "regex"


class TenderDocumentExtraction(BaseModel):
    """Structured intelligence extracted from a tender document."""

    tender_reference: ExtractedField | None = None
    title: ExtractedField | None = None
    procuring_entity: ExtractedField | None = None
    department: ExtractedField | None = None
    buyer: ExtractedField | None = None
    estimated_value: ExtractedField | None = None
    estimated_cost: ExtractedField | None = None
    emd_amount: ExtractedField | None = None
    tender_fee: ExtractedField | None = None
    bid_submission_end: ExtractedField | None = None
    bid_opening_date: ExtractedField | None = None
    publication_date: ExtractedField | None = None
    category: ExtractedField | None = None
    location: ExtractedField | None = None
    boq_reference: ExtractedField | None = None
    eligibility: ExtractedField | None = None
    awarded_to: ExtractedField | None = None
    award_value: ExtractedField | None = None
    bidders_count: ExtractedField | None = None

    # Every field found, for enumeration/ranking.
    fields: list[ExtractedField] = Field(default_factory=list)
    # Extraction coverage 0..1 (fields found / fields attempted).
    coverage: float = Field(default=0.0, ge=0, le=1)
    # True when the text yielded no structured procurement signal at all.
    empty: bool = True
    char_count: int = 0
