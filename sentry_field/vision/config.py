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

    # Specialized field models.
    pothole_model: Path = MODEL_DIR / "pothole" / "yolo26_best.pt"
    road_distress_model: Path = MODEL_DIR / "road_distress" / "best.pt"

    # General scene/context model used for suppression and scene understanding.
    context_model: Path = MODEL_DIR / "context" / "yolo11n.pt"
    context_confidence: float = 0.45
    context_every_n_frames: int = 6
    person_overlap_threshold: float = 0.15

    # Open-vocabulary asset discovery model. Optional at runtime until bootstrapped.
    world_model: Path = MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt"
    world_confidence: float = 0.30
    world_every_n_frames: int = 8
    world_inference_size: int = 384

    # Scene-aware prompts. Kept narrow enough for useful field inspection.
    world_prompts: tuple[str, ...] = (
        "streetlight",
        "solar streetlight",
        "CCTV camera",
        "road sign",
        "signboard",
        "road barrier",
        "drain",
        "manhole cover",
        "solar panel",
        "traffic cone",
        "guardrail",
        "utility pole",
        "vehicle",
        "person",
    )

    # Lightweight machine-readable text modules.
    qr_enabled: bool = True
    ocr_enabled: bool = True
    qr_every_n_frames: int = 4
    ocr_every_n_frames: int = 12
    ocr_min_confidence: float = 0.55

    # Basic temporal filtering so the same object is not repeatedly emitted.
    tracking_enabled: bool = True
    track_iou_threshold: float = 0.35
    track_ttl_seconds: float = 2.5


DEFAULT_CONFIG = VisionConfig()
