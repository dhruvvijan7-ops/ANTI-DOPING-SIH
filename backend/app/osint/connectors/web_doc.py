"""Official public document/page connector (gate §32-§36, §42).

Fetches a single public web page (news release, official notice, announcement) and
extracts a readable title, paragraph text and any published timestamp. This is the
connector for Tier-1 official sources that publish plain pages rather than feeds.
Guaranteed crawler-behaviour: no JS, no auth bypass, public content only.
"""
from __future__ import annotations

from html.parser import HTMLParser
from typing import NamedTuple

from app.models.osint import OsintSource
from app.osint.common import (
    HTTP_TIMEOUT_SECONDS,
    InvalidSourceUrlError,
    HttpStatusError,
    MAX_BODY_BYTES,
    normalize_text,
    safe_get,
)
from app.osint.connectors.base import (
    CollectionQuery,
    ConnectorError,
    RawItem,
    SourceConnector,
)
from app.osint.connectors.registry import register

_TEXT_TAGS = {"p", "div", "article", "section", "h1", "h2", "h3", "h4", "li", "blockquote", "td"}
_SKIP_TAGS = {"script", "style", "noscript", "head", "iframe", "svg"}


class _Page(NamedTuple):
    title: str
    body: str
    published: str | None


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title: list[str] = []
        self._paragraphs: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._buffer: list[str] = []
        self._in_text_tag = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        low = tag.lower()
        if low in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if low == "title":
            self._in_title = True
        if low in _TEXT_TAGS:
            self._in_text_tag = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        low = tag.lower()
        if low in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if low == "title":
            self._in_title = False
        if low in _TEXT_TAGS:
            text = normalize_text("".join(self._buffer))
            if text:
                self._paragraphs.append(text)
            self._buffer = []
            self._in_text_tag = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title.append(data)
        elif self._in_text_tag:
            self._buffer.append(data)

    @property
    def title(self) -> str:
        return normalize_text(" ".join(self._title))

    @property
    def body(self) -> str:
        return " ".join(self._paragraphs)


def _extract(page_html: bytes, url: str) -> _Page:
    parser = _Extractor()
    try:
        text = page_html.decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - decode fallback
        raise ConnectorError(f"Cannot decode page: {exc}") from exc
    parser.feed(text)

    title = parser.title or url
    body = parser.body
    if not body and not title:
        raise ConnectorError(f"No readable text extracted from {url}")

    # Published timestamp from common meta tags (public page metadata).
    published: str | None = None
    import re

    m = re.search(
        r'(?:article:published_time|og:published_time|datepublished|datePublished)\s*=?\s*["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    if m:
        published = m.group(1).strip()
    return _Page(title=title, body=body[:MAX_BODY_BYTES], published=published)


@register
class WebDocConnector(SourceConnector):
    connector_type = "web_doc"
    source_kind = "OFFICIAL"

    def health(self, source: OsintSource) -> str | None:
        try:
            resp = safe_get(source.url, timeout=HTTP_TIMEOUT_SECONDS)
        except (InvalidSourceUrlError, HttpStatusError, ConnectorError) as exc:
            return str(exc)
        try:
            _extract(resp.content, source.url)
        except ConnectorError as exc:
            return str(exc)
        return None

    def fetch(self, source: OsintSource, query: CollectionQuery) -> list[RawItem]:
        resp = safe_get(source.url, timeout=HTTP_TIMEOUT_SECONDS)
        page = _extract(resp.content, source.url)
        return [
            RawItem(
                title=page.title,
                source_url=source.url,
                canonical_url=source.url,
                publisher=source.name,
                content=page.body,
                published_at=page.published,
                language=None,
                source_type=self.source_kind,
                extraction_method="web_doc",
            )
        ]