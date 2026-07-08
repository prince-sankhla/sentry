from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Company, Tender
from app.schemas.analytics import PortfolioRisk, RiskSignal, RiskSummary
from app.schemas.procurement_intelligence import (
    BuyerSupplierRelationshipScore,
    ProcurementIntelligence,
    ProcurementIntelligenceSignal,
)

REPEAT_SUPPLIER_MIN_AWARDS = 2
CONCENTRATION_REVIEW_THRESHOLD = Decimal("0.50")


def build_tender_intelligence(db: Session, tender: Tender) -> ProcurementIntelligence:
    awards = _awards_with_entities(db)
    tender_awards = [award for award in awards if award.tender_id == tender.id and award.company is not None]
    buyer = _buyer_key(tender.procuring_entity)

    signals: list[ProcurementIntelligenceSignal] = []
    if len({award.company_id for award in tender_awards}) == 1 and tender_awards:
        company = tender_awards[0].company
        if company is not None:
            signals.append(
                ProcurementIntelligenceSignal(
                    type="single_bidder",
                    severity="high",
                    title="Single Bidder Detection",
                    summary=f"Only one supplier is recorded against tender {tender.reference_number}.",
                    score=80,
                    evidence=[
                        f"Recorded suppliers: 1",
                        f"Supplier: {company.name}",
                        f"Buyer: {tender.procuring_entity or 'Unknown buyer'}",
                    ],
                    tender_id=tender.id,
                    company_id=company.id,
                    buyer=tender.procuring_entity,
                )
            )

    relationship_scores = [
        _relationship_score(buyer_awards=buyer_awards, supplier_awards=supplier_awards)
        for (relationship_buyer, _company_id), supplier_awards in _awards_by_buyer_supplier(awards).items()
        for buyer_awards in [_awards_by_buyer(awards)[relationship_buyer]]
        if relationship_buyer == buyer and supplier_awards and supplier_awards[0].company_id in {award.company_id for award in tender_awards}
    ]

    signals.extend(_relationship_signals(relationship_scores, tender_id=tender.id))
    return ProcurementIntelligence(
        signals=_dedupe_signals(signals),
        relationship_scores=sorted(relationship_scores, key=lambda score: score.score, reverse=True),
    )


def build_company_intelligence(db: Session, company: Company) -> ProcurementIntelligence:
    awards = _awards_with_entities(db)
    company_awards = [award for award in awards if award.company_id == company.id and award.tender is not None]
    buyer_awards = _awards_by_buyer(awards)
    relationship_scores = [
        _relationship_score(buyer_awards=buyer_awards[buyer], supplier_awards=supplier_awards)
        for buyer, supplier_awards in _company_awards_by_buyer(company_awards).items()
        if buyer in buyer_awards
    ]

    signals = _relationship_signals(relationship_scores, company_id=company.id)
    return ProcurementIntelligence(
        signals=_dedupe_signals(signals),
        relationship_scores=sorted(relationship_scores, key=lambda score: score.score, reverse=True),
    )


def build_portfolio_risk(db: Session) -> PortfolioRisk:
    awards = _awards_with_entities(db)
    valid_awards = [
        award for award in awards if award.tender is not None and award.company is not None
    ]

    signals: list[RiskSignal] = []

    # Single-bidder detection: tenders with exactly one distinct awarded company.
    awards_by_tender: dict[UUID, list[Award]] = defaultdict(list)
    for award in valid_awards:
        awards_by_tender[award.tender_id].append(award)

    single_bidder_tenders = 0
    for tender_awards in awards_by_tender.values():
        if len({award.company_id for award in tender_awards}) != 1:
            continue
        single_bidder_tenders += 1
        anchor = tender_awards[0]
        tender = anchor.tender
        company = anchor.company
        signals.append(
            RiskSignal(
                type="single_bidder",
                severity="high",
                title="Single Bidder Detection",
                summary=f"Only one supplier is recorded against tender {tender.reference_number}.",
                score=80,
                buyer=tender.procuring_entity,
                supplier_name=company.name,
                supplier_id=company.id,
                tender_id=tender.id,
                tender_reference=tender.reference_number,
                evidence=[
                    "Recorded suppliers: 1",
                    f"Supplier: {company.name}",
                    f"Buyer: {tender.procuring_entity or 'Unknown buyer'}",
                ],
            )
        )

    # Repeat-supplier / buyer-supplier relationship scoring.
    buyer_awards = _awards_by_buyer(awards)
    flagged_relationships = 0
    for (buyer, _company_id), supplier_awards in _awards_by_buyer_supplier(awards).items():
        if len(supplier_awards) < REPEAT_SUPPLIER_MIN_AWARDS:
            continue
        relationship = _relationship_score(
            buyer_awards=buyer_awards[buyer],
            supplier_awards=supplier_awards,
        )
        flagged_relationships += 1
        is_high = relationship.supplier_award_share >= CONCENTRATION_REVIEW_THRESHOLD
        signals.append(
            RiskSignal(
                type="buyer_supplier_relationship" if is_high else "repeat_supplier",
                severity="high" if is_high else "medium",
                title="Buyer-Supplier Relationship Scoring"
                if is_high
                else "Repeat Supplier Detection",
                summary=(
                    f"{relationship.supplier_name} holds {relationship.awards_to_supplier} awards "
                    f"from {relationship.buyer or 'the same buyer'} "
                    f"({relationship.supplier_award_share:.0%} of that buyer's awards)."
                ),
                score=relationship.score,
                buyer=relationship.buyer,
                supplier_name=relationship.supplier_name,
                supplier_id=relationship.supplier_id,
                tender_id=None,
                tender_reference=None,
                evidence=[
                    f"Awards to supplier: {relationship.awards_to_supplier}",
                    f"Total buyer awards indexed: {relationship.total_buyer_awards}",
                    f"Supplier share: {relationship.supplier_award_share:.0%}",
                    f"Latest award: "
                    f"{relationship.latest_award_date.isoformat() if relationship.latest_award_date else 'No award date'}",
                ],
            )
        )

    summary = RiskSummary(
        total=len(signals),
        high=sum(1 for signal in signals if signal.severity == "high"),
        medium=sum(1 for signal in signals if signal.severity == "medium"),
        low=sum(1 for signal in signals if signal.severity == "low"),
        single_bidder_tenders=single_bidder_tenders,
        flagged_relationships=flagged_relationships,
    )

    ranked = sorted(signals, key=lambda signal: signal.score, reverse=True)[:100]
    return PortfolioRisk(summary=summary, signals=ranked)


def _awards_with_entities(db: Session) -> list[Award]:
    return db.execute(
        select(Award).options(joinedload(Award.company), joinedload(Award.tender))
    ).unique().scalars().all()


def _awards_by_buyer(awards: list[Award]) -> dict[str, list[Award]]:
    grouped: dict[str, list[Award]] = defaultdict(list)
    for award in awards:
        if award.tender is not None and award.company is not None:
            grouped[_buyer_key(award.tender.procuring_entity)].append(award)
    return grouped


def _awards_by_buyer_supplier(awards: list[Award]) -> dict[tuple[str, UUID], list[Award]]:
    grouped: dict[tuple[str, UUID], list[Award]] = defaultdict(list)
    for award in awards:
        if award.tender is not None and award.company is not None:
            grouped[(_buyer_key(award.tender.procuring_entity), award.company_id)].append(award)
    return grouped


def _company_awards_by_buyer(awards: list[Award]) -> dict[str, list[Award]]:
    grouped: dict[str, list[Award]] = defaultdict(list)
    for award in awards:
        if award.tender is not None:
            grouped[_buyer_key(award.tender.procuring_entity)].append(award)
    return grouped


def _relationship_score(
    *,
    buyer_awards: list[Award],
    supplier_awards: list[Award],
) -> BuyerSupplierRelationshipScore:
    company = supplier_awards[0].company
    total_buyer_awards = max(len(buyer_awards), 1)
    awards_to_supplier = len(supplier_awards)
    supplier_share = Decimal(awards_to_supplier) / Decimal(total_buyer_awards)
    repeat_points = min(35, max(0, awards_to_supplier - 1) * 12)
    concentration_points = int(min(45, supplier_share * Decimal(45)))
    recency_points = 10 if _latest_award_date(supplier_awards) is not None else 0
    score = min(100, 10 + repeat_points + concentration_points + recency_points)

    return BuyerSupplierRelationshipScore(
        buyer=supplier_awards[0].tender.procuring_entity if supplier_awards[0].tender else None,
        supplier_id=company.id,
        supplier_name=company.name,
        score=score,
        awards_to_supplier=awards_to_supplier,
        total_buyer_awards=total_buyer_awards,
        supplier_award_share=supplier_share,
        total_award_value=sum((award.award_value for award in supplier_awards if award.award_value is not None), Decimal("0")),
        latest_award_date=_latest_award_date(supplier_awards),
    )


def _relationship_signals(
    relationship_scores: list[BuyerSupplierRelationshipScore],
    *,
    tender_id: UUID | None = None,
    company_id: UUID | None = None,
) -> list[ProcurementIntelligenceSignal]:
    signals: list[ProcurementIntelligenceSignal] = []
    for relationship in relationship_scores:
        if relationship.awards_to_supplier >= REPEAT_SUPPLIER_MIN_AWARDS:
            signals.append(
                ProcurementIntelligenceSignal(
                    type="repeat_supplier",
                    severity="high" if relationship.supplier_award_share >= CONCENTRATION_REVIEW_THRESHOLD else "medium",
                    title="Repeat Supplier Detection",
                    summary=f"{relationship.supplier_name} has {relationship.awards_to_supplier} recorded awards from {relationship.buyer or 'the same buyer'}.",
                    score=relationship.score,
                    evidence=[
                        f"Awards to supplier: {relationship.awards_to_supplier}",
                        f"Total buyer awards indexed: {relationship.total_buyer_awards}",
                        f"Supplier share: {relationship.supplier_award_share:.0%}",
                    ],
                    tender_id=tender_id,
                    company_id=company_id or relationship.supplier_id,
                    buyer=relationship.buyer,
                )
            )
        if relationship.score >= 70:
            signals.append(
                ProcurementIntelligenceSignal(
                    type="buyer_supplier_relationship",
                    severity="high",
                    title="Buyer-Supplier Relationship Scoring",
                    summary=f"Relationship score is {relationship.score}/100 for {relationship.supplier_name} and {relationship.buyer or 'the buyer'}.",
                    score=relationship.score,
                    evidence=[
                        f"Repeat award score: {relationship.awards_to_supplier} awards",
                        f"Concentration: {relationship.supplier_award_share:.0%}",
                        f"Latest award: {relationship.latest_award_date.isoformat() if relationship.latest_award_date else 'No award date'}",
                    ],
                    tender_id=tender_id,
                    company_id=company_id or relationship.supplier_id,
                    buyer=relationship.buyer,
                )
            )
    return signals


def _latest_award_date(awards: list[Award]) -> date | None:
    return max((award.award_date for award in awards if award.award_date is not None), default=None)


def _buyer_key(name: str | None) -> str:
    return (name or "unknown buyer").strip().casefold()


def _dedupe_signals(signals: list[ProcurementIntelligenceSignal]) -> list[ProcurementIntelligenceSignal]:
    unique: dict[tuple[str, UUID | None, UUID | None, str | None], ProcurementIntelligenceSignal] = {}
    for signal in signals:
        unique.setdefault((signal.type, signal.tender_id, signal.company_id, signal.buyer), signal)
    return list(unique.values())
