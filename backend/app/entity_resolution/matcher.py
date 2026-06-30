from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - dependency fallback keeps local imports resilient.
    fuzz = None

from app.entity_resolution.normalizer import company_tokens, normalize_company_name
from app.entity_resolution.utils import extract_domain, normalize_registration_number


@dataclass(frozen=True)
class MatchCandidate:
    matched: bool
    confidence: float
    reason: str


def match_company(
    left_name: str,
    right_name: str,
    *,
    left_registration_number: str | None = None,
    right_registration_number: str | None = None,
    left_website: str | None = None,
    right_website: str | None = None,
) -> MatchCandidate:
    left_registration = normalize_registration_number(left_registration_number)
    right_registration = normalize_registration_number(right_registration_number)
    if left_registration and right_registration:
        if left_registration == right_registration:
            return MatchCandidate(True, 1.0, "registration_number")
        return MatchCandidate(False, 0.0, "registration_number_conflict")

    left_domain = extract_domain(left_website)
    right_domain = extract_domain(right_website)
    if left_domain and right_domain:
        if left_domain == right_domain:
            return MatchCandidate(True, 0.98, "website_domain")
        return MatchCandidate(False, 0.0, "website_domain_conflict")

    left_normalized = normalize_company_name(left_name)
    right_normalized = normalize_company_name(right_name)
    if not left_normalized or not right_normalized:
        return MatchCandidate(False, 0.0, "empty_name")
    if left_name.casefold().strip() == right_name.casefold().strip():
        return MatchCandidate(True, 0.99, "exact_name")
    if left_normalized == right_normalized:
        return MatchCandidate(True, 0.96, "normalized_name")

    tokens_left = company_tokens(left_name)
    tokens_right = company_tokens(right_name)
    overlap = len(tokens_left & tokens_right)
    smaller = min(len(tokens_left), len(tokens_right))
    token_coverage = overlap / smaller if smaller else 0
    if token_coverage == 1 and smaller >= 2:
        return MatchCandidate(True, 0.90, "normalized_token_subset")

    score = _fuzzy_score(left_normalized, right_normalized)

    if score >= 95 and token_coverage >= 0.8:
        return MatchCandidate(True, round(score / 100, 2), "fuzzy_name")
    if score >= 92 and token_coverage == 1 and smaller >= 2:
        return MatchCandidate(True, round(score / 100, 2), "fuzzy_token_subset")
    return MatchCandidate(False, round(score / 100, 2), "below_threshold")


def _fuzzy_score(left: str, right: str) -> float:
    if fuzz is not None:
        return float(max(fuzz.ratio(left, right), fuzz.token_sort_ratio(left, right)))
    return SequenceMatcher(None, left, right).ratio() * 100
