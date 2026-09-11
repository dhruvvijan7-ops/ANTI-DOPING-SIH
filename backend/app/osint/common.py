"""Shared OSINT primitives: SSRF-safe fetching, normalization, hashing, rate limiting.

Security and operational guards live here once so every connector path is protected:
- only http/https schemes,
- hostnames validated against private/loopback/link-local/reserved ranges,
- redirects re-validated at every hop,
- explicit connect/read timeouts,
- bounded response size,
- per-source token-bucket rate limiting.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

# Operational limits (environment-independent; conservative defaults).
HTTP_TIMEOUT_SECONDS = 30.0
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MiB per response
MAX_REDIRECTS = 4
MAX_RECORDS_PER_COLLECT = 100

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) VERITY-OSINT/0.1 (+anti-doping "
    "intelligence; contact platform admin) AppleWebKit/537.36 (KHTML, "
    "like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_SCHEME_ALLOWED = {"http", "https"}

# Reserved/private networks that must never be reached by an SSRF guard.
_BLOCKED_NETWORKS: list[ipaddress._BaseNetwork] = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("2001:db8::/32"),
]


class OsintError(Exception):
    """Base OSINT error."""


class InvalidSourceUrlError(OsintError):
    """Rejected by the SSRF guard (bad scheme, non-public host, etc.)."""


class FetchTimeoutError(OsintError):
    """Upstream did not respond in time."""


class HttpStatusError(OsintError):
    """Upstream returned an HTTP error."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429


class RateLimitedError(OsintError):
    """Per-source token bucket exhausted."""


class MalformedDataError(OsintError):
    """Upstream returned data we could not normalize."""


def is_public_url(url: str) -> bool:
    """Scheme + host checks without DNS (fast failure)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme.lower() not in _SCHEME_ALLOWED:
        return False
    host = (parts.hostname or "").strip()
    if not host:
        return False
    return True


def _is_blocked(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True  # not parseable -> treat as unsafe
    return any(ip in network for network in _BLOCKED_NETWORKS)


def validate_public_host(url: str) -> None:
    """SSRF guard: reject non-http(s), non-public hosts (resolves DNS)."""
    if not is_public_url(url):
        raise InvalidSourceUrlError(
            "Only public http/https URLs are allowed for OSINT collection"
        )
    host = urlsplit(url).hostname  # type: ignore[union-attr]
    addresses: list[str] = []
    try:
        infos = socket.getaddrinfo(host, None, family=socket.AF_UNSPEC)
        for info in infos:
            addr = info[4][0]
            addresses.append(addr)
            if _is_blocked(addr):
                raise InvalidSourceUrlError(
                    f"SSRF guard: host {host!r} resolved to non-public address {addr}"
                )
    except socket.gaierror as exc:
        raise InvalidSourceUrlError(f"Could not resolve host {host!r}: {exc}")
    if not addresses:
        raise InvalidSourceUrlError(f"Host {host!r} resolved to no usable addresses")


# HTTP 429 backoff. Several upstreams (GDELT DOC 2.0, various corporate WAFs)
# enforce a per-request minimum spacing server-side *in addition to* any
# per-source token bucket; the SSRF guard connects to the real host as soon as
# the public-address validation passes (§405 rate limiting / §312 matrix).
# Retrying on a bounded number of 429s (honouring Retry-After when present)
# keeps a single health probe + collect from bursting past the spacing window
# and avoids flapping sources to RATE_LIMITED on transient server-side charges.
GDELT_MIN_SPACING_SECONDS = 6.0
MAX_429_RETRIES = 1


def _retry_after_seconds(resp: httpx.Response) -> float:
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return GDELT_MIN_SPACING_SECONDS
    try:
        return float(raw) if raw.isdigit() else 0.0
    except ValueError:
        return GDELT_MIN_SPACING_SECONDS


def safe_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
    allow_empty: bool = False,
) -> httpx.Response:
    """HTTP GET with SSRF validation at every redirect hop."""
    validate_public_host(url)

    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)

    current_url = url
    retries = 0
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_host(current_url)
        with httpx.Client(follow_redirects=False, timeout=timeout) as client:
            resp = client.get(current_url, params=params, headers=hdrs)
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location")
            if not location:
                raise MalformedDataError("Redirect without a Location header")
            target = httpx.URL(str(resp.url)).join(location)
            if not is_public_url(str(target)):
                raise InvalidSourceUrlError("Redirect target blocked by SSRF guard")
            current_url = str(target)
            params = None  # query parameters already baked into redirect target
            continue
        if resp.status_code == 429 and retries < MAX_429_RETRIES:
            # Upstream spacing vessel (GDELT / corporate WAF) asked us to slow
            # down; honour Retry-After (or the documented minimum spacing) once,
            # then give up and let the per-source health machine report
            # RATE_LIMITED instead of looping forever (§312 failure matrix).
            time.sleep(_retry_after_seconds(resp))
            retries += 1
            continue
        if resp.status_code >= 400:
            raise HttpStatusError(resp.status_code)
        break
    else:
        raise OsintError(f"Too many redirects fetching {url}")

    if not allow_empty and len(resp.content) == 0:
        raise MalformedDataError("Empty response body")
    if len(resp.content) > MAX_BODY_BYTES:
        raise MalformedDataError("Response body exceeds the maximum allowed size")
    return resp


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")
_TITLE_NOISE = re.compile(r"[\r\n\t]+")


def normalize_text(value: str | None) -> str:
    """Collapse whitespace; trim. Used before hashing/dedupe for stability."""
    if not value:
        return ""
    value = _TITLE_NOISE.sub(" ", value)
    return _WS.sub(" ", value).strip()


def normalize_title(value: str | None) -> str:
    return normalize_text(value)


def title_signature(value: str | None) -> str:
    """Token-set signature of a title for syndication grouping (§51/§52)."""
    tokens = [t.lower() for t in re.split(r"[^a-z0-9]+", normalize_title(value) or "") if t]
    if len(tokens) < 2:
        tokens.append("__short__")
    return "-".join(sorted(set(tokens)))[:64]


def content_hash(*parts: str | None) -> str:
    """Stable sha256 fingerprint over canonical identity fields for dedupe."""
    joined = "|".join((p or "").strip().lower() for p in parts)
    return hashlib.sha256(joined.encode("utf-8", errors="replace")).hexdigest()


def parse_datetime(value: str | None) -> datetime | None:
    """Best-effort ISO/RFC 2822 datetime parsing into a tz-aware UTC datetime."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(text)
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Per-source token bucket rate limiter (single process)
# ---------------------------------------------------------------------------

class _Bucket:
    __slots__ = ("capacity", "tokens", "updated", "lock")

    def __init__(self, capacity: float) -> None:
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        now = time.monotonic()
        with self.lock:
            elapsed = now - self.updated
            self.tokens = min(self.capacity, self.tokens + elapsed * (self.capacity / 60.0))
            self.updated = now
            if self.tokens < 1.0:
                return False
            self.tokens -= 1.0
            return True


_buckets: dict[str, _Bucket] = {}
_buckets_lock = threading.Lock()


def acquire_slot(source_id: str, rate_limit_per_min: int) -> None:
    """Consume one burst slot for a source; raises RateLimitedError if exhausted.

    rate_limit_per_min <= 0 means no limit (allowed for internal stub/test sources).
    """
    if rate_limit_per_min <= 0:
        return
    with _buckets_lock:
        bucket = _buckets.get(source_id)
        if bucket is None or bucket.capacity != float(rate_limit_per_min):
            bucket = _Bucket(float(rate_limit_per_min))
            _buckets[source_id] = bucket
    if not bucket.acquire():
        raise RateLimitedError(
            f"Source {source_id} exceeded rate limit of {rate_limit_per_min}/min"
        )


def reset_rate_limiter() -> None:
    """Clear all buckets (test isolation)."""
    with _buckets_lock:
        _buckets.clear()