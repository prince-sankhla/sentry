"""Schemas for the Priority Investigation Queue.

The queue is built from the CURRENT procurement database by running the existing
deterministic investigation engine per procuring entity. Every field is a
projection of that engine's output — nothing is inferred by AI and nothing comes
from historical investigation memory.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PriorityQueueItem(BaseModel):
    """One recommended starting point, with an explainable rationale.

    Direct tender leads carry stable tender identity so the frontend can start an
    investigation against the exact database record rather than using the tender
    title as a free-text proxy.
    """

    subject: str                             # the real procuring entity to investigate
    investigation_type: str = "buyer"
    priority: str = "review"                 # critical | high | medium | review (from risk band)
    risk_level: str = "insufficient"         # engine's overall_severity, verbatim
    typology_count: int = 0                  # deterministic typologies triggered
    linked_records: int = 0                  # linked procurement records (this entity's tenders)
    evidence_strength: str = "moderate"      # high | moderate | limited (from evidence completeness)
    evidence_completeness: float = 0.0       # primary-source share from the evidence ledger
    primary_pattern: str = ""                # first triggered indicator name, verbatim
    reasons: list[str] = Field(default_factory=list)  # why this is recommended, in plain language
    tender_id: str | None = None             # stable Tender UUID for direct tender leads
    reference_number: str | None = None      # exact source/reference identifier
    tender_title: str | None = None          # display title without becoming the lookup key


class PriorityQueueResponse(BaseModel):
    """Deterministic Priority Investigation Queue over the current database."""

    items: list[PriorityQueueItem] = Field(default_factory=list)
    total: int = 0
