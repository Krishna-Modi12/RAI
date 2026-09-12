"""Tests for economics engine and historical case memory retrieval."""

from datetime import UTC, datetime

from rai.config import FLEET
from rai.economics.engine import (
    component_cost_table,
    do_nothing_exposure,
    evaluate_cleaning_options,
    evaluate_options,
    settings_snapshot,
)
from rai.memory.library import CASES, cases_for
from rai.memory.retrieval import find_similar_cases, signature_from_packet
from rai.schemas import (
    AnomalyEvidence,
    DetectorScore,
    EnvironmentEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    OperatingState,
    PeerEvidence,
    PeerVerdict,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
    SensorHealth,
)


def test_economics_settings_snapshot():
    snap = settings_snapshot()
    assert "wind_tariff_inr_per_kwh" in snap
    assert "solar_tariff_inr_per_kwh" in snap
    assert snap["wind_tariff_inr_per_kwh"] > 0
    assert snap["solar_tariff_inr_per_kwh"] > 0


def test_economics_component_cost_table():
    rows = component_cost_table()
    assert len(rows) > 0
    assert all("component" in r for r in rows)
    assert any(r["component"] == "gearbox" for r in rows)
    assert any(r["component"] == "inverter" for r in rows)


def test_economics_evaluate_options_wind():
    evidence = evaluate_options(
        asset_id="WT-017",
        component="gearbox",
        failure_probability=0.45,
        risk_window_days=(7, 30),
    )
    assert evidence.recommended_option_id in {"repair_now", "defer_3d", "defer_14d"}
    assert len(evidence.options) == 3
    assert evidence.avoidable_exposure_inr is not None
    assert evidence.avoidable_exposure_inr >= 0
    assert evidence.tariff_inr_per_kwh is not None
    assert evidence.tariff_inr_per_kwh > 0


def test_economics_do_nothing_exposure():
    exposure = do_nothing_exposure(
        asset_id="WT-017",
        component="gearbox",
        failure_probability=0.45,
        horizon_days=30,
    )
    assert exposure > 0


def test_memory_library_cases():
    assert len(CASES) >= 10
    wind_cases = cases_for("wind_turbine")
    solar_cases = cases_for("solar_inverter")
    assert len(wind_cases) > 0
    assert len(solar_cases) > 0


def test_memory_retrieval():
    wt = FLEET[0]
    now = datetime(2026, 9, 12, 10, 0, tzinfo=UTC)
    packet = EvidencePacket(
        asset_id=wt.asset_id,
        asset_type=wt.asset_type,
        generated_at=now,
        health_score=68.5,
        anomaly=AnomalyEvidence(
            anomaly_score=0.75,
            detectors=[DetectorScore(detector="z_score", score=0.8, threshold=0.6, fired=True)],
            signals=[
                ResidualSignal(
                    name="gearbox_oil_temp_c",
                    unit="C",
                    actual=82.0,
                    expected=65.0,
                    residual=17.0,
                    residual_pct=26.1,
                    z_score=3.8,
                )
            ],
        ),
        peers=PeerEvidence(
            peer_group="kutch-wind",
            n_peers=18,
            asset_residual_pct=-10.5,
            peer_median_residual_pct=0.2,
            deviation_percentile=95.0,
            verdict=PeerVerdict.ASSET_SPECIFIC,
        ),
        environment=EnvironmentEvidence(
            source="site_met",
            operating_state=OperatingState.NORMAL,
            curtailment_detected=False,
            sensor_health=SensorHealth.OK,
            explains_fraction=0.05,
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
        ),
        risk=RiskAssessment(
            risk_score=0.65,
            risk_band=RiskBand.ELEVATED,
            horizon_days=30,
            drivers={"gearbox_oil_temp_c": 0.8},
        ),
    )

    sig = signature_from_packet(packet)
    assert "thermal_z" in sig
    assert sig["thermal_z"] > 0

    similar = find_similar_cases(packet, k=3)
    assert len(similar) <= 3
    assert len(similar) > 0
    assert similar[0].similarity >= 0


def test_evaluate_cleaning_options_now():
    advisor = evaluate_cleaning_options(
        asset_id="INV-023",
        soiling_loss_pct=11.5,
        accumulation_rate_pct_day=0.25,
        rain_probability_48h=0.05,
        dust_risk_level="high",
    )
    assert advisor.recommended_action == "clean_now"
    assert advisor.current_soiling_loss_pct == 11.5
    assert advisor.break_even_days <= 6.0
    assert len(advisor.options) == 4
    assert advisor.confidence > 0.8


def test_evaluate_cleaning_options_rain_wait():
    advisor = evaluate_cleaning_options(
        asset_id="INV-023",
        soiling_loss_pct=8.0,
        accumulation_rate_pct_day=0.20,
        rain_probability_48h=0.85,
        dust_risk_level="high",
    )
    # High rain forecast should defer immediate washing to leverage natural washing
    assert advisor.recommended_action == "post_rain_reassess"
    assert "precipitation" in advisor.recommended_window.lower()
    wait_opt = [o for o in advisor.options if o.option_id == "wait_72h"][0]
    assert wait_opt.rain_cleaning_probability == 0.85
    # Since dust is high and rain is high, cementation risk is false (strong rain > 5mm cleans rather than cements)
    assert advisor.confidence > 0.8

