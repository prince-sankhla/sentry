"""Context Plugin Registry — discovery and per-indicator lookup.

Plugins self-register at import via the :func:`register` decorator.
:func:`load_plugins` auto-imports every module in ``app.services.context_plugins``
so adding a new procurement context requires creating ONE new plugin file —
nothing else changes, least of all the Evidence Challenge engine.
"""

from __future__ import annotations

import importlib
import pkgutil

from app.services.context_plugins.base import ContextPlugin

_REGISTRY: dict[str, ContextPlugin] = {}
_LOADED = False


def register(cls: type[ContextPlugin]) -> type[ContextPlugin]:
    """Class decorator: instantiate and register a plugin under its ``id``."""
    plugin = cls()
    if not plugin.id:
        raise ValueError(f"Context plugin {cls.__name__} must declare an id.")
    _REGISTRY[plugin.id] = plugin
    return cls


def load_plugins() -> None:
    """Import every module in this package once, letting plugins self-register."""
    global _LOADED
    if _LOADED:
        return
    import app.services.context_plugins as package

    for module in sorted(m.name for m in pkgutil.iter_modules(package.__path__)):
        if module in ("base", "registry"):
            continue
        importlib.import_module(f"app.services.context_plugins.{module}")
    _LOADED = True


def all_plugins() -> list[ContextPlugin]:
    load_plugins()
    return sorted(_REGISTRY.values(), key=lambda p: p.id)


def applicable_plugins(indicator_id: str) -> list[ContextPlugin]:
    """Plugins that can logically explain the indicator, in their declared
    per-indicator order (ties broken by plugin id for determinism)."""
    load_plugins()
    matched = [p for p in _REGISTRY.values() if p.applies_to(indicator_id)]
    return sorted(matched, key=lambda p: (p.indicator_priority[indicator_id], p.id))
