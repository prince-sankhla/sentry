"""Phase 3 — Procurement Context Analyzer.

The final runtime layer of the Verified Context Engine:

    Deterministic Finding → Verified Context Engine (local → trusted retrieval)
                          → relevant guidance selected for THAT finding
                          → organized into fixed presentation sections
                          → Investigator Workspace

Strictly read-only and strictly organizational:
  * it consumes guidance exactly as Phase 1/2 return it — authority names,
    document references, and citations pass through verbatim;
  * it selects only guidance whose declared applicability covers the finding;
  * it renders NO opinions and NO conclusions — the Current Assessment is a
    fixed, neutral statement, and when nothing relevant is found the analyzer
    says so with the fixed no-guidance message instead of fabricating context;
  * nothing is cached, saved, learned, or scored — every call re-resolves.

It never touches the investigation: findings, severities, indicators, scores,
the Evidence Challenge, and the Investigator Review are read, never written.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from app.verified_context.applicability import (
    APPLICABILITY_LABELS,
    Applicability,
    ContextFacts,
    evaluate_card,
)
from app.verified_context.engine import VerifiedContextEngine
from app.verified_context.schema import ContextCard, ContextQuery
from app.verified_context.trusted import build_default_engine

# Fixed presentation language — organizational framing only, never knowledge.
NO_GUIDANCE_MESSAGE = (
    "No relevant procurement guidance was identified from the consulted authorities."
)

APPLICABILITY_NOT_ESTABLISHED_MESSAGE = (
    "Procurement guidance exists for this finding type, but its applicability could "
    "not be established from the available evidence."
)

ASSESSMENT_WITH_GUIDANCE = (
    "The available procurement guidance provides a plausible administrative explanation "
    "for the observed procurement pattern. It does not, by itself, confirm or exclude "
    "the finding — the additional evidence below is required to distinguish routine "
    "procurement from procurement requiring escalation."
)

# Deterministic classification of allowlisted authorities → source type label.
_SOURCE_TYPE_BY_AUTHORITY_KEY: dict[str, str] = {
    "gfr": "Government Procurement Rule",
    "cvc": "Vigilance Guidance",
    "cag": "Audit Authority Guidance",
    "ocp": "Open Contracting Guidance",
    "worldbank": "Multilateral Procurement Framework",
    "oecd": "International Procurement Guidance",
    "adb": "Multilateral Procurement Framework",
}


class _FindingLike(Protocol):
    """The minimal shape of a deterministic finding the analyzer accepts."""

    id: str
    name: str


class GuidanceItem(BaseModel):
    """One piece of relevant guidance, organized for presentation.

    Every field is carried over from the resolved Context Card — authority,
    document reference, and citations preserved verbatim.
    """

    supporting_guidance: str                       # the guidance text, as retrieved
    supporting_sources: list[str]                  # publisher names, verbatim
    source_type: str                               # deterministic authority classification
    authority: str                                 # publishing authority, verbatim
    reference: str                                 # document reference, verbatim
    source_urls: list[str] = Field(default_factory=list)
    applicability: str                             # declared scope, restated
    card_status: str                               # "verified" | "draft" — provenance honesty
    # Deterministic applicability classification against the retrieved facts.
    applicability_status: str = ""                 # display label (fixed vocabulary)
    applicability_evidence: str = ""               # the fact backing "directly supported"


class ProcurementContextAnalysis(BaseModel):
    """The analyzer's full output for one finding — fixed sections, no verdicts."""

    finding_id: str
    finding_name: str
    guidance_available: bool
    potential_context: str                         # neutral framing or the no-guidance message
    guidance: list[GuidanceItem] = Field(default_factory=list)
    current_assessment: str
    additional_evidence_required: list[str] = Field(default_factory=list)
    resolved_by: str = ""                          # which provider answered (provenance)
    # Neutral notes for guidance that was retrieved but NOT shown because its
    # applicability could not be established from the retrieved facts.
    applicability_notes: list[str] = Field(default_factory=list)


class ProcurementContextAnalyzer:
    """Retrieve → select → organize → present. Nothing else."""

    def __init__(self, engine: VerifiedContextEngine | None = None) -> None:
        # No caching: the engine re-resolves on every call; the analyzer holds
        # no state beyond its (stateless) engine reference.
        self.engine = engine or build_default_engine()

    def analyze(
        self,
        finding: _FindingLike,
        *,
        facts: ContextFacts | None = None,
        jurisdiction: str = "",
    ) -> ProcurementContextAnalysis:
        """Organize the trusted guidance relevant to one deterministic finding.

        When ``facts`` are provided, every candidate card must first pass an
        applicability evaluation against them (evidence-driven, not
        template-driven): supported/procedural guidance is shown with its
        classification; guidance whose premise the facts cannot establish — or
        contradict — is withheld with a neutral note. Without facts, guidance
        is shown but honestly labeled as not establishable from evidence.
        """
        resolution = self.engine.resolve(
            ContextQuery(indicator_id=finding.id, jurisdiction=jurisdiction)
        )

        # Select ONLY guidance whose declared applicability covers this finding
        # (defence in depth — providers already filter on the same contract).
        relevant = [c for c in resolution.cards if finding.id in c.applies_to_indicators]

        if not resolution.available or not relevant:
            return ProcurementContextAnalysis(
                finding_id=finding.id,
                finding_name=finding.name,
                guidance_available=False,
                potential_context=NO_GUIDANCE_MESSAGE,
                current_assessment=NO_GUIDANCE_MESSAGE,
                resolved_by=resolution.provider,
            )

        # ---- applicability evaluation (evidence-driven gating) -------------
        shown: list[tuple[Applicability, ContextCard, str]] = []
        notes: list[str] = []
        if facts is not None:
            for card in relevant:
                evaluation = evaluate_card(card.card_id, facts)
                if evaluation.status in (Applicability.SUPPORTED, Applicability.POTENTIAL):
                    shown.append((evaluation.status, card, evaluation.evidence))
                else:
                    # Neutral, identical phrasing for indeterminate AND
                    # contradicted — the analyzer never manufactures a conflict
                    # between the evidence and authority guidance.
                    notes.append(
                        f"Applicability of “{card.title}” could not be established "
                        "from the available evidence."
                    )
            # Most relevant first: directly-supported guidance before procedural.
            order = {Applicability.SUPPORTED: 0, Applicability.POTENTIAL: 1}
            shown.sort(key=lambda entry: (order[entry[0]], entry[1].card_id))
        else:
            # No facts supplied: nothing can be evaluated — shown, honestly labeled.
            shown = [(Applicability.INDETERMINATE, card, "") for card in relevant]

        if not shown:
            return ProcurementContextAnalysis(
                finding_id=finding.id,
                finding_name=finding.name,
                guidance_available=False,
                potential_context=APPLICABILITY_NOT_ESTABLISHED_MESSAGE,
                current_assessment=APPLICABILITY_NOT_ESTABLISHED_MESSAGE,
                applicability_notes=notes,
                resolved_by=resolution.provider,
            )

        questions: list[str] = []
        for _, card, _ in shown:
            for q in card.verification_questions:
                if q not in questions:
                    questions.append(q)

        return ProcurementContextAnalysis(
            finding_id=finding.id,
            finding_name=finding.name,
            guidance_available=True,
            potential_context=(
                f"The finding “{finding.name}” may have a legitimate administrative "
                "explanation under the procurement guidance below."
            ),
            guidance=[
                _organize(card, status, evidence) for status, card, evidence in shown
            ],
            current_assessment=ASSESSMENT_WITH_GUIDANCE,
            additional_evidence_required=questions,
            applicability_notes=notes,
            resolved_by=resolution.provider,
        )


def _organize(
    card: ContextCard,
    status: Applicability = Applicability.INDETERMINATE,
    evidence: str = "",
) -> GuidanceItem:
    """Project one Context Card into the presentation shape — verbatim fields."""
    return GuidanceItem(
        supporting_guidance=card.summary,
        supporting_sources=[s.publisher for s in card.sources if s.publisher],
        source_type=_source_type(card),
        authority="; ".join(s.publisher for s in card.sources if s.publisher) or "—",
        reference=card.title,
        source_urls=[s.url for s in card.sources if s.url],
        applicability=_applicability(card),
        card_status=card.status,
        applicability_status=APPLICABILITY_LABELS[status],
        applicability_evidence=evidence,
    )


def _source_type(card: ContextCard) -> str:
    from app.verified_context.trusted import TRUSTED_AUTHORITIES

    for source in card.sources:
        for key, authority in TRUSTED_AUTHORITIES.items():
            if source.publisher == authority.publisher:
                return _SOURCE_TYPE_BY_AUTHORITY_KEY.get(key, "Trusted Procurement Guidance")
    return "Trusted Procurement Guidance"


def _applicability(card: ContextCard) -> str:
    """Restate the card's own declared scope — nothing inferred."""
    parts = [f"Relevant to findings of type: {', '.join(card.applies_to_indicators)}"]
    if card.jurisdictions:
        parts.append(f"jurisdiction: {', '.join(card.jurisdictions)}")
    if card.categories:
        parts.append(f"category: {', '.join(card.categories)}")
    return "; ".join(parts) + "."
