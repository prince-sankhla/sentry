"""Schemas for the deterministic Procurement Risk Engine V2.

SENTRY is an *oversight tool*, not a judge. The engine surfaces evidence-backed
**Procurement Integrity Indicators** for investigator review — it never declares
fraud, corruption, or collusion. Every indicator and pattern is deterministic,
reproducible, and fully explainable; the LLM later only narrates this structure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IndicatorSeverity = Literal["low", "medium", "high", "critical"]
OverallSeverity = Literal["low", "medium", "high", "critical", "insufficient"]
EvidenceStatus = Literal["verified", "probable", "unknown"]

REVIEW_NOTE = "Requires Investigator Review"
OVERSIGHT_DISCLAIMER = (
    "This is an oversight tool. It surfaces evidence-backed procurement integrity "
    "indicators for investigator review and does not allege fraud, corruption, or "
    "collusion. Every finding requires independent verification."
)


class RiskEvidenceRef(BaseModel):
    """A concrete pointer to the record/document/entity backing an indicator."""

    kind: str          # tender | award | document | entity | buyer | supplier
    reference: str     # tender reference / document title / entity name
    source: str = ""   # originating source_name
    detail: str = ""


class RiskIndicatorV2(BaseModel):
    """One deterministic, evidence-backed procurement integrity indicator."""

    id: str
    name: str
    category: str
    severity: IndicatorSeverity
    base_severity: IndicatorSeverity
    score: int = Field(ge=0, le=100)
    status: str = "triggered"
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0, le=1)
    reason: str
    required_evidence: list[str] = Field(default_factory=list)
    supporting_records: list[str] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    review_required: bool = True
    review_note: str = REVIEW_NOTE


class RiskPattern(BaseModel):
    """A named pattern produced by a deterministic combination of indicators.

    Risk classification is by explicit rule combinations, never arithmetic
    addition — e.g. "single_bidder + gst_overlap → Critical Pattern".
    """

    id: str
    name: str
    severity: IndicatorSeverity
    rule: str
    indicators: list[str] = Field(default_factory=list)
    reason: str = ""
    review_note: str = REVIEW_NOTE


class RiskExplainabilityNode(BaseModel):
    """The audit trail for a single indicator's score.

    indicator → rule triggered → evidence → source → context applied → final score.
    The LLM converts ONLY this into natural language; it never recomputes it.
    """

    indicator_id: str
    name: str
    base_severity: IndicatorSeverity
    base_score: int
    rule_triggered: str
    evidence: list[RiskEvidenceRef] = Field(default_factory=list)
    evidence_status: EvidenceStatus
    context_applied: list[str] = Field(default_factory=list)
    score_contribution: int
    final_severity: IndicatorSeverity
    reason: str = ""


class RiskConfidence(BaseModel):
    """Confidence in the assessment — independent of the risk score itself."""

    score: float = Field(ge=0, le=1)
    level: Literal["high", "moderate", "low", "very_low"]
    explanation: str = ""


class RiskAssessmentV2(BaseModel):
    """The complete deterministic risk assessment for an investigation package."""

    overall_severity: OverallSeverity
    overall_score: int = Field(ge=0, le=100)
    method: str = "deterministic_risk_engine_v2"
    indicators: list[RiskIndicatorV2] = Field(default_factory=list)
    patterns: list[RiskPattern] = Field(default_factory=list)
    explainability: list[RiskExplainabilityNode] = Field(default_factory=list)
    confidence: RiskConfidence | None = None
    summary: str = ""
    disclaimer: str = OVERSIGHT_DISCLAIMER
