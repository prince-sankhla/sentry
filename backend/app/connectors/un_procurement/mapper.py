from __future__ import annotations

from typing import Any, Callable

from app.connectors.base import NormalizedEntity, NormalizedProcurementRecord
from app.connectors.common.generic_mapper import FieldHints, map_flat_record

SOURCE_NAME = "un_procurement"
SOURCE_LABEL = "United Nations Procurement (UNGM)"

_HINTS = FieldHints(
    title=("title", "notice_title", "subject", "description"),
    buyer=("agency", "organization", "un_organization", "buyer"),
    reference=("reference", "reference_no", "notice_id", "id"),
    value=("value", "estimated_value", "amount"),
    published=("published", "publication_date", "issue_date", "start_date"),
    closing=("deadline", "closing_date", "response_deadline", "end_date"),
    supplier=("supplier", "awarded_to", "vendor", "contractor"),
    location=("country", "duty_station", "location"),
)


def map_record(
    raw_record: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    return map_flat_record(
        raw_record,
        source_name=SOURCE_NAME,
        reference_prefix="UN",
        entity_extractor=entity_extractor,
        hints=_HINTS,
        currency_default="USD",
    )
