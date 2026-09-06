from dataclasses import dataclass
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"
EVIDENCE_DIR = ROOT / "field_evidence"


@dataclass(frozen=True)
class VisionConfig:
    source: str = os.getenv("SENTRY_CAMERA_URL", "http://127.0.0.1:4747/video")
    inference_size: int = 256
    confidence: float = 0.65
    every_n_frames: int = 2
    evidence_cooldown_seconds: float = 3.0
    evidence_dir: Path = Path(os.getenv("SENTRY_EVIDENCE_DIR", str(EVIDENCE_DIR)))
    mission_id: str | None = os.getenv("SENTRY_MISSION_ID") or None
    requirement_id: str | None = os.getenv("SENTRY_REQUIREMENT_ID") or None
    pothole_model: Path = MODEL_DIR / "pothole" / "yolo26_best.pt"
    road_distress_model: Path = MODEL_DIR / "road_distress" / "best.pt"
    context_model: Path = MODEL_DIR / "context" / "yolo11n.pt"
    context_confidence: float = 0.45
    context_every_n_frames: int = 6
    person_overlap_threshold: float = 0.15


DEFAULT_CONFIG = VisionConfig()
