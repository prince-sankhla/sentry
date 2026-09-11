from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"

REQUIRED_ULTRALYTICS = "8.4.146"

# Public prototype weights. Large binaries stay out of git and are fetched locally.
MODELS = {
    "pothole": (
        MODEL_DIR / "pothole" / "yolo26_best.pt",
        "https://huggingface.co/DanielsStulpe/pothole-detection/resolve/main/yolo26_best.pt?download=true",
        False,
    ),
    "context": (
        MODEL_DIR / "context" / "yolo11n.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",
        False,
    ),
    "open_vocabulary": (
        MODEL_DIR / "open_vocabulary" / "yolov8s-worldv2.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt",
        False,
    ),
    "streetlight_specialized": (
        MODEL_DIR / "streetlight" / "yolor-streetlights-last.pt",
        "https://huggingface.co/cpnlab/YOLOR-Streetlights/resolve/main/last.pt?download=true",
        True,
    ),
    "road_crack_specialized": (
        MODEL_DIR / "road_distress" / "best.pt",
        "https://huggingface.co/cazzz307/yolov8-crack-detection/resolve/main/best.pt?download=true",
        True,
    ),
}

REQUIRED_PACKAGES = {
    "torch": "torch",
    "torchvision": "torchvision",
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


def ensure_ultralytics() -> None:
    try:
        import ultralytics
        from packaging.version import Version
        installed = Version(str(ultralytics.__version__))
        required = Version(REQUIRED_ULTRALYTICS)
        if installed >= required:
            print(f"OK package: ultralytics=={installed}")
            return
        print(f"Upgrading Ultralytics {installed} -> >= {REQUIRED_ULTRALYTICS} for YOLO26 support")
    except Exception:
        print(f"Installing Ultralytics >= {REQUIRED_ULTRALYTICS}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", f"ultralytics>={REQUIRED_ULTRALYTICS}"])


def download(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1_000_000:
        print(f"OK model: {destination.relative_to(ROOT)}")
        return

    temp = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "SENTRY-Field/1.0"})
            print(f"Downloading {destination.name} (attempt {attempt}/{retries}) ...")
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
            return
        except (HTTPError, URLError, OSError, RuntimeError) as exc:
            last_error = exc
            temp.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Could not download {url}: {last_error}")


def main() -> None:
    print("SENTRY FIELD bootstrap")
    print(f"Project root: {ROOT}")

    print("\n[1/2] Python dependencies")
    ensure_ultralytics()
    for module, package in REQUIRED_PACKAGES.items():
        ensure_package(module, package)

    print("\n[2/2] Field model weights")
    warnings: list[str] = []
    for name, (destination, url, optional) in MODELS.items():
        try:
            download(url, destination)
        except Exception as exc:
            if optional:
                warnings.append(f"{name}: {exc}")
                print(f"WARN optional model unavailable: {name}: {exc}")
            else:
                raise

    print("\nBootstrap complete.")
    if warnings:
        print("Optional model warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    print("Run: python sentry_field\\scripts\\test_vision_setup.py")


if __name__ == "__main__":
    main()
