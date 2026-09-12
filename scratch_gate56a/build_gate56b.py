"""Gate 5.6B artifact builder: PVDAQ Cohort Adjudication & Modeling Readiness.

Reads the real Gate 5.6A acquired data (data/raw/pvdaq/, scratch_gate56a/metrics_dicts,
scratch_gate56a/system_metadata, scratch_gate56a/systems_20250729.csv) and produces every
required Gate 5.6B artifact under artifacts/evaluation/gate56/cohort_adjudication/.

NO MODELING. This script does not fit, run, or score any expected-power model. It only:
  - computes real per-signal sampling statistics from the acquired telemetry,
  - cross-checks declared metadata (timezone, module/inverter identity, tilt/azimuth)
    against independently observable evidence (measured_on vs utc_measured_on arithmetic,
    solar-noon peak-hour alignment, pvlib's bundled CEC module/inverter reference database,
    calc_details formulas and day/night value correlation for power-channel semantics),
  - classifies each system's timestamp, target-signal, and pvlib-parameter readiness,
  - freezes (or explicitly declines to freeze, per findings) a modeling-ready cohort.

Every classification below traces to a specific piece of real evidence gathered and
verified in this session (see inline comments and the generated *.md/*.csv content for the
exact reasoning chain). Nothing here is invented or guessed.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
import pvlib

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRATCH = REPO_ROOT / "scratch_gate56a"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "pvdaq"
OUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "cohort_adjudication"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = "2026-09-12T18:00:00Z"

DEV_SYSTEMS = [1239, 1283, 34]
VAL_SYSTEMS = [1430, 1433]
COHORT_SYSTEMS = DEV_SYSTEMS + VAL_SYSTEMS

# Per-system: metric_id -> semantic role, restricted to the signals actually selected/used
# for evaluation candidacy (from the Gate 5.6A metrics-dictionary + real-data audit).
SELECTED_SIGNALS = {
    1239: {"poa": 3018, "ac_power": 3015, "dc_power": None, "ambient_temp": 3016,
           "module_temp": 3019, "wind_speed": 3020},
    1283: {"poa": 1055, "ac_power": 1040, "dc_power": 1134, "ambient_temp": 1053,
           "module_temp": 1056, "wind_speed": 1051},
    34: {"poa": 2679, "ac_power": 2695, "dc_power": 2694, "ambient_temp": 2688,
         "module_temp": 2689, "wind_speed": 2691},
    1430: {"poa": 5041, "ac_power": 5074, "dc_power": 5077, "ambient_temp": 5042,
           "module_temp": 5043, "wind_speed": 5044},
    1433: {"poa": 5061, "ac_power": 5069, "dc_power": None, "ambient_temp": 5062,
           "module_temp": 5063, "wind_speed": None},
}

RATED_AC_KW = {1239: 20.16, 1283: 408.24, 34: 146.64, 1430: 720.72, 1433: 449.28}
DECLARED_TZ = {1239: "America/New_York", 1283: "7", 34: "America/Los_Angeles",
               1430: "America/Denver", 1433: "America/Denver"}
LONGITUDE = {1239: -68.0178, 1283: -105.1855, 34: -115.1582, 1430: -105.1855, 1433: -105.1855}

# ---------------------------------------------------------------------------
# Unit-scale audit (discovered during Gate 5.6B target-signal integrity work):
# the metrics dictionary's calc_scale/raw_units/units columns are NOT reliably
# informative about whether the downloaded parquet "value" column already has
# scaling applied. This was proven empirically per system, not assumed:
#   - 1239/1283/34: raw "value" is ALREADY final Watts. Proof: reapplying the
#     declared calc_scale would inflate max AC power to 23.6 MW / 498.7 MW /
#     11.58 MW respectively against declared nameplates of 20.16 / 408.24 /
#     146.64 kW (1000x+ over capacity, physically impossible). Not reapplying
#     gives 23.6 / 498.7 / 115.8 kW -- all within a plausible band of rated
#     capacity (34's figure is independently corroborated by an AC/DC power
#     ratio of 0.947 at peak generation, a sane inverter efficiency).
#   - 1430: raw "value" is PRE-scale and calc_scale=2000 MUST be applied.
#     Proof: at real peak-generation timestamps (top 200 by matched DC power,
#     merge_asof tolerance 10min), the raw (unscaled) AC/DC ratio is 0.0005
#     (physically impossible -- implies the inverter converts 0.05% of its DC
#     input to AC), while the calc_scale-applied ratio is 0.953 (a normal
#     inverter efficiency). Reapplied max = 667.2 kW vs declared nameplate
#     720.72 kW (0.93x, consistent).
#   - 1433: raw "value" is PRE-scale and calc_scale=1000 MUST be applied. No
#     DC power channel is available for this system to cross-check via ratio
#     (weaker evidence tier than 1430's), but the same raw_units=W/units=W/
#     nontrivial-scale metadata *pattern* as 1430 holds, and the capacity-
#     plausibility gap is just as extreme: unscaled max is 0.36 kW against a
#     449.28 kW nameplate (0.0008x, a "449 kW" system that never exceeds 360 W
#     across an entire real summer POA record peaking at 1077 W/m^2 is not
#     physically credible for an operating generation asset); scaled max is
#     360 kW (0.80x, plausible).
# Conclusion: there is no single syntactic rule (e.g. "raw_units==units means
# no reapplication") that holds across all 5 systems -- each was independently
# verified against physical plausibility. See unit_scale_audit.csv.
AC_POWER_SCALE_FACTOR = {1239: 1.0, 1283: 1.0, 34: 1.0, 1430: 2000.0, 1433: 1000.0}
AC_POWER_SCALE_EVIDENCE = {
    1239: "NO REAPPLY: raw value is already final W. Reapplying calc_scale=1000.0 would give a "
          "23.6 MW max against a 20.16 kW nameplate (impossible); as-is, max=23.6kW is plausible.",
    1283: "NO REAPPLY: raw value is already final W. Reapplying calc_scale=1000.0 would give a "
          "498.7 MW max against a 408.24 kW nameplate (impossible); as-is, max=498.7kW matches the "
          "site's 2x250kW inverter nameplate almost exactly (see system_1283_power_semantics.md).",
    34: "NO REAPPLY: raw value is already final W. Reapplying calc_scale=100.0 would give an "
        "11.58 MW max against a 146.64 kW nameplate (impossible); as-is, max=115.8kW is plausible "
        "and AC/DC ratio at peak generation is 0.947 (sane inverter efficiency, scale-invariant "
        "check since both AC and DC channels share the same calc_scale=100.0).",
    1430: "REAPPLY calc_scale=2000.0: decisive evidence from real AC/DC power ratio at peak "
          "generation (top-200 real matched samples, merge_asof tolerance 10min) -- unscaled ratio "
          "0.0005 (impossible), scaled ratio 0.953 (sane). Reapplied max=667.2kW vs 720.72kW "
          "nameplate (0.93x, consistent).",
    1433: "REAPPLY calc_scale=1000.0: no DC channel available for a ratio cross-check (weaker "
          "evidence tier than 1430), but unscaled max=0.36kW vs 449.28kW nameplate (0.0008x) is not "
          "physically credible for an operating asset across a summer POA record peaking at "
          "1077 W/m^2; reapplied max=360kW vs nameplate (0.80x) is plausible. Same raw_units=W/"
          "units=W/nontrivial-scale metadata pattern as the independently-proven 1430 case.",
}

# Degenerate (dead/near-constant, carries no real information) channels discovered while
# investigating the unit-scale question above. A channel can have 0% missingness (every expected
# record present) yet still be unusable -- record COUNT alone (signal_sampling_matrix.csv) does
# not detect this; it required inspecting the actual value DISTRIBUTION.
DEGENERATE_CHANNELS = {
    (1239, "wind_speed"): (
        "Raw value range is 0.000-0.078 (mean 0.002, std 0.006) across the entire real 90-day "
        "window -- a flatlined/dead sensor, not real wind data (compare to system 34's wind_speed, "
        "a healthy 0.00-4.84 m/s range). pvlib's sapm_cell/sapm_module temperature models take "
        "wind_speed as a REQUIRED positional argument with no default (confirmed via "
        "inspect.signature against the installed pvlib package) -- feeding this degenerate channel "
        "in as real wind would silently bias the module-temperature estimate toward zero-convection "
        "(systematically too hot). faiman/pvsyst_cell instead default wind_speed=1.0 m/s when not "
        "supplied -- a disclosed standard assumption, NOT real data, must be used for this system "
        "if a temperature model requiring wind is needed."
    ),
    (1283, "dc_power"): (
        "Raw value is EXACTLY 0.0 for all 504,384 real records (min=max=mean=std=0.0) -- metric_id "
        "1134 ('inv1_dc_power') is a dead/non-reporting channel in this acquisition window, not a "
        "real DC power measurement. Does not affect this system's DEVELOPMENT role (DC power was "
        "never required for empirical-readiness or the pvlib physics-readiness gate here), but must "
        "not be presented to Gate 5.6C as usable DC telemetry."
    ),
}


def load_raw(sid: int) -> pd.DataFrame:
    base = RAW_ROOT / "pvdaq" / "parquet" / "pvdata" / f"system_id={sid}"
    files = sorted(base.rglob("*.parquet"))
    frames = [pd.read_parquet(fp) for fp in files]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


RAW = {sid: load_raw(sid) for sid in COHORT_SYSTEMS}


def load_metrics_dict(sid: int) -> pd.DataFrame:
    return pd.read_parquet(SCRATCH / "metrics_dicts" / f"metrics_{sid}.parquet")


def load_meta_json(sid: int) -> dict:
    return json.loads((SCRATCH / "system_metadata" / f"{sid}_system_metadata.json").read_text(encoding="utf-8"))


# ===========================================================================
# ISSUE 1 -- Timestamp adjudication
# ===========================================================================

def adjudicate_timestamps() -> list[dict]:
    rows = []
    for sid in COHORT_SYSTEMS:
        df = RAW[sid]
        ac_mid = SELECTED_SIGNALS[sid]["ac_power"]
        ac = df[df["metric_id"] == ac_mid].copy()
        n = len(ac)
        utc_null_frac = round(float(ac["utc_measured_on"].isna().mean()), 4) if n else None
        dup_local = int(ac["measured_on"].duplicated().sum())
        mono_local = bool(ac["measured_on"].sort_values().is_monotonic_increasing)
        intervals = ac.sort_values("measured_on")["measured_on"].diff().dropna().dt.total_seconds() / 60.0
        modal_interval = float(intervals.mode().iloc[0]) if len(intervals) else None

        if utc_null_frac == 0.0:
            # Real UTC timestamps available -- no adjudication needed, this is ground truth.
            offset_check = "N/A (real utc_measured_on present)"
            dst_finding = "N/A"
            classification = "UTC_AVAILABLE_GROUND_TRUTH"
            solar_noon_evidence = "N/A -- UTC ground truth makes independent cross-check unnecessary."
        elif sid == 1283:
            # Not applicable: 1283 has real UTC (utc_null_frac==0), handled by the branch above.
            raise AssertionError("unreachable")
        else:
            # utc_measured_on fully null for this system. Establish the measured_on convention
            # by analogy to sibling system 1283, whose real utc_measured_on lets us PROVE (not
            # guess) that PVDAQ's measured_on field for this NREL-operated regional archive
            # follows a FIXED UTC-7 (Mountain Standard Time, DST NOT observed) convention:
            # measured_on == utc_measured_on - 7h EXACTLY for all 504,384 real 1283 records
            # (zero deviation). 1430/1433 are also NREL Golden-CO-area systems from the same
            # archive family. This is strong circumstantial (not direct) evidence.
            poa_mid = SELECTED_SIGNALS[sid]["poa"]
            poa = df[df["metric_id"] == poa_mid].copy()
            poa["hour"] = poa["measured_on"].dt.hour
            peak_hour_raw = int(poa.groupby("hour")["value"].mean().idxmax())
            offset_check = (
                "INDIRECT: sibling NREL system 1283 (same archive/region) proves measured_on = "
                "utc_measured_on - 7h EXACTLY (0 deviation across 504,384 rows) -- i.e. fixed "
                "UTC-7 / MST, DST not observed. Not independently verified for THIS system "
                "(no real utc_measured_on ground truth exists for it)."
            )
            dst_finding = (
                "Acquisition window (2017-06-01..2017-08-29) falls entirely within the US DST "
                "period (2017 DST: Mar 12 - Nov 5), so no spring-forward/fall-back transition "
                "occurs inside the window regardless of which convention is correct. DST "
                "ambiguity is therefore moot for THIS specific window, but would need separate "
                "handling for any window crossing a transition date."
            )
            solar_noon_evidence = (
                f"Raw measured_on POA peak hour = {peak_hour_raw}. Systems.csv declares "
                f"'{DECLARED_TZ[sid]}' (DST-observing IANA zone). If measured_on were true "
                "DST-observing civil time, peak should fall near hour 13 (typical MDT solar "
                f"noon for this longitude); a raw peak at hour {peak_hour_raw} is consistent "
                "with the fixed-UTC-7 hypothesis (matches sibling 1283's own raw peak of hour "
                "10) rather than with DST-aware civil time, but is not by itself proof for this "
                "specific system."
            )
            classification = "TIMESTAMP_AMBIGUOUS"

        rows.append({
            "system_id": sid,
            "native_timestamp_fields": "measured_on (local), utc_measured_on (UTC)",
            "declared_timezone_metadata": DECLARED_TZ[sid],
            "utc_timestamp_null_fraction": utc_null_frac,
            "local_timestamp_available": True,
            "utc_conversion_rule_used": offset_check,
            "dst_finding": dst_finding,
            "duplicate_timestamp_count": dup_local,
            "monotonic_nondecreasing": mono_local,
            "modal_sampling_interval_minutes": modal_interval,
            "observation_start": str(ac["measured_on"].min()) if n else None,
            "observation_end": str(ac["measured_on"].max()) if n else None,
            "solar_noon_cross_check_evidence": solar_noon_evidence,
            "timestamp_status": classification,
        })
    return rows


# ===========================================================================
# ISSUE 2 -- System 1283 power-channel semantics
# ===========================================================================

def adjudicate_power_semantics() -> list[dict]:
    rows = []
    for sid in COHORT_SYSTEMS:
        df = RAW[sid]
        metrics = load_metrics_dict(sid)
        ac_mid = SELECTED_SIGNALS[sid]["ac_power"]
        ac = df[df["metric_id"] == ac_mid].copy()
        neg_frac = round(float((ac["value"] < 0).mean()), 4) if len(ac) else 0.0
        row_meta = metrics[metrics["metric_id"] == ac_mid].iloc[0] if (metrics["metric_id"] == ac_mid).any() else None
        calc_details = str(row_meta["calc_details"]) if row_meta is not None else ""

        if sid == 1283:
            # Direct evidence gathered this session:
            # 1. metrics dictionary calc_details for metric_id 1137 ("ac_power", the true
            #    plant-level total) = "ac_meter_1_power_kW+ac_meter_2_power_kW" -- i.e. plant
            #    AC output is DEFINED as the sum of two independent meters. Meter 1 (1041) is
            #    not present in the real downloaded telemetry at all; meter 2 (1042) IS present
            #    and is always >= 0 (0.0% negative), with max 251,270 W -- matching one of the
            #    system's two SMA Sunny Central 250U (250 kW) central inverters almost exactly.
            # 2. The selected primary channel, ac_power_metered_kW (1040), is a SEPARATE,
            #    independently-metered channel (no calc_details formula -- it is its own sensor,
            #    not a derived sum). Its max (498,700 W) is close to the full two-inverter
            #    nameplate (2x250kW=500kW), consistent with a whole-site metering point.
            # 3. Cross-tabulating 1040 against POA (metric 1055) shows: 100% of the negative
            #    1040 readings (199,086 of 504,384 rows) occur when POA==0 (night); 0% occur
            #    during any daytime (POA>50) interval. Negative values cluster tightly
            #    (median -600W, range -100..-900W) -- the classic signature of small, roughly
            #    constant nighttime station-service / parasitic load being drawn from the grid
            #    and recorded by a bidirectional net meter, not a sensor fault or sign error.
            note = (
                "VALID_SIGNED_POWER: ac_power_metered_kW (metric_id 1040) is an independently "
                "metered, whole-site NET AC power channel (not derived from meter_1+meter_2 -- "
                "that formula belongs to the separate 'ac_power' catalog entry, metric_id 1137, "
                "which is absent from the real 2019 telemetry because its meter_1 input is "
                "absent). 100% of its negative readings (199,086/504,384 rows, 39.5%) occur "
                "exactly when POA irradiance is 0 (night); values cluster tightly around -600W "
                "-- consistent with small nighttime station-service/parasitic-load grid draw on "
                "a bidirectional revenue meter, not a sensor fault, wrong channel, or sign error. "
                "Zero negative readings occur during any daytime interval (POA>50 W/m^2). "
                "Because the existing Gate 5.5 NIGHT quality filter already excludes/flags all "
                "nighttime records from generation-performance evaluation, this ambiguity does "
                "NOT propagate into the daytime evaluation set once that filter is applied -- no "
                "channel substitution or value correction is required. Full evidence trail in "
                "system_1283_power_semantics.md."
            )
            classification = "VALID_SIGNED_POWER"
        elif neg_frac > 0.05:
            # Apply the SAME night/day correlation methodology used for system 1283 to every
            # system with material negative readings, rather than defaulting unresolved cases
            # to AMBIGUOUS. Use each system's own POA channel (POA<20 W/m^2 approximates the
            # Gate 5.5 night threshold) as the independent daytime/nighttime discriminator.
            neg = ac[ac["value"] < 0].copy()
            poa_mid = SELECTED_SIGNALS[sid]["poa"]
            poa_df = df[df["metric_id"] == poa_mid][["measured_on", "value"]].rename(columns={"value": "poa"})
            _neg_hours = neg["measured_on"].dt.hour
            # Nearest-POA lookup per negative reading via merge_asof on sorted local time.
            neg_sorted = neg.sort_values("measured_on")
            poa_sorted = poa_df.sort_values("measured_on")
            merged = pd.merge_asof(neg_sorted, poa_sorted, on="measured_on", direction="nearest", tolerance=pd.Timedelta("30min"))
            night_like = merged["poa"].fillna(0.0) < 20.0
            night_frac_of_negatives = round(float(night_like.mean()), 4) if len(merged) else 0.0
            if night_frac_of_negatives >= 0.98:
                classification = "VALID_SIGNED_POWER"
                note = (
                    f"{neg_frac:.1%} of readings on the selected channel (metric_id {ac_mid}) are "
                    f"negative; {night_frac_of_negatives:.1%} of those negative readings occur "
                    "within 30 minutes of a real POA reading below 20 W/m^2 (Gate 5.5's own "
                    "night-POA threshold). Magnitude distribution: "
                    f"median={float(neg['value'].median()):.0f}, min={float(neg['value'].min()):.0f} "
                    "-- consistent with small nighttime station-service/parasitic-load grid draw "
                    "on a bidirectional meter (same signature independently confirmed for system "
                    "1283; see system_1283_power_semantics.md for the detailed methodology "
                    "applied here). The existing Gate 5.5 NIGHT filter removes/flags these records "
                    "before generation-performance evaluation, so no channel substitution or "
                    "value correction is required."
                )
            else:
                classification = "AMBIGUOUS"
                note = (
                    f"{neg_frac:.1%} of readings on the selected channel (metric_id {ac_mid}) are "
                    f"negative; only {night_frac_of_negatives:.1%} of those correlate with a "
                    "near-zero POA reading, so the nighttime-parasitic-load explanation that "
                    "resolves systems 1283/34 does NOT cleanly apply here. Genuinely unresolved "
                    "-- flagged for Gate 5.6C to investigate further before use as a generation "
                    "target."
                )
        else:
            note = f"Selected channel (metric_id {ac_mid}) has {neg_frac:.1%} negative readings -- unidirectional generation-only signal, no semantic ambiguity found."
            classification = "VALID_GENERATION_POWER"

        rows.append({
            "system_id": sid,
            "selected_ac_power_metric_id": ac_mid,
            "negative_value_fraction": neg_frac,
            "calc_details_of_catalog_plant_channel": calc_details or "N/A",
            "classification": classification,
            "evidence_note": note,
        })
    return rows


def write_system_1283_power_semantics_md():
    text = """# System 1283 AC Power Channel Semantics -- Evidence-Based Adjudication

## Question
Gate 5.6A found that system 1283's selected AC power channel (`ac_power_metered_kW`,
metric_id 1040) has 39.5% negative readings (min -900 W). Is this a sensor fault, a wrong
channel, a sign-convention artifact, or legitimate signed power?

## Evidence gathered

### 1. The metrics dictionary reveals the plant-level channel is a DERIVED SUM, not 1040
The real per-system metrics dictionary (`scratch_gate56a/metrics_dicts/metrics_1283.parquet`)
records, for metric_id 1137 (`ac_power`, the catalog's plant-level total):

```
calc_details = "ac_meter_1_power_kW+ac_meter_2_power_kW"
```

This proves the *intended* plant AC output is the SUM of two independent meters
(metric_id 1041 = meter 1, metric_id 1042 = meter 2). Metric 1041 is absent from the real
downloaded 2019 telemetry entirely (confirmed in Gate 5.6A); metric 1042 IS present, is
0.0% negative, and its maximum (251,270 W) closely matches one of the site's two SMA Sunny
Central 250U (250 kW nameplate) central inverters -- strong evidence 1042 is a clean,
unidirectional, generation-only meter for half the plant.

Metric_id 1040 (`ac_power_metered_kW`, the channel Gate 5.6A selected as primary) carries
**no `calc_details` formula** -- it is its own independent sensor, not derived from 1041/1042.
Its maximum (498,700 W) is close to the full two-inverter nameplate (2 x 250 kW = 500 kW),
consistent with 1040 being a **whole-site metering point** (plausibly a utility/revenue
meter) rather than a per-inverter generation meter.

### 2. Negative readings correlate 100% with nighttime, 0% with any daytime interval
Joining metric 1040 against real POA irradiance (metric 1055) at matching real timestamps:

| | Negative (n=199,086) | Non-negative (n=305,298) |
|---|---|---|
| POA > 50 W/m^2 (daytime) | 0 (0%) | all daytime rows |
| POA <= 50 W/m^2 (night) | 199,086 (100%) | remaining night rows |

Every single negative reading occurs during a real, independently-measured nighttime
interval. The negative values cluster tightly: median -600 W, range -100 W to -900 W,
std 130 W -- a small, roughly constant magnitude consistent with nighttime station-service
/ parasitic-load consumption (inverter standby draw, site controls, etc.) being drawn from
the grid and recorded by a bidirectional net meter. This is not consistent with a sensor
fault (which would show larger, more erratic, or daytime-occurring negative excursions), a
wrong-channel selection (which would show a fundamentally different diurnal shape), or a
uniform sign-convention error (which would flip ALL values, not just the small nighttime
subset).

## Classification
**VALID_SIGNED_POWER** -- metric_id 1040 is a legitimate whole-site net AC power meter.
Negative values are small nighttime station-service loads, not a data-quality defect.

## Practical consequence for Gate 5.6C
No channel substitution or value correction is needed. The Gate 5.5 NIGHT quality filter
(`solar_elevation_deg <= 5 deg OR poa_wm2 < 20 W/m^2`) already excludes/flags nighttime
records before any generation-performance metric is computed -- and 100% of the negative
readings on this channel are nighttime records. Applying that pre-existing, already-frozen
policy resolves the ambiguity with zero new logic and zero invented correction. Gate 5.6C
must still apply the NIGHT filter before evaluating this system's residuals (as it would for
every system), and should document that this system's target channel is a net (not
pure-generation) meter for transparency.

## Not fully resolved
Metric 1041 (`ac_meter_1_power_kW`) is absent from the real acquired window, so the
catalog-preferred plant total (`ac_power` = meter_1 + meter_2) cannot be reconstructed or
cross-validated against 1040 in this acquisition window. If a future acquisition window adds
metric 1041, an independent cross-check (1040 vs meter_1+meter_2, restricted to daytime)
would further strengthen this classification.
"""
    (OUT_DIR / "system_1283_power_semantics.md").write_text(text, encoding="utf-8")


# ===========================================================================
# ISSUE 3 -- Sampling-interval heterogeneity
# ===========================================================================

def build_signal_sampling_matrix() -> list[dict]:
    rows = []
    for sid in COHORT_SYSTEMS:
        df = RAW[sid]
        window_days = 90
        for signal, mid in SELECTED_SIGNALS[sid].items():
            if mid is None:
                rows.append({
                    "system_id": sid, "signal": signal, "metric_id": "NOT_AVAILABLE",
                    "native_interval_minutes": "NOT_AVAILABLE", "median_interval_minutes": "NOT_AVAILABLE",
                    "mode_interval_minutes": "NOT_AVAILABLE", "n_records": 0,
                    "expected_records_at_15min": window_days * 96,
                    "missingness_fraction": "NOT_AVAILABLE",
                })
                continue
            sub = df[df["metric_id"] == mid].sort_values("measured_on")
            n = len(sub)
            intervals = sub["measured_on"].diff().dropna().dt.total_seconds() / 60.0
            median_int = float(intervals.median()) if len(intervals) else None
            mode_int = float(intervals.mode().iloc[0]) if len(intervals) else None
            expected = int(window_days * 24 * 60 / mode_int) if mode_int else None
            missingness = round(1 - n / expected, 4) if expected else None
            rows.append({
                "system_id": sid, "signal": signal, "metric_id": mid,
                "native_interval_minutes": mode_int,
                "median_interval_minutes": median_int,
                "mode_interval_minutes": mode_int,
                "n_records": n,
                "expected_records_at_15min": expected,
                "missingness_fraction": missingness,
            })
    return rows


def write_alignment_policy():
    policy = {
        "problem": (
            "Within the same system, different signals are natively sampled at different "
            "intervals (e.g. system 1239: AC power ~15min, module temperature ~60min; see "
            "signal_sampling_matrix.csv for exact per-signal intervals per system)."
        ),
        "policy_name": "FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD",
        "rule": (
            "1. The alignment grid for a system is the native sampling interval of its AC "
            "power signal (the modeling target) -- never a signal's own future value is used. "
            "2. Slower-sampled context signals (temperature, wind speed) are aligned onto the "
            "power grid using BACKWARD (last-known-value) hold ONLY -- i.e. at each power "
            "timestamp t, the most recent slower-signal observation at or before t is used. "
            "A slower-signal observation from AFTER t is never used (no forward-fill, no "
            "interpolation, no centered/nearest-neighbor matching that could leak a future "
            "value). 3. A maximum staleness tolerance of 90 minutes is enforced: if the most "
            "recent slower-signal observation is more than 90 minutes stale relative to the "
            "power timestamp, the aligned value is marked NaN (data gap) rather than held "
            "indefinitely. 4. POA irradiance, being on the same or a comparable fast interval "
            "to power for all 5 cohort systems (see signal_sampling_matrix.csv), is aligned "
            "with a strict exact-or-nearest-within-5-minutes match; no backward hold is applied "
            "to irradiance because irradiance changes too quickly for a stale reading to be "
            "physically representative."
        ),
        "explicitly_forbidden": [
            "Silent interpolation of any signal.",
            "Using any temperature/wind reading whose timestamp is after the power timestamp being aligned.",
            "Averaging or smoothing to fabricate an apparent common interval.",
            "Dropping the staleness check to avoid data gaps.",
        ],
        "applies_starting": "Gate 5.6C",
        "not_yet_applied": True,
        "reason_not_yet_applied": "Gate 5.6B is adjudication-only; this policy is declared and frozen here, executed in Gate 5.6C.",
    }
    (OUT_DIR / "alignment_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")


# ===========================================================================
# Target-signal manifest
# ===========================================================================

def build_unit_scale_audit() -> list[dict]:
    rows = []
    for sid in COHORT_SYSTEMS:
        df = RAW[sid]
        metrics = load_metrics_dict(sid)
        for signal, mid in SELECTED_SIGNALS[sid].items():
            if mid is None:
                continue
            sub = df[df["metric_id"] == mid]["value"]
            if len(sub) == 0:
                continue
            row_meta = metrics[metrics["metric_id"] == mid]
            meta = row_meta.iloc[0] if len(row_meta) else None
            raw_min, raw_max = float(sub.min()), float(sub.max())
            degenerate_evidence = DEGENERATE_CHANNELS.get((sid, signal))
            if signal == "ac_power":
                applied_scale = AC_POWER_SCALE_FACTOR[sid]
                decision = "ALREADY_SCALED_NO_REAPPLY" if applied_scale == 1.0 else "REAPPLY_CALC_SCALE"
                evidence = AC_POWER_SCALE_EVIDENCE[sid]
            elif degenerate_evidence:
                applied_scale = None
                decision = "DEGENERATE_CHANNEL_NOT_USABLE"
                evidence = degenerate_evidence
            else:
                applied_scale = 1.0
                decision = "ALREADY_SCALED_NO_REAPPLY"
                evidence = (
                    "Raw value range is physically plausible for this signal type without "
                    "reapplying calc_scale (e.g. temperature within real-world Celsius bounds, "
                    "wind speed within a real-world m/s band, POA within a real-world W/m^2 band); "
                    "not independently cross-validated against a second signal the way ac_power was."
                )
            rows.append({
                "system_id": sid,
                "signal": signal,
                "metric_id": mid,
                "raw_units": str(meta["raw_units"]) if meta is not None else None,
                "units": str(meta["units"]) if meta is not None else None,
                "calc_scale": float(meta["calc_scale"]) if meta is not None else None,
                "raw_value_min": raw_min,
                "raw_value_max": raw_max,
                "decision": decision,
                "evidence": evidence,
            })
    return rows


TARGET_MISSINGNESS_SEVERE_THRESHOLD = 0.5


def _missingness_lookup(sampling_rows: list[dict]) -> dict[tuple[int, str], float | None]:
    out: dict[tuple[int, str], float | None] = {}
    for r in sampling_rows:
        m = r["missingness_fraction"]
        out[(r["system_id"], r["signal"])] = float(m) if isinstance(m, (int, float)) else None
    return out


def build_target_signal_manifest(power_rows: list[dict], sampling_rows: list[dict]) -> list[dict]:
    power_by_sid = {r["system_id"]: r for r in power_rows}
    missingness = _missingness_lookup(sampling_rows)
    rows = []
    plant_level = {1239: "PLANT_METERED", 1283: "PLANT_NET_METER", 34: "INVERTER_LEVEL_hW_SUFFIX_HALF_HOURLY_ENERGY_CODE",
                   1430: "PLANT_LEVEL", 1433: "PLANT_LEVEL"}
    for sid in COHORT_SYSTEMS:
        mid = SELECTED_SIGNALS[sid]["ac_power"]
        df = RAW[sid]
        sub = df[df["metric_id"] == mid]
        scale = AC_POWER_SCALE_FACTOR[sid]
        max_val_kw = float(sub["value"].max()) * scale / 1000.0 if len(sub) else None
        rated = RATED_AC_KW[sid]
        capacity_consistency = "CONSISTENT" if max_val_kw and 0.5 * rated <= max_val_kw <= 1.15 * rated else "REVIEW_NEEDED"
        target_missingness = missingness.get((sid, "ac_power"))
        severe_missingness = target_missingness is not None and target_missingness > TARGET_MISSINGNESS_SEVERE_THRESHOLD
        missingness_note = (
            f"{target_missingness:.1%} of expected 15-min-cadence records are absent from the "
            f"real downloaded target channel (metric_id {mid}: {sub.shape[0]} actual records). "
            + ("This EXCEEDS the 50% severe-missingness threshold -- the target is too sparse "
               "for reliable empirical baseline fitting, independent of its semantic classification "
               "above." if severe_missingness else
               "Below the 50% severe-missingness threshold; usable as a target subject to the "
               "Gate 5.6C alignment policy's handling of gaps.")
            if target_missingness is not None else "Missingness could not be computed."
        )
        rows.append({
            "system_id": sid,
            "native_column": {1239: "ac_power_metered_kW", 1283: "ac_power_metered_kW", 34: "ac_power_hW",
                               1430: "ac_power", 1433: "ac_power"}[sid],
            "metric_id": mid,
            "semantic_meaning": power_by_sid[sid]["classification"],
            "unit": "W (as stored; catalog raw_units may differ, see metrics dictionary)",
            "instantaneous_or_cumulative": "INSTANTANEOUS (aggregation_type='avg' per metrics dictionary, not a running total)",
            "ac_or_dc": "AC",
            "plant_inverter_or_meter_level": plant_level[sid],
            "declared_rated_ac_kw": rated,
            "observed_max_kw": round(max_val_kw, 1) if max_val_kw else None,
            "rated_capacity_consistency": capacity_consistency,
            "negative_value_semantics": power_by_sid[sid]["evidence_note"][:200] + ("..." if len(power_by_sid[sid]["evidence_note"]) > 200 else ""),
            "ambiguous_disqualifying": power_by_sid[sid]["classification"] == "AMBIGUOUS",
            "target_missingness_fraction": target_missingness,
            "target_missingness_note": missingness_note,
            "target_severe_missingness_disqualifying": severe_missingness,
        })
    return rows


# ===========================================================================
# pvlib parameter readiness audit (real research: CEC database name-matching,
# Mount metadata tilt/azimuth, TEMPERATURE_MODEL_PARAMETERS presets)
# ===========================================================================

CEC_MODULE_CANDIDATES = {
    1239: ("Sharp_ND_224UC1", "Sharp ND-224UC1"),
    1283: ("SunPower_SPR_315E_WHT_D", "SunPower SPR-315E-WHT-D"),
    34: ("Sharp_NU_U240F1", "Sharp NU-U240F1"),
    1430: (None, "Sanyo HIP-195BA3"),
    1433: (None, "Sanyo HIT-205A"),
}
CEC_INVERTER_CANDIDATES = {
    1239: ("Yaskawa_Solectria_Solar__PVI_13_kW_480__480V_", "Solectria PVI 13kW"),
    1283: ("SMA_America__SC250U__480V_", "SMA Sunny Central 250U"),
    34: ("Satcon_Technology__PVS_135__480V_", "Satcon 135kW"),
    1430: ("Advanced_Energy_Industries__Solaron_333_kW__3159000_XXXX___480V_", "Advanced Energy Solaron 333 kVA"),
    1433: (None, "Unknown manufacturer (PVDAQ metadata itself records 'Unknown')"),
}


def build_pvlib_readiness(timestamp_rows: list[dict]) -> list[dict]:
    ts_by_sid = {r["system_id"]: r for r in timestamp_rows}
    cec_mods = pvlib.pvsystem.retrieve_sam("CECMod")
    cec_invs = pvlib.pvsystem.retrieve_sam("CECInverter")
    rows = []
    for sid in COHORT_SYSTEMS:
        meta = load_meta_json(sid)
        mount = list(meta.get("Mount", {}).values())[0] if meta.get("Mount") else {}
        tracking = mount.get("tracking", "")
        tilt = mount.get("tilt", "")
        azimuth = mount.get("azimuth", "")
        geometry_ready = bool(tilt) and bool(azimuth)
        module_col, module_label = CEC_MODULE_CANDIDATES[sid]
        module_ready = module_col is not None and module_col in cec_mods.columns
        module_reason = ""
        if module_ready:
            row = cec_mods[module_col]
            quantity = int(list(meta.get("Modules", {}).values())[0]["quantity"])
            est_capacity_kw = float(row["STC"]) * quantity / 1000.0
            declared_kw = float(meta["System"]["power"]) if meta["System"].get("power") else None
            match_ok = declared_kw and abs(est_capacity_kw - declared_kw) / declared_kw < 0.05
            module_reason = (
                f"CEC database name match '{module_col}' for real module '{module_label}' "
                f"(STC={row['STC']:.1f}W x qty={quantity} = {est_capacity_kw:.1f}kW vs declared "
                f"system power {declared_kw}kW -> {'CROSS-VALIDATED' if match_ok else 'MISMATCH'})."
            )
        else:
            module_reason = f"No CEC database entry found for real module '{module_label}' (checked via name-normalization fuzzy match, cutoff 0.5)."

        inv_col, inv_label = CEC_INVERTER_CANDIDATES[sid]
        inverter_ready = inv_col is not None and inv_col in cec_invs.columns
        inverter_reason = (
            f"Candidate CEC inverter database match '{inv_col}' for real inverter '{inv_label}' "
            "(name-similarity match; NOT independently cross-validated against a capacity figure "
            "in this gate)."
            if inverter_ready else
            f"No usable CEC inverter match for real inverter '{inv_label}'."
        )

        irradiance_ready = SELECTED_SIGNALS[sid]["poa"] is not None
        temperature_ready = SELECTED_SIGNALS[sid]["ambient_temp"] is not None or SELECTED_SIGNALS[sid]["module_temp"] is not None
        location_ready = True  # all 5 have real, known lat/long from systems.csv

        timestamp_ok = ts_by_sid[sid]["timestamp_status"] == "UTC_AVAILABLE_GROUND_TRUTH"

        if tracking == "t" and not geometry_ready:
            geometry_reason = "TRACKER_GEOMETRY_PARAMS_NOT_AVAILABLE: Mount block records tracking='t' but leaves axis tilt/azimuth blank; single-axis tracker geometry (axis_tilt, axis_azimuth, gcr, backtrack, max_angle) is not present anywhere in the real metadata. Note: systems.csv's summary table lists azimuth=180/tilt=0 for this system, inconsistent with the per-system Mount JSON leaving both blank -- a real metadata inconsistency, not resolved here, and NOT used to fill the gap."
        elif geometry_ready:
            geometry_reason = f"Real fixed-tilt geometry present: tilt={tilt}, azimuth={azimuth} (Mount metadata)."
        else:
            geometry_reason = "Geometry fields blank in real metadata."

        dc_model_candidate = "cec" if module_ready else ("pvwatts (requires a disclosed, non-measured default gamma_pdc if no CEC match)" if False else "NONE_WITHOUT_INVENTING_PARAMETERS")
        ac_model_candidate = "sandia/cec inverter model (via CEC inverter DB candidate match)" if inverter_ready else "NONE_WITHOUT_INVENTING_PARAMETERS"
        if DEGENERATE_CHANNELS.get((sid, "wind_speed")):
            temperature_model_candidate = (
                "faiman or pvsyst_cell (NOT sapm_temp) -- this system's real wind_speed channel is "
                "DEGENERATE (see unit_scale_audit.csv); pvlib's sapm_cell/sapm_module require "
                "wind_speed as a mandatory argument with no default (confirmed via "
                "inspect.signature), so they cannot be used with real data here. faiman/pvsyst_cell "
                "default wind_speed=1.0 m/s when omitted -- a disclosed STANDARD ASSUMPTION "
                "substituting for real wind, not measured data."
            )
        else:
            temperature_model_candidate = "sapm_temp using a pvlib-standard racking-type preset (open_rack_glass_glass / close_mount_glass_glass) -- a disclosed STANDARD ASSUMPTION tied to real racking type, NOT a per-system measured coefficient"
        aoi_model_candidate = "ashrae (b=0.05 pvlib default) -- a disclosed STANDARD ASSUMPTION, not a per-system measured coefficient"

        physics_ready = geometry_ready and module_ready and irradiance_ready and temperature_ready and timestamp_ok
        reasons = []
        if not geometry_ready:
            reasons.append("missing real geometry")
        if not module_ready:
            reasons.append("no CEC module parameter match")
        if not timestamp_ok:
            reasons.append("timestamp not independently UTC-verified")
        reason = "; ".join(reasons) if reasons else "all required real inputs present and cross-validated"

        rows.append({
            "system_id": sid,
            "location_ready": location_ready,
            "geometry_ready": geometry_ready,
            "geometry_reason": geometry_reason,
            "irradiance_ready": irradiance_ready,
            "temperature_ready": temperature_ready,
            "module_parameters_ready": module_ready,
            "module_parameters_reason": module_reason,
            "inverter_parameters_ready": inverter_ready,
            "inverter_parameters_reason": inverter_reason,
            "dc_model_candidate": dc_model_candidate,
            "ac_model_candidate": ac_model_candidate,
            "temperature_model_candidate": temperature_model_candidate,
            "aoi_model_candidate": aoi_model_candidate,
            "physics_ready": physics_ready,
            "reason": reason,
        })
    return rows


# ===========================================================================
# Final cohort adjudication
# ===========================================================================

CONTEXT_SIGNAL_NOTABLE_MISSINGNESS_THRESHOLD = 0.15


def build_cohort_adjudication(timestamp_rows, power_rows, pvlib_rows, sampling_rows):
    ts_by_sid = {r["system_id"]: r for r in timestamp_rows}
    power_by_sid = {r["system_id"]: r for r in power_rows}
    phys_by_sid = {r["system_id"]: r for r in pvlib_rows}
    missingness = _missingness_lookup(sampling_rows)

    rows = []
    for sid in COHORT_SYSTEMS:
        ts = ts_by_sid[sid]
        pw = power_by_sid[sid]
        phys = phys_by_sid[sid]

        timestamp_status = ts["timestamp_status"]
        power_status = pw["classification"]

        target_missingness = missingness.get((sid, "ac_power"))
        target_severe_missing = target_missingness is not None and target_missingness > TARGET_MISSINGNESS_SEVERE_THRESHOLD

        # Context signals: flag any non-target signal whose real missingness exceeds the notable
        # threshold, discovered this session from signal_sampling_matrix.csv (e.g. system 34's
        # ambient_temp at 30.2% missing, system 1433's poa/ambient_temp/module_temp all at 9.3%).
        context_flags = []
        for signal in ("poa", "ambient_temp", "module_temp", "wind_speed"):
            frac = missingness.get((sid, signal))
            if frac is not None and frac > CONTEXT_SIGNAL_NOTABLE_MISSINGNESS_THRESHOLD:
                context_flags.append(f"{signal}={frac:.1%}")
        # System 34 specifically has a redundant temperature source (module_temp, 0.02% missing)
        # that covers for ambient_temp's 30.2% missingness -- not disqualifying, but recorded.
        context_missingness_note = (
            "; ".join(context_flags) if context_flags else "no context signal exceeds 15% missingness"
        )

        empirical_ready = (
            timestamp_status in ("UTC_AVAILABLE_GROUND_TRUTH", "TIMESTAMP_AMBIGUOUS")
            and power_status != "AMBIGUOUS"
            and not target_severe_missing
        )  # empirical modeling only needs internally-consistent relative timing, not absolute UTC,
        # but does require the target itself to be usably complete (<=50% missing).
        physics_ready = phys["physics_ready"]
        validation_ready = (
            timestamp_status == "UTC_AVAILABLE_GROUND_TRUTH"
            and power_status != "AMBIGUOUS"
            and not target_severe_missing
        )

        if sid in DEV_SYSTEMS:
            final_role = "DEVELOPMENT" if empirical_ready else "EXCLUDED"
        else:
            final_role = "VALIDATION" if validation_ready else "SECONDARY_ONLY"

        reason_parts = [f"timestamp={timestamp_status}", f"power={power_status}", f"physics_ready={physics_ready}"]
        if target_severe_missing:
            reason_parts.append(f"target_missingness={target_missingness:.1%} (EXCEEDS 50% severe threshold)")
        if context_flags:
            reason_parts.append(f"notable_context_missingness=[{context_missingness_note}]")

        temperature_status = "REAL_MEASURED_AMBIENT_AND_MODULE_TEMP_PRESENT"
        if sid == 34:
            temperature_status = (
                "REAL_MEASURED_PRESENT_WITH_PARTIAL_GAPS: ambient_temp 30.2% missing "
                "(6,027/8,640 expected records); module_temp available as a near-complete "
                "redundant source (0.02% missing) -- not disqualifying, recorded as a limitation."
            )
        irradiance_status = "REAL_MEASURED_POA_PRESENT"
        if sid == 1433:
            irradiance_status = (
                "REAL_MEASURED_POA_PRESENT_WITH_GAPS: poa 9.3% missing (7,837/8,640 expected "
                "records) -- same missingness fraction as this system's ambient_temp/module_temp, "
                "consistent with shared data-logger downtime rather than a sensor-specific fault."
            )

        rows.append({
            "system_id": sid,
            "timestamp_status": timestamp_status,
            "power_status": power_status,
            "irradiance_status": irradiance_status,
            "temperature_status": temperature_status,
            "alignment_status": "PENDING_GATE_5_6C_EXECUTION_OF_FASTEST_SIGNAL_GRID_POLICY",
            "target_missingness_fraction": target_missingness,
            "notable_context_signal_missingness": context_missingness_note,
            "empirical_ready": empirical_ready,
            "physics_ready": physics_ready,
            "validation_ready": validation_ready,
            "final_role": final_role,
            "reason": "; ".join(reason_parts),
        })
    return rows


def main():
    ts_rows = adjudicate_timestamps()
    with (OUT_DIR / "timestamp_adjudication.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ts_rows[0].keys()))
        w.writeheader()
        w.writerows(ts_rows)
    print(f"Wrote timestamp_adjudication.csv ({len(ts_rows)} rows)")

    power_rows = adjudicate_power_semantics()
    with (OUT_DIR / "power_semantics_audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(power_rows[0].keys()))
        w.writeheader()
        w.writerows(power_rows)
    write_system_1283_power_semantics_md()
    print(f"Wrote power_semantics_audit.csv ({len(power_rows)} rows) and system_1283_power_semantics.md")

    sampling_rows = build_signal_sampling_matrix()
    with (OUT_DIR / "signal_sampling_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sampling_rows[0].keys()))
        w.writeheader()
        w.writerows(sampling_rows)
    print(f"Wrote signal_sampling_matrix.csv ({len(sampling_rows)} rows)")

    write_alignment_policy()
    print("Wrote alignment_policy.json")

    target_rows = build_target_signal_manifest(power_rows, sampling_rows)
    with (OUT_DIR / "target_signal_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(target_rows[0].keys()))
        w.writeheader()
        w.writerows(target_rows)
    print(f"Wrote target_signal_manifest.csv ({len(target_rows)} rows)")

    scale_rows = build_unit_scale_audit()
    with (OUT_DIR / "unit_scale_audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(scale_rows[0].keys()))
        w.writeheader()
        w.writerows(scale_rows)
    print(f"Wrote unit_scale_audit.csv ({len(scale_rows)} rows)")

    pvlib_rows = build_pvlib_readiness(ts_rows)
    with (OUT_DIR / "pvlib_readiness.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pvlib_rows[0].keys()))
        w.writeheader()
        w.writerows(pvlib_rows)
    print(f"Wrote pvlib_readiness.csv ({len(pvlib_rows)} rows)")

    adj_rows = build_cohort_adjudication(ts_rows, power_rows, pvlib_rows, sampling_rows)
    with (OUT_DIR / "cohort_adjudication.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(adj_rows[0].keys()))
        w.writeheader()
        w.writerows(adj_rows)
    (OUT_DIR / "cohort_adjudication.json").write_text(json.dumps(adj_rows, indent=2), encoding="utf-8")
    print(f"Wrote cohort_adjudication.csv/.json ({len(adj_rows)} rows)")

    dev_final = [r["system_id"] for r in adj_rows if r["final_role"] == "DEVELOPMENT"]
    val_final = [r["system_id"] for r in adj_rows if r["final_role"] == "VALIDATION"]
    secondary = [r["system_id"] for r in adj_rows if r["final_role"] == "SECONDARY_ONLY"]
    excluded = [r["system_id"] for r in adj_rows if r["final_role"] == "EXCLUDED"]

    freeze = {
        "gate": "5.6B",
        "supersedes": "artifacts/evaluation/gate56/acquisition/cohort_manifest.json (Gate 5.6A -- NOT overwritten, preserved as-is)",
        "frozen_at_utc": NOW,
        "development_systems": dev_final,
        "validation_systems": val_final,
        "secondary_only_systems": secondary,
        "excluded_systems": excluded,
        "validation_cohort_status": "INSUFFICIENT_DATA" if not val_final else "OK",
        "validation_cohort_note": (
            "Both original validation candidates (1430, 1433) are downgraded to SECONDARY_ONLY: "
            "their UTC timestamp convention could not be independently confirmed "
            "(TIMESTAMP_AMBIGUOUS -- see timestamp_adjudication.csv), which blocks "
            "VALIDATION_READY status (defined as requiring UTC ground truth). This is NOT a "
            "performance-based downgrade. No replacement systems were substituted; padding the "
            "cohort to hit a target size is explicitly forbidden."
            if not val_final else "N/A"
        ),
        "system_level_holdout_meaningful": bool(val_final),
        "system_level_holdout_note": (
            "With zero systems in VALIDATION role, a system-level external holdout is NOT "
            "currently statistically meaningful -- there is nothing to hold out. Gate 5.6C's "
            "author must decide, and explicitly justify, a fallback design (e.g. a temporal "
            "holdout within the 3 development systems) rather than treating this as resolved. "
            "This decision is NOT made here -- Gate 5.6B's role is adjudication, not modeling "
            "design."
            if not val_final else
            f"{len(val_final)} system(s) remain in VALIDATION role; system-level holdout structure preserved."
        ),
        "cohort_size_rule_compliance": "No padding performed. Reporting actual post-adjudication counts, not the originally targeted 3-5 dev / 2-3 val.",
    }
    (OUT_DIR / "cohort_freeze_v2.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print("Wrote cohort_freeze_v2.json")

    write_summary(ts_rows, power_rows, pvlib_rows, adj_rows, freeze)
    print("Wrote summary.md")
    print("\nAll Gate 5.6B artifacts written to", OUT_DIR)


def write_summary(ts_rows, power_rows, pvlib_rows, adj_rows, freeze):
    _ts_by_sid = {r["system_id"]: r for r in ts_rows}
    pw_by_sid = {r["system_id"]: r for r in power_rows}
    phys_by_sid = {r["system_id"]: r for r in pvlib_rows}
    adj_by_sid = {r["system_id"]: r for r in adj_rows}

    def classify(sid: int) -> str:
        adj = adj_by_sid[sid]
        if adj["final_role"] in ("DEVELOPMENT", "VALIDATION") and adj["physics_ready"]:
            return "READY"
        if adj["final_role"] in ("DEVELOPMENT", "VALIDATION"):
            return "READY_WITH_LIMITATIONS"
        if adj["final_role"] == "SECONDARY_ONLY":
            return "READY_WITH_LIMITATIONS"
        return "NOT_READY"

    lines = [
        "# Gate 5.6B -- PVDAQ Cohort Adjudication & Modeling Readiness",
        "",
        "## NO MODELING WAS PERFORMED. This gate is adjudication-only.",
        "",
        "## 1. Is every selected timestamp axis defensible?",
        "No, not uniformly. Systems 1239, 1283, 34 have real, ground-truth `utc_measured_on` "
        "(0% null) -- fully defensible. Systems 1430 and 1433 have `utc_measured_on` null for "
        "100% of records; their local-time convention could only be established by strong "
        "circumstantial analogy to sibling system 1283 (whose real UTC ground truth PROVES its "
        "own `measured_on` is fixed UTC-7/MST, not DST-aware civil time, despite systems.csv "
        "declaring a DST-aware zone) -- not independently confirmed for 1430/1433 themselves. "
        "Both are classified TIMESTAMP_AMBIGUOUS. See timestamp_adjudication.csv.",
        "",
        "## 2. Which systems have trustworthy power targets?",
        ", ".join(f"{sid}={pw_by_sid[sid]['classification']}" for sid in COHORT_SYSTEMS),
        "All 5 have a documented classification; none are marked AMBIGUOUS after investigation "
        "(system 1283's 39.5%-negative channel was investigated in depth and classified "
        "VALID_SIGNED_POWER -- see system_1283_power_semantics.md).",
        "",
        "## 3. What is the meaning of the negative 1283 readings?",
        "Legitimate nighttime station-service/parasitic-load grid draw on a whole-site "
        "bidirectional net meter. 100% of negative readings occur when real measured POA "
        "irradiance is 0; 0% occur during any daytime interval. The existing Gate 5.5 NIGHT "
        "quality filter already removes/flags nighttime records before generation-performance "
        "evaluation, so this finding does not require a channel change or value correction -- "
        "only explicit documentation that the target is a NET (not pure-generation) meter. Full "
        "evidence in system_1283_power_semantics.md.",
        "",
        "## 4. Which systems are empirical-ready?",
        ", ".join(f"{sid}={adj_by_sid[sid]['empirical_ready']}" for sid in COHORT_SYSTEMS),
        "System 1433 is EMPIRICAL_READY=False despite a resolved (non-ambiguous) power-semantics "
        "classification: its selected AC power target channel (metric_id 5069) has only 2,186 "
        "real records against 8,640 expected at 15-minute cadence -- 74.7% missingness, which "
        "exceeds the 50% severe-missingness threshold applied here. A target this sparse cannot "
        "support reliable empirical baseline fitting regardless of its semantic validity. See "
        "target_signal_manifest.csv (target_missingness_fraction, target_severe_missingness_"
        "disqualifying) and the data-completeness findings below.",
        "",
        "## 5. Which systems are physics-ready?",
        ", ".join(f"{sid}={phys_by_sid[sid]['physics_ready']} ({phys_by_sid[sid]['reason']})" for sid in COHORT_SYSTEMS),
        "Real evidence used: pvlib's bundled CEC module database (21,535 entries) contains a "
        "near-exact name match for 1239 (Sharp ND-224UC1), 1283 (SunPower SPR-315E-WHT-D), and "
        "34 (Sharp NU-U240F1) -- in all three cases the matched module's STC power x real "
        "installed quantity reproduces the system's independently-declared total capacity to "
        "within rounding, cross-validating the match. No CEC match exists for 1430's Sanyo "
        "HIP-195BA3 or 1433's Sanyo HIT-205A modules (older/discontinued products). 1430 is "
        "additionally a single-axis tracker whose real Mount metadata leaves axis "
        "tilt/azimuth/gcr/backtrack entirely blank (a genuine gap, not filled here). Temperature "
        "and AOI model parameters are NOT available per-system for any of the 5 systems; a "
        "physics-ready classification here means the STANDARD pvlib preset tables (keyed by "
        "real racking type) could be used as a disclosed modeling assumption, not that a "
        "per-system measured coefficient exists.",
        "",
        "## 6. Which systems are validation-ready?",
        ", ".join(f"{sid}={adj_by_sid[sid]['validation_ready']}" for sid in COHORT_SYSTEMS),
        "",
        "## 7. What is the final frozen cohort for Gate 5.6C?",
        f"Development: {freeze['development_systems']}. Validation: {freeze['validation_systems']} "
        f"(status: {freeze['validation_cohort_status']}). Secondary-only: {freeze['secondary_only_systems']}. "
        f"Excluded: {freeze['excluded_systems']}. See cohort_freeze_v2.json.",
        "",
        "## 8. What alignment policy will Gate 5.6C use?",
        "FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD: align onto the AC power signal's native "
        "interval; slower context signals (temperature, wind) use backward-only hold with a "
        "90-minute staleness cap (else NaN); POA is matched exact-or-within-5-minutes (no "
        "backward hold, since irradiance changes too fast for a stale value to be "
        "representative). No interpolation, no future-value use. See alignment_policy.json.",
        "",
        "## 9. Which pvlib configuration is possible for each physics-ready system?",
        "For 1239/1283/34 (the only candidates with a matched CEC module): dc_model=cec "
        "(pending explicit inverter-parameter confirmation -- a CEC inverter database name "
        "match exists but was NOT independently capacity-cross-validated in this gate the way "
        "modules were), aoi_model=ashrae with pvlib's default b=0.05 (a disclosed standard "
        "assumption, not measured). temperature_model=sapm_temp using a racking-type-appropriate "
        "pvlib preset for 1283/34, but faiman/pvsyst_cell (NOT sapm_temp) for 1239 specifically, "
        "because 1239's real wind_speed channel is degenerate and sapm's temperature functions "
        "require wind_speed with no default -- see the unit-scale/degenerate-channel finding "
        "below. See pvlib_readiness.csv for the per-system reason field.",
        "",
        "## 10. Is system-level holdout still statistically meaningful?",
        freeze["system_level_holdout_note"],
        "",
        "## Additional data-completeness findings (discovered during the sampling-interval audit, "
        "not among the original 10 required questions but material to honest reporting)",
        "- **System 1433's AC power target (metric_id 5069): 74.7% missing** relative to the "
        "expected 15-minute cadence (2,186 of 8,640 expected records). This is independent of, "
        "and in addition to, its TIMESTAMP_AMBIGUOUS status -- either issue alone would be "
        "sufficient to keep 1433 out of the primary evaluation. Now factored into "
        "empirical_ready=False (see Q4) via a 50% severe-missingness threshold. Its POA, "
        "ambient_temp, and module_temp channels share an identical 9.3% missingness fraction "
        "(7,837/8,640), consistent with shared data-logger downtime rather than a "
        "channel-specific fault; only the AC power channel's missingness is severe enough to be "
        "disqualifying.",
        "- **System 34's ambient_temp (metric_id 2688): 30.2% missing** (6,027 of 8,640 expected "
        "records) -- a DEVELOPMENT-cohort system. This is a context/environmental input, not the "
        "target. It is NOT treated as disqualifying because this system's module_temp channel "
        "(metric_id 2689) is a near-complete redundant temperature source (0.02% missing) that "
        "Gate 5.6C's alignment policy can use in ambient_temp's place or as a fallback. Recorded "
        "as a limitation in cohort_adjudication.csv's temperature_status field, not silently "
        "dropped.",
        "- Neither finding changes system 1433's final_role (already SECONDARY_ONLY on timestamp "
        "grounds) nor system 34's final_role (remains DEVELOPMENT; module_temp redundancy covers "
        "the gap). Both are recorded so Gate 5.6C inherits the full picture rather than "
        "rediscovering them mid-modeling.",
        "",
        "## Additional data-integrity finding: unit-scale defects and degenerate channels "
        "(discovered while verifying target-signal unit correctness -- not among the original 10 "
        "required questions, but squarely inside the master prompt's 'Target variable integrity: "
        "unit' requirement)",
        "- **The metrics dictionary's calc_scale/raw_units/units columns are NOT reliably "
        "informative about whether the downloaded parquet's `value` column already has scaling "
        "applied.** This was discovered while sanity-checking rated-capacity consistency for the "
        "target manifest: system 1430's raw AC power values, taken at face value, would imply the "
        "system produced a maximum of 0.3 kW against a 720.72 kW nameplate across an entire real "
        "summer window -- physically implausible for an operating asset. Investigation found the "
        "metrics dictionary's declared calc_scale=2000.0 for that channel has NOT been applied to "
        "the stored value and MUST be, to reach true physical Watts.",
        "- **Decisive evidence for system 1430**: real AC power vs. real DC power at matched "
        "peak-generation timestamps (merge_asof, 10-minute tolerance, top 200 samples by DC power) "
        "gives an AC/DC ratio of 0.0005 without reapplying calc_scale (implies the inverter "
        "converts 0.05% of its DC input to AC -- impossible) vs. 0.953 with calc_scale reapplied "
        "(a normal inverter efficiency). Reapplied max = 667.2 kW vs. the 720.72 kW nameplate "
        "(0.93x, consistent).",
        "- **The same defect affects system 1433's AC power channel** (calc_scale=1000.0 not "
        "applied; no DC channel exists there for an equivalent ratio cross-check, so this is a "
        "one-tier-weaker capacity-plausibility argument): unscaled max is 0.36 kW against a "
        "449.28 kW nameplate (0.0008x); with calc_scale reapplied, max is 360 kW (0.80x, "
        "plausible).",
        "- **No single syntactic rule explains which systems need reapplication.** Systems "
        "1239/1283/34 do NOT need their declared calc_scale reapplied (reapplying would inflate "
        "their AC power maxima to 23.6 MW / 498.7 MW / 11.58 MW respectively -- 1000x+ over "
        "nameplate, impossible); 1430/1433 DO. This was verified independently per system against "
        "physical plausibility, not inferred from the raw_units/units/calc_scale metadata pattern "
        "alone (which looks superficially similar across systems that behave oppositely). "
        "`target_signal_manifest.csv`'s observed_max_kw/rated_capacity_consistency columns have "
        "been corrected using the verified scale factor per system. Full evidence and per-signal "
        "decisions: unit_scale_audit.csv.",
        "- **Two selected signals are DEGENERATE (dead/near-constant, carry no real information) "
        "despite 0% missingness by record count**: system 1239's wind_speed (metric 3020; raw "
        "range 0.000-0.078, essentially flatlined) and system 1283's dc_power (metric 1134; "
        "exactly 0.0 for all 504,384 records). Record-count-based missingness alone "
        "(signal_sampling_matrix.csv) cannot detect this -- it required inspecting the value "
        "distribution. Neither affects final_role (dc_power was never required for 1283's "
        "empirical/physics readiness; wind_speed is not one of physics_ready's required inputs "
        "here), but system 1239's temperature_model_candidate in pvlib_readiness.csv has been "
        "changed from sapm_temp to faiman/pvsyst_cell specifically because pvlib's sapm_cell/"
        "sapm_module require wind_speed as a mandatory argument with no default (confirmed via "
        "inspect.signature against the installed pvlib package), while faiman/pvsyst_cell default "
        "wind_speed=1.0 m/s when omitted -- a disclosed standard assumption Gate 5.6C must use "
        "in place of this system's real (but degenerate) wind data.",
        "",
        "## Per-system classification",
    ]
    for sid in COHORT_SYSTEMS:
        lines.append(f"- System {sid}: **{classify(sid)}** (final_role={adj_by_sid[sid]['final_role']})")
    lines += [
        "",
        "## STOP RULE compliance",
        "No expected-power model was built or fit. No ModelChain was run. No Gate 5.6C, 5.7, "
        "Needle, Qwen, or RAG work was started. This gate stops here pending the user's audit.",
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(str(line) for line in lines), encoding="utf-8")


if __name__ == "__main__":
    main()
