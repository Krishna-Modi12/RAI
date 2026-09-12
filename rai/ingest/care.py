"""CARE to Compare SCADA loader: column normalisation and quality filtering.

CARE to Compare (Zenodo 10958775, CC-BY-SA-4.0) is a labelled wind-turbine SCADA
benchmark covering three wind farms. Two properties of it drive this module's design:

* **Width.** Up to ~957 columns for one farm, because nearly every sensor is published
  four times as ``<sensor>_avg`` / ``_min`` / ``_max`` / ``_std`` over the 10-minute
  interval. We want ~9 signals out of that, so we resolve columns through an explicit,
  inspectable mapping table and prefer the ``avg`` variant. `resolve_columns` returns the
  decision it made for every canonical signal so a reviewer can audit the mapping instead
  of trusting positional guesswork.
* **Anonymisation and known quality caveats.** Farm B and C sensor names are anonymised
  (``sensor_41_avg``), and the authors document sensor drop-outs and status periods that
  are not what they claim. So: (a) an optional sidecar sensor map translates anonymised
  ids to physical meanings, and (b) `quality_filter` drops physically impossible values
  and non-normal operating states rather than feeding them to a residual model.

Nothing here downloads anything. The archive is ~5.5 GB; `discover` reports exactly what
is on disk and `CareDatasetAbsent` carries the acquisition instructions.

Attribution is mandatory under CC-BY-SA-4.0 - see `ATTRIBUTION`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from rai.ingest.registry import get_dataset

_SPEC = get_dataset("care")

ATTRIBUTION: Final = _SPEC.attribution
LICENCE: Final = _SPEC.licence
CARE_ROOT: Final[Path] = _SPEC.local_dir


class CareDatasetAbsent(FileNotFoundError):
    """Raised when no CARE files are on disk. Message carries the acquisition steps."""


# ---------------------------------------------------------------------------
# Canonical target schema (our wind telemetry contract)
# ---------------------------------------------------------------------------

CANONICAL_WIND_COLUMNS: Final[tuple[str, ...]] = (
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
)

#: Statistical variant to prefer, best first. CARE publishes avg/min/max/std per sensor;
#: the residual models are built on interval means.
VARIANT_PREFERENCE: Final[tuple[str, ...]] = ("avg", "mean", "", "max", "min", "std")

_VARIANT_RE = re.compile(r"^(?P<base>.*?)[_\s-]*(?P<variant>avg|mean|min|max|std|stddev)$")


@dataclass(frozen=True)
class WindSignalSpec:
    """How to find one canonical signal in a foreign SCADA table, and what is plausible.

    `aliases` are matched against the *normalised* base column name (lower_snake, variant
    suffix stripped). An exact alias match always beats a token-subset match.
    `reject_tokens` blocks look-alikes - without it, "gearbox_bearing_temperature" would
    happily answer to `main_bearing_temp_c`.
    """

    canonical: str
    unit: str
    aliases: tuple[str, ...]
    plausible_min: float | None = None
    plausible_max: float | None = None
    reject_tokens: tuple[str, ...] = ()
    is_angle: bool = False
    note: str = ""


#: The documented mapping table. Aliases are drawn from the naming conventions used by
#: Kelmarsh/Penmanshiel (descriptive), EDP (abbreviated) and CARE (anonymised + sidecar
#: descriptions), so the same table serves all three.
WIND_SIGNAL_SPECS: Final[tuple[WindSignalSpec, ...]] = (
    WindSignalSpec(
        canonical="power_kw",
        unit="kW",
        aliases=(
            "power",
            "active_power",
            "grid_production_power",
            "power_output",
            "p",
            "active_power_kw",
            "generated_power",
        ),
        plausible_min=-500.0,
        plausible_max=20_000.0,
        reject_tokens=("reactive", "apparent", "factor", "setpoint", "limit", "available"),
        note="Negative values are real (self-consumption when idle), so the floor is not 0.",
    ),
    WindSignalSpec(
        canonical="wind_speed_ms",
        unit="m/s",
        aliases=("wind_speed", "windspeed", "ws", "nacelle_wind_speed", "anemometer"),
        plausible_min=0.0,
        plausible_max=45.0,
        reject_tokens=("estimated", "corrected", "met_mast", "direction"),
    ),
    WindSignalSpec(
        canonical="wind_direction_deg",
        unit="deg",
        aliases=(
            "wind_direction",
            "winddirection",
            "wind_dir",
            "wd",
            "absolute_wind_direction",
            "nacelle_direction",
        ),
        plausible_min=0.0,
        plausible_max=360.0,
        is_angle=True,
        note="Angle: wrapped into [0, 360) rather than clipped, and averaged circularly.",
    ),
    WindSignalSpec(
        canonical="rotor_rpm",
        unit="rpm",
        aliases=("rotor_speed", "rotor_rpm", "rotor", "rs", "hub_speed"),
        plausible_min=0.0,
        plausible_max=60.0,
        reject_tokens=("generator", "gen_"),
        note="Rotor side only. Generator-side rpm is ~100x and must not be mapped here.",
    ),
    WindSignalSpec(
        canonical="pitch_angle_deg",
        unit="deg",
        aliases=("pitch_angle", "blade_pitch", "pitch", "blade_angle", "pitch_position"),
        plausible_min=-10.0,
        plausible_max=95.0,
        reject_tokens=("motor", "setpoint", "demand", "speed"),
    ),
    WindSignalSpec(
        canonical="ambient_temp_c",
        unit="degC",
        aliases=(
            "ambient_temperature",
            "ambient_temp",
            "outdoor_temperature",
            "external_temperature",
            "air_temperature",
            "temp_ambient",
        ),
        plausible_min=-40.0,
        plausible_max=60.0,
        reject_tokens=("nacelle", "gearbox", "generator", "bearing", "hub", "tower"),
    ),
    WindSignalSpec(
        canonical="nacelle_temp_c",
        unit="degC",
        aliases=("nacelle_temperature", "nacelle_temp", "temp_nacelle"),
        plausible_min=-30.0,
        plausible_max=90.0,
    ),
    WindSignalSpec(
        canonical="gearbox_oil_temp_c",
        unit="degC",
        aliases=(
            "gearbox_oil_temperature",
            "gear_oil_temperature",
            "gearbox_oil_temp",
            "gearbox_oil_sump_temperature",
            "hydraulic_oil_temperature_gearbox",
        ),
        plausible_min=-20.0,
        plausible_max=120.0,
        reject_tokens=("bearing", "inlet_pressure", "level", "hydraulic_oil_temperature_yaw"),
    ),
    WindSignalSpec(
        canonical="generator_winding_temp_c",
        unit="degC",
        aliases=(
            "generator_winding_temperature",
            "stator_winding_temperature",
            "generator_stator_temperature",
            "generator_phase_1_temperature",
            "gen_winding_temp",
        ),
        plausible_min=-20.0,
        plausible_max=200.0,
        reject_tokens=("bearing", "slip_ring", "cooling_air"),
    ),
    WindSignalSpec(
        canonical="main_bearing_temp_c",
        unit="degC",
        aliases=(
            "main_bearing_temperature",
            "rotor_bearing_temperature",
            "main_shaft_bearing_temperature",
            "front_bearing_temperature",
        ),
        plausible_min=-20.0,
        plausible_max=150.0,
        reject_tokens=("gearbox", "generator", "hydraulic"),
        note="Gearbox and generator bearings are separate signals and are rejected here.",
    ),
    WindSignalSpec(
        canonical="drivetrain_vibration_mms",
        unit="mm/s",
        aliases=(
            "drivetrain_vibration",
            "drive_train_vibration",
            "tower_acceleration",
            "vibration",
            "nacelle_vibration",
            "drive_train_acceleration",
        ),
        plausible_min=0.0,
        plausible_max=100.0,
        note=(
            "CARE exposes only low-rate vibration/acceleration proxies, not CMS "
            "spectra. Units differ between farms; treated as a relative trend signal."
        ),
    ),
    WindSignalSpec(
        canonical="status_code",
        unit="code",
        aliases=("status_type_id", "status_code", "status", "turbine_state", "state_fault"),
        note="Integer state id; see NORMAL_STATUS_IDS for what counts as normal.",
    ),
    WindSignalSpec(
        canonical="pressure_hpa",
        unit="hPa",
        aliases=("air_pressure", "pressure", "ambient_pressure", "barometric_pressure"),
        plausible_min=800.0,
        plausible_max=1100.0,
        reject_tokens=("oil", "hydraulic", "gearbox", "differential"),
    ),
    WindSignalSpec(
        canonical="humidity_pct",
        unit="%",
        aliases=("humidity", "relative_humidity", "rh"),
        plausible_min=0.0,
        plausible_max=100.0,
    ),
    WindSignalSpec(
        canonical="air_density",
        unit="kg/m3",
        aliases=("air_density", "density"),
        plausible_min=0.8,
        plausible_max=1.5,
    ),
)

SPECS_BY_CANONICAL: Final[dict[str, WindSignalSpec]] = {
    s.canonical: s for s in WIND_SIGNAL_SPECS
}

#: Timestamp column aliases. CARE uses `time_stamp`.
TS_ALIASES: Final[tuple[str, ...]] = (
    "time_stamp",
    "timestamp",
    "date_time",
    "datetime",
    "date_and_time",
    "ts",
    "time",
)

#: Asset identifier aliases. CARE uses `asset_id` (anonymised integer per turbine).
ASSET_ALIASES: Final[tuple[str, ...]] = (
    "asset_id",
    "turbine_id",
    "wind_turbine",
    "turbine",
    "wtg",
    "unit",
)

#: Bookkeeping columns CARE ships that we carry through untouched when present.
PASSTHROUGH_COLUMNS: Final[tuple[str, ...]] = ("id", "train_test", "status_type_id")

#: status_type_id values the CARE documentation describes as normal operation. Everything
#: else (curtailment, derating, errors, maintenance, communication loss) is excluded by
#: `quality_filter(drop_non_normal=True)`.
#:
#: This is read from the dataset's own documentation, not inferred. Re-check it against
#: the event_info/README in the copy you drop into data/raw/care/ - the authors note that
#: some labelled periods are imperfect, and `quality_filter` takes the set as an argument
#: precisely so you can override it without editing this module.
NORMAL_STATUS_IDS: Final[tuple[int, ...]] = (0, 2)


# ---------------------------------------------------------------------------
# Name normalisation and column resolution
# ---------------------------------------------------------------------------


def normalise_name(name: str) -> str:
    """Lower-snake a foreign column name: 'Gearbox Oil Temp. (avg)' -> 'gearbox_oil_temp_avg'."""
    s = str(name).strip().lower()
    s = re.sub(r"\[[^\]]*\]|\([^)]*\)", lambda m: " " + m.group(0)[1:-1] + " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def split_variant(name: str) -> tuple[str, str]:
    """Split a normalised column into (base, variant). Variant is '' when absent."""
    m = _VARIANT_RE.match(name)
    if not m:
        return name, ""
    variant = m.group("variant")
    return m.group("base").strip("_"), "avg" if variant == "mean" else (
        "std" if variant == "stddev" else variant
    )


def _tokens(name: str) -> list[str]:
    return [t for t in name.split("_") if t]


def _alias_score(base: str, spec: WindSignalSpec) -> int:
    """Higher is a better match; 0 means no match.

    Exact alias hit scores 1000. Otherwise an alias whose tokens are all present in the
    base scores by alias specificity minus the base's extra tokens, so a longer, more
    specific alias wins over a short generic one ('power' vs 'active_power').
    """
    base_tokens = _tokens(base)
    if any(rt in base for rt in spec.reject_tokens):
        return 0
    best = 0
    for alias in spec.aliases:
        a = normalise_name(alias)
        if base == a:
            return 1000
        at = _tokens(a)
        if at and all(t in base_tokens for t in at):
            extra = len(base_tokens) - len(at)
            best = max(best, 100 * len(at) - extra)
    return best


@dataclass
class ColumnResolution:
    """The mapping decision, exposed so it can be audited rather than trusted."""

    mapping: dict[str, str] = field(default_factory=dict)
    variant_used: dict[str, str] = field(default_factory=dict)
    score: dict[str, int] = field(default_factory=dict)
    ts_column: str | None = None
    asset_column: str | None = None
    unmatched: tuple[str, ...] = ()
    n_source_columns: int = 0

    def report(self) -> str:
        lines = [
            (f"resolved {len(self.mapping)}/{len(WIND_SIGNAL_SPECS)} signals "
            f"from {self.n_source_columns} source columns"),
            f"  ts -> {self.ts_column!r}   asset -> {self.asset_column!r}",
        ]
        for canonical in sorted(self.mapping):
            lines.append(
                f"  {canonical:<26} <- {self.mapping[canonical]!r} "
                f"[variant={self.variant_used.get(canonical) or 'none'}, "
                f"score={self.score.get(canonical)}]"
            )
        if self.unmatched:
            lines.append("  unmatched (left null): " + ", ".join(self.unmatched))
        return "\n".join(lines)


def _pick_plain(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    norm = {normalise_name(c): c for c in columns}
    for alias in aliases:
        a = normalise_name(alias)
        if a in norm:
            return norm[a]
    for alias in aliases:
        a = normalise_name(alias)
        for n, original in norm.items():
            if a in n:
                return original
    return None


def resolve_columns(
    columns: list[str] | pd.Index,
    sensor_map: dict[str, str] | None = None,
) -> ColumnResolution:
    """Decide which source column feeds each canonical signal.

    `sensor_map` translates anonymised CARE ids to descriptive names, e.g.
    ``{"sensor_41": "gearbox_oil_temperature"}``. It is applied to the *base* name before
    alias matching, so ``sensor_41_avg`` resolves through the alias table normally.
    """
    cols = [str(c) for c in columns]
    smap = {normalise_name(k): normalise_name(v) for k, v in (sensor_map or {}).items()}

    # candidates[canonical] = list of (score, variant_rank, base, original)
    candidates: dict[str, list[tuple[int, int, str, str]]] = {}
    for original in cols:
        norm = normalise_name(original)
        base, variant = split_variant(norm)
        base = smap.get(base, base)
        vrank = (
            VARIANT_PREFERENCE.index(variant)
            if variant in VARIANT_PREFERENCE
            else len(VARIANT_PREFERENCE)
        )
        for spec in WIND_SIGNAL_SPECS:
            s = _alias_score(base, spec)
            if s > 0:
                candidates.setdefault(spec.canonical, []).append((s, vrank, base, original))

    res = ColumnResolution(n_source_columns=len(cols))
    used: set[str] = set()
    # Resolve the highest-confidence signals first so a strong match claims its column
    # before a weaker signal can steal it.
    order = sorted(
        candidates,
        key=lambda c: -max(x[0] for x in candidates[c]),
    )
    for canonical in order:
        pool = [c for c in candidates[canonical] if c[3] not in used]
        if not pool:
            continue
        best = min(pool, key=lambda x: (-x[0], x[1], x[3]))
        score, vrank, base, original = best
        res.mapping[canonical] = original
        res.variant_used[canonical] = (
            VARIANT_PREFERENCE[vrank] if vrank < len(VARIANT_PREFERENCE) else ""
        )
        res.score[canonical] = score
        used.add(original)

    res.ts_column = _pick_plain(cols, TS_ALIASES)
    res.asset_column = _pick_plain(cols, ASSET_ALIASES)
    res.unmatched = tuple(
        s.canonical for s in WIND_SIGNAL_SPECS if s.canonical not in res.mapping
    )
    return res


# ---------------------------------------------------------------------------
# Angles
# ---------------------------------------------------------------------------


def wrap_deg(values: pd.Series | np.ndarray | float) -> pd.Series | np.ndarray | float:
    """Wrap any angle onto [0, 360). Handles negatives and >360 alike."""
    if isinstance(values, pd.Series):
        return values.mod(360.0)
    return np.mod(values, 360.0)


def circular_mean_deg(values: pd.Series | np.ndarray) -> float:
    """Mean of compass bearings. A plain mean of 350 and 10 gives 180, which is wrong."""
    arr = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype="float64")
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    rad = np.deg2rad(arr)
    return float(np.rad2deg(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360.0)


def angular_difference_deg(a: float, b: float) -> float:
    """Signed smallest difference a-b in (-180, 180]."""
    return float((a - b + 180.0) % 360.0 - 180.0)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def normalise_care_frame(
    df: pd.DataFrame,
    *,
    asset_id: str | None = None,
    asset_prefix: str = "CARE-WT",
    sensor_map: dict[str, str] | None = None,
    resolution: ColumnResolution | None = None,
) -> pd.DataFrame:
    """Project a raw CARE SCADA frame onto the canonical wind telemetry columns.

    Signals not present in the source are emitted as all-null columns, never filled.
    The `ColumnResolution` used is attached as ``df.attrs["resolution"]``.
    """
    res = resolution or resolve_columns(df.columns, sensor_map=sensor_map)
    out = pd.DataFrame(index=df.index)

    if res.ts_column is None:
        raise ValueError(
            "no timestamp column found; expected one of "
            f"{TS_ALIASES} among {list(df.columns)[:12]}..."
        )
    out["ts"] = pd.to_datetime(df[res.ts_column], utc=True, errors="coerce", format="mixed")

    if asset_id is not None:
        out["asset_id"] = asset_id
    elif res.asset_column is not None:
        out["asset_id"] = (
            df[res.asset_column].astype("string").map(lambda v: f"{asset_prefix}-{v}")
        )
    else:
        out["asset_id"] = f"{asset_prefix}-unknown"

    for spec in WIND_SIGNAL_SPECS:
        src = res.mapping.get(spec.canonical)
        if src is None:
            out[spec.canonical] = pd.Series([pd.NA] * len(df), dtype="Float64")
            continue
        values = pd.to_numeric(df[src], errors="coerce")
        if spec.is_angle:
            values = values.mod(360.0)
        out[spec.canonical] = values.astype("float64")

    if "status_code" in out.columns:
        out["status_code"] = out["status_code"].astype("Int64")

    out["operating_state"] = pd.Series([pd.NA] * len(df), dtype="string")
    if "status_code" in out.columns:
        known = out["status_code"].notna()
        out.loc[known, "operating_state"] = np.where(
            out.loc[known, "status_code"].isin(NORMAL_STATUS_IDS), "normal", "unknown"
        )

    for col in PASSTHROUGH_COLUMNS:
        match = _pick_plain(list(df.columns), (col,))
        if match is not None and col not in out.columns:
            out[f"care_{col}"] = df[match].to_numpy()

    ordered = list(CANONICAL_WIND_COLUMNS) + [
        c for c in out.columns if c not in CANONICAL_WIND_COLUMNS
    ]
    out = out.loc[:, [c for c in ordered if c in out.columns]]
    out = out.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    out.attrs["source"] = "care"
    out.attrs["licence"] = LICENCE
    out.attrs["attribution"] = ATTRIBUTION
    out.attrs["resolution"] = res
    return out


# ---------------------------------------------------------------------------
# Quality filtering
# ---------------------------------------------------------------------------


@dataclass
class QualityReport:
    """What the filter actually removed. Every number here is counted, not estimated."""

    rows_in: int = 0
    rows_out: int = 0
    values_nulled: dict[str, int] = field(default_factory=dict)
    rows_dropped_non_normal: int = 0
    rows_dropped_all_null: int = 0
    rows_dropped_duplicate_ts: int = 0
    frozen_signal_rows: dict[str, int] = field(default_factory=dict)

    def report(self) -> str:
        lines = [f"quality filter: {self.rows_in} -> {self.rows_out} rows"]
        if self.rows_dropped_non_normal:
            lines.append(f"  dropped {self.rows_dropped_non_normal} non-normal-state rows")
        if self.rows_dropped_duplicate_ts:
            lines.append(f"  dropped {self.rows_dropped_duplicate_ts} duplicate timestamps")
        if self.rows_dropped_all_null:
            lines.append(f"  dropped {self.rows_dropped_all_null} rows with no usable signal")
        for col, n in sorted(self.values_nulled.items(), key=lambda kv: -kv[1]):
            if n:
                lines.append(f"  nulled {n} out-of-range values in {col}")
        for col, n in sorted(self.frozen_signal_rows.items(), key=lambda kv: -kv[1]):
            if n:
                lines.append(f"  nulled {n} frozen-sensor values in {col}")
        return "\n".join(lines)


def quality_filter(
    df: pd.DataFrame,
    *,
    drop_non_normal: bool = True,
    normal_status_ids: tuple[int, ...] = NORMAL_STATUS_IDS,
    drop_duplicate_ts: bool = True,
    frozen_run_length: int | None = 12,
    required_signals: tuple[str, ...] = ("power_kw", "wind_speed_ms"),
) -> tuple[pd.DataFrame, QualityReport]:
    """Remove what a residual model must not learn from.

    Four things get removed, in this order:

    1. Values outside the physically plausible range for their signal -> null (not the
       whole row, so one bad thermocouple does not discard a good power reading).
    2. Runs of a byte-identical value longer than `frozen_run_length` intervals -> null.
       A sensor reading exactly 42.0 for two hours is stuck, not stable. Set to None to
       skip. Angles and integer state codes are exempt.
    3. Rows whose status code is not in `normal_status_ids` (curtailment, derating,
       errors, maintenance) when `drop_non_normal`.
    4. Rows with no usable value in `required_signals`, and duplicate timestamps.
    """
    rep = QualityReport(rows_in=len(df))
    out = df.copy()

    for spec in WIND_SIGNAL_SPECS:
        col = spec.canonical
        if col not in out.columns or col == "status_code":
            continue
        if spec.plausible_min is None and spec.plausible_max is None:
            continue
        values = pd.to_numeric(out[col], errors="coerce")
        bad = pd.Series(False, index=out.index)
        if spec.is_angle:
            # Angles are wrapped, not discarded; only non-finite values are unusable.
            out[col] = values.mod(360.0)
            rep.values_nulled[col] = 0
            continue
        if spec.plausible_min is not None:
            bad |= values < spec.plausible_min
        if spec.plausible_max is not None:
            bad |= values > spec.plausible_max
        rep.values_nulled[col] = int(bad.sum())
        out[col] = values.mask(bad)

    if frozen_run_length is not None and frozen_run_length > 0:
        for spec in WIND_SIGNAL_SPECS:
            col = spec.canonical
            if col not in out.columns or col == "status_code" or spec.is_angle:
                continue
            values = pd.to_numeric(out[col], errors="coerce")
            if values.notna().sum() < frozen_run_length:
                rep.frozen_signal_rows[col] = 0
                continue
            group = (values.ne(values.shift())).cumsum()
            run_len = values.groupby(group).transform("size")
            stuck = values.notna() & (run_len >= frozen_run_length)
            rep.frozen_signal_rows[col] = int(stuck.sum())
            out[col] = values.mask(stuck)

    if drop_non_normal and "status_code" in out.columns:
        codes = pd.to_numeric(out["status_code"], errors="coerce")
        keep = codes.isna() | codes.isin(list(normal_status_ids))
        rep.rows_dropped_non_normal = int((~keep).sum())
        out = out.loc[keep]

    present = [s for s in required_signals if s in out.columns]
    if present:
        usable = pd.concat(
            [pd.to_numeric(out[s], errors="coerce").notna() for s in present], axis=1
        ).any(axis=1)
        rep.rows_dropped_all_null = int((~usable).sum())
        out = out.loc[usable]

    if drop_duplicate_ts and "ts" in out.columns:
        before = len(out)
        out = out.drop_duplicates(subset=["ts", "asset_id"], keep="first")
        rep.rows_dropped_duplicate_ts = before - len(out)

    out = out.reset_index(drop=True)
    out.attrs.update(df.attrs)
    rep.rows_out = len(out)
    out.attrs["quality_report"] = rep
    return out, rep


# ---------------------------------------------------------------------------
# Discovery + loading
# ---------------------------------------------------------------------------


@dataclass
class CareInventory:
    """What is on disk under data/raw/care/ right now."""

    root: Path
    present: bool
    farms: dict[str, list[Path]] = field(default_factory=dict)
    event_info: list[Path] = field(default_factory=list)
    archives: list[Path] = field(default_factory=list)
    loose_csvs: list[Path] = field(default_factory=list)
    instructions: str = ""

    @property
    def n_csv(self) -> int:
        return sum(len(v) for v in self.farms.values()) + len(self.loose_csvs)

    def explain(self) -> str:
        if not self.present:
            return (
                f"CARE to Compare is not present at {self.root}.\n"
                f"Licence: {LICENCE}. Size: {_SPEC.approx_size} - deliberately not "
                "downloaded by this project.\n" + self.instructions
            )
        lines = [f"CARE to Compare found at {self.root}: {self.n_csv} CSV file(s)."]
        for farm, files in sorted(self.farms.items()):
            lines.append(f"  {farm}: {len(files)} dataset CSV(s)")
        if self.loose_csvs:
            lines.append(f"  (root): {len(self.loose_csvs)} CSV(s)")
        if self.event_info:
            lines.append(f"  event_info files: {len(self.event_info)}")
        if self.archives:
            lines.append(
                f"  {len(self.archives)} archive(s) still zipped - extract them first: "
                + ", ".join(p.name for p in self.archives[:4])
            )
        lines.append(f"Attribution required: {ATTRIBUTION}")
        return "\n".join(lines)


def discover(root: Path | None = None) -> CareInventory:
    """Detect-and-explain. Never raises; inspect `.present` and print `.explain()`."""
    base = Path(root) if root is not None else CARE_ROOT
    inv = CareInventory(root=base, present=False, instructions=_SPEC.instructions)
    if not base.exists():
        return inv

    archives = sorted(p for p in base.rglob("*.zip") if p.is_file())
    events: list[Path] = []
    farms: dict[str, list[Path]] = {}
    loose: list[Path] = []
    for p in sorted(base.rglob("*.csv")):
        if not p.is_file():
            continue
        name = p.name.lower()
        if "event" in name and "info" in name:
            events.append(p)
            continue
        rel = p.relative_to(base)
        if len(rel.parts) >= 2:
            farms.setdefault(rel.parts[0], []).append(p)
        else:
            loose.append(p)

    inv.farms = farms
    inv.event_info = events
    inv.archives = archives
    inv.loose_csvs = loose
    inv.present = bool(farms or loose or events or archives)
    return inv


def require_present(root: Path | None = None) -> CareInventory:
    inv = discover(root)
    if not inv.present:
        raise CareDatasetAbsent(inv.explain())
    return inv


def load_sensor_map(path: Path) -> dict[str, str]:
    """Load a sidecar map of anonymised CARE sensor ids to descriptive names.

    Accepts a two-column CSV (id, description) or a JSON object. Use it when you know
    what Wind Farm B's `sensor_41` actually is.
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        import json

        data = json.loads(p.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    raw = pd.read_csv(p)
    if raw.shape[1] < 2:
        raise ValueError(f"{p} needs at least two columns (sensor id, description)")
    return {
        str(a): str(b)
        for a, b in zip(raw.iloc[:, 0], raw.iloc[:, 1], strict=False)
        if pd.notna(a) and pd.notna(b)
    }


def load_care_csv(
    path: Path,
    *,
    asset_id: str | None = None,
    asset_prefix: str = "CARE-WT",
    sensor_map: dict[str, str] | None = None,
    apply_quality_filter: bool = True,
    nrows: int | None = None,
    **filter_kwargs: object,
) -> tuple[pd.DataFrame, ColumnResolution, QualityReport | None]:
    """Load one CARE dataset CSV into canonical wind columns.

    Returns (frame, resolution, quality_report). The resolution and report are returned
    rather than logged so the caller can put real counts in front of a human.
    """
    p = Path(path)
    if not p.exists():
        raise CareDatasetAbsent(
            f"{p} does not exist.\n{_SPEC.instructions}"
        )
    # The real archive is semicolon-delimited (verified against Zenodo record 14006163's
    # per-farm dataset CSVs) - comma is never used, so this is not a configurable guess.
    raw = pd.read_csv(p, sep=";", nrows=nrows, low_memory=False)
    res = resolve_columns(raw.columns, sensor_map=sensor_map)
    frame = normalise_care_frame(
        raw, asset_id=asset_id, asset_prefix=asset_prefix, resolution=res
    )
    if not apply_quality_filter:
        return frame, res, None
    filtered, rep = quality_filter(frame, **filter_kwargs)  # type: ignore[arg-type]
    return filtered, res, rep


def load_event_info(path: Path) -> pd.DataFrame:
    """Load a CARE event_info table (the anomaly labels) with parsed timestamps."""
    raw = pd.read_csv(Path(path), sep=";")
    for col in raw.columns:
        if "date" in col.lower() or "time" in col.lower():
            raw[col] = pd.to_datetime(raw[col], utc=True, errors="coerce", format="mixed")
    return raw
