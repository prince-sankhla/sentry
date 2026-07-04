from __future__ import annotations

from typing import TYPE_CHECKING

from app.connectors import SourceManager
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
    ) -> None:
        self.source_manager = source_manager or SourceManager()
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
                            reference_number=record.tender.id,
                            title=record.tender.title,
                            description=record.tender.description,
                            procuring_entity=record.tender.procuring_entity,
                            published_date=record.tender.published_date,
                            closing_date=record.tender.closing_date,
                            estimated_value=record.tender.value,
                            currency=record.tender.currency,
                            metadata=InvestigationSourceMetadata(
                                source_name=record.tender.source_name,
                                source_record_id=record.tender.source_record_id,
                                source_url=record.tender.source_url,
                                retrieved_at=record.tender.retrieved_at,
                            ),
                        )
                    )
                    # Add companies
                    for company in record.companies:
                        pkg_record.companies.append(
                            InvestigationCompanyResult(
                                name=company.name,
                                registration_number=company.registration_number,
                                metadata=InvestigationSourceMetadata(
                                    source_name=company.source_name,
                                    source_record_id=company.source_record_id,
                                    source_url=company.source_url,
                                    retrieved_at=company.retrieved_at,
                                ),
                            )
                        )
                    # Add awards
                    for award in record.awards:
                        pkg_record.awards.append(
                            InvestigationAwardResult(
                                tender_reference_number=award.tender_id,
                                company_name=award.company_name,
                                company_registration_number=award.company_registration_number,
                                award_date=award.award_date,
                                award_value=award.value,
                                currency=award.currency,
                                metadata=InvestigationSourceMetadata(
                                    source_name=award.source_name,
                                    source_record_id=award.source_record_id,
                                    source_url=award.source_url,
                                    retrieved_at=award.retrieved_at,
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
                                    source_name=document.source_name,
                                    source_record_id=document.source_record_id,
                                    source_url=document.source_url,
                                    retrieved_at=document.retrieved_at,
                                ),
                            )
                        )
                    pkg.records.append(pkg_record)
                    step_result.records_added += 1

        # Placeholder for other modules
        # TODO: Implement logic for other modules (graph, timeline, entity_resolution, etc.)

        return step_result
