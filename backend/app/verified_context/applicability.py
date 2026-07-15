"""Applicability evaluation — is this guidance actually supported by the facts?

The analyzer must behave like an experienced procurement investigator: a rule
is never forced onto a finding. Before any Context Card is shown, it is
evaluated against the retrieved investigation facts:

    SUPPORTED      — the facts affirmatively match the guidance's premise
                     (e.g. award dates genuinely cluster at financial year-end)
    POTENTIAL      — the guidance is procedural (its discriminating facts live
                     off-portal) and nothing in the retrieved facts contradicts it
    INDETERMINATE  — the facts needed to evaluate the premise are absent
    CONTRADICTED   — the retrieved facts are inconsistent with the premise
                     (e.g. no award falls anywhere near year-end)

Display policy (applied by the analyzer):
    SUPPORTED      → shown as  "Directly supported by retrieved evidence"
    POTENTIAL      → shown as  "Potentially applicable based on retrieved evidence"
    INDETERMINATE / CONTRADICTED → NOT shown; a neutral note states that
    applicability could not be established from the available evidence.
    (Deliberately the same neutral phrasing for both — the analyzer never
    manufactures a conflict between evidence and authority guidance.)

Everything here is deterministic arithmetic/term matching over a minimal,
read-only facts payload. No AI, no probabilities, no opinions.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Callable

from pydantic import BaseModel, Field

# Mirrors the deterministic constants the risk engine already uses — read-only
# reuse so the analyzer never disagrees with the engine about what counts as
# emergency/corrigendum language or a normal award-publication window.
from app.services.investigation_indicators import _AWARD_GRACE_DAYS
from app.services.risk_engine import _CORRECTION_TERMS, _DISASTER_TERMS, _EMERGENCY_TERMS


class Applicability(str, Enum):
    SUPPORTED = "directly_supported"
    POTENTIAL = "potentially_applicable"
    INDETERMINATE = "not_established"
    CONTRADICTED = "not_established_contradicted"


# Display labels — fixed, neutral, deterministic.
APPLICABILITY_LABELS: dict[Applicability, str] = {
    Applicability.SUPPORTED: "Directly supported by retrieved evidence",
    Applicability.POTENTIAL: "Potentially applicable based on retrieved evidence",
    Applicability.INDETERMINATE: "Applicability cannot be established from available evidence",
    Applicability.CONTRADICTED: "Applicability cannot be established from available evidence",
}


class FactRecord(BaseModel):
    """Minimal, read-only projection of one procurement record's facts."""

    reference_number: str = ""
    title: str = ""
    description: str = ""
    procuring_entity: str = ""
    suppliers: list[str] = Field(default_factory=list)
    published_date: date | None = None
    closing_date: date | None = None
    award_dates: list[date] = Field(default_factory=list)


class ContextFacts(BaseModel):
    """The retrieved facts of the investigation, as the analyzer sees them."""

    records: list[FactRecord] = Field(default_factory=list)
    as_of: date | None = None      # data-retrieval date (for award-window arithmetic)


class Evaluation(BaseModel):
    status: Applicability
    evidence: str = ""             # the fact backing SUPPORTED, verbatim arithmetic


# ------------------------------------------------------------------ evaluators

def _blob(facts: ContextFacts) -> str:
    return " ".join(f"{r.title} {r.description}" for r in facts.records).casefold()


def eval_fy_end(facts: ContextFacts) -> Evaluation:
    """Year-end guidance applies only when award dates genuinely cluster in Feb–Mar."""
    dates = [d for r in facts.records for d in r.award_dates]
    if not dates:
        return Evaluation(status=Applicability.INDETERMINATE)
    fy = [d for d in dates if d.month in (2, 3)]
    if fy and len(fy) * 2 >= len(dates):
        return Evaluation(
            status=Applicability.SUPPORTED,
            evidence=f"{len(fy)} of {len(dates)} award dates fall in February–March.",
        )
    return Evaluation(status=Applicability.CONTRADICTED)


def eval_emergency(facts: ContextFacts) -> Evaluation:
    """Emergency guidance applies only when emergency/disaster language exists."""
    blob = _blob(facts)
    if not blob.strip():
        return Evaluation(status=Applicability.INDETERMINATE)
    hits = [t for t in (*_EMERGENCY_TERMS, *_DISASTER_TERMS) if t in blob]
    if hits:
        return Evaluation(
            status=Applicability.SUPPORTED,
            evidence=f"Emergency/urgency language present in the retrieved records (“{hits[0]}”).",
        )
    return Evaluation(status=Applicability.INDETERMINATE)


def eval_corrigendum_upgrade(facts: ContextFacts) -> Evaluation:
    """Bid-time guidance is procedural; a correction notice upgrades it to supported."""
    blob = _blob(facts)
    hits = [t for t in _CORRECTION_TERMS if t in blob]
    if hits:
        return Evaluation(
            status=Applicability.SUPPORTED,
            evidence=f"A correction notice is present in the retrieved records (“{hits[0]}”).",
        )
    return Evaluation(status=Applicability.POTENTIAL)


def eval_works_programme(facts: ContextFacts) -> Evaluation:
    """Lot-splitting guidance is supported when the batch shows distinct work scopes."""
    titles = [r.title.strip().casefold() for r in facts.records if r.title.strip()]
    if len(titles) < 3:
        return Evaluation(status=Applicability.INDETERMINATE)
    if len(set(titles)) == len(titles):
        return Evaluation(
            status=Applicability.SUPPORTED,
            evidence=f"All {len(titles)} tenders describe distinct works/locations.",
        )
    return Evaluation(status=Applicability.POTENTIAL)


def eval_award_window(facts: ContextFacts) -> Evaluation:
    """'Award not yet due' guidance requires closed award-less tenders within the window."""
    if facts.as_of is None:
        return Evaluation(status=Applicability.INDETERMINATE)
    closed_no_award = [
        r for r in facts.records if r.closing_date is not None and not r.award_dates
    ]
    if not closed_no_award:
        return Evaluation(status=Applicability.INDETERMINATE)
    overdue = [r for r in closed_no_award if (facts.as_of - r.closing_date).days >= _AWARD_GRACE_DAYS]
    if overdue:
        return Evaluation(status=Applicability.CONTRADICTED)
    return Evaluation(
        status=Applicability.SUPPORTED,
        evidence=(
            f"{len(closed_no_award)} closed tender(s) without an award are within the "
            f"~{_AWARD_GRACE_DAYS}-day publication window as of {facts.as_of}."
        ),
    )


def eval_supplier_breadth(facts: ContextFacts) -> Evaluation:
    """Repeat-winner guidance upgrades when a supplier demonstrably serves several buyers."""
    supplier_buyers: dict[str, set[str]] = {}
    for r in facts.records:
        if not r.procuring_entity:
            continue
        for supplier in r.suppliers:
            supplier_buyers.setdefault(supplier, set()).add(r.procuring_entity)
    for supplier, buyers in sorted(supplier_buyers.items()):
        if len(buyers) >= 2:
            return Evaluation(
                status=Applicability.SUPPORTED,
                evidence=f"{supplier} holds awards from {len(buyers)} distinct procuring entities.",
            )
    return Evaluation(status=Applicability.POTENTIAL)


def eval_procedural(_: ContextFacts) -> Evaluation:
    """Guidance whose discriminating facts live off-portal (files, registers):
    shown as potentially applicable — nothing in portal facts can confirm it."""
    return Evaluation(status=Applicability.POTENTIAL)


# Corpus/library entry id → its applicability evaluator. Cards without an
# entry here are treated as procedural (POTENTIAL) — shown but honestly labeled.
EVALUATORS: dict[str, Callable[[ContextFacts], Evaluation]] = {
    "gfr-year-end-rush": eval_fy_end,
    "gfr-emergency-direct": eval_emergency,
    "gfr-bid-time": eval_corrigendum_upgrade,
    "cvc-splitting": eval_works_programme,
    "ocp-award-publication": eval_award_window,
    "ocp-repeat-winner": eval_supplier_breadth,
    "gfr-single-bid": eval_procedural,
    "worldbank-cost-estimates": eval_procedural,
}


def evaluate_card(card_id: str, facts: ContextFacts) -> Evaluation:
    """Evaluate one card's applicability against the retrieved facts."""
    key = card_id.removeprefix("draft-")
    evaluator = EVALUATORS.get(key, eval_procedural)
    return evaluator(facts)
