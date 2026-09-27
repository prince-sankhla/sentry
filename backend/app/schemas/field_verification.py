from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldRequirement(BaseModel):
    id: str
    capability: str
    label: str = ""
    expected_quantity: int = Field(default=1, ge=0)


class FieldObservation(BaseModel):
    capability: str = ""
    observation: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)
    track_id: str | None = None
    frame_url: str | None = None
    gps: dict[str, Any] | None = None
    observed_at: float | None = None


class FieldReanalysisRequest(BaseModel):
    tender_id: str
    mission_id: str = Field(min_length=1, max_length=200)
    requirements: list[FieldRequirement] = Field(default_factory=list)
    observations: list[FieldObservation] = Field(default_factory=list)
    verification_objective: str | None = Field(default=None, max_length=1000)
    dispatch_reason: str | None = Field(default=None, max_length=1000)
    operator_id: str | None = Field(default=None, max_length=200)
    rover_id: str | None = Field(default=None, max_length=200)
    mission_started_at: str | None = Field(default=None, max_length=100)
    mission_completed_at: str | None = Field(default=None, max_length=100)
