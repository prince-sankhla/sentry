from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceConnectorMetadata:
    name: str
    label: str
    version: str = "1.0"
    raw_directory: str | None = None
    data_source: str | None = None
    supported_entities: tuple[str, ...] = (
        "Tender",
        "Buyer",
        "Supplier",
        "Award",
        "Document",
        "Evidence",
    )
    last_update_capability: str = "raw-file incremental sync"
    import_mechanism: str = "file-backed normalized import"
    normalization_quality: str = "maps source records into SENTRY normalized procurement records"
    public_access_notes: str = "public-source data only"


@dataclass(frozen=True)
class NormalizedSourceMetadata:
    source_name: str
    source_record_id: str
    source_url: str | None
    retrieved_at: datetime | None


@dataclass(frozen=True)
class NormalizedTender:
    reference_number: str
    title: str
    description: str | None
    procuring_entity: str | None
    published_date: date | None
    closing_date: date | None
    estimated_value: Decimal | None
    currency: str
    metadata: NormalizedSourceMetadata


@dataclass(frozen=True)
class NormalizedCompany:
    name: str
    registration_number: str | None
    metadata: NormalizedSourceMetadata


@dataclass(frozen=True)
class NormalizedAward:
    tender_reference_number: str
    company_name: str
    company_registration_number: str | None
    award_date: date | None
    award_value: Decimal | None
    currency: str
    metadata: NormalizedSourceMetadata


@dataclass(frozen=True)
class NormalizedDocument:
    title: str
    url: str | None
    document_type: str
    metadata: NormalizedSourceMetadata


@dataclass(frozen=True)
class NormalizedEntity:
    name: str
    entity_type: str
    source_record_id: str
    registration_number: str | None = None


@dataclass(frozen=True)
class NormalizedProcurementRecord:
    tender: NormalizedTender
    companies: list[NormalizedCompany] = field(default_factory=list)
    awards: list[NormalizedAward] = field(default_factory=list)
    documents: list[NormalizedDocument] = field(default_factory=list)
    entities: list[NormalizedEntity] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    metadata: SourceConnectorMetadata

    @abstractmethod
    def search(self, query: str, limit: int = 25) -> list[NormalizedProcurementRecord]:
        raise NotImplementedError

    @abstractmethod
    def fetchTender(self, tender_id: str) -> NormalizedTender | None:
        raise NotImplementedError

    @abstractmethod
    def fetchAwards(self, tender_id: str) -> list[NormalizedAward]:
        raise NotImplementedError

    @abstractmethod
    def fetchDocuments(self, tender_id: str) -> list[NormalizedDocument]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_record: dict[str, Any]) -> NormalizedProcurementRecord:
        raise NotImplementedError

    @abstractmethod
    def extractEntities(self, record: NormalizedProcurementRecord | dict[str, Any]) -> list[NormalizedEntity]:
        raise NotImplementedError


class FileBackedSourceConnector(SourceConnector):
    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = data_root or Path(__file__).resolve().parents[3] / "data" / "raw"

    @property
    def raw_directory(self) -> Path | None:
        if self.metadata.raw_directory is None:
            return None
        return self.data_root / self.metadata.raw_directory

    def search(self, query: str, limit: int = 25) -> list[NormalizedProcurementRecord]:
        normalized_query = query.strip().casefold()
        if not normalized_query:
            return []

        results: list[NormalizedProcurementRecord] = []
        for raw_record in self._iter_raw_records():
            try:
                record = self.normalize(raw_record)
            except Exception:
                logger.exception("Skipping invalid %s source record during search.", self.metadata.name)
                continue
            if self._matches(record, normalized_query):
                results.append(record)
                if len(results) >= limit:
                    break
        return results

    def fetchTender(self, tender_id: str) -> NormalizedTender | None:
        record = self._find_record(tender_id)
        return record.tender if record is not None else None

    def fetchAwards(self, tender_id: str) -> list[NormalizedAward]:
        record = self._find_record(tender_id)
        return record.awards if record is not None else []

    def fetchDocuments(self, tender_id: str) -> list[NormalizedDocument]:
        record = self._find_record(tender_id)
        return record.documents if record is not None else []

    def extractEntities(self, record: NormalizedProcurementRecord | dict[str, Any]) -> list[NormalizedEntity]:
        normalized = self.normalize(record) if isinstance(record, dict) else record
        entities = [
            NormalizedEntity(
                name=normalized.tender.procuring_entity,
                entity_type="buyer",
                source_record_id=normalized.tender.metadata.source_record_id,
            )
        ] if normalized.tender.procuring_entity else []
        entities.extend(
            NormalizedEntity(
                name=company.name,
                entity_type="supplier",
                source_record_id=company.metadata.source_record_id,
                registration_number=company.registration_number,
            )
            for company in normalized.companies
        )
        return entities

    def _find_record(self, tender_id: str) -> NormalizedProcurementRecord | None:
        normalized_id = tender_id.strip().casefold()
        for raw_record in self._iter_raw_records():
            try:
                record = self.normalize(raw_record)
            except Exception:
                logger.exception("Skipping invalid %s source record during fetch.", self.metadata.name)
                continue
            tender = record.tender
            if normalized_id in {
                tender.reference_number.casefold(),
                tender.metadata.source_record_id.casefold(),
            }:
                return record
        return None

    def _iter_raw_records(self) -> Iterator[dict[str, Any]]:
        directory = self.raw_directory
        if directory is None or not directory.exists():
            return

        for path in sorted(directory.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as file:
                    payload = json.load(file)
            except Exception:
                logger.exception("Skipping unreadable source record %s.", path)
                continue
            if isinstance(payload, dict):
                yield payload

    def _matches(self, record: NormalizedProcurementRecord, query: str) -> bool:
        haystack = " ".join(
            value
            for value in [
                record.tender.reference_number,
                record.tender.title,
                record.tender.description or "",
                record.tender.procuring_entity or "",
                *(company.name for company in record.companies),
                *(company.registration_number or "" for company in record.companies),
            ]
            if value
        ).casefold()
        return query in haystack


def normalize_metadata(metadata: Any) -> NormalizedSourceMetadata:
    return NormalizedSourceMetadata(
        source_name=metadata.source_name,
        source_record_id=metadata.source_record_id,
        source_url=getattr(metadata, "source_url", None),
        retrieved_at=getattr(metadata, "retrieved_at", None),
    )
