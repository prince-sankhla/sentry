from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.live_cppp_ingestion import LiveCPPPIngestion, LiveCPPPIngestionError
from app.services.live_gem_ingestion import LiveGeMIngestion, LiveGeMIngestionError

router = APIRouter(prefix="/api/live-ingestion", tags=["live-ingestion"])


class LiveTenderIngestRequest(BaseModel):
    url: str = Field(min_length=20, max_length=4000)


class LiveTenderIngestResponse(BaseModel):
    status: str
    tender_id: str
    tender_pk: str
    reference_number: str
    source_url: str
    retrieved_at: str
    imported_tenders: int
    updated_tenders: int
    imported_companies: int
    imported_awards: int
    imported_documents: int
    unchanged_records: int
    failed: int
    message: str


@router.post("/cppp", response_model=LiveTenderIngestResponse)
def ingest_cppp_tender(payload: LiveTenderIngestRequest, db: Session = Depends(get_db)) -> LiveTenderIngestResponse:
    try:
        result = LiveCPPPIngestion().ingest(db, payload.url)
    except LiveCPPPIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Live CPPP ingestion failed: {exc}") from exc
    return LiveTenderIngestResponse(**result)


@router.post("/gem", response_model=LiveTenderIngestResponse)
def ingest_gem_tender(payload: LiveTenderIngestRequest, db: Session = Depends(get_db)) -> LiveTenderIngestResponse:
    try:
        result = LiveGeMIngestion().ingest(db, payload.url)
    except LiveGeMIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Live GeM ingestion failed: {exc}") from exc
    return LiveTenderIngestResponse(**result)
