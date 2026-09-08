"""Priority Investigation Queue — built from the CURRENT procurement database.

Answers "where should an investigator start today?" from the live imported data,
NOT from past investigations. For buyer-level leads it runs the EXISTING
 deterministic investigation engine (``build_indicators`` + ``assess_risk_v2``)
over the buyer's tenders and ranks the results.

The queue also surfaces explicit field-ready tender records (``FIELD:`` records
and CAG audit reconstruction records) as direct investigation leads. Those leads
are not assigned an invented risk score: they are surfaced because the database
contains a procurement/audit record that can be investigated and, where
appropriate, handed to SENTRY FIELD for physical verification.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Tender
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationCompanyResult,
    InvestigationDocumentResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan
from app.schemas.priority_queue import PriorityQueueItem, PriorityQueueResponse
from app.services.investigation_evidence import build_evidence_ledger
from app.services.investigation_indicators import build_indicators
from app.services.investigation_repository import DatabaseRecordSource
from app.services.risk_engine import assess_risk_v2

# International / foreign-financier sources are excluded from the India-targeted
# landing queue (same country isolation the executor applies).
_INTERNATIONAL_SOURCES = ("world_bank", "adb", "un_procurement", "prozorro")

# Minimum tenders for a buyer to be worth surfacing as an investigation lead.
_MIN_CLUSTER = 2

# Reserve room in the queue for direct tender leads so newly seeded field-ready
# records are discoverable even when most buyers only have a single tender.
_DEFAULT_LIMIT = 20

# Deterministic ordering of the engine's own severity band.
_RISK_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "insufficient": 0}
_PRIORITY_LABEL = {"critical": "critical", "high": "high", "medium": "medium", "low": "review", "insufficient": "review"}

# Placeholder / test / unattributed buyers that must never appear as a real lead.
_PLACEHOLDER_BUYERS = {
    "", "unknown", "unknown buyer", "unattributed", "n/a", "na", "none", "null",
    "test", "test buyer", "sample", "placeholder", "acme", "acme corp", "acme ltd",
    "demo", "example", "tbd", "xxx",
}


def _is_real_buyer(buyer: str | None) -> bool:
    """Exclude test/placeholder/incomplete procuring entities."""
    if not buyer:
        return False
    name = buyer.strip()
    normalized = name.casefold()
    if normalized in _PLACEHOLDER_BUYERS:
        return False
    letters = sum(1 for ch in name if ch.isalpha())
    if letters < 3:
        return False
    segments = [s for s in name.replace("||", " ").split() if s]
    if len(segments) == 1 and len(segments[0]) < 4:
        return False
    return True


def _evidence_strength(share: float) -> str:
    if share >= 0.66:
        return "high"
    if share >= 0.33:
        return "moderate"
    return "limited"


def _package_for_buyer(records: list[InvestigationProcurementRecord]) -> InvestigationPackage:
    plan = InvestigationPlan(
        query="", investigation_type="buyer", confidence=1.0,
        connectors=[], modules=["retrieval", "risk"], steps=[],
    )
    pkg = InvestigationPackage(plan=plan, records=records)
    pkg.indicators = build_indicators(pkg)
    try:
        pkg.risk_assessment_v2 = assess_risk_v2(pkg)
    except Exception:
        pkg.risk_assessment_v2 = None
    return pkg


def _to_pkg_record(record) -> InvestigationProcurementRecord:
    """Map a normalized DB record into the package record shape (deterministic)."""
    t = record.tender

    def meta(m) -> InvestigationSourceMetadata:
        return InvestigationSourceMetadata(
            source_name=m.source_name, source_record_id=m.source_record_id,
            source_url=m.source_url, retrieved_at=m.retrieved_at,
        )

    pr = InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=t.reference_number, title=t.title, description=t.description,
            procuring_entity=t.procuring_entity, published_date=t.published_date,
            closing_date=t.closing_date, estimated_value=t.estimated_value,
            currency=t.currency, metadata=meta(t.metadata),
        )
    )
    for company in record.companies:
        pr.companies.append(InvestigationCompanyResult(
            name=company.name, registration_number=company.registration_number,
            tax_id=None, company_identifier=company.registration_number,
            address=None, website=None, metadata=meta(company.metadata),
        ))
    for award in record.awards:
        pr.awards.append(InvestigationAwardResult(
            tender_reference_number=award.tender_reference_number, company_name=award.company_name,
            company_registration_number=award.company_registration_number, company_tax_id=None,
            company_identifier=award.company_registration_number, company_address=None,
            company_website=None, award_date=award.award_date, award_value=award.award_value,
            currency=award.currency, metadata=meta(award.metadata),
        ))
    for document in record.documents:
        pr.documents.append(InvestigationDocumentResult(
            title=document.title, url=document.url, document_type=document.document_type,
            metadata=meta(document.metadata),
        ))
    return pr


def _explain(pkg: InvestigationPackage, record_count: int, has_recent: bool, evidence_share: float) -> list[str]:
    """Deterministic, human-readable reasons this entity is recommended today."""
    reasons: list[str] = []
    rv2 = pkg.risk_assessment_v2
    typ = len(rv2.indicators) if rv2 else len(pkg.indicators)
    if typ >= 2:
        reasons.append(f"{typ} deterministic typologies triggered")
    elif typ == 1:
        name = (rv2.indicators[0].name if rv2 and rv2.indicators else pkg.indicators[0].title)
        reasons.append(f"Deterministic typology triggered: {name}")
    if record_count >= 5:
        reasons.append(f"Large linked procurement cluster ({record_count} tenders)")
    elif record_count >= 2:
        reasons.append(f"Multiple related tenders ({record_count})")
    if evidence_share >= 0.66:
        reasons.append("High evidence completeness")
    if has_recent:
        reasons.append("Recent procurement activity")
    if not reasons:
        reasons.append(f"{record_count} linked procurement record(s)")
    return reasons


def _field_ready_tender_items(db: Session) -> list[PriorityQueueItem]:
    """Return explicit field/audit tender records as direct investigation leads.

    Only records intentionally tagged by the field-seeding flow are included:
    ``FIELD:`` references for current procurement demos and ``cag`` audit records.
    This avoids turning arbitrary one-off database records into queue noise.
    """
    rows = db.execute(
        select(Tender)
        .where(Tender.source_name.notin_(_INTERNATIONAL_SOURCES))
        .where((Tender.reference_number.ilike("FIELD:%")) | (Tender.source_name == "cag"))
        .order_by(Tender.created_at.desc())
    ).scalars().all()

    items: list[PriorityQueueItem] = []
    seen_source_records: set[str] = set()
    for tender in rows:
        source_record_id = (tender.source_record_id or "").strip()
        if not source_record_id or source_record_id in seen_source_records:
            continue
        seen_source_records.add(source_record_id)

        is_audit = (tender.source_name or "").casefold() == "cag"
        label = "CAG audit record" if is_audit else "Field-verification-ready tender"
        reasons = [
            label + " in the current procurement database",
            "Direct tender lead — investigate the record before any field escalation",
        ]
        if is_audit:
            reasons.append("Historical audit evidence is preserved as source evidence; no new wrongdoing is inferred")
        else:
            reasons.append("Eligible for SENTRY FIELD capability planning after procurement review")

        items.append(PriorityQueueItem(
            subject=tender.title,
            investigation_type="tender",
            priority="review",
            risk_level="insufficient",
            typology_count=0,
            linked_records=1,
            evidence_strength="high" if tender.source_url else "limited",
            evidence_completeness=1.0 if tender.source_url else 0.0,
            primary_pattern="Field verification candidate" if not is_audit else "Audit reconstruction",
            reasons=reasons,
        ))
    return items


def build_priority_queue(db: Session, *, limit: int = _DEFAULT_LIMIT, candidate_pool: int = 40) -> PriorityQueueResponse:
    """Rank buyer leads, then reserve queue capacity for explicit tender leads."""
    buyer_label = Tender.procuring_entity
    rows = db.execute(
        select(buyer_label, func.count(Tender.id).label("c"))
        .where(buyer_label.isnot(None))
        .where(Tender.source_name.notin_(_INTERNATIONAL_SOURCES))
        .group_by(buyer_label)
        .order_by(func.count(Tender.id).desc())
        .limit(candidate_pool)
    ).all()

    source = DatabaseRecordSource(db)
    buyer_items: list[PriorityQueueItem] = []

    for buyer, tender_count in rows:
        if not _is_real_buyer(buyer) or tender_count < _MIN_CLUSTER:
            continue

        records = source.search(buyer, precision=True, limit=60, indian_only=True)
        pkg_records = [_to_pkg_record(r) for r in records if r.tender.procuring_entity == buyer]
        if len(pkg_records) < _MIN_CLUSTER:
            continue

        pkg = _package_for_buyer(pkg_records)
        rv2 = pkg.risk_assessment_v2
        risk_level = (rv2.overall_severity if rv2 else "insufficient") or "insufficient"
        typ = len(rv2.indicators) if rv2 else len(pkg.indicators)

        ledger = build_evidence_ledger(pkg)
        primary = sum(1 for c in ledger if c.quality_tier == "primary")
        evidence_share = round(primary / len(ledger), 2) if ledger else 0.0

        dates = [r.tender.published_date for r in pkg_records if r.tender.published_date]
        has_recent = bool(dates)

        primary_pattern = ""
        if rv2 and rv2.indicators:
            primary_pattern = rv2.indicators[0].name
        elif pkg.indicators:
            primary_pattern = pkg.indicators[0].title

        buyer_items.append(PriorityQueueItem(
            subject=buyer,
            investigation_type="buyer",
            priority=_PRIORITY_LABEL.get(risk_level.lower(), "review"),
            risk_level=risk_level,
            typology_count=typ,
            linked_records=len(pkg_records),
            evidence_strength=_evidence_strength(evidence_share),
            evidence_completeness=evidence_share,
            primary_pattern=primary_pattern,
            reasons=_explain(pkg, len(pkg_records), has_recent, evidence_share),
        ))

    buyer_items.sort(
        key=lambda it: (
            _RISK_RANK.get(it.risk_level.lower(), 0),
            it.typology_count,
            it.linked_records,
            it.evidence_completeness,
        ),
        reverse=True,
    )

    tender_items = _field_ready_tender_items(db)

    # Keep the established buyer-risk ordering, but guarantee that explicit
    # field/audit tender records remain discoverable in the same queue. With the
    # default 20-card queue this yields 10 buyer slots + the direct tender leads.
    buyer_slots = max(0, limit - min(len(tender_items), 10))
    selected = buyer_items[:buyer_slots] + tender_items[: max(0, limit - buyer_slots)]
    return PriorityQueueResponse(items=selected, total=len(selected))
