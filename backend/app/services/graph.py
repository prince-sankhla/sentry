from __future__ import annotations

import hashlib
from collections import deque
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Company, Tender
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse
from app.webintel.models import WebEvidence, WebProcurementEvidence

HIGH_VALUE_THRESHOLD = Decimal("10000000")
SHORT_SUBMISSION_DAYS = 7


def build_relationship_graph(
    db: Session,
    company_id: UUID | None = None,
    tender_id: UUID | None = None,
    depth: int = 2,
) -> GraphResponse:
    awards = db.execute(
        select(Award).options(joinedload(Award.company), joinedload(Award.tender))
    ).unique().scalars().all()
    companies = db.scalars(select(Company)).all()
    tenders = db.scalars(select(Tender)).all()
    web_procurement_evidence = db.execute(
        select(WebProcurementEvidence)
        .options(joinedload(WebProcurementEvidence.web_evidence))
    ).unique().scalars().all()

    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    for company in companies:
        company_node_id = _node_id("company", company.id)
        nodes.setdefault(
            company_node_id,
            GraphNode(
                id=company_node_id,
                type="company",
                label=company.name,
                data={
                    "database_id": str(company.id),
                    "registration_number": company.registration_number,
                    "created_at": _serialize(company.created_at),
                },
            ),
        )

    for tender in tenders:
        tender_node_id = _node_id("tender", tender.id)
        buyer_node_id = _buyer_node_id(tender.procuring_entity)
        nodes.setdefault(
            tender_node_id,
            GraphNode(
                id=tender_node_id,
                type="tender",
                label=tender.title,
                data={
                    "database_id": str(tender.id),
                    "reference_number": tender.reference_number,
                    "procuring_entity": tender.procuring_entity,
                    "published_date": _serialize(tender.published_date),
                    "estimated_value": _serialize(tender.estimated_value),
                    "currency": tender.currency,
                },
            ),
        )
        if tender.source_url:
            document_node_id = _document_node_id(tender.source_url)
            nodes.setdefault(
                document_node_id,
                GraphNode(
                    id=document_node_id,
                    type="document",
                    label=tender.source_name or "Tender source document",
                    data={
                        "summary": "Source document linked to this tender record.",
                        "source": tender.source_name,
                        "source_url": tender.source_url,
                        "related_tender": str(tender.id),
                        "timeline": _compact_timeline([("Retrieved", tender.retrieved_at), ("Published", tender.published_date)]),
                    },
                ),
            )
            _add_edge(edges, source=document_node_id, target=tender_node_id, edge_type="document_tender", label="belongs to")

        nodes.setdefault(
            buyer_node_id,
            GraphNode(
                id=buyer_node_id,
                type="buyer",
                label=tender.procuring_entity or "Unknown buyer",
                data={
                    "name": tender.procuring_entity,
                },
            ),
        )
        _add_edge(
            edges,
            source=buyer_node_id,
            target=tender_node_id,
            edge_type="buyer_tender",
            label="published",
        )

    for award in awards:
        if award.company is None or award.tender is None:
            continue

        company_node_id = _node_id("company", award.company.id)
        tender_node_id = _node_id("tender", award.tender.id)
        award_node_id = _node_id("award", award.id)

        nodes.setdefault(
            award_node_id,
            GraphNode(
                id=award_node_id,
                type="award",
                label=f"Award {award.award_value or 'unknown'} {award.currency}",
                data={
                    "database_id": str(award.id),
                    "award_date": _serialize(award.award_date),
                    "award_value": _serialize(award.award_value),
                    "currency": award.currency,
                },
            ),
        )
        _add_edge(
            edges,
            source=company_node_id,
            target=tender_node_id,
            edge_type="company_tender",
            label="participated in",
        )
        _add_edge(
            edges,
            source=tender_node_id,
            target=award_node_id,
            edge_type="tender_award",
            label="has award",
        )
        _add_edge(
            edges,
            source=award_node_id,
            target=company_node_id,
            edge_type="award_company",
            label="awarded to",
        )

    _add_procurement_indicators(nodes, edges, tenders, awards)
    _add_web_evidence_nodes(nodes, edges, web_procurement_evidence)

    seed_node_ids = _seed_node_ids(company_id=company_id, tender_id=tender_id)
    if seed_node_ids:
        return _filter_graph(nodes, edges, seed_node_ids, depth)

    return GraphResponse(nodes=list(nodes.values()), edges=list(edges.values()))


def _seed_node_ids(company_id: UUID | None, tender_id: UUID | None) -> set[str]:
    seed_ids = set()
    if company_id is not None:
        seed_ids.add(_node_id("company", company_id))
    if tender_id is not None:
        seed_ids.add(_node_id("tender", tender_id))
    return seed_ids


def _filter_graph(
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    seed_node_ids: set[str],
    depth: int,
) -> GraphResponse:
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for edge in edges.values():
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)

    visited = {seed for seed in seed_node_ids if seed in nodes}
    queue = deque((seed, 0) for seed in visited)
    while queue:
        node_id, distance = queue.popleft()
        if distance >= depth:
            continue
        for next_node_id in adjacency.get(node_id, set()):
            if next_node_id in visited:
                continue
            visited.add(next_node_id)
            queue.append((next_node_id, distance + 1))

    filtered_edges = [
        edge for edge in edges.values() if edge.source in visited and edge.target in visited
    ]
    return GraphResponse(
        nodes=[nodes[node_id] for node_id in visited],
        edges=filtered_edges,
    )


def _node_id(node_type: str, identifier: UUID) -> str:
    return f"{node_type}:{identifier}"


def _buyer_node_id(name: str | None) -> str:
    normalized = (name or "unknown buyer").strip().lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"buyer:{digest}"


def _add_edge(
    edges: dict[str, GraphEdge],
    source: str,
    target: str,
    edge_type: str,
    label: str,
) -> None:
    edge_id = f"{edge_type}:{source}->{target}"
    edges.setdefault(
        edge_id,
        GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            type=edge_type,  # type: ignore[arg-type]
            label=label,
        ),
    )


def _add_procurement_indicators(
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    tenders: list[Tender],
    awards: list[Award],
) -> None:
    awards_by_tender: dict[UUID, list[Award]] = {}
    awards_by_buyer_company: dict[tuple[str, UUID], list[Award]] = {}
    awards_by_buyer: dict[str, list[Award]] = {}
    for award in awards:
        if award.tender is None or award.company is None:
            continue
        awards_by_tender.setdefault(award.tender_id, []).append(award)
        buyer_key = _buyer_key(award.tender.procuring_entity)
        awards_by_buyer.setdefault(buyer_key, []).append(award)
        awards_by_buyer_company.setdefault((buyer_key, award.company_id), []).append(award)

    for tender in tenders:
        tender_node_id = _node_id("tender", tender.id)
        buyer_node_id = _buyer_node_id(tender.procuring_entity)

        if tender.estimated_value is not None and tender.estimated_value >= HIGH_VALUE_THRESHOLD:
            _add_indicator(
                nodes,
                edges,
                indicator_key=f"high_value:{tender.id}",
                title="High Value Procurement",
                finding=f"Tender value is {tender.estimated_value} {tender.currency}, above the configured high-value threshold.",
                supporting_evidence=f"Estimated value: {tender.estimated_value} {tender.currency}.",
                source=tender.source_name or "procurement_record",
                source_url=tender.source_url,
                tender=tender,
                buyer=tender.procuring_entity,
                related_node_id=tender_node_id,
                related_edge_type="tender_indicator",
                timeline=[("Published", tender.published_date), ("Closing", tender.closing_date), ("Retrieved", tender.retrieved_at)],
            )

        if tender.published_date and tender.closing_date:
            submission_days = (tender.closing_date - tender.published_date).days
            if 0 <= submission_days <= SHORT_SUBMISSION_DAYS:
                _add_indicator(
                    nodes,
                    edges,
                    indicator_key=f"short_submission:{tender.id}",
                    title="Short Submission Window",
                    finding=f"Tender submission window was {submission_days} days.",
                    supporting_evidence=f"Published on {tender.published_date.isoformat()} and closed on {tender.closing_date.isoformat()}.",
                    source=tender.source_name or "procurement_record",
                    source_url=tender.source_url,
                    tender=tender,
                    buyer=tender.procuring_entity,
                    related_node_id=tender_node_id,
                    related_edge_type="tender_indicator",
                    timeline=[("Published", tender.published_date), ("Closing", tender.closing_date), ("Retrieved", tender.retrieved_at)],
                )

        tender_awards = awards_by_tender.get(tender.id, [])
        if len({award.company_id for award in tender_awards}) == 1 and len(tender_awards) > 1:
            company = tender_awards[0].company
            if company is not None:
                _add_indicator(
                    nodes,
                    edges,
                    indicator_key=f"single_awarded_supplier:{tender.id}",
                    title="Single Awarded Supplier",
                    finding="All available award records for this tender point to one supplier.",
                    supporting_evidence=f"{len(tender_awards)} award records link tender {tender.reference_number} to {company.name}.",
                    source=tender.source_name or "procurement_record",
                    source_url=tender.source_url,
                    tender=tender,
                    company=company,
                    buyer=tender.procuring_entity,
                    related_node_id=tender_node_id,
                    related_edge_type="tender_indicator",
                    timeline=[("Published", tender.published_date), ("Closing", tender.closing_date), ("Retrieved", tender.retrieved_at)],
                )

    for (buyer_key, company_id), supplier_awards in awards_by_buyer_company.items():
        if len(supplier_awards) < 2:
            continue
        company = supplier_awards[0].company
        buyer_name = supplier_awards[0].tender.procuring_entity if supplier_awards[0].tender else buyer_key
        if company is None:
            continue
        company_node_id = _node_id("company", company.id)
        buyer_node_id = _buyer_node_id(buyer_name)
        _add_edge(edges, source=buyer_node_id, target=company_node_id, edge_type="buyer_company", label="previously awarded")
        _add_indicator(
            nodes,
            edges,
            indicator_key=f"repeat_supplier:{buyer_key}:{company.id}",
            title="Repeat Supplier",
            finding=f"{company.name} has multiple awards from {buyer_name or 'the same buyer'}.",
            supporting_evidence=f"{len(supplier_awards)} awards from the same buyer to this supplier are present in procurement records.",
            source="procurement_records",
            source_url=_first_url([award.source_url for award in supplier_awards]),
            company=company,
            buyer=buyer_name,
            related_node_id=company_node_id,
            related_edge_type="company_indicator",
            timeline=[("First award", min((award.award_date for award in supplier_awards if award.award_date), default=None)), ("Latest award", max((award.award_date for award in supplier_awards if award.award_date), default=None))],
        )

        buyer_awards = awards_by_buyer.get(buyer_key, [])
        if len(buyer_awards) >= 3 and len(supplier_awards) / len(buyer_awards) >= 0.6:
            _add_indicator(
                nodes,
                edges,
                indicator_key=f"award_concentration:{buyer_key}:{company.id}",
                title="High Award Concentration",
                finding=f"{company.name} accounts for {len(supplier_awards)} of {len(buyer_awards)} known awards from {buyer_name or 'this buyer'}.",
                supporting_evidence="Award concentration is calculated from existing award records for the same buyer.",
                source="procurement_records",
                source_url=_first_url([award.source_url for award in supplier_awards]),
                company=company,
                buyer=buyer_name,
                related_node_id=company_node_id,
                related_edge_type="company_indicator",
                timeline=[("First award", min((award.award_date for award in supplier_awards if award.award_date), default=None)), ("Latest award", max((award.award_date for award in supplier_awards if award.award_date), default=None))],
            )


def _add_indicator(
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    *,
    indicator_key: str,
    title: str,
    finding: str,
    supporting_evidence: str,
    source: str,
    source_url: str | None,
    related_node_id: str,
    related_edge_type: str,
    timeline: list[tuple[str, date | datetime | None]],
    tender: Tender | None = None,
    company: Company | None = None,
    buyer: str | None = None,
) -> None:
    indicator_node_id = f"indicator:{hashlib.sha1(indicator_key.encode('utf-8')).hexdigest()[:16]}"
    evidence_node_id = f"evidence:{hashlib.sha1((indicator_key + ':evidence').encode('utf-8')).hexdigest()[:16]}"
    nodes.setdefault(
        indicator_node_id,
        GraphNode(
            id=indicator_node_id,
            type="indicator",
            label=title,
            data={
                "summary": finding,
                "title": title,
                "finding": finding,
                "supporting_evidence": supporting_evidence,
                "source": source,
                "source_url": source_url,
                "related_tender": tender.title if tender else None,
                "related_company": company.name if company else None,
                "related_buyer": buyer,
                "documents": [source_url] if source_url else [],
                "timeline": _compact_timeline(timeline),
            },
        ),
    )
    nodes.setdefault(
        evidence_node_id,
        GraphNode(
            id=evidence_node_id,
            type="evidence",
            label=supporting_evidence,
            data={
                "summary": supporting_evidence,
                "source": source,
                "source_url": source_url,
                "related_tender": tender.title if tender else None,
                "related_company": company.name if company else None,
                "related_buyer": buyer,
                "documents": [source_url] if source_url else [],
                "timeline": _compact_timeline(timeline),
            },
        ),
    )
    _add_edge(edges, source=related_node_id, target=indicator_node_id, edge_type=related_edge_type, label="has finding")
    _add_edge(edges, source=evidence_node_id, target=indicator_node_id, edge_type="evidence_indicator", label="supports")


def _add_web_evidence_nodes(
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    evidence_rows: list[WebProcurementEvidence],
) -> None:
    for evidence in evidence_rows:
        web = evidence.web_evidence
        if web is None:
            continue
        web_node_id = _node_id("web_evidence", web.id)
        nodes.setdefault(
            web_node_id,
            GraphNode(
                id=web_node_id,
                type="web_evidence",
                label=web.title or web.source,
                data={
                    "summary": evidence.contract_title or evidence.tender_title or evidence.company_name or "Stored web evidence",
                    "source": web.source,
                    "source_url": web.url,
                    "related_tender": str(evidence.tender_id) if evidence.tender_id else evidence.tender_title,
                    "related_company": str(evidence.company_id) if evidence.company_id else evidence.company_name,
                    "related_buyer": evidence.government_buyer,
                    "documents": [web.url],
                    "timeline": _compact_timeline([("Retrieved", web.retrieved_at), ("Published", evidence.publication_date), ("Award", evidence.award_date)]),
                },
            ),
        )
        if evidence.company_id:
            _add_edge(edges, source=web_node_id, target=_node_id("company", evidence.company_id), edge_type="web_evidence_company", label="references")
        if evidence.tender_id:
            _add_edge(edges, source=_node_id("tender", evidence.tender_id), target=web_node_id, edge_type="tender_evidence", label="has evidence")
            _add_edge(edges, source=web_node_id, target=_node_id("tender", evidence.tender_id), edge_type="web_evidence_tender", label="references")
        if evidence.award_id:
            _add_edge(edges, source=web_node_id, target=_node_id("award", evidence.award_id), edge_type="web_evidence_award", label="references")
        category = evidence.procurement_sector or evidence.tender_category
        if category and evidence.tender_id:
            category_node_id = _text_node_id("category", category)
            nodes.setdefault(category_node_id, GraphNode(id=category_node_id, type="category", label=category, data={"summary": f"Procurement category: {category}"}))
            _add_edge(edges, source=category_node_id, target=_node_id("tender", evidence.tender_id), edge_type="category_tender", label="contains")
        organization = evidence.organization or evidence.government_buyer
        if organization:
            organization_node_id = _text_node_id("organization", organization)
            nodes.setdefault(organization_node_id, GraphNode(id=organization_node_id, type="organization", label=organization, data={"summary": f"Organization mentioned in web evidence: {organization}"}))
            _add_edge(edges, source=organization_node_id, target=web_node_id, edge_type="organization_evidence", label="mentioned in")


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _buyer_key(name: str | None) -> str:
    return (name or "unknown buyer").strip().casefold()


def _text_node_id(node_type: str, value: str) -> str:
    normalized = value.strip().casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{node_type}:{digest}"


def _document_node_id(url: str) -> str:
    digest = hashlib.sha1(url.strip().casefold().encode("utf-8")).hexdigest()[:16]
    return f"document:{digest}"


def _first_url(values: list[str | None]) -> str | None:
    return next((value for value in values if value), None)


def _compact_timeline(items: list[tuple[str, date | datetime | None]]) -> list[dict[str, str]]:
    return [{"label": label, "date": value.isoformat()} for label, value in items if value is not None]
