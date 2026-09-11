"""Reusable RSS/Atom connector (gate §40: one generic implementation, feed is config).

Any official/public feed an operator configures is fetched and normalized through
the same code path. feedparser handles RSS 0.9x/1.0/2.0 and Atom.
"""
from __future__ import annotations

import feedparser

from app.models.osint import OsintSource
from app.osint.common import (
    HTTP_TIMEOUT_SECONDS,
    InvalidSourceUrlError,
    HttpStatusError,
    normalize_title,
    parse_datetime,
    safe_get,
)
from app.osint.connectors.base import (
    CollectionQuery,
    ConnectorError,
    RawItem,
    SourceConnector,
)
from app.osint.connectors.registry import register


@register
class RSSConnector(SourceConnector):
    connector_type = "rss"
    source_kind = "FEED"

    def health(self, source: OsintSource) -> str | None:
        try:
            resp = safe_get(source.url, allow_empty=False, timeout=HTTP_TIMEOUT_SECONDS)
        except (InvalidSourceUrlError, HttpStatusError, ConnectorError) as exc:
            return str(exc)
        try:
            parsed = feedparser.parse(resp.content)
        except Exception as exc:  # feedparser rarely throws, but be safe
            return f"Feed parse error: {exc}"
        if parsed.bozo and not parsed.entries:
            msg = parsed.get("bozo_exception", "")
            return f"Feed bozo: {msg}" if msg else "Feed parse warning"
        return None

    def fetch(self, source: OsintSource, query: CollectionQuery) -> list[RawItem]:
        resp = safe_get(source.url, timeout=HTTP_TIMEOUT_SECONDS)
        parsed = feedparser.parse(resp.content)
        entries = parsed.entries or []
        if not entries:
            return []

        items: list[RawItem] = []
        for entry in entries[: max(1, query.max_records)]:
            title = normalize_title(entry.get("title"))
            if not title:
                continue
            link = (entry.get("link") or "").strip()
            author = None
            if entry.get("author"):
                author = entry.get("author").strip()
            elif entry.get("authors"):
                first = entry.get("authors", [{}])[0]
                author = (first.get("name") or "").strip() or None
            items.append(
                RawItem(
                    title=title,
                    source_url=link or None,
                    canonical_url=link or None,
                    publisher=(parsed.feed.get("title") if parsed.feed else None) or source.name,
                    author=author,
                    content=(entry.get("summary") or entry.get("description") or "").strip() or None,
                    published_at=(
                        entry.get("published") or entry.get("updated") or None
                    ),
                    language=(parsed.feed.get("language") if parsed.feed else None),
                    source_type=self.source_kind,
                    extraction_method="rss_feed",
                )
            )
        return items