"""Test suite validating FastAPI backend endpoints against docs/API_CONTRACT.md."""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_api_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "data_as_of" in data
    assert "needle_available" in data
    assert "models_loaded" in data
    assert data["assets"] == 42


def test_api_fleet():
    resp = client.get("/api/fleet")
    assert resp.status_code == 200
    data = resp.json()
    assert "fleet_health" in data
    assert "expected_yield_pct" in data
    assert data["assets_total"] == 42
    assert "generation_kw" in data
    assert "expected_generation_kw" in data
    assert "revenue_at_risk_inr_per_day" in data
    assert len(data["by_type"]) == 2
    types = {t["asset_type"] for t in data["by_type"]}
    assert "wind_turbine" in types
    assert "solar_inverter" in types


def test_api_fleet_priority():
    resp = client.get("/api/fleet/priority")
    assert resp.status_code == 200
    queue = resp.json()
    assert isinstance(queue, list)
    if queue:
        item = queue[0]
        assert "asset_id" in item
        assert "headline" in item
        assert "risk_score" in item
        assert "recommended_action" in item
        assert "revenue_at_risk_inr" in item


def test_api_assets_list():
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    assets = resp.json()
    assert len(assets) == 42
    sample = assets[0]
    for key in ("asset_id", "name", "asset_type", "site", "health_score", "risk_score", "power_kw"):
        assert key in sample


def test_api_asset_detail_wind():
    resp = client.get("/api/assets/WT-017")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset"]["asset_id"] == "WT-017"
    assert data["asset"]["asset_type"] == "wind_turbine"
    assert "state" in data
    assert "risk" in data
    assert "anomaly" in data
    assert "peers" in data
    assert "environment" in data
    assert data["soiling"] is None


def test_api_asset_detail_solar():
    resp = client.get("/api/assets/INV-023")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset"]["asset_id"] == "INV-023"
    assert data["asset"]["asset_type"] == "solar_inverter"
    assert data["soiling"] is not None
    assert "soiling_ratio" in data["soiling"]
    assert "soiling_loss_pct" in data["soiling"]


def test_api_asset_not_found():
    resp = client.get("/api/assets/WT-999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "asset_not_found"
    assert "unknown asset_id 'WT-999'" in data["detail"]


def test_api_asset_timeseries():
    resp = client.get("/api/assets/WT-017/timeseries?signal=power_kw&hours=48")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "WT-017"
    assert data["signal"] == "power_kw"
    assert "points" in data
    assert "events" in data


def test_api_asset_peers():
    resp = client.get("/api/assets/WT-017/peers")
    assert resp.status_code == 200
    data = resp.json()
    assert "peer_group" in data
    assert "assets" in data
    assert any(a["is_subject"] for a in data["assets"])


def test_api_asset_investigate():
    resp = client.post("/api/assets/WT-017/investigate", json={"force_refresh": False})
    assert resp.status_code == 200
    data = resp.json()
    assert "investigation_id" in data
    assert data["asset_id"] == "WT-017"
    assert "verdict" in data
    assert "timeline" in data
    assert len(data["timeline"]) > 0
    assert "historical_cases" in data
    assert "citations" in data
    assert "economics" in data


def test_api_asset_cases():
    resp = client.get("/api/assets/WT-017/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)


def test_api_asset_economics():
    resp = client.get("/api/assets/WT-017/economics")
    assert resp.status_code == 200
    econ = resp.json()
    assert "options" in econ
    assert "recommended_option_id" in econ
    assert "avoidable_exposure_inr" in econ


def test_api_soiling():
    resp = client.get("/api/soiling")
    assert resp.status_code == 200
    data = resp.json()
    assert data["site"] == "Charanka Solar Park"
    assert "site_soiling_loss_pct" in data
    assert "dust_risk" in data
    assert "recommendation" in data
    assert "zones" in data
    assert len(data["zones"]) >= 2


def test_api_knowledge_search():
    resp = client.get("/api/knowledge/search?q=gearbox+bearing")
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "results" in data
    assert len(data["results"]) > 0


def test_api_knowledge_docs():
    resp = client.get("/api/knowledge/docs")
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 19
    assert all("doc_id" in d and "sections" in d for d in docs)


def test_api_simulator_scenarios():
    resp = client.get("/api/simulator/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()
    assert len(scenarios) == 12
    names = {s["scenario"] for s in scenarios}
    assert "gearbox_bearing_wear" in names
    assert "cloud_transient" in names
    assert "curtailment_window" in names


def test_api_simulator_inject():
    resp = client.post(
        "/api/simulator/inject",
        json={
            "asset_id": "WT-017",
            "scenario": "gearbox_bearing_wear",
            "severity": 0.7,
            "acceleration": 60,
            "duration_days": 14,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "WT-017"
    assert data["scenario"] == "gearbox_bearing_wear"
    assert "run_id" in data
    assert "ground_truth" in data


def test_api_simulator_reset():
    resp = client.post("/api/simulator/reset", json={"asset_id": "WT-017"})
    assert resp.status_code == 200
    assert resp.json()["reset"] == ["WT-017"]


def test_api_evaluation():
    resp = client.get("/api/evaluation")
    assert resp.status_code == 200
    data = resp.json()
    assert "computed_at" in data
    assert "dataset" in data
    assert "split" in data
    assert "champion_model" in data
    assert data["champion_model"]["care_score"] > 0.60
    assert data["champion_model"]["pr_auc"] > 0.75
    assert "alert_fatigue_funnel" in data
    assert "decision_regret" in data
    assert "track_b_external_benchmark" in data
