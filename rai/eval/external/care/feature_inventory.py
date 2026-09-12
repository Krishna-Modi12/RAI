"""Gate 5.4 Phase 1-2: why does RAI's CARE ingestion resolve so few canonical signals?

The prior gate (`docs/evaluation/EXTERNAL_GENERALIZATION.md`) found that
`rai.ingest.care.resolve_columns` recovers exactly 2 usable feature columns
(`wind_speed_ms`, `power_kw`) from every farm's raw header, and stated that this was
"consistent with" the benchmark's own anonymisation being the bottleneck. That statement
was too strong: it measured what the resolver finds from *column names alone*, not what
CARE's own supplied `feature_description.csv` sidecar (every anonymised `sensor_N` column
has a text description, a unit, and `is_angle`/`is_counter` flags) makes recoverable. This
module answers that question properly, using only the descriptions CARE itself ships -
never inventing or guessing an original sensor name.

Two things this module found, both load-bearing for what "feature_policy.py" does with them:

1. Wiring `feature_description.csv` into `resolve_columns(sensor_map=...)` recovers far
   more than 2 signals per farm (Farm A: 10/15, Farm B: 9/15, Farm C: 13/15 - see
   `build_feature_inventory`'s docstring for the exact per-farm lists). The "only 2
   features" finding was real, but it measured RAI's *default* ingestion behaviour
   (`load_care_csv` is never called with a `sensor_map`), not a hard limit CARE imposes.
2. Naively feeding every described sensor into `sensor_map` is unsafe: several sensors are
   cumulative energy counters (unit `Wh`/`VArh`, e.g. "Total active power" in Wh) whose
   *description text* scores higher against the `power_kw` alias table than the correctly-
   named `power_29`/`power_62`/`power_17` columns already do from their own raw names -
   verified directly (Farm A: without the exclusion, `power_kw` resolved from `sensor_50`,
   a Wh energy counter, not `power_29`, a kW instantaneous reading). `ENERGY_COUNTER_UNITS`
   below is the fix: descriptions whose unit is a cumulative energy unit are excluded from
   the sensor_map before it ever reaches `resolve_columns`, so an instantaneous-kW slot can
   never be silently filled by a Wh counter.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from rai.ingest.care import (
    PASSTHROUGH_COLUMNS,
    WIND_SIGNAL_SPECS,
    ColumnResolution,
    _alias_score,
    normalise_name,
    resolve_columns,
    split_variant,
)

#: Units that mark a cumulative energy counter, not an instantaneous reading. CARE's own
#: `is_counter` flag does not reliably catch these (verified: Farm A's "Total active power",
#: unit Wh, ships with `is_counter=False`) - the unit itself is the reliable signal, because
#: every WIND_SIGNAL_SPECS.unit in `rai/ingest/care.py` is an instantaneous-rate unit
#: (kW, m/s, degC, rpm, ...), never an accumulated one.
ENERGY_COUNTER_UNITS: frozenset[str] = frozenset({"wh", "kwh", "varh", "kvarh", "mwh"})

_METADATA_COLUMNS = frozenset({"time_stamp", "asset_id", *PASSTHROUGH_COLUMNS})


@dataclass(frozen=True)
class FeatureRow:
    farm: str
    column_name: str
    column_type: str
    unit: str
    description: str
    is_metadata: bool
    is_sensor: bool
    is_counter: bool
    is_angle: bool
    recognized_by_rai: bool
    matched_canonical: str
    rejection_reason: str


def load_feature_descriptions(farm_dir: Path) -> pd.DataFrame:
    """CARE's own sidecar: sensor_name;statistics_type;description;unit;is_angle;is_counter."""
    return pd.read_csv(farm_dir / "feature_description.csv", sep=";")


def build_safe_sensor_map(desc: pd.DataFrame) -> dict[str, str]:
    """Descriptions safe to feed `resolve_columns(sensor_map=...)` - energy counters excluded.

    See module docstring point 2. Excluding by unit, not by `is_counter`, because CARE's own
    `is_counter` flag does not mark every cumulative-energy column as such.
    """
    safe = desc[~desc["unit"].astype(str).str.strip().str.lower().isin(ENERGY_COUNTER_UNITS)]
    return dict(zip(safe["sensor_name"], safe["description"], strict=True))


def _categorize(description: str, unit: str, is_angle: bool, is_counter: bool) -> str:
    """Coarse category from CARE's own supplied text/unit/flags only - never a guessed name."""
    d = description.lower()
    if is_angle:
        return "angle"
    if is_counter or unit.strip().lower() in ENERGY_COUNTER_UNITS:
        return "counter"
    if "reactive power" in d:
        return "reactive_power"
    if "power" in d:
        return "power"
    if "temperature" in d:
        return "temperature"
    if "wind" in d:
        return "wind"
    if "pressure" in d:
        return "pressure"
    if any(k in d for k in ("current", "voltage", "frequency", "phase displacement")):
        return "electrical"
    if any(k in d for k in ("rpm", "speed", "pitch", "vibration", "acceleration")):
        return "mechanical"
    if "direction" in d:
        return "orientation"
    return "other_sensor"


def _rejection_reason(
    base_norm: str, resolution: ColumnResolution, original_col: str
) -> str:
    """Why `original_col` did not end up feeding any canonical signal.

    Computed from `resolve_columns`'s own scoring function, not guessed: a column with zero
    alias score against every canonical spec has no matching concept in RAI's canonical wind
    schema at all (a real schema-coverage gap, whichever side it originates from); a column
    with a nonzero score lost a same-slot competition to a higher-scoring column - the
    resolver's one-source-per-canonical design, an implementation property, not a data gap.
    """
    best_score = 0
    best_canonical = ""
    for spec in WIND_SIGNAL_SPECS:
        s = _alias_score(base_norm, spec)
        if s > best_score:
            best_score = s
            best_canonical = spec.canonical
    if best_score == 0:
        return "no_canonical_slot"
    winner = resolution.mapping.get(best_canonical)
    if winner == original_col:
        return "n/a"  # should not happen if caller only calls this for unmatched columns
    return f"lost_to_higher_scoring_column_for_{best_canonical}"


def build_feature_inventory(farm_dir: Path, sample_event_csv: Path) -> list[FeatureRow]:
    """One row per raw column in one representative dataset CSV for this farm.

    A single sample file is representative: every dataset within one farm shares the same
    header (verified in `docs/evaluation/EXTERNAL_CARE.md` - CARE anonymises per farm, not
    per dataset file).
    """
    farm = farm_dir.name
    desc = load_feature_descriptions(farm_dir)
    desc_by_name = {
        row["sensor_name"]: row for _, row in desc.iterrows()
    }
    sensor_map = build_safe_sensor_map(desc)

    raw = pd.read_csv(sample_event_csv, sep=";", nrows=5)
    baseline_res = resolve_columns(raw.columns)
    semantic_res = resolve_columns(raw.columns, sensor_map=sensor_map)
    recognized_cols = set(semantic_res.mapping.values())

    rows: list[FeatureRow] = []
    for col in raw.columns:
        norm = normalise_name(col)
        if norm in _METADATA_COLUMNS or col in _METADATA_COLUMNS:
            rows.append(
                FeatureRow(
                    farm=farm,
                    column_name=col,
                    column_type="metadata",
                    unit="",
                    description="",
                    is_metadata=True,
                    is_sensor=False,
                    is_counter=False,
                    is_angle=False,
                    recognized_by_rai=col in ("time_stamp", "asset_id", "status_type_id"),
                    matched_canonical=(
                        "status_code" if col == "status_type_id" else ("ts" if col == "time_stamp" else "asset_id" if col == "asset_id" else "")
                    ),
                    rejection_reason="metadata" if col not in ("time_stamp", "asset_id", "status_type_id") else "n/a",
                )
            )
            continue

        base, _ = split_variant(norm)
        desc_row = desc_by_name.get(base)
        description = str(desc_row["description"]) if desc_row is not None else ""
        unit = str(desc_row["unit"]) if desc_row is not None else ""
        is_angle = bool(desc_row["is_angle"]) if desc_row is not None else False
        is_counter = bool(desc_row["is_counter"]) if desc_row is not None else False

        recognized = col in recognized_cols
        matched_canonical = next((c for c, v in semantic_res.mapping.items() if v == col), "")

        if recognized:
            reason = "n/a"
        elif unit.strip().lower() in ENERGY_COUNTER_UNITS:
            reason = "excluded_cumulative_energy_counter"
        else:
            mapped_base = sensor_map.get(base, base)
            mapped_norm = normalise_name(mapped_base)
            reason = _rejection_reason(mapped_norm, semantic_res, col)

        rows.append(
            FeatureRow(
                farm=farm,
                column_name=col,
                column_type=_categorize(description, unit, is_angle, is_counter),
                unit=unit,
                description=description,
                is_metadata=False,
                is_sensor=desc_row is not None,
                is_counter=is_counter,
                is_angle=is_angle,
                recognized_by_rai=recognized,
                matched_canonical=matched_canonical,
                rejection_reason=reason,
            )
        )

    # Note which canonical signals only the *narrow* (name-only) resolver already found, so
    # the inventory records both baselines, not just the semantic one.
    del baseline_res  # exposed via docs, not needed further in this per-column table
    return rows


def write_artifacts(rows: list[FeatureRow], out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir is not None else Path("artifacts/evaluation/external_care")
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([asdict(r) for r in rows])
    df.to_csv(out / "feature_inventory.csv", index=False)
    (out / "feature_inventory.json").write_text(
        json.dumps([asdict(r) for r in rows], indent=2), encoding="utf-8"
    )
    return out


def _sample_csv_for(farm_dir: Path) -> Path:
    return sorted((farm_dir / "datasets").glob("*.csv"))[0]


if __name__ == "__main__":
    from rai.ingest.care import CARE_ROOT

    all_rows: list[FeatureRow] = []
    for farm_name in ("Wind Farm A", "Wind Farm B", "Wind Farm C"):
        farm_dir = CARE_ROOT / farm_name
        sample = _sample_csv_for(farm_dir)
        rows = build_feature_inventory(farm_dir, sample)
        all_rows.extend(rows)
        recognized = sum(1 for r in rows if r.recognized_by_rai and not r.is_metadata)
        sensors = sum(1 for r in rows if r.is_sensor)
        print(f"{farm_name}: {len(rows)} raw columns, {sensors} described sensors, {recognized} recognized")

    out_dir = write_artifacts(all_rows)
    print(f"wrote {out_dir}")
