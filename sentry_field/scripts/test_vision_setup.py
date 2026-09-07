from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"

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
        + ". Run: python sentry_field/scripts/bootstrap_all.py"
    )

if failed:
    print("SENTRY FIELD vision setup OK with optional model warnings")
else:
    print("SENTRY FIELD vision setup OK - all configured models available")
