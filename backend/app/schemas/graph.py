from typing import Any, Literal

from pydantic import BaseModel, Field


GraphNodeType = Literal[
    "company",
    "tender",
    "award",
    "buyer",
    "indicator",
    "evidence",
    "document",
    "web_evidence",
    "organization",
    "category",
]
GraphEdgeType = Literal[
    "company_tender",
    "tender_award",
    "award_company",
    "buyer_tender",
    "buyer_company",
    "tender_indicator",
    "company_indicator",
    "evidence_indicator",
    "tender_evidence",
    "web_evidence_company",
    "web_evidence_tender",
    "web_evidence_award",
    "document_tender",
    "category_tender",
    "organization_evidence",
]


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
