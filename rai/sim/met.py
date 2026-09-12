"""Site meteorology: the common physical driver behind every asset's telemetry.

Three design decisions here are load-bearing for every downstream phase:

* Wind speed keeps a site-calibrated Weibull marginal, but it is generated through a
  Gaussian copula driven by an Ornstein-Uhlenbeck process, so consecutive 10-minute
  samples are autocorrelated the way real SCADA is. IID Weibull draws would make
  thermal lag meaningless and every persistence metric trivial.
* Irradiance is pvlib clear-sky modulated by a stochastic cloud field, then decomposed
  (Erbs) and transposed (Hay-Davies), so POA is physically consistent with GHI/DNI/DHI
  instead of being a scaled copy of it.
* Grid curtailment is generated at *site* level, so every asset on the site sees the same
  window. A per-asset draw would let the peer layer trivially explain it away.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pvlib import irradiance
from pvlib.location import Location
from scipy import stats
from scipy.signal import lfilter

from rai.config import AIR_GAS_CONSTANT, SITES
from rai.schemas import OperatingState

# India Standard Time offset, used only to place diurnal cycles in local solar time.
LOCAL_UTC_OFFSET_H = 5.5

SITE_MET_COLUMNS = [
    "ts",
    "site",
    "wind_speed_ms",
    "wind_direction_deg",
    "ambient_temp_c",
    "pressure_hpa",
    "humidity_pct",
    "ghi_wm2",
    "dni_wm2",
    "dhi_wm2",
    "precip_mm",
    "dust_aod",
]

# Integer status codes written to telemetry alongside the string operating_state.
STATUS_CODE: dict[OperatingState, int] = {
    OperatingState.UNKNOWN: 0,
    OperatingState.NORMAL: 1,
    OperatingState.BELOW_CUTIN: 2,
    OperatingState.ABOVE_CUTOUT: 3,
    OperatingState.STOPPED: 4,
    OperatingState.MAINTENANCE: 5,
    OperatingState.CURTAILED: 6,
    OperatingState.DERATED: 7,
    OperatingState.NIGHT: 8,
}

RAIN_CLEANING_MM = 4.0  # daily rainfall that counts as a full module wash


# ---------------------------------------------------------------------------
# Small numeric helpers shared by the wind and solar generators
# ---------------------------------------------------------------------------


def child_seed(seed: int, *labels: str) -> np.random.Generator:
    """Deterministic per-entity RNG. `hash()` is salted per process, crc32 is not."""
    entropy = [int(seed)] + [int(zlib.crc32(label.encode("utf-8"))) for label in labels]
    return np.random.default_rng(np.random.SeedSequence(entropy))


def wrap_deg(angle: np.ndarray | float) -> np.ndarray | float:
    return np.mod(angle, 360.0)


def angular_diff_deg(a: np.ndarray | float, b: np.ndarray | float) -> np.ndarray | float:
    """Signed smallest difference a - b, in (-180, 180]."""
    return (np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0


def circular_mean_deg(angles: np.ndarray) -> float:
    a = np.deg2rad(np.asarray(angles, dtype=float))
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    return float(np.rad2deg(np.arctan2(np.sin(a).mean(), np.cos(a).mean())) % 360.0)


def ou_process(
    n: int,
    tau_steps: float,
    rng: np.random.Generator,
    sigma: float = 1.0,
) -> np.ndarray:
    """Unit-variance AR(1) / discretised Ornstein-Uhlenbeck series of length n."""
    if n <= 0:
        return np.zeros(0)
    phi = float(np.exp(-1.0 / max(tau_steps, 1e-6)))
    innov_sd = float(np.sqrt(max(1.0 - phi * phi, 1e-12)))
    eps = rng.standard_normal(n) * innov_sd
    out = lfilter([1.0], [1.0, -phi], eps, zi=[phi * rng.standard_normal()])[0]
    return np.asarray(out) * sigma


def first_order_lag(
    x: np.ndarray,
    tau_min: float,
    dt_min: float,
    x0: float | None = None,
) -> np.ndarray:
    """Exponential (first-order) lag filter: y[k] = y[k-1] + a*(x[k] - y[k-1])."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x.copy()
    alpha = 1.0 - float(np.exp(-dt_min / max(tau_min, 1e-6)))
    y_init = float(x[0]) if x0 is None else float(x0)
    zi = [(1.0 - alpha) * y_init]
    out = lfilter([alpha], [1.0, -(1.0 - alpha)], x, zi=zi)[0]
    return np.asarray(out)


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def monsoon_weight(doy: np.ndarray) -> np.ndarray:
    """Gujarat south-west monsoon envelope: peaks late July, negligible by November."""
    d = np.asarray(doy, dtype=float)
    return np.exp(-0.5 * ((d - 210.0) / 38.0) ** 2)


def local_hour(index: pd.DatetimeIndex) -> np.ndarray:
    utc_hour = index.hour.to_numpy() + index.minute.to_numpy() / 60.0
    return np.mod(utc_hour + LOCAL_UTC_OFFSET_H, 24.0)


# ---------------------------------------------------------------------------
# Site meteorology
# ---------------------------------------------------------------------------


@dataclass
class SiteMet:
    """Canonical site weather plus derived fields the asset models need.

    `frame` holds exactly the persisted site_met columns. `extras` holds quantities that
    are derived from them (POA, air density, solar geometry, curtailment windows) and are
    deliberately *not* persisted, so the parquet schema stays frozen.
    """

    site: str
    interval_min: int
    index: pd.DatetimeIndex
    frame: pd.DataFrame
    extras: pd.DataFrame

    @property
    def dt_min(self) -> float:
        return float(self.interval_min)

    def col(self, name: str) -> np.ndarray:
        if name in self.frame.columns:
            return self.frame[name].to_numpy(dtype=float)
        return self.extras[name].to_numpy(dtype=float)


def _rain_series(
    index: pd.DatetimeIndex,
    interval_min: int,
    monsoon: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Poisson rain events, monsoon-weighted, spread over consecutive intervals."""
    n = len(index)
    precip = np.zeros(n)
    per_day = round(24 * 60 / interval_min)
    days = pd.Series(index.normalize()).unique()
    for day in days:
        mask = index.normalize() == day
        pos = np.flatnonzero(mask)
        if pos.size == 0:
            continue
        w = float(monsoon[pos].mean())
        p_rain = 0.015 + 0.45 * w
        if rng.random() > p_rain:
            continue
        total_mm = float(rng.gamma(shape=1.25, scale=9.0))
        # Convective rain in Gujarat clusters in the afternoon and overnight.
        start_frac = float(rng.choice([0.55, 0.70, 0.05], p=[0.45, 0.35, 0.20]))
        start = pos[0] + int(start_frac * per_day)
        span = int(rng.integers(2, max(3, per_day // 6)))
        idx = np.arange(start, min(start + span, n))
        if idx.size == 0:
            continue
        shape = rng.random(idx.size) + 0.25
        precip[idx] += total_mm * shape / shape.sum()
    return precip


def _cloud_factor(
    index: pd.DatetimeIndex,
    interval_min: int,
    monsoon: np.ndarray,
    precip: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Stochastic clearness modifier in (0, 1]: slow cloud field + deep short drops."""
    n = len(index)
    tau_steps = 180.0 / interval_min  # ~3 h cloud-field memory
    latent = ou_process(n, tau_steps, rng)
    synoptic = ou_process(n, (36 * 60.0) / interval_min, rng)
    bias = -1.55 + 2.15 * monsoon + 0.55 * synoptic
    base = 1.0 - 0.55 * _sigmoid(1.2 * latent + bias)

    # Deep multiplicative transients (cumulus passing the plane of array).
    drops = np.ones(n)
    per_day = round(24 * 60 / interval_min)
    n_days = max(1, n // per_day)
    for d in range(n_days):
        w = float(monsoon[min(d * per_day, n - 1)])
        lam = 1.0 + 6.0 * w
        for _ in range(int(rng.poisson(lam))):
            start = int(rng.integers(d * per_day, min((d + 1) * per_day, n)))
            span = int(rng.integers(1, 9))
            depth = float(rng.uniform(0.12, 0.58))
            idx = np.arange(start, min(start + span, n))
            drops[idx] = np.minimum(drops[idx], depth)

    factor = base * drops
    raining = precip > 0.02
    factor[raining] = np.minimum(factor[raining], rng.uniform(0.10, 0.32, size=int(raining.sum())))
    return np.clip(factor, 0.04, 1.0)


def generate_site_met(
    site_key: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval_min: int,
    seed: int,
) -> SiteMet:
    """Generate one site's meteorology on [start, end) at the given cadence."""
    if site_key not in SITES:
        raise KeyError(f"unknown site {site_key!r}")
    site = SITES[site_key]
    rng = child_seed(seed, "met", site_key)

    index = pd.date_range(start, end, freq=f"{interval_min}min", tz="UTC", inclusive="left")
    n = len(index)
    if n == 0:
        raise ValueError("empty time index; check start/end/interval")
    doy = index.dayofyear.to_numpy().astype(float)
    lhour = local_hour(index)
    monsoon = monsoon_weight(doy)

    # --- precipitation and cloud ------------------------------------------------
    precip = _rain_series(index, interval_min, monsoon, rng)
    cloud = _cloud_factor(index, interval_min, monsoon, precip, rng)

    # --- irradiance -------------------------------------------------------------
    loc = Location(
        latitude=float(site["latitude"]),
        longitude=float(site["longitude"]),
        altitude=float(site["elevation_m"]),
        tz="UTC",
    )
    solpos = loc.get_solarposition(index)
    clearsky = loc.get_clearsky(index, model="ineichen")
    zenith = solpos["apparent_zenith"].to_numpy(dtype=float)
    cs_ghi = clearsky["ghi"].to_numpy(dtype=float)
    ghi = np.clip(cs_ghi * cloud, 0.0, None)
    ghi[zenith >= 90.0] = 0.0

    decomp = irradiance.erbs(pd.Series(ghi, index=index), solpos["zenith"], index)
    dni = np.nan_to_num(decomp["dni"].to_numpy(dtype=float), nan=0.0)
    dhi = np.nan_to_num(decomp["dhi"].to_numpy(dtype=float), nan=0.0)
    dni = np.clip(dni, 0.0, 1100.0)
    dhi = np.clip(dhi, 0.0, 700.0)

    tilt = site.get("tilt_deg")
    if tilt is not None:
        dni_extra = irradiance.get_extra_radiation(index)
        poa = irradiance.get_total_irradiance(
            surface_tilt=float(tilt),
            surface_azimuth=float(site["azimuth_deg"]),
            solar_zenith=solpos["apparent_zenith"],
            solar_azimuth=solpos["azimuth"],
            dni=pd.Series(dni, index=index),
            ghi=pd.Series(ghi, index=index),
            dhi=pd.Series(dhi, index=index),
            dni_extra=dni_extra,
            albedo=0.20,
            model="haydavies",
        )["poa_global"].to_numpy(dtype=float)
        poa = np.nan_to_num(poa, nan=0.0)
        poa[zenith >= 90.0] = 0.0
        poa = np.clip(poa, 0.0, 1300.0)
    else:
        poa = np.zeros(n)

    # --- temperature ------------------------------------------------------------
    # Daily-mean cloudiness damps the diurnal amplitude; monsoon days are flatter.
    cloud_daily = (
        pd.Series(cloud, index=index).groupby(index.normalize()).transform("mean").to_numpy()
    )
    seasonal = 29.0 + 6.5 * np.cos(2 * np.pi * (doy - 135.0) / 365.0)
    amp = 5.9 - 2.3 * (1.0 - cloud_daily)
    diurnal = amp * np.cos(2 * np.pi * (lhour - 15.0) / 24.0)
    temp = seasonal + diurnal + ou_process(n, 90.0 / interval_min, rng, sigma=0.9)
    temp -= 1.6 * (precip > 0.05)
    temp = np.clip(temp, 14.0, 46.0)

    # --- humidity ---------------------------------------------------------------
    hum_base = 34.0 + 42.0 * monsoon
    hum = (
        hum_base
        - 1.9 * diurnal
        + ou_process(n, 120.0 / interval_min, rng, sigma=5.0)
        + 18.0 * (precip > 0.05)
    )
    hum = np.clip(hum, 18.0, 99.0)

    # --- pressure ---------------------------------------------------------------
    p_ref = 1013.25 * float(np.exp(-float(site["elevation_m"]) / 8400.0))
    semidiurnal = 1.1 * np.cos(2 * np.pi * (lhour - 10.0) / 12.0)
    pressure = (
        p_ref
        - 8.0 * monsoon
        + semidiurnal
        + ou_process(n, (18 * 60.0) / interval_min, rng, sigma=2.4)
    )

    # --- wind speed: OU latent -> Gaussian copula -> Weibull marginal -----------
    scale = float(site.get("weibull_scale", 7.0))
    shape = float(site.get("weibull_shape", 2.0))
    latent = (
        ou_process(n, 150.0 / interval_min, rng)
        + 0.55 * ou_process(n, (4 * 24 * 60.0) / interval_min, rng)  # synoptic
        + 0.38 * np.cos(2 * np.pi * (lhour - 16.0) / 24.0)  # diurnal sea breeze
        + 0.22 * np.cos(2 * np.pi * (doy - 200.0) / 365.0)  # seasonal
    )
    latent = (latent - latent.mean()) / max(latent.std(), 1e-9)
    u = np.clip(stats.norm.cdf(latent), 1e-6, 1 - 1e-6)
    wind_speed = stats.weibull_min.ppf(u, shape, scale=scale)
    wind_speed = np.clip(wind_speed, 0.0, 32.0)

    # --- wind direction: wrapped random walk about the prevailing bearing -------
    prevailing = float(site.get("prevailing_direction_deg", 250.0))
    dev = 22.0 * ou_process(n, (8 * 60.0) / interval_min, rng)
    regime = np.zeros(n)
    per_day = round(24 * 60 / interval_min)
    for _ in range(int(rng.integers(3, 9))):
        start_i = int(rng.integers(0, n))
        span = int(rng.integers(per_day // 4, max(per_day, 2)))
        regime[start_i : start_i + span] += float(rng.normal(0.0, 38.0))
    direction = wrap_deg(prevailing + dev + regime)

    # --- air density and dust ---------------------------------------------------
    air_density = (pressure * 100.0) / (AIR_GAS_CONSTANT * (temp + 273.15))

    aod_base = 0.36 - 0.13 * monsoon
    aod = aod_base * np.exp(0.35 * ou_process(n, (12 * 60.0) / interval_min, rng))
    for _ in range(int(rng.integers(1, 5))):  # dust storms
        start_i = int(rng.integers(0, n))
        span = int(rng.integers(per_day // 6, max(per_day // 2, 2)))
        aod[start_i : start_i + span] += float(rng.uniform(0.20, 0.65))
    # Rain scavenges aerosol: decay the AOD for ~a day after meaningful rain.
    wet = first_order_lag((precip > 0.2).astype(float), 240.0, interval_min)
    aod *= 1.0 - 0.55 * np.clip(wet / max(wet.max(), 1e-9), 0.0, 1.0)
    aod = np.clip(aod, 0.03, 1.2)

    frame = pd.DataFrame(
        {
            "ts": index,
            "site": site_key,
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": direction,
            "ambient_temp_c": temp,
            "pressure_hpa": pressure,
            "humidity_pct": hum,
            "ghi_wm2": ghi,
            "dni_wm2": dni,
            "dhi_wm2": dhi,
            "precip_mm": precip,
            "dust_aod": aod,
        }
    )[SITE_MET_COLUMNS]

    extras = pd.DataFrame(
        {
            "poa_wm2": poa,
            "clearsky_ghi_wm2": cs_ghi,
            "solar_zenith_deg": zenith,
            "solar_azimuth_deg": solpos["azimuth"].to_numpy(dtype=float),
            "air_density": air_density,
            "cloud_factor": cloud,
            "monsoon_weight": monsoon,
            "local_hour": lhour,
            "curtail_cap_frac": site_curtailment(index, interval_min, site_key, seed),
        },
        index=index,
    )

    return SiteMet(site=site_key, interval_min=interval_min, index=index, frame=frame, extras=extras)


def site_curtailment(
    index: pd.DatetimeIndex,
    interval_min: int,
    site_key: str,
    seed: int,
) -> np.ndarray:
    """Site-wide grid curtailment cap as a fraction of rated power; NaN when free.

    Generated at site level on purpose: curtailment hits every asset on the feeder at
    once, which is what lets the peer layer recognise it as non-asset-specific.
    """
    rng = child_seed(seed, "curtail", site_key)
    n = len(index)
    cap = np.full(n, np.nan)
    per_day = round(24 * 60 / interval_min)
    for _ in range(int(rng.integers(2, 5))):
        start = int(rng.integers(0, max(n - per_day, 1)))
        span = int(rng.integers(max(per_day // 24, 1) * 6, per_day // 4 + 1))
        cap[start : start + span] = float(rng.uniform(0.45, 0.78))
    return cap


def daily_rain_mm(index: pd.DatetimeIndex, precip_mm: np.ndarray) -> np.ndarray:
    """Per-interval broadcast of that UTC day's total rainfall."""
    return (
        pd.Series(precip_mm, index=index)
        .groupby(index.normalize())
        .transform("sum")
        .to_numpy(dtype=float)
    )
