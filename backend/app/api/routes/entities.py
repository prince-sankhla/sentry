from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.entity_resolution.models import CanonicalCompany, CanonicalCompanyLink
from app.entity_resolution.resolver import CompanyResolver
from app.entity_resolution.schemas import (
    CanonicalCompanyResponse,
    LinkedAward,
    LinkedProcurementCompany,
    LinkedSource,
    LinkedTender,
    LinkedWebEvidence,
)
from app.models import Award, Company, Tender
from app.webintel.models import WebEvidence, WebProcurementEvidence

router = APIRouter(prefix="/api/entities", tags=["entity-resolution"])


@router.get("/company/{id}", response_model=CanonicalCompanyResponse)
def get_canonical_company(id: UUID, db: Session = Depends(get_db)) -> CanonicalCompanyResponse:
    canonical = db.get(CanonicalCompany, id)
    if canonical is None:
        company = db.get(Company, id)
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company entity {id} was not found.",
            )
        canonical = CompanyResolver(db).resolve_company(company)
        db.commit()
        db.refresh(canonical)

    canonical = db.execute(
        select(CanonicalCompany)
        .where(CanonicalCompany.id == canonical.id)
        .options(joinedload(CanonicalCompany.links))
    ).unique().scalar_one()

    company_ids = [link.company_id for link in canonical.links if link.company_id is not None]
    companies = db.scalars(select(Company).where(Company.id.in_(company_ids))).all() if company_ids else []
    awards = (
        db.execute(
            select(Award).where(Award.company_id.in_(company_ids)).options(joinedload(Award.tender))
        ).unique().scalars().all()
        if company_ids
        else []
    )
    tender_by_id = {award.tender.id: award.tender for award in awards if award.tender is not None}

    web_evidence_rows = db.execute(
        select(WebProcurementEvidence, WebEvidence)
        .join(WebEvidence, WebEvidence.id == WebProcurementEvidence.web_evidence_id)
        .where(
            WebProcurementEvidence.id.in_(
                [
                    UUID(link.source_id)
                    for link in canonical.links
                    if link.source_type == "web_procurement_evidence"
                ]
            )
        )
    ).all()

    return CanonicalCompanyResponse(
        id=canonical.id,
        canonical_name=canonical.canonical_name,
        aliases=canonical.aliases or [],
        matched_sources=[
            LinkedSource(
                source_type=link.source_type,
                source_id=link.source_id,
                alias=link.alias,
                confidence=link.confidence,
                match_reason=link.match_reason,
            )
            for link in canonical.links
        ],
        confidence=canonical.confidence,
        linked_company_ids=[company.id for company in companies],
        linked_procurement_companies=[
            LinkedProcurementCompany(
                id=company.id,
                name=company.name,
                registration_number=company.registration_number,
                source_name=company.source_name,
                source_record_id=company.source_record_id,
            )
            for company in companies
        ],
        linked_web_evidence=[
            LinkedWebEvidence(
                id=web.id,
                url=web.url,
                title=web.title,
                source=web.source,
                retrieved_at=web.retrieved_at,
                company_name=evidence.company_name,
                tender_id=evidence.tender_id,
                award_id=evidence.award_id,
            )
            for evidence, web in web_evidence_rows
        ],
        linked_tenders=[
            LinkedTender(
                id=tender.id,
                reference_number=tender.reference_number,
                title=tender.title,
                procuring_entity=tender.procuring_entity,
                published_date=tender.published_date,
                estimated_value=tender.estimated_value,
                currency=tender.currency,
            )
            for tender in tender_by_id.values()
        ],
        linked_awards=[
            LinkedAward(
                id=award.id,
                tender_id=award.tender_id,
                company_id=award.company_id,
                award_date=award.award_date,
                award_value=award.award_value,
                currency=award.currency,
            )
            for award in awards
        ],
    )
