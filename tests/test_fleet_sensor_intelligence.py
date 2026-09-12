"""Unit tests for fleet common-cause event detection and sensor health gating."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rai.models.fleet_common_cause import detect_fleet_common_cause
from rai.models.sensor_health import evaluate_sensor_health


def test_detect_fleet_common_cause_isolated():
    # Only 1 out of 10 peers has high anomaly
    peers = [0.1, 0.05, 0.08, 0.85, 0.12, 0.04, 0.09, 0.11, 0.07, 0.10]
    res = detect_fleet_common_cause(
        asset_id="WT-017",
        asset_class="wind_turbine",
        peer_anomaly_scores=peers,
        threshold_fraction=0.30,
    )
    assert res.is_common_cause is False
    assert res.suppression_factor == 1.0
    assert "Isolated anomaly confirmed" in res.rationale


def test_detect_fleet_common_cause_widespread_sandstorm():
    # 8 out of 10 solar inverters drop concurrently during a sandstorm
    peers = [0.85, 0.90, 0.78, 0.82, 0.88, 0.15, 0.79, 0.84, 0.20, 0.81]
    res = detect_fleet_common_cause(
        asset_id="INV-009",
        asset_class="solar_inverter",
        peer_anomaly_scores=peers,
        site_environmental_score=0.80,
        threshold_fraction=0.30,
    )
    assert res.is_common_cause is True
    assert res.common_cause_type == "sandstorm_dust"
    assert res.suppression_factor <= 0.20
    assert res.affected_fraction >= 0.70


def test_evaluate_sensor_health_nominal():
    df = pd.DataFrame({
        "wind_speed_ms": np.random.normal(8.0, 1.2, 50),
        "rotor_speed_rpm": np.random.normal(15.0, 1.0, 50),
        "active_power_kw": np.random.normal(1200.0, 80.0, 50),
        "gearbox_oil_temp_c": np.random.normal(68.0, 2.0, 50),
    })
    report = evaluate_sensor_health(df, "wind_turbine")
    assert report.status == "OK"
    assert report.sensor_reliability_multiplier >= 0.85
    assert len(report.stuck_sensors) == 0
    assert report.requires_human_review is False


def test_evaluate_sensor_health_frozen_thermocouple():
    # Thermocouple stuck exactly at 65.0 deg C (zero variance)
    df = pd.DataFrame({
        "wind_speed_ms": np.random.normal(8.0, 1.2, 50),
        "rotor_speed_rpm": np.random.normal(15.0, 1.0, 50),
        "active_power_kw": np.random.normal(1200.0, 80.0, 50),
        "gearbox_oil_temp_c": [65.0] * 50,  # Frozen channel
    })
    report = evaluate_sensor_health(df, "wind_turbine")
    assert "gearbox_oil_temp_c" in report.stuck_sensors
    assert report.status in {"SUSPECT", "FAILED"}
    assert report.requires_human_review is True
