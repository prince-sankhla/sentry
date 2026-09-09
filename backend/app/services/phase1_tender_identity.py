from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Tender
from app.schemas.tenders import BuyerInfo, CompanySummary, TenderDetail, TenderSummary
from app.services.pdf_intelligence import extract_tender_fields
from app.services.procurement_intelligence import build_tender_intelligence
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES


def get_exact_tender(db: Session, tender_id: UUID) -> TenderDetail:
    tender = db.execute(
        select(Tender)
        .where(Tender.id == tender_id, Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .options(joinedload(Tender.awards).joinedload(Award.company), joinedload(Tender.documents))
    ).unique().scalar_one_or_none()
    if tender is None:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} was not found.")

    companies = sorted(
        {award.company for award in tender.awards if award.company is not None},
        key=lambda company: company.name,
    )
    document_text = "\n".join(part for part in (tender.title, tender.description) if part)
    return TenderDetail(
        **TenderSummary.model_validate(tender).model_dump(),
        description=tender.description,
        buyer=BuyerInfo(name=tender.procuring_entity),
        awards=tender.awards,
        participating_companies=[CompanySummary.model_validate(company) for company in companies],
        intelligence=build_tender_intelligence(db, tender),
        pdf_intelligence=extract_tender_fields(document_text),
    )
