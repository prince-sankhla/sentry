from __future__ import annotations

from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"

MIN_ULTRALYTICS = Version("8.4.146")
MODELS = {
    "pothole": MODEL_DIR / "pothole" / "yolo26_best.pt",
    "context": MODEL_DIR / "context" / "yolo11n.pt",
    "open_vocabulary": MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt",
    "streetlight_specialized": MODEL_DIR / "streetlight" / "yolor-streetlights-last.pt",
    "road_crack_specialized": MODEL_DIR / "road_distress" / "best.pt",
}

print("SENTRY FIELD setup check")
print(f"Project root: {ROOT}")

try:
    import cv2
    import torch
    import ultralytics
    print(f"OpenCV: {cv2.__version__}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Ultralytics: {ultralytics.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if Version(str(ultralytics.__version__)) < MIN_ULTRALYTICS:
        raise RuntimeError(
            f"Ultralytics {ultralytics.__version__} is too old for the configured YOLO26 pothole model; "
            f"install >= {MIN_ULTRALYTICS} with: python -m pip install -U ultralytics>={MIN_ULTRALYTICS}"
        )
except Exception as exc:
    raise SystemExit(f"Vision dependency check failed: {exc}") from exc

from ultralytics import YOLO

failed: list[str] = []
for name, path in MODELS.items():
    if not path.exists() or path.stat().st_size <= 1_000_000:
        status = "MISSING"
        failed.append(name)
        print(f"{name}: {status} -> {path}")
        continue

    try:
        model = YOLO(str(path))
        print(f"{name}: OK ({path.stat().st_size / 1024 / 1024:.1f} MB) | classes={model.names}")
    except Exception as exc:
        failed.append(name)
        print(f"{name}: BROKEN -> {exc}")

optional = {"streetlight_specialized", "road_crack_specialized"}
required_failed = [name for name in failed if name not in optional]
if required_failed:
    raise SystemExit(
        "Required field models are missing/broken: "
        + ", ".join(required_failed)
        + ". Run: python sentry_field\\scripts\\bootstrap_all.py"
    )

if failed:
    print("SENTRY FIELD vision setup OK with optional model warnings")
else:
    print("SENTRY FIELD vision setup OK - all configured models available")
