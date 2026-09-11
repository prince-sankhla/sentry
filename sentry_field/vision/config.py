from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import os
import time

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"
EVIDENCE_DIR = ROOT / "field_evidence"

MODEL_SOURCES = {
    "pothole": (
        MODEL_DIR / "pothole" / "yolo26_best.pt",
        "https://huggingface.co/DanielsStulpe/pothole-detection/resolve/main/yolo26_best.pt?download=true",
    ),
    "road_crack": (
        MODEL_DIR / "road_distress" / "best.pt",
        "https://huggingface.co/cazzz307/yolov8-crack-detection/resolve/main/best.pt?download=true",
    ),
    "open_vocabulary": (
        MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt",
    ),
}


def _ensure_model(name: str) -> Path:
    path, url = MODEL_SOURCES[name]
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            request = Request(url, headers={"User-Agent": "SENTRY-FIELD/1.0"})
            with urlopen(request, timeout=300) as response, temp.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            if temp.stat().st_size <= 1_000_000:
                raise RuntimeError(f"Downloaded {name} model is unexpectedly small")
            temp.replace(path)
            return path
        except (HTTPError, URLError, OSError, RuntimeError) as exc:
            last_error = exc
            temp.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt)
    raise RuntimeError(f"Could not download {name} model: {last_error}")


@dataclass(frozen=True)
class VisionConfig:
    source: str = os.getenv("SENTRY_CAMERA_URL", "http://127.0.0.1:4747/video")
    # 416 is a practical CPU-friendly size for road defects; camera delivery is decoupled.
    inference_size: int = int(os.getenv("SENTRY_INFERENCE_SIZE", "416"))
    confidence: float = float(os.getenv("SENTRY_CONFIDENCE", "0.25"))
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
    context_every_n_frames: int = int(os.getenv("SENTRY_CONTEXT_EVERY_N_FRAMES", "90"))
    person_overlap_threshold: float = 0.15
    world_model: Path = MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt"
    world_confidence: float = float(os.getenv("SENTRY_WORLD_CONFIDENCE", "0.22"))
    world_every_n_frames: int = int(os.getenv("SENTRY_WORLD_EVERY_N_FRAMES", "4"))
    world_inference_size: int = int(os.getenv("SENTRY_WORLD_INFERENCE_SIZE", "320"))
    world_prompts: tuple[str, ...] = (
        "pothole", "road crack", "streetlight", "solar streetlight", "CCTV camera",
        "road sign", "signboard", "road barrier", "drain", "manhole cover", "solar panel",
        "traffic cone", "guardrail", "utility pole", "vehicle", "person",
    )
    qr_enabled: bool = True
    ocr_enabled: bool = True
    qr_every_n_frames: int = int(os.getenv("SENTRY_QR_EVERY_N_FRAMES", "45"))
    ocr_every_n_frames: int = int(os.getenv("SENTRY_OCR_EVERY_N_FRAMES", "120"))
    ocr_min_confidence: float = 0.55
    tracking_enabled: bool = True
    track_iou_threshold: float = 0.35
    track_ttl_seconds: float = 2.5
    device: str = os.getenv("SENTRY_VISION_DEVICE", "auto")
    half: bool = os.getenv("SENTRY_VISION_HALF", "auto").lower() != "false"
    stream_max_width: int = int(os.getenv("SENTRY_STREAM_MAX_WIDTH", "960"))
    jpeg_quality: int = int(os.getenv("SENTRY_STREAM_JPEG_QUALITY", "72"))


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


def build_config(*, source=None, confidence=None, every_n_frames=None, mission_id=None, requirement_id=None, capabilities=None, bootstrap_models=True) -> VisionConfig:
    selected = tuple(capabilities if capabilities is not None else CAPABILITY_ALIASES.values())
    specialized = {"pothole", "road_crack"}
    world_caps = {"streetlight", "cctv_camera", "signboard", "road_barrier", "drain", "solar_panel", "manhole_cover", "utility_pole"}

    if bootstrap_models:
        if "pothole" in selected:
            _ensure_model("pothole")
        if "road_crack" in selected:
            _ensure_model("road_crack")
        # Open-vocabulary is only needed when an asset capability has no dedicated detector.
        if selected.intersection(world_caps):
            try:
                _ensure_model("open_vocabulary")
            except Exception:
                pass

    requested_confidence = DEFAULT_CONFIG.confidence if confidence is None else float(confidence)
    effective_confidence = max(0.10, min(0.35, requested_confidence))

    # Context inference adds substantial CPU cost and is not required for specialized road-defect missions.
    needs_context = not bool(selected.intersection(specialized))
    context_model = DEFAULT_CONFIG.context_model if needs_context else Path("__disabled_context__.pt")

    # Never run YOLO-World on pothole/road-crack missions when the specialized model exists.
    needs_world = bool(selected.intersection(world_caps))
    world_model = DEFAULT_CONFIG.world_model if needs_world else Path("__disabled_world__.pt")

    return VisionConfig(
        source=source or DEFAULT_CONFIG.source,
        inference_size=DEFAULT_CONFIG.inference_size,
        confidence=effective_confidence,
        every_n_frames=DEFAULT_CONFIG.every_n_frames if every_n_frames is None else max(1, every_n_frames),
        evidence_cooldown_seconds=DEFAULT_CONFIG.evidence_cooldown_seconds,
        evidence_dir=DEFAULT_CONFIG.evidence_dir,
        mission_id=mission_id or DEFAULT_CONFIG.mission_id,
        requirement_id=requirement_id or DEFAULT_CONFIG.requirement_id,
        selected_capabilities=selected,
        pothole_model=DEFAULT_CONFIG.pothole_model,
        road_distress_model=DEFAULT_CONFIG.road_distress_model,
        context_model=context_model,
        context_confidence=DEFAULT_CONFIG.context_confidence,
        context_every_n_frames=DEFAULT_CONFIG.context_every_n_frames,
        person_overlap_threshold=DEFAULT_CONFIG.person_overlap_threshold,
        world_model=world_model,
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
        device=DEFAULT_CONFIG.device,
        half=DEFAULT_CONFIG.half,
        stream_max_width=DEFAULT_CONFIG.stream_max_width,
        jpeg_quality=DEFAULT_CONFIG.jpeg_quality,
    )
