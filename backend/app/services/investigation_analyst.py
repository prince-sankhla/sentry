"""Multi-step analyst — grounded, tool-driven reasoning over the package.

A real procurement analyst does not glance once and conclude; they pull threads:
"who won this?", "is this buyer concentrated?", "are these values outliers?",
"what's the strongest evidence?". This module models that as a bounded sequence
of **read-only tools** that operate *only* over the :class:`InvestigationPackage`.

Each tool returns facts derived purely from the package plus the citations that
back them. The runner executes a fixed analyst playbook and emits an auditable
:class:`AnalystStep` trace. Because every observation is computed from package
data (never generated), the trace cannot hallucinate — it is the backend proving,
step by step, what the narrative will later explain.

If a live LLM is configured it may *narrate* the trace, but tool selection and
every observed fact remain deterministic and grounded.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_reasoning import AnalystStep, ReasoningCitation
from app.services.investigation_evidence import citation_from_record


def _record_by_ref(pkg: InvestigationPackage) -> dict[str, object]:
    return {r.tender.reference_number: r for r in pkg.records}


# --------------------------------------------------------------------------- tools
# Every tool returns (observation_text, citations). Facts only.


def tool_survey_records(pkg: InvestigationPackage) -> tuple[str, list[ReasoningCitation]]:
    n = len(pkg.records)
    awards = sum(len(r.awards) for r in pkg.records)
    ents = len(pkg.canonical_companies)
    cits = [citation_from_record(r, confidence=0.6) for r in pkg.records[:3]]
    return (
        f"Reviewed {n} procurement record(s) spanning {ents} resolved entity(ies) "
        f"and {awards} award(s).",
        cits,
    )


def tool_buyer_concentration(pkg: InvestigationPackage) -> tuple[str, list[ReasoningCitation]]:
    buyers = Counter(
        (r.tender.procuring_entity or "").strip()
        for r in pkg.records
        if (r.tender.procuring_entity or "").strip()
    )
    if not buyers:
        return ("No procuring-entity data available to assess buyer concentration.", [])
    top_buyer, count = buyers.most_common(1)[0]
    total = sum(buyers.values())
    share = round(count / total * 100) if total else 0
    cits = [
        citation_from_record(r, confidence=0.65)
        for r in pkg.records
        if (r.tender.procuring_entity or "").strip() == top_buyer
    ][:3]
    verdict = "elevated" if share >= 60 else "moderate" if share >= 35 else "low"
    return (
        f"Buyer concentration is {verdict}: “{top_buyer}” accounts for {count} of "
        f"{total} tenders ({share}%).",
        cits,
    )


def tool_value_outliers(pkg: InvestigationPackage) -> tuple[str, list[ReasoningCitation]]:
    valued = [
        (r, Decimal(r.tender.estimated_value))
        for r in pkg.records
        if r.tender.estimated_value is not None
    ]
    if len(valued) < 2:
        return ("Insufficient valued tenders to compute value outliers.", [])
    values = [v for _, v in valued]
    mean = sum(values) / len(values)
    top_rec, top_val = max(valued, key=lambda x: x[1])
    ratio = float(top_val / mean) if mean else 0.0
    cit = citation_from_record(top_rec, confidence=0.7)
    flag = "a significant outlier" if ratio >= 3 else "above average" if ratio >= 1.5 else "within normal range"
    return (
        f"Highest-value tender ({top_rec.tender.reference_number}) is {flag} at "
        f"{ratio:.1f}× the mean estimated value across the record set.",
        [cit],
    )


def tool_award_recipients(pkg: InvestigationPackage) -> tuple[str, list[ReasoningCitation]]:
    winners = Counter(
        a.company_name.strip()
        for r in pkg.records
        for a in r.awards
        if a.company_name.strip()
    )
    if not winners:
        return ("No awards are recorded for this investigation.", [])
    top_winner, wins = winners.most_common(1)[0]
    cits = [
        citation_from_record(r, confidence=0.7, related_entity=top_winner)
        for r in pkg.records
        if any(a.company_name.strip() == top_winner for a in r.awards)
    ][:3]
    repeat = " — a repeat winner worth scrutiny" if wins >= 2 else ""
    return (f"Top award recipient is “{top_winner}” with {wins} award(s){repeat}.", cits)


def tool_strongest_evidence(pkg: InvestigationPackage) -> tuple[str, list[ReasoningCitation]]:
    from app.services.investigation_evidence import build_evidence_ledger

    ledger = build_evidence_ledger(pkg)
    if not ledger:
        return ("No verifiable evidence items are attached to this investigation.", [])
    best = ledger[0]  # ledger is sorted by quality desc
    return (
        f"Strongest evidence is a {best.quality_tier} source "
        f"({best.source_name}, quality {best.quality}/100){' with an attached document' if best.document_url else ''}.",
        [best],
    )


_PLAYBOOK = [
    ("survey_records", tool_survey_records),
    ("buyer_concentration", tool_buyer_concentration),
    ("value_outliers", tool_value_outliers),
    ("award_recipients", tool_award_recipients),
    ("strongest_evidence", tool_strongest_evidence),
]


def run_analyst_trace(pkg: InvestigationPackage) -> list[AnalystStep]:
    """Execute the analyst playbook, emitting a grounded, auditable step trace."""
    if not pkg.records:
        return []
    steps: list[AnalystStep] = []
    for order, (tool_name, fn) in enumerate(_PLAYBOOK, start=1):
        try:
            observation, citations = fn(pkg)
        except Exception:
            continue
        steps.append(
            AnalystStep(
                order=order,
                tool=tool_name,
                observation=observation,
                citations=citations,
            )
        )
    return steps
