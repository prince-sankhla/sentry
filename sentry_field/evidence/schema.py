from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceEvent:
    """A traceable field observation produced by a SENTRY capability."""

    event_id: str
    observed_at_utc: str
    capability: str
    observation: str
    confidence: float
    bbox: Optional[list[int]] = None
    frame_path: Optional[str] = None
    gps: Optional[dict[str, float]] = None
    mission_id: Optional[str] = None
    requirement_id: Optional[str] = None
    source: Optional[str] = None
    verification_state: str = "observed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
