"""Unit tests for Solar Environmental Intelligence & Soiling Kinetics Engine."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from rai.config import FLEET
from rai.models.environment_solar import (
    AdditiveLossDecomposition,
    DustStormRisk,
    SolarSoilingState,
    assess_soiling_kinetics,
    compute_clear_sky_poa,
    decompose_solar_losses,
    detect_dust_storm_risk,
)
from rai.models.weather_provider import AtmosphericConditions
from rai.schemas import AssetType


def test_detect_dust_storm_risk_benign():
    cond = AtmosphericConditions(
        timestamp=datetime.now(UTC),
        site="charanka-solar",
        is_live=True,
        dust_ug_m3=25.0,
        aod_550nm=0.15,
        pm10_ug_m3=30.0,
        pm25_ug_m3=15.0,
        precipitation_mm=0.0,
        rain_probability_pct=5.0,
        ambient_temp_c=32.0,
        wind_speed_ms=4.0,
        wind_direction_deg=220.0,
        relative_humidity_pct=40.0,
    )
    risk = detect_dust_storm_risk(cond)
    assert isinstance(risk, DustStormRisk)
    assert risk.risk_level == "low"
    assert risk.expected_duration_hours == 0.0
    assert risk.confidence > 0.5


def test_detect_dust_storm_risk_high():
    cond = AtmosphericConditions(
        timestamp=datetime.now(UTC),
        site="charanka-solar",
        is_live=True,
        dust_ug_m3=550.0,
        aod_550nm=1.8,
        pm10_ug_m3=450.0,
        pm25_ug_m3=220.0,
        precipitation_mm=0.0,
        rain_probability_pct=0.0,
        ambient_temp_c=41.0,
        wind_speed_ms=14.0,
        wind_direction_deg=270.0,
        relative_humidity_pct=15.0,
    )
    risk = detect_dust_storm_risk(cond)
    assert isinstance(risk, DustStormRisk)
    assert risk.risk_level in ("high", "extreme")
    assert risk.expected_onset_hours >= 0.0
    assert len(risk.evidence) > 0


def test_compute_clearsky_poa():
    times = pd.date_range("2026-06-21 06:00", "2026-06-21 18:00", freq="1h", tz="UTC")
    poa = compute_clear_sky_poa(
        lat=23.9,
        lon=71.2,
        timestamps=times,
        tilt_deg=24.0,
        azimuth_deg=180.0,
    )
    assert isinstance(poa, pd.Series)
    assert len(poa) == len(times)
    assert (poa >= 0.0).all()
    # Midday irradiance at Charanka Solar Park in June should exceed 500 W/m²
    assert poa.max() > 500.0


def test_assess_soiling_kinetics_with_rain():
    solar_assets = [a for a in FLEET if a.asset_type == AssetType.SOLAR_INVERTER]
    assert len(solar_assets) > 0
    asset = solar_assets[0]

    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-01", periods=24, freq="1h"),
            "soiling_ratio": [0.88] * 24,
            "power_kw": [200.0] * 24,
        }
    )

    # Substantial rain forecast (>5mm)
    cond = AtmosphericConditions(
        timestamp=datetime.now(UTC),
        site="charanka-solar",
        is_live=True,
        dust_ug_m3=120.0,
        aod_550nm=0.4,
        pm10_ug_m3=90.0,
        pm25_ug_m3=45.0,
        precipitation_mm=9.0,  # Effective washing rain
        rain_probability_pct=85.0,
        ambient_temp_c=34.0,
        wind_speed_ms=5.0,
        wind_direction_deg=200.0,
        relative_humidity_pct=65.0,
        precipitation_24h_mm=10.0,
        rain_probability_48h=0.85,
        days_since_rain=1.0,
    )

    state = assess_soiling_kinetics(asset, frame, cond)
    assert isinstance(state, SolarSoilingState)
    assert state.soiling_ratio == 0.88
    assert state.soiling_loss_pct == 12.0
    assert state.natural_cleaning_likely is True
    assert state.cementation_risk is False


def test_decompose_solar_losses_additive():
    solar_assets = [a for a in FLEET if a.asset_type == AssetType.SOLAR_INVERTER]
    asset = solar_assets[0]

    decomp = decompose_solar_losses(
        asset=asset,
        actual_power_kw=175.0,
        expected_clean_power_kw=250.0,
        measured_poa_wm2=800.0,
        expected_poa_wm2=1000.0,
        module_temp_c=45.0,
        ambient_temp_c=35.0,
        soiling_loss_pct=8.0,
        is_curtailed=False,
        is_confirmed_equipment_fault=False,
    )

    assert isinstance(decomp, AdditiveLossDecomposition)
    assert decomp.total_loss_kw == pytest.approx(75.0, abs=0.1)
    assert decomp.total_loss_pct == pytest.approx(30.0, abs=0.1)

    sum_components = (
        decomp.irradiance_cloud_loss_kw
        + decomp.soiling_loss_kw
        + decomp.thermal_loss_kw
        + decomp.curtailment_loss_kw
        + decomp.equipment_loss_kw
        + decomp.unexplained_loss_kw
    )
    # Exact additive property: sum of components equals total loss
    assert sum_components == pytest.approx(decomp.total_loss_kw, abs=0.1)
    assert decomp.irradiance_cloud_loss_kw > 0.0
    assert decomp.soiling_loss_kw > 0.0
    assert decomp.thermal_loss_kw > 0.0
    assert "irradiance" in decomp.fractions
