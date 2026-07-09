"""Complete investigation graph builder.

The investigation graph must faithfully represent the *entire* Investigation
Package. If the package contains evidence, documents, procurement indicators,
organizations and awards, the graph must contain the corresponding nodes and
relationships — it must never show zero evidence or zero indicator nodes while
the report clearly lists them.

This builder walks the finalized package and emits a typed node/edge set using
the same vocabulary the relationship graph already uses (company, tender, award,
buyer, indicator, evidence, document, organization), so the package graph can be
rendered directly.

Pure projection of package data — it invents nothing; every node traces to a
record, evidence row, indicator or resolved entity already in the package.
"""

from __future__ import annotations

import hashlib

from app.schemas.investigation_executor import (
    InvestigationGraph,
    InvestigationGraphEdge,
    InvestigationGraphNode,
    InvestigationPackage,
)


def _slug(*parts: str) -> str:
    raw = "|".join(p for p in parts if p)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class _GraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, InvestigationGraphNode] = {}
        self.edges: dict[str, InvestigationGraphEdge] = {}

    def add_node(self, node_id: str, node_type: str, label: str, **data) -> str:
        if node_id not in self.nodes:
            self.nodes[node_id] = InvestigationGraphNode(
                id=node_id, type=node_type, label=label[:200] if label else node_type, data=data
            )
        return node_id

    def add_edge(self, source: str, target: str, edge_type: str, label: str = "", **data) -> None:
        edge_id = f"{source}->{target}:{edge_type}"
        if edge_id not in self.edges and source in self.nodes and target in self.nodes:
            self.edges[edge_id] = InvestigationGraphEdge(
                id=edge_id, source=source, target=target, type=edge_type, label=label, data=data
            )

    def build(self) -> InvestigationGraph:
        return InvestigationGraph(nodes=list(self.nodes.values()), edges=list(self.edges.values()))


def build_investigation_graph(pkg: InvestigationPackage) -> InvestigationGraph:
    """Project the complete package into a typed node/edge graph."""
    b = _GraphBuilder()

    # ------------------------------------------------------------------ records
    for record in pkg.records:
        tender = record.tender
        t_id = f"tender:{tender.reference_number}"
        b.add_node(
            t_id, "tender", tender.title or tender.reference_number,
            reference_number=tender.reference_number,
            buyer=tender.procuring_entity,
            estimated_value=str(tender.estimated_value) if tender.estimated_value is not None else None,
            currency=tender.currency,
            published_date=tender.published_date.isoformat() if tender.published_date else None,
            source=tender.metadata.source_name,
        )

        if tender.procuring_entity:
            buyer_id = f"buyer:{tender.procuring_entity.casefold().strip()}"
            b.add_node(buyer_id, "buyer", tender.procuring_entity, role="Procuring entity")
            b.add_edge(buyer_id, t_id, "buyer_tender", "issued")

        for company in record.companies:
            c_id = f"company:{(company.canonical_company_id or company.name).casefold().strip()}"
            b.add_node(c_id, "company", company.name, registration_number=company.registration_number,
                       source=company.metadata.source_name)
            b.add_edge(c_id, t_id, "company_tender", "participated")

        for award in record.awards:
            c_id = f"company:{(award.canonical_company_id or award.company_name).casefold().strip()}"
            b.add_node(c_id, "company", award.company_name,
                       registration_number=award.company_registration_number)
            a_id = f"award:{tender.reference_number}:{award.company_name.casefold().strip()}"
            b.add_node(
                a_id, "award", f"{award.company_name} — {tender.reference_number}",
                award_value=str(award.award_value) if award.award_value is not None else None,
                currency=award.currency,
                award_date=award.award_date.isoformat() if award.award_date else None,
            )
            b.add_edge(t_id, a_id, "tender_award", "awarded")
            b.add_edge(a_id, c_id, "award_company", "to")

        for document in record.documents:
            d_id = f"document:{_slug(tender.reference_number, document.title, document.url or '')}"
            b.add_node(d_id, "document", document.title or "Document",
                       document_type=document.document_type, url=document.url,
                       source=document.metadata.source_name)
            b.add_edge(d_id, t_id, "document_tender", "supports")

    # ----------------------------------------------------------------- evidence
    # Every evidence row becomes a node linked to its tender/entity, so the graph
    # never shows zero evidence when the package carries it.
    for idx, ev in enumerate(pkg.evidence):
        e_id = f"evidence:{_slug(ev.evidence_type, ev.source_name, ev.source_record_id, str(idx))}"
        b.add_node(
            e_id, "evidence", ev.title or ev.evidence_type,
            evidence_type=ev.evidence_type, source=ev.source_name,
            source_url=ev.source_url, source_record_id=ev.source_record_id,
        )
        if ev.related_tender:
            t_id = f"tender:{ev.related_tender}"
            if t_id in b.nodes:
                b.add_edge(e_id, t_id, "tender_evidence", "evidences")
        if ev.related_entity:
            c_id = f"company:{ev.related_entity.casefold().strip()}"
            if c_id in b.nodes:
                b.add_edge(e_id, c_id, "organization_evidence", "mentions")

    # --------------------------------------------------------------- indicators
    # Every procurement indicator becomes a node, linked to the tenders, buyers
    # and suppliers it was computed from — so risk is visible in the graph.
    for idx, ind in enumerate(pkg.indicators):
        i_id = f"indicator:{_slug(ind.type, str(idx))}"
        b.add_node(
            i_id, "indicator", ind.title,
            indicator_type=ind.type, severity=ind.severity, score=ind.score,
            confidence=ind.confidence, summary=ind.summary, supporting_evidence=ind.reason,
        )
        for ref in ind.related_tenders:
            t_id = f"tender:{ref}"
            if t_id in b.nodes:
                b.add_edge(t_id, i_id, "tender_indicator", ind.severity)
        for supplier in ind.supporting_suppliers:
            c_id = f"company:{supplier.casefold().strip()}"
            if c_id in b.nodes:
                b.add_edge(c_id, i_id, "company_indicator", "flagged")

    # -------------------------------------------------- organizations (entities)
    # Government buyers / organizations resolved as entities that are not already
    # present as buyer/company nodes still deserve representation.
    for entity in pkg.entities:
        if entity.entity_type == "government_buyer":
            org_id = f"buyer:{entity.name.casefold().strip()}"
            b.add_node(org_id, "buyer", entity.name, role="Procuring entity",
                       sources=entity.sources)
        elif entity.entity_type == "company":
            org_id = f"company:{entity.name.casefold().strip()}"
            b.add_node(org_id, "company", entity.name,
                       registration_number=entity.registration_number, sources=entity.sources)

    return b.build()
