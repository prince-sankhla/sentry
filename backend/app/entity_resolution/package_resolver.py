from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import NAMESPACE_URL, uuid5

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - dependency fallback keeps imports resilient.
    fuzz = None

from app.entity_resolution.normalizer import canonical_aliases, normalize_company_name
from app.entity_resolution.utils import compact_unique, extract_domain, normalize_registration_number
from app.schemas.investigation_executor import (
    CanonicalCompany,
    CanonicalCompanyMatchedSource,
    InvestigationAwardResult,
    InvestigationCompanyResult,
    InvestigationPackage,
)


@dataclass
class EntityMatch:
    matched: bool
    confidence: float
    reason: str


@dataclass
class CompanyObservation:
    source_type: str
    source_id: str
    source_name: str
    source_record_id: str
    alias: str
    tender_reference_number: str
    record_index: int
    company: InvestigationCompanyResult | None = None
    award: InvestigationAwardResult | None = None

    @property
    def registration_number(self) -> str | None:
        if self.company is not None:
            return self.company.registration_number
        if self.award is not None:
            return self.award.company_registration_number
        return None

    @property
    def tax_id(self) -> str | None:
        if self.company is not None:
            return self.company.tax_id
        if self.award is not None:
            return self.award.company_tax_id
        return None

    @property
    def company_identifier(self) -> str | None:
        if self.company is not None:
            return self.company.company_identifier
        if self.award is not None:
            return self.award.company_identifier
        return None

    @property
    def address(self) -> str | None:
        if self.company is not None:
            return self.company.address
        if self.award is not None:
            return self.award.company_address
        return None

    @property
    def website(self) -> str | None:
        if self.company is not None:
            return self.company.website
        if self.award is not None:
            return self.award.company_website
        return None


class InvestigationEntityResolver:
    def resolve_package(self, package: InvestigationPackage) -> InvestigationPackage:
        observations = _collect_observations(package)
        groups: list[list[tuple[CompanyObservation, EntityMatch]]] = []

        for observation in observations:
            best_index: int | None = None
            best_match = EntityMatch(False, 0.0, "no_match")
            for index, group in enumerate(groups):
                match = self._match_group(group, observation)
                if match.matched and match.confidence > best_match.confidence:
                    best_index = index
                    best_match = match
            if best_index is None:
                groups.append([(observation, EntityMatch(True, 1.0, "seed"))])
            else:
                groups[best_index].append((observation, best_match))

        canonical_companies = [_canonical_company(group) for group in groups]
        for group, canonical in zip(groups, canonical_companies):
            for observation, _match in group:
                if observation.company is not None:
                    observation.company.canonical_company_id = canonical.id
                if observation.award is not None:
                    observation.award.canonical_company_id = canonical.id

        for index, record in enumerate(package.records):
            ids = [
                *(company.canonical_company_id for company in record.companies),
                *(award.canonical_company_id for award in record.awards),
            ]
            record.canonical_company_ids = compact_unique(ids)

        package.canonical_companies = canonical_companies
        return package

    def _match_group(self, group: list[tuple[CompanyObservation, EntityMatch]], candidate: CompanyObservation) -> EntityMatch:
        best = EntityMatch(False, 0.0, "no_match")
        for existing, _existing_match in group:
            match = match_observations(existing, candidate)
            if match.confidence > best.confidence:
                best = match
        return best


def match_observations(left: CompanyObservation, right: CompanyObservation) -> EntityMatch:
    for left_value, right_value, confidence, reason in [
        (left.registration_number, right.registration_number, 1.0, "registration_number"),
        (left.tax_id, right.tax_id, 0.99, "tax_id"),
        (left.company_identifier, right.company_identifier, 0.98, "company_identifier"),
    ]:
        left_normalized = normalize_registration_number(left_value)
        right_normalized = normalize_registration_number(right_value)
        if left_normalized and right_normalized:
            if left_normalized == right_normalized:
                return EntityMatch(True, confidence, reason)
            return EntityMatch(False, 0.0, f"{reason}_conflict")

    left_domain = extract_domain(left.website)
    right_domain = extract_domain(right.website)
    if left_domain and right_domain:
        if left_domain == right_domain:
            return EntityMatch(True, 0.94, "website_domain")
        return EntityMatch(False, 0.0, "website_domain_conflict")

    left_name = normalize_company_name(left.alias)
    right_name = normalize_company_name(right.alias)
    if not left_name or not right_name:
        return EntityMatch(False, 0.0, "empty_name")
    if left.alias.casefold().strip() == right.alias.casefold().strip():
        return EntityMatch(True, 0.97, "exact_name")
    if left_name == right_name:
        return EntityMatch(True, 0.93, "normalized_name")

    name_score = _similarity(left_name, right_name)
    address_score = _similarity(_normalize_address(left.address), _normalize_address(right.address))
    if name_score >= 0.94:
        return EntityMatch(True, round(name_score * 0.90, 2), "fuzzy_name")
    if name_score >= 0.86 and address_score >= 0.85:
        return EntityMatch(True, round((name_score * 0.65) + (address_score * 0.25), 2), "fuzzy_name_address")
    return EntityMatch(False, round(max(name_score, address_score) * 0.80, 2), "below_threshold")


def _collect_observations(package: InvestigationPackage) -> list[CompanyObservation]:
    observations: list[CompanyObservation] = []
    for record_index, record in enumerate(package.records):
        tender_reference = record.tender.reference_number
        for company in record.companies:
            source_id = company.metadata.source_record_id or f"{tender_reference}:company:{company.name}"
            observations.append(
                CompanyObservation(
                    source_type="procurement_company",
                    source_id=source_id,
                    source_name=company.metadata.source_name,
                    source_record_id=company.metadata.source_record_id,
                    alias=company.name,
                    tender_reference_number=tender_reference,
                    record_index=record_index,
                    company=company,
                )
            )
        for award in record.awards:
            source_id = award.metadata.source_record_id or f"{tender_reference}:award:{award.company_name}"
            observations.append(
                CompanyObservation(
                    source_type="procurement_award",
                    source_id=source_id,
                    source_name=award.metadata.source_name,
                    source_record_id=award.metadata.source_record_id,
                    alias=award.company_name,
                    tender_reference_number=tender_reference,
                    record_index=record_index,
                    award=award,
                )
            )
    return observations


def _canonical_company(group: list[tuple[CompanyObservation, EntityMatch]]) -> CanonicalCompany:
    observations = [observation for observation, _match in group]
    canonical_name = _choose_canonical_name(observations)
    canonical_key = _canonical_key(observations, canonical_name)
    return CanonicalCompany(
        id=str(uuid5(NAMESPACE_URL, f"sentry:canonical-company:{canonical_key}")),
        canonical_name=canonical_name,
        aliases=canonical_aliases(*(observation.alias for observation in observations)),
        confidence=min(match.confidence for _observation, match in group),
        matched_sources=[
            CanonicalCompanyMatchedSource(
                source_type=observation.source_type,
                source_id=observation.source_id,
                source_name=observation.source_name,
                source_record_id=observation.source_record_id,
                alias=observation.alias,
                confidence=match.confidence,
                match_reason=match.reason,
                tender_reference_number=observation.tender_reference_number,
            )
            for observation, match in group
        ],
        matched_procurement_records=compact_unique([observation.tender_reference_number for observation in observations]),
    )


def _canonical_key(observations: list[CompanyObservation], canonical_name: str) -> str:
    for getter, prefix in [
        (lambda observation: normalize_registration_number(observation.registration_number), "registration"),
        (lambda observation: normalize_registration_number(observation.tax_id), "tax"),
        (lambda observation: normalize_registration_number(observation.company_identifier), "identifier"),
        (lambda observation: extract_domain(observation.website), "website"),
    ]:
        for observation in observations:
            value = getter(observation)
            if value:
                return f"{prefix}:{value}"
    return f"name:{normalize_company_name(canonical_name)}"


def _choose_canonical_name(observations: list[CompanyObservation]) -> str:
    return sorted((observation.alias.strip() for observation in observations), key=lambda name: (-len(name), name.casefold()))[0]


def _normalize_address(address: str | None) -> str:
    if not address:
        return ""
    normalized = address.casefold()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return max(float(fuzz.ratio(left, right)), float(fuzz.token_sort_ratio(left, right))) / 100
    return SequenceMatcher(None, left, right).ratio()
