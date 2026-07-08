from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
import html

SOURCE_NAME = "cppp"


class CPPPMappingError(ValueError):
    """Raised when a CPPP raw record cannot be mapped."""


@dataclass(frozen=True)
class SourceMetadata:
    source_name: str
    source_record_id: str
    source_url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class MappedTender:
    reference_number: str
    title: str
    description: str | None
    procuring_entity: str | None
    published_date: date | None
    closing_date: date | None
    estimated_value: Decimal | None
    currency: str
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedCompany:
    name: str
    registration_number: str | None
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedAward:
    tender_reference_number: str
    company_name: str
    company_registration_number: str | None
    award_date: date | None
    award_value: Decimal | None
    currency: str
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedNotice:
    tender: MappedTender
    companies: list[MappedCompany] = field(default_factory=list)
    awards: list[MappedAward] = field(default_factory=list)


def map_notice_file(path: Path) -> MappedNotice:
    with path.open("r", encoding="utf-8") as file:
        envelope = json.load(file)

    if not isinstance(envelope, dict):
        raise CPPPMappingError("CPPP raw record root must be an object.")

    data = envelope.get("data")
    if not isinstance(data, dict):
        raise CPPPMappingError("CPPP raw record must contain a data object.")

    detail_html = data.get("detail_html")
    if not isinstance(detail_html, str) or not detail_html.strip():
        raise CPPPMappingError("CPPP raw record must contain detail_html.")

    source_url = _required_string(envelope, "source_url")
    retrieved_at = _parse_datetime(envelope.get("retrieved_at")) or datetime.now(UTC)
    return map_notice(detail_html, source_url=source_url, retrieved_at=retrieved_at)


def map_notice(
    detail_html: str,
    source_url: str,
    retrieved_at: datetime,
    source_name: str = SOURCE_NAME,
    reference_prefix: str = "CPPP",
) -> MappedNotice:
    fields = _extract_label_values(detail_html)
    tender_id = _first_field(fields, "Tender ID")
    tender_reference = _first_field(fields, "Tender Reference Number")
    if not tender_id and not tender_reference:
        raise CPPPMappingError("CPPP notice is missing Tender ID and Tender Reference Number.")

    record_id = tender_id or tender_reference
    reference_number = f"{reference_prefix}:{tender_reference or tender_id}"
    work_description = _first_field(fields, "Work Description")
    title = _first_field(fields, "Tender Title") or work_description or f"CPPP tender {record_id}"
    organisation_chain = _first_field(fields, "Organisation Chain")
    tender_value = _parse_decimal(_first_field(fields, "Tender Value in"))

    metadata = SourceMetadata(
        source_name=source_name,
        source_record_id=record_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
    )
    tender = MappedTender(
        reference_number=_truncate(reference_number, 100),
        title=_truncate(title, 500),
        description=work_description,
        procuring_entity=_truncate(organisation_chain, 255) if organisation_chain else None,
        published_date=_parse_date(_first_field(fields, "Published Date")),
        closing_date=_parse_date(
            _first_field(fields, "Bid Submission End Date")
            or _first_field(fields, "Document Download / Sale End Date")
            or _first_field(fields, "Closing Date")
        ),
        estimated_value=tender_value,
        currency="INR",
        metadata=metadata,
    )
    return MappedNotice(tender=tender)


def _extract_label_values(page_html: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    labels = {
        "organisation chain",
        "tender reference number",
        "tender id",
        "tender title",
        "work description",
        "tender value in",
        "published date",
        "bid submission end date",
        "document download / sale end date",
        "closing date",
    }
    pattern = re.compile(
        r'<td\b[^>]*class="[^"]*\btd_caption\b[^"]*"[^>]*>(?P<label>.*?)</td>\s*'
        r'<td\b[^>]*class="[^"]*\btd_field\b[^"]*"[^>]*>(?P<value>.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        normalized = _normalize_label(_html_to_text(match.group("label")))
        if normalized in labels:
            value = _html_to_text(match.group("value"))
            if value:
                fields.setdefault(normalized, value)
    return fields


def _first_field(fields: dict[str, str], label: str) -> str | None:
    normalized = _normalize_label(label)
    for key, value in fields.items():
        if key == normalized or key.startswith(normalized):
            return value
    return None


def _normalize_label(value: str) -> str:
    value = value.replace("₹", "")
    return re.sub(r"\s+", " ", value).strip().strip(":").lower()


def _html_to_text(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CPPPMappingError(f"Missing required string field: {key}")
    return value.strip()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    stripped = value.strip()
    for fmt in ("%d-%b-%Y %I:%M %p", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(stripped[:20], fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    normalized = re.sub(r"[^0-9.]", "", str(value))
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _truncate(value: str, length: int) -> str:
    return value.strip()[:length]
