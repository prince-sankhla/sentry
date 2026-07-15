"""Build the Investigator Review from an executed investigation package.

Runs AFTER deterministic findings are produced and reorganizes what the pipeline
already knows into the three questions a senior procurement investigator asks:

  * What evidence supports this finding?
  * What evidence argues against it (supports routine procurement)?
  * What evidence is still missing?

Strictly deterministic and strictly organizational:
  - Supporting items restate triggered indicators/patterns and package facts.
  - Routine items restate ONLY evidence-backed context the engine or records
    already contain (emergency/disaster/corrigendum language, PSU buyers,
    within-window award timing, multi-buyer supplier footprints, attached
    primary documents). Nothing is speculated; no indicator is suppressed.
  - Required items come from each indicator's declared ``required_evidence``
    plus a curated, per-typology investigator checklist (the questions that
    distinguish routine from suspicious procurement). This checklist is the
    LAST layer — content, not matching logic.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigator_review import InvestigatorReview, ReviewItem

# ------------------------------------------------------------------ checklists

# Per-typology "evidence still required" — each item helps distinguish routine
# procurement from procurement needing escalation. Curated from standard
# procurement-audit practice (CVC/CAG-style verification steps); content only.
_REQUIRED_BY_INDICATOR: dict[str, list[str]] = {
    "contract_fragmentation": [
        "Do the lots share one funding source / budget head?",
        "Is there a single Detailed Project Report (DPR) covering the works?",
        "Were the lots part of one sanctioned work package or scheme?",
        "Was the same evaluation committee used across lots?",
        "Is there a recorded justification for lot-wise tendering?",
        "Do the lot values sit just below a sanction/approval threshold?",
    ],
    "single_bidder": [
        "How many bids were received and how many were technically qualified?",
        "Was the tender re-floated before award, as rules typically require?",
        "Is there a documented single-bid justification/approval?",
    ],
    "repeat_supplier": [
        "Were the awards under one framework agreement / rate contract?",
        "Bid participation lists — did other bidders compete and lose?",
        "Do the contracts belong to distinct projects, phases, or corridors?",
    ],
    "award_clustering": [
        "Do the awards fall at financial year-end (budget-lapse pressure)?",
        "Same work package / project phase, or independent requirements?",
        "Were sanctions/approvals dated before or after the clustering window?",
    ],
    "buyer_concentration": [
        "Bid participation records — is the concentration explained by lack of competitors?",
        "Are there pre-qualification criteria that narrowed the field?",
    ],
    "supplier_concentration": [
        "Does the supplier's registered capability match the awarded scope?",
        "Are there other buyers procuring the same category from other suppliers?",
    ],
    "high_value_direct_award": [
        "Is there a recorded nomination/direct-award justification?",
        "Was administrative/financial sanction obtained at the right level?",
    ],
    "suspicious_timing": [
        "Tender opening and evaluation minutes — do dates support the timeline?",
        "Any corrigendum that legitimately compressed or shifted the schedule?",
    ],
    "abnormal_value": [
        "Cost estimate basis (schedule of rates / market survey) for the outlier?",
        "Contract amendments or scope changes after award?",
    ],
    "missing_award_data": [
        "Award notice from the portal's archived results section?",
        "Was the tender cancelled/re-tendered rather than awarded?",
    ],
    "missing_documents": [
        "NIT / BoQ / corrigendum from the official portal record?",
    ],
}

# Generic items appended when an indicator has no curated checklist.
_GENERIC_REQUIRED = [
    "Award justification / evaluation record for the flagged tenders?",
    "Contract amendments after award?",
]


# ------------------------------------------------------------------ builders

def build_investigator_review(pkg: InvestigationPackage) -> InvestigatorReview:
    """Assemble the three-section review from the finished package. Pure/deterministic."""
    review = InvestigatorReview()
    rv2 = pkg.risk_assessment_v2
    indicators = list(rv2.indicators) if rv2 else []

    # ---------------------------------------------- 1. evidence supporting investigation
    for ind in indicators:
        review.supporting.append(ReviewItem(
            statement=ind.reason,
            basis=f"risk_engine:{ind.id}",
            records=list(ind.supporting_records)[:25],
        ))
    if rv2:
        for pattern in rv2.patterns:
            review.supporting.append(ReviewItem(
                statement=f"Rule combination triggered: {pattern.name} — {pattern.reason or pattern.rule}",
                basis=f"risk_engine:pattern:{pattern.name}",
            ))

    # Package-level objective facts (only stated when true in the records).
    _add_cluster_facts(pkg, review)
    _add_identical_value_facts(pkg, review)

    # ---------------------------------------------- 2. evidence supporting routine procurement
    # (a) Context the engine itself detected — restated as competing evidence,
    #     WITHOUT changing any severity. These notes exist only when the engine
    #     found the corresponding language/structure in the records.
    seen_notes: set[str] = set()
    for ind in indicators:
        for note in ind.context_notes:
            if note not in seen_notes:
                seen_notes.add(note)
                review.routine.append(ReviewItem(
                    statement=note, basis=f"risk_engine:context:{ind.id}",
                    records=list(ind.supporting_records)[:10],
                ))

    # (b) Award-timing within the expected window (evidence-backed benign reading).
    _add_award_timing_routine(pkg, review)

    # (c) Supplier breadth: a supplier awarded by several distinct buyers in this
    #     package is consistent with an established multi-client contractor.
    _add_supplier_breadth_routine(pkg, review)

    # (c2) Financial year-end clustering: award dates concentrated in Feb–Mar
    #      (Indian FY end) are consistent with budget-lapse-driven activity.
    _add_fy_end_routine(pkg, review)

    # (d) Primary documents attached: the procurement is documented on the portal.
    docs = sum(
        1 for r in pkg.records
        for d in r.documents
        if (d.document_type or "").casefold() not in ("source_notice", "source notice", "")
    )
    if docs:
        review.routine.append(ReviewItem(
            statement=(
                f"{docs} primary procurement document(s) (NIT/BoQ/corrigendum) are published "
                "on the official portal — the process is publicly documented."
            ),
            basis="records:documents",
        ))

    # ---------------------------------------------- 3. evidence still required
    seen_required: set[str] = set()
    for ind in indicators:
        for question in _REQUIRED_BY_INDICATOR.get(ind.id, _GENERIC_REQUIRED):
            if question not in seen_required:
                seen_required.add(question)
                review.required.append(ReviewItem(
                    statement=question, basis=f"checklist:{ind.id}",
                    records=list(ind.supporting_records)[:10],
                ))
        # The indicator's own declared evidence requirements (engine metadata).
        missing_fields = ", ".join(ind.required_evidence)
        if missing_fields and ind.evidence_status != "verified":
            item = f"Verify against source records: {missing_fields} (evidence status: {ind.evidence_status})."
            if item not in seen_required:
                seen_required.add(item)
                review.required.append(ReviewItem(statement=item, basis=f"risk_engine:{ind.id}:required_evidence"))

    return review


# ------------------------------------------------------------------ fact helpers

def _add_cluster_facts(pkg: InvestigationPackage, review: InvestigatorReview) -> None:
    """Same-buyer cluster and shared-identifier facts, stated only when present."""
    by_buyer: dict[str, list] = defaultdict(list)
    for r in pkg.records:
        buyer = (r.tender.procuring_entity or "").strip()
        if buyer:
            by_buyer[buyer].append(r)
    for buyer, records in by_buyer.items():
        if len(records) >= 5:
            review.supporting.append(ReviewItem(
                statement=f"Large linked procurement cluster: {len(records)} tenders from '{buyer}' in this package.",
                basis="records:cluster",
                records=[r.tender.reference_number for r in records][:25],
            ))
    # Shared human procurement identifier across records (e.g. one NIT number).
    # Uses tender metadata source_record_id stems only when genuinely shared.
    stems: dict[str, list[str]] = defaultdict(list)
    for r in pkg.records:
        rid = (r.tender.metadata.source_record_id or "") if r.tender.metadata else ""
        if "_" in rid:
            stems[rid.rsplit("_", 1)[0]].append(r.tender.reference_number)
    for stem, refs in stems.items():
        if len(refs) >= 5:
            review.supporting.append(ReviewItem(
                statement=f"Shared procurement identifier: {len(refs)} tenders are numbered lots of one master record ({stem}).",
                basis="records:shared_identifier",
                records=refs[:25],
            ))


def _add_identical_value_facts(pkg: InvestigationPackage, review: InvestigatorReview) -> None:
    values: dict[Decimal, list[str]] = defaultdict(list)
    for r in pkg.records:
        if r.tender.estimated_value is not None:
            values[r.tender.estimated_value].append(r.tender.reference_number)
    identical = {v: refs for v, refs in values.items() if len(refs) > 1}
    if identical:
        pairs = sum(len(refs) for refs in identical.values())
        review.supporting.append(ReviewItem(
            statement=f"Identical estimated values: {pairs} tenders share {len(identical)} exact value(s).",
            basis="records:identical_values",
            records=[ref for refs in identical.values() for ref in refs][:25],
        ))


def _add_award_timing_routine(pkg: InvestigationPackage, review: InvestigatorReview) -> None:
    from app.services.investigation_indicators import award_timing_status

    try:
        status = award_timing_status(pkg)
    except Exception:
        return
    pending = status.get("pending") or []
    overdue = status.get("overdue") or []
    if pending and not overdue and status.get("as_of") is not None:
        review.routine.append(ReviewItem(
            statement=(
                f"{len(pending)} closed tender(s) without an award are still within the expected "
                f"award-publication window (as of {status['as_of']}) — absence of awards is "
                "consistent with a normal in-progress lifecycle, not a transparency gap."
            ),
            basis="indicators:award_timing_status",
            records=[r.tender.reference_number for r in pending][:10],
        ))


def _add_fy_end_routine(pkg: InvestigationPackage, review: InvestigatorReview) -> None:
    """Award dates concentrated at Indian financial year-end (Feb–Mar).

    Deterministic date check + authoritative procurement context: budget-lapse
    pressure legitimately concentrates awards before 31 March. Presented as
    competing evidence only — the clustering indicator itself is untouched.
    """
    award_dates = [a.award_date for r in pkg.records for a in r.awards if a.award_date]
    if not award_dates:
        return
    fy_end = [d for d in award_dates if d.month in (2, 3)]
    if len(fy_end) * 2 >= len(award_dates) and fy_end:
        refs = [
            r.tender.reference_number
            for r in pkg.records
            if any(a.award_date and a.award_date.month in (2, 3) for a in r.awards)
        ]
        review.routine.append(ReviewItem(
            statement=(
                f"{len(fy_end)} of {len(award_dates)} award date(s) fall in February–March — "
                "financial year-end procurement activity (budget-lapse pressure before 31 March) "
                "may explain award clustering."
            ),
            basis="records:award_dates_fy_end",
            records=refs[:10],
        ))


def _add_supplier_breadth_routine(pkg: InvestigationPackage, review: InvestigatorReview) -> None:
    supplier_buyers: dict[str, set[str]] = defaultdict(set)
    for r in pkg.records:
        buyer = (r.tender.procuring_entity or "").strip()
        for a in r.awards:
            if a.company_name and buyer:
                supplier_buyers[a.company_name].add(buyer)
    for supplier, buyers in supplier_buyers.items():
        if len(buyers) >= 2:
            review.routine.append(ReviewItem(
                statement=(
                    f"{supplier} holds awards from {len(buyers)} distinct procuring entities in this "
                    "package — consistent with an established multi-client contractor rather than a "
                    "single-buyer capture."
                ),
                basis="records:supplier_breadth",
            ))
