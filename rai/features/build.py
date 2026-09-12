"""Feature engineering and the split policy.

Two rules govern everything here, and both exist to stop the models from cheating:

1. **No future leakage.** Every feature at time *t* is computed from data at or before *t*.
   Rolling windows are trailing, lags are backwards, and no fault label or maintenance record
   ever enters a feature.
2. **Time-ordered splits only.** Telemetry is autocorrelated, so a random split puts a sample
   from 10:00 in train and its near-twin from 10:10 in test, which inflates every score.
   Splits here are strictly chronological, and the training window additionally excludes
   every interval at or after an injected fault onset — a normal-behaviour model must never
   see the abnormal behaviour it is meant to flag.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from rai.config import Asset, get_asset
from rai.schemas import AssetType, OperatingState

# Operating states in which the asset is producing under its own control. Everything else is
# excluded from normal-behaviour training: a stopped turbine is not an underperforming one.
PRODUCTIVE_STATES = {OperatingState.NORMAL.value, OperatingState.DERATED.value}

WIND_TARGET = "power_kw"
SOLAR_TARGET = "ac_power_kw"

THERMAL_TARGETS = [
    "gearbox_oil_temp_c",
    "generator_winding_temp_c",
    "main_bearing_temp_c",
]

# Trailing windows in minutes; the thermal models need load history because component
# temperature follows a first-order lag rather than instantaneous load.
LOAD_LAGS_MIN = [30, 60, 180]
LOAD_WINDOWS_MIN = [60, 180, 360]


@dataclass(frozen=True)
class Split:
    train_end: pd.Timestamp
    val_end: pd.Timestamp
    start: pd.Timestamp
    end: pd.Timestamp

    def describe(self) -> dict[str, str]:
        return {
            "policy": "time_ordered_healthy_prefix",
            "train": f"{self.start:%Y-%m-%d}..{self.train_end:%Y-%m-%d}",
            "validation": f"{self.train_end:%Y-%m-%d}..{self.val_end:%Y-%m-%d}",
            "test": f"{self.val_end:%Y-%m-%d}..{self.end:%Y-%m-%d}",
        }


def chronological_split(
    index: pd.DatetimeIndex, train_frac: float = 0.6, val_frac: float = 0.2
) -> Split:
    """Split a timeline by position in time, never at random."""
    start, end = index.min(), index.max()
    span = end - start
    return Split(
        start=start,
        train_end=start + span * train_frac,
        val_end=start + span * (train_frac + val_frac),
        end=end,
    )


def _steps(minutes: int, interval_min: float) -> int:
    return max(int(round(minutes / interval_min)), 1)


def infer_interval_min(df: pd.DataFrame) -> float:
    deltas = df["ts"].diff().dropna()
    if deltas.empty:
        return 10.0
    return float(deltas.median().total_seconds() / 60.0)


def clean(df: pd.DataFrame, asset: Asset) -> pd.DataFrame:
    """Drop physically impossible values before anything downstream sees them."""
    out = df.copy()
    limits: dict[str, tuple[float, float]] = {
        "wind_speed_ms": (0.0, 40.0),
        "wind_direction_deg": (0.0, 360.0),
        "ambient_temp_c": (-20.0, 60.0),
        "humidity_pct": (0.0, 100.0),
        "pressure_hpa": (850.0, 1100.0),
        "air_density": (0.9, 1.5),
        "power_kw": (-50.0, asset.rated_power_kw * 1.15),
        "ac_power_kw": (-5.0, asset.rated_power_kw * 1.15),
        "dc_power_kw": (-5.0, (asset.dc_capacity_kw or asset.rated_power_kw * 1.25) * 1.2),
        "rotor_rpm": (0.0, 25.0),
        "drivetrain_vibration_mms": (0.0, 40.0),
        "poa_wm2": (0.0, 1400.0),
        "ghi_wm2": (0.0, 1400.0),
        "performance_ratio": (0.0, 1.4),
        "soiling_ratio": (0.2, 1.05),
    }
    for column, (lo, hi) in limits.items():
        if column in out.columns:
            out.loc[(out[column] < lo) | (out[column] > hi), column] = np.nan

    for column in ("gearbox_oil_temp_c", "generator_winding_temp_c", "main_bearing_temp_c"):
        if column in out.columns and "ambient_temp_c" in out.columns:
            # A component colder than ambient under load is a sensor fault, not physics.
            impossible = out[column] < out["ambient_temp_c"] - 8.0
            out.loc[impossible, column] = np.nan
    return out


def productive_mask(df: pd.DataFrame) -> pd.Series:
    """Rows where the asset was actually producing under its own control."""
    mask = df["operating_state"].isin(PRODUCTIVE_STATES)
    target = WIND_TARGET if WIND_TARGET in df.columns else SOLAR_TARGET
    return mask & df[target].notna() & (df[target] > 0)


def build_features(df: pd.DataFrame, asset: Asset) -> pd.DataFrame:
    """Add model features. All windows are trailing, so nothing reads the future."""
    out = clean(df, asset)
    interval = infer_interval_min(out)
    out = out.sort_values("ts").reset_index(drop=True)

    local = out["ts"].dt.tz_convert("Asia/Kolkata")
    out["hour"] = local.dt.hour + local.dt.minute / 60.0
    out["day_of_year"] = local.dt.dayofyear
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24.0)
    out["doy_sin"] = np.sin(2 * np.pi * out["day_of_year"] / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * out["day_of_year"] / 365.25)

    if asset.asset_type is AssetType.WIND_TURBINE:
        direction = np.radians(out["wind_direction_deg"].to_numpy(dtype=float))
        out["dir_sin"] = np.sin(direction)
        out["dir_cos"] = np.cos(direction)
        out["wind_speed_cubed"] = out["wind_speed_ms"] ** 3
        out["wind_power_density"] = 0.5 * out["air_density"] * out["wind_speed_cubed"]
        speed = out["wind_speed_ms"]
        for minutes in (60, 180):
            out[f"wind_mean_{minutes}m"] = speed.rolling(
                _steps(minutes, interval), min_periods=2
            ).mean()
        out["wind_std_60m"] = speed.rolling(_steps(60, interval), min_periods=2).std()
        out["turbulence_intensity"] = out["wind_std_60m"] / out["wind_mean_60m"].replace(0, np.nan)
        load = out["power_kw"] / asset.rated_power_kw
    else:
        out["poa_clipped"] = out["poa_wm2"].clip(lower=0.0)
        out["temp_derate"] = 1.0 - 0.004 * (out["module_temp_c"] - 25.0)
        out["poa_temp_product"] = out["poa_clipped"] * out["temp_derate"]
        for minutes in (60, 180):
            out[f"poa_mean_{minutes}m"] = out["poa_clipped"].rolling(
                _steps(minutes, interval), min_periods=2
            ).mean()
        out["poa_std_60m"] = out["poa_clipped"].rolling(_steps(60, interval), min_periods=2).std()
        # High irradiance variability means broken cloud, which explains scattered dips.
        out["irradiance_variability"] = out["poa_std_60m"] / out["poa_mean_60m"].replace(0, np.nan)
        load = out["ac_power_kw"] / asset.rated_power_kw

    out["load_fraction"] = load
    for minutes in LOAD_LAGS_MIN:
        out[f"load_lag_{minutes}m"] = load.shift(_steps(minutes, interval))
    for minutes in LOAD_WINDOWS_MIN:
        out[f"load_mean_{minutes}m"] = load.rolling(
            _steps(minutes, interval), min_periods=2
        ).mean()
    # Exponentially weighted load is the closest linear analogue of a thermal lag.
    out["load_ewm_60m"] = load.ewm(halflife=_steps(60, interval), min_periods=2).mean()
    out["load_ewm_180m"] = load.ewm(halflife=_steps(180, interval), min_periods=2).mean()
    return out


def wind_power_features() -> list[str]:
    return [
        "wind_speed_ms",
        "wind_speed_cubed",
        "wind_power_density",
        "air_density",
        "dir_sin",
        "dir_cos",
        "ambient_temp_c",
        "wind_mean_60m",
        "wind_std_60m",
        "turbulence_intensity",
        "hour_sin",
        "hour_cos",
    ]


def solar_power_features() -> list[str]:
    return [
        "poa_clipped",
        "poa_temp_product",
        "module_temp_c",
        "ambient_temp_c",
        "temp_derate",
        "poa_mean_60m",
        "poa_std_60m",
        "irradiance_variability",
        "wind_speed_ms",
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
    ]


def thermal_features(asset_type: AssetType) -> list[str]:
    """Load history dominates: component temperature lags load, it does not track it."""
    base = [
        "load_fraction",
        "load_lag_30m",
        "load_lag_60m",
        "load_lag_180m",
        "load_mean_60m",
        "load_mean_180m",
        "load_mean_360m",
        "load_ewm_60m",
        "load_ewm_180m",
        "ambient_temp_c",
    ]
    if asset_type is AssetType.WIND_TURBINE:
        return [*base, "wind_speed_ms", "rotor_rpm"]
    return [*base, "poa_clipped"]


def vibration_features() -> list[str]:
    return [
        "load_fraction",
        "load_ewm_60m",
        "rotor_rpm",
        "wind_speed_ms",
        "turbulence_intensity",
        "ambient_temp_c",
    ]


def target_for(asset: Asset) -> str:
    return WIND_TARGET if asset.asset_type is AssetType.WIND_TURBINE else SOLAR_TARGET


def monitored_signals(asset_id: str) -> list[tuple[str, str]]:
    """Signals the evidence layer reports, as (column, unit)."""
    asset = get_asset(asset_id)
    if asset.asset_type is AssetType.WIND_TURBINE:
        return [
            ("power_kw", "kW"),
            ("gearbox_oil_temp_c", "°C"),
            ("generator_winding_temp_c", "°C"),
            ("main_bearing_temp_c", "°C"),
            ("drivetrain_vibration_mms", "mm/s"),
        ]
    return [
        ("ac_power_kw", "kW"),
        ("dc_power_kw", "kW"),
        ("dc_current_a", "A"),
        ("inverter_temp_c", "°C"),
        ("performance_ratio", "ratio"),
    ]
