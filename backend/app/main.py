from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.connection import verify_database_connection
from app.services.investigation_safety_patch import apply_safety_patch

apply_safety_patch()

from app.api.routes import (  # noqa: E402
    analytics,
    benchmarks,
    buyer_kundali,
    companies,
    dashboard,
    entities,
    ecosystem_graph,
    field_reanalysis,
    field_verification,
    graph,
    investigations,
    investigation_field_leads,
    live_ingestion,
    monitoring,
    profiles,
    provenance,
    search,
    statistics,
    supplier_kundali,
    tender_kundali,
    tenders,
    web,
    web_archive,
    web_context,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    verify_database_connection()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_origin_regex=r"https://sentry-platform-evaluation(?:-[a-z0-9]+)?-prince-sankhla-s-projects\.vercel\.app",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Sentry Backend",
        "version": settings.app_version,
    }


app.include_router(tenders.router)
app.include_router(tender_kundali.router)
app.include_router(companies.router)
app.include_router(supplier_kundali.router)
app.include_router(buyer_kundali.router)
app.include_router(benchmarks.router)
app.include_router(analytics.router)
app.include_router(entities.router)
app.include_router(dashboard.router)
app.include_router(graph.router)
app.include_router(ecosystem_graph.router)
app.include_router(investigations.router)
app.include_router(investigation_field_leads.router)
app.include_router(field_verification.router)
app.include_router(field_reanalysis.router)
app.include_router(live_ingestion.router)
app.include_router(monitoring.router)
app.include_router(search.router)
app.include_router(statistics.router)
app.include_router(profiles.router)
app.include_router(web.router)
app.include_router(web_archive.router)
app.include_router(web_context.router)
app.include_router(provenance.router)
