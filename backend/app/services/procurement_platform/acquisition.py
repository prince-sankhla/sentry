"""Large-scale data acquisition pipeline (Phase X).

Orchestrates the existing connector downloaders (which already provide
pagination, resume, tenacity retry, conditional-request caching and duplicate
detection) end-to-end: probe → download → import → delta report. It legally
acquires the maximum *publicly accessible* data and NEVER fabricates records.

Every source is honestly classified into one of:
    already_imported · newly_downloaded · unavailable · skipped

When a source cannot be acquired (missing API key, bot protection / 403,
authenticated-only portal, network limits) the pipeline is still fully wired
and the concrete blocker is reported instead of inventing data.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.importers.generic import GenericConnectorImporter
from app.models import Tender
from app.services.procurement_platform.incremental import plan_delta

logger = logging.getLogger(__name__)

# Priority order requested by the platform sprint.
PRIORITY_SOURCES = [
    "cppp", "gem",
    "eproc_rajasthan", "eproc_maharashtra", "eproc_karnataka",
    "eproc_kerala", "eproc_tamilnadu", "eproc_odisha",
    "eproc_gujarat", "eproc_delhi", "eproc_westbengal",
    "eproc_andhrapradesh", "eproc_telangana", "eproc_punjab",
    "eproc_haryana", "eproc_uttarpradesh",
    "world_bank", "adb", "un_procurement", "datagovin",
]

# Reachability probe endpoints (HEAD/GET, short timeout).
_PROBE_URLS: dict[str, str] = {
    "world_bank": "https://search.worldbank.org/api/v2/procnotices?format=json&rows=1&os=0",
    "cppp": "https://eprocure.gov.in/cppp/",
    "gem": "https://gem.gov.in/",
    "adb": "https://www.adb.org/projects/tenders",
    "un_procurement": "https://www.ungm.org/",
    "datagovin": "https://api.data.gov.in/catalog",
}


@dataclass
class AcquisitionResult:
    source: str
    reachable: bool | None = None
    probe_status: int | None = None
    already_imported: int = 0          # DB rows for this source before acquisition
    newly_downloaded: int = 0          # envelope files added to disk
    unchanged_on_disk: int = 0
    imported_new: int = 0              # DB rows inserted from this acquisition
    imported_updated: int = 0
    outcome: str = "skipped"           # acquired | already_imported | unavailable | skipped
    blocker: str | None = None
    delta: dict = field(default_factory=dict)


# Downloader adapters: source -> callable(output_dir, limit) -> newly_downloaded count.
def _download_world_bank(output_dir: Path, limit: int) -> int:
    from app.connectors.world_bank.downloader import WorldBankProcurementDownloader

    existing = sum(1 for _ in output_dir.glob("*.json")) if output_dir.exists() else 0
    stats = WorldBankProcurementDownloader(output_dir).download(limit=existing + limit)
    return stats.downloaded_notices


def _download_cppp(output_dir: Path, limit: int) -> int:
    from app.connectors.cppp.downloader import CPPPDownloader

    stats = CPPPDownloader(output_dir).download(limit=limit)
    return getattr(stats, "downloaded", 0) or getattr(stats, "downloaded_notices", 0)


def _download_state_eproc(source: str):
    def _run(output_dir: Path, limit: int) -> int:
        from app.connectors.state_eproc.downloader import downloader_for

        stats = downloader_for(source, output_dir).download(limit=limit)
        return getattr(stats, "downloaded", 0)

    return _run


def _download_feed(source: str):
    def _run(output_dir: Path, limit: int) -> int:
        module = __import__(f"app.connectors.{source}.downloader", fromlist=["_"])
        # Each feed downloader is <Name>Downloader(output_dir); attempt best-effort.
        cls = next(
            obj for name, obj in vars(module).items()
            if name.endswith("Downloader") and isinstance(obj, type)
        )
        stats = cls(output_dir).download(limit=limit)
        return getattr(stats, "downloaded", 0)

    return _run


def _download_datagovin(output_dir: Path, limit: int) -> int:
    from app.connectors.datagovin.downloader import DataGovInDownloader

    if not os.environ.get("DATA_GOV_IN_API_KEY"):
        raise RuntimeError("DATA_GOV_IN_API_KEY not configured")
    resource_ids = [
        value.strip()
        for value in os.environ.get("DATA_GOV_IN_RESOURCE_IDS", "").split(",")
        if value.strip()
    ]
    if not resource_ids:
        raise RuntimeError("DATA_GOV_IN_RESOURCE_IDS not configured")
    stats = DataGovInDownloader(output_dir, resource_ids=resource_ids).download(limit=limit)
    return getattr(stats, "downloaded", 0)


_DOWNLOADERS: dict[str, Callable[[Path, int], int]] = {
    "world_bank": _download_world_bank,
    "cppp": _download_cppp,
    "eproc_rajasthan": _download_state_eproc("eproc_rajasthan"),
    "eproc_maharashtra": _download_state_eproc("eproc_maharashtra"),
    "eproc_karnataka": _download_state_eproc("eproc_karnataka"),
    "eproc_kerala": _download_state_eproc("eproc_kerala"),
    "eproc_tamilnadu": _download_state_eproc("eproc_tamilnadu"),
    "eproc_odisha": _download_state_eproc("eproc_odisha"),
    "eproc_gujarat": _download_state_eproc("eproc_gujarat"),
    "eproc_delhi": _download_state_eproc("eproc_delhi"),
    "eproc_westbengal": _download_state_eproc("eproc_westbengal"),
    "eproc_andhrapradesh": _download_state_eproc("eproc_andhrapradesh"),
    "eproc_telangana": _download_state_eproc("eproc_telangana"),
    "eproc_punjab": _download_state_eproc("eproc_punjab"),
    "eproc_haryana": _download_state_eproc("eproc_haryana"),
    "eproc_uttarpradesh": _download_state_eproc("eproc_uttarpradesh"),
    "gem": _download_feed("gem"),
    "adb": _download_feed("adb"),
    "un_procurement": _download_feed("un_procurement"),
    "datagovin": _download_datagovin,
}

# Sources with no automated public download path (documented blockers).
_STATIC_BLOCKERS: dict[str, str] = {
    "gem": "GeM enforces authenticated sessions / bot protection; no open public API (needs official API credentials).",
    "adb": "ADB tender portal returns HTTP 403 to automated clients (bot protection).",
    "un_procurement": "UNGM requires an authenticated session / POST search; no open bulk JSON feed.",
    "datagovin": "data.gov.in requires DATA_GOV_IN_API_KEY and DATA_GOV_IN_RESOURCE_IDS for specific public resources.",
}


def probe_source(source: str, timeout: float = 6.0) -> tuple[bool | None, int | None]:
    url = _PROBE_URLS.get(source)
    if not url:
        return None, None
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True, headers={"User-Agent": "SENTRY-Probe/1.0"})
        return True, response.status_code
    except Exception as error:  # noqa: BLE001
        logger.warning("Probe failed for %s: %s", source, error)
        return False, None


def acquire(
    db: Session,
    source: str,
    data_root: Path,
    *,
    limit: int = 25,
    download: bool = True,
) -> AcquisitionResult:
    """Acquire one source end-to-end and classify the outcome honestly."""
    result = AcquisitionResult(source=source)
    result.already_imported = int(
        db.scalar(select(func.count(Tender.id)).where(Tender.source_name == source)) or 0
    )
    output_dir = data_root / source
    result.reachable, result.probe_status = probe_source(source)

    if download and source in _DOWNLOADERS:
        try:
            before = _count_files(output_dir)
            result.newly_downloaded = _DOWNLOADERS[source](output_dir, limit)
            after = _count_files(output_dir)
            result.newly_downloaded = max(result.newly_downloaded, after - before)
        except Exception as error:  # noqa: BLE001
            result.outcome = "unavailable"
            result.blocker = _STATIC_BLOCKERS.get(source) or f"{type(error).__name__}: {str(error)[:160]}"
            return _finalize(db, source, output_dir, result)

    return _finalize(db, source, output_dir, result)


def _finalize(db: Session, source: str, output_dir: Path, result: AcquisitionResult) -> AcquisitionResult:
    if not output_dir.exists() or not any(output_dir.glob("*.json")):
        if result.outcome != "unavailable":
            result.outcome = "unavailable"
            result.blocker = result.blocker or _STATIC_BLOCKERS.get(source) or "No local envelopes and no successful download."
        return result

    # Import whatever is on disk (idempotent; unchanged records skip).
    try:
        stats = GenericConnectorImporter(db, source).import_directory(output_dir)
        result.imported_new = stats.imported_tenders
        result.imported_updated = stats.updated_tenders
        result.unchanged_on_disk = stats.unchanged_records
        result.delta = plan_delta(db, source, output_dir).summary()
    except Exception as error:  # noqa: BLE001
        result.outcome = "unavailable"
        result.blocker = f"import failed: {type(error).__name__}: {str(error)[:160]}"
        return result

    if result.newly_downloaded or result.imported_new or result.imported_updated:
        result.outcome = "acquired"
    else:
        result.outcome = "already_imported"
    return result


def acquire_all(
    db: Session,
    data_root: Path,
    *,
    sources: list[str] | None = None,
    limit: int = 25,
    download: bool = True,
) -> list[AcquisitionResult]:
    results = []
    for source in (sources or PRIORITY_SOURCES):
        results.append(acquire(db, source, data_root, limit=limit, download=download))
    return results


def _count_files(directory: Path) -> int:
    return sum(1 for _ in directory.glob("*.json")) if directory.exists() else 0
