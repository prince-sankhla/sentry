"""Profiles are focused investigations.

A tender/company/buyer profile runs the InvestigationExecutor against the real
database seeded by that entity, then reshapes the resulting InvestigationPackage
into an overview + related lists + graph. All investigation logic (records,
timeline, evidence, indicators, entity resolution, graph seeds) is reused — this
module only projects the package, it never recomputes it.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Tender
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse
from app.schemas.investigation_executor import (
    InvestigationExecutionRequest,
    InvestigationPackage,
)
from app.schemas.profiles import (
    ProfileOverview,
    ProfileResponse,
    RelatedAward,
    RelatedDocument,
    RelatedTender,
)
from app.services.investigation_executor import InvestigationExecutor
from app.services.investigation_planner import InvestigationPlanner


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def _package(self, query: str, limit: int = 50) -> InvestigationPackage:
        plan = InvestigationPlanner().build_plan(query=query)
        executor = InvestigationExecutor(session=self.db)
        request = InvestigationExecutionRequest(plan=plan, limit_per_connector=limit)
        return await executor.execute(request)

    async def tender_profile(self, tender_id: UUID) -> ProfileResponse | None:
        tender = self.db.get(Tender, tender_id)
        if tender is None:
            return None
        pkg = await self._package(tender.reference_number)
        pkg = _focus(pkg, tender_refs={tender.reference_number})
        overview = ProfileOverview(
            kind="tender",
            id=str(tender.id),
            title=tender.title,
            subtitle=tender.procuring_entity,
            stats={
                "reference_number": tender.reference_number,
                "estimated_value": _num(tender.estimated_value),
                "currency": tender.currency,
                "published_date": _iso(tender.published_date),
                "closing_date": _iso(tender.closing_date),
                "source_name": tender.source_name,
                "awards": sum(len(r.awards) for r in pkg.records),
                "documents": sum(len(r.documents) for r in pkg.records),
                "suppliers": len({a.company_name for r in pkg.records for a in r.awards}),
            },
        )
        return _to_response(overview, pkg)

    async def company_profile(self, company_id: UUID) -> ProfileResponse | None:
        company = self.db.get(Company, company_id)
        if company is None:
            return None
        pkg = await self._package(company.name)
        pkg = _focus(pkg, company_names={company.name})
        awards = [a for r in pkg.records for a in r.awards]
        total = sum((a.award_value for a in awards if a.award_value is not None), Decimal("0"))
        overview = ProfileOverview(
            kind="company",
            id=str(company.id),
            title=company.name,
            subtitle=company.registration_number,
            stats={
                "registration_number": company.registration_number,
                "awards": len(awards),
                "tenders": len({r.tender.reference_number for r in pkg.records}),
                "buyers": len({r.tender.procuring_entity for r in pkg.records if r.tender.procuring_entity}),
                "total_award_value": _num(total),
                "source_name": company.source_name,
            },
        )
        return _to_response(overview, pkg)

    async def buyer_profile(self, name: str) -> ProfileResponse | None:
        cleaned = name.strip()
        if not cleaned:
            return None
        pkg = await self._package(cleaned)
        pkg = _focus(pkg, buyer=cleaned)
        if not pkg.records:
            return None
        awards = [a for r in pkg.records for a in r.awards]
        total = sum((a.award_value for a in awards if a.award_value is not None), Decimal("0"))
        overview = ProfileOverview(
            kind="buyer",
            id=cleaned,
            title=cleaned,
            subtitle="Procuring entity",
            stats={
                "tenders": len({r.tender.reference_number for r in pkg.records}),
                "awards": len(awards),
                "suppliers": len({a.company_name for a in awards}),
                "total_award_value": _num(total),
            },
        )
        return _to_response(overview, pkg)


def _focus(
    pkg: InvestigationPackage,
    *,
    tender_refs: set[str] | None = None,
    company_names: set[str] | None = None,
    buyer: str | None = None,
) -> InvestigationPackage:
    """Keep records genuinely connected to the seed entity, then rebuild
    package projections so indicators/timeline/graph reflect the focus."""
    records = pkg.records
    if tender_refs is not None:
        records = [r for r in records if r.tender.reference_number in tender_refs]
    elif company_names is not None:
        lowered = {n.casefold() for n in company_names}
        records = [
            r
            for r in records
            if any(a.company_name.casefold() in lowered for a in r.awards)
            or any(c.name.casefold() in lowered for c in r.companies)
        ]
    elif buyer is not None:
        needle = buyer.casefold()
        records = [r for r in records if r.tender.procuring_entity and needle in r.tender.procuring_entity.casefold()]
    if len(records) == len(pkg.records):
        return pkg

    from app.services.investigation_executor import (
        _build_entities,
        _build_evidence,
        _build_graph_seeds,
        _build_timeline,
    )
    from app.services.investigation_indicators import build_indicators

    pkg.records = records
    pkg.entities = _build_entities(pkg)
    pkg.evidence = _build_evidence(pkg)
    pkg.timeline = _build_timeline(pkg)
    pkg.graph_seeds = _build_graph_seeds(pkg)
    pkg.indicators = build_indicators(pkg)
    return pkg


def _to_response(overview: ProfileOverview, pkg: InvestigationPackage) -> ProfileResponse:
    seen_tenders: dict[str, RelatedTender] = {}
    related_awards: list[RelatedAward] = []
    related_documents: list[RelatedDocument] = []
    for record in pkg.records:
        tender = record.tender
        seen_tenders.setdefault(
            tender.reference_number,
            RelatedTender(
                reference_number=tender.reference_number,
                title=tender.title,
                procuring_entity=tender.procuring_entity,
                published_date=tender.published_date,
                estimated_value=tender.estimated_value,
                currency=tender.currency,
                source_name=tender.metadata.source_name,
            ),
        )
        for award in record.awards:
            related_awards.append(
                RelatedAward(
                    tender_reference_number=tender.reference_number,
                    company_name=award.company_name,
                    award_value=award.award_value,
                    currency=award.currency,
                    award_date=award.award_date,
                )
            )
        for document in record.documents:
            related_documents.append(
                RelatedDocument(
                    title=document.title,
                    url=document.url,
                    document_type=document.document_type,
                    related_tender=tender.reference_number,
                )
            )

    return ProfileResponse(
        overview=overview,
        indicators=pkg.indicators,
        timeline=pkg.timeline,
        evidence=pkg.evidence,
        relationships=pkg.graph_seeds,
        related_tenders=list(seen_tenders.values()),
        related_awards=related_awards,
        related_documents=related_documents,
        graph=_graph_from_seeds(pkg),
        canonical_companies=pkg.canonical_companies,
        entities=pkg.entities,
    )


_REL_EDGE = {
    "buyer_of": ("buyer", "tender", "buyer_tender"),
    "participated_in": ("company", "tender", "company_tender"),
    "awarded_to": ("tender", "company", "tender_award"),
}


def _graph_from_seeds(pkg: InvestigationPackage) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    def node(kind: str, label: str) -> str:
        node_id = f"{kind}:{label}"
        nodes.setdefault(node_id, GraphNode(id=node_id, type=kind, label=label))
        return node_id

    for seed in pkg.graph_seeds:
        mapping = _REL_EDGE.get(seed.relationship)
        if mapping is None:
            continue
        source_kind, target_kind, edge_type = mapping
        source_id = node(source_kind, seed.source)
        target_id = node(target_kind, seed.target)
        edge_id = f"{edge_type}:{source_id}->{target_id}"
        edges.setdefault(
            edge_id,
            GraphEdge(
                id=edge_id,
                source=source_id,
                target=target_id,
                type=edge_type,
                label=seed.relationship.replace("_", " "),
                data={"source_name": seed.source_name, "source_record_id": seed.source_record_id},
            ),
        )
    return GraphResponse(nodes=list(nodes.values()), edges=list(edges.values()))


def _num(value) -> str | None:
    return str(value) if value is not None else None


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None
