from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from app.connectors.base import SourceConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connector_classes: dict[str, type[SourceConnector]] = {}

    def register(self, connector_class: type[SourceConnector]) -> type[SourceConnector]:
        self._connector_classes[connector_class.metadata.name] = connector_class
        return connector_class

    def get(self, source_name: str, data_root: Path | None = None) -> SourceConnector | None:
        connector_class = self._connector_classes.get(source_name)
        return connector_class(data_root=data_root) if connector_class is not None else None

    def all(self, data_root: Path | None = None) -> list[SourceConnector]:
        return [connector_class(data_root=data_root) for connector_class in self._connector_classes.values()]

    def names(self) -> list[str]:
        return sorted(self._connector_classes)


registry = ConnectorRegistry()


def register_connector(connector_class: type[SourceConnector]) -> type[SourceConnector]:
    return registry.register(connector_class)


def discover_connectors() -> ConnectorRegistry:
    connectors_path = [str(Path(__file__).resolve().parent)]
    for module_info in pkgutil.iter_modules(connectors_path, "app.connectors."):
        if module_info.name.rsplit(".", 1)[-1] in {"base", "registry", "manager"}:
            continue
        module_name = f"{module_info.name}.connector"
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name != module_name:
                raise
    return registry
