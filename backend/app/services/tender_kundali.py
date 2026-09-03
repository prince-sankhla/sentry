from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from statistics import quantiles
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Award, Document, SourceRecordVersion, Tender
from app.schemas.tender_kundali import (
    KundaliAward,
    KundaliBenchmark,
    KundaliComparableTender,
    KundaliDocument,
    KundaliSignal,
    KundaliSourceSnapshot,
    KundaliSupplierHistory,
    TenderKundaliResponse,
)

_INTERNATIONAL_SOURCES = {"world_bank", "adb", "un_procurement", "prozorro"}


def build_tender_kundali(db: Session, tender_id: UUID) -> TenderKundaliResponse | None:
    tender = db.execute(
        select(Tender)
        .where(Tender.id == tender_id, Tender.source_name.notin_(_INTERNATIONAL_SOURCES))
        .options(
            selectinload(Tender.awards).joinedload(Award.company),
            selectinload(Tender.documents),
        )
    ).unique().scalar_one_or_none()
    if tender is None:
        return None

    source_snapshot = _source_snapshot(db, tender)
    documents = _documents(tender.documents)
    awards = _awards(tender.awards)
    comparable = _comparables(db, tender)
    benchmark = _benchmark(tender, comparable)
    supplier_history = _supplier_history(db, awards)
    signals = _signals(tender, awards, documents, comparable, benchmark)

    evidence_summary = {
        "source_snapshots": int(source_snapshot.content_hash is not None),
        "documents": len(documents),
        "awards": len(awards),
        "comparables": len(comparable),
        "supplier_histories": len(supplier_history),
        "verified_documents": sum(1 for d in documents if d.evidence_hash or d.content_hash),
    }
    limitations = [
        "CPPP/GeM public tender pages are winner/tender-centric; individual bidder identities and bid amounts are shown only when the source actually provides them.",
        "Comparable-tender benchmarking is descriptive context, not a fraud determination or a statutory threshold.",
    ]
    return TenderKundaliResponse(
        tender_id=str(tender.id),
        reference_number=tender.reference_number,
        title=tender.title,
        status=_status(tender, source_snapshot.retrieved_at),
        as_of=source_snapshot.retrieved_at,
        buyer=tender.procuring_entity,
        procurement_method=tender.procurement_method,
        category=tender.category,
        geography=tender.geography,
        estimated_value=tender.estimated_value,
        currency=tender.currency,
        published_date=tender.published_date,
        closing_date=tender.closing_date,
        source=source_snapshot,
        documents=documents,
        document_summary=dict(Counter(d.document_type for d in documents)),
        awards=awards,
        comparable_tenders=comparable,
        benchmark=benchmark,
        supplier_history=supplier_history,
        signals=signals,
        evidence_summary=evidence_summary,
        limitations=limitations,
    )


def _status(tender: Tender, as_of: datetime | None) -> str:
    pivot = as_of.date() if as_of is not None else date.today()
    if tender.closing_date and tender.closing_date < pivot:
        return "closed"
    if tender.published_date and tender.published_date > pivot:
        return "scheduled"
    return "open"


def _source_snapshot(db: Session, tender: Tender) -> KundaliSourceSnapshot:
    latest = None
    if tender.source_name and tender.source_record_id:
        latest = db.scalar(
            select(SourceRecordVersion)
            .where(
                SourceRecordVersion.source_name == tender.source_name,
                SourceRecordVersion.source_record_id == tender.source_record_id,
            )
            .order_by(SourceRecordVersion.retrieved_at.desc().nullslast(), SourceRecordVersion.imported_at.desc())
            .limit(1)
        )
    return KundaliSourceSnapshot(
        source_name=tender.source_name or "unknown",
        source_record_id=tender.source_record_id or tender.reference_number,
        source_url=tender.source_url,
        content_hash=latest.content_hash if latest else None,
        retrieved_at=latest.retrieved_at if latest else tender.retrieved_at,
        action=latest.action if latest else None,
    )


def _documents(documents: list[Document]) -> list[KundaliDocument]:
    return [
        KundaliDocument(
            id=str(document.id),
            title=document.title,
            document_type=document.document_type,
            url=document.url or document.source_url,
            retrieved_at=document.retrieved_at,
            content_hash=document.content_hash,
            evidence_hash=document.evidence_hash,
            available=bool(document.url or document.local_path),
        )
        for document in documents
    ]


def _awards(awards: list[Award]) -> list[KundaliAward]:
    result: list[KundaliAward] = []
    for award in awards:
        if award.company is None:
            continue
        result.append(
            KundaliAward(
                id=str(award.id),
                supplier_id=str(award.company_id),
                supplier_name=award.company.name,
                award_date=award.award_date,
                award_value=award.award_value,
                currency=award.currency,
                source_name=award.source_name,
                source_url=award.source_url,
            )
        )
    return result


def _comparables(db: Session, tender: Tender) -> list[KundaliComparableTender]:
    candidates = db.scalars(
        select(Tender)
        .where(Tender.id != tender.id, Tender.source_name.notin_(_INTERNATIONAL_SOURCES))
        .options(selectinload(Tender.awards).joinedload(Award.company))
        .limit(2000)
    ).unique().all()
    ranked: list[tuple[int, Tender]] = []
    buyer = _fold(tender.procuring_entity)
    for candidate in candidates:
        score = 0
        reasons: list[str] = []
        if buyer and buyer == _fold(candidate.procuring_entity):
            score += 4; reasons.append("same buyer")
        if tender.category and tender.category.casefold() == (candidate.category or "").casefold():
            score += 3; reasons.append("same category")
        if tender.procurement_method and tender.procurement_method.casefold() == (candidate.procurement_method or "").casefold():
            score += 2; reasons.append("same procurement method")
        if tender.currency == candidate.currency:
            score += 1
        if tender.estimated_value and candidate.estimated_value:
            ratio = max(tender.estimated_value, candidate.estimated_value) / min(tender.estimated_value, candidate.estimated_value)
            if ratio <= Decimal("2"):
                score += 2; reasons.append("similar value band")
        if score >= 5:
            ranked.append((score, candidate))
    ranked.sort(key=lambda item: (item[0], item[1].published_date or date.min), reverse=True)
    result: list[KundaliComparableTender] = []
    for score, candidate in ranked[:12]:
        award = next((a for a in candidate.awards if a.company is not None), None)
        result.append(
            KundaliComparableTender(
                id=str(candidate.id),
                reference_number=candidate.reference_number,
                title=candidate.title,
                buyer=candidate.procuring_entity,
                category=candidate.category,
                procurement_method=candidate.procurement_method,
                published_date=candidate.published_date,
                estimated_value=candidate.estimated_value,
                currency=candidate.currency,
                similarity_reasons=[f"match score {score}", *([] if not score else [])] + _similarity_reasons(tender, candidate),
                award_supplier=award.company.name if award and award.company else None,
                award_value=award.award_value if award else None,
            )
        )
    return result


def _similarity_reasons(a: Tender, b: Tender) -> list[str]:
    reasons: list[str] = []
    if a.procuring_entity and _fold(a.procuring_entity) == _fold(b.procuring_entity): reasons.append("same buyer")
    if a.category and a.category.casefold() == (b.category or "").casefold(): reasons.append("same category")
    if a.procurement_method and a.procurement_method.casefold() == (b.procurement_method or "").casefold(): reasons.append("same method")
    return reasons


def _benchmark(tender: Tender, comparable: list[KundaliComparableTender]) -> KundaliBenchmark:
    values = sorted([c.estimated_value for c in comparable if c.estimated_value is not None and c.currency == tender.currency])
    if not values:
        return KundaliBenchmark(sample_size=0, median=None, p25=None, p75=None, min_value=None, max_value=None, tender_percentile=None, position="insufficient", basis=["same-buyer/category/method comparable set"])
    median = values[len(values) // 2]
    if len(values) >= 4:
        qs = quantiles(values, n=4, method="inclusive")
        p25, p75 = qs[0], qs[2]
    else:
        p25 = values[0]
        p75 = values[-1]
    t = tender.estimated_value
    percentile = None
    if t is not None:
        percentile = round(100.0 * sum(1 for v in values if v <= t) / len(values), 1)
    position = "within comparable range"
    if t is not None and t < p25: position = "below P25"
    elif t is not None and t > p75: position = "above P75"
    return KundaliBenchmark(
        sample_size=len(values), median=median, p25=p25, p75=p75,
        min_value=values[0], max_value=values[-1], tender_percentile=percentile,
        position=position, basis=["Indian records only", "same buyer/category/method/value similarity", "descriptive benchmark"]
    )


def _supplier_history(db: Session, awards: list[KundaliAward]) -> list[KundaliSupplierHistory]:
    if not awards:
        return []
    ids = [UUID(a.supplier_id) for a in awards]
    rows = db.execute(
        select(Award).where(Award.company_id.in_(ids)).options(joinedload(Award.company), joinedload(Award.tender))
    ).unique().scalars().all()
    grouped: dict[UUID, list[Award]] = defaultdict(list)
    for row in rows:
        grouped[row.company_id].append(row)
    result: list[KundaliSupplierHistory] = []
    for supplier_id in ids:
        history = grouped.get(supplier_id, [])
        if not history:
            continue
        company = history[0].company
        buyer_names = sorted({a.tender.procuring_entity for a in history if a.tender and a.tender.procuring_entity})
        dates = [a.award_date for a in history if a.award_date]
        result.append(KundaliSupplierHistory(
            supplier_id=str(supplier_id),
            supplier_name=company.name,
            award_count=len(history),
            total_award_value=sum((a.award_value for a in history if a.award_value is not None), Decimal("0")),
            buyer_count=len(buyer_names),
            buyer_names=buyer_names[:12],
            first_award_date=min(dates) if dates else None,
            latest_award_date=max(dates) if dates else None,
            tender_references=[a.tender.reference_number for a in history if a.tender][:20],
        ))
    return result


def _signals(tender: Tender, awards: list[KundaliAward], documents: list[KundaliDocument], comparables: list[KundaliComparableTender], benchmark: KundaliBenchmark) -> list[KundaliSignal]:
    signals: list[KundaliSignal] = []
    if tender.estimated_value and benchmark.position in {"above P75", "below P25"}:
        signals.append(KundaliSignal(type="benchmark_position", severity="medium", title="Value outside comparable central range", summary=f"Tender estimate is {benchmark.position} of the comparable Indian sample.", evidence=[f"Tender estimate: {tender.estimated_value} {tender.currency}", f"P25: {benchmark.p25}", f"P75: {benchmark.p75}"], supported_by=["historical comparable tenders"], review_required=True))
    if awards and tender.estimated_value:
        for award in awards:
            if award.award_value and award.award_value > tender.estimated_value * Decimal("2"):
                signals.append(KundaliSignal(type="award_value_exceeds_tender", severity="high", title="Award substantially exceeds tender estimate", summary=f"Recorded award is {award.award_value / tender.estimated_value:.1f}× the tender estimate.", evidence=[f"Estimate: {tender.estimated_value}", f"Award: {award.award_value}"], supported_by=["official award record"], review_required=True))
    if not documents:
        signals.append(KundaliSignal(type="missing_documents", severity="low", title="No documents indexed", summary="No tender documents are currently linked to this tender record.", evidence=["Document count: 0"], supported_by=["SENTRY source index"], review_required=True))
    if len(awards) > 1:
        signals.append(KundaliSignal(type="multiple_awards", severity="low", title="Multiple recorded awards", summary=f"This tender has {len(awards)} recorded award rows.", evidence=[f"Award rows: {len(awards)}"], supported_by=["official award records"], review_required=False))
    return signals


def _fold(value: str | None) -> str:
    return " ".join((value or "").casefold().split())
