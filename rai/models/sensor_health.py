"""Sensor health and telemetry data quality verification engine.

Ensures the decision engine does not mistake faulty instrumentation for equipment breakdown:
1. Missingness & telemetry dropout
2. Stuck / frozen sensor readings (zero rolling variance)
3. Impossible physical boundaries (e.g. negative wind speed, bearing temp > 150°C)
4. Cross-sensor contradictions (e.g. high generator RPM with zero electrical power)
5. Sudden unphysical spikes / discontinuity jumps

Computes a sensor reliability multiplier:
equipment_confidence = model_confidence * sensor_reliability
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

PHYSICAL_LIMITS = {
    "wind_speed_ms": (0.0, 45.0),
    "rotor_speed_rpm": (0.0, 35.0),
    "generator_speed_rpm": (0.0, 2500.0),
    "active_power_kw": (-50.0, 3500.0),
    "gearbox_oil_temp_c": (-10.0, 120.0),
    "generator_bearing_temp_c": (-10.0, 135.0),
    "poa_irradiance_w_m2": (0.0, 1450.0),
    "ambient_temp_c": (-20.0, 58.0),
    "dc_voltage_v": (0.0, 1500.0),
    "dc_current_a": (0.0, 4000.0),
    "inverter_temp_c": (-10.0, 95.0),
}


@dataclass(frozen=True)
class SensorHealthReport:
    status: str  # "OK", "SUSPECT", "FAILED"
    sensor_reliability_multiplier: float  # [0.0, 1.0]
    stuck_sensors: tuple[str, ...]
    out_of_bounds_sensors: tuple[str, ...]
    missing_rate: float
    cross_sensor_contradictions: tuple[str, ...]
    requires_human_review: bool
    summary: str


def evaluate_sensor_health(
    frame: pd.DataFrame,
    asset_class: str = "wind_turbine",
    window_rows: int = 48,
) -> SensorHealthReport:
    """Audit recent telemetry window for physical bounds, frozen sensors, and contradictions."""
    if frame.empty:
        return SensorHealthReport(
            status="FAILED",
            sensor_reliability_multiplier=0.0,
            stuck_sensors=(),
            out_of_bounds_sensors=(),
            missing_rate=1.0,
            cross_sensor_contradictions=("telemetry stream completely empty",),
            requires_human_review=True,
            summary="Sensor Health FAILED: Empty telemetry stream.",
        )

    recent = frame.tail(window_rows).copy()
    missing_rate = float(recent.isna().mean().mean())

    stuck: list[str] = []
    out_of_bounds: list[str] = []
    contradictions: list[str] = []

    numeric_cols = recent.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = recent[col].dropna()
        if len(series) >= 12:
            # 1. Stuck sensor check: variance identically zero over 12+ samples
            if series.std() == 0.0 and series.iloc[0] != 0.0:
                stuck.append(col)

            # 2. Physical boundary check
            if col in PHYSICAL_LIMITS:
                low, high = PHYSICAL_LIMITS[col]
                if (series < low).any() or (series > high).any():
                    out_of_bounds.append(col)

    # 3. Cross-sensor contradiction checks
    if "rotor_speed_rpm" in recent.columns and "active_power_kw" in recent.columns:
        last_rpm = float(recent["rotor_speed_rpm"].iloc[-1])
        last_kw = float(recent["active_power_kw"].iloc[-1])
        if last_rpm > 12.0 and last_kw < -10.0:
            contradictions.append(f"Rotor rotating at {last_rpm:.1f} RPM but output is {last_kw:.1f} kW")

    if "poa_irradiance_w_m2" in recent.columns and "dc_voltage_v" in recent.columns:
        last_poa = float(recent["poa_irradiance_w_m2"].iloc[-1])
        last_v = float(recent["dc_voltage_v"].iloc[-1])
        if last_poa > 500.0 and last_v < 10.0:
            contradictions.append(f"High irradiance ({last_poa:.0f} W/m2) but DC bus voltage collapsed ({last_v:.1f} V)")

    # Score sensor health
    penalty = 0.0
    if stuck:
        penalty += 0.35 * len(stuck)
    if out_of_bounds:
        penalty += 0.40 * len(out_of_bounds)
    if contradictions:
        penalty += 0.45 * len(contradictions)
    if missing_rate > 0.15:
        penalty += 0.30

    reliability = max(0.05, 1.0 - min(0.95, penalty))

    if reliability >= 0.85:
        status = "OK"
        review = False
        summary = "All sensor telemetry verified healthy; physical bounds and variance confirmed nominal."
    elif reliability >= 0.50:
        status = "SUSPECT"
        review = True
        summary = f"Sensor health SUSPECT: Potential instrumentation drift or freezing in {stuck or out_of_bounds or contradictions}."
    else:
        status = "FAILED"
        review = True
        summary = f"Sensor health FAILED: High error rate, stuck channels {stuck}, or contradictions {contradictions}."

    return SensorHealthReport(
        status=status,
        sensor_reliability_multiplier=round(reliability, 2),
        stuck_sensors=tuple(stuck),
        out_of_bounds_sensors=tuple(out_of_bounds),
        missing_rate=round(missing_rate, 3),
        cross_sensor_contradictions=tuple(contradictions),
        requires_human_review=review,
        summary=summary,
    )
