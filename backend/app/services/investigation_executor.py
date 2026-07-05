from __future__ import annotations

from typing import TYPE_CHECKING

from app.connectors import SourceManager
from app.entity_resolution.package_resolver import InvestigationEntityResolver
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationCompanyResult,
    InvestigationDocumentResult,
    InvestigationExecutionRequest,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationStepResult,
    InvestigationTenderResult,
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
    ) -> None:
        self.source_manager = source_manager or SourceManager()
        self.entity_resolver = entity_resolver or InvestigationEntityResolver()
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

        return pkg

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
            for connector_name in step.connectors:
                records =  self.source_manager.search(
                    query=step.inputs["query"],
                    source_names=[connector_name],
                    limit=limit_per_connector,
                )
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

        # Placeholder for other modules
        # TODO: Implement logic for other modules (graph, timeline, entity_resolution, etc.)

        return step_result
