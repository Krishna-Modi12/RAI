"""Atmospheric dust exposure modeling and deposition prior estimation.

Implements:
1. CAMS aerosol optical depth (AOD @ 550nm) and dust mass concentration monitoring.
2. Cumulative Environmental Exposure Memory:
   Integrals over 3h, 12h, 24h, 72h, 7d, and 14d windows:
   D(t) = integral_{t-T}^t f(dust, wind, RH) dt
3. Physical Deposition Prior:
   Distinguishes atmospheric column concentration from surface glass deposition by
   accounting for wind shear resuspension vs settling and humidity-induced adhesion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from rai.environment.weather_provider import AtmosphericConditions, get_weather_provider

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DustStormRisk:
    risk_level: str  # "low", "moderate", "high", "extreme"
    confidence: float
    expected_onset_hours: float
    expected_duration_hours: float
    aod_550nm: float
    dust_ug_m3: float
    pm10_ug_m3: float
    evidence: list[str]


@dataclass(frozen=True)
class CumulativeDustExposure:
    """Environmental memory of particulate and aerosol exposure over multiple horizons."""

    dust_3h_ug_m3_h: float
    dust_12h_ug_m3_h: float
    dust_24h_ug_m3_h: float
    dust_72h_ug_m3_h: float
    dust_7d_ug_m3_h: float
    dust_14d_ug_m3_h: float
    aod_integral_72h: float
    effective_deposition_index: float  # [0.0, 1.0] non-dimensional deposition intensity
    wind_shear_factor: float  # high wind (>8 m/s) resuspends; calm (1-4 m/s) settles
    humidity_adhesion_factor: float  # high RH (>65%) causes moisture sticking


def compute_dust_exposure_memory(
    conditions: AtmosphericConditions,
    historical_dust_series: list[float] | None = None,
) -> CumulativeDustExposure:
    """Compute cumulative environmental exposure integrals across multiple time horizons.

    D(t) = integral_{t-T}^t f(dust, wind, RH) dt
    """
    current_dust = conditions.dust_ug_m3
    current_aod = conditions.aod_550nm
    wind = conditions.wind_speed_ms
    rh = conditions.relative_humidity_pct

    # If historical series is provided, use exact sums; otherwise synthesize based on current state & 24h integral
    if historical_dust_series and len(historical_dust_series) >= 24:
        s = historical_dust_series
        dust_3h = float(np.sum(s[-3:])) if len(s) >= 3 else current_dust * 3.0
        dust_12h = float(np.sum(s[-12:])) if len(s) >= 12 else current_dust * 12.0
        dust_24h = float(np.sum(s[-24:]))
        dust_72h = float(np.sum(s[-72:])) if len(s) >= 72 else dust_24h * 3.0
        dust_7d = float(np.sum(s[-168:])) if len(s) >= 168 else dust_24h * 7.0
        dust_14d = float(np.sum(s[-336:])) if len(s) >= 336 else dust_24h * 14.0
    else:
        # Realistic decay / rolling approximation based on CAMS 24h integral
        base_rate = max(current_dust, 15.0)
        dust_3h = base_rate * 3.0
        dust_12h = base_rate * 12.0
        dust_24h = conditions.dust_24h_integral if conditions.dust_24h_integral > 0 else base_rate * 24.0
        dust_72h = dust_24h * 3.0
        dust_7d = dust_24h * 7.0
        dust_14d = dust_24h * 14.0

    aod_integral_72h = current_aod * 72.0

    # Physics-based transfer factors:
    # 1. Wind shear: low wind (1-4 m/s) allows particle settling; high wind (>8 m/s) creates resuspension/scouring
    if wind < 4.0:
        wind_factor = 1.25  # stagnant air promotes deposition
    elif wind > 8.5:
        wind_factor = 0.65  # high wind creates turbulent detachment / resuspension
    else:
        wind_factor = 1.0

    # 2. Humidity adhesion: high RH (>65%) promotes dew/hygroscopic sticking
    if rh > 75.0:
        rh_factor = 1.40
    elif rh > 60.0:
        rh_factor = 1.15
    else:
        rh_factor = 0.90

    # Non-dimensional deposition intensity [0, 1] normalized against severe desert conditions (100 ug/m3 for 72h)
    normalized_exposure = min(1.0, dust_72h / (120.0 * 72.0))
    deposition_index = float(np.clip(normalized_exposure * wind_factor * rh_factor, 0.0, 1.0))

    return CumulativeDustExposure(
        dust_3h_ug_m3_h=round(dust_3h, 1),
        dust_12h_ug_m3_h=round(dust_12h, 1),
        dust_24h_ug_m3_h=round(dust_24h, 1),
        dust_72h_ug_m3_h=round(dust_72h, 1),
        dust_7d_ug_m3_h=round(dust_7d, 1),
        dust_14d_ug_m3_h=round(dust_14d, 1),
        aod_integral_72h=round(aod_integral_72h, 2),
        effective_deposition_index=round(deposition_index, 3),
        wind_shear_factor=round(wind_factor, 2),
        humidity_adhesion_factor=round(rh_factor, 2),
    )


def estimate_deposition_prior(
    conditions: AtmosphericConditions,
    exposure_memory: CumulativeDustExposure | None = None,
) -> float:
    """Estimate the prior probability or daily deposition rate (%/day) from atmospheric conditions."""
    if exposure_memory is None:
        exposure_memory = compute_dust_exposure_memory(conditions)

    # Base dry deposition rate typically 0.2% - 0.4%/day in clean arid zones,
    # escalating to 1.5% - 2.8%/day during severe dust events
    base_rate_pct = 0.22
    deposition_rate_pct_day = base_rate_pct + (exposure_memory.effective_deposition_index * 2.2)
    return float(np.clip(deposition_rate_pct_day, 0.15, 3.5))


def detect_dust_storm_risk(conditions: AtmosphericConditions | None = None) -> DustStormRisk:
    """Assess atmospheric dust and sandstorm risk from CAMS aerosol forecasts."""
    if conditions is None:
        conditions = get_weather_provider().get_current_conditions("charanka-solar")

    dust = conditions.dust_ug_m3
    aod = conditions.aod_550nm
    pm10 = conditions.pm10_ug_m3
    wind = conditions.wind_speed_ms

    evidence: list[str] = []
    risk_score = 0.0

    # AOD impact
    if aod >= 1.0:
        risk_score += 0.45
        evidence.append(f"Critical atmospheric turbidity: AOD {aod:.2f} >= 1.0 (extreme haze/sandstorm)")
    elif aod >= 0.60:
        risk_score += 0.30
        evidence.append(f"Elevated aerosol optical depth: AOD {aod:.2f} >= 0.60")
    elif aod >= 0.40:
        risk_score += 0.15

    # Near-surface dust impact
    if dust >= 150.0:
        risk_score += 0.40
        evidence.append(f"Severe desert dust concentration: {dust:.1f} ug/m3")
    elif dust >= 80.0:
        risk_score += 0.25
        evidence.append(f"Elevated surface dust concentration: {dust:.1f} ug/m3")
    elif dust >= 40.0:
        risk_score += 0.10

    # High wind velocity elevates transport and sandstorm risk
    if wind >= 12.0:
        risk_score += 0.20
        evidence.append(f"High surface wind velocity ({wind:.1f} m/s) driving active sand saltation")
    elif wind >= 8.0:
        risk_score += 0.10

    risk_score = min(1.0, risk_score)

    if risk_score >= 0.75:
        level = "extreme"
    elif risk_score >= 0.50:
        level = "high"
    elif risk_score >= 0.25:
        level = "moderate"
    else:
        level = "low"

    return DustStormRisk(
        risk_level=level,
        confidence=round(0.80 + 0.15 * min(1.0, (aod + dust / 200.0) / 2.0), 2),
        expected_onset_hours=0.0 if level in {"high", "extreme"} else (24.0 if level == "moderate" else 48.0),
        expected_duration_hours=36.0 if level in {"high", "extreme"} else (12.0 if level == "moderate" else 0.0),
        aod_550nm=aod,
        dust_ug_m3=dust,
        pm10_ug_m3=pm10,
        evidence=evidence,
    )
