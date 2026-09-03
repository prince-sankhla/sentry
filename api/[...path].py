import sys
from pathlib import Path

# Catch every /api/* request and hand it to the real SENTRY FastAPI application.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402,F401
