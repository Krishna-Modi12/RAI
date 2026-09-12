"""Atmospheric composition and weather forecast provider.

Integrates Copernicus Atmosphere Monitoring Service (CAMS) global atmospheric
forecasts and meteorological data via Open-Meteo with cached offline fallbacks:
- Desert dust aerosol concentration (ug/m3)
- Aerosol Optical Depth (AOD @ 550nm)
- Particulate matter (PM10, PM2.5)
- Precipitation accumulation and rain probabilities (24h, 48h, 72h)
- Solar irradiance, ambient temperature, and wind velocity
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
import numpy as np

from rai.config import ARTIFACTS

log = logging.getLogger(__name__)

CACHE_DIR = ARTIFACTS / "weather_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SITE_COORDINATES = {
    "charanka-solar": {"lat": 23.90, "lon": 71.20, "name": "Charanka Solar Park"},
    "kutch-wind": {"lat": 23.25, "lon": 69.67, "name": "Kutch Wind Farm"},
}


@dataclass(frozen=True)
class AtmosphericConditions:
    timestamp: datetime
    site: str
    is_live: bool
    dust_ug_m3: float
    aod_550nm: float
    pm10_ug_m3: float
    pm25_ug_m3: float
    precipitation_mm: float
    rain_probability_pct: float
    ambient_temp_c: float
    wind_speed_ms: float
    wind_direction_deg: float
    relative_humidity_pct: float
    # Derived rolling features
    dust_24h_integral: float = 0.0
    aod_24h_mean: float = 0.0
    precipitation_24h_mm: float = 0.0
    rain_probability_48h: float = 0.0
    days_since_rain: float = 14.0
    source_detail: str = "open_meteo_cams"


class WeatherProvider:
    """Manages atmospheric composition and weather ingestion with offline caching."""

    def __init__(self, timeout_s: float = 6.0):
        self.timeout_s = timeout_s

    def get_current_conditions(self, site: str = "charanka-solar") -> AtmosphericConditions:
        """Fetch current atmospheric metrics for a plant site, falling back to cache."""
        coords = SITE_COORDINATES.get(site, SITE_COORDINATES["charanka-solar"])
        lat, lon = coords["lat"], coords["lon"]

        try:
            # Query Open-Meteo Air Quality (CAMS Global Atmospheric Composition)
            aq_url = (
                f"https://air-quality-api.open-meteo.com/v1/air-quality?"
                f"latitude={lat}&longitude={lon}&hourly=dust,pm10,pm2_5,aerosol_optical_depth&forecast_days=3"
            )
            met_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,"
                f"precipitation,precipitation_probability,wind_speed_10m,wind_direction_10m&forecast_days=3"
            )

            with httpx.Client(timeout=self.timeout_s) as client:
                aq_resp = client.get(aq_url)
                met_resp = client.get(met_url)

            if aq_resp.status_code == 200 and met_resp.status_code == 200:
                aq_data = aq_resp.json().get("hourly", {})
                met_data = met_resp.json().get("hourly", {})
                conditions = self._parse_live_arrays(site, aq_data, met_data)
                # Persist to local cache for offline runs
                self._save_cache(site, conditions)
                return conditions
        except Exception as exc:  # noqa: BLE001
            log.warning("Live atmospheric fetch failed (%s: %s); utilizing cached fallback", type(exc).__name__, exc)

        return self._load_cache_or_fallback(site)

    def _parse_live_arrays(self, site: str, aq: dict, met: dict) -> AtmosphericConditions:
        dust_series = [float(v) for v in aq.get("dust", [45.0]) if v is not None] or [45.0]
        aod_series = [float(v) for v in aq.get("aerosol_optical_depth", [0.35]) if v is not None] or [0.35]
        pm10_series = [float(v) for v in aq.get("pm10", [60.0]) if v is not None] or [60.0]
        pm25_series = [float(v) for v in aq.get("pm2_5", [25.0]) if v is not None] or [25.0]

        precip_series = [float(v) for v in met.get("precipitation", [0.0]) if v is not None] or [0.0]
        rain_prob_series = [float(v) for v in met.get("precipitation_probability", [0.0]) if v is not None] or [0.0]
        temp_series = [float(v) for v in met.get("temperature_2m", [32.0]) if v is not None] or [32.0]
        wind_spd_series = [float(v) for v in met.get("wind_speed_10m", [4.5]) if v is not None] or [4.5]
        wind_dir_series = [float(v) for v in met.get("wind_direction_10m", [240.0]) if v is not None] or [240.0]
        rh_series = [float(v) for v in met.get("relative_humidity_2m", [45.0]) if v is not None] or [45.0]

        # Rolling calculations
        dust_24h = float(np.sum(dust_series[:24]))
        aod_24h = float(np.mean(aod_series[:24]))
        precip_24h = float(np.sum(precip_series[:24]))
        rain_prob_48h = float(np.max(rain_prob_series[:48])) / 100.0 if rain_prob_series else 0.0

        return AtmosphericConditions(
            timestamp=datetime.now(tz=datetime.now().astimezone().tzinfo),
            site=site,
            is_live=True,
            dust_ug_m3=round(dust_series[0], 1),
            aod_550nm=round(aod_series[0], 3),
            pm10_ug_m3=round(pm10_series[0], 1),
            pm25_ug_m3=round(pm25_series[0], 1),
            precipitation_mm=round(precip_series[0], 2),
            rain_probability_pct=round(rain_prob_series[0], 1),
            ambient_temp_c=round(temp_series[0], 1),
            wind_speed_ms=round(wind_spd_series[0], 1),
            wind_direction_deg=round(wind_dir_series[0], 1),
            relative_humidity_pct=round(rh_series[0], 1),
            dust_24h_integral=round(dust_24h, 1),
            aod_24h_mean=round(aod_24h, 3),
            precipitation_24h_mm=round(precip_24h, 2),
            rain_probability_48h=round(rain_prob_48h, 2),
            days_since_rain=19.0,
            source_detail="open_meteo_cams_live",
        )

    def _save_cache(self, site: str, cond: AtmosphericConditions) -> None:
        path = CACHE_DIR / f"{site}_latest.json"
        data = {
            "timestamp": cond.timestamp.isoformat(),
            "site": cond.site,
            "dust_ug_m3": cond.dust_ug_m3,
            "aod_550nm": cond.aod_550nm,
            "pm10_ug_m3": cond.pm10_ug_m3,
            "pm25_ug_m3": cond.pm25_ug_m3,
            "precipitation_mm": cond.precipitation_mm,
            "rain_probability_pct": cond.rain_probability_pct,
            "ambient_temp_c": cond.ambient_temp_c,
            "wind_speed_ms": cond.wind_speed_ms,
            "wind_direction_deg": cond.wind_direction_deg,
            "relative_humidity_pct": cond.relative_humidity_pct,
            "dust_24h_integral": cond.dust_24h_integral,
            "aod_24h_mean": cond.aod_24h_mean,
            "precipitation_24h_mm": cond.precipitation_24h_mm,
            "rain_probability_48h": cond.rain_probability_48h,
            "days_since_rain": cond.days_since_rain,
            "source_detail": "open_meteo_cams_cached",
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_cache_or_fallback(self, site: str) -> AtmosphericConditions:
        path = CACHE_DIR / f"{site}_latest.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return AtmosphericConditions(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    site=data["site"],
                    is_live=False,
                    dust_ug_m3=data["dust_ug_m3"],
                    aod_550nm=data["aod_550nm"],
                    pm10_ug_m3=data["pm10_ug_m3"],
                    pm25_ug_m3=data["pm25_ug_m3"],
                    precipitation_mm=data["precipitation_mm"],
                    rain_probability_pct=data["rain_probability_pct"],
                    ambient_temp_c=data["ambient_temp_c"],
                    wind_speed_ms=data["wind_speed_ms"],
                    wind_direction_deg=data["wind_direction_deg"],
                    relative_humidity_pct=data["relative_humidity_pct"],
                    dust_24h_integral=data["dust_24h_integral"],
                    aod_24h_mean=data["aod_24h_mean"],
                    precipitation_24h_mm=data["precipitation_24h_mm"],
                    rain_probability_48h=data["rain_probability_48h"],
                    days_since_rain=data["days_since_rain"],
                    source_detail="open_meteo_cams_cached",
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Cache parse failed: %s", exc)

        # Static default profile calibrated to Gujarat pre-monsoon dry conditions
        return AtmosphericConditions(
            timestamp=datetime.now(tz=datetime.now().astimezone().tzinfo),
            site=site,
            is_live=False,
            dust_ug_m3=68.5,
            aod_550nm=0.42,
            pm10_ug_m3=82.0,
            pm25_ug_m3=31.5,
            precipitation_mm=0.0,
            rain_probability_pct=23.0,
            ambient_temp_c=34.2,
            wind_speed_ms=5.2,
            wind_direction_deg=245.0,
            relative_humidity_pct=38.0,
            dust_24h_integral=1640.0,
            aod_24h_mean=0.45,
            precipitation_24h_mm=0.0,
            rain_probability_48h=0.23,
            days_since_rain=19.0,
            source_detail="charanka_calibrated_offline_fixture",
        )


_provider = WeatherProvider()


def get_weather_provider() -> WeatherProvider:
    return _provider
