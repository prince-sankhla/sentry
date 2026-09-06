import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import torch
from ultralytics import YOLO

from ..evidence import EvidenceWriter
from .config import DEFAULT_CONFIG, VisionConfig


class LatestFrameReader:
    """Keep only the newest camera frame so inference cannot build a stale queue."""

    def __init__(self, source: str):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.latest: Optional[object] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source: {self.source}")
        self.running = True
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        while self.running:
            ok, frame = self.cap.read()
            if ok:
                self.latest = frame
            else:
                time.sleep(0.01)

    def stop(self) -> None:
        self.running = False
        self.cap.release()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)


def resolve_device() -> str:
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _box_as_ints(box) -> list[int]:
    return [int(round(float(value))) for value in box]


def _intersection_over_area(box_a: list[int], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = [float(value) for value in box_b]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(1.0, float(ax2 - ax1) * float(ay2 - ay1))
    return intersection / area_a


def _person_overlaps(pothole_box: list[int], context_result, threshold: float) -> bool:
    if context_result is None or context_result.boxes is None or len(context_result.boxes) == 0:
        return False

    names = context_result.names
    for index in range(len(context_result.boxes)):
        class_id = int(context_result.boxes.cls[index].item())
        class_name = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(class_id)
        if class_name.lower() != "person":
            continue
        confidence = float(context_result.boxes.conf[index].item())
        if confidence < 0.45:
            continue
        person_box = context_result.boxes.xyxy[index].tolist()
        if _intersection_over_area(pothole_box, person_box) >= threshold:
            return True
    return False


def _render_filtered_result(frame, result, safe_indexes: list[int]):
    """Render only accepted potholes; suppressed candidates remain visible as warnings."""
    output = frame.copy()
    names = result.names
    safe_set = set(safe_indexes)
    for index in range(len(result.boxes)) if result.boxes is not None else []:
        box = _box_as_ints(result.boxes.xyxy[index].tolist())
        confidence = float(result.boxes.conf[index].item())
        class_id = int(result.boxes.cls[index].item())
        class_name = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(class_id)

        if index in safe_set:
            cv2.rectangle(output, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 2)
            cv2.putText(
                output,
                f"{class_name} {confidence:.2f}",
                (box[0], max(22, box[1] - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 0, 0),
                2,
                cv2.LINE_AA,
            )
        else:
            cv2.rectangle(output, (box[0], box[1]), (box[2], box[3]), (0, 140, 255), 2)
            cv2.putText(
                output,
                "suppressed: person overlap",
                (box[0], max(22, box[1] - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 140, 255),
                2,
                cv2.LINE_AA,
            )
    return output


def run_pothole_demo(config: VisionConfig = DEFAULT_CONFIG) -> None:
    """Run pothole detection with person-context suppression and evidence capture."""
    model_path = Path(config.pothole_model)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Pothole model not found: {model_path}. "
            "Place yolo26_best.pt there before starting the demo."
        )

    context_path = Path(config.context_model)
    if not context_path.exists():
        raise FileNotFoundError(
            f"Context model not found: {context_path}. "
            "Run: python sentry_field/scripts/bootstrap_context_model.py"
        )

    model = YOLO(str(model_path))
    context_model = YOLO(str(context_path))
    device = resolve_device()
    evidence_writer = EvidenceWriter(config.evidence_dir)

    print(f"SENTRY FIELD device: {device}")
    print(f"SENTRY FIELD evidence: {config.evidence_dir}")
    print("SENTRY FIELD context gate: person suppression enabled")

    reader = LatestFrameReader(config.source)
    reader.start()
    frame_count = 0
    context_count = 0
    last_annotated = None
    last_context = None
    last_evidence_at = 0.0

    try:
        while True:
            frame = reader.latest
            if frame is None:
                continue

            frame_count += 1
            if frame_count % max(1, config.every_n_frames) == 0:
                result = model(
                    frame,
                    imgsz=config.inference_size,
                    conf=config.confidence,
                    device=device,
                    verbose=False,
                )[0]

                context_count += 1
                if context_count % max(1, config.context_every_n_frames) == 0:
                    last_context = context_model(
                        frame,
                        imgsz=320,
                        conf=config.context_confidence,
                        device=device,
                        verbose=False,
                    )[0]

                safe_boxes = []
                if result.boxes is not None and len(result.boxes) > 0:
                    for index in range(len(result.boxes)):
                        box = _box_as_ints(result.boxes.xyxy[index].tolist())
                        if not _person_overlaps(box, last_context, config.person_overlap_threshold):
                            safe_boxes.append(index)

                last_annotated = _render_filtered_result(frame, result, safe_boxes)

                now = time.monotonic()
                if safe_boxes and now - last_evidence_at >= config.evidence_cooldown_seconds:
                    names = result.names
                    for index in safe_boxes:
                        box = _box_as_ints(result.boxes.xyxy[index].tolist())
                        confidence = float(result.boxes.conf[index].item())
                        class_id = int(result.boxes.cls[index].item())
                        class_name = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(class_id)

                        event = evidence_writer.record_detection(
                            frame,
                            capability="pothole_detection",
                            observation=f"{class_name} detected in field camera frame",
                            confidence=confidence,
                            bbox=box,
                            gps=None,
                            mission_id=config.mission_id,
                            requirement_id=config.requirement_id,
                            source=config.source,
                        )
                        print(
                            f"FIELD EVIDENCE: {event.event_id} | "
                            f"{class_name} | confidence={confidence:.2f}"
                        )
                    last_evidence_at = now

            display = last_annotated if last_annotated is not None else frame
            cv2.imshow("SENTRY FIELD - Live Vision", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        reader.stop()
        cv2.destroyAllWindows()
