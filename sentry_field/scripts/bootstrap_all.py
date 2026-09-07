from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"

# Small, public model set used by the current SENTRY FIELD prototype.
# Large weights stay out of git; this script downloads them locally when needed.
MODELS = {
    "pothole": (
        MODEL_DIR / "pothole" / "yolo26_best.pt",
        "https://huggingface.co/DanielsStulpe/pothole-detection/resolve/main/yolo26_best.pt?download=true",
    ),
    "context": (
        MODEL_DIR / "context" / "yolo11n.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",
    ),
    "open_vocabulary": (
        MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt",
    ),
    "streetlight": (
        MODEL_DIR / "streetlight" / "yolor-streetlights-last.pt",
        "https://huggingface.co/cpnlab/YOLOR-Streetlights/resolve/main/last.pt?download=true",
    ),
    "road_crack": (
        MODEL_DIR / "road_distress" / "best.pt",
        "https://huggingface.co/cazzz307/yolov8-crack-detection/resolve/main/best.pt?download=true",
    ),
}

REQUIRED_PACKAGES = {
    "ultralytics": "ultralytics",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "pandas": "pandas",
    "pytesseract": "pytesseract",
    "pyzbar": "pyzbar",
}


def ensure_package(module: str, package: str) -> None:
    if importlib.util.find_spec(module) is not None:
        print(f"OK package: {package}")
        return
    print(f"Installing package: {package}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1_000_000:
        print(f"OK model: {destination.relative_to(ROOT)}")
        return

    temp = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "SENTRY-Field/1.0"})
    print(f"Downloading {destination.name} ...")
    try:
        with urlopen(request, timeout=300) as response, temp.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        size = temp.stat().st_size
        if size < 1_000_000:
            raise RuntimeError(f"Downloaded file is unexpectedly small: {size} bytes")
        temp.replace(destination)
        print(f"OK model: {destination.relative_to(ROOT)} ({size / 1024 / 1024:.1f} MB)")
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    print("SENTRY FIELD bootstrap")
    print(f"Project root: {ROOT}")
    print("\n[1/2] Python dependencies")
    for module, package in REQUIRED_PACKAGES.items():
        ensure_package(module, package)

    print("\n[2/2] Field model weights")
    for name, (destination, url) in MODELS.items():
        try:
            download(url, destination)
        except Exception as exc:
            # The specialized crack/streetlight weights are additive; do not block
            # pothole/context/world setup if a third-party host is temporarily down.
            if name in {"road_crack", "streetlight"}:
                print(f"WARN optional model unavailable ({name}): {exc}")
            else:
                raise

    print("\nBootstrap complete.")
    print("Run: python sentry_field\\scripts\\test_vision_setup.py")


if __name__ == "__main__":
    main()
