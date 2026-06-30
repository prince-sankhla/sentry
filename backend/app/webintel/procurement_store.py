from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Award, Company, Tender
from app.webintel.models import WebEvidence, WebProcurementEvidence
from app.webintel.procurement_extractor import ProcurementExtraction, extract_procurement_intelligence, normalize_company_name


def ensure_procurement_evidence(session: Session, web_evidence: WebEvidence) -> WebProcurementEvidence:
    existing = session.scalar(
        select(WebProcurementEvidence).where(WebProcurementEvidence.web_evidence_id == web_evidence.id)
    )
    extraction = extract_procurement_intelligence(
        query=web_evidence.query,
        title=web_evidence.title,
        content=web_evidence.content,
    )
    links = _find_links(session, extraction)

    if existing is None:
        existing = WebProcurementEvidence(web_evidence_id=web_evidence.id)
        session.add(existing)

    existing.tender_id = links["tender_id"]
    existing.company_id = links["company_id"]
    existing.award_id = links["award_id"]
    existing.company_name = _limit(extraction.company_name, 500)
    existing.normalized_company_name = _limit(extraction.normalized_company_name, 500)
    existing.government_buyer = _limit(extraction.government_buyer, 500)
    existing.tender_title = extraction.tender_title
    existing.contract_title = extraction.contract_title
    existing.contract_value = extraction.contract_value
    existing.currency = _limit(extraction.currency, 3)
    existing.tender_category = _limit(extraction.tender_category, 255)
    existing.procurement_sector = _limit(extraction.procurement_sector, 255)
    existing.country = _limit(extraction.country, 100)
    existing.publication_date = extraction.publication_date
    existing.award_date = extraction.award_date
    existing.contract_number = _limit(extraction.contract_number, 255)
    existing.tender_number = _limit(extraction.tender_number, 255)
    existing.organization = _limit(extraction.organization, 500)
    existing.people_mentioned = extraction.people_mentioned
    existing.related_companies = extraction.related_companies
    existing.raw_signals = extraction.raw_signals
    session.flush()
    return existing


def _limit(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def _find_links(session: Session, extraction: ProcurementExtraction) -> dict[str, object | None]:
    tender = _find_tender(session, extraction)
    company = _find_company(session, extraction)
    award = _find_award(session, tender, company)
    return {
        "tender_id": tender.id if tender else None,
        "company_id": company.id if company else None,
        "award_id": award.id if award else None,
    }


def _find_tender(session: Session, extraction: ProcurementExtraction) -> Tender | None:
    candidates = [value for value in [extraction.tender_number, extraction.contract_number] if value]
    if candidates:
        tender = session.scalar(select(Tender).where(Tender.reference_number.in_(candidates)).limit(1))
        if tender:
            return tender

    title = extraction.tender_title or extraction.contract_title
    if title and len(title) >= 12:
        return session.scalar(select(Tender).where(Tender.title.ilike(f"%{title[:80]}%")).limit(1))
    return None


def _find_company(session: Session, extraction: ProcurementExtraction) -> Company | None:
    names = [name for name in [extraction.company_name, extraction.normalized_company_name] if name]
    if not names:
        return None

    exact = session.scalar(select(Company).where(or_(Company.name.in_(names), Company.registration_number.in_(names))).limit(1))
    if exact:
        return exact

    normalized_target = extraction.normalized_company_name
    if not normalized_target:
        return None
    for company in session.scalars(select(Company).limit(500)):
        if normalize_company_name(company.name) == normalized_target:
            return company
    return None


def _find_award(session: Session, tender: Tender | None, company: Company | None) -> Award | None:
    if tender is None or company is None:
        return None
    return session.scalar(
        select(Award).where(Award.tender_id == tender.id, Award.company_id == company.id).limit(1)
    )
