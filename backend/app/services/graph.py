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
            label="procured",
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


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value
