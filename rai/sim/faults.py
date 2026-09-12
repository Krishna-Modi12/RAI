"""Scenario injection with exact ground truth.

Every scenario applies a modifier over healthy telemetry along a known severity ramp, and
records an `InjectedEvent` giving the precise onset, the point the signature becomes
physically detectable, and the final severity. That record is the reason the evaluation in
`rai/eval` can state a real detection lead time and a real false-alarm rate instead of an
impression.

Six scenarios are genuine equipment faults. Six are not — they are the ways a healthy asset
can *look* broken: weather, dirt, grid instruction, and instruments that lie. A monitoring
system that cannot tell the two groups apart is worse than no monitoring, because it trains
operators to ignore it. The non-equipment scenarios are therefore first-class, not filler.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from rai.config import Asset
from rai.schemas import AssetType, InjectedEvent, OperatingState
from rai.sim.met import STATUS_CODE, SiteMet, child_seed

RampShape = Literal["linear", "exponential", "step", "sigmoid"]


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    asset_type: AssetType
    component: str
    is_equipment_fault: bool
    typical_onset_days: int
    ramp: RampShape
    description: str
    expected_detection: str
    # Fraction of the ramp that must elapse before the signature clears sensor noise.
    detectable_at: float = 0.15
    tags: tuple[str, ...] = field(default_factory=tuple)


SCENARIOS: dict[str, Scenario] = {
    "gearbox_bearing_wear": Scenario(
        name="gearbox_bearing_wear",
        label="Gearbox bearing wear",
        asset_type=AssetType.WIND_TURBINE,
        component="gearbox",
        is_equipment_fault=True,
        typical_onset_days=14,
        ramp="exponential",
        description="Progressive vibration and oil-temperature rise with mild power loss",
        expected_detection="Asset-specific equipment fault, escalated for inspection",
        detectable_at=0.12,
    ),
    "generator_overheating": Scenario(
        name="generator_overheating",
        label="Generator overheating",
        asset_type=AssetType.WIND_TURBINE,
        component="generator",
        is_equipment_fault=True,
        typical_onset_days=9,
        ramp="sigmoid",
        description="Winding temperature climbs and the controller derates at high load",
        expected_detection="Asset-specific thermal fault",
    ),
    "pitch_misalignment": Scenario(
        name="pitch_misalignment",
        label="Pitch misalignment",
        asset_type=AssetType.WIND_TURBINE,
        component="pitch_system",
        is_equipment_fault=True,
        typical_onset_days=7,
        ramp="step",
        description="Power loss concentrated at mid wind speeds with no thermal signature",
        expected_detection="Aerodynamic fault distinguished from drivetrain wear by absent thermal rise",
    ),
    "yaw_misalignment": Scenario(
        name="yaw_misalignment",
        label="Yaw misalignment",
        asset_type=AssetType.WIND_TURBINE,
        component="yaw_system",
        is_equipment_fault=True,
        typical_onset_days=10,
        ramp="linear",
        description="Cosine-squared power loss correlated with wind direction",
        expected_detection="Direction-dependent loss, separable from a uniform derate",
    ),
    "string_outage": Scenario(
        name="string_outage",
        label="DC string outage",
        asset_type=AssetType.SOLAR_INVERTER,
        component="dc_string",
        is_equipment_fault=True,
        typical_onset_days=1,
        ramp="step",
        description="Step loss of DC current when strings drop offline",
        expected_detection="Step change isolated to one inverter",
        detectable_at=0.02,
    ),
    "inverter_derate": Scenario(
        name="inverter_derate",
        label="Inverter thermal derate",
        asset_type=AssetType.SOLAR_INVERTER,
        component="inverter",
        is_equipment_fault=True,
        typical_onset_days=5,
        ramp="sigmoid",
        description="Inverter temperature rises and output is clipped below rating",
        expected_detection="Asset-specific thermal fault on the AC side",
    ),
    # ---------------------------------------------------------------- not equipment faults
    "soiling_accumulation": Scenario(
        name="soiling_accumulation",
        label="Soiling accumulation",
        asset_type=AssetType.SOLAR_INVERTER,
        component="soiling",
        is_equipment_fault=False,
        typical_onset_days=21,
        ramp="linear",
        description="Dust builds on the array and washes off after rain",
        expected_detection="Recoverable loss, cleaning economics rather than a repair ticket",
        detectable_at=0.25,
    ),
    "anemometer_drift": Scenario(
        name="anemometer_drift",
        label="Anemometer drift",
        asset_type=AssetType.WIND_TURBINE,
        component="anemometer",
        is_equipment_fault=False,
        typical_onset_days=12,
        ramp="linear",
        description=(
            "The wind sensor reads progressively high, so the asset appears to underperform "
            "against its own measured wind while nothing mechanical has changed"
        ),
        expected_detection="Instrumentation fault, NOT a drivetrain alarm",
        detectable_at=0.20,
    ),
    "sensor_freeze": Scenario(
        name="sensor_freeze",
        label="Frozen sensor",
        asset_type=AssetType.WIND_TURBINE,
        component="anemometer",
        is_equipment_fault=False,
        typical_onset_days=2,
        ramp="step",
        description="A sensor holds its last value while the asset keeps operating",
        expected_detection="Data-quality fault, suppressed from equipment alarms",
        detectable_at=0.02,
    ),
    "curtailment_window": Scenario(
        name="curtailment_window",
        label="Grid curtailment",
        asset_type=AssetType.WIND_TURBINE,
        component="none",
        is_equipment_fault=False,
        typical_onset_days=1,
        ramp="step",
        description="Output capped by grid instruction",
        expected_detection="Commanded reduction, never an equipment alarm",
        detectable_at=0.02,
    ),
    "cloud_transient": Scenario(
        name="cloud_transient",
        label="Cloud transient",
        asset_type=AssetType.SOLAR_INVERTER,
        component="none",
        is_equipment_fault=False,
        typical_onset_days=1,
        ramp="step",
        description="Deep short-lived irradiance drops across the plant",
        expected_detection="Environmental, explained by irradiance",
        detectable_at=0.02,
    ),
    "icing_event": Scenario(
        name="icing_event",
        label="Blade icing",
        asset_type=AssetType.WIND_TURBINE,
        component="none",
        is_equipment_fault=False,
        typical_onset_days=2,
        ramp="sigmoid",
        description="Power loss under low temperature and high humidity",
        expected_detection="Environmental, explained by ambient conditions",
        detectable_at=0.10,
    ),
}

EQUIPMENT_SCENARIOS = [s.name for s in SCENARIOS.values() if s.is_equipment_fault]
ENVIRONMENTAL_SCENARIOS = [s.name for s in SCENARIOS.values() if not s.is_equipment_fault]


# --------------------------------------------------------------------------- severity ramp


def severity_ramp(
    index: pd.DatetimeIndex,
    onset: pd.Timestamp,
    end: pd.Timestamp,
    shape: RampShape,
    final: float,
) -> np.ndarray:
    """Severity in [0, final] over the event window, zero outside it."""
    total = (end - onset).total_seconds()
    if total <= 0:
        return np.zeros(len(index))

    # Pandas arithmetic throughout: the index is tz-aware, and numpy datetime64 has no
    # timezone representation, so converting first silently corrupts the offset.
    elapsed = (index - onset).total_seconds().to_numpy(dtype=float)
    progress = np.clip(elapsed / total, 0.0, 1.0)
    active = np.asarray(index >= onset) & np.asarray(index <= end)

    if shape == "linear":
        curve = progress
    elif shape == "exponential":
        curve = (np.exp(2.4 * progress) - 1.0) / (np.exp(2.4) - 1.0)
    elif shape == "sigmoid":
        curve = 1.0 / (1.0 + np.exp(-9.0 * (progress - 0.5)))
    else:  # step
        curve = np.where(progress > 0.0, 1.0, 0.0)

    return np.where(active, curve * final, 0.0)


def _detectable_from(
    onset: pd.Timestamp, end: pd.Timestamp, scenario: Scenario
) -> pd.Timestamp:
    return onset + (end - onset) * scenario.detectable_at


# --------------------------------------------------------------------------- modifiers

Modifier = Callable[[pd.DataFrame, Asset, SiteMet, np.ndarray, np.random.Generator], None]


def _mod_gearbox_bearing_wear(df, asset, met, s, rng) -> None:
    running = df["power_kw"] > 0
    df.loc[running, "drivetrain_vibration_mms"] *= 1.0 + 0.34 * s[running]
    df["gearbox_oil_temp_c"] += 9.0 * s
    df["main_bearing_temp_c"] += 3.2 * s
    df.loc[running, "power_kw"] *= 1.0 - 0.11 * s[running]


def _mod_generator_overheating(df, asset, met, s, rng) -> None:
    load = df["power_kw"] / asset.rated_power_kw
    df["generator_winding_temp_c"] += 21.0 * s
    df["nacelle_temp_c"] += 3.5 * s
    df["power_kw"] *= 1.0 - 0.09 * s * np.clip(load, 0.0, 1.0)


def _mod_pitch_misalignment(df, asset, met, s, rng) -> None:
    wind = df["wind_speed_ms"].to_numpy()
    # Loss concentrates where pitch control matters most, and leaves no thermal trace.
    shape = np.exp(-0.5 * ((wind - 8.5) / 3.0) ** 2)
    df["power_kw"] *= 1.0 - 0.16 * s * shape
    df["pitch_angle_deg"] += 2.6 * s


def _mod_yaw_misalignment(df, asset, met, s, rng) -> None:
    error_deg = 18.0 * s
    df["power_kw"] *= np.cos(np.radians(error_deg)) ** 2


def _mod_string_outage(df, asset, met, s, rng) -> None:
    n_strings = asset.n_strings or 20
    strings_lost = np.maximum(1, np.round(s * 3))
    fraction = np.where(s > 0, strings_lost / n_strings, 0.0)
    keep = 1.0 - fraction
    df["dc_power_kw"] *= keep
    df["dc_current_a"] *= keep
    df["ac_power_kw"] *= keep
    df["performance_ratio"] *= keep


def _mod_inverter_derate(df, asset, met, s, rng) -> None:
    df["inverter_temp_c"] += 15.0 * s
    cap = asset.rated_power_kw * (1.0 - 0.22 * s)
    df["ac_power_kw"] = np.minimum(df["ac_power_kw"], cap)
    daylight = df["poa_wm2"] > 5.0
    df.loc[daylight, "performance_ratio"] *= 1.0 - 0.18 * s[daylight]


def _mod_soiling_accumulation(df, asset, met, s, rng) -> None:
    extra_loss = 0.13 * s
    df["soiling_ratio"] *= 1.0 - extra_loss
    df["dc_power_kw"] *= 1.0 - extra_loss
    df["dc_current_a"] *= 1.0 - extra_loss
    df["ac_power_kw"] *= 1.0 - extra_loss
    df["performance_ratio"] *= 1.0 - extra_loss


def _mod_anemometer_drift(df, asset, met, s, rng) -> None:
    """Only the measurement drifts. Power, rpm and pitch stay true to the real wind.

    That inconsistency is the tell: the asset appears to underperform against its own
    reported wind speed, while every mechanical channel says it is healthy.
    """
    df["wind_speed_ms"] *= 1.0 + 0.19 * s


def _mod_sensor_freeze(df, asset, met, s, rng) -> None:
    frozen = s > 0
    if not frozen.any():
        return
    first = int(np.argmax(frozen))
    column = "wind_speed_ms" if "wind_speed_ms" in df.columns else "poa_wm2"
    held = df[column].iloc[max(first - 1, 0)]
    df.loc[frozen, column] = held


def _mod_curtailment_window(df, asset, met, s, rng) -> None:
    active = s > 0
    if not active.any():
        return
    power_col = "power_kw" if "power_kw" in df.columns else "ac_power_kw"
    cap = asset.rated_power_kw * 0.55
    df.loc[active, power_col] = np.minimum(df.loc[active, power_col], cap)
    df.loc[active, "operating_state"] = OperatingState.CURTAILED.value
    df.loc[active, "status_code"] = STATUS_CODE[OperatingState.CURTAILED]


def _mod_cloud_transient(df, asset, met, s, rng) -> None:
    active = s > 0
    if not active.any():
        return
    n = int(active.sum())
    # Multiplicative drops with short dwell, the signature of broken cumulus.
    drops = np.clip(rng.beta(1.4, 3.0, n) * 1.3, 0.0, 0.92)
    factor = 1.0 - drops
    for column in ("poa_wm2", "ghi_wm2", "dc_power_kw", "ac_power_kw", "dc_current_a"):
        if column in df.columns:
            df.loc[active, column] *= factor


def _mod_icing_event(df, asset, met, s, rng) -> None:
    active = s > 0
    df["power_kw"] *= 1.0 - 0.38 * s
    df.loc[active, "ambient_temp_c"] = np.minimum(df.loc[active, "ambient_temp_c"], 3.0)
    df.loc[active, "humidity_pct"] = np.maximum(df.loc[active, "humidity_pct"], 93.0)
    df["drivetrain_vibration_mms"] *= 1.0 + 0.09 * s


MODIFIERS: dict[str, Modifier] = {
    "gearbox_bearing_wear": _mod_gearbox_bearing_wear,
    "generator_overheating": _mod_generator_overheating,
    "pitch_misalignment": _mod_pitch_misalignment,
    "yaw_misalignment": _mod_yaw_misalignment,
    "string_outage": _mod_string_outage,
    "inverter_derate": _mod_inverter_derate,
    "soiling_accumulation": _mod_soiling_accumulation,
    "anemometer_drift": _mod_anemometer_drift,
    "sensor_freeze": _mod_sensor_freeze,
    "curtailment_window": _mod_curtailment_window,
    "cloud_transient": _mod_cloud_transient,
    "icing_event": _mod_icing_event,
}


# --------------------------------------------------------------------------- application


def apply_scenario(
    df: pd.DataFrame,
    asset: Asset,
    met: SiteMet,
    scenario_name: str,
    onset: pd.Timestamp,
    duration_days: float,
    severity: float,
    seed: int,
    event_id: str,
) -> tuple[pd.DataFrame, InjectedEvent]:
    """Apply one scenario in place on a copy, returning the frame and its ground truth."""
    if scenario_name not in SCENARIOS:
        raise KeyError(f"unknown scenario {scenario_name!r}")
    scenario = SCENARIOS[scenario_name]
    rng = child_seed(seed, "fault", asset.asset_id, scenario_name)

    index = pd.DatetimeIndex(df["ts"])
    end = onset + pd.Timedelta(days=duration_days)
    s = severity_ramp(index, onset, end, scenario.ramp, severity)

    out = df.copy()
    MODIFIERS[scenario_name](out, asset, met, s, rng)

    # Physical floors and ceilings after modification.
    for column, lo, hi in (
        ("power_kw", 0.0, asset.rated_power_kw * 1.02),
        ("ac_power_kw", 0.0, asset.rated_power_kw * 1.02),
        ("dc_power_kw", 0.0, None),
        ("dc_current_a", 0.0, None),
        ("drivetrain_vibration_mms", 0.02, None),
        ("soiling_ratio", 0.3, 1.0),
        ("performance_ratio", 0.0, 1.3),
        ("poa_wm2", 0.0, None),
        ("ghi_wm2", 0.0, None),
    ):
        if column in out.columns:
            out[column] = out[column].clip(lower=lo, upper=hi)

    event = InjectedEvent(
        event_id=event_id,
        asset_id=asset.asset_id,
        scenario=scenario_name,
        component=scenario.component,
        is_equipment_fault=scenario.is_equipment_fault,
        onset=onset.floor('s').to_pydatetime(),
        detectable_from=_detectable_from(onset, end, scenario).floor('s').to_pydatetime(),
        end=end.floor('s').to_pydatetime(),
        severity_final=float(severity),
        description=scenario.description,
    )
    return out, event


def scenario_catalog() -> list[dict]:
    """Serialisable catalogue for GET /api/simulator/scenarios."""
    return [
        {
            "scenario": s.name,
            "label": s.label,
            "asset_type": s.asset_type.value,
            "component": s.component,
            "is_equipment_fault": s.is_equipment_fault,
            "typical_onset_days": s.typical_onset_days,
            "description": s.description,
            "expected_detection": s.expected_detection,
        }
        for s in SCENARIOS.values()
    ]
