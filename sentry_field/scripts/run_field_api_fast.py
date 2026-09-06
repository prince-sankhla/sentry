import os

import uvicorn

from ..api_fast import FIELD_API_PORT


if __name__ == "__main__":
    host = os.getenv("SENTRY_FIELD_API_HOST", "127.0.0.1")
    port = FIELD_API_PORT
    print(f"SENTRY FIELD low-latency gateway: http://{host}:{port}")
    print("Frontend: http://localhost:3000/field")
    uvicorn.run("sentry_field.api_fast:app", host=host, port=port, reload=False)
