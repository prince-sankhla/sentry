"""Registry-based connector classification (India-first scope).

Sprint-1 introduces an India-first build. Rather than physically moving connector
packages (which would churn imports and the registry's auto-discovery), we layer a
*classification* over the existing registry:

* every registered connector is assigned exactly one :class:`ConnectorClass`;
* only India-facing classes are **enabled by default**; International and
  Experimental connectors are **disabled by default** for live enumeration.

Nothing is deleted and nothing is removed from the registry — reporting,
validation and explicit ``get(name)`` lookups still see every connector. Only the
*default* connector enumeration used by live search (``SourceManager`` with no
explicit source list) is narrowed to the enabled set. Disabled connectors remain
fully reachable when named explicitly, and the whole filter can be turned off with
an environment variable, so this is fully reversible and breaks nothing.

Environment overrides (no code change required):

* ``SENTRY_ENABLE_ALL_SOURCES=1``      -> enable every connector (pre-Sprint-1 behaviour)
* ``SENTRY_ENABLE_INTERNATIONAL=1``    -> additionally enable International connectors
"""

from __future__ import annotations

import os
from enum import Enum


class ConnectorClass(str, Enum):
    INDIA_PROCUREMENT = "india_procurement"
    INDIA_OVERSIGHT = "india_oversight"
    INDIA_CORPORATE = "india_corporate"
    INTERNATIONAL = "international"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


# Classes that are part of the India-first default build.
INDIA_CLASSES: frozenset[ConnectorClass] = frozenset(
    {
        ConnectorClass.INDIA_PROCUREMENT,
        ConnectorClass.INDIA_OVERSIGHT,
        ConnectorClass.INDIA_CORPORATE,
    }
)

# Explicit per-connector classification. State portals (``eproc_*``) are matched by
# prefix below, so they do not need individual entries. Kept in sync with
# INDIA_DATA_AUDIT.md — the single source of truth for the audit is that document.
_CLASSIFICATION: dict[str, ConnectorClass] = {
    # -- Indian Procurement --------------------------------------------------
    "cppp": ConnectorClass.INDIA_PROCUREMENT,
    "gem": ConnectorClass.INDIA_PROCUREMENT,
    # -- Indian Oversight ----------------------------------------------------
    "cag": ConnectorClass.INDIA_OVERSIGHT,
    # -- International -------------------------------------------------------
    "world_bank": ConnectorClass.INTERNATIONAL,
    "prozorro": ConnectorClass.INTERNATIONAL,
    # -- Experimental (non-functional scaffolding / no verified source) ------
    "datagovin": ConnectorClass.EXPERIMENTAL,
    "adb": ConnectorClass.EXPERIMENTAL,
    "un_procurement": ConnectorClass.EXPERIMENTAL,
}

# Prefix rule: every NIC state eProcurement portal is Indian Procurement.
_STATE_PREFIX = "eproc_"

# Unknown/new connectors default to Experimental (disabled) so the India-first
# scope is never silently widened by a newly-registered source; add the connector
# to ``_CLASSIFICATION`` (and the audit) to promote it.
_DEFAULT_CLASS = ConnectorClass.EXPERIMENTAL


def classify(source_name: str) -> ConnectorClass:
    """Return the :class:`ConnectorClass` for a connector name."""
    if source_name.startswith(_STATE_PREFIX):
        return ConnectorClass.INDIA_PROCUREMENT
    return _CLASSIFICATION.get(source_name, _DEFAULT_CLASS)


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_enabled_by_default(source_name: str) -> bool:
    """Whether a connector participates in default (unscoped) live enumeration.

    India-facing connectors are always enabled. International connectors are
    enabled only when ``SENTRY_ENABLE_INTERNATIONAL`` (or ``SENTRY_ENABLE_ALL_SOURCES``)
    is set. Experimental/Deprecated require ``SENTRY_ENABLE_ALL_SOURCES``.
    """
    if _truthy_env("SENTRY_ENABLE_ALL_SOURCES"):
        return True
    connector_class = classify(source_name)
    if connector_class in INDIA_CLASSES:
        return True
    if connector_class is ConnectorClass.INTERNATIONAL and _truthy_env("SENTRY_ENABLE_INTERNATIONAL"):
        return True
    return False


def default_enabled_names(source_names: list[str]) -> list[str]:
    """Filter a list of connector names to those enabled by default (order preserved)."""
    return [name for name in source_names if is_enabled_by_default(name)]


def classification_summary() -> dict[str, str]:
    """Static name->class map for the named (non-state) connectors, for reporting."""
    return {name: connector_class.value for name, connector_class in _CLASSIFICATION.items()}
