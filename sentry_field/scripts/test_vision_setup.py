from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
model_path = ROOT / "models" / "field" / "pothole" / "yolo26_best.pt"

print("SENTRY FIELD setup check")
print(f"Project root: {ROOT}")
print(f"Pothole model: {'OK' if model_path.exists() else 'MISSING'}")

try:
    import cv2
    import torch
    import ultralytics
    print(f"OpenCV: {cv2.__version__}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Ultralytics: {ultralytics.__version__}")
except Exception as exc:
    raise SystemExit(f"Vision dependency check failed: {exc}") from exc

if not model_path.exists():
    raise SystemExit("Run: python sentry_field/scripts/bootstrap_models.py")

from ultralytics import YOLO
model = YOLO(str(model_path))
print(f"Model classes: {model.names}")
print("SENTRY FIELD vision setup OK")
