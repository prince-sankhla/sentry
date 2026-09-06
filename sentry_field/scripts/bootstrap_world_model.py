from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "models" / "field" / "open_vocabulary" / "yolov8s-worldv2.pt"
URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt"


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists() and DESTINATION.stat().st_size > 1_000_000:
        print(f"already present: {DESTINATION}")
        return

    temp = DESTINATION.with_suffix(".pt.part")
    request = Request(URL, headers={"User-Agent": "SENTRY-Field/1.0"})
    print(f"downloading: {DESTINATION.name}")
    try:
        with urlopen(request, timeout=120) as response, temp.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        size = temp.stat().st_size
        if size < 1_000_000:
            raise RuntimeError(f"Downloaded file is unexpectedly small: {size} bytes")
        temp.replace(DESTINATION)
    finally:
        temp.unlink(missing_ok=True)

    print(f"saved: {DESTINATION} ({size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
