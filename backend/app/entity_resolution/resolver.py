from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entity_resolution.matcher import match_company
from app.entity_resolution.models import CanonicalCompany, CanonicalCompanyLink
from app.entity_resolution.normalizer import canonical_aliases, normalize_company_name
from app.entity_resolution.utils import compact_unique, normalize_registration_number, source_key
from app.models import Company
from app.webintel.models import WebProcurementEvidence


class CompanyResolver:
    def __init__(self, db: Session):
        self.db = db

    def resolve_company(self, company: Company) -> CanonicalCompany:
        canonical = self.resolve_name(
            company.name,
            registration_number=company.registration_number,
            source_type="procurement_company",
            source_id=str(company.id),
            company_id=company.id,
        )
        self._attach_matching_companies(canonical, company)
        self._attach_matching_web_evidence(canonical)
        self.db.flush()
        return canonical

    def resolve_name(
        self,
        name: str,
        *,
        registration_number: str | None = None,
        website: str | None = None,
        source_type: str,
        source_id: str,
        company_id: UUID | None = None,
    ) -> CanonicalCompany:
        existing_link = self.db.scalar(
            select(CanonicalCompanyLink).where(
                CanonicalCompanyLink.source_type == source_type,
                CanonicalCompanyLink.source_id == source_id,
            )
        )
        if existing_link is not None:
            return existing_link.canonical_company

        canonical = self._best_existing_match(name, registration_number=registration_number, website=website)
        match_reason = "new_entity"
        confidence = Decimal("1.0000")
        if canonical is None:
            canonical = CanonicalCompany(
                canonical_name=_choose_canonical_name(name),
                canonical_key=normalize_company_name(name),
                aliases=canonical_aliases(name),
                matched_sources=[],
                confidence=confidence,
                linked_company_ids=[],
            )
            self.db.add(canonical)
            self.db.flush()
        else:
            match = match_company(canonical.canonical_name, name)
            match_reason = match.reason
            confidence = Decimal(str(max(match.confidence, 0.8))).quantize(Decimal("0.0001"))

        self._add_link(
            canonical,
            source_type=source_type,
            source_id=source_id,
            alias=name,
            confidence=confidence,
            match_reason=match_reason,
            company_id=company_id,
            registration_number=registration_number,
            website=website,
        )
        return canonical

    def _best_existing_match(
        self,
        name: str,
        *,
        registration_number: str | None,
        website: str | None,
    ) -> CanonicalCompany | None:
        normalized = normalize_company_name(name)
        if not normalized:
            return None
        exact = self.db.scalar(select(CanonicalCompany).where(CanonicalCompany.canonical_key == normalized))
        if exact is not None:
            existing_registration = _source_registration(exact)
            incoming_registration = normalize_registration_number(registration_number)
            if existing_registration and incoming_registration and existing_registration != incoming_registration:
                return None
            return exact

        best: tuple[float, CanonicalCompany] | None = None
        for canonical in self.db.scalars(select(CanonicalCompany)).all():
            candidates = [canonical.canonical_name, *(canonical.aliases or [])]
            for alias in candidates:
                match = match_company(
                    alias,
                    name,
                    left_registration_number=_source_registration(canonical),
                    right_registration_number=registration_number,
                    left_website=_source_website(canonical),
                    right_website=website,
                )
                if match.matched and (best is None or match.confidence > best[0]):
                    best = (match.confidence, canonical)
        return best[1] if best else None

    def _attach_matching_companies(self, canonical: CanonicalCompany, seed: Company) -> None:
        for company in self.db.scalars(select(Company)).all():
            if company.id == seed.id:
                continue
            if self._company_is_linked(company.id):
                continue
            match = match_company(
                canonical.canonical_name,
                company.name,
                left_registration_number=_source_registration(canonical),
                right_registration_number=company.registration_number,
            )
            if match.matched:
                self._add_link(
                    canonical,
                    source_type="procurement_company",
                    source_id=str(company.id),
                    alias=company.name,
                    confidence=Decimal(str(match.confidence)).quantize(Decimal("0.0001")),
                    match_reason=match.reason,
                    company_id=company.id,
                    registration_number=company.registration_number,
                )

    def _attach_matching_web_evidence(self, canonical: CanonicalCompany) -> None:
        rows = self.db.scalars(
            select(WebProcurementEvidence).where(WebProcurementEvidence.company_name.isnot(None))
        ).all()
        for evidence in rows:
            if self._source_is_linked("web_procurement_evidence", str(evidence.id)):
                continue
            candidate_name = evidence.company_name or evidence.normalized_company_name
            if not candidate_name:
                continue
            match = match_company(canonical.canonical_name, candidate_name)
            if match.matched:
                self._add_link(
                    canonical,
                    source_type="web_procurement_evidence",
                    source_id=str(evidence.id),
                    alias=candidate_name,
                    confidence=Decimal(str(match.confidence)).quantize(Decimal("0.0001")),
                    match_reason=match.reason,
                    company_id=evidence.company_id,
                )

    def _company_is_linked(self, company_id: UUID) -> bool:
        return self.db.scalar(select(CanonicalCompanyLink.id).where(CanonicalCompanyLink.company_id == company_id)) is not None

    def _source_is_linked(self, source_type: str, source_id: str) -> bool:
        return self.db.scalar(
            select(CanonicalCompanyLink.id).where(
                CanonicalCompanyLink.source_type == source_type,
                CanonicalCompanyLink.source_id == source_id,
            )
        ) is not None

    def _add_link(
        self,
        canonical: CanonicalCompany,
        *,
        source_type: str,
        source_id: str,
        alias: str,
        confidence: Decimal,
        match_reason: str,
        company_id: UUID | None,
        registration_number: str | None = None,
        website: str | None = None,
    ) -> None:
        link = CanonicalCompanyLink(
            canonical_company_id=canonical.id,
            company_id=company_id,
            source_type=source_type,
            source_id=source_id,
            alias=alias,
            confidence=confidence,
            match_reason=match_reason,
        )
        self.db.add(link)
        aliases = compact_unique([*(canonical.aliases or []), alias])
        source = {
            "source_type": source_type,
            "source_id": source_id,
            "alias": alias,
            "confidence": str(confidence),
            "match_reason": match_reason,
            "key": source_key(source_type, source_id),
        }
        if registration_number:
            source["registration_number"] = registration_number
        if website:
            source["website"] = website
        existing_sources = [item for item in (canonical.matched_sources or []) if item.get("key") != source["key"]]
        canonical.aliases = aliases
        canonical.matched_sources = [*existing_sources, source]
        canonical.linked_company_ids = compact_unique([*(canonical.linked_company_ids or []), str(company_id) if company_id else None])
        canonical.confidence = min(Decimal(str(canonical.confidence or 1)), confidence)


def _choose_canonical_name(name: str) -> str:
    return " ".join(part.strip() for part in name.strip().split())


def _source_registration(canonical: CanonicalCompany) -> str | None:
    for source in canonical.matched_sources or []:
        registration = normalize_registration_number(source.get("registration_number"))
        if registration:
            return registration
    return None


def _source_website(canonical: CanonicalCompany) -> str | None:
    for source in canonical.matched_sources or []:
        website = source.get("website")
        if website:
            return str(website)
    return None
