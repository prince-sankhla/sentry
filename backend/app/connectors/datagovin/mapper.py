from __future__ import annotations

from typing import Any, Callable

from app.connectors.base import NormalizedEntity, NormalizedProcurementRecord
from app.connectors.common.generic_mapper import map_flat_record

SOURCE_NAME = "datagovin"
SOURCE_LABEL = "data.gov.in Procurement Datasets"


def map_record(
    raw_record: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    return map_flat_record(
        raw_record,
        source_name=SOURCE_NAME,
        reference_prefix="DATAGOVIN",
        entity_extractor=entity_extractor,
        currency_default="INR",
    )
