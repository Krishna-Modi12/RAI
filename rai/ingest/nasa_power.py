"""NASA POWER hourly point client, normalised onto our `site_met` schema.

Real HTTP, real cache, no fallbacks that invent weather. If the API cannot be reached
and there is no cached parquet for the request, this module raises `NasaPowerUnavailable`
and the caller must decide what to do. It will never return a synthesised frame.

Endpoint
    GET https://power.larc.nasa.gov/api/temporal/hourly/point
No API key. Response shape (verified live 2026-09-12, POWER Hourly API v2.10.0)::

    {"geometry": {"coordinates": [lon, lat, elev]},
     "properties": {"parameter": {"T2M": {"2024010100": 11.04, ...}, ...}},
     "header": {"fill_value": -999.0, "time_standard": "UTC", ...},
     "parameters": {"T2M": {"units": "C", "longname": "..."}, ...}}

Timestamp keys are `YYYYMMDDHH` and label the *start* of the hour.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final

import httpx
import pandas as pd

from rai.config import RAW, SITES

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class NasaPowerError(RuntimeError):
    """Base class for every failure mode of this client."""


class NasaPowerUnavailable(NasaPowerError):
    """The API could not be reached and no cache entry satisfies the request."""


class NasaPowerResponseError(NasaPowerError):
    """The API answered, but not with a payload we can trust."""


# ---------------------------------------------------------------------------
# Request definition
# ---------------------------------------------------------------------------

API_URL: Final = "https://power.larc.nasa.gov/api/temporal/hourly/point"
CACHE_DIR: Final[Path] = RAW / "nasa_power"
FILL_VALUE: Final = -999.0

#: POWER parameter -> (canonical site_met column, multiplicative factor, note)
#:
#: Unit reconciliation, all confirmed against the `parameters` block the API returns:
#:  - ALLSKY_* are reported as Wh/m^2 accumulated over the hour. Over a 1-hour interval
#:    that is numerically identical to the mean W/m^2, so the factor is 1.0.
#:  - PS is kPa; site_met wants hPa, hence x10.
#:  - PRECTOTCORR is a rate in mm/day even on the hourly endpoint; the hour's depth in mm
#:    is therefore value/24.
PARAMETER_MAP: Final[dict[str, tuple[str, float, str]]] = {
    "ALLSKY_SFC_SW_DWN": ("ghi_wm2", 1.0, "Wh/m^2 per hour == mean W/m^2"),
    "ALLSKY_SFC_SW_DNI": ("dni_wm2", 1.0, "Wh/m^2 per hour == mean W/m^2"),
    "ALLSKY_SFC_SW_DIFF": ("dhi_wm2", 1.0, "Wh/m^2 per hour == mean W/m^2"),
    "T2M": ("ambient_temp_c", 1.0, "already degC"),
    "WS50M": ("wind_speed_ms", 1.0, "50 m is closer to our 80 m hub than 10 m"),
    "WD50M": ("wind_direction_deg", 1.0, "degrees clockwise from north"),
    "RH2M": ("humidity_pct", 1.0, "already %"),
    "PS": ("pressure_hpa", 10.0, "kPa -> hPa"),
    "PRECTOTCORR": ("precip_mm", 1.0 / 24.0, "mm/day rate -> mm within the hour"),
}

#: Requested in addition to the mapped set: 10 m wind is kept as a secondary column so a
#: caller can build a shear estimate instead of us asserting one.
EXTRA_PARAMETERS: Final[tuple[str, ...]] = ("WS10M", "WD10M")

DEFAULT_PARAMETERS: Final[tuple[str, ...]] = tuple(PARAMETER_MAP) + EXTRA_PARAMETERS

#: site_met column order from the canonical schema.
SITE_MET_COLUMNS: Final[tuple[str, ...]] = (
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
)

#: Aerosol optical depth is not offered on the hourly endpoint. We emit the column so the
#: schema is satisfied, but every value is null - never a plausible-looking constant.
UNAVAILABLE_COLUMNS: Final[tuple[str, ...]] = ("dust_aod",)

ATTRIBUTION: Final = (
    "These data were obtained from the NASA Langley Research Center POWER Project funded "
    "through the NASA Earth Science Directorate Applied Science Program."
)


# ---------------------------------------------------------------------------
# Cache addressing
# ---------------------------------------------------------------------------


def _as_yyyymmdd(value: str | date | datetime) -> str:
    if isinstance(value, str):
        cleaned = value.replace("-", "")
        if len(cleaned) != 8 or not cleaned.isdigit():
            raise ValueError(f"date must be YYYYMMDD or YYYY-MM-DD, got {value!r}")
        return cleaned
    return value.strftime("%Y%m%d")


def cache_key(
    latitude: float,
    longitude: float,
    start: str | date | datetime,
    end: str | date | datetime,
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
) -> str:
    """Stable filename stem for one request. Parameter set is hashed, not spelled out."""
    phash = hashlib.sha1(",".join(sorted(parameters)).encode()).hexdigest()[:8]
    return (
        f"lat{latitude:+08.3f}_lon{longitude:+09.3f}"
        f"_{_as_yyyymmdd(start)}_{_as_yyyymmdd(end)}_{phash}"
    )


def cache_path(
    latitude: float,
    longitude: float,
    start: str | date | datetime,
    end: str | date | datetime,
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
    cache_dir: Path | None = None,
) -> Path:
    root = CACHE_DIR if cache_dir is None else cache_dir
    return root / f"{cache_key(latitude, longitude, start, end, parameters)}.parquet"


def cached_requests(cache_dir: Path | None = None) -> list[Path]:
    root = CACHE_DIR if cache_dir is None else cache_dir
    if not root.exists():
        return []
    return sorted(root.glob("*.parquet"))


# ---------------------------------------------------------------------------
# Normalisation (pure, offline-testable)
# ---------------------------------------------------------------------------


def normalise_payload(payload: dict[str, Any], site: str = "nasa_power_point") -> pd.DataFrame:
    """Turn a POWER hourly JSON payload into a canonical `site_met` frame.

    Raises NasaPowerResponseError on anything structurally unexpected, rather than
    quietly producing a short or empty frame.
    """
    try:
        params = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise NasaPowerResponseError(
            f"payload has no properties.parameter block (top-level keys: "
            f"{sorted(payload) if isinstance(payload, dict) else type(payload).__name__})"
        ) from exc

    if not isinstance(params, dict) or not params:
        raise NasaPowerResponseError("properties.parameter is empty")

    header = payload.get("header") or {}
    fill = float(header.get("fill_value", FILL_VALUE))

    series: dict[str, pd.Series] = {}
    for power_name, values in params.items():
        if not isinstance(values, dict) or not values:
            raise NasaPowerResponseError(f"parameter {power_name!r} carried no values")
        s = pd.Series(values, dtype="float64")
        s = s.mask(s == fill)
        series[power_name] = s

    index_keys = next(iter(series.values())).index
    try:
        ts = pd.to_datetime(pd.Index(index_keys), format="%Y%m%d%H", utc=True)
    except ValueError as exc:
        raise NasaPowerResponseError(
            f"timestamp keys are not YYYYMMDDHH (first: {list(index_keys)[:3]})"
        ) from exc

    out = pd.DataFrame({"ts": ts})
    out["site"] = site

    for power_name, (canonical, factor, _note) in PARAMETER_MAP.items():
        if power_name in series:
            out[canonical] = series[power_name].to_numpy(dtype="float64") * factor

    for power_name in EXTRA_PARAMETERS:
        if power_name in series:
            out[power_name.lower()] = series[power_name].to_numpy(dtype="float64")

    # Wind direction is an angle: keep it on [0, 360) even if the source drifts.
    if "wind_direction_deg" in out.columns:
        out["wind_direction_deg"] = out["wind_direction_deg"] % 360.0
    if "wd10m" in out.columns:
        out["wd10m"] = out["wd10m"] % 360.0

    for col in SITE_MET_COLUMNS:
        if col not in out.columns:
            out[col] = pd.Series([pd.NA] * len(out), dtype="Float64")

    ordered = list(SITE_MET_COLUMNS) + [
        c for c in out.columns if c not in SITE_MET_COLUMNS
    ]
    out = out.loc[:, ordered].sort_values("ts").reset_index(drop=True)
    out.attrs["source"] = "nasa_power"
    out.attrs["attribution"] = ATTRIBUTION
    out.attrs["unavailable_columns"] = list(UNAVAILABLE_COLUMNS)
    out.attrs["power_api"] = (header.get("api") or {}).get("version", "unknown")
    return out


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def request_params(
    latitude: float,
    longitude: float,
    start: str | date | datetime,
    end: str | date | datetime,
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
    community: str = "RE",
) -> dict[str, str]:
    return {
        "parameters": ",".join(parameters),
        "community": community,
        "latitude": f"{latitude}",
        "longitude": f"{longitude}",
        "start": _as_yyyymmdd(start),
        "end": _as_yyyymmdd(end),
        "format": "JSON",
        "time-standard": "UTC",
    }


def probe(timeout: float = 20.0, client: httpx.Client | None = None) -> tuple[bool, str]:
    """One-day reachability check. Returns (reachable, human-readable detail)."""
    params = request_params(23.25, 69.67, "20240101", "20240101", ("T2M",))
    owned = client is None
    c = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        t0 = time.perf_counter()
        r = c.get(API_URL, params=params)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        if r.status_code != 200:
            return False, f"HTTP {r.status_code} in {dt_ms:.0f} ms"
        n = len(r.json()["properties"]["parameter"]["T2M"])
        return True, f"HTTP 200 in {dt_ms:.0f} ms, {n} hourly values for the probe day"
    except Exception as exc:  # noqa: BLE001 - reachability, any failure is a "no"
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        if owned:
            c.close()


def _get_json(
    params: dict[str, str],
    timeout: float,
    retries: int,
    client: httpx.Client | None,
) -> dict[str, Any]:
    owned = client is None
    c = client or httpx.Client(timeout=timeout, follow_redirects=True)
    last: Exception | None = None
    try:
        for attempt in range(1, retries + 1):
            try:
                r = c.get(API_URL, params=params)
            except Exception as exc:  # noqa: BLE001 - transport errors are retryable
                last = exc
            else:
                if r.status_code == 200:
                    try:
                        return r.json()
                    except json.JSONDecodeError as exc:
                        raise NasaPowerResponseError(
                            f"HTTP 200 but body is not JSON (first 200 bytes: {r.text[:200]!r})"
                        ) from exc
                if 400 <= r.status_code < 500:
                    raise NasaPowerResponseError(
                        f"POWER rejected the request: HTTP {r.status_code} "
                        f"{r.text[:300]!r}"
                    )
                last = httpx.HTTPStatusError(
                    f"HTTP {r.status_code}", request=r.request, response=r
                )
            if attempt < retries:
                time.sleep(min(2.0 * attempt, 6.0))
        raise NasaPowerUnavailable(
            f"POWER unreachable after {retries} attempt(s): {type(last).__name__}: {last}"
        )
    finally:
        if owned:
            c.close()


def fetch_hourly(
    latitude: float,
    longitude: float,
    start: str | date | datetime,
    end: str | date | datetime,
    *,
    site: str = "nasa_power_point",
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    refresh: bool = False,
    timeout: float = 60.0,
    retries: int = 3,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Hourly weather for one point, normalised to `site_met` columns.

    Cached as parquet under data/raw/nasa_power/, so the second call for the same
    lat/lon/date-range/parameter-set does no network I/O at all.

    Raises NasaPowerUnavailable if the network fails and no cache entry exists.
    """
    path = cache_path(latitude, longitude, start, end, parameters, cache_dir)
    if use_cache and not refresh and path.exists():
        df = pd.read_parquet(path)
        df.attrs["source"] = "nasa_power"
        df.attrs["attribution"] = ATTRIBUTION
        df.attrs["cache_hit"] = True
        df.attrs["cache_path"] = str(path)
        return df

    payload = _get_json(
        request_params(latitude, longitude, start, end, parameters), timeout, retries, client
    )
    df = normalise_payload(payload, site=site)
    if df.empty:
        raise NasaPowerResponseError("POWER returned a payload with zero hours")

    if use_cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        meta = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "start": _as_yyyymmdd(start),
            "end": _as_yyyymmdd(end),
            "parameters": list(parameters),
            "rows": len(df),
            "api_version": df.attrs.get("power_api", "unknown"),
            "attribution": ATTRIBUTION,
            "unavailable_columns": list(UNAVAILABLE_COLUMNS),
        }
        path.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    df.attrs["cache_hit"] = False
    df.attrs["cache_path"] = str(path) if use_cache else ""
    return df


def fetch_for_site(
    site_key: str,
    start: str | date | datetime,
    end: str | date | datetime,
    **kwargs: Any,
) -> pd.DataFrame:
    """Fetch POWER data at the real coordinates of one configured RAI site."""
    if site_key not in SITES:
        raise KeyError(f"unknown site {site_key!r}; known: {sorted(SITES)}")
    site = SITES[site_key]
    kwargs.setdefault("site", site_key)
    return fetch_hourly(
        float(site["latitude"]), float(site["longitude"]), start, end, **kwargs
    )


def coverage(df: pd.DataFrame) -> dict[str, float | int | str | None]:
    """Measured facts about a fetched frame. Used for status reporting - no estimates."""
    if df.empty:
        return {"rows": 0, "first_ts": None, "last_ts": None}
    out: dict[str, float | int | str | None] = {
        "rows": len(df),
        "first_ts": str(df["ts"].iloc[0]),
        "last_ts": str(df["ts"].iloc[-1]),
    }
    for col in SITE_MET_COLUMNS:
        if col in ("ts", "site"):
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        out[f"{col}_non_null"] = int(s.notna().sum())
    return out
