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
    "streetlight": "streetlight",
    "solar streetlight": "streetlight",
    "cctv camera": "cctv_camera",
    "road sign": "signboard",
    "signboard": "signboard",
    "road barrier": "road_barrier",
    "drain": "drain",
    "manhole cover": "drain",
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
    return [
        Detection(
            label=str(names.get(int(result.boxes.cls[i].item()), int(result.boxes.cls[i].item())))
            if isinstance(names, dict)
            else str(int(result.boxes.cls[i].item())),
            confidence=float(result.boxes.conf[i].item()),
            bbox=_box(result.boxes.xyxy[i].tolist()),
            detector=detector,
        )
        for i in range(len(result.boxes))
    ]


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
        for key in [k for k, item in self.tracks.items() if now - item["last_seen"] > self.ttl_seconds]:
            self.tracks.pop(key, None)
        best_key = None
        best_iou = 0.0
        for key, item in self.tracks.items():
            if item["label"] != label:
                continue
            score = self.iou(bbox, item["bbox"])
            if score >= self.iou_threshold and score > best_iou:
                best_key, best_iou = key, score
        if best_key is not None:
            self.tracks[best_key]["bbox"] = bbox
            self.tracks[best_key]["last_seen"] = now
            return best_key, False
        self.counter += 1
        track_id = f"trk-{self.counter:05d}"
        self.tracks[track_id] = {"label": label, "bbox": bbox, "last_seen": now}
        return track_id, True


def _overlaps_person(box: list[int], context: list[Detection]) -> bool:
    return any(
        item.label.lower() == "person"
        and item.confidence >= 0.45
        and SimpleTrackStore.iou(box, item.bbox) >= 0.15
        for item in context
    )


class FieldScanner:
    """Unified SENTRY FIELD pipeline selected by the frontend mission controls."""

    def __init__(self, config: VisionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.selected = set(config.selected_capabilities or CAPABILITY_ALIASES.values())
        self.context_model = self._load_optional(config.context_model)
        self.pothole_model = self._load_required(config.pothole_model) if "pothole" in self.selected else None
        self.road_distress_model = self._load_optional(config.road_distress_model) if "road_crack" in self.selected else None
        needs_world = bool(
            self.selected.intersection(
                {
                    "streetlight",
                    "cctv_camera",
                    "signboard",
                    "drain",
                    "solar_panel",
                    "manhole_cover",
                    "road_barrier",
                    "road_crack",
                }
            )
        )
        self.world_model = self._load_world(config.world_model) if needs_world else None
        if self.world_model is not None:
            prompts = [p for p in config.world_prompts if self._prompt_enabled(p)]
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

    def _prompt_enabled(self, prompt: str) -> bool:
        mapping = {
            "streetlight": "streetlight",
            "solar streetlight": "streetlight",
            "cctv camera": "cctv_camera",
            "road sign": "signboard",
            "signboard": "signboard",
            "road barrier": "road_barrier",
            "drain": "drain",
            "manhole cover": "drain",
            "solar panel": "solar_panel",
            "traffic cone": "road_barrier",
            "guardrail": "road_barrier",
            "utility pole": "utility_pole",
            "road crack": "road_crack",
            "vehicle": "__context__",
            "person": "__context__",
        }
        target = mapping.get(prompt.lower(), prompt.lower())
        return target in self.selected or target == "__context__"

    @staticmethod
    def _load_required(path: Path):
        if not Path(path).exists():
            raise FileNotFoundError(f"Required field model not found: {path}")
        return YOLO(str(path))

    @staticmethod
    def _load_optional(path: Path):
        return YOLO(str(path)) if Path(path).exists() else None

    @staticmethod
    def _load_world(path: Path):
        if YOLOWorld is None or not Path(path).exists():
            return None
        return YOLOWorld(str(path))

    def _save_detection(self, frame, detection: Detection, track_id: str, quality: str) -> dict:
        now = time.monotonic()
        if now - self.last_evidence_at.get(track_id, 0.0) < self.config.evidence_cooldown_seconds:
            return {}
        event = self.writer.record_detection(
            frame,
            capability=detection.label.lower().replace(" ", "_"),
            observation=f"{detection.label} observed in field camera frame",
            confidence=detection.confidence,
            bbox=detection.bbox,
            gps=None,
            mission_id=self.config.mission_id,
            requirement_id=self.config.requirement_id,
            source=self.config.source,
            detector=detection.detector,
            track_id=track_id,
            evidence_quality=quality,
        )
        self.last_evidence_at[track_id] = now
        return event.to_dict()

    def _qr_scan(self, frame) -> str | None:
        try:
            value, _, _ = self.qr_detector.detectAndDecode(frame)
            return str(value) if value else None
        except cv2.error:
            return None

    def _barcode_scan(self, frame) -> str | None:
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

    def _ocr_scan(self, frame) -> str | None:
        if not self.ocr_available or self.pytesseract is None:
            return None
        try:
            text = self.pytesseract.image_to_string(frame, config="--psm 11")
            cleaned = " ".join(text.split())
            return cleaned[:160] if cleaned else None
        except Exception:
            return None

    def scan(self, frame, frame_index: int):
        context: list[Detection] = []
        accepted: list[Detection] = []
        evidence: list[dict] = []

        if (
            self.context_model is not None
            and frame_index % max(1, self.config.context_every_n_frames) == 0
        ):
            context = _parse_result(
                self.context_model(frame, imgsz=320, conf=self.config.context_confidence, verbose=False)[0],
                "context_model",
            )

        if (
            "pothole" in self.selected
            and self.pothole_model is not None
            and frame_index % max(1, self.config.every_n_frames) == 0
        ):
            result = self.pothole_model(
                frame, imgsz=self.config.inference_size, conf=self.config.confidence, verbose=False
            )[0]
            for d in _parse_result(result, "pothole_model"):
                if _overlaps_person(d.bbox, context):
                    continue
                tid, _ = self.tracker.assign(d.label, d.bbox, time.monotonic())
                d.track_id = tid
                accepted.append(d)
                event = self._save_detection(frame, d, tid, "context_filtered")
                if event:
                    evidence.append(event)

        if (
            "road_crack" in self.selected
            and self.road_distress_model is not None
            and frame_index % max(1, self.config.every_n_frames) == 0
        ):
            result = self.road_distress_model(
                frame, imgsz=self.config.inference_size, conf=self.config.confidence, verbose=False
            )[0]
            for d in _parse_result(result, "road_distress_model"):
                tid, _ = self.tracker.assign(d.label, d.bbox, time.monotonic())
                d.track_id = tid
                accepted.append(d)
                event = self._save_detection(frame, d, tid, "specialized")
                if event:
                    evidence.append(event)

        if self.world_model is not None and frame_index % max(1, self.config.world_every_n_frames) == 0:
            result = self.world_model.predict(
                frame, imgsz=self.config.world_inference_size, conf=self.config.world_confidence, verbose=False
            )[0]
            allowed = {x.lower() for x in WORLD_EVIDENCE_CLASSES}
            for d in _parse_result(result, "open_vocabulary"):
                raw_label = d.label.lower()
                if raw_label not in allowed:
                    continue
                canonical = WORLD_CANONICAL.get(raw_label, raw_label)
                d.label = canonical.replace("_", " ")
                tid, new = self.tracker.assign(canonical, d.bbox, time.monotonic())
                d.track_id = tid
                accepted.append(d)
                if new:
                    event = self._save_detection(frame, d, tid, "open_vocabulary")
                    if event:
                        evidence.append(event)

        qr = (
            self._qr_scan(frame)
            if "asset_qr" in self.selected
            and frame_index % max(1, self.config.qr_every_n_frames) == 0
            else None
        )
        barcode = (
            self._barcode_scan(frame)
            if "asset_qr" in self.selected
            and frame_index % max(1, self.config.qr_every_n_frames) == 0
            else None
        )
        ocr = (
            self._ocr_scan(frame)
            if "asset_text" in self.selected
            and frame_index % max(1, self.config.ocr_every_n_frames) == 0
            else None
        )
        return accepted, context, qr, barcode, ocr, evidence


def run_field_scanner(config: VisionConfig = DEFAULT_CONFIG) -> None:
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(config.source)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video source: {config.source}")
    frame_index = 0
    previous_time = time.monotonic()
    fps = 0.0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                time.sleep(0.01)
                continue
            frame_index += 1
            detections, context, qr_value, barcode_value, ocr_text, _ = scanner.scan(frame, frame_index)
            for d in detections:
                x1, y1, x2, y2 = d.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    frame,
                    f"{d.label} {d.confidence:.2f}",
                    (x1, max(22, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 0, 0),
                    2,
                )
            now = time.monotonic()
            dt = now - previous_time
            previous_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)
            cv2.putText(
                frame,
                f"SENTRY FIELD | FPS {fps:.1f} | findings {len(detections)} | context {len(context)}",
                (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            identity = " | ".join(v for v in (qr_value, barcode_value, ocr_text) if v)
            if identity:
                cv2.putText(
                    frame,
                    f"ID: {identity[:120]}",
                    (14, 56),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (0, 255, 0),
                    2,
                )
            cv2.imshow("SENTRY FIELD - Unified Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
