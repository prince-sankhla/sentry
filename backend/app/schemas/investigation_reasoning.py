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

    # True when there was not enough evidence to reach a conclusion.
    insufficient_evidence: bool = False
