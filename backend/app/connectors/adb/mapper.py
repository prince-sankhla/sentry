from __future__ import annotations

from typing import Any, Callable

from app.connectors.base import NormalizedEntity, NormalizedProcurementRecord
from app.connectors.common.generic_mapper import FieldHints, map_flat_record

SOURCE_NAME = "adb"
SOURCE_LABEL = "Asian Development Bank Procurement"

_HINTS = FieldHints(
    title=("notice_title", "title", "project_name", "contract_title", "description"),
    buyer=("executing_agency", "borrower", "country", "department", "agency"),
    reference=("contract_number", "reference", "notice_id", "csrn", "id"),
    value=("contract_amount", "amount", "value"),
    supplier=("contractor", "supplier", "awarded", "vendor"),
    award_value=("contract_amount", "awarded_amount"),
    award_date=("contract_award_date", "award_date", "signing_date"),
)


def map_record(
    raw_record: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    return map_flat_record(
        raw_record,
        source_name=SOURCE_NAME,
        reference_prefix="ADB",
        entity_extractor=entity_extractor,
        hints=_HINTS,
        currency_default="USD",
    )
