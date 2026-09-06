import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO

try:
    from ultralytics import YOLOWorld
except ImportError:  # pragma: no cover - depends on installed Ultralytics build
    YOLOWorld = None  # type: ignore[assignment]

from ..evidence import EvidenceWriter
from .capabilities import WORLD_EVIDENCE_CLASSES
from .config import DEFAULT_CONFIG, VisionConfig


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: list[int]
    detector: str
    track_id: str | None = None


class SimpleTrackStore:
    """Small IoU-based tracker used to suppress repeat evidence from the same view."""

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
        expired = [key for key, item in self.tracks.items() if now - item["last_seen"] > self.ttl_seconds]
        for key in expired:
            self.tracks.pop(key, None)

        best_key: str | None = None
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


def _box(box: Any) -> list[int]:
    return [int(round(float(value))) for value in box]


def _parse_result(result: Any, detector: str) -> list[Detection]:
    if result is None or result.boxes is None or len(result.boxes) == 0:
        return []
    names = result.names
    output: list[Detection] = []
    for index in range(len(result.boxes)):
        class_id = int(result.boxes.cls[index].item())
        label = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(class_id)
        output.append(
            Detection(
                label=label,
                confidence=float(result.boxes.conf[index].item()),
                bbox=_box(result.boxes.xyxy[index].tolist()),
                detector=detector,
            )
        )
    return output


def _overlaps_person(box: list[int], context: list[Detection]) -> bool:
    for item in context:
        if item.label.lower() != "person" or item.confidence < 0.45:
            continue
        overlap = SimpleTrackStore.iou(box, item.bbox)
        if overlap >= 0.15:
            return True
    return False


class FieldScanner:
    """Unified SENTRY FIELD vision pipeline for specialized + general + identity signals."""

    def __init__(self, config: VisionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.pothole_model = self._load_required(config.pothole_model)
        self.context_model = self._load_required(config.context_model)
        self.world_model = self._load_world(config.world_model)
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

    @staticmethod
    def _load_required(path: Path):
        if not Path(path).exists():
            raise FileNotFoundError(f"Required field model not found: {path}")
        return YOLO(str(path))

    @staticmethod
    def _load_world(path: Path):
        if YOLOWorld is None or not Path(path).exists():
            return None
        model = YOLOWorld(str(path))
        return model

    def _save_detection(self, frame, detection: Detection, track_id: str, quality: str) -> None:
        now = time.monotonic()
        last = self.last_evidence_at.get(track_id, 0.0)
        if now - last < self.config.evidence_cooldown_seconds:
            return

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
        print(
            f"FIELD EVIDENCE: {event.event_id} | {detection.label} | "
            f"confidence={detection.confidence:.2f} | track={track_id}"
        )

    def _qr_scan(self, frame) -> str | None:
        if not self.config.qr_enabled:
            return None
        try:
            value, points, _ = self.qr_detector.detectAndDecode(frame)
            if value:
                return str(value)
        except cv2.error:
            return None
        return None

    def _ocr_scan(self, frame) -> str | None:
        if not self.config.ocr_enabled or not self.ocr_available or self.pytesseract is None:
            return None
        try:
            # OCR is intentionally sparse: it runs less often than object detection.
            text = self.pytesseract.image_to_string(frame, config="--psm 11")
            cleaned = " ".join(text.split())
            return cleaned[:160] if cleaned else None
        except Exception:
            return None

    def scan(self, frame, frame_index: int) -> tuple[Any, list[Detection], list[Detection], str | None, str | None]:
        all_detections: list[Detection] = []

        if frame_index % max(1, self.config.every_n_frames) == 0:
            result = self.pothole_model(
                frame,
                imgsz=self.config.inference_size,
                conf=self.config.confidence,
                verbose=False,
            )[0]
            potholes = _parse_result(result, "pothole_model")
        else:
            potholes = []

        context = []
        if frame_index % max(1, self.config.context_every_n_frames) == 0:
            result = self.context_model(
                frame,
                imgsz=320,
                conf=self.config.context_confidence,
                verbose=False,
            )[0]
            context = _parse_result(result, "context_model")

        accepted: list[Detection] = []
        for detection in potholes:
            if _overlaps_person(detection.bbox, context):
                continue
            accepted.append(detection)
            track_id, _ = self.tracker.assign(detection.label, detection.bbox, time.monotonic())
            detection.track_id = track_id
            if self.config.tracking_enabled:
                self._save_detection(frame, detection, track_id, "context_filtered")

        all_detections.extend(accepted)
        all_detections.extend(item for item in context if item.label.lower() != "person")

        if self.world_model is not None and frame_index % max(1, self.config.world_every_n_frames) == 0:
            self.world_model.set_classes(list(self.config.world_prompts))
            result = self.world_model.predict(
                frame,
                imgsz=self.config.world_inference_size,
                conf=self.config.world_confidence,
                verbose=False,
            )[0]
            for detection in _parse_result(result, "open_vocabulary"):
                if detection.label.lower() not in {item.lower() for item in WORLD_EVIDENCE_CLASSES}:
                    continue
                track_id, is_new = self.tracker.assign(detection.label, detection.bbox, time.monotonic())
                detection.track_id = track_id
                accepted.append(detection)
                if is_new:
                    self._save_detection(frame, detection, track_id, "open_vocabulary")

        qr_value = None
        if frame_index % max(1, self.config.qr_every_n_frames) == 0:
            qr_value = self._qr_scan(frame)
            if qr_value:
                print(f"FIELD IDENTITY: QR={qr_value[:100]}")

        ocr_text = None
        if frame_index % max(1, self.config.ocr_every_n_frames) == 0:
            ocr_text = self._ocr_scan(frame)
            if ocr_text:
                print(f"FIELD IDENTITY: OCR={ocr_text}")

        return frame, accepted, context, qr_value, ocr_text


def run_field_scanner(config: VisionConfig = DEFAULT_CONFIG) -> None:
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(config.source)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video source: {config.source}")

    print("SENTRY FIELD unified scanner")
    print(f"  device: CPU/CUDA selected by Ultralytics")
    print(f"  world detector: {'enabled' if scanner.world_model is not None else 'not bootstrapped'}")
    print(f"  OCR: {'enabled' if scanner.ocr_available else 'optional/unavailable'}")
    print("  QR: enabled")
    print("Press Q to stop")

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
            _, detections, context, qr_value, ocr_text = scanner.scan(frame, frame_index)
            display = frame.copy()

            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                label = f"{detection.label} {detection.confidence:.2f}"
                if detection.track_id:
                    label += f" [{detection.track_id}]"
                cv2.putText(display, label, (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

            now = time.monotonic()
            dt = now - previous_time
            previous_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            hud = f"SENTRY FIELD | FPS {fps:.1f} | detections {len(detections)}"
            if context:
                hud += f" | context {len(context)}"
            cv2.putText(display, hud, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            if qr_value:
                cv2.putText(display, f"QR: {qr_value[:70]}", (14, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 0), 2)
            if ocr_text:
                cv2.putText(display, f"OCR: {ocr_text[:70]}", (14, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 0), 2)

            cv2.imshow("SENTRY FIELD - Unified Scanner", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
