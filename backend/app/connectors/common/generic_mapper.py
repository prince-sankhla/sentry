"""Defensive flat-record mapper shared by JSON/tabular procurement sources.

Government open-data feeds (data.gov.in, ADB, UN, ...) expose procurement rows
with wildly inconsistent column names. Rather than hand-write a mapper per
feed, this matches columns by fuzzy substring hints and produces a normalized
record. Unknown shapes degrade gracefully instead of raising.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Sequence

from app.connectors.base import (
    NormalizedAward,
    NormalizedCompany,
    NormalizedEntity,
    NormalizedProcurementRecord,
    NormalizedSourceMetadata,
    NormalizedTender,
)
from app.connectors.common.envelope import build_record, documents_from_envelope
from app.connectors.common.parse import (
    is_url,
    now_utc,
    optional_string,
    parse_date,
    parse_datetime,
    parse_decimal,
    truncate,
)


@dataclass(frozen=True)
class FieldHints:
    title: Sequence[str] = ("tender_title", "title", "subject", "notice_title", "name", "description")
    description: Sequence[str] = ("description", "work_description", "detail", "scope")
    buyer: Sequence[str] = ("organisation", "organization", "department", "ministry", "buyer", "entity", "agency", "procuring")
    reference: Sequence[str] = ("tender_reference", "reference_no", "reference", "tender_id", "notice_id", "bid_no", "contract_no")
    value: Sequence[str] = ("tender_value", "estimated_value", "value", "amount", "contract_value")
    published: Sequence[str] = ("published_date", "publish_date", "notice_date", "date_published", "issue_date", "start_date")
    closing: Sequence[str] = ("closing_date", "submission_end", "deadline", "bid_submission_end", "end_date", "due_date")
    supplier: Sequence[str] = ("supplier", "awarded_to", "vendor", "contractor", "bidder", "winner")
    supplier_reg: Sequence[str] = ("supplier_id", "vendor_id", "registration", "gstin", "pan")
    award_value: Sequence[str] = ("award_value", "awarded_amount", "contract_amount", "final_value")
    award_date: Sequence[str] = ("award_date", "contract_date", "date_of_award")
    category: Sequence[str] = ("category", "sector", "product", "classification")
    location: Sequence[str] = ("location", "state", "city", "region", "district", "country")
    document: Sequence[str] = ("document", "url", "link", "attachment", "file", "pdf")


def _pick(data: dict[str, Any], hints: Sequence[str]) -> str | None:
    lowered = {str(key).lower(): value for key, value in data.items()}
    for hint in hints:
        for key, value in lowered.items():
            if hint in key:
                text = optional_string(value)
                if text:
                    return text
    return None


def _pick_decimal(data: dict[str, Any], hints: Sequence[str]) -> Decimal | None:
    value = _pick(data, hints)
    return parse_decimal(value) if value is not None else None


def _pick_date(data: dict[str, Any], hints: Sequence[str]):
    value = _pick(data, hints)
    return parse_date(value) if value is not None else None


def _document_urls(data: dict[str, Any], hints: Sequence[str]) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for key, value in data.items():
        if any(hint in str(key).lower() for hint in hints) and is_url(value):
            documents.append({"title": str(key), "url": str(value).strip(), "document_type": "attachment"})
    return documents


def map_flat_record(
    raw_record: dict[str, Any],
    *,
    source_name: str,
    reference_prefix: str,
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
    hints: FieldHints | None = None,
    currency_default: str = "INR",
    currency: str | None = None,
) -> NormalizedProcurementRecord:
    hints = hints or FieldHints()
    data = raw_record.get("data") if isinstance(raw_record.get("data"), dict) else raw_record
    if not isinstance(data, dict):
        raise ValueError("flat record payload must be an object")

    source_record_id = optional_string(raw_record.get("source_record_id")) or _pick(data, hints.reference) or ""
    if not source_record_id:
        raise ValueError("flat record is missing an identifier")
    reference = _pick(data, hints.reference) or source_record_id
    reference_number = truncate(f"{reference_prefix}:{reference}", 100) or reference_number_fallback(reference_prefix, source_record_id)

    source_url = optional_string(raw_record.get("source_url"))
    retrieved_at = parse_datetime(raw_record.get("retrieved_at")) or now_utc()
    resolved_currency = currency or currency_default

    metadata = NormalizedSourceMetadata(
        source_name=source_name,
        source_record_id=source_record_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
    )

    title = truncate(_pick(data, hints.title) or f"{reference_prefix} record {reference}", 500)
    tender = NormalizedTender(
        reference_number=reference_number,
        title=title or reference_number,
        description=_pick(data, hints.description),
        procuring_entity=truncate(_pick(data, hints.buyer), 255),
        published_date=_pick_date(data, hints.published),
        closing_date=_pick_date(data, hints.closing),
        estimated_value=_pick_decimal(data, hints.value),
        currency=resolved_currency,
        metadata=metadata,
    )

    companies: list[NormalizedCompany] = []
    awards: list[NormalizedAward] = []
    supplier = _pick(data, hints.supplier)
    if supplier:
        supplier_reg = _pick(data, hints.supplier_reg)
        company_metadata = NormalizedSourceMetadata(
            source_name=source_name,
            source_record_id=f"{source_record_id}:company:{supplier_reg or supplier}",
            source_url=source_url,
            retrieved_at=retrieved_at,
        )
        companies.append(
            NormalizedCompany(
                name=truncate(supplier, 255) or supplier,
                registration_number=truncate(supplier_reg, 100),
                metadata=company_metadata,
            )
        )
        awards.append(
            NormalizedAward(
                tender_reference_number=reference_number,
                company_name=truncate(supplier, 255) or supplier,
                company_registration_number=truncate(supplier_reg, 100),
                award_date=_pick_date(data, hints.award_date) or tender.published_date,
                award_value=_pick_decimal(data, hints.award_value),
                currency=resolved_currency,
                metadata=NormalizedSourceMetadata(
                    source_name=source_name,
                    source_record_id=f"{source_record_id}:award:{supplier_reg or supplier}",
                    source_url=source_url,
                    retrieved_at=retrieved_at,
                ),
            )
        )

    documents = documents_from_envelope(raw_record, metadata)
    return build_record(
        tender=tender,
        companies=companies,
        awards=awards,
        documents=documents,
        raw=raw_record,
        entity_extractor=entity_extractor,
    )


def reference_number_fallback(prefix: str, source_record_id: str) -> str:
    return f"{prefix}:{source_record_id}"[:100]
