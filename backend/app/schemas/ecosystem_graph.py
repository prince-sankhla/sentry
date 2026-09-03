from typing import Any, Literal

from pydantic import BaseModel, Field


EcosystemNodeType = Literal[
    "buyer", "tender", "company", "award", "document", "evidence", "category"
]

EcosystemEdgeType = Literal[
    "buyer_tender",
    "tender_award",
    "award_company",
    "document_tender",
    "evidence_tender",
    "evidence_company",
    "buyer_company",
    "category_tender",
]


class EcosystemNode(BaseModel):
    id: str
    type: EcosystemNodeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class EcosystemEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EcosystemEdgeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class RelationshipSignal(BaseModel):
    code: str
    title: str
    severity: Literal["info", "review", "notable"]
    summary: str
    evidence: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]


class EcosystemGraphResponse(BaseModel):
    nodes: list[EcosystemNode]
    edges: list[EcosystemEdge]
    relationship_signals: list[RelationshipSignal] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
