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
from app.schemas.investigation_executor import (
    InvestigationExecutionRequest,
    InvestigationPackage,
)
from app.schemas.investigation_reasoning import InvestigationReasoning
from app.schemas.priority_queue import PriorityQueueResponse
from app.services.priority_queue import build_priority_queue
from app.services.entity_resolution_service import resolve_entities
from app.services.investigation_planner import InvestigationPlanner
from app.services.investigation_executor import InvestigationExecutor
from app.services.investigation_reasoning import build_reasoning
from app.services.investigation_packet import build_packet_document, render_packet_html
from app.clients.llm import available_providers, get_llm_client
from app.api.routes.web import search_web
from app.api.routes.web_context import search_web_context, WebContextSearchRequest
from app.webintel.schemas import SearchRequest

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class LLMProviderStatus(BaseModel):
    """Observability for the multi-provider reasoning chain."""

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
    """Human-readable attribution for the completed reasoning SSE step."""
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
    """Procurement Context Analyzer — trusted procurement context for one finding."""
    from types import SimpleNamespace

    from app.verified_context import ProcurementContextAnalyzer

    finding = SimpleNamespace(id=finding_id, name=finding_name or finding_id)
    return ProcurementContextAnalyzer().analyze(finding, jurisdiction=jurisdiction)


class ContextAnalysisRequest(BaseModel):
    """Evidence-driven context analysis: the finding plus the retrieved facts."""

    finding_id: str
    finding_name: str = ""
    jurisdiction: str = ""
    facts: dict | None = None


@router.post("/context-analysis")
def context_analysis_with_facts(request: ContextAnalysisRequest):
    """Procurement Context Analyzer with applicability evaluation."""
    from types import SimpleNamespace

    from app.verified_context import ContextFacts, ProcurementContextAnalyzer

    finding = SimpleNamespace(id=request.finding_id, name=request.finding_name or request.finding_id)
    facts = ContextFacts.model_validate(request.facts) if request.facts is not None else None
    return ProcurementContextAnalyzer().analyze(
        finding, facts=facts, jurisdiction=request.jurisdiction
    )


@router.get("/priority-queue", response_model=PriorityQueueResponse)
def priority_queue(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PriorityQueueResponse:
    """Priority Investigation Queue — built from the CURRENT procurement database."""
    return build_priority_queue(db, limit=limit)


class EntityResolutionRequest(BaseModel):
    query: str


@router.post("/resolve-entity", response_model=EntityResolutionResult)
def resolve_entity(request: EntityResolutionRequest, db: Session = Depends(get_db)) -> EntityResolutionResult:
    """Resolve free text to ranked canonical entity candidates before investigating."""
    return resolve_entities(db, request.query)


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
    """Run a full investigation from one free-text prompt, streaming live progress."""

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield _sse("step", {"key": "resolve_entity", "status": "running", "label": "Resolving canonical entity"})
            try:
                resolution = resolve_entities(db, request.query)
                yield _sse("candidates", resolution.model_dump(mode="json"))
                detail = (
                    f"{len(resolution.candidates)} candidate(s)"
                    + (" · selection recommended" if resolution.requires_disambiguation else "")
                )
            except Exception:
                detail = "resolution skipped"
            yield _sse("step", {"key": "resolve_entity", "status": "complete", "label": "Entity resolution complete", "detail": detail})

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
            risk_v2 = package.risk_assessment_v2
            indicators_detail = f"{len(package.indicators)} indicators"
            if risk_v2 is not None:
                indicators_detail += (
                    f" · {len(risk_v2.patterns)} pattern(s) · "
                    f"{risk_v2.overall_severity} (deterministic V2)"
                )
            yield _sse(
                "step",
                {
                    "key": "indicators",
                    "status": "complete",
                    "label": "Risk engine complete",
                    "detail": indicators_detail,
                },
            )
            documents_available = sum(1 for r in package.records if r.documents)
            yield _sse(
                "step",
                {
                    "key": "evidence",
                    "status": "complete",
                    "label": "Evidence engine complete",
                    "detail": f"{len(package.evidence)} evidence items · {documents_available} documents",
                },
            )
            yield _sse(
                "step",
                {
                    "key": "grounding",
                    "status": "complete",
                    "label": "Grounding verified",
                    "detail": f"{len(package.graph.nodes)} graph nodes anchored to source records",
                },
            )

            # Automatic open-source intelligence is additive. Procurement web
            # pages are stored in the web evidence subsystem; historical/news
            # context is stored without a WebProcurementEvidence link, so it
            # cannot change the deterministic risk engine.
            web_procurement_count = 0
            web_context_count = 0
            yield _sse(
                "step",
                {
                    "key": "web_search",
                    "status": "running",
                    "label": "Searching the open web",
                    "detail": "Searching current tender, contract and procurement records…",
                },
            )
            try:
                web_result = search_web(SearchRequest(query=request.query), db)
                web_procurement_count = len(web_result.stored_pages)
                yield _sse(
                    "step",
                    {
                        "key": "web_search",
                        "status": "running",
                        "label": "Searching procurement web sources",
                        "detail": f"Found {len(web_result.search_results)} results · captured {web_procurement_count} procurement pages…",
                    },
                )
            except Exception as exc:
                yield _sse(
                    "step",
                    {
                        "key": "web_search",
                        "status": "running",
                        "label": "Searching procurement web sources",
                        "detail": f"Current web evidence unavailable · continuing safely ({type(exc).__name__})",
                    },
                )

            yield _sse(
                "step",
                {
                    "key": "web_search",
                    "status": "running",
                    "label": "Reading historical context",
                    "detail": "Checking past tender, contract, audit and procurement coverage…",
                },
            )
            try:
                context_result = search_web_context(
                    WebContextSearchRequest(
                        query=request.query,
                        focus="tender contract procurement news audit investigation history",
                        limit=8,
                    ),
                    db,
                )
                web_context_count = int(context_result.get("downloaded_pages", 0))
            except Exception:
                web_context_count = 0

            yield _sse(
                "step",
                {
                    "key": "web_search",
                    "status": "complete",
                    "label": "Open-source intelligence collected",
                    "detail": f"{web_procurement_count} procurement pages · {web_context_count} context pages · news/history excluded from risk scoring",
                },
            )

            provider_status = _provider_status()
            yield _sse(
                "step",
                {
                    "key": "reasoning",
                    "status": "running",
                    "label": "Analyst reasoning over evidence",
                    "detail": (
                        f"Engaging {', '.join(provider_status.providers)}"
                        if provider_status.mode == "llm"
                        else "Deterministic analyst (no LLM provider configured)"
                    ),
                },
            )
            reasoning = build_reasoning(package, request.query)
            yield _sse(
                "step",
                {
                    "key": "reasoning",
                    "status": "complete",
                    "label": "Analyst report generated",
                    "detail": _reasoning_detail(reasoning),
                },
            )

            report = InvestigationReport(package=package, reasoning=reasoning)
            yield _sse("report", report.model_dump(mode="json"))
            yield _sse("done", {"ok": True})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def _run_and_build_packet(db: Session, query: str, limit: int):
    """Reuse the full pipeline (plan → execute → reason) and assemble the packet."""
    plan = InvestigationPlanner().build_plan(query=query)
    executor = InvestigationExecutor(session=db)
    package = await executor.execute(
        InvestigationExecutionRequest(plan=plan, limit_per_connector=limit)
    )
    reasoning = build_reasoning(package, query)
    doc = build_packet_document(
        package, reasoning, subject=query, generated_at=datetime.now(timezone.utc)
    )
    return doc


@router.get("/evidence-packet.html", response_class=HTMLResponse)
async def evidence_packet_html(
    query: str = Query(..., min_length=1),
    limit_per_connector: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """One-click Evidence Packet export: a self-contained, print-ready HTML document."""
    doc = await _run_and_build_packet(db, query, limit_per_connector)
    return HTMLResponse(content=render_packet_html(doc))


@router.get("/evidence-packet")
async def evidence_packet_json(
    query: str = Query(..., min_length=1),
    limit_per_connector: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Structured Evidence Packet (the same 15 grounded sections) for API consumers."""
    from dataclasses import asdict

    doc = await _run_and_build_packet(db, query, limit_per_connector)
    return asdict(doc)
