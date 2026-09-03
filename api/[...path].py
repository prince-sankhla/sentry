import sys
from pathlib import Path

# Catch-all Vercel Python function for every /api/* request.
# The existing FastAPI application remains the single source of API routes.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402,F401
