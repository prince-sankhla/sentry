from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from app.connectors import SourceManager
from app.entity_resolution.package_resolver import InvestigationEntityResolver
from app.entity_resolution.utils import compact_unique
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationCompanyResult,
    InvestigationDocumentResult,
    InvestigationEntity,
    InvestigationEvidence,
    InvestigationExecutionRequest,
    InvestigationGraphSeed,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationStepResult,
    InvestigationTenderResult,
    InvestigationTimelineEvent,
)
from app.schemas.investigation_planner import InvestigationPlanStep, InvestigationType

if TYPE_CHECKING:
    from app.services.investigation_planner import InvestigationPlanner


class InvestigationExecutor:
    def __init__(
        self,
        source_manager: SourceManager | None = None,
        investigation_planner: InvestigationPlanner | None = None,
        entity_resolver: InvestigationEntityResolver | None = None,
        session=None,
    ) -> None:
        self.source_manager = source_manager or SourceManager()
        self.entity_resolver = entity_resolver or InvestigationEntityResolver()
        # When a DB session is supplied, investigations run against the real
        # imported PostgreSQL data; otherwise they fall back to file connectors.
        if session is not None:
            from app.services.investigation_repository import DatabaseRecordSource

            self.record_source = DatabaseRecordSource(session)
        else:
            self.record_source = self.source_manager
        # Lazily import to avoid circular dependency
        if investigation_planner:
            self.investigation_planner = investigation_planner
        else:
            from app.services.investigation_planner import InvestigationPlanner
            self.investigation_planner = InvestigationPlanner(source_manager=self.source_manager)

    async def execute(self, request: InvestigationExecutionRequest) -> InvestigationPackage:
        if request.package:
            pkg = request.package
        else:
            pkg = InvestigationPackage(plan=request.plan)

        for step in request.plan.steps:
            step_result = await self._execute_step(pkg, step, request.limit_per_connector)
            pkg.step_results.append(step_result)

        self._finalize_package(pkg)
        return pkg

    def _search(self, query: str, connectors: list[str], limit_per_connector: int):
        """One search per step. Against the DB (source of truth) we query the
        whole store; file-backed connectors are still queried per source."""
        from app.services.investigation_repository import DatabaseRecordSource

        if isinstance(self.record_source, DatabaseRecordSource):
            scaled = limit_per_connector * max(len(connectors), 1)
            return self.record_source.search(query, source_names=None, limit=scaled)
        results = []
        for connector_name in connectors:
            results.extend(
                self.record_source.search(query, source_names=[connector_name], limit=limit_per_connector)
            )
        return results

    def _finalize_package(self, pkg: InvestigationPackage) -> None:
        """Derive package-level projections from the collected procurement records.

        Rebuilt from scratch on every execute() so the package stays consistent when
        an existing package is passed back in for incremental execution.
        """
        from app.services.investigation_indicators import build_indicators

        pkg.entities = _build_entities(pkg)
        pkg.evidence = _build_evidence(pkg)
        pkg.timeline = _build_timeline(pkg)
        pkg.graph_seeds = _build_graph_seeds(pkg)
        pkg.indicators = build_indicators(pkg)

    async def _execute_step(
        self, pkg: InvestigationPackage, step: InvestigationPlanStep, limit_per_connector: int
    ) -> InvestigationStepResult:
        step_result = InvestigationStepResult(
            order=step.order,
            module=step.module,
            action=step.action,
            connectors=step.connectors,
        )

        if step.module in {"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}:
            for records in [self._search(step.inputs["query"], step.connectors, limit_per_connector)]:
                for record in records:
                    pkg_record = InvestigationProcurementRecord(
                        tender=InvestigationTenderResult(
                            reference_number=record.tender.reference_number,
                            title=record.tender.title,
                            description=record.tender.description,
                            procuring_entity=record.tender.procuring_entity,
                            published_date=record.tender.published_date,
                            closing_date=record.tender.closing_date,
                            estimated_value=record.tender.estimated_value,
                            currency=record.tender.currency,
                            metadata=InvestigationSourceMetadata(
                                source_name=record.tender.metadata.source_name,
                                source_record_id=record.tender.metadata.source_record_id,
                                source_url=record.tender.metadata.source_url,
                                retrieved_at=record.tender.metadata.retrieved_at,
                            ),
                        )
                    )
                    # Add companies
                    for company in record.companies:
                        pkg_record.companies.append(
                            InvestigationCompanyResult(
                                name=company.name,
                                registration_number=company.registration_number,
                                tax_id=None,
                                company_identifier=company.registration_number,
                                address=None,
                                website=None,
                                metadata=InvestigationSourceMetadata(
                                    source_name=company.metadata.source_name,
                                    source_record_id=company.metadata.source_record_id,
                                    source_url=company.metadata.source_url,
                                    retrieved_at=company.metadata.retrieved_at,
                                ),
                            )
                        )
                    # Add awards
                    for award in record.awards:
                        pkg_record.awards.append(
                            InvestigationAwardResult(
                                tender_reference_number=award.tender_reference_number,
                                company_name=award.company_name,
                                company_registration_number=award.company_registration_number,
                                company_tax_id=None,
                                company_identifier=award.company_registration_number,
                                company_address=None,
                                company_website=None,
                                award_date=award.award_date,
                                award_value=award.award_value,
                                currency=award.currency,
                                metadata=InvestigationSourceMetadata(
                                    source_name=award.metadata.source_name,
                                    source_record_id=award.metadata.source_record_id,
                                    source_url=award.metadata.source_url,
                                    retrieved_at=award.metadata.retrieved_at,
                                ),
                            )
                        )
                    # Add documents
                    for document in record.documents:
                        pkg_record.documents.append(
                            InvestigationDocumentResult(
                                title=document.title,
                                url=document.url,
                                document_type=document.document_type,
                                metadata=InvestigationSourceMetadata(
                                    source_name=document.metadata.source_name,
                                    source_record_id=document.metadata.source_record_id,
                                    source_url=document.metadata.source_url,
                                    retrieved_at=document.metadata.retrieved_at,
                                ),
                            )
                        )
                    pkg.records.append(pkg_record)
                    step_result.records_added += 1
            self.entity_resolver.resolve_package(pkg)
            step_result.entities_added = len(pkg.canonical_companies)
            step_result.evidence_added = sum(len(record.documents) for record in pkg.records)

        return step_result


def _build_entities(pkg: InvestigationPackage) -> list[InvestigationEntity]:
    """One entity per canonical company plus every distinct procuring entity (buyer)."""
    entities: list[InvestigationEntity] = []

    for canonical in pkg.canonical_companies:
        registration = next(
            (
                source.source_record_id
                for source in canonical.matched_sources
                if source.source_record_id
            ),
            None,
        )
        entities.append(
            InvestigationEntity(
                name=canonical.canonical_name,
                entity_type="company",
                registration_number=registration,
                source_record_ids=compact_unique(
                    [source.source_record_id for source in canonical.matched_sources]
                ),
                sources=compact_unique(
                    [source.source_name for source in canonical.matched_sources]
                ),
            )
        )

    buyers: dict[str, InvestigationEntity] = {}
    for record in pkg.records:
        buyer_name = record.tender.procuring_entity
        if not buyer_name:
            continue
        key = buyer_name.casefold().strip()
        entity = buyers.get(key)
        if entity is None:
            buyers[key] = InvestigationEntity(
                name=buyer_name,
                entity_type="government_buyer",
                source_record_ids=[record.tender.metadata.source_record_id],
                sources=[record.tender.metadata.source_name],
            )
        else:
            entity.source_record_ids = compact_unique(
                [*entity.source_record_ids, record.tender.metadata.source_record_id]
            )
            entity.sources = compact_unique(
                [*entity.sources, record.tender.metadata.source_name]
            )
    entities.extend(buyers.values())

    return entities


def _build_evidence(pkg: InvestigationPackage) -> list[InvestigationEvidence]:
    """Surface tenders, awards, and documents as source-attributed evidence rows."""
    evidence: list[InvestigationEvidence] = []

    for record in pkg.records:
        tender = record.tender
        evidence.append(
            InvestigationEvidence(
                evidence_type="tender",
                title=tender.title,
                source_name=tender.metadata.source_name,
                source_record_id=tender.metadata.source_record_id,
                source_url=tender.metadata.source_url,
                related_tender=tender.reference_number,
            )
        )
        for award in record.awards:
            evidence.append(
                InvestigationEvidence(
                    evidence_type="award",
                    title=f"{award.company_name} — {tender.reference_number}",
                    source_name=award.metadata.source_name,
                    source_record_id=award.metadata.source_record_id,
                    source_url=award.metadata.source_url,
                    related_tender=tender.reference_number,
                    related_entity=award.company_name,
                )
            )
        for document in record.documents:
            evidence.append(
                InvestigationEvidence(
                    evidence_type="document",
                    title=document.title,
                    source_name=document.metadata.source_name,
                    source_record_id=document.metadata.source_record_id,
                    source_url=document.url or document.metadata.source_url,
                    related_tender=tender.reference_number,
                )
            )

    return evidence


def _build_timeline(pkg: InvestigationPackage) -> list[InvestigationTimelineEvent]:
    """Chronological events from tender publication/closing dates and award dates."""
    events: list[InvestigationTimelineEvent] = []

    for record in pkg.records:
        tender = record.tender
        if tender.published_date is not None:
            events.append(
                InvestigationTimelineEvent(
                    label=f"Tender published: {tender.title}",
                    event_date=tender.published_date,
                    source_name=tender.metadata.source_name,
                    source_record_id=tender.metadata.source_record_id,
                    related_tender=tender.reference_number,
                )
            )
        if tender.closing_date is not None:
            events.append(
                InvestigationTimelineEvent(
                    label=f"Tender closing: {tender.title}",
                    event_date=tender.closing_date,
                    source_name=tender.metadata.source_name,
                    source_record_id=tender.metadata.source_record_id,
                    related_tender=tender.reference_number,
                )
            )
        for award in record.awards:
            if award.award_date is None:
                continue
            events.append(
                InvestigationTimelineEvent(
                    label=f"Award: {award.company_name}",
                    event_date=award.award_date,
                    source_name=award.metadata.source_name,
                    source_record_id=award.metadata.source_record_id,
                    related_tender=tender.reference_number,
                    related_entity=award.company_name,
                )
            )

    events.sort(key=lambda event: _timeline_sort_key(event.event_date))
    return events


def _timeline_sort_key(event_date: date | datetime) -> date:
    return event_date.date() if isinstance(event_date, datetime) else event_date


def _build_graph_seeds(pkg: InvestigationPackage) -> list[InvestigationGraphSeed]:
    """Relationship edges: buyer→tender, company→tender, tender→award, award→company."""
    seeds: list[InvestigationGraphSeed] = []

    for record in pkg.records:
        tender = record.tender
        tender_key = tender.reference_number
        source_name = tender.metadata.source_name
        source_record_id = tender.metadata.source_record_id

        if tender.procuring_entity:
            seeds.append(
                InvestigationGraphSeed(
                    source=tender.procuring_entity,
                    target=tender_key,
                    relationship="buyer_of",
                    source_name=source_name,
                    source_record_id=source_record_id,
                )
            )

        for company in record.companies:
            seeds.append(
                InvestigationGraphSeed(
                    source=company.canonical_company_id or company.name,
                    target=tender_key,
                    relationship="participated_in",
                    source_name=company.metadata.source_name,
                    source_record_id=company.metadata.source_record_id,
                )
            )

        for award in record.awards:
            seeds.append(
                InvestigationGraphSeed(
                    source=tender_key,
                    target=award.canonical_company_id or award.company_name,
                    relationship="awarded_to",
                    source_name=award.metadata.source_name,
                    source_record_id=award.metadata.source_record_id,
                )
            )

    return seeds
