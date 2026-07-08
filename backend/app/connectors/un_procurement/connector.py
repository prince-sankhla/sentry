from __future__ import annotations

from typing import Any

from app.connectors.base import (
    FileBackedSourceConnector,
    NormalizedProcurementRecord,
    SourceConnectorMetadata,
)
from app.connectors.registry import register_connector
from app.connectors.un_procurement.mapper import SOURCE_LABEL, SOURCE_NAME, map_record


@register_connector
class UNProcurementSourceConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(name=SOURCE_NAME, label=SOURCE_LABEL, raw_directory="un_procurement")

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        return map_record(raw_record, entity_extractor=self.extractEntities)
