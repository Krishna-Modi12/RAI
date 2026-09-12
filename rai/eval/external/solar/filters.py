"""Solar Operational Telemetry Quality & Hazard Filters.

Implements audited Gate 5.5 data quality hazard policies:
1. Nighttime zero filtering (elevation <= 5 deg, POA < 20 W/m^2).
2. Inverter clipping detection (actual power >= 98% rated and POA > 800 W/m^2).
3. Grid curtailment state tracking.
4. Data gap tagging (> 30 min / NaN values) without illegal forward-fill across day/night.
5. Pyranometer sensor consistency cross-checks against clear-sky envelopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
import pvlib

from rai.eval.external.solar.pvdaq import PVDAQSystemMetadata


class QualityState(str, Enum):
    """Operational data quality state."""

    VALID_DAYTIME = "VALID_DAYTIME"
    NIGHTTIME = "NIGHTTIME"
    CLIPPING = "CLIPPING"
    CURTAILED = "CURTAILED"
    DATA_GAP = "DATA_GAP"
    SENSOR_ANOMALY = "SENSOR_ANOMALY"


@dataclass(frozen=True)
class QualityFilterResult:
    """Summary of data points filtered or tagged by quality rules."""

    total_records: int
    valid_daytime_count: int
    nighttime_filtered_count: int
    clipping_tagged_count: int
    curtailed_tagged_count: int
    data_gap_count: int
    sensor_anomaly_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "valid_daytime_count": self.valid_daytime_count,
            "nighttime_filtered_count": self.nighttime_filtered_count,
            "clipping_tagged_count": self.clipping_tagged_count,
            "curtailed_tagged_count": self.curtailed_tagged_count,
            "data_gap_count": self.data_gap_count,
            "sensor_anomaly_count": self.sensor_anomaly_count,
            "valid_daytime_pct": round(
                (self.valid_daytime_count / max(self.total_records, 1)) * 100.0, 2
            ),
        }


def apply_quality_filters(
    df: pd.DataFrame,
    meta: PVDAQSystemMetadata,
    min_elevation_deg: float = 5.0,
    min_poa_wm2: float = 20.0,
    max_poa_wm2: float = 1500.0,
    clipping_fraction: float = 0.98,
    clipping_min_poa_wm2: float = 800.0,
) -> tuple[pd.DataFrame, QualityFilterResult]:
    """Apply deterministic data quality filtering and state assignment.

    Returns:
        pd.DataFrame with added columns:
            quality_state, is_valid_daytime, is_clipping, is_curtailed, is_gap
        QualityFilterResult with counts.
    """
    out = df.copy()
    n = len(out)

    # 1. Identify Data Gaps (NaN in critical measurements)
    is_gap = (
        out["is_data_gap"]
        | out["poa_wm2"].isna()
        | out["ac_power_kw"].isna()
        | out["ambient_temp_c"].isna()
    ).to_numpy()

    # 2. Nighttime identification
    # Safe handling of NaNs in poa_wm2
    poa_clean = out["poa_wm2"].fillna(0.0).to_numpy()
    elev_clean = out["solar_elevation_deg"].fillna(-90.0).to_numpy()

    is_night = (elev_clean <= min_elevation_deg) | (poa_clean < min_poa_wm2)
    # Don't tag true gaps as merely nighttime
    is_night = is_night & (~is_gap)

    # 3. Sensor anomaly check (unphysical POA or GHI > 1500 W/m^2)
    is_sensor_anomaly = (poa_clean > max_poa_wm2) & (~is_gap)

    # 4. Inverter Clipping Detection
    # If AC power approaches nominal rating under high irradiance
    ac_clean = out["ac_power_kw"].fillna(0.0).to_numpy()
    rated_ac = meta.rated_ac_kw
    is_clipping = (
        (ac_clean >= (clipping_fraction * rated_ac))
        & (poa_clean >= clipping_min_poa_wm2)
        & (~is_night)
        & (~is_gap)
    )

    # 5. Curtailment
    is_curtailed = out["is_curtailed_flag"].fillna(False).to_numpy() & (~is_night) & (~is_gap)

    # 6. Primary Quality State Assignment
    # Priority: DATA_GAP > SENSOR_ANOMALY > NIGHTTIME > CURTAILED > CLIPPING > VALID_DAYTIME
    states = np.full(n, QualityState.VALID_DAYTIME.value, dtype=object)
    states[is_clipping] = QualityState.CLIPPING.value
    states[is_curtailed] = QualityState.CURTAILED.value
    states[is_sensor_anomaly] = QualityState.SENSOR_ANOMALY.value
    states[is_night] = QualityState.NIGHTTIME.value
    states[is_gap] = QualityState.DATA_GAP.value

    # Valid daytime means neither night, gap, nor sensor anomaly
    # Note: Clipping and Curtailed are still daytime data, but tagged for regime analysis
    is_valid_daytime = (~is_night) & (~is_gap) & (~is_sensor_anomaly)

    out["quality_state"] = states
    out["is_valid_daytime"] = is_valid_daytime
    out["is_clipping"] = is_clipping
    out["is_curtailed"] = is_curtailed
    out["is_gap"] = is_gap

    res = QualityFilterResult(
        total_records=n,
        valid_daytime_count=int(np.sum(is_valid_daytime)),
        nighttime_filtered_count=int(np.sum(is_night)),
        clipping_tagged_count=int(np.sum(is_clipping)),
        curtailed_tagged_count=int(np.sum(is_curtailed)),
        data_gap_count=int(np.sum(is_gap)),
        sensor_anomaly_count=int(np.sum(is_sensor_anomaly)),
    )

    return out, res


def verify_clearsky_consistency(
    times: pd.DatetimeIndex,
    poa_measured: np.ndarray,
    meta: PVDAQSystemMetadata,
    tolerance_factor: float = 1.35,
) -> np.ndarray:
    """Check if measured POA is within realistic atmospheric clear-sky limits.

    Returns boolean mask of physically plausible irradiance.
    """
    site = pvlib.location.Location(meta.latitude, meta.longitude, tz="UTC", altitude=meta.altitude_m)
    solpos = site.get_solarposition(times)
    cs = site.get_clearsky(times, model="ineichen")

    dni_extra = pvlib.irradiance.get_extra_radiation(times).to_numpy()
    poa_cs_res = pvlib.irradiance.get_total_irradiance(
        surface_tilt=meta.tilt_deg,
        surface_azimuth=meta.azimuth_deg,
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=cs["dni"],
        ghi=cs["ghi"],
        dhi=cs["dhi"],
        dni_extra=dni_extra,
        model="perez",
    )
    poa_cs = np.nan_to_num(np.asarray(poa_cs_res["poa_global"]), nan=0.0)

    # Cloud enhancement can boost ground irradiance up to ~1.35x clear sky temporarily
    max_allowable = np.maximum(poa_cs * tolerance_factor, 50.0)
    return poa_measured <= max_allowable
