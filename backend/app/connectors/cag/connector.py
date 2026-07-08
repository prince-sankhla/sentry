from __future__ import annotations

from typing import Any

from app.connectors.base import (
    FileBackedSourceConnector,
    NormalizedProcurementRecord,
    SourceConnectorMetadata,
)
from app.connectors.cag.mapper import SOURCE_LABEL, SOURCE_NAME, map_record
from app.connectors.registry import register_connector


@register_connector
class CAGSourceConnector(FileBackedSourceConnector):
    metadata = SourceConnectorMetadata(name=SOURCE_NAME, label=SOURCE_LABEL, raw_directory="cag")

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        return map_record(raw_record, entity_extractor=self.extractEntities)
