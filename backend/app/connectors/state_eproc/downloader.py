"""State eProcurement downloader — CPPP downloader retargeted per NIC portal."""

from __future__ import annotations

from pathlib import Path

from app.connectors.cppp.downloader import CPPPDownloader
from app.connectors.state_eproc.portals import STATE_PORTALS, StatePortal


class StateEProcDownloader(CPPPDownloader):
    def __init__(self, output_dir: Path, portal: StatePortal, timeout: float = 30.0, max_list_pages: int = 20) -> None:
        super().__init__(output_dir, timeout=timeout, max_list_pages=max_list_pages)
        self.portal = portal
        self.base_url = portal.base_url
        self.list_url = f"{portal.base_url}{portal.app_path}?page=FrontEndListTendersbyDate&service=page"

    def _save_record(self, output_path: Path, record_id: str, source_url: str, detail_html: str) -> None:
        # Reuse CPPP envelope but tag with this portal's source name.
        import json
        from datetime import UTC, datetime

        from app.connectors.common.envelope import build_envelope

        envelope = build_envelope(
            source_name=self.portal.name,
            source_record_id=record_id,
            source_url=source_url,
            retrieved_at=datetime.now(UTC),
            content_type="text/html",
            data={"detail_html": detail_html},
        )
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(envelope, file, ensure_ascii=False, indent=2)
            file.write("\n")


def downloader_for(source_name: str, output_dir: Path, **kwargs) -> StateEProcDownloader:
    portal = next((portal for portal in STATE_PORTALS if portal.name == source_name), None)
    if portal is None:
        raise ValueError(f"Unknown state eProcurement portal: {source_name}")
    return StateEProcDownloader(output_dir, portal, **kwargs)
