"""Canonical raw-record envelope + normalized-record builders.

The on-disk envelope is the durable provenance/preservation layer: it keeps
``source_url``, ``retrieved_at``, a stable ``content_hash`` (so unchanged
records are never re-imported) and the full list of document/attachment URLs
so future OCR/RAG can be layered on without changing the architecture.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

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


_NIC_DOC_TYPE_MAP = {
    "nit document": "nit",
    "boq": "boq",
    "tender documents": "tender_document",
    "tender document": "tender_document",
    "work item documents": "work_item",
    "corrigendum": "corrigendum",
}


def _nic_doc_type(label: str) -> str:
    key = re.sub(r"\s+", " ", _strip_tags(label)).strip().lower()
    return _NIC_DOC_TYPE_MAP.get(key) or re.sub(r"[^a-z0-9]+", "_", key).strip("_") or "attachment"


def _strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _extract_nic_documents(detail_html: str, base_url: str) -> list[dict[str, Any]]:
    """Surface primary NIC/GePNIC procurement documents from a stored detail page.

    Reads the two standard NIC document tables already present in the detail HTML
    we retrieve — the "NIT Document" table (``docDownoad`` anchors) and the
    "Work Item Documents" table — and returns one ``{title, url, document_type}``
    entry per document. Identity + URL + type only; PDF bytes are never fetched.
    """
    documents: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()

    # 1. NIT Document table: <a id="docDownoad*" href="...">filename</a>
    for match in re.finditer(
        r'<a\b[^>]*\bid="docDownoad[^"]*"[^>]*\bhref="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
        detail_html,
        re.IGNORECASE,
    ):
        title = html.unescape(match.group(2)).strip()
        if not title:
            continue
        url = urljoin(base_url, html.unescape(match.group(1)))
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        documents.append({"title": title, "url": url, "document_type": "nit"})

    # 2. Work Item Documents table: Document Type cell + filename span + download link
    work_item = re.search(
        r'id="workItemDocumenttable".*?</table>', detail_html, re.IGNORECASE | re.DOTALL
    )
    if work_item:
        for row in re.split(r'(?=<tr\b[^>]*\bid="informal_\d+")', work_item.group(0))[1:]:
            name = re.search(r"([A-Za-z0-9][\w.\- ]*\.[A-Za-z0-9]{2,5})\s*</span>", row)
            if not name:
                continue
            title = html.unescape(name.group(1)).strip()
            cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.DOTALL)
            type_label = cells[1] if len(cells) > 1 else "work_item"
            href = re.search(r'href="([^"]*\bcomponent=[^"]+)"', row)
            url = urljoin(base_url, html.unescape(href.group(1))) if href else None
            key = (title, url)
            if key in seen:
                continue
            seen.add(key)
            documents.append(
                {"title": title, "url": url, "document_type": _nic_doc_type(type_label)}
            )

    return documents


def documents_from_envelope(
    raw_record: dict[str, Any],
    metadata: NormalizedSourceMetadata,
) -> list[NormalizedDocument]:
    """Rebuild NormalizedDocument entries for every preserved attachment URL.

    Always yields the source notice itself (so the primary URL is never lost)
    plus one entry per attachment recorded in the envelope's ``documents`` list.
    When that list is empty, fall back to parsing the primary NIC/GePNIC document
    tables out of the stored detail HTML, so already-downloaded records surface
    their NIT/BoQ/Tender documents without any re-scraping.
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
    entries = raw_record.get("documents") or []
    if not entries and metadata.source_url:
        data = raw_record.get("data")
        detail_html = data.get("detail_html") if isinstance(data, dict) else None
        if isinstance(detail_html, str) and detail_html.strip():
            entries = _extract_nic_documents(detail_html, metadata.source_url)
    for entry in entries:
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
