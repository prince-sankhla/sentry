import sys
from pathlib import Path

# The production FastAPI application lives under backend/app. Vercel's Python
# runtime loads this module as the /api/* function, so expose the existing ASGI
# app without duplicating routes or business logic.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402,F401
