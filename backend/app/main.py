from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import companies, dashboard, entities, graph, tenders, web
from app.core.config import get_settings
from app.db.connection import verify_database_connection

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
    allow_methods=["GET", "POST"],
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
app.include_router(companies.router)
app.include_router(entities.router)
app.include_router(dashboard.router)
app.include_router(graph.router)
app.include_router(web.router)
