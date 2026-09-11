"""Integration + unit tests: OSINT gate (checkpoint 1006).

Covers the master-prompt connector test matrix (§312: success, duplicate,
timeout, 429, 500, malformed, missing fields, bad URL) plus SSRF guidance,
per-source rate limiting, health transitions (ACTIVE/DEGRADED/FAILED/
RATE_LIMITED/DISABLED), syndication/dedupe clustering, provenance-preserving
promotion into intelligence, claims round-trip, default source registry seeding
and RBAC (§30-§54, §240-§254, §405, §463).
"""
from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.osint import OsintSource
from app.osint.common import (
    InvalidSourceUrlError,
    RateLimitedError,
    is_public_url,
    safe_get,
    validate_public_host,
)
from app.osint.connectors.base import CollectionQuery, ConnectorError, RawItem, SourceConnector
from app.osint.connectors.registry import get_connector, register_type
from app.osint.service import run_source_collection
from tests.support_domain import ALICE, seed_domain

# ---------------------------------------------------------------------------
# Test connector: a fully local stub (no network) that emulates every upstream
# failure the real connectors can encounter.
# ---------------------------------------------------------------------------

class StubConnector(SourceConnector):
    connector_type = "stub_news"
    source_kind = "NEWS"

    def health(self, source: OsintSource) -> str | None:
        return None

    def fetch(self, source: OsintSource, query: CollectionQuery) -> list[RawItem]:
        cfg = source.extra_config or {}
        err = cfg.get("stub_error")
        if err == "connector":
            raise ConnectorError("stub connector boom")
        if err == "malformed":
            raise ConnectorError("upstream returned malformed data")
        if err == "badurl":
            raise InvalidSourceUrlError("stub bad url")
        if err == "ratelimit":
            raise RateLimitedError("stub upstream rate limited")
        if err == "timeout":
            raise httpx.ReadTimeout("stub timeout")
        if err == "http404":
            from app.osint.common import HttpStatusError

            raise HttpStatusError(404)
        if err == "http500":
            from app.osint.common import HttpStatusError

            raise HttpStatusError(500)
        if err == "http429":
            from app.osint.common import HttpStatusError

            raise HttpStatusError(429)
        rows = []
        for it in cfg.get("stub_items") or []:
            kwargs = {k: v for k, v in it.items() if k in RawItem.__dataclass_fields__}
            rows.append(RawItem(**kwargs))
        return rows


register_type("stub_news", StubConnector)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.osint.common import reset_rate_limiter

    reset_rate_limiter()
    yield


DEFAULT_ITEM = {
    "title": "Anti-doping agency issues statement on Test ATH-ALICE",
    "source_url": "https://www.wada-ama.org/en/news/2024-03-15/statement",
    "canonical_url": "https://www.wada-ama.org/en/news/2024-03-15/statement",
    "publisher": "wada-ama.org",
    "published_at": "2024-03-15T10:00:00Z",
    "content": "The anti-doping agency released a statement concerning Test ATH-ALICE and the ongoing review of whereabout filings.",
    "language": "en",
}


def _source_body(source_id="test-news-1", **overrides) -> dict:
    body = {
        "source_id": source_id,
        "name": "Test news wire",
        "connector_type": "stub_news",
        "url": "https://example.com/news",
        "authority": "PUBLIC_NEWS",
        "jurisdiction": "GLOBAL",
        "rate_limit_per_min": 20,
        "extra_config": {"stub_items": [dict(DEFAULT_ITEM)]},
    }
    body.update(overrides)
    return body


def _create(client, **overrides) -> dict:
    resp = client.post("/api/v1/osint/sources", json=_source_body(**overrides))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _collect(client, source_id: uuid.UUID, **params) -> dict:
    resp = client.post(
        f"/api/v1/osint/sources/{source_id}/collect",
        json={"terms": params.pop("terms", None), **params},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _err(resp) -> str:
    body = resp.json()
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"].get("message") or ""
    return str(body)


# ---------------------------------------------------------------------------
# Source registry CRUD, validation, connector metadata
# ---------------------------------------------------------------------------

def test_connector_types_available(admin_client):
    resp = admin_client.get("/api/v1/osint/connector-types")
    assert resp.status_code == 200, resp.text
    by_type = {c["connector_type"]: c for c in resp.json()["connectors"]}
    assert {"gdelt", "rss", "web_doc", "stub_news"} <= set(by_type)
    assert by_type["gdelt"]["source_kind"] == "NEWS"
    assert by_type["gdelt"]["search_driven"] is True
    assert by_type["rss"]["source_kind"] == "FEED"


def test_source_lifecycle_and_validation(admin_client):
    created = _create(admin_client, source_id="lifecycle-1")
    assert created["source_id"] == "lifecycle-1"
    assert created["health"] == "ACTIVE"
    assert created["enabled"] is True

    dup = admin_client.post(
        "/api/v1/osint/sources", json=_source_body(source_id="lifecycle-1")
    )
    assert dup.status_code == 409

    bad_type = admin_client.post(
        "/api/v1/osint/sources", json=_source_body(source_id="lt-2", connector_type="nope")
    )
    assert bad_type.status_code == 422

    bad_scheme = admin_client.post(
        "/api/v1/osint/sources",
        json=_source_body(source_id="lt-3", url="file:///etc/passwd"),
    )
    assert bad_scheme.status_code == 422
    assert "public" in _err(bad_scheme).lower()

    bad_authority = admin_client.post(
        "/api/v1/osint/sources", json=_source_body(source_id="lt-4", authority="TOP_SECRET")
    )
    assert bad_authority.status_code == 422

    patched = admin_client.patch(
        f"/api/v1/osint/sources/{created['id']}",
        json={"name": "Renamed wire", "authority": "OFFICIAL"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Renamed wire"
    assert patched.json()["authority"] == "OFFICIAL"

    health = admin_client.get(f"/api/v1/osint/sources/{created['id']}/health")
    assert health.status_code == 200
    assert health.json()["health"] == "ACTIVE"

    listing = admin_client.get("/api/v1/osint/sources")
    assert listing.status_code == 200
    assert any(s["source_id"] == "lifecycle-1" for s in listing.json()["sources"])

    gone = admin_client.delete(f"/api/v1/osint/sources/{created['id']}")
    assert gone.status_code == 200
    missing = admin_client.get(
        f"/api/v1/osint/sources/{created['id']}/health"
    )
    assert missing.status_code == 404
    assert admin_client.get("/api/v1/osint/sources").json()["count"] == 0


def test_default_source_registry_seeded_idempotently(admin_client):
    first = admin_client.post("/api/v1/osint/sources/defaults")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["sources_total"] == 5
    assert body["records_total"] == 0  # configuration only, no fabricated records

    again = admin_client.post("/api/v1/osint/sources/defaults").json()
    assert again["sources_total"] == 5  # idempotent

    listing = admin_client.get("/api/v1/osint/sources").json()
    refs = {s["source_id"]: s for s in listing["sources"]}
    assert "gdelt-global" in refs
    assert "wada-news-rss" in refs
    assert "nadaindia-site" not in refs  # disabled by default -> hidden
    assert get_connector(refs["gdelt-official"]["connector_type"]) is not None


# ---------------------------------------------------------------------------
# Collection: success, provenance, mentions, dedupe, syndication
# ---------------------------------------------------------------------------

def test_collection_stores_records_with_provenance_and_mentions(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    source = _create(admin_client, source_id="collect-1")
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)

    assert out["ok"] is True
    assert out["health"] == "ACTIVE"
    assert out["new_records"] == 1
    assert out["duplicates"] == 0
    assert out["mentions"] == 1  # Test ATH-ALICE grounded to ALICE
    assert out["stored"][0]["duplicate"] is False

    listing = investigator_client.get("/api/v1/osint/records").json()
    assert listing["count"] == 1
    rec = listing["records"][0]
    assert rec["title"] == DEFAULT_ITEM["title"]
    assert rec["publisher"] == "wada-ama.org"
    assert rec["authority_level"] == "PUBLIC_NEWS"
    assert rec["is_duplicate"] is False
    assert rec["source_url"].startswith("https://")

    detail = investigator_client.get(f"/api/v1/osint/records/{rec['id']}").json()
    assert detail["content"]
    assert detail["content_hash"]
    assert len(detail["mentions"]) == 1
    assert detail["mentions"][0]["subject_type"] == "ATHLETE"
    assert detail["mentions"][0]["subject_id"] == str(ALICE)
    assert detail["mentions"][0]["match_kind"] == "EXACT"
    assert detail["promoted_reports"] == 0
    assert detail["source"]["source_id"] == "collect-1"

    cluster = investigator_client.get(
        f"/api/v1/osint/records/{rec['id']}/dedupe-cluster"
    ).json()
    assert cluster["member_count"] == 1
    assert cluster["independent_sources"] == 1


def test_dedupe_by_content_hash_and_canonical_url(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    s1 = _create(admin_client, source_id="dup-a")
    base = dict(DEFAULT_ITEM)
    # same canonical URL, different publisher+date => canonical_url collision
    s2 = _create(
        admin_client,
        source_id="dup-b",
        name="Second wire",
        url="https://example.org/wire",
        extra_config={
            "stub_items": [
                {
                    **base,
                    "publisher": "news.example.org",
                    "source_url": "https://news.example.org/2024/03/15/story",
                    "published_at": "2024-03-15T08:30:00Z",
                }
            ]
        },
    )
    # same identity as s2 (title+publisher+date) but a different URL => content-hash
    # collision against the s2 row
    s3 = _create(
        admin_client,
        source_id="dup-c",
        name="Third wire",
        url="https://example2.org/wire",
        extra_config={
            "stub_items": [
                {
                    **base,
                    "publisher": "news.example.org",
                    "source_url": "https://cdn.example.org/mirror/story",
                    "canonical_url": "https://cdn.example.org/mirror/story",
                    "published_at": "2024-03-15T08:30:00Z",
                }
            ]
        },
    )

    _collect(investigator_client, uuid.UUID(s1["id"]), terms=None)
    r2 = _collect(investigator_client, uuid.UUID(s2["id"]), terms=None)
    r3 = _collect(investigator_client, uuid.UUID(s3["id"]), terms=None)

    assert r2["new_records"] == 0
    assert any(e["duplicate"] and e["reason"] == "canonical_url" for e in r2["stored"])
    assert r3["new_records"] == 0
    assert any(e["duplicate"] and e["reason"] == "content_hash" for e in r3["stored"])

    all_rows = investigator_client.get(
        "/api/v1/osint/records", params={"include_duplicates": True}
    ).json()
    assert all_rows["count"] == 3

    originals = investigator_client.get("/api/v1/osint/records").json()
    assert originals["count"] == 1  # duplicates hidden by default

    cluster = investigator_client.get(
        f"/api/v1/osint/records/{r2['stored'][0]['id']}/dedupe-cluster"
    ).json()
    assert cluster["member_count"] == 3  # syndicated family by identical title set
    assert cluster["independent_sources"] == 2


def test_syndication_group_key_truncation(admin_client, investigator_client, db):
    """A long title signature plus the unique suffix must not exceed the
    VARCHAR(64) syndication_group column."""
    seed_domain(db)
    db.commit()
    words = " ".join(f"t{i:02d}" for i in range(48))
    source = _create(
        admin_client,
        source_id="long-sig",
        extra_config={"stub_items": [{"title": f"{words} item"}]},
    )
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    assert out["ok"] is True
    assert out["new_records"] == 1
    rec = investigator_client.get("/api/v1/osint/records").json()["records"][0]
    assert rec["syndication_group"] and len(rec["syndication_group"]) <= 64


def test_collection_missing_fields_and_empty_results(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    source = _create(
        admin_client,
        source_id="minimal-1",
        extra_config={
            "stub_items": [
                {"title": "Only a title"},  # every other field missing
            ]
        },
    )
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    assert out["ok"] is True
    assert out["new_records"] == 1
    rec = investigator_client.get("/api/v1/osint/records").json()["records"][0]
    assert rec["title"] == "Only a title"
    assert rec["publisher"] is None
    assert rec["source_url"] is None

    empty = _create(
        admin_client,
        source_id="empty-1",
        extra_config={"stub_items": []},
    )
    out2 = _collect(investigator_client, uuid.UUID(empty["id"]), terms=None)
    assert out2["ok"] is True and out2["new_records"] == 0


# ---------------------------------------------------------------------------
# Health state machine + failure mapping (§312 matrix)
# ---------------------------------------------------------------------------

def test_health_failure_recovery_and_active(admin_client, investigator_client):
    source = _create(
        admin_client,
        source_id="health-1",
        extra_config={"stub_error": "connector", "stub_items": [dict(DEFAULT_ITEM)]},
    )
    sid = uuid.UUID(source["id"])

    failed = _collect(investigator_client, sid, terms=None)
    assert failed["ok"] is False
    assert failed["health"] == "FAILED"
    assert "boom" in (failed["error"] or "")

    h = investigator_client.get(f"/api/v1/osint/sources/{sid}/health").json()
    assert h["consecutive_failures"] == 1
    assert h["last_failure_reason"]

    # operator fixes the configuration, next clean run reports DEGRADED (recovering)
    patched = admin_client.patch(
        f"/api/v1/osint/sources/{sid}", json={"extra_config": {"stub_items": [dict(DEFAULT_ITEM)]}}
    )
    assert patched.status_code == 200, patched.text

    recovering = _collect(investigator_client, sid, terms=None)
    assert recovering["ok"] is True
    assert recovering["health"] == "DEGRADED"
    assert recovering["new_records"] == 1

    stable = _collect(investigator_client, sid, terms=None)
    assert stable["ok"] is True
    assert stable["health"] == "ACTIVE"
    assert stable["duplicates"] == 1  # re-collecting the same story is a dup


@pytest.mark.parametrize(
    "stub_error, expected_health, reason_fragment",
    [
        ("http404", "FAILED", "404"),
        ("http500", "FAILED", "HTTP 500"),
        ("http429", "RATE_LIMITED", "HTTP 429"),
        ("timeout", "FAILED", "timeout"),
        ("badurl", "FAILED", "Invalid source URL"),
        ("malformed", "FAILED", "malformed"),
        ("ratelimit", "RATE_LIMITED", "rate limit"),
    ],
)
def test_upstream_failure_matrix(admin_client, investigator_client, stub_error, expected_health, reason_fragment):
    source = _create(
        admin_client,
        source_id=f"failure-{stub_error}",
        extra_config={
            "stub_error": stub_error,
            "stub_items": [dict(DEFAULT_ITEM)],
        },
    )
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    assert out["ok"] is False
    assert out["health"] == expected_health
    assert reason_fragment in out["error"]
    h = investigator_client.get(f"/api/v1/osint/sources/{uuid.UUID(source['id'])}/health").json()
    assert h["health"] == expected_health
    assert reason_fragment in (h["last_failure_reason"] or "")


def test_disabled_source_collect_reports_disabled(admin_client, investigator_client):
    source = _create(admin_client, source_id="disabled-1", enabled=False)
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    assert out["ok"] is False
    assert out["health"] == "DISABLED"
    assert "disabled" in (out["error"] or "").lower()


def test_rate_limit_per_source(admin_client, investigator_client):
    source = _create(admin_client, source_id="rl-1", rate_limit_per_min=1)
    sid = uuid.UUID(source["id"])

    first = _collect(investigator_client, sid, terms=None)
    assert first["ok"] is True and first["health"] == "ACTIVE"

    second = _collect(investigator_client, sid, terms=None)
    assert second["ok"] is False
    assert second["health"] == "RATE_LIMITED"
    assert "exceeded rate limit" in second["error"]


# ---------------------------------------------------------------------------
# Targeted collection
# ---------------------------------------------------------------------------

def test_targeted_collection_across_enabled_sources(admin_client, investigator_client):
    _create(admin_client, source_id="tgt-a")
    _create(admin_client, source_id="tgt-b")
    disabled = _create(admin_client, source_id="tgt-c", enabled=False)
    sources = investigator_client.get(
        "/api/v1/osint/sources", params={"include_disabled": True}
    ).json()["sources"]
    chosen = [s["id"] for s in sources if s["source_id"] in {"tgt-a", "tgt-b"}]
    assert len(chosen) == 2

    resp = investigator_client.post(
        "/api/v1/osint/collect",
        json={"terms": "doping", "source_ids": chosen},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sources_run"] == 2
    assert all(r["ok"] is True for r in body["results"])
    assert body["results"][0]["new_records"] == 1

    # including a disabled source id must not run it
    resp2 = investigator_client.post(
        "/api/v1/osint/collect",
        json={"terms": "doping", "source_ids": [disabled["id"]]},
    )
    assert resp2.status_code == 200
    assert resp2.json()["sources_run"] == 0


# ---------------------------------------------------------------------------
# Promotion into intelligence with provenance
# ---------------------------------------------------------------------------

def test_promotion_produces_intelligence_report_with_provenance(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    source = _create(admin_client, source_id="promo-1")
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    record_id = out["stored"][0]["id"]

    promoted = investigator_client.post(
        f"/api/v1/osint/records/{record_id}/promote",
        json={"subject_type": "ATHLETE", "subject_id": str(ALICE), "confidence": 0.6},
    )
    assert promoted.status_code == 200, promoted.text
    report_id = promoted.json()["report_id"]

    reports = investigator_client.get(
        "/api/v1/intelligence/reports", params={"subject_id": str(ALICE)}
    ).json()["reports"]
    match = next(r for r in reports if r["id"] == report_id)
    assert match["url"] == DEFAULT_ITEM["source_url"]
    assert match["publisher"] == "wada-ama.org"
    assert match["osint_record_id"] == record_id
    assert match["retrieved_at"] is not None
    assert match["content_hash"]
    assert match["info_category"] == "OSINT"

    audit = db.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "OSINT_PROMOTED",
            AuditEvent.entity_id == report_id,
        )
    )
    assert audit is not None
    import json as _json

    assert _json.loads(audit.metadata_json)["osint_source_id"] == "promo-1"

    # unanchored promotion is allowed (no subject grounding)
    unanchored = investigator_client.post(f"/api/v1/osint/records/{record_id}/promote", json={})
    assert unanchored.status_code == 200, unanchored.text

    # bad subject type -> 422
    bad = investigator_client.post(
        f"/api/v1/osint/records/{record_id}/promote",
        json={"subject_type": "WATERMELON", "subject_id": str(ALICE)},
    )
    assert bad.status_code == 422

    # subject_type without subject_id -> 422
    partial = investigator_client.post(
        f"/api/v1/osint/records/{record_id}/promote", json={"subject_type": "ATHLETE"}
    )
    assert partial.status_code == 422


def test_promote_missing_record_is_404(admin_client):
    resp = admin_client.post(
        f"/api/v1/osint/records/{uuid.uuid4()}/promote", json={}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Claims (§53-§54)
# ---------------------------------------------------------------------------

def test_claims_roundtrip_and_verification(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    source = _create(admin_client, source_id="claim-1")
    out = _collect(investigator_client, uuid.UUID(source["id"]), terms=None)
    record_id = out["stored"][0]["id"]

    created = admin_client.post(
        f"/api/v1/osint/records/{record_id}/claims",
        json={
            "subject_type": "ATHLETE",
            "subject_id": str(ALICE),
            "subject_label": "Test ATH-ALICE",
            "predicate": "under_investigation",
            "object_value": "alleged anti-doping rule violation",
            "confidence": 0.7,
            "notes": "first pass",
        },
    )
    assert created.status_code == 200, created.text
    claim_id = created.json()["id"]
    assert created.json()["verification"] == "UNREVIEWED"
    assert created.json()["record_id"] == record_id

    detail = investigator_client.get(f"/api/v1/osint/records/{record_id}").json()
    assert len(detail["claims"]) == 1
    assert detail["claims"][0]["predicate"] == "under_investigation"

    reviewed = admin_client.patch(
        f"/api/v1/osint/claims/{claim_id}",
        json={"verification": "CORROBORATED", "notes": "second source found", "confidence": 0.85},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["verification"] == "CORROBORATED"
    assert reviewed.json()["reviewed_at"] is not None
    assert reviewed.json()["confidence"] == 0.85

    bad_state = admin_client.patch(
        f"/api/v1/osint/claims/{claim_id}",
        json={"verification": "MAYBE"},
    )
    assert bad_state.status_code == 422

    audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "CLAIM_REVIEWED"))
    assert audit is not None
    import json as _json

    assert _json.loads(audit.metadata_json)["verification"] == "CORROBORATED"


# ---------------------------------------------------------------------------
# Records listing filters
# ---------------------------------------------------------------------------

def test_records_filters_and_pagination(admin_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    mix = [dict(DEFAULT_ITEM)]
    mix.append({
        "title": "Federation athlete sanctions",
        "source_url": "https://federation.example/sanctions",
        "publisher": "federation.example",
        "published_at": "2024-01-10T09:00:00Z",
        "content": "Sanctions issued.",
    })
    source = _create(
        admin_client, source_id="filter-1",
        extra_config={"stub_items": mix},
    )
    _collect(investigator_client, uuid.UUID(source["id"]), terms=None)

    listing = investigator_client.get(
        "/api/v1/osint/records", params={"q": "wada-ama"}
    ).json()
    assert listing["count"] == 1

    by_q = investigator_client.get(
        "/api/v1/osint/records", params={"q": "sanctions"}
    ).json()
    assert by_q["count"] == 1
    assert "sanctions" in by_q["records"][0]["title"].lower()

    by_date = investigator_client.get(
        "/api/v1/osint/records", params={"date_from": "2024-03-01", "date_to": "2024-03-31"}
    ).json()
    assert by_date["count"] == 1

    page = investigator_client.get(
        "/api/v1/osint/records", params={"limit": 1, "offset": 0, "include_duplicates": True}
    ).json()
    assert page["count"] == 2
    assert len(page["records"]) == 1

    detail_missing = investigator_client.get(f"/api/v1/osint/records/{uuid.uuid4()}")
    assert detail_missing.status_code == 404


# ---------------------------------------------------------------------------
# SSRF guidance + service guards
# ---------------------------------------------------------------------------

def test_ssrf_guard_common():
    assert is_public_url("https://www.wada-ama.org/en/rss.xml") is True
    assert is_public_url("ftp://example.com/file") is False
    assert is_public_url("http://") is False
    assert is_public_url("file:///etc/passwd") is False

    for url in (
        "http://127.0.0.1/",
        "http://localhost/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/",
    ):
        with pytest.raises(InvalidSourceUrlError):
            validate_public_host(url)
        with pytest.raises(InvalidSourceUrlError):
            safe_get(url)  # guard raises before any request is made


def test_run_source_collection_missing_connector_maps_to_failed(db, admin_client):
    row = OsintSource(
        source_id="no-connector",
        name="No connector",
        connector_type="does_not_exist",
        url="https://example.com",
        authority="PUBLIC_NEWS",
        rate_limit_per_min=20,
    )
    db.add(row)
    db.commit()
    summary = run_source_collection(db, row, max_records=10)
    assert summary["ok"] is False
    assert summary["health"] == "FAILED"
    assert "No connector registered" in summary["error"]
    db.rollback()


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

def test_osint_rbac(client, viewer_client, investigator_client, analyst_client, admin_client, db):
    # unauthenticated access denied
    assert client.get("/api/v1/osint/sources").status_code == 401
    assert client.get("/api/v1/osint/records").status_code == 401

    # viewer: read only
    assert viewer_client.get("/api/v1/osint/sources").status_code == 200
    assert viewer_client.get("/api/v1/osint/connector-types").status_code == 200
    create_viewer = viewer_client.post("/api/v1/osint/sources", json=_source_body(source_id="v-1"))
    assert create_viewer.status_code == 403

    # analyst manages sources
    source = _create(analyst_client, source_id="rbac-1")
    sid = uuid.UUID(source["id"])

    # investigator cannot create/administer but can collect
    assert (
        investigator_client.post("/api/v1/osint/sources", json=_source_body(source_id="i-1")).status_code
        == 403
    )
    collect_ok = _collect(investigator_client, sid, terms=None)
    assert collect_ok["ok"] is True
    record_id = collect_ok["stored"][0]["id"]

    # viewer cannot collect, promote, or claim
    viewer_collect = viewer_client.post(f"/api/v1/osint/sources/{sid}/collect", json={"terms": None})
    assert viewer_collect.status_code == 403
    assert viewer_client.post(f"/api/v1/osint/records/{record_id}/promote", json={}).status_code == 403
    assert (
        viewer_client.post(f"/api/v1/osint/records/{record_id}/claims", json={
            "predicate": "x", "object_value": "y",
        }).status_code
        == 403
    )
    assert (
        viewer_client.patch(
            f"/api/v1/osint/sources/{sid}", json={"name": "hax"}
        ).status_code
        == 403
    )

    # analyst can claim + review
    claim = analyst_client.post(
        f"/api/v1/osint/records/{record_id}/claims",
        json={"predicate": "under_review", "object_value": "claim by analyst"},
    )
    assert claim.status_code == 200, claim.text
    assert (
        analyst_client.patch(
            f"/api/v1/osint/claims/{claim.json()['id']}", json={"verification": "REVIEWED"}
        ).status_code
        == 200
    )

    # admin-level ops explicitly denied for investigator
    assert (
        investigator_client.delete(f"/api/v1/osint/sources/{sid}").status_code == 403
    )
    assert (
        investigator_client.patch(
            f"/api/v1/osint/sources/{sid}", json={"name": "nope"}
        ).status_code
        == 403
    )


def test_rbac_401_when_token_expired_or_missing(client):
    resp = client.get("/api/v1/osint/sources", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401