import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sentry_field.api import FIELD_API_PORT, app


if __name__ == "__main__":
    host = os.getenv("SENTRY_FIELD_API_HOST", "127.0.0.1")
    port = FIELD_API_PORT
    print(f"SENTRY FIELD canonical gateway: http://{host}:{port}")
    print(f"Loaded app: {app.title}")
    uvicorn.run(app, host=host, port=port, reload=False)
