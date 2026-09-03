from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.ecosystem_graph import EcosystemGraphResponse
from app.services.ecosystem_graph import build_ecosystem_graph

router = APIRouter(prefix="/api/ecosystem", tags=["ecosystem"])


@router.get("/graph", response_model=EcosystemGraphResponse)
def get_ecosystem_graph(
    company_id: UUID | None = Query(default=None),
    tender_id: UUID | None = Query(default=None),
    buyer: str | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    db: Session = Depends(get_db),
) -> EcosystemGraphResponse:
    return build_ecosystem_graph(
        db=db,
        company_id=company_id,
        tender_id=tender_id,
        buyer=buyer,
        depth=depth,
    )
