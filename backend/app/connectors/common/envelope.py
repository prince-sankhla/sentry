"""Canonical raw-record envelope + normalized-record builders.

The on-disk envelope is the durable provenance/preservation layer: it keeps
``source_url``, ``retrieved_at``, a stable ``content_hash`` (so unchanged
records are never re-imported) and the full list of document/attachment URLs
so future OCR/RAG can be layered on without changing the architecture.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.connectors.base import (
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedSourceMetadata,
    NormalizedTender,
    NormalizedCompany,
    NormalizedAward,
    NormalizedEntity,
)
from app.connectors.common.parse import now_utc, optional_string

ENVELOPE_VERSION = 1


def content_hash(data: Any) -> str:
    """Stable SHA-256 of a record payload, used to skip unchanged records."""
    serialized = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_envelope(
    *,
    source_name: str,
    source_record_id: str,
    source_url: str | None,
    data: Any,
    documents: list[dict[str, Any]] | None = None,
    retrieved_at: datetime | None = None,
    content_type: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "envelope_version": ENVELOPE_VERSION,
        "source_name": source_name,
        "source_record_id": source_record_id,
        "source_url": source_url,
        "retrieved_at": (retrieved_at or now_utc()).isoformat(),
        "content_hash": content_hash(data),
        "documents": documents or [],
        "data": data,
    }
    if content_type:
        envelope["content_type"] = content_type
    if etag:
        envelope["etag"] = etag
    if last_modified:
        envelope["last_modified"] = last_modified
    if extra:
        envelope.update(extra)
    return envelope


def write_envelope(path: Path, envelope: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(envelope, file, ensure_ascii=False, indent=2)
        file.write("\n")


def make_document(
    *,
    title: str,
    url: str | None,
    document_type: str,
    metadata: NormalizedSourceMetadata,
) -> NormalizedDocument:
    return NormalizedDocument(title=title, url=url, document_type=document_type, metadata=metadata)


def documents_from_envelope(
    raw_record: dict[str, Any],
    metadata: NormalizedSourceMetadata,
) -> list[NormalizedDocument]:
    """Rebuild NormalizedDocument entries for every preserved attachment URL.

    Always yields the source notice itself (so the primary URL is never lost)
    plus one entry per attachment recorded in the envelope's ``documents`` list.
    """
    documents: list[NormalizedDocument] = []
    if metadata.source_url:
        documents.append(
            make_document(
                title="Source notice",
                url=metadata.source_url,
                document_type="source_notice",
                metadata=metadata,
            )
        )
    for entry in raw_record.get("documents") or []:
        if not isinstance(entry, dict):
            continue
        url = optional_string(entry.get("url"))
        if not url or url == metadata.source_url:
            continue
        doc_metadata = NormalizedSourceMetadata(
            source_name=metadata.source_name,
            source_record_id=f"{metadata.source_record_id}:doc:{content_hash(url)[:12]}",
            source_url=url,
            retrieved_at=metadata.retrieved_at,
        )
        documents.append(
            make_document(
                title=optional_string(entry.get("title")) or "Attachment",
                url=url,
                document_type=optional_string(entry.get("document_type")) or "attachment",
                metadata=doc_metadata,
            )
        )
    return documents


def build_record(
    *,
    tender: NormalizedTender,
    companies: list[NormalizedCompany],
    awards: list[NormalizedAward],
    documents: list[NormalizedDocument],
    raw: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    base = NormalizedProcurementRecord(
        tender=tender, companies=companies, awards=awards, documents=documents, raw=raw
    )
    return NormalizedProcurementRecord(
        tender=tender,
        companies=companies,
        awards=awards,
        documents=documents,
        entities=entity_extractor(base),
        raw=raw,
    )
