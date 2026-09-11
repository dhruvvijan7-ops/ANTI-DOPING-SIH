"""Graph gate (§100-112) backend integration tests.

Covers: node creation, role assignment, relationship edit/delete,
provenance, filters, position persistence, and graph safety.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from tests.support_domain import ALICE, BOB, seed_domain


def _create_case(client) -> str:
    resp = client.post(
        "/api/v1/investigations",
        json={
            "title": "Graph gate test",
            "subject_type": "ATHLETE",
            "subject_id": str(ALICE),
                "priority": "MODERATE",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# §107 Node creation
# ---------------------------------------------------------------------------

class TestNodeCreation:
    def test_create_athlete_node(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "ATHLETE",
            "name": "Test Athlete",
            "external_ref": "ATH-TEST-NODE-1",
            "graph_role": "ATHLETE",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["entity_type"] == "ATHLETE"
        assert data["name"] == "Test Athlete"
        assert data["graph_role"] == "ATHLETE"
        assert data["verification"] == "UNVERIFIED"

    def test_create_team_node(self, analyst_client, db: Session):
        resp = analyst_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "TEAM",
            "name": "Test FC",
            "country": "CHE",
            "graph_role": "TEAM",
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["entity_type"] == "TEAM"

    def test_create_event_node(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "EVENT",
            "name": "World Championships 2025",
            "event_type": "COMPETITION",
            "location": "Zurich",
            "start_date": "2025-09-01",
            "end_date": "2025-09-07",
            "graph_role": "EVENT",
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["entity_type"] == "EVENT"

    def test_create_competition_node(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "COMPETITION",
            "name": "National Cycling Cup",
            "sport": "CYCLING",
            "level": "NATIONAL",
            "graph_role": "EVENT",
        })
        assert resp.status_code == 200, resp.text

    def test_create_location_node(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "LOCATION",
            "name": "Zurich Training Center",
            "country": "CHE",
            "city": "Zurich",
            "graph_role": "LOCATION",
        })
        assert resp.status_code == 200, resp.text

    def test_create_source_node(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "SOURCE",
            "name": "Anonymous Whistleblower",
            "source_type": "CONFIDENTIAL",
            "reliability": "B",
            "graph_role": "SOURCE",
        })
        assert resp.status_code == 200, resp.text

    def test_create_node_invalid_type(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "ALIEN",
            "name": "Not valid",
        })
        assert resp.status_code == 422

    def test_create_node_empty_name(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "TEAM",
            "name": "",
        })
        assert resp.status_code == 422

    def test_create_node_invalid_role(self, investigator_client, db: Session):
        resp = investigator_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "TEAM",
            "name": "Bad Role Team",
            "graph_role": "ALIEN",
        })
        assert resp.status_code == 422

    def test_readonly_user_cannot_create_node(self, viewer_client, db: Session):
        resp = viewer_client.post("/api/v1/relationships/nodes", json={
            "entity_type": "TEAM",
            "name": "Viewer Team",
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# §100 Role vocabulary
# ---------------------------------------------------------------------------

class TestRoleVocabulary:
    def test_roles_endpoint(self, investigator_client, db: Session):
        resp = investigator_client.get("/api/v1/relationships/roles")
        assert resp.status_code == 200
        data = resp.json()
        assert "ATHLETE" in data["roles"]
        assert "COACH" in data["roles"]
        assert "TRAINER" in data["roles"]
        assert data["count"] >= 10


# ---------------------------------------------------------------------------
# §108 Relationship edit (PATCH)
# ---------------------------------------------------------------------------

class TestRelationshipEdit:
    def test_edit_relationship_confidence(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        # create a relationship via POST
        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TESTING_PARTNER",
            "confidence": 0.5,
        })
        assert create_resp.status_code == 200, create_resp.text
        rel_id = create_resp.json()["id"]

        # PATCH
        patch_resp = investigator_client.patch(f"/api/v1/relationships/{rel_id}", json={
            "confidence": 0.95,
            "notes": "Updated with corroborating evidence",
            "frequency": "WEEKLY",
        })
        assert patch_resp.status_code == 200, patch_resp.text
        patched = patch_resp.json()
        assert patched["confidence"] == 0.95
        assert patched["notes"] == "Updated with corroborating evidence"
        assert patched["frequency"] == "WEEKLY"

    def test_edit_relationship_type(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "OLD_TYPE",
        })
        rel_id = create_resp.json()["id"]
        patch_resp = investigator_client.patch(f"/api/v1/relationships/{rel_id}", json={
            "relationship_type": "NEW_TYPE",
        })
        assert patch_resp.status_code == 200
        assert patch_resp.json()["relationship_type"] == "NEW_TYPE"

    def test_edit_nonexistent_returns_404(self, investigator_client, db: Session):
        fake_id = str(uuid.uuid4())
        resp = investigator_client.patch(f"/api/v1/relationships/{fake_id}", json={
            "confidence": 0.5,
        })
        assert resp.status_code == 404

    def test_edit_deleted_returns_404(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TO_DELETE",
        })
        rel_id = create_resp.json()["id"]
        del_resp = investigator_client.delete(f"/api/v1/relationships/{rel_id}")
        assert del_resp.status_code == 200

        patch_resp = investigator_client.patch(f"/api/v1/relationships/{rel_id}", json={
            "confidence": 0.99,
        })
        assert patch_resp.status_code == 404

    def test_edit_confidence_out_of_range(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "RANGE_TEST",
            "confidence": 0.5,
        })
        rel_id = create_resp.json()["id"]
        patch_resp = investigator_client.patch(f"/api/v1/relationships/{rel_id}", json={
            "confidence": 1.5,
        })
        assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# §105 Soft delete
# ---------------------------------------------------------------------------

class TestRelationshipDelete:
    def test_soft_delete_relationship(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "SOFT_DEL_TEST",
        })
        rel_id = create_resp.json()["id"]

        del_resp = investigator_client.delete(f"/api/v1/relationships/{rel_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "DELETED"

        # Detail returns 404
        detail_resp = investigator_client.get(f"/api/v1/relationships/{rel_id}")
        assert detail_resp.status_code == 404

        # List excludes it by default
        list_resp = investigator_client.get("/api/v1/relationships")
        ids = [r["id"] for r in list_resp.json()["relationships"]]
        assert rel_id not in ids

        # List includes when include_deleted=True
        list_all = investigator_client.get("/api/v1/relationships?include_deleted=true")
        ids_all = [r["id"] for r in list_all.json()["relationships"]]
        assert rel_id in ids_all

    def test_delete_nonexistent_returns_404(self, investigator_client, db: Session):
        resp = investigator_client.delete(f"/api/v1/relationships/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_readonly_cannot_delete(self, viewer_client, db: Session):
        seed_domain(db)
        db.commit()
        create_resp = viewer_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "NO_DEL",
        })
        assert create_resp.status_code == 403


# ---------------------------------------------------------------------------
# §103 Provenance
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_detail_includes_source_and_audit(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        from tests.support_domain import _source
        src = _source(db, "Test Provenance Source", "OSINT", "B")
        db.commit()

        create_resp = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "PROVENANCE_TEST",
            "source_id": str(src.id),
            "notes": "Source-backed edge",
        })
        assert create_resp.status_code == 200
        rel_id = create_resp.json()["id"]

        detail = investigator_client.get(f"/api/v1/relationships/{rel_id}").json()
        assert detail["provenance"]["source"] is not None
        assert detail["provenance"]["source"]["name"] == "Test Provenance Source"
        assert detail["provenance"]["created_by_actor"] is not None
        assert detail["notes"] == "Source-backed edge"


# ---------------------------------------------------------------------------
# §426 Graph filters
# ---------------------------------------------------------------------------

class TestGraphFilters:
    def test_filter_by_verification(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        r1 = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "FILTER_TEST",
            "verification": "VERIFIED",
        })
        r2 = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "FILTER_TEST2",
            "verification": "UNVERIFIED",
        })

        resp = investigator_client.get("/api/v1/relationships?verification=VERIFIED")
        data = resp.json()
        ids = [r["id"] for r in data["relationships"]]
        assert r1.json()["id"] in ids
        assert r2.json()["id"] not in ids

    def test_filter_by_confidence_min(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        r1 = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "CONF_TEST",
            "confidence": 0.9,
        })
        investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "CONF_TEST2",
            "confidence": 0.3,
        })

        resp = investigator_client.get("/api/v1/relationships?confidence_min=0.8")
        ids = [r["id"] for r in resp.json()["relationships"]]
        assert r1.json()["id"] in ids

    def test_filter_by_rel_type(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        r1 = investigator_client.post("/api/v1/relationships", json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "UNIQUE_TYPE_XYZ",
        })

        resp = investigator_client.get("/api/v1/relationships?relationship_type=UNIQUE_TYPE_XYZ")
        assert resp.json()["count"] >= 1
        ids = [r["id"] for r in resp.json()["relationships"]]
        assert r1.json()["id"] in ids


# ---------------------------------------------------------------------------
# §553 Node position persistence
# ---------------------------------------------------------------------------

class TestNodePositions:
    def test_persist_and_read_positions(self, investigator_client, db: Session):
        seed_domain(db)
        db.commit()
        resp = investigator_client.patch(
            f"/api/v1/relationships/nodes/ATHLETE/{ALICE}/position",
            json={"x": 100.0, "y": 200.0},
        )
        assert resp.status_code == 200
        assert resp.json()["x"] == 100.0
        assert resp.json()["y"] == 200.0

        # Read back
        features = investigator_client.get("/api/v1/relationships/nodes/features").json()
        alice_feat = [f for f in features["features"] if f["entity_id"] == str(ALICE)]
        assert len(alice_feat) == 1
        assert alice_feat[0]["position_x"] == 100.0
        assert alice_feat[0]["position_y"] == 200.0


# ---------------------------------------------------------------------------
# §110 Graph safety (no invented relationships)
# ---------------------------------------------------------------------------

class TestGraphSafety:
    def test_graph_does_not_invent_relationships(self, investigator_client, db: Session):
        """The case graph should only contain explicitly stored edges."""
        seed_domain(db)
        db.commit()
        inv_id = _create_case(investigator_client)

        graph = investigator_client.get(f"/api/v1/investigations/{inv_id}/relationships").json()

        # No relationships exist between ALICE and entities outside seed_domain
        edge_targets = {e["target"] for e in graph["edges"]}
        # All edges must reference the subject (ALICE)
        for edge in graph["edges"]:
            assert edge["source"] == f"ATHLETE:{ALICE}" or edge["target"] == f"ATHLETE:{ALICE}"

    def test_node_feature_validation(self, investigator_client, db: Session):
        resp = investigator_client.patch(
            f"/api/v1/relationships/nodes/ATHLETE/{ALICE}",
            json={"graph_role": "INVALID_ROLE"},
        )
        assert resp.status_code == 422

    def test_node_feature_update_role(self, investigator_client, db: Session):
        resp = investigator_client.patch(
            f"/api/v1/relationships/nodes/ATHLETE/{ALICE}",
            json={"graph_role": "COACH", "verification": "REVIEWED"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["graph_role"] == "COACH"
        assert data["verification"] == "REVIEWED"
