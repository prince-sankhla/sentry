from fastapi import APIRouter

from app.schemas.investigation_planner import InvestigationPlan, InvestigationPlanRequest
from app.services.investigation_planner import InvestigationPlanner

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.post("/plan", response_model=InvestigationPlan)
def plan_investigation(request: InvestigationPlanRequest) -> InvestigationPlan:
    return InvestigationPlanner().build_plan(
        query=request.query,
        source_names=request.source_names,
    )
