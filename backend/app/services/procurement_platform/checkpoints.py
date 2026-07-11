"""Facade: incremental / checkpoint engine (Phase 6)."""
from app.services.procurement_platform.incremental import (  # noqa: F401
    DeltaPlan, RetryQueue, plan_delta, resolve_conflict,
    rollback_to_version, synchronize_deletions,
)
