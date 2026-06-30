from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


SOURCE_NAME = "world_bank"
SOURCE_LABEL = "World Bank Procurement Notices"


@dataclass(frozen=True)
class RawNotice:
    id: str
    payload: dict[str, Any]
    source_url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class SourceMetadata:
    source_name: str
    source_record_id: str
    source_url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class MappedTender:
    reference_number: str
    title: str
    description: str | None
    procuring_entity: str | None
    published_date: date | None
    closing_date: date | None
    estimated_value: Decimal | None
    currency: str
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedCompany:
    name: str
    registration_number: str | None
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedAward:
    tender_reference_number: str
    company_name: str
    company_registration_number: str | None
    award_date: date | None
    award_value: Decimal | None
    currency: str
    metadata: SourceMetadata


@dataclass(frozen=True)
class MappedNotice:
    tender: MappedTender
    companies: list[MappedCompany] = field(default_factory=list)
    awards: list[MappedAward] = field(default_factory=list)
