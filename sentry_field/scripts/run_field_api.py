import os
import sys
from pathlib import Path

import uvicorn

# Running `python sentry_field\scripts\run_field_api.py` puts only the
# `scripts` directory on sys.path. Add the repository root so the package
# import works reliably from PowerShell and VS Code on Windows.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sentry_field.api_fast import FIELD_API_PORT


if __name__ == "__main__":
    host = os.getenv("SENTRY_FIELD_API_HOST", "127.0.0.1")
    port = FIELD_API_PORT
    print(f"SENTRY FIELD low-latency gateway: http://{host}:{port}")
    print("Frontend: http://localhost:3000/field")
    print("Live stream target: 60 FPS capture/display, AI runs on newest available frame")
    uvicorn.run("sentry_field.api_fast:app", host=host, port=port, reload=False)
