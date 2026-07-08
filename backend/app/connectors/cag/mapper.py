from __future__ import annotations

from typing import Any, Callable

from app.connectors.base import NormalizedEntity, NormalizedProcurementRecord
from app.connectors.common.generic_mapper import FieldHints, map_flat_record

SOURCE_NAME = "cag"
SOURCE_LABEL = "Comptroller and Auditor General Procurement Audit Reports"

_HINTS = FieldHints(
    title=("title", "report_title", "subject"),
    buyer=("audited_entity", "ministry", "department", "state"),
    reference=("report_no", "report_number", "reference", "id"),
    published=("published", "report_date", "tabled_date", "year"),
    document=("url", "report_url", "pdf", "link", "attachment"),
)


def map_record(
    raw_record: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    return map_flat_record(
        raw_record,
        source_name=SOURCE_NAME,
        reference_prefix="CAG",
        entity_extractor=entity_extractor,
        hints=_HINTS,
        currency_default="INR",
    )
