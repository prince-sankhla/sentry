from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.investigation_executor import InvestigationExecutionRequest
from app.services.investigation_executor import InvestigationExecutor

router = APIRouter(prefix="/api/investigations/execute", tags=["investigations"])


@router.post("")
async def execute_investigation(
    request: InvestigationExecutionRequest, db: Session = Depends(get_db)
) -> InvestigationExecutionRequest:
    # Run against the imported PostgreSQL data (source of truth) so results are
    # Indian-procurement-ranked, matching the streaming /execute path.
    executor = InvestigationExecutor(session=db)
    package = await executor.execute(request)
    return InvestigationExecutionRequest(
        plan=request.plan,
        limit_per_connector=request.limit_per_connector,
        package=package,
    )
