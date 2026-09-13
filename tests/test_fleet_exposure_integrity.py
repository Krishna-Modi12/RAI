"""Regression tests for the Fleet Overview exposure fix.

Guards against the bug flagged during release hardening: `services/api/routers/fleet.py`
used to derive `revenue_at_risk_inr` from an instantaneous `expected_power_kw - power_kw`
proxy, which read exactly ₹0 for any asset whose current output wasn't below its physics
baseline — even a CRITICAL-risk asset flagged by a non-power signal (vibration, temperature).
These tests pin the fix: exposure is now driven by `rai.economics.engine.do_nothing_exposure`
(calibrated risk + component cost table), so it is non-zero for a genuinely high-risk asset
regardless of what its instantaneous power deficit looks like.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from rai.schemas import (
    AnomalyEvidence,
    AssetState,
    AssetType,
    OperatingState,
    RiskAssessment,
    RiskBand,
)
from services.api.main import app
from services.api.routers.fleet import (
    PRIORITY_QUEUE_HORIZON_DAYS,
    _component_for,
    _expected_consequence_inr,
)

client = TestClient(app)


def _critical_wind_state(power_kw: float, expected_power_kw: float) -> AssetState:
    """A CRITICAL-risk wind turbine, flagged by a vibration signal, not by power output."""
    return AssetState(
        asset_id="WT-017",
        asset_type=AssetType.WIND_TURBINE,
        name="Turbine 17",
        site="Kutch Wind Farm",
        as_of=datetime.now(UTC),
        health_score=42.0,
        operating_state=OperatingState.NORMAL,
        power_kw=power_kw,
        expected_power_kw=expected_power_kw,
        anomaly=AnomalyEvidence(anomaly_score=0.91, dominant_signal="drivetrain_vibration_mms"),
        risk=RiskAssessment(risk_score=0.85, risk_band=RiskBand.CRITICAL, risk_window_days=(7, 21)),
    )


def test_exposure_nonzero_when_power_not_below_baseline():
    """The exact bug: current power >= expected, but the asset is CRITICAL on another signal."""
    st = _critical_wind_state(power_kw=2000.0, expected_power_kw=1900.0)  # no deficit
    exposure = _expected_consequence_inr(st, PRIORITY_QUEUE_HORIZON_DAYS)
    assert exposure is not None
    assert exposure > 0, "a CRITICAL asset must never show ₹0 exposure"


def test_exposure_matches_regardless_of_instantaneous_deficit():
    """Exposure is a modeled consequence of risk, not a readout of the current power gap."""
    no_deficit = _critical_wind_state(power_kw=2000.0, expected_power_kw=1900.0)
    with_deficit = _critical_wind_state(power_kw=900.0, expected_power_kw=1900.0)

    exposure_no_deficit = _expected_consequence_inr(no_deficit, PRIORITY_QUEUE_HORIZON_DAYS)
    exposure_with_deficit = _expected_consequence_inr(with_deficit, PRIORITY_QUEUE_HORIZON_DAYS)

    assert exposure_no_deficit is not None
    assert exposure_with_deficit is not None
    assert exposure_no_deficit == exposure_with_deficit


def test_expected_consequence_none_when_risk_unavailable():
    """No fabricated ₹0 when the estimate genuinely cannot be computed."""
    st = _critical_wind_state(power_kw=2000.0, expected_power_kw=1900.0)
    st.risk = None
    assert _expected_consequence_inr(st, PRIORITY_QUEUE_HORIZON_DAYS) is None


def test_component_for_mapping():
    assert _component_for("drivetrain_vibration_mms", AssetType.WIND_TURBINE) == "gearbox"
    assert _component_for("gearbox_oil_temp_c", AssetType.WIND_TURBINE) == "gearbox"
    assert _component_for("dc_power_kw", AssetType.SOLAR_INVERTER) == "inverter"
    assert _component_for("generator_winding_temp_c", AssetType.WIND_TURBINE) == "generator"
    assert _component_for(None, AssetType.WIND_TURBINE) == "generator"


def test_priority_endpoint_never_reports_zero_for_flagged_assets():
    """End-to-end: every asset the live queue flags carries a genuine, non-zero exposure."""
    resp = client.get("/api/fleet/priority")
    assert resp.status_code == 200
    queue = resp.json()
    assert isinstance(queue, list)
    for item in queue:
        assert item["revenue_at_risk_inr"] is None or item["revenue_at_risk_inr"] > 0, (
            f"{item['asset_id']} is in the action queue (risk_score={item['risk_score']}) "
            "but shows ₹0 exposure"
        )
