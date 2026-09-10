import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2

from .schema import EvidenceEvent


class EvidenceWriter:
    """Persist field evidence as a JSON event plus its supporting frame."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _write_event(
        self,
        frame,
        *,
        capability: str,
        observation: str,
        confidence: float,
        bbox: list[int] | None = None,
        gps: dict[str, float] | None = None,
        mission_id: str | None = None,
        requirement_id: str | None = None,
        source: str | None = None,
        detector: str | None = None,
        track_id: str | None = None,
        evidence_quality: str = "raw_detection",
        metadata: dict | None = None,
    ) -> EvidenceEvent:
        event_id = f"field-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}"
        event_dir = self.root / event_id
        event_dir.mkdir(parents=True, exist_ok=True)

        frame_path = event_dir / "frame.jpg"
        if not cv2.imwrite(str(frame_path), frame):
            raise RuntimeError(f"Could not write evidence frame: {frame_path}")

        event = EvidenceEvent(
            event_id=event_id,
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
            capability=capability,
            observation=observation,
            confidence=round(float(confidence), 4),
            bbox=bbox,
            frame_path=str(frame_path),
            gps=gps,
            mission_id=mission_id,
            requirement_id=requirement_id,
            source=source,
            detector=detector,
            track_id=track_id,
            evidence_quality=evidence_quality,
            metadata=metadata,
        )

        with (event_dir / "evidence.json").open("w", encoding="utf-8") as handle:
            json.dump(event.to_dict(), handle, indent=2)

        return event

    def record_detection(
        self,
        frame,
        *,
        capability: str,
        observation: str,
        confidence: float,
        bbox: list[int] | None = None,
        gps: dict[str, float] | None = None,
        mission_id: str | None = None,
        requirement_id: str | None = None,
        source: str | None = None,
        detector: str | None = None,
        track_id: str | None = None,
        evidence_quality: str = "raw_detection",
        metadata: dict | None = None,
    ) -> EvidenceEvent:
        return self._write_event(
            frame,
            capability=capability,
            observation=observation,
            confidence=confidence,
            bbox=bbox,
            gps=gps,
            mission_id=mission_id,
            requirement_id=requirement_id,
            source=source,
            detector=detector,
            track_id=track_id,
            evidence_quality=evidence_quality,
            metadata=metadata,
        )

    def record_observation(
        self,
        frame,
        *,
        capability: str,
        observation: str,
        gps: dict[str, float] | None = None,
        mission_id: str | None = None,
        requirement_id: str | None = None,
        source: str | None = None,
        detector: str | None = None,
        evidence_quality: str = "identity_observation",
        metadata: dict | None = None,
    ) -> EvidenceEvent:
        return self._write_event(
            frame,
            capability=capability,
            observation=observation,
            confidence=1.0,
            gps=gps,
            mission_id=mission_id,
            requirement_id=requirement_id,
            source=source,
            detector=detector,
            evidence_quality=evidence_quality,
            metadata=metadata,
        )
