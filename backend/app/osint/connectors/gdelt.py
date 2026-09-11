"""GDELT DOC 2.0 connector (gate §39 §235; free, keyless, public news monitoring).

The DOC API returns matching news articles. The base query is configured on the
source (url carries the API endpoint or defaults to the official endpoint) and can
include GDELT operators such as `domain:wada-ama.org` to restrict collection to
official publications. Every result keeps its origin URL so provenance is retained.
"""
from __future__ import annotations

import json
from typing import Any

from app.models.osint import OsintSource
from app.osint.common import (
    HTTP_TIMEOUT_SECONDS,
    HttpStatusError,
    InvalidSourceUrlError,
    safe_get,
)
from app.osint.connectors.base import (
    CollectionQuery,
    ConnectorError,
    RawItem,
    SourceConnector,
)
from app.osint.connectors.registry import register

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


def _gdelt_query(source: OsintSource, query: CollectionQuery) -> str:
    base = ((source.extra_config or {}).get("base_query") or "").strip()
    terms = ((query.terms or "").strip()) if query.terms else ""
    parts = [p for p in (terms, base) if p]
    if not parts:
        raise ConnectorError("GDELT source requires terms in the source query")
    return " ".join(parts)


def _ko_json_articles(data: Any) -> list[dict]:
    if isinstance(data, dict) and isinstance(data.get("articles"), list):
        return data["articles"]
    raise ConnectorError("GDELT response did not include an articles array")


@register
class GDELTConnector(SourceConnector):
    connector_type = "gdelt"
    source_kind = "NEWS"

    def health(self, source: OsintSource) -> str | None:
        probe = source.extra_config.get("probe_query") if source.extra_config else None
        query = probe or (source.extra_config or {}).get("base_query") or "journal doping"
        try:
            resp = safe_get(
                GDELT_ENDPOINT,
                params={"query": query, "mode": "artlist", "format": "json", "maxrecords": "1"},
                allow_empty=True,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except (InvalidSourceUrlError, HttpStatusError, ConnectorError) as exc:
            return str(exc)
        try:
            _ko_json_articles(json.loads(resp.text))
        except (ValueError, ConnectorError) as exc:
            return f"Unparseable response: {exc}"
        return None

    def fetch(self, source: OsintSource, query: CollectionQuery) -> list[RawItem]:
        params: dict[str, Any] = {
            "query": _gdelt_query(source, query),
            "mode": "artlist",
            "format": "json",
            "sort": "datedesc",
        }
        params["maxrecords"] = str(max(1, min(query.max_records, 100)))
        if query.days and query.days > 0:
            params["timespan"] = f"{int(query.days)}d"

        resp = safe_get(GDELT_ENDPOINT, params=params, timeout=HTTP_TIMEOUT_SECONDS)
        try:
            payload = json.loads(resp.text)
            articles = _ko_json_articles(payload)
        except (ValueError, ConnectorError) as exc:
            raise ConnectorError(f"GDELT produced malformed data: {exc}") from exc

        items: list[RawItem] = []
        for art in articles:
            if not isinstance(art, dict):
                continue
            title = (art.get("title") or "").strip()
            url = (art.get("url") or "").strip()
            if not title and not url:
                continue
            items.append(
                RawItem(
                    title=title or url,
                    source_url=url or None,
                    canonical_url=url or None,
                    publisher=art.get("domain") or None,
                    published_at=art.get("seendate") or None,
                    language=art.get("language") or None,
                    content=(art.get("content") or "").strip() or None,
                    source_type=self.source_kind,
                    extraction_method="gdelt_doc_api",
                    extra={
                        "seendate": art.get("seendate"),
                        "sourcecountry": art.get("sourcecountry"),
                    },
                )
            )
        return items