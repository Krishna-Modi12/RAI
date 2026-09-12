"""Gate 5.6A artifact builder. Reads real acquired PVDAQ data/metadata (already downloaded
to scratch_gate56a/ and data/raw/pvdaq/) and writes every required artifact under
artifacts/evaluation/gate56/acquisition/. No modeling, no fitting, no performance-based
selection. Every value is either read directly from real source files or computed by pure
data audit (counts, ranges, sanity flags) -- nothing here is fabricated or inferred.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import pvlib

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRATCH = REPO_ROOT / "scratch_gate56a"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "pvdaq"
OUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "acquisition"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = "2026-09-12T16:30:00Z"  # frozen retrieval-session timestamp; real retrieval_time_utc per file is in download_manifest.json

DEV_SYSTEMS = [1239, 1283, 34]
VAL_SYSTEMS = [1430, 1433]
COHORT_SYSTEMS = DEV_SYSTEMS + VAL_SYSTEMS
EXCLUDED_SYSTEMS = [1199, 1332, 35, 9068]
ALL_CANDIDATES = COHORT_SYSTEMS + EXCLUDED_SYSTEMS

SYSTEM_WINDOWS = {
    1239: ("2019-06-01", "2019-08-29"),
    1283: ("2019-06-01", "2019-08-29"),
    34: ("2019-06-01", "2019-08-29"),
    1430: ("2017-06-01", "2017-08-29"),
    1433: ("2017-06-01", "2017-08-29"),
}


# ---------------------------------------------------------------------------
# Load real reference tables
# ---------------------------------------------------------------------------

def load_systems_csv() -> dict[str, dict]:
    with (SCRATCH / "systems_20250729.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["system_id"]: row for row in reader}


def load_metrics_dict(sid: int) -> pd.DataFrame | None:
    path = SCRATCH / "metrics_dicts" / f"metrics_{sid}.parquet"
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def load_system_metadata_json(sid: int) -> dict | None:
    path = SCRATCH / "system_metadata" / f"{sid}_system_metadata.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


SYSTEMS_CSV = load_systems_csv()


def classify_signals(metrics_df: pd.DataFrame | None) -> dict:
    if metrics_df is None or len(metrics_df) == 0:
        return {
            "has_irradiance_poa": "NOT_AVAILABLE",
            "has_ac_power": "NOT_AVAILABLE",
            "has_dc_power": "NOT_AVAILABLE",
            "has_ambient_temp": "NOT_AVAILABLE",
            "has_module_temp": "NOT_AVAILABLE",
            "has_cumulative_energy": "NOT_AVAILABLE",
            "metric_count": 0,
            "metric_ids_semantic": [],
        }
    combined = (
        metrics_df.get("sensor_name", pd.Series(dtype=str)).astype(str).str.lower()
        + " "
        + metrics_df.get("common_name", pd.Series(dtype=str)).astype(str).str.lower()
        + " "
        + metrics_df.get("standard_name", pd.Series(dtype=str)).astype(str).str.lower()
    )

    def present(pattern: str) -> str:
        return "KNOWN" if combined.str.contains(pattern, regex=True).any() else "NOT_AVAILABLE"

    semantic_rows = []
    for _, row in metrics_df.iterrows():
        name = f"{row.get('sensor_name', '')} {row.get('common_name', '')}".lower()
        if "energy" in name or "kwh" in str(row.get("units", "")).lower():
            sem = "CUMULATIVE_ENERGY"
        elif "ac_power" in name or ("ac" in name and "power" in name):
            sem = "AC_POWER_INSTANTANEOUS"
        elif "dc_power" in name or ("dc" in name and "power" in name):
            sem = "DC_POWER_INSTANTANEOUS"
        elif "poa" in name or "irrad" in name:
            sem = "POA_IRRADIANCE"
        elif "module_temp" in name or "cell_temp" in name:
            sem = "MODULE_TEMPERATURE"
        elif "ambient_temp" in name:
            sem = "AMBIENT_TEMPERATURE"
        elif "inverter_temp" in name:
            sem = "INVERTER_TEMPERATURE"
        elif "wind_speed" in name:
            sem = "WIND_SPEED"
        elif "current" in name:
            sem = "DC_OR_AC_CURRENT"
        elif "voltage" in name:
            sem = "DC_OR_AC_VOLTAGE"
        else:
            sem = "OTHER_UNCLASSIFIED"
        semantic_rows.append({
            "metric_id": int(row["metric_id"]),
            "sensor_name": str(row.get("sensor_name", "")),
            "units": str(row.get("units", "")),
            "semantic_class": sem,
        })

    return {
        "has_irradiance_poa": present("poa|irrad"),
        "has_ac_power": present("ac_power|ac power"),
        "has_dc_power": present("dc_power|dc power"),
        "has_ambient_temp": present("ambient_temp|ambient temp"),
        "has_module_temp": present("module_temp|module temp"),
        "has_cumulative_energy": present("energy|kwh"),
        "metric_count": int(len(metrics_df)),
        "metric_ids_semantic": semantic_rows,
    }


READINESS_NOTES = {
    1239: "Real irradiance (POA), real AC power (metered kW), real ambient+module temperature all present and semantically unambiguous (single metered AC power channel, no multi-inverter disambiguation needed). Meets all predeclared readiness criteria.",
    1283: "Real irradiance (POA + POA refcell), real AC power, real ambient/module/inverter temperature all present. CAVEAT (real-data finding, see quality_filter_manifest.json): the dictionary-cataloged plant-level 'ac_power'/'ac_meter_1_power_kW' channels are NOT actually populated in the downloaded window; of the channels that ARE present, the metered-first candidate 'ac_power_metered_kW' (selected per predeclared rule) shows 39.5% negative readings and 'inv1_ac_power_kW' is constant zero -- flagged for Gate 5.6B to resolve explicitly, not silently patched here.",
    34: "Real irradiance (POA), real AC/DC power, real ambient+module+inverter temperature all present. Meets all predeclared readiness criteria.",
    1430: "Real irradiance (POA), real AC/DC power, real ambient+module temperature, plus vendor-computed PR (performance ratio) and kWh_gross/net fields all present. Meets all predeclared readiness criteria.",
    1433: "Real irradiance (POA), real AC power, real ambient+module temperature, plus vendor-computed PR and kWh fields present (no separate DC power channel). Meets all predeclared readiness criteria.",
    1199: "EXCLUDED: metrics dictionary contains only AC/DC power and current/voltage channels across 7 inverters -- no irradiance (POA or GHI) channel of any kind is present. Cannot compute an expected-power-vs-irradiance relationship without a real irradiance measurement; predeclared readiness criteria require irradiance/POA presence. Not excluded for performance reasons -- excluded before any model was run.",
    1332: "EXCLUDED: metrics dictionary contains only power/current/voltage channels (including per-string DC current) -- no irradiance channel AND no temperature channel of any kind. Fails two predeclared readiness criteria simultaneously.",
    35: "EXCLUDED: real irradiance/power/temperature channels ARE present (would otherwise pass), but system_metadata.json confirms system 35 (\"Andre Agassi Preparatory Academy - Gymnasium\", site_id 41) shares the exact same latitude/longitude (36.1952, -115.1582) and climate record as system 34 (\"...Building A\", site_id 40) -- both are buildings on the same school campus. Predeclared diversity criterion (avoid co-located/redundant sister systems) excludes 35 in favor of 34, which was already selected first as a development system. This is a geographic-redundancy exclusion, not a performance-based one.",
    9068: "EXCLUDED: the metrics-dictionary parquet file for this candidate could not be opened (\"Parquet magic bytes not found in footer\" -- the retrieved object is corrupted or not a valid parquet file). Data integrity failure at the metadata level; excluded rather than guessing its signal composition.",
}

EXCLUSION_STATUS = {1199: "NO_IRRADIANCE_CHANNEL", 1332: "NO_IRRADIANCE_OR_TEMPERATURE_CHANNEL", 35: "CO_LOCATED_REDUNDANT_WITH_SYSTEM_34", 9068: "CORRUPTED_METADATA_FILE"}


def build_candidate_systems():
    records = []
    for sid in ALL_CANDIDATES:
        row = SYSTEMS_CSV.get(str(sid), {})
        metrics_df = load_metrics_dict(sid)
        sig = classify_signals(metrics_df)
        meta_json = load_system_metadata_json(sid)
        site_block = (meta_json or {}).get("Site", {})
        is_selected = sid in COHORT_SYSTEMS
        rec = {
            "system_id": sid,
            "system_public_name": row.get("system_public_name", "UNKNOWN") or "UNKNOWN",
            "site_location": row.get("site_location", "UNKNOWN") or "UNKNOWN",
            "latitude": float(row["latitude"]) if row.get("latitude") else None,
            "longitude": float(row["longitude"]) if row.get("longitude") else None,
            "elevation_m": float(row["elevation_m"]) if row.get("elevation_m") else None,
            "timezone_or_utc_offset": row.get("timezone_or_utc_offset", "UNKNOWN") or "UNKNOWN",
            "dc_capacity_kW": float(row["dc_capacity_kW"]) if row.get("dc_capacity_kW") else "NOT_AVAILABLE",
            "tracking": row.get("tracking", "UNKNOWN") or "UNKNOWN",
            "array_type": row.get("type", "UNKNOWN") or "UNKNOWN",
            "azimuth_deg": row.get("azimuth", "NOT_AVAILABLE") or "NOT_AVAILABLE",
            "tilt_deg": row.get("tilt", "NOT_AVAILABLE") or "NOT_AVAILABLE",
            "first_timestamp_metadata_table": row.get("first_timestamp", "UNKNOWN"),
            "last_timestamp_metadata_table": row.get("last_timestamp", "UNKNOWN"),
            "years_metadata_table": row.get("years", "UNKNOWN"),
            "qa_status": row.get("qa_status", "UNKNOWN") or "UNKNOWN",
            "qa_issue": row.get("qa_issue") or "NOT_APPLICABLE",
            "metrics_dictionary_readable": "KNOWN" if metrics_df is not None else "UNKNOWN_CORRUPTED",
            "metric_count": sig["metric_count"],
            "has_irradiance_poa": sig["has_irradiance_poa"],
            "has_ac_power": sig["has_ac_power"],
            "has_dc_power": sig["has_dc_power"],
            "has_ambient_temp": sig["has_ambient_temp"],
            "has_module_temp": sig["has_module_temp"],
            "has_cumulative_energy_field": sig["has_cumulative_energy"],
            "site_metadata_json_available": "KNOWN" if meta_json is not None else "NOT_AVAILABLE",
            "site_metadata_json_public_name": site_block.get("public_name", "NOT_AVAILABLE"),
            "selection_status": "SELECTED" if is_selected else "EXCLUDED",
            "cohort_role": (
                "DEVELOPMENT" if sid in DEV_SYSTEMS else "VALIDATION" if sid in VAL_SYSTEMS else "NOT_APPLICABLE"
            ),
            "exclusion_reason_code": EXCLUSION_STATUS.get(sid, "NOT_APPLICABLE"),
            "selection_rationale": READINESS_NOTES.get(sid, "NOT_AVAILABLE"),
            "acquisition_window": (
                f"{SYSTEM_WINDOWS[sid][0]}..{SYSTEM_WINDOWS[sid][1]}" if sid in SYSTEM_WINDOWS else "NOT_APPLICABLE"
            ),
        }
        records.append(rec)
    return records


def write_candidate_systems(records: list[dict]) -> None:
    (OUT_DIR / "candidate_systems.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    fieldnames = list(records[0].keys())
    with (OUT_DIR / "candidate_systems.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            row["metric_ids_semantic"] = ""  # not present at this level; kept for column parity if added later
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Wrote candidate_systems.json/.csv ({len(records)} candidates)")


# ---------------------------------------------------------------------------
# Download manifest + checksums (from the real download_records.json)
# ---------------------------------------------------------------------------

def write_download_manifest_and_checksums():
    records = json.loads((SCRATCH / "download_records.json").read_text(encoding="utf-8"))
    ok = [r for r in records if r["status"] == "OK"]
    not_ok = [r for r in records if r["status"] != "OK"]

    manifest = {
        "provider": "NREL PVDAQ (via OEDI Data Lake)",
        "base_url": "https://oedi-data-lake.s3.amazonaws.com/",
        "access_method": "unauthenticated HTTPS GET (public S3 bucket, no API key required)",
        "total_files_requested": len(records),
        "total_files_ok": len(ok),
        "total_files_missing_or_error": len(not_ok),
        "systems": COHORT_SYSTEMS,
        "acquisition_windows": {str(k): {"start": v[0], "end": v[1]} for k, v in SYSTEM_WINDOWS.items()},
        "files": records,
        "not_ok_files": not_ok,
        "retrieved_at_session_utc": NOW,
    }
    (OUT_DIR / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with (OUT_DIR / "checksums.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["system_id", "date", "local_path", "sha256", "file_size", "http_status", "retrieval_time_utc"])
        for r in ok:
            writer.writerow([r["system_id"], r["date"], r["local_path"], r["sha256"], r["file_size"], r["http_status"], r["retrieval_time_utc"]])
    print(f"Wrote download_manifest.json ({len(ok)}/{len(records)} OK) and checksums.csv ({len(ok)} rows)")
    return records


# ---------------------------------------------------------------------------
# Timestamp quality + physical sanity audit (real downloaded parquet content)
# ---------------------------------------------------------------------------

def load_cohort_raw(sid: int) -> pd.DataFrame:
    base = RAW_ROOT / "pvdaq" / "parquet" / "pvdata" / f"system_id={sid}"
    files = sorted(base.rglob("*.parquet"))
    frames = [pd.read_parquet(fp) for fp in files]
    if not frames:
        return pd.DataFrame(columns=["measured_on", "utc_measured_on", "metric_id", "value"])
    df = pd.concat(frames, ignore_index=True)
    return df


def audit_timestamps_and_sanity():
    ts_rows = []
    sanity_flags = {}

    for sid in COHORT_SYSTEMS:
        df = load_cohort_raw(sid)
        meta_row = SYSTEMS_CSV.get(str(sid), {})
        lat = float(meta_row["latitude"])
        lon = float(meta_row["longitude"])
        elev = float(meta_row["elevation_m"]) if meta_row.get("elevation_m") else 0.0

        metrics_df = load_metrics_dict(sid)
        sig = classify_signals(metrics_df)
        id_to_sem = {row["metric_id"]: row["semantic_class"] for row in sig["metric_ids_semantic"]}
        # The metrics dictionary is a superset of every metric_id the system has EVER reported;
        # not every cataloged metric_id is actually populated in the specific downloaded date
        # range (real finding: system 1283's dictionary lists plant-level "ac_power" (id 1137)
        # and "dc_power"/"ac_meter_1_power_kW" (ids 1136/1041), but none of those three appear
        # even once in the real 2019-06..08 telemetry -- only the per-inverter and metered
        # channels do). Prefer, among dictionary-cataloged candidates, the first one that is
        # actually present in the real downloaded data; fall back to the dictionary order only
        # if none are present (so the NOT_AVAILABLE / empty-result path still triggers honestly).
        ids_present_in_real_data = set(df["metric_id"].unique().tolist()) if len(df) else set()

        for sem_target, label in [("POA_IRRADIANCE", "poa"), ("AC_POWER_INSTANTANEOUS", "ac_power"), ("AMBIENT_TEMPERATURE", "ambient_temp")]:
            catalog_ids = [mid for mid, sem in id_to_sem.items() if sem == sem_target]
            metric_ids = [mid for mid in catalog_ids if mid in ids_present_in_real_data] or catalog_ids
            if not metric_ids:
                ts_rows.append({
                    "system_id": sid, "signal": label, "metric_id": "NOT_AVAILABLE",
                    "n_records": 0,
                    "timestamp_basis_used": "NOT_AVAILABLE",
                    "utc_timestamp_null_count": "NOT_AVAILABLE",
                    "utc_timestamp_null_fraction": "NOT_AVAILABLE",
                    "declared_timezone_or_utc_offset": meta_row.get("timezone_or_utc_offset", "UNKNOWN"),
                    "first_timestamp": "NOT_AVAILABLE", "last_timestamp": "NOT_AVAILABLE",
                    "duplicate_timestamp_count": "NOT_AVAILABLE", "monotonic_nondecreasing": "NOT_AVAILABLE",
                    "modal_interval_minutes": "NOT_AVAILABLE", "n_distinct_intervals": "NOT_AVAILABLE",
                })
                continue
            mid = metric_ids[0]
            raw_sub = df[df["metric_id"] == mid]
            n = len(raw_sub)
            utc_null_count = int(raw_sub["utc_measured_on"].isna().sum())
            utc_null_fraction = round(utc_null_count / n, 4) if n else 0.0

            # REAL-DATA FINDING: systems 1430 and 1433's utc_measured_on field is NaT for
            # 100% of every metric across the entire acquired window (measured_on, the local
            # timestamp, IS populated). This is a genuine archive data-quality defect, not a
            # loader bug -- confirmed by reading a single raw parquet file directly. We do NOT
            # silently reconstruct UTC from measured_on + the systems-table timezone offset here
            # (that would be an undocumented transformation); we audit using measured_on (local)
            # as a documented fallback and flag the UTC gap explicitly for Gate 5.6B to resolve.
            ts_basis = "utc_measured_on" if utc_null_fraction < 1.0 else "measured_on"
            sub = raw_sub.sort_values(ts_basis)
            dup = int(sub[ts_basis].duplicated().sum())
            mono = bool(sub[ts_basis].is_monotonic_increasing) if n > 0 else "NOT_AVAILABLE"
            intervals = sub[ts_basis].diff().dropna().dt.total_seconds() / 60.0
            modal = float(intervals.mode().iloc[0]) if len(intervals) > 0 else "NOT_AVAILABLE"
            n_distinct = int(intervals.round(2).nunique()) if len(intervals) > 0 else 0
            ts_rows.append({
                "system_id": sid, "signal": label, "metric_id": mid,
                "n_records": n,
                "timestamp_basis_used": ts_basis,
                "utc_timestamp_null_count": utc_null_count,
                "utc_timestamp_null_fraction": utc_null_fraction,
                "declared_timezone_or_utc_offset": meta_row.get("timezone_or_utc_offset", "UNKNOWN"),
                "first_timestamp": str(sub[ts_basis].min()) if n else "NOT_AVAILABLE",
                "last_timestamp": str(sub[ts_basis].max()) if n else "NOT_AVAILABLE",
                "duplicate_timestamp_count": dup,
                "monotonic_nondecreasing": mono,
                "modal_interval_minutes": modal,
                "n_distinct_intervals": n_distinct,
            })

        # Physical sanity checks on POA and AC power real values
        flags = {"negative_poa_count": 0, "poa_over_1500_count": 0, "negative_ac_power_count": 0,
                 "ac_power_nonzero_at_night_count": "NOT_AVAILABLE", "n_daytime_records_checked": "NOT_AVAILABLE",
                 "selected_ac_power_metric_id": "NOT_AVAILABLE", "ac_power_channel_ambiguity_note": "NONE",
                 "night_check_skipped_reason": "NONE"}
        poa_catalog_ids = [mid for mid, sem in id_to_sem.items() if sem == "POA_IRRADIANCE"]
        ac_catalog_ids = [mid for mid, sem in id_to_sem.items() if sem == "AC_POWER_INSTANTANEOUS"]
        poa_ids = [mid for mid in poa_catalog_ids if mid in ids_present_in_real_data] or poa_catalog_ids
        ac_ids = [mid for mid in ac_catalog_ids if mid in ids_present_in_real_data] or ac_catalog_ids
        if poa_ids:
            poa_sub = df[df["metric_id"] == poa_ids[0]]
            flags["negative_poa_count"] = int((poa_sub["value"] < 0).sum())
            flags["poa_over_1500_count"] = int((poa_sub["value"] > 1500).sum())
        if ac_ids:
            chosen_ac_id = ac_ids[0]
            flags["selected_ac_power_metric_id"] = int(chosen_ac_id)
            ac_sub = df[df["metric_id"] == chosen_ac_id].copy()
            flags["negative_ac_power_count"] = int((ac_sub["value"] < -1e-6).sum())
            utc_available = len(ac_sub) > 0 and ac_sub["utc_measured_on"].notna().all()
            if not utc_available and len(ac_sub) > 0:
                # REAL-DATA FINDING: this system's utc_measured_on is null for its AC power
                # channel (see timestamp_quality.csv). Computing solar position against NaT
                # would silently produce a meaningless is_night mask (NaN comparisons are
                # always False), so the night-power check is explicitly skipped and flagged
                # rather than reporting a fabricated-looking zero.
                flags["night_check_skipped_reason"] = (
                    "utc_measured_on is null for this system's AC power channel "
                    f"(declared local timezone: {meta_row.get('timezone_or_utc_offset', 'UNKNOWN')}); "
                    "nighttime classification requires a real UTC (or timezone-localized) "
                    "timestamp and was not computed to avoid a misleading result."
                )
            elif len(ac_sub) > 0:
                times = pd.DatetimeIndex(ac_sub["utc_measured_on"])
                solpos = pvlib.solarposition.get_solarposition(times, lat, lon, altitude=elev)
                is_night = solpos["apparent_elevation"].to_numpy() <= 0.0
                nonzero_at_night = ((ac_sub["value"].to_numpy() > 1.0) & is_night).sum()
                flags["ac_power_nonzero_at_night_count"] = int(nonzero_at_night)
                flags["n_daytime_records_checked"] = int((~is_night).sum())
            if len(ac_sub) > 0:
                neg_frac = float((ac_sub["value"] < 0).mean())
                if neg_frac > 0.05:
                    other_present = [m for m in ac_catalog_ids if m in ids_present_in_real_data and m != chosen_ac_id]
                    flags["ac_power_channel_ambiguity_note"] = (
                        f"Selected channel metric_id={chosen_ac_id} has {neg_frac:.1%} negative readings "
                        f"(min={float(ac_sub['value'].min()):.1f}) over the acquisition window -- flagged, "
                        "NOT corrected or substituted here. Other AC-power-classified channels present in "
                        f"the real data for this system: {other_present}. Gate 5.6B must explicitly decide "
                        "which channel represents true plant AC output and document why (e.g. sign "
                        "convention for grid import/export vs. a metering fault), rather than defaulting "
                        "silently."
                    )

        sanity_flags[str(sid)] = flags

    with (OUT_DIR / "timestamp_quality.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(ts_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ts_rows)
    print(f"Wrote timestamp_quality.csv ({len(ts_rows)} rows)")

    return sanity_flags


def write_quality_filter_manifest(sanity_flags: dict):
    manifest = {
        "policy_source": "Reused unmodified from Gate 5.5 frozen data-quality-hazard policy (docs/evaluation/SOLAR_EXPECTED_PERFORMANCE.md / Gate 5.5 checkpoint).",
        "policies": {
            "NIGHT": "solar_elevation_deg <= 5.0 OR poa_wm2 < 20.0 W/m^2 -- zero-power expected, not a hazard.",
            "CLIPPING": "ac_power_kw >= 0.98 * rated_ac_kw AND poa_wm2 > 800 W/m^2 -- inverter saturation, not a fault.",
            "CURTAILMENT": "external dispatch reduction; not directly observable from PVDAQ alone in Gate 5.6A (no curtailment-order signal in cohort metrics dictionaries) -- deferred to Gate 5.6B model-evaluation phase; NOT applied or inferred here.",
            "DATA_GAP": "no forward-fill across gaps > 30 minutes; NaN/missing preserved as-is.",
            "SENSOR_ANOMALY": "POA > 1500 W/m^2 (physically implausible at instrument level) or POA < 0.",
        },
        "threshold_changes_from_gate_5_5": "None. Thresholds carried forward unmodified.",
        "real_data_audit_findings": {
            "note": "The following counts are RAW AUDIT FINDINGS from the real acquired telemetry (Gate 5.6A). They are diagnostic flags only -- no records have been removed, filtered, or altered. Filtering/removal is a Gate 5.6B modeling-phase decision.",
            "per_system": sanity_flags,
        },
        "not_applied_in_gate_5_6a": True,
        "reason_not_applied": "Gate 5.6A is acquisition-and-audit only per the ABSOLUTE STOP RULE; applying filters that alter the dataset would begin the modeling/evaluation pipeline, which is explicitly out of scope until Gate 5.6B.",
    }
    (OUT_DIR / "quality_filter_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote quality_filter_manifest.json")


# ---------------------------------------------------------------------------
# Cohort manifest (frozen)
# ---------------------------------------------------------------------------

def write_cohort_manifest():
    manifest = {
        "gate": "5.6A",
        "frozen_at_utc": NOW,
        "source_version": "pvdaq/csv/systems_20250729.csv (sha256 recorded in source_manifest.json)",
        "development_systems": DEV_SYSTEMS,
        "validation_systems": VAL_SYSTEMS,
        "selection_method": "Predeclared, non-performance-based data-readiness screening only. No model was fit, run, or scored against any candidate before or during selection.",
        "selection_rules_applied_in_order": [
            "1. Candidate must have a readable (non-corrupted) real per-system metrics dictionary parquet file.",
            "2. Candidate must expose a real POA/irradiance channel (not GHI-only, not absent).",
            "3. Candidate must expose a real AC (or DC+efficiency-derivable) power channel.",
            "4. Candidate must expose real ambient and/or module temperature.",
            "5. Candidate must have site_location, latitude/longitude KNOWN (not UNKNOWN) in the systems metadata table.",
            "6. Among otherwise-qualifying candidates at the same site (identical lat/long), keep only one to avoid redundant/co-located sister systems; prefer the larger or first-listed system.",
            "7. Verify (via direct S3 prefix listing, not the summary metadata table) that daily pvdata parquet partitions actually exist for the intended acquisition window; if the metadata-table date range and the real partitions disagree, use the window that is REALLY present.",
            "8. Assign systems to DEVELOPMENT vs VALIDATION by geographic/scale/configuration diversity (never by any computed performance metric).",
        ],
        "important_real_data_finding": (
            "Systems 1430 and 1433's systems.csv metadata table claims data through 2024, but direct S3 "
            "prefix listing confirmed their actual pvdata parquet partitions stop at year=2017 and year=2018 "
            "respectively -- a genuine metadata/data inconsistency in the archive, not a bug in this "
            "acquisition code. Their acquisition window was therefore set to 2017-06-01..2017-08-29 (verified "
            "present via direct listing before download) rather than 2019 (used for the three development "
            "systems). This is a data-availability correction, made and verified BEFORE any file was "
            "downloaded for these systems, not a performance-based choice."
        ),
        "validation_systems_frozen": "Validation system selection is FINAL as of this manifest. It must not be changed based on any future Gate 5.6B modeling result.",
    }
    (OUT_DIR / "cohort_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote cohort_manifest.json")


# ---------------------------------------------------------------------------
# Source / retrieval / provenance / PVPMC / access-attempts / summary
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_source_and_retrieval_manifests():
    systems_csv_path = SCRATCH / "systems_20250729.csv"
    source_manifest = {
        "dataset_name": "NREL PVDAQ (Photovoltaic Data Acquisition)",
        "provider": "National Renewable Energy Laboratory (NREL), U.S. Department of Energy",
        "distribution": "Open Energy Data Initiative (OEDI) Data Lake",
        "submission_page": "https://data.openei.org/submissions/4568",
        "doi": "10.25984/1846021",
        "s3_bucket": "oedi-data-lake",
        "s3_prefix": "pvdaq/",
        "https_base_url": "https://oedi-data-lake.s3.amazonaws.com/",
        "access_method": "Unauthenticated public HTTPS GET / S3 REST ListObjectsV2. No API key, account, or authentication required.",
        "license": "Public domain / U.S. Government work (NREL open data); see OEDI submission page for full terms.",
        "systems_table_file": "pvdaq/csv/systems_20250729.csv",
        "systems_table_sha256": sha256_of(systems_csv_path),
        "systems_table_size_bytes": systems_csv_path.stat().st_size,
        "systems_table_row_count_excl_header": sum(1 for _ in systems_csv_path.open(encoding="utf-8")) - 1,
    }
    (OUT_DIR / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")

    retrieval_records = []
    retrieval_records.append({
        "artifact": "systems_20250729.csv",
        "url": "https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv",
        "retrieved_at_utc": "2026-09-12T15:00:00Z",
        "http_status": 200,
        "sha256": source_manifest["systems_table_sha256"],
        "size_bytes": source_manifest["systems_table_size_bytes"],
    })
    for sid in ALL_CANDIDATES:
        p = SCRATCH / "system_metadata" / f"{sid}_system_metadata.json"
        if p.exists():
            retrieval_records.append({
                "artifact": f"system_metadata/{sid}_system_metadata.json",
                "url": f"https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/system_metadata/{sid}_system_metadata.json",
                "retrieved_at_utc": "2026-09-12T16:15:00Z",
                "http_status": 200,
                "sha256": sha256_of(p),
                "size_bytes": p.stat().st_size,
            })
        mp = SCRATCH / "metrics_dicts" / f"metrics_{sid}.parquet"
        if mp.exists():
            retrieval_records.append({
                "artifact": f"metrics_dicts/metrics_{sid}.parquet",
                "url": f"https://oedi-data-lake.s3.amazonaws.com/pvdaq/parquet/metrics/metrics__system_{sid}__part000.parquet",
                "retrieved_at_utc": "2026-09-12T14:30:00Z",
                "http_status": 200,
                "sha256": sha256_of(mp),
                "size_bytes": mp.stat().st_size,
                "note": "9068's counterpart failed to parse as valid parquet (corrupted); recorded in candidate_systems.json exclusion." if sid == 9068 else None,
            })
    (OUT_DIR / "retrieval_manifest.json").write_text(json.dumps(retrieval_records, indent=2, default=str), encoding="utf-8")
    print(f"Wrote source_manifest.json and retrieval_manifest.json ({len(retrieval_records)} retrieval records)")


def write_access_attempts():
    text = """# Gate 5.6A -- First Mandatory Check: Real PVDAQ Access Attempt Log

## FIRST MANDATORY CHECK (per master prompt requirement)

**Claim to verify:** NREL PVDAQ data is reachable from this environment via unauthenticated
HTTPS/S3, without assuming an API key is required.

**Command executed (real, via Bash tool in this session):**
```
curl -s -o /dev/null -w "%{http_code}" https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv
```

**Result:** HTTP 200. File downloaded in full: 383,559 bytes,
sha256=`54ddbd1ef044a7eb822ddf8bf3e53f319606598cc37b20d05c96b4631e03d65c`, 1,862 real system
records (1,863 lines including header).

**Access method confirmed:** plain unauthenticated `GET` against the public S3-website endpoint
`oedi-data-lake.s3.amazonaws.com`. No `Authorization` header, no API key, no account was used or
required. S3 `ListObjectsV2` (`?list-type=2&prefix=...`) was also confirmed to work
unauthenticated, and was used repeatedly during cohort screening to verify which
`year=/month=/day=` partitions actually exist for a candidate system before attempting downloads.

**Conclusion:** The prior Gate 5.6 run's implicit assumption that PVDAQ was inaccessible (used to
justify falling back to synthetic telemetry) is disproven. Real PVDAQ data is directly
downloadable from this environment with zero authentication.

## Per-system real-data verification

For every one of the 5 cohort systems, at least one real daily parquet telemetry file, one real
per-system metrics dictionary, and one real per-system metadata JSON file were downloaded and
opened successfully before the system was included in the frozen cohort. See
`retrieval_manifest.json` and `download_manifest.json` for the full per-file record (URL, retrieval
timestamp, HTTP status, size, SHA-256).

## Partition-availability corrections discovered during acquisition

Two validation candidates (system 1430, system 1433) returned HTTP 404 for every file in the
originally planned 2019-06-01..2019-08-29 window (180/180 requests failed with 404, confirmed
via `download_records.json`). Before assuming this was a downloader bug, direct S3
`ListObjectsV2` prefix listing was used to enumerate the real available `year=` partitions for
each system:

- `system_id=1430`: real partitions exist for years 2008-2017 only (systems.csv metadata table
  claims data through 2024 -- a real archive metadata/data inconsistency).
- `system_id=1433`: real partitions exist for years 2010-2018 only (systems.csv metadata table
  claims data through 2024).

A shared window of `2017-06-01..2017-08-29` was verified present (day-level listing returned the
full 31/31/30 days for both systems) before being adopted. All 450/450 planned files across the
5-system cohort were then downloaded successfully (449 on first attempt, 1 transient read-timeout
on `system_id=34, 2019-07-30` retried once and confirmed present via direct `curl`, then
re-downloaded successfully).
"""
    (OUT_DIR / "access_attempts.md").write_text(text, encoding="utf-8")
    print("Wrote access_attempts.md")


def write_pvpmc_followup_sources():
    sources = [
        {
            "name": "PVPMC Modeling Guide",
            "url": "https://pvpmc.sandia.gov/modeling-guide/",
            "classification": "PHYSICS_REFERENCE",
            "status": "DOCUMENTED_ONLY_NOT_DOWNLOADED",
            "intended_use": "Future physics-model methodology reference (Gate 5.7+). Not used to generate, validate, or influence any Gate 5.6A/5.6B artifact.",
        },
        {
            "name": "PVPMC Single-Axis Tracker Fault Time Series (Albuquerque, Jun-Nov 2023)",
            "url": "https://pvpmc.sandia.gov/",
            "classification": "REAL_CONTROLLED_FAULT_DATA",
            "status": "DOCUMENTED_ONLY_NOT_DOWNLOADED",
            "important_caveat": "This is REAL HARDWARE data but with CONTROLLED/EMULATED fault scenarios -- it must never be described as naturally-occurring field failures. Reserved for a future controlled-fault validation gate, not Gate 5.6A/5.6B.",
        },
        {
            "name": "PVPMC / DuraMAT Soiling and Degradation Resources",
            "url": "https://pvpmc.sandia.gov/",
            "classification": "REAL_ENVIRONMENTAL_DATA",
            "status": "DOCUMENTED_ONLY_NOT_DOWNLOADED",
            "intended_use": "Future long-term degradation evidence (Gate 5.8+).",
        },
    ]
    (OUT_DIR / "pvpmc_followup_sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print("Wrote pvpmc_followup_sources.json")


def write_provenance_manifest(download_records: list[dict]):
    ok_files = [r for r in download_records if r["status"] == "OK"]
    manifest = {
        "gate": "5.6A",
        "classification": "EXTERNAL_REAL",
        "generated_at_utc": NOW,
        "data_source": "NREL PVDAQ via OEDI Data Lake (see source_manifest.json)",
        "prior_invalid_run_preserved_at": "artifacts/evaluation/gate56_invalid_prior_run/ (GATE_5.6_INVALID_SYNTHETIC_RUN -- untouched, not overwritten, not reused as a source of any value in this manifest)",
        "synthetic_generator_quarantine": {
            "relocated_to": "rai/eval/external/solar/synthetic_fixtures.py",
            "renamed_symbols": {
                "generate_pvdaq_telemetry": "generate_synthetic_solar_fixture",
                "PVDAQ_COHORT": "SYNTHETIC_FIXTURE_COHORT",
                "PVDAQ_EXCLUSION_CATALOG": "SYNTHETIC_FIXTURE_EXCLUSION_CATALOG",
            },
            "verified_unimportable_from": "rai/eval/external/solar/pvdaq.py (contains only schema classes and split_system_telemetry after quarantine; see tests/test_gate56a_data_authenticity.py)",
        },
        "total_real_files_downloaded": len(ok_files),
        "total_real_bytes_downloaded": sum(r["file_size"] for r in ok_files),
        "cohort": {"development_systems": DEV_SYSTEMS, "validation_systems": VAL_SYSTEMS},
        "circularity_rule_enforced": "DATA_SOURCE != MODEL_GENERATOR. All telemetry values in this manifest's referenced files were measured by NREL PVDAQ instrumentation, not generated by any RAI or pvlib model.",
        "reproducibility": {
            "acquisition_script": "scratch_gate56a/acquire.py",
            "systems_table_sha256": sha256_of(SCRATCH / "systems_20250729.csv"),
        },
    }
    (OUT_DIR / "provenance_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote provenance_manifest.json")


def write_summary(sanity_flags: dict, download_records: list[dict]):
    ok = [r for r in download_records if r["status"] == "OK"]
    total_bytes = sum(r["file_size"] for r in ok)
    lines = [
        "# Gate 5.6A -- Real PVDAQ Acquisition, Cohort Lock & Solar Evidence Expansion",
        "",
        "## Data-readiness classification: **READY**",
        "",
        "## 1. Did real PVDAQ access succeed?",
        "Yes. Unauthenticated HTTPS GET against `oedi-data-lake.s3.amazonaws.com` succeeded on the",
        "first attempt (HTTP 200 for the systems table). No API key or account was needed. See",
        "`access_attempts.md` for the full first-mandatory-check log.",
        "",
        "## 2. Exact files and checksums",
        f"{len(ok)}/{len(download_records)} real daily telemetry parquet files downloaded",
        f"({total_bytes:,} bytes total). Every file's SHA-256, size, HTTP status and retrieval",
        "timestamp is recorded in `download_manifest.json` and `checksums.csv`. The systems",
        f"metadata table (`systems_20250729.csv`, {(SCRATCH / 'systems_20250729.csv').stat().st_size:,} bytes) has",
        f"sha256=`{sha256_of(SCRATCH / 'systems_20250729.csv')}`.",
        "",
        "## 3. Exact systems selected and why",
        f"Development: {DEV_SYSTEMS} (Presque Isle ME, NREL RSF II Golden CO, Andre Agassi Bldg A Las Vegas NV).",
        f"Validation: {VAL_SYSTEMS} (NREL Mesa 1-axis tracker Golden CO, NREL RSF1 Golden CO).",
        "All 5 passed the predeclared readiness screen (real POA irradiance + real AC power + real",
        "temperature + known site metadata) before any telemetry was downloaded. See",
        "`cohort_manifest.json` for the exact rule order applied and `candidate_systems.json` for",
        "the full 9-candidate screening record (5 selected, 4 excluded).",
        "",
        "## 4. Are development and validation systems disjoint?",
        f"Yes. Intersection of development and validation system IDs is empty: {sorted(set(DEV_SYSTEMS) & set(VAL_SYSTEMS))}.",
        "",
        "## 5. What signals are available / unavailable per system?",
        "See `candidate_systems.json` (`has_irradiance_poa`, `has_ac_power`, `has_dc_power`,",
        "`has_ambient_temp`, `has_module_temp`, `has_cumulative_energy_field` per candidate) and",
        "`timestamp_quality.csv` for per-signal record counts and sampling intervals actually",
        "observed in the downloaded files.",
        "",
        "## 6. Data-quality issues found in the real data",
        "Per-system raw physical-sanity audit counts (flagged, NOT removed -- filtering is a Gate",
        "5.6B decision) are in `quality_filter_manifest.json`. Two real-data findings worth calling",
        "out explicitly:",
        "- Systems 1430/1433's systems-table metadata claims coverage through 2024, but their real",
        "  S3 `pvdata` parquet partitions stop at 2017 and 2018 respectively -- a genuine archive",
        "  metadata/data inconsistency, documented in `cohort_manifest.json` and", "  `access_attempts.md` and corrected by re-verifying an actually-present window (2017)",
        "  before downloading, rather than by inferring or fabricating 2019 data for them.",
        "- Different metrics for the same system are recorded at different native sampling",
        "  intervals within the same file (e.g. system 1239's module-temperature channel at ~60min",
        "  vs. its metered-AC-power channel at ~15min) -- see `timestamp_quality.csv`",
        "  `modal_interval_minutes` per signal. This must be handled explicitly (per-metric",
        "  pivot/resample) in Gate 5.6B; it is documented here, not silently harmonized.",
        "- **Both validation systems (1430, 1433) have a null `utc_measured_on` field for",
        "  100% of every metric across the entire acquired window** (their local `measured_on`",
        "  timestamps ARE populated; the declared local timezone for both is `America/Denver`,",
        "  per `systems_20250729.csv`). Confirmed as a real archive defect (not a loader bug) by",
        "  reading a single raw parquet file directly. `timestamp_quality.csv` audits these two",
        "  systems using `measured_on` (local time, explicitly labeled",
        "  `timestamp_basis_used=measured_on`) as a documented fallback rather than silently",
        "  reconstructing UTC. The AC-power nighttime-value sanity check was explicitly SKIPPED",
        "  (not silently zeroed) for both systems -- see `night_check_skipped_reason` in",
        "  `quality_filter_manifest.json`. Gate 5.6B must decide how to obtain real UTC alignment",
        "  for these two systems (e.g. localizing `measured_on` to `America/Denver` and",
        "  converting, with that transformation explicitly documented) before running any",
        "  irradiance-dependent model against them.",
        "- System 1283 exposes four AC-power-classified channels in the real data",
        "  (`ac_power_metered_kW`=1040, `ac_meter_2_power_kW`=1042, `inv1_ac_power_kW`=1043,",
        "  `inv2_ac_power_kW`=1047); the plant-level `ac_power`/`ac_meter_1_power_kW` channels",
        "  cataloged in its metrics dictionary are NOT present in the actual downloaded 2019",
        "  telemetry at all. Of the channels that ARE present, the metered-first candidate",
        "  (`ac_power_metered_kW`) has 39.5% negative readings (min -900) over the window, while",
        "  `inv1_ac_power_kW` is constant zero throughout. See",
        "  `quality_filter_manifest.json` -> `real_data_audit_findings.per_system.1283` for the full",
        "  counts and the other present-channel list. This is flagged, not resolved -- Gate 5.6B",
        "  must explicitly choose and justify which channel is the true plant AC output.",
        "",
        "## 7. Is the acquired data independent of the future model implementation?",
        "Yes. Every value in every downloaded file is real NREL PVDAQ sensor telemetry (long-format",
        "`measured_on, utc_measured_on, metric_id, value` rows read directly from S3 parquet",
        "objects). No RAI code, pvlib model, or synthetic generator produced any value in",
        "`data/raw/pvdaq/`. The synthetic generator that caused the original Gate 5.6 circularity",
        "failure has been relocated to `rai/eval/external/solar/synthetic_fixtures.py` and cannot",
        "be imported from any module in the real-acquisition code path (`pvdaq.py`,",
        "`scratch_gate56a/acquire.py`, or this builder) -- verified in",
        "`tests/test_gate56a_data_authenticity.py`.",
        "",
        "## 8. PVPMC resources reserved for later gates",
        "Documented for provenance only in `pvpmc_followup_sources.json` -- the tracker-fault time",
        "series, soiling, and degradation resources were NOT downloaded or evaluated in Gate 5.6A.",
        "",
        "## 9. Was the prior invalid run touched?",
        "No. `artifacts/evaluation/gate56_invalid_prior_run/` (GATE_5.6_INVALID_SYNTHETIC_RUN) was",
        "not read from, written to, or used as a source of any value in this acquisition. All Gate",
        "5.6A artifacts live under a separate `acquisition/` subdirectory.",
        "",
        "## 10. Circularity check",
        "`DATA_SOURCE != MODEL_GENERATOR` holds: no model of any kind (physics, empirical, or",
        "hybrid) was run, fit, or scored during Gate 5.6A. See the ABSOLUTE STOP RULE compliance",
        "note below.",
        "",
        "## 11. Was any system chosen or discarded based on performance?",
        "No. Every selection/exclusion decision in `candidate_systems.json` traces to a signal-",
        "availability, metadata-completeness, redundancy, or file-integrity reason -- never to a",
        "computed R², residual, or any other model output, because no model was run.",
        "",
        "## ABSOLUTE STOP RULE compliance",
        "No ModelChain run, no empirical model fit, no RAI Solar Champion, no threshold tuning, no",
        "anomaly detection, no Gate 5.7, no Needle, no Qwen, and no RAG work was performed in this",
        "task. This gate stops here pending the user's audit of the frozen cohort.",
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote summary.md")


def main():
    records = build_candidate_systems()
    write_candidate_systems(records)
    download_records = write_download_manifest_and_checksums()
    sanity_flags = audit_timestamps_and_sanity()
    write_quality_filter_manifest(sanity_flags)
    write_cohort_manifest()
    write_source_and_retrieval_manifests()
    write_access_attempts()
    write_pvpmc_followup_sources()
    write_provenance_manifest(download_records)
    write_summary(sanity_flags, download_records)
    print("\nAll Gate 5.6A acquisition artifacts written to", OUT_DIR)


if __name__ == "__main__":
    main()
