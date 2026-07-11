"""State eProcurement connectors — one registered connector per NIC portal.

Reuses the CPPP mapper (identical NIC markup) with a per-state source name and
reference prefix, so state tenders normalize into the same SENTRY schema.
"""

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
from app.connectors.cppp.mapper import MappedNotice, map_notice
from app.connectors.common.envelope import documents_from_envelope
from app.connectors.common.generic_mapper import FieldHints, map_flat_record
from app.connectors.registry import register_connector
from app.connectors.state_eproc.portals import STATE_PORTALS, StatePortal


_STATE_HINTS = FieldHints(
    title=("tender_title", "title", "work_description", "description", "item", "subject"),
    buyer=("department", "organisation", "organization", "ministry", "buyer", "agency", "office"),
    reference=("tender_id", "tender_reference", "reference_no", "nit_no", "bid_no", "id"),
    value=("tender_value", "estimated_value", "emd_amount", "amount", "value"),
    published=("published_date", "publish_date", "notice_date", "start_date", "created_date"),
    closing=("closing_date", "bid_submission_end", "due_date", "end_date"),
    supplier=("awarded_to", "supplier", "vendor", "contractor", "bidder"),
    supplier_reg=("gstin", "pan", "vendor_id", "registration"),
    award_value=("award_value", "contract_value", "awarded_amount"),
    award_date=("award_date", "contract_date"),
    category=("category", "sector", "classification", "tender_category"),
    location=("state", "district", "city", "location"),
)


class _StateEProcConnector(FileBackedSourceConnector):
    portal: StatePortal

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        data = raw_record.get("data") if isinstance(raw_record.get("data"), dict) else {}
        detail_html = data.get("detail_html")
        if not isinstance(detail_html, str) or not detail_html.strip():
            return map_flat_record(
                raw_record,
                source_name=self.portal.name,
                reference_prefix=self.portal.name.upper(),
                entity_extractor=self.extractEntities,
                hints=_STATE_HINTS,
                currency_default="INR",
            )
        mapped = map_notice(
            detail_html,
            source_url=str(raw_record.get("source_url") or ""),
            retrieved_at=_parse_datetime(raw_record.get("retrieved_at")) or datetime.now(UTC),
            source_name=self.portal.name,
            reference_prefix=self.portal.name.upper(),
        )
        return self._to_record(mapped, raw_record)

    def _to_record(self, mapped: MappedNotice, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
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
        base = NormalizedProcurementRecord(
            tender=tender, companies=companies, awards=awards, documents=documents, raw=raw_record
        )
        return NormalizedProcurementRecord(
            tender=tender,
            companies=companies,
            awards=awards,
            documents=documents,
            entities=self.extractEntities(base),
            raw=raw_record,
        )


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _build_connectors() -> list[type[_StateEProcConnector]]:
    classes: list[type[_StateEProcConnector]] = []
    for portal in STATE_PORTALS:
        connector_cls = type(
            f"StateEProc_{portal.name}",
            (_StateEProcConnector,),
            {
                "portal": portal,
                "metadata": SourceConnectorMetadata(
                    name=portal.name,
                    label=portal.label,
                    raw_directory=portal.name,
                    data_source=portal.base_url,
                    last_update_capability="resumable raw-file incremental sync",
                    import_mechanism=f"{portal.parser} state eProcurement downloader + generic importer",
                    normalization_quality=(
                        "NIC HTML parser with JSON/tabular fallback"
                        if portal.parser == "nic"
                        else "generic public-record mapper for non-NIC state portal exports"
                    ),
                ),
            },
        )
        classes.append(register_connector(connector_cls))
    return classes


STATE_CONNECTORS = _build_connectors()
