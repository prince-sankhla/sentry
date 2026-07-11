from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.base import (
    FileBackedSourceConnector,
    NormalizedAward,
    NormalizedCompany,
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedTender,
    SourceConnectorMetadata,
    normalize_metadata,
)
from app.connectors.common.envelope import documents_from_envelope
from app.connectors.cppp.mapper import MappedNotice, map_notice
from app.connectors.registry import register_connector


@register_connector
class CPPPSourceConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(
        name="cppp",
        label="Central Public Procurement Portal",
        raw_directory="cppp",
    )

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        data = raw_record.get("data") if isinstance(raw_record.get("data"), dict) else {}
        detail_html = data.get("detail_html")
        if not isinstance(detail_html, str) or not detail_html.strip():
            raise ValueError("CPPP record is missing detail_html.")
        mapped = map_notice(
            detail_html,
            source_url=str(raw_record.get("source_url") or ""),
            retrieved_at=_parse_datetime(raw_record.get("retrieved_at")) or datetime.now(UTC),
        )
        return _to_normalized_record(mapped, raw_record)


def _to_normalized_record(mapped: MappedNotice, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
    tender_metadata = normalize_metadata(mapped.tender.metadata)
    tender = NormalizedTender(
        reference_number=mapped.tender.reference_number,
        title=mapped.tender.title,
        description=mapped.tender.description,
        procuring_entity=mapped.tender.procuring_entity,
        published_date=mapped.tender.published_date,
        closing_date=mapped.tender.closing_date,
        estimated_value=mapped.tender.estimated_value,
        currency=mapped.tender.currency,
        metadata=tender_metadata,
    )
    companies = [
        NormalizedCompany(
            name=company.name,
            registration_number=company.registration_number,
            metadata=normalize_metadata(company.metadata),
        )
        for company in mapped.companies
    ]
    awards = [
        NormalizedAward(
            tender_reference_number=award.tender_reference_number,
            company_name=award.company_name,
            company_registration_number=award.company_registration_number,
            award_date=award.award_date,
            award_value=award.award_value,
            currency=award.currency,
            metadata=normalize_metadata(award.metadata),
        )
        for award in mapped.awards
    ]
    documents = documents_from_envelope(raw_record, tender_metadata)
    record = NormalizedProcurementRecord(tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record)
    return NormalizedProcurementRecord(
        tender=tender,
        companies=companies,
        awards=awards,
        documents=documents,
        entities=CPPPSourceConnector().extractEntities(record),
        raw=raw_record,
    )


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
