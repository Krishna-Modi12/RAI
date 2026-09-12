"""Wind turbine telemetry generation.

Power comes from the actual aerodynamic relation rather than a lookup table:

    P = 0.5 * rho * A * Cp(v) * v^3,  capped at rated

Air density enters the physics directly, so density correction is a property of the model
instead of a patch applied afterwards. Cp peaks near the design tip-speed ratio and falls
away on either side; above rated the controller pitches to hold power flat.

Component temperatures use a first-order thermal lag driven by filtered load, not an
instantaneous function of it. That choice matters downstream: a normal-behaviour model for
gearbox oil temperature has to learn load *history*, which is what makes a thermal residual
a meaningful degradation signal rather than a restatement of current power.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rai.config import STANDARD_AIR_DENSITY, Asset
from rai.schemas import OperatingState
from rai.sim.met import (
    STATUS_CODE,
    SiteMet,
    angular_diff_deg,
    child_seed,
    first_order_lag,
    ou_process,
)

WIND_COLUMNS = [
    "ts",
    "asset_id",
    "wind_speed_ms",
    "wind_direction_deg",
    "ambient_temp_c",
    "pressure_hpa",
    "humidity_pct",
    "air_density",
    "power_kw",
    "rotor_rpm",
    "pitch_angle_deg",
    "nacelle_temp_c",
    "gearbox_oil_temp_c",
    "generator_winding_temp_c",
    "main_bearing_temp_c",
    "drivetrain_vibration_mms",
    "status_code",
    "operating_state",
]

CP_MAX = 0.45
CP_PEAK_MS = 8.0
CP_SPREAD_MS = 4.5

# Thermal model: per-component ambient rise at full load, and lag time constant in minutes.
THERMAL = {
    "gearbox_oil_temp_c": {"rise_k": 38.0, "tau_min": 42.0, "noise": 0.45},
    "generator_winding_temp_c": {"rise_k": 62.0, "tau_min": 18.0, "noise": 0.70},
    "main_bearing_temp_c": {"rise_k": 26.0, "tau_min": 55.0, "noise": 0.35},
    "nacelle_temp_c": {"rise_k": 14.0, "tau_min": 30.0, "noise": 0.40},
}

# Row B sits in row A's wake for winds arriving from the prevailing sector.
WAKE_CENTRE_DEG = 250.0
WAKE_HALF_WIDTH_DEG = 42.0
WAKE_MAX_DEFICIT = 0.13


def power_coefficient(wind_speed: np.ndarray) -> np.ndarray:
    """Cp(v): peaks near the design tip-speed ratio, falls away on either side."""
    return CP_MAX * np.exp(-0.5 * ((wind_speed - CP_PEAK_MS) / CP_SPREAD_MS) ** 2)


def theoretical_power_kw(
    wind_speed: np.ndarray,
    air_density: np.ndarray,
    rotor_diameter_m: float,
    rated_kw: float,
    cut_in_ms: float,
    cut_out_ms: float,
    rated_ms: float = 12.5,
) -> np.ndarray:
    """Electrical power for the given conditions.

    Below rated wind speed the turbine extracts what the wind offers, so density enters
    directly. At and above rated the controller pitches to shed surplus energy and holds
    rated power flat to cut-out — the plateau is a control decision, not an aerodynamic
    limit, so it must be modelled as a cap rather than as a falling Cp.
    """
    wind_speed = np.asarray(wind_speed, dtype=float)
    air_density = np.asarray(air_density, dtype=float)
    swept_area = np.pi * (rotor_diameter_m / 2.0) ** 2
    available = 0.5 * air_density * swept_area * power_coefficient(wind_speed) * wind_speed**3
    power = np.clip(available / 1000.0, 0.0, rated_kw)

    # Density still matters above rated: a thin-air day reaches rated slightly later.
    density_ratio = np.clip(air_density / STANDARD_AIR_DENSITY, 0.85, 1.15)
    at_rated = wind_speed >= (rated_ms / np.cbrt(density_ratio))
    power = np.where(at_rated, rated_kw, power)

    power = np.where((wind_speed < cut_in_ms) | (wind_speed >= cut_out_ms), 0.0, power)
    return power


def wake_deficit(direction_deg: np.ndarray, in_wake: bool) -> np.ndarray:
    """Direction-dependent wake loss fraction for downstream turbines.

    Peer comparison would be trivial if every turbine saw identical wind. The wake makes
    row B genuinely lower-yielding than row A under prevailing winds, so a useful peer
    engine has to compare against the right peer group rather than the whole site.
    """
    if not in_wake:
        return np.zeros_like(direction_deg)
    offset = np.abs(angular_diff_deg(direction_deg, WAKE_CENTRE_DEG))
    shape = np.clip(1.0 - (offset / WAKE_HALF_WIDTH_DEG) ** 2, 0.0, 1.0)
    return WAKE_MAX_DEFICIT * shape


def simulate_turbine(asset: Asset, met: SiteMet, seed: int) -> pd.DataFrame:
    """Generate healthy 10-minute telemetry for one turbine. Faults are applied afterwards."""
    rng = child_seed(seed, "wind", asset.asset_id)
    index = met.index
    n = len(index)

    wind_site = met.col("wind_speed_ms")
    direction = met.col("wind_direction_deg")
    ambient = met.col("ambient_temp_c")
    pressure = met.col("pressure_hpa")
    humidity = met.col("humidity_pct")
    density = met.col("air_density")
    curtail_cap = met.col("curtail_cap_frac")

    # Per-turbine wind: local terrain offset plus turbulence that is coherent in time.
    terrain_gain = float(rng.normal(1.0, 0.025))
    turbulence = ou_process(n, tau_steps=3.0, sigma=0.32, rng=rng)
    wind = np.clip(wind_site * terrain_gain + turbulence, 0.0, None)

    in_wake = asset.peer_group.endswith("row-b")
    wind = wind * (1.0 - wake_deficit(direction, in_wake))

    cut_in = asset.cut_in_ms or 3.0
    cut_out = asset.cut_out_ms or 25.0
    rated_ms = asset.rated_ms or 12.5
    rated_kw = asset.rated_power_kw

    power = theoretical_power_kw(
        wind, density, asset.rotor_diameter_m or 92.0, rated_kw, cut_in, cut_out, rated_ms
    )

    # Turbine-specific conversion efficiency: real fleets are not identical machines.
    efficiency = float(rng.normal(1.0, 0.018))
    power = power * efficiency
    power = np.clip(power + rng.normal(0.0, 6.0, n), 0.0, rated_kw * 1.02)

    state = np.full(n, OperatingState.NORMAL.value, dtype=object)
    state[wind < cut_in] = OperatingState.BELOW_CUTIN.value
    state[wind >= cut_out] = OperatingState.ABOVE_CUTOUT.value
    power[wind < cut_in] = 0.0
    power[wind >= cut_out] = 0.0

    # Scheduled maintenance: a handful of daylight stoppages across the window.
    per_day = int(round(24 * 60 / met.interval_min))
    for _ in range(int(rng.integers(1, 4))):
        start = int(rng.integers(0, max(n - per_day, 1)))
        span = int(rng.integers(per_day // 8, per_day // 3))
        power[start : start + span] = 0.0
        state[start : start + span] = OperatingState.MAINTENANCE.value

    # Grid curtailment, applied site-wide so the peer layer can recognise it.
    curtailed = np.isfinite(curtail_cap)
    if curtailed.any():
        cap_kw = curtail_cap * rated_kw
        hit = curtailed & (power > cap_kw)
        power = np.where(hit, cap_kw, power)
        state[hit] = OperatingState.CURTAILED.value

    load = power / rated_kw

    rotor_rpm = np.where(
        power > 0,
        np.clip(6.0 + 10.5 * np.clip(wind / rated_ms, 0.0, 1.0), 0.0, 16.5),
        0.0,
    ) + rng.normal(0.0, 0.08, n)
    rotor_rpm = np.clip(rotor_rpm, 0.0, None)

    pitch = np.where(wind > rated_ms, np.clip((wind - rated_ms) * 2.4, 0.0, 28.0), 0.6)
    pitch = np.clip(pitch + rng.normal(0.0, 0.15, n), -1.0, 30.0)

    frame = {
        "ts": index,
        "asset_id": asset.asset_id,
        "wind_speed_ms": wind,
        "wind_direction_deg": direction,
        "ambient_temp_c": ambient,
        "pressure_hpa": pressure,
        "humidity_pct": humidity,
        "air_density": density,
        "power_kw": power,
        "rotor_rpm": rotor_rpm,
        "pitch_angle_deg": pitch,
    }

    for column, spec in THERMAL.items():
        lagged = first_order_lag(load, tau_min=spec["tau_min"], dt_min=met.interval_min)
        frame[column] = (
            ambient
            + spec["rise_k"] * lagged
            + rng.normal(0.0, spec["noise"], n)
            + float(rng.normal(0.0, 0.8))  # per-turbine sensor offset
        )

    # Vibration tracks rotational speed and load; this is the channel degradation shows in.
    vibration_load = first_order_lag(load, tau_min=20.0, dt_min=met.interval_min)
    frame["drivetrain_vibration_mms"] = np.clip(
        0.55
        + 1.75 * vibration_load
        + 0.085 * rotor_rpm
        + rng.normal(0.0, 0.09, n)
        + float(rng.normal(0.0, 0.06)),
        0.05,
        None,
    )

    df = pd.DataFrame(frame)
    df["operating_state"] = state
    df["status_code"] = [STATUS_CODE[OperatingState(s)] for s in state]

    stopped = df["operating_state"].isin(
        [
            OperatingState.MAINTENANCE.value,
            OperatingState.BELOW_CUTIN.value,
            OperatingState.ABOVE_CUTOUT.value,
        ]
    )
    df.loc[stopped, "drivetrain_vibration_mms"] *= 0.28
    df.loc[stopped, "rotor_rpm"] = np.where(
        df.loc[stopped, "operating_state"] == OperatingState.BELOW_CUTIN.value, 0.0, 0.0
    )

    return df[WIND_COLUMNS]


def expected_power_reference(
    wind_speed: np.ndarray, air_density: np.ndarray, asset: Asset
) -> np.ndarray:
    """Density-corrected reference power curve, used by the physics baseline model."""
    return theoretical_power_kw(
        np.asarray(wind_speed, dtype=float),
        np.asarray(air_density, dtype=float),
        asset.rotor_diameter_m or 92.0,
        asset.rated_power_kw,
        asset.cut_in_ms or 3.0,
        asset.cut_out_ms or 25.0,
        asset.rated_ms or 12.5,
    )


def reference_air_density() -> float:
    return STANDARD_AIR_DENSITY
