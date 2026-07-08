"""Attachment extraction, download and linkage for NIC/CPPP-style sources.

Parses the tender detail HTML already preserved on disk to discover every
attachment (tender notice, BOQ, corrigendum, addendum, technical / financial
docs, ...), links each to its tender, downloads the bytes where the URL is a
publicly fetchable file, and records metadata + local path in ``documents``.
"""

from __future__ import annotations

import html as H
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.common.envelope import content_hash
from app.connectors.common.http import safe_filename
from app.models import Document, Tender

logger = logging.getLogger(__name__)

_FILE_EXT = r"pdf|zip|rar|docx?|xlsx?|pptx?|csv|xml"
_CHROME = ("help", "manual", "sitemap", "jquery", "bootstrap", "logo", "banner", "captcha", "readme", "instruction")
_HTML_MARKERS = ("<html", "<!doctype", "stale session", "session expired", "please login")
_DOWNLOADABLE_TYPES = (
    "application/pdf",
    "application/zip",
    "application/octet-stream",
    "application/msword",
    "application/vnd",
    "application/x-rar",
    "text/csv",
    "image/",
)


@dataclass
class Attachment:
    title: str
    url: str | None
    document_type: str


@dataclass
class AttachmentStats:
    documents_linked: int = 0
    documents_downloaded: int = 0
    download_failed: int = 0
    tenders_matched: int = 0
    envelopes: int = 0
    by_type: dict[str, int] = field(default_factory=dict)


def classify(title: str) -> str:
    lowered = title.lower()
    if "boq" in lowered or "bill of quantit" in lowered:
        return "boq"
    if "corrigend" in lowered:
        return "corrigendum"
    if "addend" in lowered:
        return "addendum"
    if "aoc" in lowered or "award" in lowered or "acceptance of" in lowered:
        return "aoc"
    if "tendernotice" in lowered or "nit" in lowered or "notice inviting" in lowered:
        return "tender_notice"
    if "tech" in lowered or "specification" in lowered:
        return "technical_spec"
    if "eligib" in lowered:
        return "eligibility"
    if "financ" in lowered or "price" in lowered or "boq_" in lowered:
        return "financial"
    return "attachment"


def extract_attachments(detail_html: str, base_url: str) -> list[Attachment]:
    """Extract attachment filenames + download URLs from NIC detail HTML."""
    attachments: list[Attachment] = []
    seen: set[str] = set()

    # 1. Anchor-based: NIC download anchors (id/href contain docDownoad) or
    #    anchors whose visible text is a real filename.
    for match in re.finditer(r"<a\b[^>]*>(.*?)</a>", detail_html, re.I | re.S):
        tag = match.group(0)
        text = re.sub(r"<[^>]+>", " ", match.group(1))
        text = re.sub(r"\s+", " ", H.unescape(text)).strip()
        href_match = re.search(r'href="([^"]+)"', tag)
        href = H.unescape(href_match.group(1)) if href_match else None
        is_download_anchor = "docdownoad" in tag.lower() or (href and "docdownoad" in href.lower())
        is_file_name = bool(re.search(rf"\.({_FILE_EXT})$", text, re.I))
        if not (is_download_anchor and text) and not is_file_name:
            continue
        title = text if is_file_name or text else "attachment"
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        url = urljoin(base_url + "/", href) if href else base_url
        attachments.append(Attachment(title=title[:500], url=url, document_type=classify(title)))

    # 2. Text fallback: document filenames (doc types only) referenced without
    #    a clean anchor, skipping obvious page-chrome files.
    for match in re.finditer(rf"([\w().\-]{{3,120}}\.({_FILE_EXT}))\b", detail_html, re.I):
        title = re.sub(r"\s+", " ", H.unescape(match.group(1))).strip()
        lowered = title.lower()
        if lowered in seen or any(token in lowered for token in _CHROME):
            continue
        seen.add(lowered)
        attachments.append(Attachment(title=title[:500], url=base_url, document_type=classify(title)))

    return attachments


class AttachmentImporter:
    def __init__(self, session: Session, attachments_root: Path, timeout: float = 30.0) -> None:
        self.session = session
        self.attachments_root = attachments_root
        self.timeout = httpx.Timeout(timeout)

    def link_source(self, source_name: str, envelopes: list[dict], download: bool = True) -> AttachmentStats:
        from app.connectors.registry import discover_connectors

        stats = AttachmentStats()
        by_source_id, by_reference = self._tender_index(source_name)
        connector = discover_connectors().get(source_name)
        seen: set[tuple] = set()
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for envelope in envelopes:
                stats.envelopes += 1
                # Resolve the tender via normalize() so we use the same identity
                # the importer stored (envelope-level ids can differ).
                source_record_id = str(envelope.get("source_record_id") or "")
                tender = by_source_id.get(source_record_id)
                if tender is None and connector is not None:
                    try:
                        record = connector.normalize(envelope)
                        tender = by_source_id.get(record.tender.metadata.source_record_id) or by_reference.get(
                            record.tender.reference_number
                        )
                        source_record_id = record.tender.metadata.source_record_id
                    except Exception:
                        tender = None
                if tender is None:
                    continue
                stats.tenders_matched += 1
                base_url = str(envelope.get("source_url") or "")
                data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
                attachments = self._collect(envelope, data, base_url)
                for attachment in attachments:
                    key = (tender.id, attachment.title)
                    if key in seen:
                        continue
                    seen.add(key)
                    self._upsert(client, tender, source_name, source_record_id, attachment, download, stats)
            self.session.commit()
        return stats

    def _collect(self, envelope: dict, data: dict, base_url: str) -> list[Attachment]:
        attachments: list[Attachment] = []
        detail_html = data.get("detail_html")
        if isinstance(detail_html, str) and detail_html.strip():
            attachments.extend(extract_attachments(detail_html, base_url))
        for entry in envelope.get("documents") or []:
            if isinstance(entry, dict) and entry.get("url"):
                title = str(entry.get("title") or "attachment")
                attachments.append(
                    Attachment(title=title[:500], url=str(entry["url"]), document_type=classify(title))
                )
        return _dedupe(attachments)

    def _upsert(
        self,
        client: httpx.Client,
        tender: Tender,
        source_name: str,
        source_record_id: str,
        attachment: Attachment,
        download: bool,
        stats: AttachmentStats,
    ) -> None:
        existing = self.session.scalar(
            select(Document).where(Document.tender_id == tender.id, Document.title == attachment.title)
        )
        document = existing or Document(
            tender_id=tender.id,
            title=attachment.title,
            document_type=attachment.document_type,
            url=attachment.url,
            source_name=source_name,
            source_record_id=f"{source_record_id}:{attachment.title}"[:255],
            retrieved_at=tender.retrieved_at,
        )
        if existing is None:
            self.session.add(document)
            stats.documents_linked += 1
            stats.by_type[attachment.document_type] = stats.by_type.get(attachment.document_type, 0) + 1

        if download and document.local_path is None and attachment.url:
            if self._download(client, tender, attachment, document):
                stats.documents_downloaded += 1
            else:
                stats.download_failed += 1

    def _download(self, client: httpx.Client, tender: Tender, attachment: Attachment, document: Document) -> bool:
        if not re.search(rf"\.({_FILE_EXT})(\?|$)", attachment.title, re.I) and not re.search(
            rf"\.({_FILE_EXT})(\?|$)", attachment.url or "", re.I
        ):
            return False  # not obviously a downloadable file (skip session-bound HTML endpoints)
        try:
            response = client.get(attachment.url)
            response.raise_for_status()
        except Exception:
            return False
        body = response.content
        head = body[:512].lower()
        content_type = response.headers.get("Content-Type", "").lower()
        if any(marker in head for marker in (m.encode() for m in _HTML_MARKERS)):
            return False
        if "text/html" in content_type and not any(t in content_type for t in _DOWNLOADABLE_TYPES):
            return False
        directory = self.attachments_root / safe_filename(document.source_name or "src") / safe_filename(
            tender.reference_number
        )
        directory.mkdir(parents=True, exist_ok=True)
        extension = _extension(attachment.title)
        path = directory / safe_filename(attachment.title)
        path.write_bytes(body)
        document.local_path = str(path)
        document.content_hash = content_hash(body.decode("latin-1"))
        document.file_size = len(body)
        document.file_extension = extension
        from app.connectors.common.parse import now_utc

        document.downloaded_at = now_utc()
        return True

    def _tender_index(self, source_name: str) -> tuple[dict[str, Tender], dict[str, Tender]]:
        rows = list(self.session.scalars(select(Tender).where(Tender.source_name == source_name)))
        by_source_id = {t.source_record_id: t for t in rows if t.source_record_id}
        by_reference = {t.reference_number: t for t in rows}
        return by_source_id, by_reference


def _dedupe(attachments: list[Attachment]) -> list[Attachment]:
    seen: set[str] = set()
    result: list[Attachment] = []
    for attachment in attachments:
        key = attachment.title.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(attachment)
    return result


def _extension(title: str) -> str | None:
    match = re.search(rf"\.({_FILE_EXT})$", title, re.I)
    return match.group(1).lower() if match else None
