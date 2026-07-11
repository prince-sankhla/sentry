"""Facade: deterministic normalization."""
from app.normalization import (  # noqa: F401
    normalize_currency, normalize_document_title, normalize_org_name,
    normalize_reference, normalize_registration, normalize_text,
    org_match_key, is_normalized_org,
)
