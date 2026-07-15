"""Common Context schema — the unit of knowledge is the Context Card.

A Context Card captures ONE piece of legitimate procurement context (e.g. "GFR
2017 permits single-bid acceptance after re-tender"), with the provenance and
verification status that make it trustworthy enough to sit beside a finding.

Lifecycle (``status``):
    draft     — retrieved from a trusted source, awaiting human review (Phase 2)
    verified  — approved by a reviewer; permanent, reusable knowledge (Phase 3)
    retired   — superseded or found incorrect; never returned to investigations

Phase 1 ships the schema and an (initially empty) store of cards; only
``verified`` cards are ever served to an investigation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1

# The engine's honest answer when the library holds nothing applicable.
CONTEXT_UNAVAILABLE = "Context unavailable"


class ContextSource(BaseModel):
    """Provenance for a Context Card — where this knowledge came from."""

    title: str                          # e.g. "General Financial Rules 2017, Rule 173"
    url: str | None = None              # authoritative location, when one exists
    publisher: str = ""                 # e.g. "Ministry of Finance", "CVC"
    retrieved_at: datetime | None = None


class ContextCard(BaseModel):
    """One verified (or draft) piece of legitimate procurement context."""

    schema_version: int = SCHEMA_VERSION
    card_id: str                        # stable slug, e.g. "gfr-single-bid-retender"
    title: str                          # short human title
    summary: str                        # the context itself, stated plainly
    # Which deterministic finding types this context can legitimately explain
    # (indicator ids from the risk engine, e.g. "single_bidder").
    applies_to_indicators: list[str] = Field(default_factory=list)
    # Optional scoping — empty means "applies generally".
    jurisdictions: list[str] = Field(default_factory=list)   # e.g. ["IN", "IN-OD"]
    categories: list[str] = Field(default_factory=list)      # e.g. ["works", "goods"]
    # The questions an investigator must still answer before relying on this
    # context (a card never closes a finding by itself).
    verification_questions: list[str] = Field(default_factory=list)
    sources: list[ContextSource] = Field(default_factory=list)
    status: Literal["draft", "verified", "retired"] = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: datetime | None = None
    verified_by: str = ""               # reviewer identity (Phase 3)


class ContextQuery(BaseModel):
    """What an investigation asks the engine for."""

    indicator_id: str                   # e.g. "contract_fragmentation"
    jurisdiction: str = ""              # optional narrowing, e.g. "IN-OD"
    category: str = ""                  # optional narrowing, e.g. "works"


class ContextResolution(BaseModel):
    """The engine's answer. ``available`` is False ⇢ ``message`` explains why —
    honestly and without speculation."""

    available: bool
    cards: list[ContextCard] = Field(default_factory=list)
    message: str = ""                   # CONTEXT_UNAVAILABLE when nothing found
    provider: str = ""                  # which provider answered (provenance)
