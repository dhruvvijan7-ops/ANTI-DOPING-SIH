"""SourceConnector abstraction (gate §46 §48).

A connector knows how to talk to one family of external public sources: GDELT (news
search), RSS/Atom feeds, or a single official public web page. It exposes health()
and fetch() and returns normalized raw records; storage/dedupe/rate-limit/SSRF are
handled by the OSINT service (every connector fetch runs through common.safe_get).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.osint import OsintSource

SOURCE_TYPE_GENERIC = "GENERIC"


class ConnectorError(Exception):
    """Connector-level failure (timeout, status, parsing)."""


@dataclass
class RawItem:
    """Normalized record produced by a connector (§49 fields)."""

    title: str
    source_url: str | None = None
    canonical_url: str | None = None
    publisher: str | None = None
    author: str | None = None
    content: str | None = None
    published_at: str | None = None
    language: str | None = None
    source_type: str = "GENERIC"
    extraction_method: str = "api"
    extra: dict = field(default_factory=dict)


@dataclass
class CollectionQuery:
    """Targeted collection intent (§243 §244). Neutral sources may ignore terms."""

    terms: str | None = None
    days: int | None = None
    max_records: int = 30


class SourceConnector(ABC):
    """Interface every connector implements (§46)."""

    #: Registry key; subclass sets it.
    connector_type: str = "base"

    @abstractmethod
    def health(self, source: OsintSource) -> str | None:
        """Return None if healthy, or a machine health reason string.

        Implementations must be cheap and must not raise for network issues.
        """

    @abstractmethod
    def fetch(self, source: OsintSource, query: CollectionQuery) -> list[RawItem]:
        """Collect and normalize records from the real source.

        May raise ConnectorError; the OSINT service converts that to a FAILED
        health state with a stored reason.
        """