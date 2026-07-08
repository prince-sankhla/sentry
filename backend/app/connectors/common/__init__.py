"""Shared, reusable ingestion primitives for SENTRY source connectors.

This package factors out the download/envelope/parse logic that every
connector needs so new procurement sources can be added without duplicating
HTTP, resume, dedup, provenance or document-preservation code.
"""

from app.connectors.common.envelope import (
    build_envelope,
    build_record,
    content_hash,
    documents_from_envelope,
    write_envelope,
)
from app.connectors.common.http import (
    BaseHttpDownloader,
    ConditionalCache,
    DownloadStats,
)
from app.connectors.common import parse

__all__ = [
    "BaseHttpDownloader",
    "ConditionalCache",
    "DownloadStats",
    "build_envelope",
    "build_record",
    "content_hash",
    "documents_from_envelope",
    "parse",
    "write_envelope",
]
