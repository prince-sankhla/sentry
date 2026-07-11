from __future__ import annotations

import html
import logging
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.connectors.world_bank.models import (
    SOURCE_NAME,
    MappedAward,
    MappedCompany,
    MappedNotice,
    MappedTender,
    SourceMetadata,
)

logger = logging.getLogger(__name__)


class WorldBankMappingError(ValueError):
    """Raised when a World Bank notice cannot be mapped."""


def map_notice_file(path: Path) -> MappedNotice:
    import json

    with path.open("r", encoding="utf-8") as file:
        envelope = json.load(file)

    if not isinstance(envelope, dict):
        raise WorldBankMappingError("Notice JSON root must be an object.")

    payload = envelope.get("data")
    if not isinstance(payload, dict):
        payload = envelope

    notice_id = _required_string(payload, "id")
    source_url = _optional_string(envelope.get("source_url")) or (
        f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
    )
    retrieved_at = _parse_datetime(envelope.get("retrieved_at")) or datetime.now(UTC)
    return map_notice(payload, source_url=source_url, retrieved_at=retrieved_at)


def map_notice(payload: dict[str, Any], source_url: str, retrieved_at: datetime) -> MappedNotice:
    notice_id = _required_string(payload, "id")
    bid_reference = _optional_string(payload.get("bid_reference_no"))
    project_name = _optional_string(payload.get("project_name"))
    description = _optional_string(payload.get("bid_description")) or _text_from_html(payload.get("notice_text"))
    metadata = SourceMetadata(
        source_name=SOURCE_NAME,
        source_record_id=notice_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
    )

    # `bid_reference_no` is NOT a unique key — a single solicitation is routinely
    # split into many lots that all share it (e.g. LK-MOA-448081 covers 4 separate
    # contract awards to the same supplier). Keying identity on it alone collapses
    # distinct awards into one tender row, which erases both supplier-concentration
    # and requirement-splitting signals — the exact patterns an investigation needs.
    # Bind the globally-unique notice `id`, but keep the solicitation reference as a
    # queryable prefix so lots under one solicitation can still be grouped
    # (WHERE reference_number LIKE 'WB:<bid_reference>:%').
    reference_number = _truncate(
        f"WB:{bid_reference}:{notice_id}" if bid_reference else f"WB:{notice_id}", 100
    )
    title = _truncate(description or project_name or f"World Bank procurement notice {notice_id}", 500)
    # NOTE (data semantics): for World Bank *contract-award* notices, `noticedate`
    # is the date the award notice was published — which is AFTER the tender
    # closed and was awarded. Mapping it to `published_date` therefore yields the
    # expected (non-anomalous) `award_date < published_date` and
    # `closing_date < published_date` orderings. This is inherent to award-notice
    # data, not a parse error.
    # TODO(risk-engine owner): the risk engine's "award before publication" /
    # broken-date signals should special-case World Bank award notices (via
    # payload["notice_type"]) so this notice-date semantics is not scored as an
    # anomaly. Data platform intentionally does not fabricate a synthetic
    # publication date here.
    published_date = _parse_date(payload.get("noticedate") or payload.get("submission_date"))
    closing_date = _parse_date(payload.get("submission_deadline_date"))
    award_rows = _parse_awarded_bidders(payload.get("notice_text"))
    estimated_value = _first_decimal(row.value for row in award_rows)
    currency = _first_currency(row.currency for row in award_rows)

    tender = MappedTender(
        reference_number=reference_number,
        title=title,
        description=description,
        procuring_entity=_optional_string(payload.get("contact_organization")) or project_name,
        published_date=published_date,
        closing_date=closing_date,
        estimated_value=estimated_value,
        currency=currency,
        metadata=metadata,
    )

    companies: list[MappedCompany] = []
    awards: list[MappedAward] = []
    award_date = _parse_award_date(payload.get("notice_text")) or published_date
    for row in award_rows:
        company_metadata = SourceMetadata(
            source_name=SOURCE_NAME,
            source_record_id=f"{notice_id}:company:{row.registration_number or row.name}",
            source_url=source_url,
            retrieved_at=retrieved_at,
        )
        award_metadata = SourceMetadata(
            source_name=SOURCE_NAME,
            source_record_id=f"{notice_id}:award:{row.registration_number or row.name}",
            source_url=source_url,
            retrieved_at=retrieved_at,
        )
        companies.append(
            MappedCompany(
                name=_truncate(row.name, 255),
                registration_number=_truncate(row.registration_number, 100) if row.registration_number else None,
                metadata=company_metadata,
            )
        )
        awards.append(
            MappedAward(
                tender_reference_number=reference_number,
                company_name=_truncate(row.name, 255),
                company_registration_number=_truncate(row.registration_number, 100) if row.registration_number else None,
                award_date=award_date,
                award_value=row.value,
                currency=row.currency or "USD",
                metadata=award_metadata,
            )
        )

    return MappedNotice(tender=tender, companies=_dedupe_companies(companies), awards=awards)


class _AwardedBidder:
    def __init__(
        self,
        name: str,
        registration_number: str | None,
        value: Decimal | None,
        currency: str,
    ) -> None:
        self.name = name
        self.registration_number = registration_number
        self.value = value
        self.currency = currency


def _parse_awarded_bidders(value: Any) -> list[_AwardedBidder]:
    text = _text_from_html(value)
    if not text or "Awarded Bidder" not in text:
        return []

    awarded_section = text.split("Awarded Bidder", 1)[1]
    awarded_section = re.split(r"\bEvaluated Bidder|\bRejected Bidder|\bBidder\(s\)", awarded_section, maxsplit=1)[0]

    names = []
    for match in re.finditer(r"([^\n]{3,200}?)\s*\(([\w\-./ ]{3,50})\)\s*\n", awarded_section):
        name = _clean_label(match.group(1))
        registration_number = match.group(2).strip()
        if name and not name.lower().startswith(("signed contract", "evaluated bid", "bid price")):
            names.append((name, registration_number))

    if not names:
        for line in awarded_section.splitlines():
            cleaned = _clean_label(line)
            if cleaned and not _looks_like_amount_or_label(cleaned):
                names.append((cleaned, None))
                break

    prices = _parse_signed_prices(awarded_section)
    rows: list[_AwardedBidder] = []
    for index, (name, registration_number) in enumerate(names):
        currency, amount = prices[index] if index < len(prices) else ("USD", None)
        rows.append(_AwardedBidder(name=name, registration_number=registration_number, value=amount, currency=currency))
    return rows


def _parse_signed_prices(text: str) -> list[tuple[str, Decimal | None]]:
    prices = []
    pattern = re.compile(r"Signed Contract price\s*\n\s*([A-Z]{3})\s+([0-9][0-9,.\s]*)", re.IGNORECASE)
    for match in pattern.finditer(text):
        prices.append((match.group(1).upper(), _parse_decimal(match.group(2))))
    return prices


def _parse_award_date(value: Any) -> date | None:
    text = _text_from_html(value)
    match = re.search(r"Date Notification of Award Issued\s*\n(?:\(YYYY/MM/DD\)\s*\n)?([0-9]{4}/[0-9]{2}/[0-9]{2})", text)
    if match:
        return _parse_date(match.group(1))
    return None


def _text_from_html(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = re.sub(r"(?i)<\s*(br|/div|/p|/h\d)\s*/?>", "\n", value)
    without_tags = re.sub(r"<[^>]+>", " ", normalized)
    decoded = html.unescape(without_tags)
    lines = [re.sub(r"\s+", " ", line).strip() for line in decoded.splitlines()]
    return "\n".join(line for line in lines if line)


def _dedupe_companies(companies: list[MappedCompany]) -> list[MappedCompany]:
    seen: set[tuple[str, str | None]] = set()
    deduped = []
    for company in companies:
        key = (company.name.strip().casefold(), company.registration_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(company)
    return deduped


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        if isinstance(value, int):
            return str(value)
        raise WorldBankMappingError(f"Missing required string field: {key}")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    stripped = value.strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(stripped[:20], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).date()
    except ValueError:
        return None


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


def _first_decimal(values: Any) -> Decimal | None:
    for value in values:
        if value is not None:
            return value
    return None


def _first_currency(values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()[:3].upper()
    return "USD"


def _truncate(value: str, length: int) -> str:
    return value.strip()[:length]


def _clean_label(value: str) -> str:
    return value.strip().strip(":").strip().strip('"')


def _looks_like_amount_or_label(value: str) -> bool:
    lowered = value.lower()
    return (
        len(value) < 3
        or lowered.startswith(("country:", "bid price", "evaluated bid", "signed contract", "uzs", "usd", "eur"))
        or bool(re.fullmatch(r"[0-9., ]+", value))
    )
