"""Platform-wide procurement statistics — every number from the database.

Computes buyer/supplier rankings, award concentration (HHI), supplier diversity,
competition metrics, and procurement/category/state trends directly from the
imported Tender/Award/Company rows. No placeholders, no hardcoded demo data:
if the database is empty, the aggregates are honestly zero.

Indian procurement first: geographic attribution uses the Indian state list, and
source coverage is annotated with the Indian-first priority rank so callers can
present Indian sources ahead of international ones.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.source_priority import is_indian_source, source_rank
from app.models import Award, Company, Tender
from app.schemas.procurement_statistics import (
    BuyerRanking,
    CategoryTrend,
    CompetitionMetrics,
    ConcentrationMetrics,
    ProcurementStatistics,
    SourceCoverage,
    StateTrend,
    SupplierDiversity,
    SupplierRanking,
    TrendPoint,
)

UNATTRIBUTED = "Unattributed"

INDIAN_STATES: tuple[str, ...] = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
)

_SOURCE_LABELS: dict[str, str] = {
    "gem": "Government e-Marketplace (GeM)",
    "cppp": "Central Public Procurement Portal (CPPP)",
    "cag": "Comptroller and Auditor General",
    "datagovin": "data.gov.in",
    "eproc_rajasthan": "Rajasthan eProcurement",
    "eproc_maharashtra": "Maharashtra eProcurement",
    "eproc_kerala": "Kerala eProcurement",
    "eproc_odisha": "Odisha eProcurement",
    "eproc_westbengal": "West Bengal eProcurement",
    "eproc_karnataka": "Karnataka eProcurement",
    "world_bank": "World Bank",
    "adb": "Asian Development Bank",
    "un_procurement": "United Nations (UNGM)",
    "prozorro": "Prozorro (Ukraine)",
}


def build_procurement_statistics(db: Session, *, top_n: int = 10) -> ProcurementStatistics:
    return ProcurementStatistics(
        top_buyers=_top_buyers(db, top_n),
        top_suppliers=_top_suppliers(db, top_n),
        award_concentration=_concentration(db),
        supplier_diversity=_diversity(db),
        competition=_competition(db),
        procurement_trends=_trends(db),
        category_trends=_category_trends(db, top_n),
        state_trends=_state_trends(db),
        source_coverage=_source_coverage(db),
    )


# --------------------------------------------------------------------------- rankings


def _top_buyers(db: Session, top_n: int) -> list[BuyerRanking]:
    buyer_label = func.coalesce(Tender.procuring_entity, UNATTRIBUTED)
    rows = db.execute(
        select(
            buyer_label,
            func.count(func.distinct(Award.tender_id)),
            func.count(Award.id),
            func.coalesce(func.sum(Award.award_value), 0),
            func.count(func.distinct(Award.company_id)),
        )
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .group_by(buyer_label)
        .order_by(func.coalesce(func.sum(Award.award_value), 0).desc(), func.count(Award.id).desc())
        .limit(top_n)
    ).all()

    rankings: list[BuyerRanking] = []
    for index, (buyer, tenders, awards, value, suppliers) in enumerate(rows, start=1):
        top_supplier, top_share = _buyer_top_supplier(db, buyer)
        rankings.append(
            BuyerRanking(
                rank=index,
                buyer=buyer,
                tenders=int(tenders),
                awards=int(awards),
                total_value=value,
                distinct_suppliers=int(suppliers),
                top_supplier=top_supplier,
                top_supplier_share=top_share,
            )
        )
    return rankings


def _buyer_top_supplier(db: Session, buyer: str) -> tuple[str | None, float]:
    condition = Tender.procuring_entity == buyer if buyer != UNATTRIBUTED else Tender.procuring_entity.is_(None)
    rows = db.execute(
        select(Company.name, func.count(Award.id))
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .join(Company, Award.company_id == Company.id)
        .where(condition)
        .group_by(Company.name)
        .order_by(func.count(Award.id).desc())
    ).all()
    if not rows:
        return None, 0.0
    total = sum(int(count) for _, count in rows)
    top_name, top_count = rows[0]
    return top_name, round(int(top_count) / total, 4) if total else 0.0


def _top_suppliers(db: Session, top_n: int) -> list[SupplierRanking]:
    rows = db.execute(
        select(
            Company.id,
            Company.name,
            func.count(Award.id),
            func.coalesce(func.sum(Award.award_value), 0),
            func.count(func.distinct(Tender.procuring_entity)),
        )
        .select_from(Award)
        .join(Company, Award.company_id == Company.id)
        .join(Tender, Award.tender_id == Tender.id)
        .group_by(Company.id, Company.name)
        .order_by(func.coalesce(func.sum(Award.award_value), 0).desc(), func.count(Award.id).desc())
        .limit(top_n)
    ).all()
    return [
        SupplierRanking(
            rank=index,
            company_id=company_id,
            name=name,
            awards=int(awards),
            total_value=value,
            distinct_buyers=int(buyers),
        )
        for index, (company_id, name, awards, value, buyers) in enumerate(rows, start=1)
    ]


# --------------------------------------------------------------------------- concentration


def _concentration(db: Session) -> ConcentrationMetrics:
    rows = db.execute(
        select(Company.id, func.coalesce(func.sum(Award.award_value), 0))
        .select_from(Award)
        .join(Company, Award.company_id == Company.id)
        .group_by(Company.id)
    ).all()
    total_awards = db.scalar(select(func.count(Award.id))) or 0

    values = sorted((Decimal(v) for _, v in rows), reverse=True)
    total_value = sum(values, Decimal("0"))
    if total_value <= 0:
        return ConcentrationMetrics(
            total_awards=int(total_awards),
            total_value=Decimal("0"),
            top_supplier_share=0.0,
            top5_supplier_share=0.0,
            hhi=0.0,
            interpretation="No award values recorded yet.",
        )

    top_share = float(values[0] / total_value)
    top5_share = float(sum(values[:5], Decimal("0")) / total_value)
    hhi = float(sum((v / total_value) ** 2 for v in values))
    interpretation = (
        "Highly concentrated market" if hhi >= 0.25
        else "Moderately concentrated market" if hhi >= 0.15
        else "Competitive / diffuse market"
    )
    return ConcentrationMetrics(
        total_awards=int(total_awards),
        total_value=total_value,
        top_supplier_share=round(top_share, 4),
        top5_supplier_share=round(top5_share, 4),
        hhi=round(hhi, 4),
        interpretation=interpretation,
    )


# --------------------------------------------------------------------------- diversity


def _diversity(db: Session) -> SupplierDiversity:
    distinct_suppliers = db.scalar(select(func.count(func.distinct(Award.company_id)))) or 0
    distinct_buyers = db.scalar(
        select(func.count(func.distinct(Tender.procuring_entity))).where(Tender.procuring_entity.is_not(None))
    ) or 0

    # Suppliers dependent on exactly one buyer.
    supplier_buyer_rows = db.execute(
        select(Award.company_id, func.count(func.distinct(Tender.procuring_entity)))
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .group_by(Award.company_id)
    ).all()
    single_buyer_suppliers = sum(1 for _, buyers in supplier_buyer_rows if int(buyers) == 1)

    # Buyers relying on exactly one supplier.
    buyer_supplier_rows = db.execute(
        select(Tender.procuring_entity, func.count(func.distinct(Award.company_id)))
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(Tender.procuring_entity.is_not(None))
        .group_by(Tender.procuring_entity)
    ).all()
    single_supplier_buyers = sum(1 for _, suppliers in buyer_supplier_rows if int(suppliers) == 1)

    per_buyer = round(distinct_suppliers / distinct_buyers, 2) if distinct_buyers else 0.0
    return SupplierDiversity(
        distinct_suppliers=int(distinct_suppliers),
        distinct_buyers=int(distinct_buyers),
        suppliers_per_buyer=per_buyer,
        single_buyer_suppliers=single_buyer_suppliers,
        single_supplier_buyers=single_supplier_buyers,
    )


# --------------------------------------------------------------------------- competition


def _competition(db: Session) -> CompetitionMetrics:
    total_tenders = db.scalar(select(func.count(Tender.id))) or 0
    tenders_with_awards = db.scalar(select(func.count(func.distinct(Award.tender_id)))) or 0

    bidder_rows = db.execute(
        select(Award.tender_id, func.count(func.distinct(Award.company_id)))
        .group_by(Award.tender_id)
    ).all()
    single_bidder = sum(1 for _, c in bidder_rows if int(c) == 1)
    multi_bidder = sum(1 for _, c in bidder_rows if int(c) > 1)
    avg_bidders = (
        round(sum(int(c) for _, c in bidder_rows) / len(bidder_rows), 2) if bidder_rows else 0.0
    )

    closed_tenders = db.scalar(
        select(func.count(Tender.id)).where(Tender.closing_date.is_not(None))
    ) or 0
    closed_with_awards = db.scalar(
        select(func.count(func.distinct(Award.tender_id)))
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(Tender.closing_date.is_not(None))
    ) or 0

    return CompetitionMetrics(
        total_tenders=int(total_tenders),
        tenders_with_awards=int(tenders_with_awards),
        single_bidder_tenders=single_bidder,
        single_bidder_rate=round(single_bidder / len(bidder_rows), 4) if bidder_rows else 0.0,
        multi_bidder_tenders=multi_bidder,
        average_bidders_per_tender=avg_bidders,
        tender_success_rate=round(closed_with_awards / closed_tenders, 4) if closed_tenders else 0.0,
    )


# --------------------------------------------------------------------------- trends


def _trends(db: Session) -> list[TrendPoint]:
    month_expr = func.to_char(Tender.published_date, "YYYY-MM")
    tender_rows = db.execute(
        select(
            month_expr,
            func.count(Tender.id),
            func.coalesce(func.sum(Tender.estimated_value), 0),
        )
        .where(Tender.published_date.is_not(None))
        .group_by(month_expr)
        .order_by(month_expr.desc())
        .limit(24)
    ).all()

    award_month = func.to_char(Award.award_date, "YYYY-MM")
    award_rows = {
        row[0]: int(row[1])
        for row in db.execute(
            select(award_month, func.count(Award.id))
            .where(Award.award_date.is_not(None))
            .group_by(award_month)
        ).all()
    }

    points = [
        TrendPoint(period=period, tenders=int(tenders), awards=award_rows.get(period, 0), value=value)
        for period, tenders, value in tender_rows
    ]
    return list(reversed(points))


def _category_trends(db: Session, top_n: int) -> list[CategoryTrend]:
    """Category trends derived from tender titles keyword-bucketed.

    We do not have a dedicated category column, so buckets come from title
    keywords. Every count is a real tender count — uncategorised tenders are
    honestly reported under "Other".
    """
    buckets: dict[str, tuple[int, Decimal]] = defaultdict(lambda: (0, Decimal("0")))
    rows = db.execute(select(Tender.title, Tender.estimated_value)).all()
    for title, value in rows:
        category = _category_of(title)
        count, total = buckets[category]
        buckets[category] = (count + 1, total + (value or Decimal("0")))
    trends = [
        CategoryTrend(category=name, tenders=count, value=total)
        for name, (count, total) in buckets.items()
    ]
    trends.sort(key=lambda item: item.tenders, reverse=True)
    return trends[:top_n]


_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Construction & Roads", ("road", "bridge", "construction", "building", "civil", "infrastructure")),
    ("Electrical & Power", ("electric", "power", "transformer", "solar", "energy", "lighting", "cable")),
    ("Medical & Health", ("medical", "hospital", "medicine", "drug", "health", "surgical", "equipment")),
    ("IT & Software", ("software", "computer", "server", "network", "it ", "laptop", "hardware")),
    ("Water & Sanitation", ("water", "sewer", "sanitation", "pipe", "drainage", "pump")),
    ("Supply & Goods", ("supply", "procurement of", "purchase", "goods", "material")),
    ("Consultancy & Services", ("consultancy", "consultant", "service", "maintenance", "repair")),
)


def _category_of(title: str | None) -> str:
    text = (title or "").casefold()
    for label, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return label
    return "Other"


def _state_trends(db: Session) -> list[StateTrend]:
    award_counts: dict = {
        row[0]: int(row[1])
        for row in db.execute(
            select(Award.tender_id, func.count(Award.id)).group_by(Award.tender_id)
        ).all()
    }
    rows = db.execute(
        select(Tender.id, Tender.title, Tender.procuring_entity, Tender.estimated_value)
    ).all()

    tenders: dict[str, int] = defaultdict(int)
    values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    awards: dict[str, int] = defaultdict(int)
    for tender_id, title, buyer, value in rows:
        state = _state_of(buyer, title)
        tenders[state] += 1
        values[state] += value or Decimal("0")
        awards[state] += award_counts.get(tender_id, 0)

    trends = [
        StateTrend(state=state, tenders=count, awards=awards[state], value=values[state])
        for state, count in tenders.items()
    ]
    trends.sort(key=lambda item: item.tenders, reverse=True)
    return trends


def _state_of(buyer: str | None, title: str | None) -> str:
    haystack = f"{buyer or ''} {title or ''}".casefold()
    for state in INDIAN_STATES:
        if state.casefold() in haystack:
            return state
    return UNATTRIBUTED


def _source_coverage(db: Session) -> list[SourceCoverage]:
    label = func.coalesce(Tender.source_name, "unknown")
    rows = db.execute(
        select(label, func.count(Tender.id)).group_by(label)
    ).all()
    coverage = [
        SourceCoverage(
            source_name=name,
            label=_SOURCE_LABELS.get(name, name),
            tenders=int(count),
            is_indian=is_indian_source(name),
            priority_rank=source_rank(name),
        )
        for name, count in rows
    ]
    # Indian-first ordering.
    coverage.sort(key=lambda item: (item.priority_rank, -item.tenders))
    return coverage
