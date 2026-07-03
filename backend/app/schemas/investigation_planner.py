from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


InvestigationType = Literal[
    "company",
    "supplier",
    "buyer",
    "tender",
    "director",
    "contract",
    "ministry",
    "location",
]

PlanStepStatus = Literal["planned"]


class InvestigationPlanRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    source_names: list[str] | None = None


class InvestigationPlanStep(BaseModel):
    order: int
    module: str
    action: str
    connectors: list[str] = Field(default_factory=list)
    inputs: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: PlanStepStatus = "planned"


class InvestigationPlan(BaseModel):
    query: str
    investigation_type: InvestigationType
    confidence: float = Field(ge=0, le=1)
    connectors: list[str]
    modules: list[str]
    steps: list[InvestigationPlanStep]
