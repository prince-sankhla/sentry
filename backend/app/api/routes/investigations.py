import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.entity_resolution import EntityResolutionResult
from app.schemas.investigation_planner import InvestigationPlan, InvestigationPlanRequest
from app.schemas.investigation_executor import InvestigationExecutionRequest, InvestigationPackage
from app.schemas.investigation_reasoning import InvestigationReasoning
from app.schemas.priority_queue import PriorityQueueResponse
from app.services.priority_queue import build_priority_queue
from app.services.entity_resolution_service import resolve_entities
from app.services.investigation_planner import InvestigationPlanner
from app.services.investigation_executor import InvestigationExecutor
from app.services.investigation_reasoning import build_reasoning
from app.services.investigation_packet import build_packet_document, render_packet_html
from app.clients.llm import available_providers, get_llm_client

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class LLMProviderStatus(BaseModel):
    mode: str
    providers: list[str]
    fallback_order: list[str]


def _provider_status() -> LLMProviderStatus:
    providers = available_providers()
    return LLMProviderStatus(
        mode="llm" if get_llm_client() is not None else "deterministic",
        providers=providers,
        fallback_order=providers,
    )


_FALLBACK_LABELS = {
    "no_provider": "no LLM provider configured",
    "provider_error": "all providers errored/refused — safe deterministic report",
    "grounding_guard": "model phrasing failed the grounding guard — safe deterministic report",
}


def _reasoning_detail(reasoning: InvestigationReasoning) -> str:
    if reasoning.generated_by == "llm":
        who = reasoning.provider or "LLM"
        if reasoning.model:
            who = f"{who} · {reasoning.model}"
        return f"{reasoning.risk_level} risk · authored by {who}"
    reason = _FALLBACK_LABELS.get(reasoning.fallback_reason or "", "deterministic analyst")
    return f"{reasoning.risk_level} risk · {reason}"


@router.get("/providers", response_model=LLMProviderStatus)
def llm_providers() -> LLMProviderStatus:
    return _provider_status()


@router.get("/context-analysis")
def context_analysis(
    finding_id: str = Query(..., min_length=1, max_length=80),
    finding_name: str = Query("", max_length=200),
    jurisdiction: str = Query("", max_length=20),
):
    from types import SimpleNamespace
    from app.verified_context import ProcurementContextAnalyzer

    finding = SimpleNamespace(id=finding_id, name=finding_name or finding_id)
    return ProcurementContextAnalyzer().analyze(finding, jurisdiction=jurisdiction)


class ContextAnalysisRequest(BaseModel):
    finding_id: str
    finding_name: str = ""
    jurisdiction: str = ""
    facts: dict | None = None


@router.post("/context-analysis")
def context_analysis_with_facts(request: ContextAnalysisRequest):
    from types import SimpleNamespace
    from app.verified_context import ContextFacts, ProcurementContextAnalyzer

    finding = SimpleNamespace(id=request.finding_id, name=request.finding_name or request.finding_id)
    facts = ContextFacts.model_validate(request.facts) if request.facts is not None else None
    return ProcurementContextAnalyzer().analyze(finding, facts=facts, jurisdiction=request.jurisdiction)


@router.get("/priority-queue", response_model=PriorityQueueResponse)
def priority_queue(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)) -> PriorityQueueResponse:
    return build_priority_queue(db, limit=limit)


class EntityResolutionRequest(BaseModel):
    query: str


@router.post("/resolve-entity", response_model=EntityResolutionResult)
def resolve_entity(request: EntityResolutionRequest, db: Session = Depends(get_db)) -> EntityResolutionResult:
    return resolve_entities(db, request.query)


@router.post("/plan", response_model=InvestigationPlan)
def plan_investigation(request: InvestigationPlanRequest) -> InvestigationPlan:
    return InvestigationPlanner().build_plan(query=request.query, source_names=request.source_names)


@router.post("/execute")
async def execute_investigation(request: InvestigationExecutionRequest, db: Session = Depends(get_db)) -> InvestigationExecutionRequest:
    package = await InvestigationExecutor(session=db).execute(request)
    return InvestigationExecutionRequest(plan=request.plan, limit_per_connector=request.limit_per_connector, package=package)


class InvestigationStreamRequest(BaseModel):
    query: str
    source_names: list[str] | None = None
    limit_per_connector: int = 25


class InvestigationReport(BaseModel):
    package: InvestigationPackage
    reasoning: InvestigationReasoning


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/stream")
async def stream_investigation(request: InvestigationStreamRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Core investigation stream. External web research is intentionally non-blocking and runs in the parallel intelligence panel."""

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield _sse("step", {"key": "resolve_entity", "status": "running", "label": "Resolving canonical entity"})
            try:
                resolution = resolve_entities(db, request.query)
                yield _sse("candidates", resolution.model_dump(mode="json"))
                detail = f"{len(resolution.candidates)} candidate(s)" + (" · selection recommended" if resolution.requires_disambiguation else "")
            except Exception:
                detail = "resolution skipped"
            yield _sse("step", {"key": "resolve_entity", "status": "complete", "label": "Entity resolution complete", "detail": detail})

            yield _sse("step", {"key": "plan", "status": "running", "label": "Understanding request & selecting sources"})
            plan = InvestigationPlanner().build_plan(query=request.query, source_names=request.source_names)
            yield _sse("plan", plan.model_dump(mode="json"))
            yield _sse("step", {"key": "plan", "status": "complete", "label": "Investigation plan ready", "detail": f"{plan.investigation_type} · {len(plan.connectors)} sources · {len(plan.steps)} steps"})

            yield _sse("step", {"key": "retrieve", "status": "running", "label": "Retrieving procurement records"})
            package = await InvestigationExecutor(session=db).execute(
                InvestigationExecutionRequest(plan=plan, limit_per_connector=request.limit_per_connector)
            )
            yield _sse("step", {"key": "retrieve", "status": "complete", "label": "Records retrieved", "detail": f"{len(package.records)} records"})
            yield _sse("step", {"key": "resolve", "status": "complete", "label": "Entities resolved", "detail": f"{len(package.canonical_companies)} canonical entities"})

            risk_v2 = package.risk_assessment_v2
            indicators_detail = f"{len(package.indicators)} indicators"
            if risk_v2 is not None:
                indicators_detail += f" · {len(risk_v2.patterns)} pattern(s) · {risk_v2.overall_severity} (deterministic V2)"
            yield _sse("step", {"key": "indicators", "status": "complete", "label": "Risk engine complete", "detail": indicators_detail})

            documents_available = sum(1 for r in package.records if r.documents)
            yield _sse("step", {"key": "evidence", "status": "complete", "label": "Evidence engine complete", "detail": f"{len(package.evidence)} evidence items · {documents_available} documents"})
            yield _sse("step", {"key": "grounding", "status": "complete", "label": "Grounding verified", "detail": f"{len(package.graph.nodes)} graph nodes anchored to source records"})

            yield _sse(
                "step",
                {
                    "key": "web_search",
                    "status": "complete",
                    "label": "Open-source intelligence available in parallel",
                    "detail": "Web context research runs in the parallel intelligence panel and does not block the core procurement investigation.",
                },
            )

            provider_status = _provider_status()
            yield _sse("step", {"key": "reasoning", "status": "running", "label": "Analyst reasoning over evidence", "detail": (f"Engaging {', '.join(provider_status.providers)}" if provider_status.mode == "llm" else "Deterministic analyst (no LLM provider configured)")})
            reasoning = build_reasoning(package, request.query)
            yield _sse("step", {"key": "reasoning", "status": "complete", "label": "Analyst report generated", "detail": _reasoning_detail(reasoning)})

            yield _sse("report", InvestigationReport(package=package, reasoning=reasoning).model_dump(mode="json"))
            yield _sse("done", {"ok": True})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


async def _run_and_build_packet(db: Session, query: str, limit: int):
    plan = InvestigationPlanner().build_plan(query=query)
    package = await InvestigationExecutor(session=db).execute(InvestigationExecutionRequest(plan=plan, limit_per_connector=limit))
    reasoning = build_reasoning(package, query)
    return build_packet_document(package, reasoning, subject=query, generated_at=datetime.now(timezone.utc))


@router.get("/evidence-packet.html", response_class=HTMLResponse)
async def evidence_packet_html(query: str = Query(..., min_length=1), limit_per_connector: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)) -> HTMLResponse:
    doc = await _run_and_build_packet(db, query, limit_per_connector)
    return HTMLResponse(content=render_packet_html(doc))


@router.get("/evidence-packet")
async def evidence_packet_json(query: str = Query(..., min_length=1), limit_per_connector: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)) -> dict:
    from dataclasses import asdict
    doc = await _run_and_build_packet(db, query, limit_per_connector)
    return asdict(doc)
