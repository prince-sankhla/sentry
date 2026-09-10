from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO

try:
    from ultralytics import YOLOWorld
except ImportError:  # pragma: no cover
    YOLOWorld = None  # type: ignore[assignment]

from ..evidence import EvidenceWriter
from .capabilities import WORLD_EVIDENCE_CLASSES
from .config import CAPABILITY_ALIASES, DEFAULT_CONFIG, VisionConfig

WORLD_CANONICAL = {
    "pothole": "pothole",
    "streetlight": "streetlight",
    "solar streetlight": "streetlight",
    "cctv camera": "cctv_camera",
    "road sign": "signboard",
    "signboard": "signboard",
    "road barrier": "road_barrier",
    "drain": "drain",
    "manhole cover": "manhole_cover",
    "solar panel": "solar_panel",
    "traffic cone": "road_barrier",
    "guardrail": "road_barrier",
    "utility pole": "utility_pole",
    "road crack": "road_crack",
}


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: list[int]
    detector: str
    track_id: str | None = None


def _box(box: Any) -> list[int]:
    return [int(round(float(value))) for value in box]


def _parse_result(result: Any, detector: str) -> list[Detection]:
    if result is None or result.boxes is None or len(result.boxes) == 0:
        return []
    names = result.names
    out: list[Detection] = []
    for index in range(len(result.boxes)):
        cls_id = int(result.boxes.cls[index].item())
        label = str(names.get(cls_id, cls_id)) if isinstance(names, dict) else str(cls_id)
        out.append(Detection(label=label, confidence=float(result.boxes.conf[index].item()), bbox=_box(result.boxes.xyxy[index].tolist()), detector=detector))
    return out


class SimpleTrackStore:
    def __init__(self, iou_threshold: float = 0.35, ttl_seconds: float = 2.5) -> None:
        self.iou_threshold = iou_threshold
        self.ttl_seconds = ttl_seconds
        self.tracks: dict[str, dict[str, Any]] = {}
        self.counter = 0

    @staticmethod
    def iou(a: list[int], b: list[int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        aa = max(1, (ax2 - ax1) * (ay2 - ay1))
        ab = max(1, (bx2 - bx1) * (by2 - by1))
        return inter / float(aa + ab - inter)

    def assign(self, label: str, bbox: list[int], now: float) -> tuple[str, bool]:
        for key in [key for key, item in self.tracks.items() if now - item["last_seen"] > self.ttl_seconds]:
            self.tracks.pop(key, None)
        best_key = None
        best_score = 0.0
        for key, item in self.tracks.items():
            if item["label"] != label:
                continue
            score = self.iou(bbox, item["bbox"])
            if score >= self.iou_threshold and score > best_score:
                best_key, best_score = key, score
        if best_key is not None:
            self.tracks[best_key]["bbox"] = bbox
            self.tracks[best_key]["last_seen"] = now
            return best_key, False
        self.counter += 1
        track_id = f"trk-{self.counter:05d}"
        self.tracks[track_id] = {"label": label, "bbox": bbox, "last_seen": now}
        return track_id, True


class FieldScanner:
    """Single FIELD scanner selected by the investigation's capability plan."""

    def __init__(self, config: VisionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.selected = set(config.selected_capabilities or CAPABILITY_ALIASES.values())
        self.current_gps: dict[str, Any] | None = None
        self.context_model = self._load_optional(config.context_model)
        self.pothole_model = self._load_optional(config.pothole_model) if "pothole" in self.selected else None
        self.road_distress_model = self._load_optional(config.road_distress_model) if "road_crack" in self.selected else None
        world_caps = {"pothole", "road_crack", "streetlight", "cctv_camera", "signboard", "road_barrier", "drain", "solar_panel", "manhole_cover", "utility_pole"}
        self.world_model = self._load_world(config.world_model) if self.selected.intersection(world_caps) else None
        if self.world_model is not None:
            prompts = [prompt for prompt in config.world_prompts if self._prompt_enabled(prompt)]
            if prompts:
                self.world_model.set_classes(prompts)
        self.qr_detector = cv2.QRCodeDetector()
        self.writer = EvidenceWriter(config.evidence_dir)
        self.tracker = SimpleTrackStore(config.track_iou_threshold, config.track_ttl_seconds)
        self.last_evidence_at: dict[str, float] = {}
        self.ocr_available = False
        self.pytesseract = None
        if config.ocr_enabled:
            try:
                import pytesseract  # type: ignore
                self.pytesseract = pytesseract
                self.ocr_available = True
            except ImportError:
                pass
        self.barcode_decode = None
        try:
            from pyzbar.pyzbar import decode as barcode_decode  # type: ignore
            self.barcode_decode = barcode_decode
        except ImportError:
            pass

    @staticmethod
    def _load_optional(path: Path):
        return YOLO(str(path)) if Path(path).exists() else None

    @staticmethod
    def _load_world(path: Path):
        if YOLOWorld is None or not Path(path).exists():
            return None
        return YOLOWorld(str(path))

    def _prompt_enabled(self, prompt: str) -> bool:
        mapping = {
            "pothole": "pothole", "road crack": "road_crack", "streetlight": "streetlight", "solar streetlight": "streetlight",
            "cctv camera": "cctv_camera", "road sign": "signboard", "signboard": "signboard", "road barrier": "road_barrier",
            "drain": "drain", "manhole cover": "manhole_cover", "solar panel": "solar_panel", "traffic cone": "road_barrier",
            "guardrail": "road_barrier", "utility pole": "utility_pole", "vehicle": "__context__", "person": "__context__",
        }
        target = mapping.get(prompt.lower(), prompt.lower())
        return target in self.selected or target == "__context__"

    @staticmethod
    def _normalise_world_label(label: str) -> str | None:
        raw = label.strip().lower()
        canonical = WORLD_CANONICAL.get(raw)
        if canonical:
            return canonical
        for alias, mapped in WORLD_CANONICAL.items():
            if raw == alias or alias in raw:
                return mapped
        return None

    def _save_detection(self, frame: Any, detection: Detection, track_id: str, quality: str) -> dict[str, Any]:
        now = time.monotonic()
        if now - self.last_evidence_at.get(track_id, 0.0) < self.config.evidence_cooldown_seconds:
            return {}
        event = self.writer.record_detection(
            frame,
            capability=detection.label.lower().replace(" ", "_"),
            observation=f"{detection.label} observed in field camera frame",
            confidence=detection.confidence,
            bbox=detection.bbox,
            gps=self.current_gps,
            mission_id=self.config.mission_id,
            requirement_id=self.config.requirement_id,
            source=self.config.source,
            detector=detection.detector,
            track_id=track_id,
            evidence_quality=quality,
        )
        self.last_evidence_at[track_id] = now
        return event.to_dict()

    def _qr_scan(self, frame: Any) -> str | None:
        try:
            value, _, _ = self.qr_detector.detectAndDecode(frame)
            return str(value) if value else None
        except cv2.error:
            return None

    def _barcode_scan(self, frame: Any) -> str | None:
        if self.barcode_decode is None:
            return None
        try:
            for item in self.barcode_decode(frame):
                value = item.data.decode("utf-8", errors="replace").strip()
                if value:
                    return value
        except Exception:
            pass
        return None

    def _ocr_scan(self, frame: Any) -> str | None:
        if not self.ocr_available or self.pytesseract is None:
            return None
        try:
            text = self.pytesseract.image_to_string(frame, config="--psm 11")
            cleaned = " ".join(text.split())
            return cleaned[:160] if cleaned else None
        except Exception:
            return None

    def _specialized(self, frame: Any, model: Any, detector_name: str, frame_index: int) -> list[Detection]:
        if model is None or frame_index % max(1, self.config.every_n_frames) != 0:
            return []
        result = model(frame, imgsz=self.config.inference_size, conf=self.config.confidence, verbose=False)[0]
        return _parse_result(result, detector_name)

    def scan(self, frame: Any, frame_index: int, gps: dict[str, Any] | None = None):
        self.current_gps = gps
        accepted: list[Detection] = []
        context: list[Detection] = []
        evidence: list[dict[str, Any]] = []

        if self.context_model is not None and frame_index % max(1, self.config.context_every_n_frames) == 0:
            context = _parse_result(self.context_model(frame, imgsz=320, conf=self.config.context_confidence, verbose=False)[0], "context_model")

        def add(detection: Detection, quality: str) -> None:
            track_id, is_new = self.tracker.assign(detection.label, detection.bbox, time.monotonic())
            detection.track_id = track_id
            accepted.append(detection)
            if is_new:
                event = self._save_detection(frame, detection, track_id, quality)
                if event:
                    evidence.append(event)

        for detection in self._specialized(frame, self.pothole_model, "pothole_model", frame_index):
            detection.label = self._normalise_world_label(detection.label) or detection.label.strip()
            add(detection, "specialized")
        for detection in self._specialized(frame, self.road_distress_model, "road_distress_model", frame_index):
            detection.label = self._normalise_world_label(detection.label) or "road crack"
            add(detection, "specialized")

        # The open-vocabulary detector is the universal fallback for physical
        # capabilities whenever a specialised weight is unavailable, and also
        # provides the common roadside asset detector family.
        if self.world_model is not None and frame_index % max(1, self.config.world_every_n_frames) == 0:
            result = self.world_model.predict(frame, imgsz=self.config.world_inference_size, conf=self.config.world_confidence, verbose=False)[0]
            allowed = {item.lower() for item in WORLD_EVIDENCE_CLASSES}
            specialised_missing = {
                capability
                for capability, model in (("pothole", self.pothole_model), ("road_crack", self.road_distress_model))
                if capability in self.selected and model is None
            }
            for detection in _parse_result(result, "open_vocabulary"):
                raw = detection.label.lower()
                if raw not in allowed and not any(alias in raw for alias in WORLD_CANONICAL):
                    continue
                canonical = self._normalise_world_label(raw)
                if canonical is None:
                    continue
                if canonical not in self.selected and not (canonical in specialised_missing):
                    continue
                detection.label = canonical.replace("_", " ")
                add(detection, "open_vocabulary_fallback" if canonical in specialised_missing else "open_vocabulary")

        qr = self._qr_scan(frame) if "asset_qr" in self.selected and frame_index % max(1, self.config.qr_every_n_frames) == 0 else None
        barcode = self._barcode_scan(frame) if "asset_barcode" in self.selected and frame_index % max(1, self.config.qr_every_n_frames) == 0 else None
        ocr = self._ocr_scan(frame) if "asset_text" in self.selected and frame_index % max(1, self.config.ocr_every_n_frames) == 0 else None
        return accepted, context, qr, barcode, ocr, evidence


def run_field_scanner(config: VisionConfig = DEFAULT_CONFIG) -> None:
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(config.source)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video source: {config.source}")
    index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                time.sleep(0.01)
                continue
            index += 1
            detections, _context, qr, barcode, ocr, _ = scanner.scan(frame, index)
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
            cv2.imshow("SENTRY FIELD - Unified Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
