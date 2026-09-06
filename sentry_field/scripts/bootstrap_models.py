from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "field"

MODELS = {
    "pothole": (
        MODEL_DIR / "pothole" / "yolo26_best.pt",
        "https://huggingface.co/DanielsStulpe/pothole-detection/resolve/main/yolo26_best.pt?download=true",
    ),
}


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1_000_000:
        print(f"already present: {destination}")
        return

    request = Request(url, headers={"User-Agent": "SENTRY-Field/1.0"})
    print(f"downloading: {destination.name}")
    with urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)

    size = destination.stat().st_size
    if size < 1_000_000:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"Downloaded file is unexpectedly small ({size} bytes): {destination}"
        )
    print(f"saved: {destination} ({size / 1024 / 1024:.1f} MB)")


def main() -> None:
    for _, (destination, url) in MODELS.items():
        download(url, destination)
    print("SENTRY FIELD model bootstrap complete")


if __name__ == "__main__":
    main()
