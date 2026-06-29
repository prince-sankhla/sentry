from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.graph import GraphResponse
from app.services.graph import build_relationship_graph

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def get_graph(
    company_id: UUID | None = Query(default=None),
    tender_id: UUID | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    db: Session = Depends(get_db),
) -> GraphResponse:
    return build_relationship_graph(
        db=db,
        company_id=company_id,
        tender_id=tender_id,
        depth=depth,
    )
