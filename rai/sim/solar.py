"""PV inverter telemetry generation.

Standard performance chain: plane-of-array irradiance drives DC output, module temperature
derates it, soiling scales it, then an efficiency curve and AC clipping give inverter output.

Soiling is modelled as a state that accumulates with airborne dust and resets when rain
exceeds a washing threshold. That history is what makes soiling separable from genuine
module degradation — one recovers after rain, the other does not — and separating them is
the question the solar side of this system exists to answer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rai.config import (
    MODULE_NOCT,
    PV_TEMP_COEFF_PMAX,
    STC_CELL_TEMP,
    STC_IRRADIANCE,
    Asset,
)
from rai.schemas import OperatingState
from rai.sim.met import (
    RAIN_CLEANING_MM,
    STATUS_CODE,
    SiteMet,
    child_seed,
    daily_rain_mm,
    first_order_lag,
)

SOLAR_COLUMNS = [
    "ts",
    "asset_id",
    "ghi_wm2",
    "poa_wm2",
    "ambient_temp_c",
    "module_temp_c",
    "wind_speed_ms",
    "ac_power_kw",
    "dc_power_kw",
    "dc_voltage_v",
    "dc_current_a",
    "inverter_temp_c",
    "performance_ratio",
    "soiling_ratio",
    "status_code",
    "operating_state",
]

NIGHT_POA_THRESHOLD = 5.0  # W/m^2 below which the plant is considered dark
NOMINAL_MPPT_VOLTAGE = 620.0
SOILING_BASE_RATE_PER_DAY = 0.0022  # fraction of output lost per day at unit dust load


def module_temperature(
    poa: np.ndarray, ambient: np.ndarray, wind_speed: np.ndarray
) -> np.ndarray:
    """NOCT model with a wind-cooling term."""
    rise = (MODULE_NOCT - 20.0) / 800.0 * poa
    cooling = 1.0 / (1.0 + 0.06 * np.clip(wind_speed, 0.0, 20.0))
    return ambient + rise * cooling


def inverter_efficiency(load_fraction: np.ndarray) -> np.ndarray:
    """Rises steeply from zero then plateaus near 98%, as real inverters do."""
    x = np.clip(load_fraction, 0.0, 1.4)
    eff = 0.982 * (1.0 - np.exp(-14.0 * x)) - 0.016 * x
    return np.clip(eff, 0.0, 0.985)


def soiling_series(
    dust_aod: np.ndarray,
    precip_mm: np.ndarray,
    index: pd.DatetimeIndex,
    rate_scale: float,
) -> np.ndarray:
    """Soiling ratio in (0, 1]: accumulates with dust, resets after a washing rain."""
    daily_rain = daily_rain_mm(index, precip_mm)
    steps_per_day = len(index) / max((index[-1] - index[0]).total_seconds() / 86400.0, 1e-9)
    per_step = SOILING_BASE_RATE_PER_DAY * rate_scale / max(steps_per_day / 1.0, 1e-9)

    ratio = np.empty(len(index))
    current = 1.0
    dust_norm = np.clip(dust_aod / max(float(np.nanmean(dust_aod)) or 1.0, 1e-6), 0.0, 4.0)
    for i in range(len(index)):
        if daily_rain[i] >= RAIN_CLEANING_MM:
            # Heavy rain washes the array most of the way back to clean.
            current = min(1.0, current + 0.55 * (1.0 - current) + 0.35 * (1.0 - current))
            current = min(1.0, 1.0 - (1.0 - current) * 0.25)
        else:
            current = max(0.60, current - per_step * dust_norm[i])
        ratio[i] = current
    return ratio


def simulate_inverter(asset: Asset, met: SiteMet, seed: int) -> pd.DataFrame:
    """Generate healthy 15-minute telemetry for one inverter."""
    rng = child_seed(seed, "solar", asset.asset_id)
    index = met.index
    n = len(index)

    ghi = met.col("ghi_wm2")
    poa_site = met.col("poa_wm2")
    ambient = met.col("ambient_temp_c")
    wind_speed = met.col("wind_speed_ms")
    dust = met.col("dust_aod")
    precip = met.col("precip_mm")
    curtail_cap = met.col("curtail_cap_frac")

    # Per-inverter irradiance differences: row position, mounting tolerance, local shading.
    poa_gain = float(rng.normal(1.0, 0.012))
    poa = np.clip(poa_site * poa_gain, 0.0, None)

    dc_capacity = asset.dc_capacity_kw or asset.rated_power_kw * 1.25
    rated_ac = asset.rated_power_kw

    soiling = soiling_series(dust, precip, index, rate_scale=float(rng.uniform(0.8, 1.25)))
    module_temp = module_temperature(poa, ambient, wind_speed) + float(rng.normal(0.0, 0.6))

    temp_derate = 1.0 + PV_TEMP_COEFF_PMAX * (module_temp - STC_CELL_TEMP)
    array_health = float(rng.normal(1.0, 0.012))  # module binning and mismatch

    dc_power = dc_capacity * (poa / STC_IRRADIANCE) * temp_derate * soiling * array_health
    dc_power = np.clip(dc_power + rng.normal(0.0, 0.35, n), 0.0, None)

    efficiency = inverter_efficiency(dc_power / max(rated_ac, 1e-6))
    ac_power = np.minimum(dc_power * efficiency, rated_ac)

    night = poa < NIGHT_POA_THRESHOLD
    dc_power[night] = 0.0
    ac_power[night] = 0.0

    state = np.full(n, OperatingState.NORMAL.value, dtype=object)
    state[night] = OperatingState.NIGHT.value

    curtailed = np.isfinite(curtail_cap) & ~night
    if curtailed.any():
        cap_kw = curtail_cap * rated_ac
        hit = curtailed & (ac_power > cap_kw)
        ac_power = np.where(hit, cap_kw, ac_power)
        state[hit] = OperatingState.CURTAILED.value

    # DC electrical quantities consistent with P = V * I.
    voltage = np.where(
        night,
        0.0,
        NOMINAL_MPPT_VOLTAGE * (1.0 - 0.0028 * (module_temp - STC_CELL_TEMP))
        + rng.normal(0.0, 1.6, n),
    )
    voltage = np.clip(voltage, 0.0, None)
    current = np.divide(
        dc_power * 1000.0, voltage, out=np.zeros_like(dc_power), where=voltage > 1.0
    )

    inverter_load = first_order_lag(
        ac_power / max(rated_ac, 1e-6), tau_min=25.0, dt_min=met.interval_min
    )
    inverter_temp = ambient + 17.0 * inverter_load + rng.normal(0.0, 0.5, n)

    # Performance ratio: actual yield against irradiance-referenced nameplate yield.
    reference = dc_capacity * (poa / STC_IRRADIANCE)
    performance_ratio = np.divide(
        ac_power, reference, out=np.full(n, np.nan), where=reference > 0.02 * dc_capacity
    )

    df = pd.DataFrame(
        {
            "ts": index,
            "asset_id": asset.asset_id,
            "ghi_wm2": ghi,
            "poa_wm2": poa,
            "ambient_temp_c": ambient,
            "module_temp_c": np.where(night, ambient, module_temp),
            "wind_speed_ms": wind_speed,
            "ac_power_kw": ac_power,
            "dc_power_kw": dc_power,
            "dc_voltage_v": voltage,
            "dc_current_a": current,
            "inverter_temp_c": inverter_temp,
            "performance_ratio": performance_ratio,
            "soiling_ratio": soiling,
        }
    )
    df["operating_state"] = state
    df["status_code"] = [STATUS_CODE[OperatingState(s)] for s in state]
    return df[SOLAR_COLUMNS]


def expected_dc_power(
    poa: np.ndarray, module_temp: np.ndarray, dc_capacity_kw: float
) -> np.ndarray:
    """Clean-array expected DC power, the denominator of the soiling ratio."""
    temp_derate = 1.0 + PV_TEMP_COEFF_PMAX * (np.asarray(module_temp) - STC_CELL_TEMP)
    return dc_capacity_kw * (np.asarray(poa) / STC_IRRADIANCE) * temp_derate
