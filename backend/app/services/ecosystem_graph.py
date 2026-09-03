from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Company, Document, Tender
from app.schemas.ecosystem_graph import (
    EcosystemEdge,
    EcosystemGraphResponse,
    EcosystemNode,
    RelationshipSignal,
)
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES


def _buyer_id(name: str | None) -> str:
    return f"buyer:{(name or 'unknown buyer').strip().casefold()}"


def _category_id(category: str | None) -> str:
    return f"category:{(category or 'unknown').strip().casefold()}"


def build_ecosystem_graph(
    db: Session,
    company_id: UUID | None = None,
    tender_id: UUID | None = None,
    buyer: str | None = None,
    depth: int = 2,
) -> EcosystemGraphResponse:
    """Build an India-scoped procurement ecosystem graph.

    This is an investigation projection, not a generic visualization. Every
    relationship is backed by a tender, award, document or explicitly linked
    evidence record. Award records do not imply competitive participation when
    bidder-level data is unavailable.
    """
    tenders = [
        t for t in db.scalars(select(Tender)).all()
        if t.source_name not in INTERNATIONAL_PROCUREMENT_SOURCES
    ]
    tender_ids = {t.id for t in tenders}

    awards = db.execute(
        select(Award).options(joinedload(Award.company), joinedload(Award.tender))
    ).unique().scalars().all()
    awards = [a for a in awards if a.tender_id in tender_ids and a.company is not None]

    if company_id:
        connected = {a.tender_id for a in awards if a.company_id == company_id}
        tenders = [t for t in tenders if t.id in connected]
        tender_ids = {t.id for t in tenders}
        awards = [a for a in awards if a.tender_id in tender_ids]
    if tender_id:
        tenders = [t for t in tenders if t.id == tender_id]
        tender_ids = {t.id for t in tenders}
        awards = [a for a in awards if a.tender_id in tender_ids]
    if buyer:
        key = buyer.strip().casefold()
        tenders = [t for t in tenders if (t.procuring_entity or '').strip().casefold() == key]
        tender_ids = {t.id for t in tenders}
        awards = [a for a in awards if a.tender_id in tender_ids]

    tenders.sort(
        key=lambda t: (t.published_date is not None, t.published_date, str(t.id)),
        reverse=True,
    )
    tenders = tenders[:500]
    tender_ids = {t.id for t in tenders}
    awards = [a for a in awards if a.tender_id in tender_ids]

    nodes: dict[str, EcosystemNode] = {}
    edges: dict[str, EcosystemEdge] = {}
    buyer_company_awards: defaultdict[tuple[str, UUID], list[Award]] = defaultdict(list)
    buyer_awards: defaultdict[str, list[Award]] = defaultdict(list)

    def node(node_id: str, node_type: str, label: str, **data) -> None:
        nodes.setdefault(node_id, EcosystemNode(id=node_id, type=node_type, label=label[:200], data=data))

    def edge(source: str, target: str, edge_type: str, label: str, **data) -> None:
        edge_id = f"{edge_type}:{source}->{target}"
        edges.setdefault(
            edge_id,
            EcosystemEdge(id=edge_id, source=source, target=target, type=edge_type, label=label, data=data),
        )

    for tender in tenders:
        tid = f"tender:{tender.id}"
        node(
            tid, "tender", tender.title or tender.reference_number,
            reference_number=tender.reference_number,
            buyer=tender.procuring_entity,
            estimated_value=str(tender.estimated_value) if tender.estimated_value is not None else None,
            procurement_method=tender.procurement_method,
            category=tender.category,
            geography=tender.geography,
            source=tender.source_name,
            source_url=tender.source_url,
        )
        bid = _buyer_id(tender.procuring_entity)
        node(bid, "buyer", tender.procuring_entity or "Unknown buyer")
        edge(bid, tid, "buyer_tender", "issued")
        if tender.category:
            cid = _category_id(tender.category)
            node(cid, "category", tender.category)
            edge(cid, tid, "category_tender", "classified as")

    companies: dict[UUID, Company] = {a.company_id: a.company for a in awards if a.company is not None}
    for award in awards:
        tid = f"tender:{award.tender_id}"
        aid = f"award:{award.id}"
        cid = f"company:{award.company_id}"
        node(
            cid, "company", award.company.name,
            database_id=str(award.company_id),
            registration_number=award.company.registration_number,
        )
        node(
            aid, "award", f"Award — {award.company.name}",
            database_id=str(award.id),
            award_value=str(award.award_value) if award.award_value is not None else None,
            currency=award.currency,
            award_date=award.award_date.isoformat() if award.award_date else None,
            source=award.source_name,
            source_url=award.source_url,
        )
        edge(tid, aid, "tender_award", "awarded")
        edge(aid, cid, "award_company", "to")
        bid = _buyer_id(award.tender.procuring_entity if award.tender else None)
        buyer_company_awards[(bid, award.company_id)].append(award)
        buyer_awards[bid].append(award)

    documents = [d for d in db.scalars(select(Document)).all() if d.tender_id in tender_ids]
    for document in documents:
        did = f"document:{document.id}"
        node(
            did, "document", document.title or document.document_type or "Document",
            database_id=str(document.id),
            document_type=document.document_type,
            url=document.url,
            source=getattr(document, "source_name", None),
            source_url=getattr(document, "source_url", None),
        )
        edge(did, f"tender:{document.tender_id}", "document_tender", "supports")

    from app.webintel.models import WebProcurementEvidence

    web_rows = db.execute(
        select(WebProcurementEvidence).options(joinedload(WebProcurementEvidence.web_evidence))
    ).unique().scalars().all()
    for row in web_rows:
        if row.tender_id not in tender_ids:
            continue
        web = row.web_evidence
        eid = f"evidence:{row.id}"
        node(
            eid, "evidence", (web.title if web else None) or row.tender_title or "Evidence",
            database_id=str(row.id),
            source=web.source if web else None,
            source_url=web.url if web else None,
            company_id=str(row.company_id) if row.company_id else None,
            award_id=str(row.award_id) if row.award_id else None,
        )
        edge(eid, f"tender:{row.tender_id}", "evidence_tender", "supports")
        if row.company_id:
            edge(eid, f"company:{row.company_id}", "evidence_company", "mentions")

    signals: list[RelationshipSignal] = []
    for (bid, cid), rows in buyer_company_awards.items():
        buyer_name = next(
            (t.procuring_entity for t in tenders if _buyer_id(t.procuring_entity) == bid),
            "Unknown buyer",
        )
        company = companies.get(rows[0].company_id)
        if not company:
            continue
        if len(rows) >= 2:
            edge(
                bid, cid, "buyer_company", "repeat award relationship",
                award_count=len(rows), relationship_basis="award records",
            )
            signals.append(RelationshipSignal(
                code="repeat_buyer_supplier",
                title="Repeat buyer–supplier relationship",
                severity="review",
                summary=f"{company.name} has {len(rows)} recorded awards from {buyer_name} in the indexed Indian records.",
                evidence=["Relationship is derived from award records.", "This does not establish misconduct or bid coordination."],
                confidence="high",
            ))
        buyer_rows = buyer_awards.get(bid, [])
        if len(buyer_rows) >= 3 and len(rows) / Decimal(len(buyer_rows)) >= Decimal("0.60"):
            edge(
                bid, cid, "buyer_company", "concentrated award relationship",
                award_count=len(rows), buyer_award_count=len(buyer_rows), share=str(len(rows) / Decimal(len(buyer_rows))),
            )
            signals.append(RelationshipSignal(
                code="supplier_award_concentration",
                title="Supplier award concentration",
                severity="notable",
                summary=f"{company.name} accounts for {len(rows)}/{len(buyer_rows)} recorded awards for this buyer.",
                evidence=["Share is calculated from indexed award records only."],
                confidence="high",
            ))

    unique = {(s.code, s.summary): s for s in signals}
    limitations = [
        "Indian procurement scope excludes configured international procurement sources.",
        "Award records are not treated as bidder participation; bidder-level conclusions require bidder-level source data.",
        "Relationship signals are review leads, not findings of wrongdoing.",
        "Missing or unlinked evidence is not interpreted as negative evidence.",
    ]
    return EcosystemGraphResponse(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        relationship_signals=list(unique.values())[:100],
        limitations=limitations,
        scope={
            "jurisdiction": "India",
            "depth": depth,
            "tender_count": len(tenders),
            "award_count": len(awards),
            "company_count": len(companies),
        },
    )
