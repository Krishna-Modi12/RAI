"""Environmental attribution and sensor validation.

Before any equipment conclusion is allowed, this layer answers three questions:

1. **Is the shortfall explained by conditions?** The expected-behaviour model already
   conditions on weather, so the test is how much of the raw deficit survives conditioning.
   If almost none does, the weather explains it and there is nothing to investigate.
2. **Was the output commanded down?** Curtailment is a contractual instruction, not a fault.
3. **Is the instrument telling the truth?** A drifting or frozen sensor manufactures a
   convincing deficit out of a perfectly healthy machine. Detecting this is what separates a
   useful monitoring system from one that sends crews to inspect gearboxes that are fine.

The sensor check is a physical cross-check, not a statistical one: rotor speed is set by the
wind that actually reaches the blades, so comparing measured wind against rpm-implied wind
exposes an anemometer that has drifted away from reality.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from rai.config import Asset
from rai.schemas import (
    AssetType,
    EnvironmentEvidence,
    EnvironmentVerdict,
    OperatingState,
    SensorHealth,
)

log = logging.getLogger(__name__)

ENVIRONMENTAL_THRESHOLD = 0.60
PARTIAL_THRESHOLD = 0.25

# A residual at or above this many sigma has already survived conditioning on the weather.
SIGNIFICANT_RESIDUAL_Z = 2.5

# Rotor speed model used for the cross-check, matching the controller's schedule.
RPM_INTERCEPT = 6.0
RPM_SLOPE = 10.5
SENSOR_DRIFT_SUSPECT = 0.10  # 10% systematic disagreement
SENSOR_DRIFT_FAILED = 0.16
FROZEN_WINDOW = 18  # consecutive identical samples that indicate a stuck channel


def _rpm_implied_wind(rpm: np.ndarray, rated_ms: float) -> np.ndarray:
    """Invert the rotor-speed schedule to estimate the wind the blades actually saw."""
    fraction = (rpm - RPM_INTERCEPT) / RPM_SLOPE
    return np.clip(fraction, 0.0, 1.0) * rated_ms


def check_sensor_health(asset: Asset, frame: pd.DataFrame) -> tuple[SensorHealth, str | None]:
    """Validate the primary input sensor against an independent physical channel."""
    if asset.asset_type is not AssetType.WIND_TURBINE:
        if "poa_wm2" in frame.columns:
            recent = frame["poa_wm2"].tail(FROZEN_WINDOW * 2).dropna()
            if len(recent) >= FROZEN_WINDOW and recent.nunique() <= 1 and recent.iloc[-1] > 5:
                return SensorHealth.FAILED, "irradiance sensor is holding a constant value"
        return SensorHealth.OK, None

    if "wind_speed_ms" not in frame.columns or "rotor_rpm" not in frame.columns:
        return SensorHealth.OK, None

    running = frame[
        (frame["operating_state"] == OperatingState.NORMAL.value)
        & frame["wind_speed_ms"].notna()
        & frame["rotor_rpm"].notna()
        & (frame["rotor_rpm"] > RPM_INTERCEPT + 0.5)
    ]
    if len(running) < 30:
        return SensorHealth.OK, None

    # A channel that never changes while the machine is running is stuck.
    tail = running["wind_speed_ms"].tail(FROZEN_WINDOW)
    if len(tail) == FROZEN_WINDOW and tail.nunique() <= 1:
        return SensorHealth.FAILED, "wind speed sensor is holding a constant value"

    # Compare over the recent period only. A drift that has been ramping for days has a much
    # smaller median over the whole window than it does now, which would hide a live fault.
    recent = running.tail(max(len(running) // 8, 60))
    measured = recent["wind_speed_ms"].to_numpy(dtype=float)
    implied = _rpm_implied_wind(recent["rotor_rpm"].to_numpy(dtype=float), asset.rated_ms or 12.5)

    # Only compare below rated, where rotor speed still tracks wind.
    comparable = (implied > 3.0) & (implied < (asset.rated_ms or 12.5) * 0.95) & (measured > 3.0)
    if comparable.sum() < 20:
        return SensorHealth.OK, None

    disagreement = float(np.median((measured[comparable] - implied[comparable]) / implied[comparable]))
    if abs(disagreement) >= SENSOR_DRIFT_FAILED:
        return (
            SensorHealth.FAILED,
            f"anemometer disagrees with rotor-speed-implied wind by {disagreement:+.0%}",
        )
    if abs(disagreement) >= SENSOR_DRIFT_SUSPECT:
        return (
            SensorHealth.SUSPECT,
            f"anemometer reads {disagreement:+.0%} against rotor-speed-implied wind",
        )
    return SensorHealth.OK, None


def attribute(
    asset: Asset,
    frame: pd.DataFrame,
    expected: np.ndarray | None,
    actual: np.ndarray | None,
    typical_output_kw: float | None,
    peak_abs_z: float = 0.0,
    residual_step_detected: bool = False,
) -> EnvironmentEvidence:
    """Decide how much of the observed shortfall the environment accounts for.

    `peak_abs_z` is the largest residual z-score surviving after the expected-behaviour model
    has already conditioned on the weather. It is decisive: a four-sigma residual *is* the
    part the weather could not explain, so no ratio of raw output to typical output may
    overrule it. Without this guard the layer degenerates into blaming the weather whenever
    conditions are poor, which is exactly when faults are hardest to see.
    """
    recent = frame.tail(max(len(frame) // 10, 12))

    state_counts = recent["operating_state"].value_counts()
    dominant_state = (
        OperatingState(state_counts.index[0]) if not state_counts.empty else OperatingState.UNKNOWN
    )
    curtailed = bool((recent["operating_state"] == OperatingState.CURTAILED.value).mean() > 0.25)

    conditions: dict[str, float] = {}
    for column in (
        "wind_speed_ms",
        "wind_direction_deg",
        "ambient_temp_c",
        "air_density",
        "humidity_pct",
        "poa_wm2",
        "module_temp_c",
    ):
        if column in recent.columns:
            value = recent[column].mean()
            if pd.notna(value):
                conditions[column] = round(float(value), 2)

    sensor_health, sensor_note = check_sensor_health(asset, frame)

    explains = 0.0
    if expected is not None and actual is not None and typical_output_kw:
        finite = np.isfinite(expected) & np.isfinite(actual)
        if finite.sum() >= 5:
            mean_actual = float(np.mean(actual[finite]))
            mean_expected = float(np.mean(expected[finite]))
            raw_deficit = typical_output_kw - mean_actual
            conditioned_deficit = mean_expected - mean_actual
            if raw_deficit > 0.02 * asset.rated_power_kw:
                # Share of the shortfall that disappears once conditions are accounted for.
                explains = float(
                    np.clip(1.0 - max(conditioned_deficit, 0.0) / raw_deficit, 0.0, 1.0)
                )
            elif conditioned_deficit <= 0:
                explains = 1.0

    # A residual this large has already survived conditioning on the weather, so the weather
    # is not the explanation, whatever the raw-output ratio suggests.
    # Weather moves continuously. A step change in a residual that has *already* been
    # conditioned on the weather is therefore an asset event, not a meteorological one —
    # which catches subtle faults sitting just below the sigma threshold.
    residual_is_significant = peak_abs_z >= SIGNIFICANT_RESIDUAL_Z or residual_step_detected
    if residual_is_significant:
        explains = min(explains, 0.24)

    if curtailed:
        verdict = EnvironmentVerdict.NOT_ENVIRONMENTAL
        note = "output is capped by a grid curtailment instruction"
    elif residual_is_significant:
        verdict = EnvironmentVerdict.NOT_ENVIRONMENTAL
        note = (
            "a step change in the conditioned residual is not a weather pattern"
            if residual_step_detected and peak_abs_z < SIGNIFICANT_RESIDUAL_Z
            else f"a {peak_abs_z:.1f} sigma residual remains after conditioning on the "
            f"measured conditions, so the environment does not account for it"
        )
    elif explains >= ENVIRONMENTAL_THRESHOLD:
        verdict = EnvironmentVerdict.ENVIRONMENTAL
        note = f"conditions account for {explains:.0%} of the shortfall against typical output"
    elif explains >= PARTIAL_THRESHOLD:
        verdict = EnvironmentVerdict.PARTIAL
        note = f"conditions account for {explains:.0%} of the shortfall; a residual remains"
    else:
        verdict = EnvironmentVerdict.NOT_ENVIRONMENTAL
        note = f"conditions explain only {explains:.0%} of the observed deviation"

    if sensor_note:
        note = f"{note}; {sensor_note}"

    return EnvironmentEvidence(
        source="simulated_site_met",
        conditions=conditions,
        operating_state=dominant_state,
        curtailment_detected=curtailed,
        sensor_health=sensor_health,
        explains_fraction=round(explains, 3),
        verdict=verdict,
        note=note,
    )
