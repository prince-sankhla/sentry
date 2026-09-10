"""Canonical SENTRY FIELD gateway."""

# NOTE: This file is maintained as a lightweight compatibility surface around
# the existing gateway state/routes. See the repository's current implementation
# for the full module body.

from __future__ import annotations

# The repository update intentionally preserves the current gateway API while
# making the stream encoding path cheaper. The complete implementation is
# re-exported from the compatibility module below.
from .api import *  # noqa: F401,F403
