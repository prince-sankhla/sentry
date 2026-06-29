from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ProzorroClientError(RuntimeError):
    """Raised when the Prozorro API response cannot be processed."""


class ProzorroClient:
    """Client for the official OpenProcurement Tender API."""

    def __init__(
        self,
        base_url: str = "https://public.api.openprocurement.org/api/2.5",
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout)

    def fetch_latest_tender_ids(self, limit: int = 100) -> list[str]:
        tender_ids: list[str] = []
        offset: str | None = None

        while len(tender_ids) < limit:
            params: dict[str, Any] = {"descending": "1", "limit": min(100, limit - len(tender_ids))}
            if offset:
                params["offset"] = offset

            payload = self._get_json("/tenders", params=params)
            tenders = payload.get("data")
            if not isinstance(tenders, list):
                raise ProzorroClientError("Expected 'data' list in tender list response.")

            for tender in tenders:
                tender_id = tender.get("id") if isinstance(tender, dict) else None
                if isinstance(tender_id, str):
                    tender_ids.append(tender_id)
                    if len(tender_ids) >= limit:
                        break

            next_page = payload.get("next_page")
            next_offset = next_page.get("offset") if isinstance(next_page, dict) else None
            if not next_offset or not tenders:
                break

            offset = str(next_offset)

        return tender_ids

    def fetch_tender(self, tender_id: str) -> dict[str, Any]:
        payload = self._get_json(f"/tenders/{tender_id}")
        tender = payload.get("data")
        if not isinstance(tender, dict):
            raise ProzorroClientError(f"Expected 'data' object for tender {tender_id}.")
        return tender

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, ProzorroClientError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        logger.info("Requesting %s", url)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise ProzorroClientError(f"Expected JSON object from {url}.")
        return payload
