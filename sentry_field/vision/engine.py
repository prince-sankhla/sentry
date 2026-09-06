import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import torch
from ultralytics import YOLO

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


def run_pothole_demo(config: VisionConfig = DEFAULT_CONFIG) -> None:
    """Run the validated pothole detector against the newest live frame."""
    model_path = Path(config.pothole_model)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Pothole model not found: {model_path}. "
            "Place yolo26_best.pt there before starting the demo."
        )

    model = YOLO(str(model_path))
    device = resolve_device()
    print(f"SENTRY FIELD device: {device}")

    reader = LatestFrameReader(config.source)
    reader.start()
    frame_count = 0
    last_annotated = None

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
                last_annotated = result.plot()

            display = last_annotated if last_annotated is not None else frame
            cv2.imshow("SENTRY FIELD - Live Vision", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        reader.stop()
        cv2.destroyAllWindows()
