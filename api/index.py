import sys
from pathlib import Path

# Vercel's Python runtime exposes this module as the /api/* function.
# Keep the existing FastAPI application as the single source of API routes.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402,F401
