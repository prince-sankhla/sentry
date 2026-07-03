from __future__ import annotations

from typing import Any

from app.connectors.base import (
    FileBackedSourceConnector,
    NormalizedAward,
    NormalizedCompany,
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedSourceMetadata,
    NormalizedTender,
    SourceConnectorMetadata,
)
from app.connectors.registry import register_connector
from app.importers.prozorro import ParsedProzorroTender, parse_tender


@register_connector
class ProzorroSourceConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(
        name="prozorro",
        label="ProZorro",
        raw_directory="prozorro",
    )

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        payload = raw_record.get("data") if isinstance(raw_record.get("data"), dict) else raw_record
        parsed = parse_tender(
            payload,
            source_url=_optional_string(raw_record.get("source_url")),
            retrieved_at=None,
        )
        return _to_normalized_record(parsed, raw_record)


def _to_normalized_record(parsed: ParsedProzorroTender, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
    tender_metadata = NormalizedSourceMetadata(
        source_name=parsed.tender.source_name or "prozorro",
        source_record_id=parsed.tender.source_record_id or parsed.tender.reference_number,
        source_url=parsed.tender.source_url,
        retrieved_at=parsed.tender.retrieved_at,
    )
    tender = NormalizedTender(
        reference_number=parsed.tender.reference_number,
        title=parsed.tender.title,
        description=parsed.tender.description,
        procuring_entity=parsed.tender.procuring_entity,
        published_date=parsed.tender.published_date,
        closing_date=None,
        estimated_value=parsed.tender.estimated_value,
        currency=parsed.tender.currency,
        metadata=tender_metadata,
    )
    companies = [
        NormalizedCompany(
            name=company.name,
            registration_number=company.registration_number,
            metadata=NormalizedSourceMetadata(
                source_name=company.source_name or "prozorro",
                source_record_id=company.source_record_id or company.registration_number or company.name,
                source_url=company.source_url,
                retrieved_at=company.retrieved_at,
            ),
        )
        for company in parsed.companies
    ]
    awards = [
        NormalizedAward(
            tender_reference_number=award.tender_reference_number,
            company_name=award.company_name,
            company_registration_number=award.company_registration_number,
            award_date=award.award_date,
            award_value=award.award_value,
            currency=award.currency,
            metadata=NormalizedSourceMetadata(
                source_name=award.source_name or "prozorro",
                source_record_id=award.source_record_id or f"{award.tender_reference_number}:{award.company_registration_number or award.company_name}",
                source_url=award.source_url,
                retrieved_at=award.retrieved_at,
            ),
        )
        for award in parsed.awards
    ]
    documents = [
        NormalizedDocument(
            title="ProZorro tender notice",
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
        entities=ProzorroSourceConnector().extractEntities(record),
        raw=raw_record,
    )


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
