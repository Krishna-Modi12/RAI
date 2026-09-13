"""Test suite for standard health probes and work order REST API endpoints."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_liveness_probe():
    # Root-level Kubernetes probe
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"

    # API-level probe
    resp2 = client.get("/api/healthz")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "alive"


def test_readiness_probe():
    # Root-level Kubernetes probe
    resp = client.get("/readyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "telemetry_store" in data["checks"]
    assert data["checks"]["telemetry_store"]["status"] == "ok"
    assert "reasoner" in data["checks"]
    assert "fleet" in data["checks"]
    assert data["checks"]["fleet"]["assets_configured"] == 42
    assert "work_orders" in data["checks"]

    # API-level probe
    resp2 = client.get("/api/readyz")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ready"


def test_work_order_api_rest_endpoints():
    # 1. Propose
    prop_resp = client.post(
        "/api/work-orders/propose",
        json={
            "asset_id": "WT-006",
            "component": "transformer",
            "action": "Check transformer oil level and DGA gas samples",
            "deadline_hours": 72,
            "priority": "medium",
            "created_by": "api_test",
        },
    )
    assert prop_resp.status_code == 201
    ticket = prop_resp.json()
    tid = ticket["ticket_id"]
    assert ticket["status"] == "proposed_awaiting_human_approval"

    # 2. Get single
    get_resp = client.get(f"/api/work-orders/{tid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["ticket_id"] == tid

    # 3. Approve
    act_resp = client.post(
        f"/api/work-orders/{tid}/action",
        json={
            "action": "approve",
            "actor": "site_engineer_joshi",
            "deadline_hours": 48,
            "priority": "high",
        },
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "approved_scheduled"
    assert act_resp.json()["approved_by"] == "site_engineer_joshi"

    # 4. Feedback
    fb_resp = client.post(
        f"/api/work-orders/{tid}/feedback",
        json={
            "technician_id": "oil_lab_tech",
            "resolution": "no_fault_found",
            "findings": "DGA analysis nominal: acetylene and hydrogen below IEEE limits.",
            "component_inspected": "stepup_transformer",
            "actual_downtime_hours": 0.5,
            "actual_parts_cost_inr": 12000.0,
            "notes": "Annual sample archived.",
        },
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["status"] == "completed"
    assert len(fb_resp.json()["feedback"]) >= 1

    # 5. List with filters
    list_resp = client.get("/api/work-orders?asset_id=WT-006")
    assert list_resp.status_code == 200
    assert any(w["ticket_id"] == tid for w in list_resp.json())


def test_work_order_api_errors():
    # Unknown ticket 404
    resp = client.get("/api/work-orders/TCK-NONEXISTENT")
    assert resp.status_code == 404

    # Invalid action 400
    resp2 = client.post(
        "/api/work-orders/TCK-NONEXISTENT/action",
        json={"action": "invalid_verb", "actor": "nobody"},
    )
    assert resp2.status_code == 400

    # Reject without reason 400
    prop_resp = client.post(
        "/api/work-orders/propose",
        json={
            "asset_id": "WT-007",
            "component": "converter",
            "action": "Check IGBT gate firing",
            "deadline_hours": 72,
        },
    )
    tid = prop_resp.json()["ticket_id"]
    rej_resp = client.post(
        f"/api/work-orders/{tid}/action",
        json={"action": "reject", "actor": "supervisor"},
    )
    assert rej_resp.status_code == 400
