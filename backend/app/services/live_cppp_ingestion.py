from __future__ import annotations

import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.connectors.common.http import BaseHttpDownloader
from app.connectors.common.parse import now_utc
from app.connectors.cppp.connector import CPPPSourceConnector
from app.importers.generic import GenericConnectorImporter

_CPPP_HOSTS = {"eprocure.gov.in", "www.eprocure.gov.in"}
_TENDER_ID_RE = re.compile(r"\b\d{4}_[A-Z0-9]+_\d+_\d+\b", re.I)


class LiveCPPPIngestionError(ValueError):
    pass


class LiveCPPPIngestion:
    source_name = "cppp"

    def _validate_url(self, url: str) -> str:
        value = url.strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in _CPPP_HOSTS:
            raise LiveCPPPIngestionError("Only an official CPPP URL from eprocure.gov.in is accepted.")
        return value

    def _extract_tender_id(self, text: str) -> str | None:
        match = _TENDER_ID_RE.search(text or "")
        return match.group(0) if match else None

    def fetch(self, url: str) -> dict:
        source_url = self._validate_url(url)
        try:
            with httpx.Client(timeout=httpx.Timeout(30.0), follow_redirects=True, headers={"User-Agent": BaseHttpDownloader.user_agent}) as client:
                response = client.get(source_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LiveCPPPIngestionError(f"CPPP page could not be fetched: {exc}") from exc

        html = response.text
        tender_id = self._extract_tender_id(html) or self._extract_tender_id(source_url)
        if not tender_id:
            raise LiveCPPPIngestionError("No CPPP Tender ID was found on the supplied page.")

        documents = CPPPSourceConnector().normalize({
            "source_name": self.source_name,
            "source_record_id": tender_id,
            "source_url": source_url,
            "retrieved_at": now_utc().isoformat(),
            "data": {"detail_html": html},
        })
        # Rebuild the raw envelope from the live HTML so the existing generic importer
        # preserves documents, content hash, version history and provenance exactly as
        # it does for file-backed imports.
        with tempfile.TemporaryDirectory(prefix="sentry-cppp-") as tmp:
            out = Path(tmp)
            downloader = BaseHttpDownloader(out)
            downloader.save_record(
                record_id=tender_id,
                source_url=source_url,
                data={"detail_html": html},
                retrieved_at=now_utc(),
                content_type=response.headers.get("content-type"),
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
            importer = GenericConnectorImporter(self._db_session, self.source_name, batch_size=1)
            stats = importer.import_directory(out)

        return {
            "status": "imported" if stats.imported_tenders or stats.updated_tenders else "unchanged",
            "tender_id": tender_id,
            "source_url": source_url,
            "retrieved_at": now_utc().isoformat(),
            "imported_tenders": stats.imported_tenders,
            "updated_tenders": stats.updated_tenders,
            "imported_companies": stats.imported_companies,
            "imported_awards": stats.imported_awards,
            "imported_documents": stats.imported_documents,
            "unchanged_records": stats.unchanged_records,
            "failed": stats.failed,
            "message": "Live CPPP tender normalized and stored with provenance." if not stats.failed else "Live CPPP tender fetched but import reported failures.",
        }

    def ingest(self, db, url: str) -> dict:
        self._db_session = db
        try:
            return self.fetch(url)
        finally:
            self._db_session = None
