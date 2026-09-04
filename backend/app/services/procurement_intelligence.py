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
from app.services.procurement_scope import is_indian_source

REPEAT_SUPPLIER_MIN_AWARDS = 2
CONCENTRATION_REVIEW_THRESHOLD = Decimal("0.50")
STRONG_CONCENTRATION_THRESHOLD = Decimal("0.75")
STRONG_CONCENTRATION_MIN_AWARDS = 3


def build_tender_intelligence(db: Session, tender: Tender) -> ProcurementIntelligence:
    if not is_indian_source(tender.source_name):
        return ProcurementIntelligence(signals=[], relationship_scores=[])

    awards = _indian_awards_with_entities(db)
    tender_awards = [award for award in awards if award.tender_id == tender.id and award.company is not None]
    buyer = _buyer_key(tender.procuring_entity)
    buyer_awards_map = _awards_by_buyer(awards)

    relationship_scores = [
        _relationship_score(buyer_awards=buyer_awards_map[relationship_buyer], supplier_awards=supplier_awards)
        for (relationship_buyer, _company_id), supplier_awards in _awards_by_buyer_supplier(awards).items()
        if relationship_buyer == buyer
        and supplier_awards
        and supplier_awards[0].company_id in {award.company_id for award in tender_awards}
        and relationship_buyer in buyer_awards_map
    ]

    signals = _relationship_signals(relationship_scores, tender_id=tender.id)
    return ProcurementIntelligence(
        signals=_dedupe_signals(signals),
        relationship_scores=sorted(relationship_scores, key=lambda score: score.score, reverse=True),
    )


def build_company_intelligence(db: Session, company: Company) -> ProcurementIntelligence:
    awards = _indian_awards_with_entities(db)
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
    awards = _indian_awards_with_entities(db)

    # Indian procurement surfaces only. Award/winner-centric records cannot
    # support a single-bidder conclusion unless the source exposes bidder data.
    single_bidder_tenders = 0
    signals: list[RiskSignal] = []

    buyer_awards = _awards_by_buyer(awards)
    flagged_relationships = 0
    for (buyer, _company_id), supplier_awards in _awards_by_buyer_supplier(awards).items():
        if len(supplier_awards) < REPEAT_SUPPLIER_MIN_AWARDS or buyer not in buyer_awards:
            continue

        relationship = _relationship_score(
            buyer_awards=buyer_awards[buyer],
            supplier_awards=supplier_awards,
        )
        flagged_relationships += 1
        severity, title = _relationship_severity(relationship)
        signals.append(
            RiskSignal(
                type="buyer_supplier_relationship" if severity == "high" else "repeat_supplier",
                severity=severity,
                title=title,
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
                    "Source scope: Indian procurement records only",
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


def _indian_awards_with_entities(db: Session) -> list[Award]:
    awards = db.execute(
        select(Award).options(joinedload(Award.company), joinedload(Award.tender))
    ).unique().scalars().all()
    return [
        award
        for award in awards
        if award.tender is not None
        and award.company is not None
        and is_indian_source(award.tender.source_name)
    ]


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


def _relationship_severity(relationship: BuyerSupplierRelationshipScore) -> tuple[str, str]:
    # High is reserved for sustained, strong concentration. Repeat awards alone
    # remain medium because concentration can be entirely legitimate in a
    # specialised supplier market.
    strong = (
        relationship.awards_to_supplier >= STRONG_CONCENTRATION_MIN_AWARDS
        and relationship.supplier_award_share >= STRONG_CONCENTRATION_THRESHOLD
        and relationship.total_buyer_awards >= 4
    )
    if strong:
        return "high", "Buyer-Supplier Concentration Review"
    return "medium", "Repeat Supplier / Concentration Review"


def _relationship_signals(
    relationship_scores: list[BuyerSupplierRelationshipScore],
    *,
    tender_id: UUID | None = None,
    company_id: UUID | None = None,
) -> list[ProcurementIntelligenceSignal]:
    signals: list[ProcurementIntelligenceSignal] = []
    for relationship in relationship_scores:
        if relationship.awards_to_supplier >= REPEAT_SUPPLIER_MIN_AWARDS:
            severity = "high" if (
                relationship.awards_to_supplier >= STRONG_CONCENTRATION_MIN_AWARDS
                and relationship.supplier_award_share >= STRONG_CONCENTRATION_THRESHOLD
                and relationship.total_buyer_awards >= 4
            ) else "medium"
            signals.append(
                ProcurementIntelligenceSignal(
                    type="repeat_supplier",
                    severity=severity,
                    title="Repeat Supplier Detection" if severity == "medium" else "Buyer-Supplier Concentration Review",
                    summary=f"{relationship.supplier_name} has {relationship.awards_to_supplier} recorded awards from {relationship.buyer or 'the same buyer'}.",
                    score=relationship.score,
                    evidence=[
                        "Source scope: Indian procurement records only",
                        f"Awards to supplier: {relationship.awards_to_supplier}",
                        f"Total buyer awards indexed: {relationship.total_buyer_awards}",
                        f"Supplier share: {relationship.supplier_award_share:.0%}",
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
