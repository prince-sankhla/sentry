from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


IntelligenceSignalType = Literal[
    "single_bidder",
    "repeat_supplier",
    "buyer_supplier_relationship",
]
IntelligenceSeverity = Literal["low", "medium", "high"]


class ProcurementIntelligenceSignal(BaseModel):
    type: IntelligenceSignalType
    severity: IntelligenceSeverity
    title: str
    summary: str
    score: int
    evidence: list[str]
    tender_id: UUID | None = None
    company_id: UUID | None = None
    buyer: str | None = None


class BuyerSupplierRelationshipScore(BaseModel):
    buyer: str | None
    supplier_id: UUID
    supplier_name: str
    score: int
    awards_to_supplier: int
    total_buyer_awards: int
    supplier_award_share: Decimal
    total_award_value: Decimal
    latest_award_date: date | None


class ProcurementIntelligence(BaseModel):
    signals: list[ProcurementIntelligenceSignal]
    relationship_scores: list[BuyerSupplierRelationshipScore]
