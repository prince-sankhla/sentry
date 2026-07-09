"""Schemas for pre-investigation canonical entity resolution.

Every investigation must begin by resolving the user's free text to a *specific*
canonical entity. These schemas carry the ranked candidate set and the
disambiguation decision so no investigation ever runs on ambiguous text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityCandidate(BaseModel):
    """One canonical entity the query might refer to, with why it matched.

    Fully explainable: ``match_type`` and ``match_reason`` state *why* this
    candidate was proposed, and ``score``/``confidence`` how strongly, so an
    analyst (or the UI) can rank and choose deterministically.
    """

    entity_id: str
    canonical_name: str
    entity_type: str = "company"
    registration_number: str | None = None
    aliases: list[str] = Field(default_factory=list)
    # exact | alias | registration | official_name | fuzzy — the resolution method.
    match_type: str
    match_reason: str
    # Which field the match was made against (name / registration_number /
    # procuring_entity / alias) — Phase 6 explainability.
    matched_field: str | None = None
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    # Grounding: how much procurement activity backs this candidate.
    tender_count: int = 0
    award_count: int = 0
    sources: list[str] = Field(default_factory=list)


class EntityResolutionResult(BaseModel):
    """Result of resolving a free-text query to canonical entities.

    ``requires_disambiguation`` is ``True`` when the text maps to more than one
    plausible entity and no single candidate dominates — the caller must then
    require explicit selection before procurement retrieval begins.
    """

    query: str
    resolved: bool
    requires_disambiguation: bool
    candidates: list[EntityCandidate] = Field(default_factory=list)
    selected_entity_id: str | None = None
    reason: str = ""
