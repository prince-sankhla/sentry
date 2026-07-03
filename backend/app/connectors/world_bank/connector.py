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
from app.connectors.registry import register_connector
from app.connectors.world_bank.mapper import map_notice
from app.connectors.world_bank.models import SOURCE_LABEL, SOURCE_NAME, MappedNotice


@register_connector
class WorldBankSourceConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(
        name=SOURCE_NAME,
        label=SOURCE_LABEL,
        raw_directory="world_bank",
    )

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        payload = raw_record.get("data") if isinstance(raw_record.get("data"), dict) else raw_record
        notice_id = str(payload.get("id") or raw_record.get("source_record_id") or "").strip()
        source_url = raw_record.get("source_url") or f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
        mapped = map_notice(
            payload,
            source_url=source_url,
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
    documents = [
        NormalizedDocument(
            title="World Bank procurement notice",
            url=tender_metadata.source_url,
            document_type="source_notice",
            metadata=tender_metadata,
        )
    ] if tender_metadata.source_url else []
    record = NormalizedProcurementRecord(tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record)
    return NormalizedProcurementRecord(
        tender=tender,
        companies=companies,
        awards=awards,
        documents=documents,
        entities=WorldBankSourceConnector().extractEntities(record),
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
