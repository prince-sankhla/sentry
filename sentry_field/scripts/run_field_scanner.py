import os

from sentry_field.vision.scanner import run_field_scanner


if __name__ == "__main__":
    source = os.getenv("SENTRY_CAMERA_URL", "")
    if source:
        print(f"camera: {source}")
    run_field_scanner()
