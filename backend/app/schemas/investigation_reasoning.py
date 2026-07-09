"""Schemas for the AI reasoning layer of the investigation engine.

The reasoning layer never introduces new procurement facts. Every field here is
derived from an ``InvestigationPackage`` (records, indicators, entities, evidence)
and each conclusion carries citations back to the source records that produced it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.investigation_memory import MemoryHit

RiskLevel = Literal["low", "medium", "high", "critical", "insufficient"]


class ReasoningCitation(BaseModel):
    """A pointer from an AI conclusion back to verifiable procurement evidence.

    Carries full provenance so a conclusion can always be independently verified:
    the original source, its URL, an attached document/PDF if one exists, the time
    the record was retrieved, a confidence read-out, and a ready-to-paste citation
    string. The Evidence Engine (``services/investigation_evidence.py``) is the
    single builder of these — findings are never asserted without one.
    """

    label: str
    source_name: str
    source_record_id: str | None = None
    source_url: str | None = None
    # Attached original document / tender PDF, when the source exposes one.
    document_url: str | None = None
    document_type: str | None = None
    # Provenance timing + dates.
    retrieved_at: datetime | None = None
    published_date: str | None = None
    # 0..1 confidence that this evidence supports the conclusion it is cited for.
    confidence: float = Field(default=0.0, ge=0, le=1)
    related_tender: str | None = None
    related_entity: str | None = None
    evidence_type: str = "procurement_record"
    # Analyst-grade, ready-to-paste citation string.
    citation: str = ""
    # Evidence quality (0-100) and human tier, ranked by the Evidence Engine on
    # source authority, verifiability (URL/document), recency, and completeness.
    quality: int = Field(default=0, ge=0, le=100)
    quality_tier: Literal["primary", "corroborating", "weak", "unverified"] = "unverified"


class ReasoningFinding(BaseModel):
    """A single grounded conclusion with its supporting citations.

    ``evidence_backed`` is ``False`` only when no source citation could be
    resolved for the finding; such findings are surfaced as unverified rather
    than presented as fact.
    """

    title: str
    detail: str
    severity: Literal["low", "medium", "high"] = "medium"
    score: int = Field(default=0, ge=0, le=100)
    citations: list[ReasoningCitation] = Field(default_factory=list)
    evidence_backed: bool = True
    # Grouping: identical finding types are collapsed into one finding. These
    # fields expose the group so the UI can show "Abnormal Contract Values — 12
    # supporting records" and expand to the individual instances. All additive.
    indicator_type: str = ""
    occurrences: int = 1
    supporting_records: list[str] = Field(default_factory=list)
    instances: list[str] = Field(default_factory=list)


class FollowUpSuggestion(BaseModel):
    """A suggested next investigation the analyst can launch with one click."""

    label: str
    query: str
    rationale: str


class AnalystStep(BaseModel):
    """One step of the multi-step analyst trace.

    Each step names the read-only tool it ran over the InvestigationPackage, the
    input it ran with, the grounded observation it produced, and the citations
    backing that observation — so the reasoning path is fully auditable.
    """

    order: int
    tool: str
    input: str = ""
    observation: str
    citations: list[ReasoningCitation] = Field(default_factory=list)


class GroundingReport(BaseModel):
    """Audit of how well the narrative is anchored to verifiable evidence.

    Lets the UI prove — not merely assert — that the AI reasoned only over the
    InvestigationPackage: how many findings carry citations, the total evidence
    items referenced, and whether the whole narrative is fully grounded.
    """

    total_findings: int = 0
    evidence_backed_findings: int = 0
    total_citations: int = 0
    records_reviewed: int = 0
    documents_available: int = 0
    fully_grounded: bool = True


class RiskFactor(BaseModel):
    """One weighted contributor to the Procurement Integrity Assessment.

    Risk is NOT an indicator count — it is a weighted blend of distinct integrity
    factors. Each factor states its normalized strength (0-1), the weight it
    carries, the points it contributed, and a plain-language explanation, so the
    overall score is fully auditable.
    """

    key: str
    label: str
    weight: float = Field(ge=0, le=1)
    strength: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0)
    detail: str
    supporting_indicator_types: list[str] = Field(default_factory=list)


class IntegrityAssessment(BaseModel):
    """Weighted, explainable procurement integrity assessment.

    ``score`` (0-100) is the sum of factor contributions, not a raw indicator
    tally; ``level`` is banded from the score; ``factors`` lists every
    contributor with its weight and reasoning; ``method`` documents the model.
    """

    score: int = Field(ge=0, le=100)
    level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    factors: list[RiskFactor] = Field(default_factory=list)
    summary: str = ""
    method: str = "weighted_procurement_integrity_assessment_v1"


class ConfidenceDimension(BaseModel):
    """One measurable input to the overall confidence assessment (0-1)."""

    key: str
    label: str
    score: float = Field(ge=0, le=1)
    detail: str


class ConfidenceAssessment(BaseModel):
    """Confidence derived from measurable investigation quality — never a bare number.

    Each dimension (evidence coverage, source reliability, corroboration,
    document availability, entity-resolution quality, award completeness, timeline
    completeness, cross-source consistency) is scored 0-1 and explained; the
    overall score is their weighted blend and ``explanation`` states WHY.
    """

    score: float = Field(ge=0, le=1)
    level: Literal["high", "moderate", "low", "very_low"]
    dimensions: list[ConfidenceDimension] = Field(default_factory=list)
    explanation: str = ""


class Contradiction(BaseModel):
    """A deterministically-detected inconsistency in the procurement evidence."""

    type: str  # date_inconsistency | missing_award | value_inconsistency | duplicate_contract | conflicting_supplier | award_without_company | conflicting_value
    severity: Literal["low", "medium", "high"] = "medium"
    summary: str
    detail: str = ""
    related_tenders: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)


class BuyerInsight(BaseModel):
    name: str
    tender_count: int = 0
    award_count: int = 0
    total_award_value: str | None = None
    currency: str | None = None
    top_suppliers: list[str] = Field(default_factory=list)
    concentration_pct: int | None = None
    note: str = ""


class SupplierInsight(BaseModel):
    name: str
    award_count: int = 0
    total_award_value: str | None = None
    currency: str | None = None
    buyers: list[str] = Field(default_factory=list)
    single_buyer_dependence: bool = False
    note: str = ""


class AwardAnalysis(BaseModel):
    total_awards: int = 0
    valued_awards: int = 0
    total_value: str | None = None
    currency: str | None = None
    largest_award_value: str | None = None
    largest_award_supplier: str | None = None
    largest_award_tender: str | None = None
    note: str = ""


class TimelineAnalysis(BaseModel):
    event_count: int = 0
    first_event: str | None = None
    last_event: str | None = None
    span_days: int | None = None
    fast_awards: int = 0
    note: str = ""


class ProcurementPattern(BaseModel):
    pattern: str
    detail: str = ""
    supporting_tenders: list[str] = Field(default_factory=list)


class AnalystReport(BaseModel):
    """Grounded, structured analyst-report sections computed from the package.

    Every section is a deterministic projection of the InvestigationPackage — no
    invented entities, values, or relationships. The LLM narrates the executive
    summary from these facts; the backend proves them.
    """

    procurement_patterns: list[ProcurementPattern] = Field(default_factory=list)
    buyer_analysis: list[BuyerInsight] = Field(default_factory=list)
    supplier_analysis: list[SupplierInsight] = Field(default_factory=list)
    award_analysis: AwardAnalysis | None = None
    timeline_analysis: TimelineAnalysis | None = None
    contradictions: list[Contradiction] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence_assessment: ConfidenceAssessment | None = None


class InvestigationReasoning(BaseModel):
    """The complete AI reasoning output for an investigation.

    ``generated_by`` records whether a live model or the deterministic composer
    produced the narrative; ``provider``/``model`` attribute which LLM answered.
    The UI is always transparent about provenance.
    """

    subject: str
    investigation_type: str
    generated_by: Literal["llm", "deterministic"] = "deterministic"
    provider: str | None = None
    model: str | None = None
    # When the narrative fell back to the deterministic composer, why: no provider
    # configured, every provider errored/refused, or the model's phrasing failed
    # the grounding guard. ``None`` when a live provider authored the summary.
    fallback_reason: Literal["no_provider", "provider_error", "grounding_guard"] | None = None

    executive_summary: str
    risk_level: RiskLevel
    risk_rationale: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)

    findings: list[ReasoningFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    follow_ups: list[FollowUpSuggestion] = Field(default_factory=list)

    # Every piece of evidence referenced across the investigation, de-duplicated,
    # each with full provenance — the analyst's citation trail.
    evidence_ledger: list[ReasoningCitation] = Field(default_factory=list)
    grounding: GroundingReport = Field(default_factory=GroundingReport)

    # Multi-step, tool-driven reasoning trace over the package (auditable).
    analyst_trace: list[AnalystStep] = Field(default_factory=list)
    # Prior related investigations recalled from cross-investigation memory.
    prior_investigations: list[MemoryHit] = Field(default_factory=list)

    # Weighted, explainable procurement integrity assessment behind risk_level.
    integrity_assessment: IntegrityAssessment | None = None

    # Structured, grounded analyst-report sections (patterns, buyer/supplier/award/
    # timeline analysis, contradictions, missing evidence, derived confidence).
    analyst_report: AnalystReport | None = None

    # True when there was not enough evidence to reach a conclusion.
    insufficient_evidence: bool = False
