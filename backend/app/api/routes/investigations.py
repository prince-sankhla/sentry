import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.investigation_planner import InvestigationPlan, InvestigationPlanRequest
from app.schemas.investigation_executor import (
    InvestigationExecutionRequest,
    InvestigationPackage,
)
from app.schemas.investigation_reasoning import InvestigationReasoning
from app.services.investigation_planner import InvestigationPlanner
from app.services.investigation_executor import InvestigationExecutor
from app.services.investigation_reasoning import build_reasoning
from app.clients.llm import available_providers, get_llm_client

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class LLMProviderStatus(BaseModel):
    """Observability for the multi-provider reasoning chain.

    ``mode`` is ``llm`` when at least one provider is configured (the chain will
    attempt live narration, falling back deterministically on failure) or
    ``deterministic`` when none is configured (fully offline reasoning).
    """

    mode: str
    providers: list[str]
    fallback_order: list[str]


@router.get("/providers", response_model=LLMProviderStatus)
def llm_providers() -> LLMProviderStatus:
    providers = available_providers()
    return LLMProviderStatus(
        mode="llm" if get_llm_client() is not None else "deterministic",
        providers=providers,
        fallback_order=providers,
    )


@router.post("/plan", response_model=InvestigationPlan)
def plan_investigation(request: InvestigationPlanRequest) -> InvestigationPlan:
    return InvestigationPlanner().build_plan(
        query=request.query,
        source_names=request.source_names,
    )


@router.post("/execute")
async def execute_investigation(
    request: InvestigationExecutionRequest, db: Session = Depends(get_db)
) -> InvestigationExecutionRequest:
    executor = InvestigationExecutor(session=db)
    package = await executor.execute(request)
    return InvestigationExecutionRequest(
        plan=request.plan,
        limit_per_connector=request.limit_per_connector,
        package=package,
    )


class InvestigationStreamRequest(BaseModel):
    query: str
    source_names: list[str] | None = None
    limit_per_connector: int = 25


class InvestigationReport(BaseModel):
    """Full result of a streamed investigation: the executed package + AI reasoning."""

    package: InvestigationPackage
    reasoning: InvestigationReasoning


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/stream")
async def stream_investigation(
    request: InvestigationStreamRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    """Run a full investigation from one free-text prompt, streaming live progress.

    Emits SSE frames as the multi-step agent works:
      * ``step``   — a pipeline step started/completed (plan, execute, resolve, indicators, reasoning)
      * ``plan``   — the generated investigation plan
      * ``report`` — the final package + grounded AI reasoning
      * ``error``  — an unrecoverable failure

    The heavy lifting reuses the existing planner, executor, entity resolution,
    and indicator services — this endpoint only orchestrates and narrates them.
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            # Step 1 — understand request & plan connectors
            yield _sse("step", {"key": "plan", "status": "running", "label": "Understanding request & selecting sources"})
            planner = InvestigationPlanner()
            plan = planner.build_plan(query=request.query, source_names=request.source_names)
            yield _sse("plan", plan.model_dump(mode="json"))
            yield _sse(
                "step",
                {
                    "key": "plan",
                    "status": "complete",
                    "label": "Investigation plan ready",
                    "detail": f"{plan.investigation_type} · {len(plan.connectors)} sources · {len(plan.steps)} steps",
                },
            )

            # Step 2 — retrieve records + resolve entities + build graph/indicators.
            # The executor runs the planner's steps end to end and finalizes the package.
            yield _sse("step", {"key": "retrieve", "status": "running", "label": "Retrieving procurement records"})
            executor = InvestigationExecutor(session=db)
            package = await executor.execute(
                InvestigationExecutionRequest(plan=plan, limit_per_connector=request.limit_per_connector)
            )
            yield _sse(
                "step",
                {
                    "key": "retrieve",
                    "status": "complete",
                    "label": "Records retrieved",
                    "detail": f"{len(package.records)} records",
                },
            )
            yield _sse(
                "step",
                {
                    "key": "resolve",
                    "status": "complete",
                    "label": "Entities resolved",
                    "detail": f"{len(package.canonical_companies)} canonical entities",
                },
            )
            yield _sse(
                "step",
                {
                    "key": "indicators",
                    "status": "complete",
                    "label": "Risk engine complete",
                    "detail": f"{len(package.indicators)} indicators",
                },
            )

            # Step 3 — AI reasoning over the grounded package.
            yield _sse("step", {"key": "reasoning", "status": "running", "label": "Reasoning over evidence"})
            reasoning = build_reasoning(package, request.query)
            yield _sse(
                "step",
                {
                    "key": "reasoning",
                    "status": "complete",
                    "label": "Findings generated",
                    "detail": f"{reasoning.risk_level} risk · {reasoning.generated_by}",
                },
            )

            report = InvestigationReport(package=package, reasoning=reasoning)
            yield _sse("report", report.model_dump(mode="json"))
            yield _sse("done", {"ok": True})
        except Exception as exc:  # surface failures to the client as an SSE error frame
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
