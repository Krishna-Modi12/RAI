"""Feature policy management and schema inventory for the external CARE benchmark.

Supports three explicit evaluation policies:
1. CARE_2D: The narrow representation reproducing the baseline adapter from Gate 5.1/5.2
   (wind speed, active power).
2. CARE_COMMON: A cross-farm semantic representation matching WindADBench Track 4
   (wind speed, active power, rotor speed), mapped safely across Farms A, B, and C.
3. CARE_NATIVE_SEMANTIC: The available farm-specific numeric sensor schema (81 sensors in Farm A,
   252 in Farm B, 952 in Farm C), excluding timestamps, metadata, and status IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from rai.ingest.care import CARE_ROOT

FeaturePolicy = Literal["care_2d", "care_common", "care_native", "care_native_semantic"]

# Canonical semantic signals
CARE_2D_SIGNALS: tuple[str, ...] = ("wind_speed", "power")
CARE_COMMON_SIGNALS: tuple[str, ...] = ("wind_speed", "active_power", "rotor_speed")

# Verified mappings per farm for CARE_2D (reproducing Gate 5.1 / 5.2 baseline adapter)
FARM_2D_MAPPING: dict[str, dict[str, str]] = {
    "Wind Farm A": {
        "wind_speed": "wind_speed_3_avg",
        "power": "power_29_avg",
    },
    "Wind Farm B": {
        "wind_speed": "wind_speed_59_avg",
        "power": "power_58_avg",
    },
    "Wind Farm C": {
        "wind_speed": "wind_speed_235_avg",
        "power": "power_17_avg",
    },
}

# Verified mappings per farm based on feature_description.csv and sensor descriptions
FARM_COMMON_MAPPING: dict[str, dict[str, str]] = {
    "Wind Farm A": {
        "wind_speed": "wind_speed_3_avg",
        "active_power": "power_29_avg",
        "rotor_speed": "sensor_52_avg",  # feature_description: "Rotor rpm"
    },
    "Wind Farm B": {
        "wind_speed": "wind_speed_59_avg",
        "active_power": "power_58_avg",  # Available power / active generation
        "rotor_speed": "sensor_25_avg",  # feature_description: "Rotor speed"
    },
    "Wind Farm C": {
        "wind_speed": "wind_speed_235_avg",
        "active_power": "power_17_avg",  # Active power converter
        "rotor_speed": "sensor_144_avg",  # feature_description: "Rotor speed 1"
    },
}

METADATA_COLUMNS: frozenset[str] = frozenset({
    "time_stamp",
    "id",
    "care_id",
    "status_type_id",
    "care_status_type_id",
    "train_test",
    "care_train_test",
    "status_code",
    "operating_state",
    "asset_id",
    "ts",
})


def classify_sensor_semantic_category(
    description: str,
    unit: str,
    is_angle: bool,
    is_counter: bool,
    sensor_name: str,
) -> str:
    """Classify a CARE sensor into physical and operational semantic categories based on metadata.

    Categories investigated:
    wind_speed, active_power, rotor_speed, reactive_power, temperature, pitch,
    yaw, vibration, generator, gearbox, nacelle, electrical, hydraulic, pressure,
    counters, angles.
    """
    d = str(description).lower()
    u = str(unit).lower()
    s = str(sensor_name).lower()

    if is_counter or "counter" in d or "total positive" in d or "total negative" in d:
        return "counters"
    if "rotor" in d and ("rpm" in d or "speed" in d):
        return "rotor_speed"
    if ("wind" in d and ("speed" in d or "windspeed" in d)) or "wind_speed" in s:
        return "wind_speed"
    if "reactive power" in d or "reactive" in s or u in ("kvar", "kvarh", "varh"):
        return "reactive_power"
    if "active power" in d or "grid power" in d or "available power" in d or ("power" in s and "reactive" not in d):
        return "active_power"
    if "temperature" in d or "temp" in d or u in ("c", "celsius", "°c", "c"):
        return "temperature"
    if "vibration" in d or "acceleration" in d or u in ("mg", "m/s2", "mm/s"):
        return "vibration"
    if "pitch" in d or "blade" in d:
        return "pitch"
    if "yaw" in d:
        return "yaw"
    if "gearbox" in d:
        return "gearbox"
    if "generator" in d:
        return "generator"
    if "nacelle" in d:
        return "nacelle"
    if "hydraulic" in d or "fluid" in d or "oil level" in d:
        return "hydraulic"
    if "pressure" in d or u in ("bar", "hpa", "mbar", "kpa"):
        return "pressure"
    if is_angle or "direction" in d or "angle" in d or u in ("deg", "°", ""):
        return "angles"
    if any(k in d for k in ("voltage", "current", "frequency", "phase", "rms", "inverter", "grid", "hv", "apparent power", "cable load", "torque", "battery", "flow")):
        return "electrical"

    return "other_sensor"


@dataclass(frozen=True)
class FeatureInventoryItem:
    farm: str
    sensor_name: str
    statistic_type: str
    description: str
    unit: str
    is_angle: bool
    is_counter: bool
    raw_column_matches: str
    resolved_semantic_category: str
    rai_currently_uses: bool
    exclusion_reason: str


def get_feature_columns(
    farm_name: str, policy: FeaturePolicy, frame_columns: list[str] | tuple[str, ...]
) -> list[str]:
    """Return the ordered list of feature column names for a given farm and policy."""
    cols_set = set(frame_columns)

    if policy == "care_2d":
        mapping = FARM_2D_MAPPING.get(farm_name)
        if not mapping:
            raise ValueError(f"No CARE_2D mapping defined for {farm_name}")
        cols_2d: list[str] = []
        for signal in CARE_2D_SIGNALS:
            col = mapping.get(signal)
            if col and col in cols_set:
                cols_2d.append(col)
            else:
                matched = next((c for c in frame_columns if c.lower() == (col or "").lower()), None)
                if matched:
                    cols_2d.append(matched)
                else:
                    raise KeyError(f"Required CARE_2D signal {signal} (expected {col}) not found in columns")
        return cols_2d

    if policy == "care_common":
        mapping = FARM_COMMON_MAPPING.get(farm_name)
        if not mapping:
            raise ValueError(f"No CARE_COMMON mapping defined for {farm_name}")
        common_cols: list[str] = []
        for signal in CARE_COMMON_SIGNALS:
            col = mapping.get(signal)
            if col and col in cols_set:
                common_cols.append(col)
            else:
                matched = next((c for c in frame_columns if c.lower() == (col or "").lower()), None)
                if matched:
                    common_cols.append(matched)
                else:
                    raise KeyError(f"Required CARE_COMMON signal {signal} (expected {col}) not found in columns")
        return common_cols

    if policy in ("care_native", "care_native_semantic"):
        # All columns in frame that are not metadata
        return [c for c in frame_columns if c.lower() not in METADATA_COLUMNS]

    raise ValueError(f"Unknown feature policy: {policy}")


def build_feature_inventory(
    care_root: Path = CARE_ROOT,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Inspect and catalog all feature columns across Farms A, B, and C."""
    farms = ("Wind Farm A", "Wind Farm B", "Wind Farm C")
    summary_by_farm: dict[str, Any] = {}
    detailed_inventory: list[dict[str, Any]] = []

    for farm in farms:
        farm_dir = care_root / farm
        if not farm_dir.is_dir():
            continue

        desc_file = farm_dir / "feature_description.csv"
        desc_df = pd.read_csv(desc_file, sep=";") if desc_file.is_file() else pd.DataFrame()

        # Inspect the first dataset file when the full CARE archive is available.
        # CI may use the committed metadata-only fixture, so retain semantic inventory
        # coverage without pretending that raw columns were downloaded.
        ds_files = sorted((farm_dir / "datasets").glob("*.csv"))
        if ds_files:
            sample_df = pd.read_csv(ds_files[0], sep=";", nrows=5)
            raw_cols = list(sample_df.columns)
        else:
            raw_cols = sorted({
                *desc_df.get("sensor_name", pd.Series(dtype=str)).dropna().astype(str).tolist(),
                *FARM_2D_MAPPING.get(farm, {}).values(),
                *FARM_COMMON_MAPPING.get(farm, {}).values(),
            })

        # Build map of base_sensor -> list of matching columns in raw data
        col_matches: dict[str, list[str]] = {}
        for c in raw_cols:
            if c.lower() in METADATA_COLUMNS:
                continue
            base = c
            for suffix in ("_avg", "_min", "_max", "_std", "_mean", "_stddev"):
                if c.endswith(suffix):
                    base = c[:-len(suffix)]
                    break
            col_matches.setdefault(base, []).append(c)

        mapping_2d = FARM_2D_MAPPING.get(farm, {})
        mapping_common = FARM_COMMON_MAPPING.get(farm, {})
        used_2d_cols = set(mapping_2d.values())
        used_common_cols = set(mapping_common.values())

        category_counts: dict[str, int] = {}
        native_cols: list[str] = [c for c in raw_cols if c.lower() not in METADATA_COLUMNS]

        for _, row in desc_df.iterrows():
            s_name = str(row.get("sensor_name", ""))
            stat_type = str(row.get("statistics_type", ""))
            desc = str(row.get("description", ""))
            unit = str(row.get("unit", ""))
            is_ang = bool(row.get("is_angle", False))
            is_cnt = bool(row.get("is_counter", False))

            cat = classify_sensor_semantic_category(desc, unit, is_ang, is_cnt, s_name)
            category_counts[cat] = category_counts.get(cat, 0) + 1

            matches = col_matches.get(s_name, [])
            matches_str = ", ".join(matches) if matches else "none"

            # Does RAI currently use this sensor?
            is_used_by_rai = any(m in used_2d_cols or m in used_common_cols for m in matches)

            if not matches:
                exclusion_reason = "No matching raw dataset column"
            elif is_cnt:
                exclusion_reason = "Counter / non-stationary cumulative integral"
            elif not is_used_by_rai:
                exclusion_reason = "Excluded from narrow CARE_2D/CARE_COMMON baselines; available in CARE_NATIVE_SEMANTIC"
            else:
                exclusion_reason = ""

            item = FeatureInventoryItem(
                farm=farm,
                sensor_name=s_name,
                statistic_type=stat_type,
                description=desc,
                unit=unit,
                is_angle=is_ang,
                is_counter=is_cnt,
                raw_column_matches=matches_str,
                resolved_semantic_category=cat,
                rai_currently_uses=is_used_by_rai,
                exclusion_reason=exclusion_reason,
            )
            detailed_inventory.append(item.__dict__)

        summary_by_farm[farm] = {
            "sensor_descriptions_count": len(desc_df),
            "raw_total_columns": len(raw_cols),
            "metadata_columns_count": len(raw_cols) - len(native_cols),
            "recognized_sensor_columns": len(native_cols),
            "semantic_categories_breakdown": category_counts,
            "care_2d_columns": list(used_2d_cols),
            "care_common_columns": list(used_common_cols),
            "care_native_columns_count": len(native_cols),
        }

    return summary_by_farm, detailed_inventory
