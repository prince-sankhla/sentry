from dataclasses import dataclass, field
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"
EVIDENCE_DIR = ROOT / "field_evidence"


@dataclass(frozen=True)
class VisionConfig:
    source: str = os.getenv("SENTRY_CAMERA_URL", "http://127.0.0.1:4747/video")
    inference_size: int = int(os.getenv("SENTRY_INFERENCE_SIZE", "256"))
    confidence: float = float(os.getenv("SENTRY_CONFIDENCE", "0.65"))
    every_n_frames: int = int(os.getenv("SENTRY_POTHOLE_EVERY_N_FRAMES", "1"))
    evidence_cooldown_seconds: float = float(os.getenv("SENTRY_EVIDENCE_COOLDOWN_SECONDS", "3.0"))
    evidence_dir: Path = Path(os.getenv("SENTRY_EVIDENCE_DIR", str(EVIDENCE_DIR)))
    mission_id: str | None = os.getenv("SENTRY_MISSION_ID") or None
    requirement_id: str | None = os.getenv("SENTRY_REQUIREMENT_ID") or None
    selected_capabilities: tuple[str, ...] = field(default_factory=tuple)
    pothole_model: Path = MODEL_DIR / "pothole" / "yolo26_best.pt"
    road_distress_model: Path = MODEL_DIR / "road_distress" / "best.pt"
    context_model: Path = MODEL_DIR / "context" / "yolo11n.pt"
    context_confidence: float = float(os.getenv("SENTRY_CONTEXT_CONFIDENCE", "0.45"))
    context_every_n_frames: int = int(os.getenv("SENTRY_CONTEXT_EVERY_N_FRAMES", "60"))
    person_overlap_threshold: float = 0.15
    world_model: Path = MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt"
    world_confidence: float = float(os.getenv("SENTRY_WORLD_CONFIDENCE", "0.30"))
    world_every_n_frames: int = int(os.getenv("SENTRY_WORLD_EVERY_N_FRAMES", "15"))
    world_inference_size: int = 320
    world_prompts: tuple[str, ...] = (
        "pothole", "road crack", "streetlight", "solar streetlight", "CCTV camera",
        "road sign", "signboard", "road barrier", "drain", "manhole cover", "solar panel",
        "traffic cone", "guardrail", "utility pole", "vehicle", "person",
    )
    qr_enabled: bool = True
    ocr_enabled: bool = True
    qr_every_n_frames: int = int(os.getenv("SENTRY_QR_EVERY_N_FRAMES", "30"))
    ocr_every_n_frames: int = int(os.getenv("SENTRY_OCR_EVERY_N_FRAMES", "60"))
    ocr_min_confidence: float = 0.55
    tracking_enabled: bool = True
    track_iou_threshold: float = 0.35
    track_ttl_seconds: float = 2.5


DEFAULT_CONFIG = VisionConfig()
CAPABILITY_ALIASES = {
    "Pothole": "pothole",
    "Road crack": "road_crack",
    "Streetlight": "streetlight",
    "CCTV": "cctv_camera",
    "Signboard": "signboard",
    "Drain / manhole": "drain",
    "Solar panel": "solar_panel",
    "Road barrier": "road_barrier",
    "Manhole cover": "manhole_cover",
    "QR / asset ID": "asset_qr",
    "OCR": "asset_text",
    "Barcode": "asset_barcode",
}


def build_config(*, source=None, confidence=None, every_n_frames=None, mission_id=None, requirement_id=None, capabilities=None) -> VisionConfig:
    selected = tuple(capabilities if capabilities is not None else CAPABILITY_ALIASES.values())
    return VisionConfig(
        source=source or DEFAULT_CONFIG.source,
        inference_size=DEFAULT_CONFIG.inference_size,
        confidence=DEFAULT_CONFIG.confidence if confidence is None else max(0.05, min(0.99, confidence)),
        every_n_frames=DEFAULT_CONFIG.every_n_frames if every_n_frames is None else max(1, every_n_frames),
        evidence_cooldown_seconds=DEFAULT_CONFIG.evidence_cooldown_seconds,
        evidence_dir=DEFAULT_CONFIG.evidence_dir,
        mission_id=mission_id or DEFAULT_CONFIG.mission_id,
        requirement_id=requirement_id or DEFAULT_CONFIG.requirement_id,
        selected_capabilities=selected,
        pothole_model=DEFAULT_CONFIG.pothole_model,
        road_distress_model=DEFAULT_CONFIG.road_distress_model,
        context_model=DEFAULT_CONFIG.context_model,
        context_confidence=DEFAULT_CONFIG.context_confidence,
        context_every_n_frames=DEFAULT_CONFIG.context_every_n_frames,
        person_overlap_threshold=DEFAULT_CONFIG.person_overlap_threshold,
        world_model=DEFAULT_CONFIG.world_model,
        world_confidence=DEFAULT_CONFIG.world_confidence,
        world_every_n_frames=DEFAULT_CONFIG.world_every_n_frames,
        world_inference_size=DEFAULT_CONFIG.world_inference_size,
        world_prompts=DEFAULT_CONFIG.world_prompts,
        qr_enabled="asset_qr" in selected,
        ocr_enabled="asset_text" in selected,
        qr_every_n_frames=DEFAULT_CONFIG.qr_every_n_frames,
        ocr_every_n_frames=DEFAULT_CONFIG.ocr_every_n_frames,
        ocr_min_confidence=DEFAULT_CONFIG.ocr_min_confidence,
        tracking_enabled=DEFAULT_CONFIG.tracking_enabled,
        track_iou_threshold=DEFAULT_CONFIG.track_iou_threshold,
        track_ttl_seconds=DEFAULT_CONFIG.track_ttl_seconds,
    )
