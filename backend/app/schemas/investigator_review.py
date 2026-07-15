"""Investigator Review — the three questions a senior investigator always asks.

SENTRY organizes evidence; it does not decide guilt. For every investigation the
review presents exactly three evidence-driven sections:

  1. Evidence Supporting Investigation   — objective facts that increase
     investigative interest (never assumptions).
  2. Evidence Supporting Routine Procurement — competing evidence that argues
     for a benign reading (never speculation, never cancelling the finding).
  3. Evidence Still Required             — what is missing to distinguish
     routine from suspicious procurement.

Every item is deterministic and traceable: it names the facts and records it
came from. There are no probabilities, no confidence meters, no verdicts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    """One evidence-driven statement in the Investigator Review.

    ``statement`` is an objective sentence; ``basis`` names the deterministic
    source of the statement (which detector, which record field); ``records``
    lists the tender references behind it so an auditor can verify each claim.
    """

    statement: str
    basis: str = ""                                   # e.g. "risk_engine:contract_fragmentation"
    records: list[str] = Field(default_factory=list)  # supporting tender references


class InvestigatorReview(BaseModel):
    """The three-section evidence review attached to every investigation.

    This is an organizational layer over evidence the deterministic pipeline
    already produced — it introduces no new detection, no scoring, and no
    judgment. ``supporting`` never asserts wrongdoing; ``routine`` never cancels
    an indicator; ``required`` tells the investigator exactly what to obtain next.
    """

    supporting: list[ReviewItem] = Field(default_factory=list)   # evidence supporting investigation
    routine: list[ReviewItem] = Field(default_factory=list)      # evidence supporting routine procurement
    required: list[ReviewItem] = Field(default_factory=list)     # evidence still required
    principle: str = (
        "SENTRY organizes evidence for investigator review. It does not determine "
        "wrongdoing. Indicators are leads, competing evidence is presented alongside "
        "them, and the evidence still required lists what would distinguish routine "
        "procurement from procurement needing escalation."
    )
