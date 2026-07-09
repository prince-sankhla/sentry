"""Pytest bootstrap.

``app.models`` and ``app.webintel.models`` reference each other, a latent circular
that Python resolves cleanly only when ``app.models`` is imported first (as it is
in normal app startup via ``app.main``). A test module that imports a
``app.webintel`` submodule cold would otherwise trip the cycle at collection time.
Importing the model package here — before any test module is collected —
establishes the module graph in the correct order for the whole test session.
"""

from __future__ import annotations

import app.models  # noqa: F401  (import-order side effect: resolves the model cycle)
