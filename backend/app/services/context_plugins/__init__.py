"""Context Plugin package — one file per legitimate procurement context.

The Evidence Challenge engine consumes plugins exclusively through
:mod:`app.services.context_plugins.registry`; it has no knowledge of any
specific context. To add a new procurement context, create ONE new module in
this package defining a ``ContextPlugin`` subclass decorated with ``@register``
— nothing else in the codebase changes.
"""

from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import all_plugins, applicable_plugins, load_plugins, register

__all__ = ["ContextPlugin", "all_plugins", "applicable_plugins", "load_plugins", "register"]
