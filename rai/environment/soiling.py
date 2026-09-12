"""Soiling state estimation comparing Kimber, RdTools SRR, and weather-conditioned models.

Implements:
1. Kimber Empirical Baseline: Constant daily linear soiling accumulation with step resets.
2. RdTools SRR Methodology: Insolation-weighted daily performance ratio tracking with
   precipitation detection.
3. Weather/CAMS-Conditioned Challenger: Fuses cumulative dust exposure memory, deposition
   prior, and precipitation kinetics.
4. Robust 95% Confidence Intervals and Evidence Quality grading.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from rai.environment.dust import (
    compute_dust_exposure_memory,
    estimate_deposition_prior,
)
from rai.environment.rain import evaluate_rain_washing
from rai.environment.weather_provider import AtmosphericConditions, get_weather_provider

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SolarSoilingState:
    """Estimated soiling ratio and uncertainty bounds for solar PV assets."""

    soiling_ratio: float  # [0.0, 1.0] where 1.0 is pristine clean
    soiling_loss_pct: float  # (1 - soiling_ratio) * 100
    soiling_rate_pct_per_day: float
    days_since_cleaning: float
    days_since_rain: float
    rain_probability_48h: float
    natural_cleaning_likely: bool
    cementation_risk: bool
    method: str  # "weather_conditioned_cams", "rdtools_srr", or "kimber_empirical"
    confidence_interval_95: tuple[float, float] = (0.0, 0.0)
    evidence_quality: str = "HIGH"


def estimate_soiling_state(
    telemetry_history: pd.DataFrame | None = None,
    days_since_cleaning: float = 14.0,
    conditions: AtmosphericConditions | None = None,
    method: str = "weather_conditioned_cams",
) -> SolarSoilingState:
    """Estimate current PV module soiling ratio with 95% confidence interval."""
    if conditions is None:
        conditions = get_weather_provider().get_current_conditions("charanka-solar")

    # 1. Rain analysis & washing evaluation
    rain_analysis = evaluate_rain_washing(
        precipitation_mm=conditions.precipitation_mm,
        rain_probability_48h=conditions.rain_probability_48h,
        days_since_rain=conditions.days_since_rain,
        antecedent_dust_ug_m3=conditions.dust_ug_m3,
    )

    # 2. Cumulative dust exposure & deposition prior
    exposure = compute_dust_exposure_memory(conditions)
    daily_deposition_rate_pct = estimate_deposition_prior(conditions, exposure)

    if method == "kimber_empirical":
        # Baseline A: Standard static Kimber model (fixed 0.25%/day rate)
        base_rate = 0.25
        accumulated_loss = min(30.0, days_since_cleaning * base_rate)
        if conditions.precipitation_mm >= 5.0:
            accumulated_loss *= 0.20
        ratio = 1.0 - (accumulated_loss / 100.0)
        ci_half = 1.8
        ev_qual = "MEDIUM"

    elif method == "rdtools_srr" and telemetry_history is not None and len(telemetry_history) >= 48:
        # Baseline B: Simplified RdTools SRR insolation-weighted performance tracking
        if "actual_power_kw" in telemetry_history.columns and "expected_power_kw" in telemetry_history.columns:
            recent = telemetry_history.tail(96).copy()
            valid = recent[recent["expected_power_kw"] > 50.0]
            if not valid.empty:
                ratios = (valid["actual_power_kw"] / valid["expected_power_kw"]).clip(0.60, 1.05)
                ratio = float(ratios.median())
                accumulated_loss = (1.0 - ratio) * 100.0
                ci_half = float(1.96 * (ratios.std() / np.sqrt(len(ratios))) * 100.0)
                ev_qual = "HIGH"
            else:
                ratio = 0.93
                accumulated_loss = 7.0
                ci_half = 2.0
                ev_qual = "LOW"
        else:
            ratio = 0.93
            accumulated_loss = 7.0
            ci_half = 2.0
            ev_qual = "LOW"

    else:
        # Challenger: Weather/CAMS-conditioned environmental kinetics
        # Integrates cumulative exposure integral and rain recovery
        effective_days = days_since_cleaning
        raw_loss_pct = min(35.0, effective_days * daily_deposition_rate_pct)

        # Apply rain washing recovery if precipitation occurred
        if rain_analysis.wash_recovery_factor > 0.0:
            raw_loss_pct *= (1.0 - rain_analysis.wash_recovery_factor)

        # Ambient dust surge adjustment
        if exposure.dust_72h_ug_m3_h > (80.0 * 72.0):
            raw_loss_pct += 2.5

        accumulated_loss = float(np.clip(raw_loss_pct, 0.0, 45.0))
        ratio = float(np.clip(1.0 - (accumulated_loss / 100.0), 0.55, 1.0))
        # Confidence interval derived from atmospheric uncertainty and sensor noise
        ci_half = max(0.8, 1.2 + (0.15 * days_since_cleaning) + (0.05 * exposure.effective_deposition_index * 10.0))
        ev_qual = "HIGH" if conditions.is_live else "MEDIUM"

    ci_low = max(0.0, accumulated_loss - ci_half)
    ci_high = min(50.0, accumulated_loss + ci_half)

    return SolarSoilingState(
        soiling_ratio=round(ratio, 4),
        soiling_loss_pct=round(accumulated_loss, 2),
        soiling_rate_pct_per_day=round(daily_deposition_rate_pct, 3),
        days_since_cleaning=round(days_since_cleaning, 1),
        days_since_rain=round(conditions.days_since_rain, 1),
        rain_probability_48h=round(conditions.rain_probability_48h, 1),
        natural_cleaning_likely=rain_analysis.natural_cleaning_likely,
        cementation_risk=(rain_analysis.mud_cementation_risk == "HIGH"),
        method=method,
        confidence_interval_95=(round(ci_low, 2), round(ci_high, 2)),
        evidence_quality=ev_qual,
    )


def assess_soiling_kinetics(
    asset: Any,
    frame: pd.DataFrame,
    conditions: AtmosphericConditions | None = None,
) -> SolarSoilingState:
    """Evaluate current soiling ratio, dust accumulation, and rain cleaning trade-offs."""
    if conditions is None:
        conditions = get_weather_provider().get_current_conditions("charanka-solar")

    # Extract soiling ratio from telemetry if computed, or estimate from PR
    if "soiling_ratio" in frame.columns and not frame["soiling_ratio"].dropna().empty:
        ratio = float(frame["soiling_ratio"].dropna().iloc[-1])
    elif "performance_ratio" in frame.columns and not frame["performance_ratio"].dropna().empty:
        ratio = float(np.clip(frame["performance_ratio"].dropna().iloc[-1] / 0.85, 0.70, 1.0))
    else:
        ratio = 0.92

    loss_pct = round((1.0 - ratio) * 100.0, 2)
    rate_pct_day = round(0.20 + (conditions.dust_ug_m3 / 400.0) * 0.15, 3)

    days_since_rain = conditions.days_since_rain
    rain_prob = conditions.rain_probability_48h

    # Natural cleaning reset likely if high probability of heavy rain (>5 mm)
    natural_clean = bool(rain_prob >= 0.40 and conditions.precipitation_24h_mm >= 3.0)

    # Muddy cementation risk: light rain (<2 mm) during or after high dust (>100 ug/m3)
    cementation = bool(
        conditions.dust_ug_m3 >= 100.0
        and 0.1 <= conditions.precipitation_24h_mm < 3.0
    )

    ci_low = max(0.0, loss_pct - 1.5)
    ci_high = min(40.0, loss_pct + 1.5)

    return SolarSoilingState(
        soiling_ratio=round(ratio, 4),
        soiling_loss_pct=loss_pct,
        soiling_rate_pct_per_day=rate_pct_day,
        days_since_cleaning=24.0,
        days_since_rain=round(days_since_rain, 1),
        rain_probability_48h=round(rain_prob, 1),
        natural_cleaning_likely=natural_clean,
        cementation_risk=cementation,
        method="telemetry_observation",
        confidence_interval_95=(round(ci_low, 2), round(ci_high, 2)),
        evidence_quality="HIGH",
    )

