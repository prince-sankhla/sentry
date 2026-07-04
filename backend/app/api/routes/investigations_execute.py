from fastapi import APIRouter, Depends

from app.schemas.investigation_executor import InvestigationExecutionRequest
from app.services.investigation_executor import InvestigationExecutor

router = APIRouter(prefix="/api/investigations/execute", tags=["investigations"])


@router.post("")
def execute_investigation(request: InvestigationExecutionRequest, executor: InvestigationExecutor = Depends()) -> InvestigationExecutionRequest:
    package = executor.execute_plan(request)
    return InvestigationExecutionRequest(
        plan=request.plan,
        limit_per_connector=request.limit_per_connector,
        package=package,
    )