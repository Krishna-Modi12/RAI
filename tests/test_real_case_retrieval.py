"""Targeted regression and evaluation suite for Real Historical Case Corpus.

Verifies:
1. Real case provenance and licensing preservation
2. Real vs synthetic separation (no silent merging)
3. Event classification semantics (never confuse operational events with equipment failures)
4. Metadata filtering and asset-type isolation
5. Deterministic trajectory retrieval
6. Why matched, what differed, why may not apply explanations
7. No-match abstention (MIN_SIMILARITY threshold)
8. Environmental contradiction suppression
9. Temporal leakage prevention (knowledge_cutoff)
10. Agent tool integration and API endpoints
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from rai.agent.tools import get_case_details as tool_get_case_details
from rai.agent.tools import search_similar_cases
from rai.config import FLEET
from rai.memory.library import (
    CASE_BY_ID,
    SYNTHETIC_CASES,
    cases_for,
    get_all_cases,
    get_real_cases,
)
from rai.memory.real_corpus import RealEventClass, get_real_case_records
from rai.memory.retrieval import find_similar_cases
from rai.schemas import (
    AnomalyEvidence,
    AssetType,
    DetectorScore,
    EnvironmentEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    HistoricalSourceType,
    PeerEvidence,
    PeerVerdict,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
    SensorHealth,
)
from services.api.main import app

client = TestClient(app)


def _make_wind_packet(
    *,
    gearbox_oil_temp: float = 65.0,
    power_kw: float = 1750.0,
    wind_speed: float = 8.5,
    thermal_z: float = 3.2,
    power_z: float = -1.2,
    persistence_h: float = 48.0,
    env_verdict: EnvironmentVerdict = EnvironmentVerdict.NOT_ENVIRONMENTAL,
    explains_fraction: float = 0.05,
    step_change: bool = False,
) -> EvidencePacket:
    asset = next(a for a in FLEET if a.asset_type.value == "wind_turbine")
    detectors = [DetectorScore(detector="residual_z", score=0.85, fired=True)]
    if step_change:
        detectors.append(DetectorScore(detector="changepoint", score=1.0, fired=True))

    return EvidencePacket(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        generated_at=datetime(2026, 9, 12, tzinfo=UTC),
        health_score=62.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.82,
            persistence_hours=persistence_h,
            detectors=detectors,
            signals=[
                ResidualSignal(
                    name="gearbox_oil_temp_c",
                    unit="C",
                    actual=gearbox_oil_temp,
                    expected=50.0,
                    residual=gearbox_oil_temp - 50.0,
                    z_score=thermal_z,
                ),
                ResidualSignal(
                    name="power_kw",
                    unit="kW",
                    actual=power_kw,
                    expected=1950.0,
                    residual=power_kw - 1950.0,
                    z_score=power_z,
                ),
            ],
        ),
        peers=PeerEvidence(
            peer_group="kutch-wind",
            n_peers=8,
            deviation_percentile=94,
            verdict=PeerVerdict.ASSET_SPECIFIC,
        ),
        environment=EnvironmentEvidence(
            source="site_met",
            sensor_health=SensorHealth.OK,
            explains_fraction=explains_fraction,
            verdict=env_verdict,
        ),
        risk=RiskAssessment(risk_score=0.72, risk_band=RiskBand.HIGH),
    )


def _make_solar_packet(
    *,
    poa_wm2: float = 850.0,
    ac_power_kw: float = 0.0,
    power_z: float = -4.0,
    persistence_h: float = 3.0,
) -> EvidencePacket:
    asset = next(a for a in FLEET if a.asset_type.value == "solar_inverter")
    return EvidencePacket(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        generated_at=datetime(2026, 9, 12, tzinfo=UTC),
        health_score=50.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.85,
            persistence_hours=persistence_h,
            detectors=[
                DetectorScore(detector="residual_z", score=0.9, fired=True),
                DetectorScore(detector="changepoint", score=1.0, fired=True),
            ],
            signals=[
                ResidualSignal(
                    name="ac_power_kw",
                    unit="kW",
                    actual=ac_power_kw,
                    expected=180.0,
                    residual=-180.0,
                    z_score=power_z,
                )
            ],
        ),
        peers=PeerEvidence(
            peer_group="charanka-solar",
            n_peers=12,
            deviation_percentile=98,
            verdict=PeerVerdict.ASSET_SPECIFIC,
        ),
        environment=EnvironmentEvidence(
            source="site_met",
            sensor_health=SensorHealth.OK,
            explains_fraction=0.02,
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
        ),
        risk=RiskAssessment(risk_score=0.78, risk_band=RiskBand.HIGH),
    )


# ---------------------------------------------------------------------------
# 1. Provenance and Licensing Preservation
# ---------------------------------------------------------------------------


def test_real_corpus_provenance_and_licensing() -> None:
    records = get_real_case_records()
    assert len(records) == 14

    for rec in records:
        assert rec.case_id.startswith("REAL-")
        assert rec.source_dataset in {
            "CARE to Compare — Wind Farm A",
            "CARE to Compare — Wind Farm B",
            "CARE to Compare — Wind Farm C",
            "Kelmarsh Wind Farm 2019",
            "NREL PVDAQ OEDI — System 34",
            "NREL PVDAQ OEDI — System 1283",
        }
        assert rec.license in {"CC-BY-SA-4.0", "CC-BY-4.0", "Public Domain / NREL OEDI"}
        assert len(rec.source_reference) > 10
        assert len(rec.limitations) >= 1

        # Adjudication audit completeness
        adj = rec.adjudication
        assert len(adj.what_is_explicitly_known) > 15
        assert len(adj.what_is_inferred) > 10
        assert len(adj.what_remains_unknown) > 10
        assert len(adj.what_source_proves) > 15
        assert len(adj.what_source_does_not_prove) > 15


# ---------------------------------------------------------------------------
# 2. Strict Real vs Synthetic Demarcation
# ---------------------------------------------------------------------------


def test_real_synthetic_separation() -> None:
    real_cases = get_real_cases()
    synth_cases = SYNTHETIC_CASES
    all_cases = get_all_cases()

    # At least the 14 curated academic cases, plus any verified operator field feedback cases
    assert len(real_cases) >= 14
    assert len(synth_cases) == 14
    assert len(all_cases) >= 28

    real_ids = {c.case_id for c in real_cases}
    synth_ids = {c.case_id for c in synth_cases}

    # Zero ID collision
    assert len(real_ids & synth_ids) == 0

    # Source type integrity
    for c in real_cases:
        assert c.source_type == HistoricalSourceType.EXTERNAL_REAL
    for c in synth_cases:
        assert c.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC

    # Partition filtering
    wind_real = cases_for("wind_turbine", partition="real")
    wind_synth = cases_for("wind_turbine", partition="synthetic")
    wind_all = cases_for("wind_turbine", partition="all")

    assert len(wind_real) >= 12
    assert len(wind_synth) == 8
    assert len(wind_all) >= 20
    assert all(c.source_type == HistoricalSourceType.EXTERNAL_REAL for c in wind_real)
    assert all(c.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC for c in wind_synth)


# ---------------------------------------------------------------------------
# 3. Eligibility Taxonomy (Never confuse operational events with failure)
# ---------------------------------------------------------------------------


def test_event_classification_semantics() -> None:
    records = {r.case_id: r for r in get_real_case_records()}

    # Verified equipment failure records
    verified_ids = [
        "REAL-CARE-A-072",  # Gearbox failure
        "REAL-CARE-A-000",  # Generator bearing
        "REAL-CARE-A-068",  # Transformer failure
        "REAL-CARE-A-022",  # Hydraulic group
        "REAL-CARE-B-053",  # Rotor bearing damage
        "REAL-CARE-C-081",  # Converter fuse
    ]
    for cid in verified_ids:
        rec = records[cid]
        case = rec.to_case()
        assert rec.event_class == RealEventClass.REAL_VERIFIED_EVENT
        assert case.equipment_fault is True

    # Operational events: MUST NOT be converted to equipment failures
    operational_ids = [
        "REAL-KEL-1-FORCED-3000",  # Frequency converter unready (4-min reset)
        "REAL-KEL-1-FORCED-2550",  # Generator fan thermal protection trip
        "REAL-PVDAQ-034-OUTAGE",   # Inverter trip / grid disconnection
        "REAL-CARE-A-025-NORM",    # Healthy normal baseline
    ]
    for cid in operational_ids:
        rec = records[cid]
        case = rec.to_case()
        assert rec.event_class == RealEventClass.REAL_OPERATIONAL_EVENT
        assert case.equipment_fault is False, f"{cid} operational event converted to equipment fault!"
        assert any(
            phrase in " ".join(rec.limitations).lower()
            for phrase in (
                "not a component failure",
                "not component failure",
                "operational_event",
                "no permanent hardware damage",
                "protection trip only",
            )
        ) or "baseline" in rec.fault_mode.lower()

    # Maintenance events
    maint_ids = [
        "REAL-KEL-1-MAINT-0020",  # Scheduled on-site maintenance (Code 20)
        "REAL-CARE-C-044",        # Post-maintenance cooling valve error
    ]
    for cid in maint_ids:
        rec = records[cid]
        case = rec.to_case()
        assert rec.event_class == RealEventClass.REAL_MAINTENANCE_EVENT
        assert case.equipment_fault is False, f"{cid} maintenance event converted to equipment fault!"

    # Environmental events
    env_ids = [
        "REAL-KEL-1-ENV-0010",        # Low wind calm (Code 10)
        "REAL-PVDAQ-1283-CLIPPING",   # Inverter power saturation / clipping
    ]
    for cid in env_ids:
        rec = records[cid]
        case = rec.to_case()
        assert rec.event_class == RealEventClass.ENVIRONMENTAL_EVENT
        assert case.equipment_fault is False, f"{cid} environmental event converted to equipment fault!"


# ---------------------------------------------------------------------------
# 4. Metadata Filtering and Asset Type Isolation
# ---------------------------------------------------------------------------


def test_asset_type_isolation() -> None:
    wind_packet = _make_wind_packet()
    solar_packet = _make_solar_packet()

    retrieved_wind = find_similar_cases(wind_packet, k=10, corpus_partition="real")
    assert retrieved_wind
    for c in retrieved_wind:
        assert c.asset_type == AssetType.WIND_TURBINE

    retrieved_solar = find_similar_cases(solar_packet, k=10, corpus_partition="real")
    assert retrieved_solar
    for c in retrieved_solar:
        assert c.asset_type == AssetType.SOLAR_INVERTER


# ---------------------------------------------------------------------------
# 5. Deterministic Real Trajectory Retrieval
# ---------------------------------------------------------------------------


def test_deterministic_real_case_retrieval() -> None:
    # Gearbox thermal runaway packet
    gb_packet = _make_wind_packet(
        gearbox_oil_temp=68.0,
        thermal_z=3.5,
        power_z=-1.5,
        persistence_h=72.0,
    )
    cases = find_similar_cases(gb_packet, k=3, corpus_partition="real")
    assert cases
    top = cases[0]
    assert top.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert top.component in ("gearbox", "generator")
    assert top.similarity >= 0.70

    # Solar midday zero generation packet
    solar_packet = _make_solar_packet(poa_wm2=850.0, ac_power_kw=0.0, power_z=-4.2)
    solar_cases = find_similar_cases(solar_packet, k=3, corpus_partition="real")
    assert solar_cases
    top_solar = solar_cases[0]
    assert top_solar.case_id == "REAL-PVDAQ-034-OUTAGE"
    assert top_solar.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert top_solar.event_class == "REAL_OPERATIONAL_EVENT"


# ---------------------------------------------------------------------------
# 6. Explanation and Disclaimers
# ---------------------------------------------------------------------------


def test_retrieval_explanation_and_disclaimers() -> None:
    packet = _make_wind_packet()
    cases = find_similar_cases(packet, k=2, corpus_partition="real")
    assert cases
    case = cases[0]

    # Explanation fields
    assert len(case.why_matched) >= 2
    assert isinstance(case.what_is_similar, list)
    assert isinstance(case.what_is_different, list)
    assert len(case.why_may_not_apply) >= 2

    # Verification that real cases do not claim to be synthetic scenarios
    combined_why_not = " ".join(case.why_may_not_apply)
    assert "internally authored synthetic case" not in combined_why_not
    assert "not proof of current diagnosis" in combined_why_not
    assert case.source_reference is not None
    assert case.adjudication != {}


# ---------------------------------------------------------------------------
# 7. No-Match Abstention
# ---------------------------------------------------------------------------


def test_no_match_abstention() -> None:
    # Create an artificial packet with extreme contradictory signals that match no known real case
    asset = next(a for a in FLEET if a.asset_type.value == "wind_turbine")
    outlier_packet = EvidencePacket(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        generated_at=datetime(2026, 9, 12, tzinfo=UTC),
        health_score=95.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.01,
            persistence_hours=0.0,
            detectors=[],
            signals=[
                ResidualSignal(
                    name="power_kw",
                    unit="kW",
                    actual=2050.0,
                    expected=2050.0,
                    residual=0.0,
                    z_score=0.0,
                )
            ],
        ),
        environment=EnvironmentEvidence(
            source="site_met",
            sensor_health=SensorHealth.OK,
            explains_fraction=1.0,
            verdict=EnvironmentVerdict.ENVIRONMENTAL,
        ),
        risk=RiskAssessment(risk_score=0.05, risk_band=RiskBand.LOW),
    )

    # All real failure cases have substantial anomalies; low-anomaly queries should abstain
    # or return only non-fault cases above MIN_SIMILARITY
    cases = find_similar_cases(outlier_packet, k=5, corpus_partition="real")
    for c in cases:
        # If any case is returned, it must not be a verified equipment failure
        assert c.event_class != RealEventClass.REAL_VERIFIED_EVENT.value or c.similarity < 0.5


# ---------------------------------------------------------------------------
# 8. Environmental Contradiction Suppression
# ---------------------------------------------------------------------------


def test_environmental_contradiction_suppression() -> None:
    # Case with equipment-like thermal residual, but environment layer confirms environmental cause
    contra_packet = _make_wind_packet(
        gearbox_oil_temp=75.0,
        thermal_z=3.8,
        env_verdict=EnvironmentVerdict.ENVIRONMENTAL,
        explains_fraction=0.95,
    )
    cases = find_similar_cases(contra_packet, k=5, corpus_partition="real")
    for c in cases:
        if c.event_type == "REAL_VERIFIED_EVENT":
            # Must carry explicit contradiction warning in why_may_not_apply
            assert any("Current environmental evidence conflicts" in w for w in c.why_may_not_apply)


# ---------------------------------------------------------------------------
# 9. Temporal Leakage Prevention
# ---------------------------------------------------------------------------


def test_temporal_leakage_cutoff() -> None:
    packet = _make_wind_packet()
    # Set knowledge cutoff to 2018-01-01 UTC
    cutoff = "2018-01-01T00:00:00Z"
    cases = find_similar_cases(packet, k=10, knowledge_cutoff=cutoff, corpus_partition="real")

    # Cases from 2019, 2021, 2022, 2023 must be excluded!
    for c in cases:
        case_obj = CASE_BY_ID.get(c.case_id)
        if case_obj and case_obj.closed_at:
            assert case_obj.closed_at <= cutoff


# ---------------------------------------------------------------------------
# 10. Agent Tool and API Integration
# ---------------------------------------------------------------------------


def test_agent_tool_retrieval_integration() -> None:
    asset = next(a for a in FLEET if a.asset_type.value == "wind_turbine")
    res = search_similar_cases(asset.asset_id, k=3, corpus_partition="real")
    assert res["count"] > 0
    assert res["corpus_partition"] == "real"
    for c in res["cases"]:
        assert c["source_type"] == "EXTERNAL_REAL"
        assert c["source_dataset"] is not None
        assert c["event_class"] is not None

    # Test single case detail retrieval
    detail_res = tool_get_case_details("REAL-CARE-A-072")
    assert detail_res["status"] == "RETRIEVED"
    case_data = detail_res["case"]
    assert case_data["case_id"] == "REAL-CARE-A-072"
    assert case_data["source_type"] == "EXTERNAL_REAL"
    assert case_data["adjudication"]["what_source_proves"] is not None


def test_api_historical_cases_endpoints() -> None:
    # Test GET /api/assets/historical-corpus/info
    info_resp = client.get("/api/assets/historical-corpus/info")
    assert info_resp.status_code == 200
    info = info_resp.json()
    assert info["synthetic_case_count"] == 14
    assert info["real_case_count"] >= 14
    assert info["total_cases"] >= 28
    assert len(info["sources"]["real"]) >= 3

    # Test GET /api/assets/historical-cases/{case_id}
    case_resp = client.get("/api/assets/historical-cases/REAL-CARE-A-072")
    assert case_resp.status_code == 200
    case_json = case_resp.json()
    assert case_json["case_id"] == "REAL-CARE-A-072"
    assert case_json["source_type"] == "EXTERNAL_REAL"
    assert case_json["adjudication"]["what_is_explicitly_known"] is not None

    # Test 404 for unknown case
    missing_resp = client.get("/api/assets/historical-cases/NONEXISTENT-CASE")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["code"] == "case_not_found"

    # Test GET /api/assets/{asset_id}/cases with partition query
    asset = next(a for a in FLEET if a.asset_type.value == "wind_turbine")
    cases_resp = client.get(f"/api/assets/{asset.asset_id}/cases?partition=real&k=4")
    assert cases_resp.status_code == 200
    retrieved = cases_resp.json()
    assert len(retrieved) > 0
    for c in retrieved:
        assert c["source_type"] == "EXTERNAL_REAL"
