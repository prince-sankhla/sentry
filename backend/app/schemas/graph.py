from typing import Any, Literal

from pydantic import BaseModel, Field


GraphNodeType = Literal["company", "tender", "award", "buyer"]
GraphEdgeType = Literal["company_tender", "tender_award", "award_company", "buyer_tender"]


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
