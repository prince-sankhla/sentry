from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.profiles import ProfileResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/tender/{tender_id}", response_model=ProfileResponse)
async def tender_profile(tender_id: UUID, db: Session = Depends(get_db)) -> ProfileResponse:
    profile = await ProfileService(db).tender_profile(tender_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return profile


@router.get("/company/{company_id}", response_model=ProfileResponse)
async def company_profile(company_id: UUID, db: Session = Depends(get_db)) -> ProfileResponse:
    profile = await ProfileService(db).company_profile(company_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return profile


@router.get("/buyer", response_model=ProfileResponse)
async def buyer_profile(
    name: str = Query(min_length=1, max_length=255), db: Session = Depends(get_db)
) -> ProfileResponse:
    profile = await ProfileService(db).buyer_profile(name)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found")
    return profile
