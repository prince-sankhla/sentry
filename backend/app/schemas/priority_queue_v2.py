from __future__ import annotations

from pydantic import BaseModel


class DirectTenderIdentity(BaseModel):
    tender_id: str
    source_record_id: str | None = None
    tender_title: str
    source_url: str | None = None
