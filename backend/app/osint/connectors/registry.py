"""Connector registry (§46). New connector families register by connector_type."""
from __future__ import annotations

from app.osint.connectors.base import SourceConnector

_REGISTRY: dict[str, type[SourceConnector]] = {}


def register(cls: type[SourceConnector]) -> type[SourceConnector]:
    _REGISTRY[cls.connector_type] = cls
    return cls


def get_connector(connector_type: str) -> type[SourceConnector] | None:
    return _REGISTRY.get(connector_type)


def connector_types() -> list[str]:
    return sorted(_REGISTRY.keys())


def register_type(connector_type: str, cls: type[SourceConnector]) -> None:
    """Test hook: register an ad-hoc connector type (e.g. a local stub)."""
    _REGISTRY[connector_type] = cls