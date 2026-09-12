"""pvlib-backed clear-sky irradiance modeling and cloud stability filtering.

Computes:
1. Solar position (zenith, azimuth, airmass) for plant site coordinates.
2. Ineichen clear-sky GHI, DNI, DHI and converts to Plane-of-Array (POA) irradiance.
3. Cloud Stability Filter: Identifies and filters out highly variable, intermittent
   cloud intervals where spatial irradiance gradient would corrupt soiling estimation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
import pvlib

from rai.config import Asset
from rai.environment.weather_provider import SITE_COORDINATES

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClearSkyBaseline:
    timestamp: pd.Timestamp
    clearsky_ghi_w_m2: float
    clearsky_poa_w_m2: float
    solar_zenith_deg: float
    solar_azimuth_deg: float
    is_daylight: bool
    is_cloud_stable: bool
    uncertainty_fraction: float


def compute_clear_sky_poa(
    lat: float,
    lon: float,
    timestamps: pd.DatetimeIndex,
    tilt_deg: float = 23.0,
    azimuth_deg: float = 180.0,
) -> pd.Series:
    """Compute clear-sky plane-of-array (POA) irradiance using pvlib."""
    loc = pvlib.location.Location(latitude=lat, longitude=lon, tz="UTC")
    cs = loc.get_clearsky(timestamps, model="ineichen")

    sol_pos = loc.get_solarposition(timestamps)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt_deg,
        surface_azimuth=azimuth_deg,
        solar_zenith=sol_pos["apparent_zenith"],
        solar_azimuth=sol_pos["azimuth"],
        dni=cs["dni"],
        ghi=cs["ghi"],
        dhi=cs["dhi"],
    )
    return cast(pd.Series, poa["poa_global"].clip(lower=0.0))


def compute_clearsky_poa(
    asset: Asset,
    timestamp: pd.Timestamp,
    surface_tilt_deg: float = 23.5,
    surface_azimuth_deg: float = 180.0,
    measured_poa_window: list[float] | None = None,
) -> ClearSkyBaseline:
    """Calculate clear-sky POA irradiance using pvlib Ineichen model with cloud filtering."""
    site_key = asset.site if asset.site in SITE_COORDINATES else "charanka-solar"
    coords = SITE_COORDINATES.get(site_key, {"lat": 23.90, "lon": 71.20})
    lat, lon = coords["lat"], coords["lon"]

    # Ensure timestamp has UTC timezone
    if timestamp.tzinfo is None:
        ts_utc = timestamp.tz_localize("UTC")
    else:
        ts_utc = timestamp.tz_convert("UTC")

    location = pvlib.location.Location(latitude=lat, longitude=lon, tz="UTC", altitude=50.0)
    solar_pos = location.get_solarposition(pd.DatetimeIndex([ts_utc]))

    zenith = float(solar_pos["apparent_zenith"].iloc[0])
    azimuth = float(solar_pos["azimuth"].iloc[0])

    if zenith >= 88.0:
        # Nighttime / low sun
        return ClearSkyBaseline(
            timestamp=ts_utc,
            clearsky_ghi_w_m2=0.0,
            clearsky_poa_w_m2=0.0,
            solar_zenith_deg=zenith,
            solar_azimuth_deg=azimuth,
            is_daylight=False,
            is_cloud_stable=True,
            uncertainty_fraction=0.05,
        )

    # Ineichen clear sky model
    cs = location.get_clearsky(pd.DatetimeIndex([ts_utc]), model="ineichen")
    ghi = float(cs["ghi"].iloc[0])
    dni = float(cs["dni"].iloc[0])
    dhi = float(cs["dhi"].iloc[0])

    # Convert to Plane of Array (POA)
    poa_components = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt_deg,
        surface_azimuth=surface_azimuth_deg,
        solar_zenith=zenith,
        solar_azimuth=azimuth,
        dni=dni,
        ghi=ghi,
        dhi=dhi,
        model="haydavies",
    )
    poa_global = float(poa_components["poa_global"].iloc[0])

    # Cloud stability filter: check variance of measured POA over recent window
    is_cloud_stable = True
    uncertainty = 0.05  # baseline model uncertainty ~5%
    if measured_poa_window and len(measured_poa_window) >= 3:
        std_window = float(np.std(measured_poa_window))
        mean_window = float(np.mean(measured_poa_window))
        if mean_window > 200.0:
            cov = std_window / mean_window
            if cov > 0.25:
                # Rapid fluctuations indicate broken cloud deck
                is_cloud_stable = False
                uncertainty = min(0.35, cov)

    return ClearSkyBaseline(
        timestamp=ts_utc,
        clearsky_ghi_w_m2=round(max(0.0, ghi), 1),
        clearsky_poa_w_m2=round(max(0.0, poa_global), 1),
        solar_zenith_deg=round(zenith, 2),
        solar_azimuth_deg=round(azimuth, 2),
        is_daylight=True,
        is_cloud_stable=is_cloud_stable,
        uncertainty_fraction=round(uncertainty, 3),
    )


def filter_cloud_unstable_intervals(
    frame: pd.DataFrame,
    poa_col: str = "poa_irradiance_w_m2",
    threshold_cov: float = 0.20,
) -> pd.DataFrame:
    """Filter out intervals with high cloud variability to prevent soiling distortion."""
    if frame.empty or poa_col not in frame.columns:
        return frame

    rolling_mean = frame[poa_col].rolling(window=4, min_periods=2).mean()
    rolling_std = frame[poa_col].rolling(window=4, min_periods=2).std()
    cov = rolling_std / (rolling_mean + 1e-3)

    stable_mask = (cov <= threshold_cov) | (frame[poa_col] < 50.0)
    return frame[stable_mask].copy()
