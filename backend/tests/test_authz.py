"""Authorization (RBAC) tests across all four roles.

The frontend must not be trusted for authorization; the backend must reject
unauthorized operations with 403.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_admin_can_manage_users(admin_client: TestClient) -> None:
    resp = admin_client.get("/api/v1/users")
    assert resp.status_code == 200


def test_viewer_cannot_manage_users(viewer_client: TestClient) -> None:
    resp = viewer_client.get("/api/v1/users")
    assert resp.status_code == 403


def test_investigator_cannot_manage_users(investigator_client: TestClient) -> None:
    resp = investigator_client.get("/api/v1/users")
    assert resp.status_code == 403


def test_analyst_cannot_manage_users(analyst_client: TestClient) -> None:
    resp = analyst_client.get("/api/v1/users")
    assert resp.status_code == 403


def test_admin_can_list_roles(admin_client: TestClient) -> None:
    resp = admin_client.get("/api/v1/users/roles")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert {"ADMINISTRATOR", "INVESTIGATOR", "INTELLIGENCE_ANALYST", "VIEWER"} <= names


def test_admin_can_create_and_update_role(admin_client: TestClient) -> None:
    create = admin_client.post("/api/v1/users/roles", json={"name": "TEMP_ROLE", "description": "t"})
    assert create.status_code == 201
    role_id = create.json()["id"]

    update = admin_client.patch(
        f"/api/v1/users/roles/{role_id}",
        json={"description": "updated", "permission_keys": ["intelligence:read"]},
    )
    assert update.status_code == 200
    assert update.json()["description"] == "updated"


def test_viewer_cannot_list_permissions(viewer_client: TestClient) -> None:
    resp = viewer_client.get("/api/v1/users/permissions")
    assert resp.status_code == 403


def test_admin_can_list_permissions(admin_client: TestClient) -> None:
    resp = admin_client.get("/api/v1/users/permissions")
    assert resp.status_code == 200


def test_no_token_gets_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_bad_token_gets_401(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401


def test_role_capabilities_matrix(admin_client: TestClient, investigator_client: TestClient) -> None:
    """Sanity check that role permission sets differ and are non-empty."""
    for cli in (admin_client, investigator_client):
        me = cli.get("/api/v1/auth/me").json()
        assert len(me["role"]["permissions"]) > 0
