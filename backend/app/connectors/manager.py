from __future__ import annotations

from pathlib import Path

from app.connectors.base import (
    NormalizedAward,
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedTender,
    SourceConnector,
)
from app.connectors.classification import is_enabled_by_default
from app.connectors.common.source_priority import prioritize_source_names, source_rank
from app.connectors.registry import discover_connectors


class SourceManager:
    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = data_root
        self.registry = discover_connectors()

    def connectors(self, source_names: list[str] | None = None) -> list[SourceConnector]:
        # Always query Indian procurement sources first so results and the shared
        # search budget favour Indian data over international sources.
        if not source_names:
            # India-first scope: the *default* (unscoped) enumeration only yields
            # connectors enabled by default (Indian classes). International and
            # Experimental connectors stay registered and reachable when named
            # explicitly, but are excluded here unless re-enabled via env flag.
            # See app/connectors/classification.py and INDIA_SCOPE_PLAN.md.
            connectors = [
                connector
                for connector in self.registry.all(data_root=self.data_root)
                if is_enabled_by_default(connector.metadata.name)
            ]
            return sorted(connectors, key=lambda connector: source_rank(connector.metadata.name))
        ordered = prioritize_source_names(list(source_names))
        return [
            connector
            for source_name in ordered
            for connector in [self.registry.get(source_name, data_root=self.data_root)]
            if connector is not None
        ]

    def search(
        self,
        query: str,
        *,
        source_names: list[str] | None = None,
        limit: int = 25,
    ) -> list[NormalizedProcurementRecord]:
        results: list[NormalizedProcurementRecord] = []
        for connector in self.connectors(source_names):
            remaining = limit - len(results)
            if remaining <= 0:
                break
            results.extend(connector.search(query, limit=remaining))
        return results

    def fetchTender(self, tender_id: str, source_name: str | None = None) -> NormalizedTender | None:
        for connector in self.connectors([source_name] if source_name else None):
            tender = connector.fetchTender(tender_id)
            if tender is not None:
                return tender
        return None

    def fetchAwards(self, tender_id: str, source_name: str | None = None) -> list[NormalizedAward]:
        for connector in self.connectors([source_name] if source_name else None):
            awards = connector.fetchAwards(tender_id)
            if awards:
                return awards
        return []

    def fetchDocuments(self, tender_id: str, source_name: str | None = None) -> list[NormalizedDocument]:
        for connector in self.connectors([source_name] if source_name else None):
            documents = connector.fetchDocuments(tender_id)
            if documents:
                return documents
        return []

    def connector_names(self) -> list[str]:
        return self.registry.names()
