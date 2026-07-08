"""Schemas for cross-investigation AI memory.

Memory is itself evidence: each entry records a *prior* investigation's grounded
conclusion with a timestamp, so recalling it later is provenanced, not invented.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InvestigationMemoryEntry(BaseModel):
    """A compact, durable record of one completed investigation."""

    subject: str
    investigation_type: str
    risk_level: str
    confidence: float = 0.0
    key_entities: list[str] = Field(default_factory=list)
    key_indicators: list[str] = Field(default_factory=list)
    records_reviewed: int = 0
    remembered_at: datetime


class MemoryHit(InvestigationMemoryEntry):
    """A recalled prior investigation, with how strongly it matched."""

    match_score: int = 0
    match_reason: str = ""
