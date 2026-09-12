"""Gate 5.6C artifact builder: Solar Expected-Performance Model Development (Path B).

STATUS: MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED. See
artifacts/evaluation/gate56/gate56c_decision_gate/decision.md for the Path B decision
record: no real component-failure event labels exist for this cohort (or any integrable
alternative found before the deadline), so this gate builds the expected-performance
engineering foundation (physics reference + empirical baseline + hybrid + residuals)
against the REAL, Gate 5.6B-adjudicated PVDAQ Development cohort [1239, 1283, 34], but
reports every tracking metric (R2, nRMSE, MAE) strictly as an INTERNAL SELF-CONSISTENCY
DIAGNOSTIC (how well the model reproduces held-out real telemetry from the SAME three
systems, temporally split), never as validated accuracy or cross-system generalization.

Reuses (does not reimplement):
  - scratch_gate56a/build_gate56b.py: RAW[sid] (real acquired parquet, loaded once),
    SELECTED_SIGNALS, AC_POWER_SCALE_FACTOR (real per-system unit-scale audit findings).
  - rai/eval/external/solar/filters.py: apply_quality_filters (real, dataset-agnostic
    quality-state tagging -- nighttime, clipping, curtailment placeholder, data gaps).
  - rai/eval/external/solar/pvdaq.py: PVDAQSystemMetadata schema, split_system_telemetry
    (chronological train/val/test split with purge gaps).
  - rai/eval/external/solar/models.py: SolarEmpiricalBaseline, RAISolarChampion (both
    generic w.r.t. the physics_model injected -- neither imports the invalid formula).
  - rai/eval/external/solar/pvlib_modelchain_reference.py (NEW this gate):
    PVLibModelChainReference -- a real pvlib.modelchain.ModelChain physics reference,
    replacing PVLibPhysicsReference (confirmed defective, never imported here).

Alignment follows artifacts/evaluation/gate56/cohort_adjudication/alignment_policy.json
(FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD): the AC-power channel's own real timestamps are
the grid; POA is matched exact-or-nearest-within-5-minutes; ambient/module temperature and
wind speed are backward-held with a 90-minute staleness cutoff (else marked a data gap).

Holdout is TEMPORAL, not system-level: Gate 5.6B froze Validation=[] (INSUFFICIENT_DATA),
so each of the 3 development systems is independently split chronologically
(60% train / 20% val / 20% test with purge gaps) and results are never described as
cross-system generalization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT))

import build_gate56b as g56b  # noqa: E402  (scratch script, sys.path-based import)

from rai.eval.external.solar.filters import apply_quality_filters  # noqa: E402
from rai.eval.external.solar.models import RAISolarChampion, SolarEmpiricalBaseline  # noqa: E402
from rai.eval.external.solar.pvdaq import (  # noqa: E402
    CohortRole,
    PVDAQSystemMetadata,
    split_system_telemetry,
)
from rai.eval.external.solar.pvlib_modelchain_reference import (  # noqa: E402
    REAL_MODELCHAIN_CONFIG,
    PVLibModelChainReference,
)

OUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "gate56c_model_development"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEV_SYSTEMS = g56b.DEV_SYSTEMS  # [1239, 1283, 34]
STALENESS_TOLERANCE = pd.Timedelta(minutes=90)
POA_MATCH_TOLERANCE = pd.Timedelta(minutes=5)

# Real per-system metadata for PVDAQSystemMetadata (schema shared with Gate 5.5/5.6B).
# module_technology / array_type are real (PVDAQ Modules/Site metadata). temp_coefficient
# and inverter_efficiency fields are DESCRIPTIVE ONLY here (not fed into
# PVLibModelChainReference, which uses the full real CEC parameter set directly) --
# each is derived from the same real CEC database entry used to build the ModelChain,
# never invented.
_SYSTEM_META_EXTRA = {
    1239: {
        "name": "Univ. of Maine - Presque Isle",
        "location": "Presque Isle, ME",
        "rated_dc_kw": 20.16,
        "module_technology": "multi-Si",
        "array_type": "fixed_roof",
        # Sharp_ND_224UC1: alpha_sc=0.006914 A/degC, I_mp_ref=7.66A -> pct/degC of I_mp
        "temp_coefficient_pct_per_c": round(0.006914 / 7.66 * 100.0, 4),
        # Yaskawa PVI 13kW: Paco/Pdco = 13700/14326.08
        "inverter_efficiency_nominal": round(13700.0 / 14326.080078, 4),
    },
    1283: {
        "name": "NREL Research Support Facility II",
        "location": "Golden, CO",
        "rated_dc_kw": 408.24,
        "module_technology": "mono-Si",
        "array_type": "fixed_roof",
        "temp_coefficient_pct_per_c": None,  # filled from real CEC dict at runtime
        "inverter_efficiency_nominal": None,  # filled from real CEC dict at runtime
    },
    34: {
        "name": "Andre Agassi Preparatory Academy - Building A",
        "location": "Las Vegas, NV",
        "rated_dc_kw": 146.64,
        "module_technology": "mono-Si",
        "array_type": "fixed_roof",
        "temp_coefficient_pct_per_c": None,
        "inverter_efficiency_nominal": None,
    },
}


def _fill_real_cec_descriptive_fields() -> None:
    """Derive temp_coefficient_pct_per_c / inverter_efficiency_nominal from real CEC dicts
    for systems where they were not hand-computed above, so nothing is invented."""
    from pvlib.pvsystem import retrieve_sam

    cec_mods = retrieve_sam("CECMod")
    cec_invs = retrieve_sam("CECInverter")
    for sid, cfg in REAL_MODELCHAIN_CONFIG.items():
        extra = _SYSTEM_META_EXTRA[sid]
        if extra["temp_coefficient_pct_per_c"] is None:
            mod = cec_mods[cfg["module_name"]]
            extra["temp_coefficient_pct_per_c"] = round(float(mod["alpha_sc"]) / float(mod["I_mp_ref"]) * 100.0, 4)
        if extra["inverter_efficiency_nominal"] is None:
            inv = cec_invs[cfg["inverter_name"]]
            extra["inverter_efficiency_nominal"] = round(float(inv["Paco"]) / float(inv["Pdco"]), 4)


_fill_real_cec_descriptive_fields()


def build_metadata(sid: int) -> PVDAQSystemMetadata:
    cfg = REAL_MODELCHAIN_CONFIG[sid]
    extra = _SYSTEM_META_EXTRA[sid]
    return PVDAQSystemMetadata(
        system_id=str(sid),
        name=extra["name"],
        location=extra["location"],
        latitude=cfg["latitude"],
        longitude=cfg["longitude"],
        altitude_m=cfg["altitude_m"],
        rated_dc_kw=extra["rated_dc_kw"],
        rated_ac_kw=g56b.RATED_AC_KW[sid],
        module_technology=extra["module_technology"],
        array_type=extra["array_type"],
        tilt_deg=cfg["tilt_deg"],
        azimuth_deg=cfg["azimuth_deg"],
        temp_coefficient_pct_per_c=extra["temp_coefficient_pct_per_c"],
        inverter_efficiency_nominal=extra["inverter_efficiency_nominal"],
        has_poa_pyranometer=True,
        has_ghi_pyranometer=False,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=cfg["wind_speed_available"],
        cohort_role=CohortRole.TRAIN_SYSTEM,
        selection_rationale="Gate 5.6A/5.6B real acquisition + adjudication; Gate 5.6C Path B model development.",
    )


def _series_for(sid: int, role: str) -> pd.DataFrame:
    """Real per-signal series for one system: columns utc_measured_on (sorted, deduped), value."""
    mid = g56b.SELECTED_SIGNALS[sid][role]
    if mid is None:
        return pd.DataFrame(columns=["utc_measured_on", "value"])
    raw = g56b.RAW[sid]
    sub = raw.loc[raw["metric_id"] == mid, ["utc_measured_on", "value"]].dropna(subset=["utc_measured_on"])
    sub = sub.sort_values("utc_measured_on").drop_duplicates(subset=["utc_measured_on"], keep="first")
    return sub.reset_index(drop=True)


def build_aligned_frame(sid: int) -> pd.DataFrame:
    """Real telemetry aligned onto the AC-power grid per alignment_policy.json."""
    ac = _series_for(sid, "ac_power").rename(columns={"value": "ac_power_raw"})
    scale = g56b.AC_POWER_SCALE_FACTOR[sid]
    ac["ac_power_kw"] = ac["ac_power_raw"] * scale / 1000.0
    grid = ac[["utc_measured_on", "ac_power_kw"]].copy()

    poa = _series_for(sid, "poa").rename(columns={"value": "poa_wm2"})
    grid = pd.merge_asof(
        grid.sort_values("utc_measured_on"),
        poa.sort_values("utc_measured_on"),
        on="utc_measured_on",
        direction="nearest",
        tolerance=POA_MATCH_TOLERANCE,
    )

    for role, col in (("ambient_temp", "ambient_temp_c"), ("module_temp", "module_temp_c")):
        s = _series_for(sid, role).rename(columns={"value": col})
        grid = pd.merge_asof(
            grid.sort_values("utc_measured_on"),
            s.sort_values("utc_measured_on"),
            on="utc_measured_on",
            direction="backward",
            tolerance=STALENESS_TOLERANCE,
        )

    if REAL_MODELCHAIN_CONFIG[sid]["wind_speed_available"]:
        s = _series_for(sid, "wind_speed").rename(columns={"value": "wind_speed_ms"})
        grid = pd.merge_asof(
            grid.sort_values("utc_measured_on"),
            s.sort_values("utc_measured_on"),
            on="utc_measured_on",
            direction="backward",
            tolerance=STALENESS_TOLERANCE,
        )
    else:
        grid["wind_speed_ms"] = np.nan  # real channel degenerate for this system; never used as real data

    grid["timestamp_utc"] = pd.DatetimeIndex(grid["utc_measured_on"]).tz_localize("UTC")
    solpos = pvlib.solarposition.get_solarposition(
        grid["timestamp_utc"],
        REAL_MODELCHAIN_CONFIG[sid]["latitude"],
        REAL_MODELCHAIN_CONFIG[sid]["longitude"],
        altitude=REAL_MODELCHAIN_CONFIG[sid]["altitude_m"],
    )
    grid["solar_elevation_deg"] = solpos["apparent_elevation"].to_numpy()

    # A real, disclosed data gap: any critical real channel missing after alignment
    # (staleness cutoff exceeded, or no observation at all). module_temp_c is included
    # even though filters.py does not itself gate on it, because both the physics and
    # empirical models consume it -- silently defaulting a missing reading to 25 degC
    # would misrepresent a gap as a real measurement.
    grid["is_data_gap"] = (
        grid["poa_wm2"].isna() | grid["ac_power_kw"].isna()
        | grid["ambient_temp_c"].isna() | grid["module_temp_c"].isna()
    )
    # No real curtailment signal exists in this PVDAQ cohort's real metadata; defaulted
    # False and disclosed here, never measured for these 3 systems.
    grid["is_curtailed_flag"] = False

    grid["system_id"] = sid
    grid["timestamp"] = grid["utc_measured_on"].astype(str)
    return grid.reset_index(drop=True)


def run_system(sid: int) -> dict:
    meta = build_metadata(sid)
    aligned = build_aligned_frame(sid)
    filtered, quality_result = apply_quality_filters(aligned, meta)

    train_df, val_df, test_df = split_system_telemetry(filtered, train_ratio=0.60, val_ratio=0.20, purge_gap_intervals=4)

    physics = PVLibModelChainReference(sid)
    empirical = SolarEmpiricalBaseline(meta).fit(train_df)
    champion = RAISolarChampion(meta, physics, empirical).calibrate(train_df)

    diagnostics_rows = []
    predictions_sample = []
    for split_name, split_df in (("train", train_df), ("val", val_df), ("test", test_df)):
        if len(split_df) == 0:
            continue
        evaluated, _evidence = champion.evaluate_health_evidence(split_df)
        eval_daytime = evaluated[evaluated["is_valid_daytime"] & (~evaluated["is_clipping"]) & (~evaluated["is_curtailed"])]
        y_act = eval_daytime["ac_power_kw"].to_numpy()
        for model_name, exp_col in (
            ("PVLIB_MODELCHAIN_PHYSICS_REFERENCE", "expected_power_physics"),
            ("SOLAR_EMPIRICAL_BASELINE", "expected_power_empirical"),
            ("RAI_SOLAR_CHAMPION_HYBRID", "expected_power_champion"),
        ):
            y_exp = eval_daytime[exp_col].to_numpy()
            n = len(y_act)
            if n < 5:
                diagnostics_rows.append({
                    "system_id": sid, "split": split_name, "model": model_name,
                    "n_valid_daytime_records": n, "r2": None, "rmse_kw": None,
                    "nrmse_pct_of_rated": None, "mae_kw": None,
                    "note": "INSUFFICIENT_DATA (<5 valid daytime records)",
                })
                continue
            resid = y_act - y_exp
            rmse = float(np.sqrt(np.mean(resid ** 2)))
            mae = float(np.mean(np.abs(resid)))
            ss_res = float(np.sum(resid ** 2))
            ss_tot = float(np.sum((y_act - np.mean(y_act)) ** 2))
            r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 1e-9 else None
            diagnostics_rows.append({
                "system_id": sid, "split": split_name, "model": model_name,
                "n_valid_daytime_records": n,
                "r2": round(r2, 4) if r2 is not None else None,
                "rmse_kw": round(rmse, 4),
                "nrmse_pct_of_rated": round(rmse / meta.rated_ac_kw * 100.0, 4),
                "mae_kw": round(mae, 4),
                "note": "MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED -- internal self-consistency diagnostic only",
            })
        if split_name == "test":
            sample_cols = [
                "timestamp", "system_id", "poa_wm2", "ac_power_kw", "module_temp_c",
                "quality_state", "expected_power_physics", "expected_power_empirical",
                "expected_power_champion", "residual_z_score", "health_evidence",
            ]
            predictions_sample.append(evaluated[sample_cols].head(200))

    return {
        "system_id": sid,
        "quality_result": quality_result.to_dict(),
        "split_sizes": {"train": len(train_df), "val": len(val_df), "test": len(test_df)},
        "alpha_blend": champion.alpha_blend,
        "residual_mean_normal_kw": round(champion.residual_mean_normal, 4),
        "residual_std_normal_kw": round(champion.residual_std_normal, 4),
        "diagnostics_rows": diagnostics_rows,
        "predictions_sample": pd.concat(predictions_sample, ignore_index=True) if predictions_sample else pd.DataFrame(),
    }


def main() -> None:
    all_diag_rows = []
    all_samples = []
    per_system_summary = {}
    for sid in DEV_SYSTEMS:
        result = run_system(sid)
        all_diag_rows.extend(result["diagnostics_rows"])
        if len(result["predictions_sample"]):
            all_samples.append(result["predictions_sample"])
        per_system_summary[sid] = {
            "quality_result": result["quality_result"],
            "split_sizes": result["split_sizes"],
            "alpha_blend": result["alpha_blend"],
            "residual_mean_normal_kw": result["residual_mean_normal_kw"],
            "residual_std_normal_kw": result["residual_std_normal_kw"],
        }

    pd.DataFrame(all_diag_rows).to_csv(OUT_DIR / "self_consistency_diagnostics.csv", index=False)
    if all_samples:
        pd.concat(all_samples, ignore_index=True).to_csv(OUT_DIR / "predictions_sample.csv", index=False)

    provenance = {
        "gate": "5.6C",
        "status": "MODEL_DEVELOPMENT",
        "validation_status": "NOT_INDEPENDENTLY_VALIDATED",
        "decision_gate_record": "artifacts/evaluation/gate56/gate56c_decision_gate/decision.md",
        "path_taken": "PATH_B",
        "development_systems": DEV_SYSTEMS,
        "excluded_systems": {
            "1430": "PARAMETERIZATION_INSUFFICIENT -- no real tracker-axis geometry available",
            "1433": "PARAMETERIZATION_INSUFFICIENT -- no CEC module/inverter database match",
        },
        "holdout_type": "TEMPORAL_WITHIN_SYSTEM",
        "holdout_note": (
            "Gate 5.6B froze Validation=[] (INSUFFICIENT_DATA) for cross-system holdout. Each "
            "development system is independently split chronologically (60/20/20, purge_gap=4 "
            "intervals) via rai.eval.external.solar.pvdaq.split_system_telemetry. Results are "
            "NEVER cross-system generalization claims."
        ),
        "alignment_policy": "artifacts/evaluation/gate56/cohort_adjudication/alignment_policy.json (FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD)",
        "physics_reference": "rai.eval.external.solar.pvlib_modelchain_reference.PVLibModelChainReference (real pvlib.modelchain.ModelChain, not the invalid hand-rolled PVLibPhysicsReference)",
        "empirical_baseline": "rai.eval.external.solar.models.SolarEmpiricalBaseline (unmodified, reused)",
        "champion_hybrid": "rai.eval.external.solar.models.RAISolarChampion (unmodified, reused)",
        "per_system_summary": per_system_summary,
        "diagnostic_metric_disclaimer": (
            "R2/RMSE/nRMSE/MAE in self_consistency_diagnostics.csv measure how well each model "
            "reproduces REAL, HELD-OUT (temporally later) telemetry from the SAME system it was "
            "fit/calibrated on. They are internal self-consistency diagnostics, not validated "
            "accuracy and not evidence of generalization to any other system, site, or time period."
        ),
    }
    (OUT_DIR / "provenance_manifest.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    write_summary(per_system_summary, all_diag_rows)


def write_summary(per_system_summary: dict, all_diag_rows: list[dict]) -> None:
    lines = [
        "# Gate 5.6C -- Solar Expected-Performance Model Development",
        "",
        "**Status: `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED`.**",
        "",
        "This gate builds a real `pvlib.modelchain.ModelChain` physics reference, an empirical",
        "baseline, and a hybrid champion model against the REAL, Gate 5.6B-adjudicated PVDAQ",
        "Development cohort (systems 1239, 1283, 34). Per the Gate 5.6C decision gate",
        "(`../gate56c_decision_gate/decision.md`, PATH B), no real component-failure event",
        "labels exist for this cohort or any integrable alternative -- so every metric below is",
        "an **internal self-consistency diagnostic** (does the model reproduce held-out real",
        "telemetry from the SAME system it was fit on), never a validated-accuracy or",
        "generalization claim. Systems 1430 and 1433 are excluded as",
        "`PARAMETERIZATION_INSUFFICIENT` (no real tracker geometry / no CEC module match",
        "respectively) -- no parameters were invented to force a model for either.",
        "",
        "## What changed vs. the invalidated prior run",
        "",
        "- Physics reference is a REAL `pvlib.pvsystem.PVSystem` + `pvlib.modelchain.ModelChain`",
        "  (`rai/eval/external/solar/pvlib_modelchain_reference.py`), using only real CEC",
        "  module/inverter database matches, real tilt/azimuth, and real inverter-quantity /",
        "  module-count metadata -- not the hand-rolled formula that caused",
        "  `GATE_5.6_INVALID_SYNTHETIC_RUN`.",
        "- All telemetry is the real, checksummed Gate 5.6A PVDAQ acquisition -- no synthetic",
        "  data anywhere in this code path (enforced by a circularity tripwire test).",
        "- Holdout is temporal-within-system (60/20/20 per system with purge gaps), never",
        "  cross-system, and never described as generalization.",
        "",
        "## Per-system results",
        "",
    ]
    for sid, s in per_system_summary.items():
        lines.append(f"### System {sid}")
        lines.append("")
        lines.append(f"- Split sizes (records): {s['split_sizes']}")
        lines.append(f"- Quality filter result: {s['quality_result']}")
        lines.append(f"- Champion hybrid blend weight (alpha on physics): {s['alpha_blend']}")
        lines.append(
            f"- Calibrated normal-operation residual: mean={s['residual_mean_normal_kw']} kW, "
            f"std={s['residual_std_normal_kw']} kW"
        )
        lines.append("")

    lines.append("## Self-consistency diagnostics (test split, internal only)")
    lines.append("")
    lines.append("| System | Model | n | R2 | RMSE (kW) | nRMSE (% of rated) | MAE (kW) |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in all_diag_rows:
        if row["split"] != "test":
            continue
        lines.append(
            f"| {row['system_id']} | {row['model']} | {row['n_valid_daytime_records']} | "
            f"{row['r2']} | {row['rmse_kw']} | {row['nrmse_pct_of_rated']} | {row['mae_kw']} |"
        )
    lines += [
        "",
        "All figures above are `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED` internal",
        "self-consistency diagnostics -- see `provenance_manifest.json`'s",
        "`diagnostic_metric_disclaimer` for the exact scope and limits of this claim.",
        "",
        "## Limitations",
        "",
        "- No real component-failure event labels exist for this cohort (Gate 5.6C decision",
        "  gate finding) -- these models cannot be validated against real fault ground truth.",
        "- AOI and spectral-mismatch corrections are not modeled (`aoi_model='no_loss'`,",
        "  `spectral_model='no_loss'`): real PVDAQ POA sensors report only broadband global",
        "  irradiance, not decomposed direct/diffuse components `run_model_from_poa` requires,",
        "  so `run_model_from_effective_irradiance` is used instead -- a disclosed simplification.",
        "- Series/parallel wiring split (modules_per_string=1) is a disclosed, power-invariant",
        "  simplification: real metadata gives only total module count and real inverter count,",
        "  not the exact per-inverter string layout.",
        "- System 1239's temperature model uses a disclosed wind_speed=1.0 m/s standard",
        "  assumption (`faiman`) because its real wind channel is degenerate (Gate 5.6B finding).",
        "",
        "## STOP RULE compliance",
        "",
        "This gate fit and ran real models against real, adjudicated telemetry. It did NOT",
        "claim validated accuracy, generalization, or cite any real fault-event ground truth.",
        "No Gate 5.7, Needle, Qwen, or RAG work was started here.",
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
