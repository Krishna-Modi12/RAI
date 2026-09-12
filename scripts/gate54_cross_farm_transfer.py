"""Gate 5.4 — Cross-Farm Wind Transfer & Target-Normal Calibration.

Evaluates the six directed cross-farm transfers:
A -> B, A -> C, B -> A, B -> C, C -> A, C -> B
under the frozen CARE_COMMON representation (wind_speed, active_power, rotor_speed).

Evaluates three operating conditions per transfer:
1. Condition A (FROZEN_SOURCE): Source model deployed directly to target without change.
2. Condition B (TARGET_NORMAL_CALIBRATED): Source model recalibrated using ONLY target-farm
   normal training data (zero target fault labels, zero prediction split data).
3. Condition C (TARGET_SPECIFIC_REFERENCE): Target-farm model trained on target training split.

All evaluation uses the official CARE scorer (Coverage, Accuracy, Reliability, Earliness, CARE)
with dependence-aware turbine-cluster bootstrap (2,000 resamples).
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rai.eval.external.care.champion import (
    RAIChampionDetector,
    fit_rai_champion,
    recalibrate_rai_champion_target_normal,
)
from rai.eval.external.care.features import (
    FARM_COMMON_MAPPING,
)
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    accuracy_score,
    care_score,
    coverage_fbeta,
    criticality_series,
    event_reliability_fbeta,
    weighted_earliness_score,
)
from rai.ingest.care import CARE_ROOT, load_event_info

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gate54")

OUT_DIR = _REPO_ROOT / "artifacts" / "evaluation" / "gate54"
FARMS = ("Wind Farm A", "Wind Farm B", "Wind Farm C")
DIRECTED_TRANSFERS: tuple[tuple[str, str], ...] = (
    ("Wind Farm A", "Wind Farm B"),
    ("Wind Farm A", "Wind Farm C"),
    ("Wind Farm B", "Wind Farm A"),
    ("Wind Farm B", "Wind Farm C"),
    ("Wind Farm C", "Wind Farm A"),
    ("Wind Farm C", "Wind Farm B"),
)
CONDITIONS = ("FROZEN_SOURCE", "TARGET_NORMAL_CALIBRATED", "TARGET_SPECIFIC_REFERENCE")
CRITICALITY_THRESHOLD = 72.0
BOOTSTRAP_RESAMPLES = 2000
RANDOM_SEED = 20260912


@dataclass
class DatasetEvaluationResult:
    source_farm: str
    target_farm: str
    condition: str
    dataset_file: str
    event_id: int
    turbine_id: str
    label: str
    fault_category: str
    alarms_count: int
    event_detected: bool
    max_criticality: float
    coverage_fbeta: float | None
    lead_time_steps: int | None
    earliness_ws: float | None
    accuracy: float | None = None


@dataclass
class TransferConditionSummary:
    source_farm: str
    target_farm: str
    condition: str
    n_total_datasets: int
    n_anomaly_datasets: int
    n_normal_datasets: int
    n_turbines: int
    coverage_fbeta: float | None
    accuracy: float
    reliability_efbeta: float
    earliness_ws: float | None
    care_score: float
    n_events_detected: int
    n_events_missed: int
    event_detection_rate: float
    normal_datasets_with_alarms: int
    dataset_alarm_incidence: float
    median_lead_time_steps: float | None


def write_csv_from_dicts(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def load_farm_dataset_frames(farm_name: str) -> list[dict[str, Any]]:
    """Load and cache all datasets for a farm under CARE_COMMON columns."""
    farm_dir = CARE_ROOT / farm_name
    event_info_file = farm_dir / "event_info.csv"
    events_df = load_event_info(event_info_file) if event_info_file.is_file() else pd.DataFrame()
    ds_dir = farm_dir / "datasets"

    cached: list[dict[str, Any]] = []
    mapping = FARM_COMMON_MAPPING[farm_name]
    target_cols = [mapping["wind_speed"], mapping["active_power"], mapping["rotor_speed"]]

    ds_files = sorted(ds_dir.glob("*.csv"))
    for csv_file in ds_files:
        try:
            event_id = int(csv_file.stem)
        except ValueError:
            continue

        df = pd.read_csv(csv_file, sep=";")
        split_col = "train_test" if "train_test" in df.columns else "care_train_test"
        id_col = "id" if "id" in df.columns else "care_id"
        status_col = "status_type_id" if "status_type_id" in df.columns else "care_status_type_id"

        sub_cols = [split_col, id_col, status_col] + [c for c in target_cols if c in df.columns]
        sub_df = df[sub_cols].copy()

        # Add canonical column aliases so detectors can resolve either raw or canonical names
        sub_df["wind_speed"] = sub_df[mapping["wind_speed"]]
        sub_df["active_power"] = sub_df[mapping["active_power"]]
        sub_df["rotor_speed"] = sub_df[mapping["rotor_speed"]]

        train_split = sub_df[sub_df[split_col] == "train"].copy()
        pred_split = sub_df[sub_df[split_col] == "prediction"].sort_values(id_col).copy()

        row_match = events_df[events_df["event_id"] == event_id] if not events_df.empty else pd.DataFrame()
        if not row_match.empty:
            ev_label_str = str(row_match.iloc[0].get("event_label", "")).strip().lower()
            is_anomaly = (ev_label_str == "anomaly")
            desc = str(row_match.iloc[0].get("event_description", "Unspecified sequence"))
        else:
            is_anomaly = False
            desc = "Normal Operation"

        label = (
            CareDatasetLabel.ANOMALY_EVENT
            if is_anomaly
            else CareDatasetLabel.NORMAL_BEHAVIOR
        )

        if not row_match.empty and "asset_id" in row_match.columns and pd.notna(row_match.iloc[0]["asset_id"]):
            turbine_id = f"CARE-WT-{row_match.iloc[0]['asset_id']}"
        elif "asset_id" in df.columns and len(df) > 0 and pd.notna(df["asset_id"].iloc[0]):
            turbine_id = f"CARE-WT-{df['asset_id'].iloc[0]}"
        else:
            turbine_id = f"turb_{event_id}"

        care_ids = pred_split[id_col].to_numpy()
        status_normal = (pred_split[status_col].to_numpy() == 0)

        if label is CareDatasetLabel.ANOMALY_EVENT and not row_match.empty:
            start_id = row_match.iloc[0].get("event_start_id")
            end_id = row_match.iloc[0].get("event_end_id")
            if pd.notna(start_id) and pd.notna(end_id):
                ground_truth = (care_ids >= int(start_id)) & (care_ids <= int(end_id))
            else:
                ground_truth = np.ones(len(pred_split), dtype=bool)
        else:
            ground_truth = np.zeros(len(pred_split), dtype=bool)

        cached.append({
            "event_id": event_id,
            "turbine_id": turbine_id,
            "label": label,
            "description": desc,
            "dataset_file": csv_file.name,
            "train_split": train_split,
            "pred_split": pred_split,
            "ground_truth": ground_truth,
            "status_normal": status_normal,
            "care_ids": care_ids,
            "status_col": status_col,
            "id_col": id_col,
            "split_col": split_col,
        })

    return cached


def compute_distribution_shift(
    source_frames: list[dict[str, Any]],
    target_frames: list[dict[str, Any]],
    source_farm: str,
    target_farm: str,
) -> list[dict[str, Any]]:
    """Compare distributions of wind_speed, active_power, and rotor_speed between source and target."""
    src_map = FARM_COMMON_MAPPING[source_farm]
    tgt_map = FARM_COMMON_MAPPING[target_farm]

    # Concatenate training data for distribution profiling
    src_train = pd.concat([d["train_split"] for d in source_frames], ignore_index=True)
    tgt_train = pd.concat([d["train_split"] for d in target_frames], ignore_index=True)

    signals = ("wind_speed", "active_power", "rotor_speed")
    shift_rows: list[dict[str, Any]] = []

    for sig in signals:
        src_col = src_map[sig]
        tgt_col = tgt_map[sig]

        src_vals = src_train[src_col].dropna().to_numpy(dtype=float)
        tgt_vals = tgt_train[tgt_col].dropna().to_numpy(dtype=float)

        src_mean, src_std = float(np.mean(src_vals)), float(np.std(src_vals)) or 1.0
        tgt_mean, tgt_std = float(np.mean(tgt_vals)), float(np.std(tgt_vals)) or 1.0

        # Cohen's d
        pooled_std = float(np.sqrt((src_std**2 + tgt_std**2) / 2.0)) or 1.0
        cohens_d = (tgt_mean - src_mean) / pooled_std

        # Kolmogorov-Smirnov test
        ks_stat, ks_pval = stats.ks_2samp(src_vals, tgt_vals)

        # Quantiles
        q_src = np.percentile(src_vals, [10, 50, 90])
        q_tgt = np.percentile(tgt_vals, [10, 50, 90])

        shift_rows.append({
            "source_farm": source_farm,
            "target_farm": target_farm,
            "signal": sig,
            "source_column": src_col,
            "target_column": tgt_col,
            "source_mean": round(src_mean, 2),
            "source_std": round(src_std, 2),
            "target_mean": round(tgt_mean, 2),
            "target_std": round(tgt_std, 2),
            "cohens_d": round(cohens_d, 3),
            "ks_statistic": round(float(ks_stat), 4),
            "ks_pvalue": float(f"{ks_pval:.2e}"),
            "source_p10": round(float(q_src[0]), 2),
            "source_p50": round(float(q_src[1]), 2),
            "source_p90": round(float(q_src[2]), 2),
            "target_p10": round(float(q_tgt[0]), 2),
            "target_p50": round(float(q_tgt[1]), 2),
            "target_p90": round(float(q_tgt[2]), 2),
        })

    return shift_rows


def turbine_cluster_bootstrap(
    run_records: list[DatasetEvaluationResult],
    reliability_inputs: list[DatasetReliabilityInput],
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Perform turbine-cluster bootstrap (resampling whole turbines, never isolated timestamps)."""
    rng = np.random.RandomState(seed)
    turbines = sorted(list({r.turbine_id for r in run_records}))
    n_turbines = len(turbines)
    if n_turbines < 3:
        return {"status": "INSUFFICIENT_DATA", "n_turbines": n_turbines}

    # Map each turbine to its list of dataset indices
    turb_to_idx: dict[str, list[int]] = {}
    for i, r in enumerate(run_records):
        turb_to_idx.setdefault(r.turbine_id, []).append(i)

    boot_cares: list[float] = []
    boot_rates: list[float] = []

    for _ in range(n_resamples):
        sampled_turbs = rng.choice(turbines, size=n_turbines, replace=True)
        sampled_indices: list[int] = []
        for t in sampled_turbs:
            sampled_indices.extend(turb_to_idx[t])

        sampled_runs = [run_records[i] for i in sampled_indices]

        anomaly_runs = [r for r in sampled_runs if r.label == CareDatasetLabel.ANOMALY_EVENT.value]
        normal_runs = [r for r in sampled_runs if r.label == CareDatasetLabel.NORMAL_BEHAVIOR.value]

        if not anomaly_runs:
            continue

        valid_covs = [r.coverage_fbeta for r in anomaly_runs if r.coverage_fbeta is not None]
        mean_cov = float(np.mean(valid_covs)) if valid_covs else 0.0

        valid_earls = [r.earliness_ws for r in anomaly_runs if r.earliness_ws is not None]
        mean_earl = float(np.mean(valid_earls)) if valid_earls else 0.0

        normal_with_alarms = sum(1 for r in normal_runs if r.alarms_count > 0)
        alarm_incidence = normal_with_alarms / max(len(normal_runs), 1)
        valid_accs = [r.accuracy for r in normal_runs if hasattr(r, "accuracy") and r.accuracy is not None]
        acc = float(np.mean(valid_accs)) if valid_accs else (1.0 - alarm_incidence if normal_runs else 1.0)

        # Vectorised event reliability from pre-evaluated detections
        g_arr = np.array([1 if r.label == CareDatasetLabel.ANOMALY_EVENT.value else 0 for r in sampled_runs], dtype=bool)
        p_arr = np.array([1 if r.event_detected else 0 for r in sampled_runs], dtype=bool)
        tp = int(np.sum(g_arr & p_arr))
        fp = int(np.sum(~g_arr & p_arr))
        fn = int(np.sum(g_arr & ~p_arr))
        num = 1.25 * tp
        denom = num + 0.25 * fn + fp
        rel_efbeta = float(num / denom) if denom > 0 else 0.0

        any_pred = any(r.alarms_count > 0 for r in sampled_runs)
        cs = care_score(
            mean_coverage_fbeta=mean_cov,
            mean_earliness_ws=mean_earl,
            event_reliability=rel_efbeta,
            mean_accuracy=acc,
            any_anomaly_predicted=any_pred,
        )

        det_count = sum(1 for r in anomaly_runs if r.event_detected)
        det_rate = det_count / len(anomaly_runs)

        boot_cares.append(cs)
        boot_rates.append(det_rate)

    if not boot_cares:
        return {"status": "INSUFFICIENT_DATA", "n_turbines": n_turbines}

    ci_care = np.percentile(boot_cares, [2.5, 97.5])
    ci_rate = np.percentile(boot_rates, [2.5, 97.5])

    return {
        "status": "VALID",
        "n_turbines": n_turbines,
        "n_resamples": len(boot_cares),
        "care_mean": round(float(np.mean(boot_cares)), 4),
        "care_std": round(float(np.std(boot_cares)), 4),
        "care_ci_lower_95": round(float(ci_care[0]), 4),
        "care_ci_upper_95": round(float(ci_care[1]), 4),
        "detection_rate_mean": round(float(np.mean(boot_rates)), 4),
        "detection_rate_ci_lower_95": round(float(ci_rate[0]), 4),
        "detection_rate_ci_upper_95": round(float(ci_rate[1]), 4),
    }


def main() -> int:
    t_start = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Starting Gate 5.4 Cross-Farm Wind Transfer & Calibration. Output: %s", OUT_DIR)

    # 1. Load and cache all datasets for Farms A, B, and C
    cache_file = OUT_DIR / "farm_data_cache.pkl"
    if cache_file.is_file():
        log.info("Loading cached CARE dataset frames from %s...", cache_file)
        import pickle
        with cache_file.open("rb") as fp:
            farm_data = pickle.load(fp)
    else:
        log.info("Loading cached CARE datasets across all three farms...")
        farm_data: dict[str, list[dict[str, Any]]] = {}
        for farm in FARMS:
            farm_data[farm] = load_farm_dataset_frames(farm)
            log.info("Loaded %s: %d datasets", farm, len(farm_data[farm]))
        import pickle
        with cache_file.open("wb") as fp:
            pickle.dump(farm_data, fp)
        log.info("Saved dataset cache to %s", cache_file)

    # 2. Train Target-Specific Baseline Models for each Farm
    log.info("Fitting source/target reference models on train splits...")
    farm_models: dict[str, RAIChampionDetector] = {}
    farm_normal_train_frames: dict[str, pd.DataFrame] = {}

    for farm in FARMS:
        train_dfs = [d["train_split"] for d in farm_data[farm]]
        full_train = pd.concat(train_dfs, ignore_index=True)
        # Filter strictly to normal status for normal-only calibration
        status_col = farm_data[farm][0]["status_col"]
        normal_train = full_train[full_train[status_col] == 0].copy()
        farm_normal_train_frames[farm] = normal_train

        model = fit_rai_champion(
            full_train,
            farm_name=farm,
            feature_policy="care_common",
            persistence_steps=3,
            z_threshold=2.5,
        )
        farm_models[farm] = model
        log.info(
            "Fitted reference model for %s (power_poly=%s, rotor_poly=%s)",
            farm,
            model.power_poly is not None,
            model.rotor_poly is not None,
        )

    # 3. Distribution Shift Audit across all 6 directed pairs
    log.info("Performing distribution shift audit across all 6 directed pairs...")
    all_distribution_shifts: list[dict[str, Any]] = []
    for src, tgt in DIRECTED_TRANSFERS:
        shifts = compute_distribution_shift(farm_data[src], farm_data[tgt], src, tgt)
        all_distribution_shifts.extend(shifts)
    write_csv_from_dicts(OUT_DIR / "distribution_shift.csv", all_distribution_shifts)

    # 4. Evaluate all 6 Directed Transfers under 3 Conditions
    log.info("Evaluating 6 directed transfers x 3 conditions under official CARE scorer...")
    all_dataset_runs: list[DatasetEvaluationResult] = []
    all_condition_summaries: list[TransferConditionSummary] = []
    bootstrap_results: list[dict[str, Any]] = []

    for src_farm, tgt_farm in DIRECTED_TRANSFERS:
        tgt_datasets = farm_data[tgt_farm]
        n_tgt = len(tgt_datasets)
        unique_turbines = sorted(list({d["turbine_id"] for d in tgt_datasets}))

        # Setup 3 models for this transfer
        # Condition A: Frozen source model
        m_frozen = farm_models[src_farm]

        # Condition B: Target-normal calibrated model
        # Uses ONLY target farm's permitted normal training data
        tgt_normal_frame = farm_normal_train_frames[tgt_farm]
        m_calibrated = recalibrate_rai_champion_target_normal(
            m_frozen,
            tgt_normal_frame,
            target_farm_name=tgt_farm,
        )

        # Condition C: Target-specific reference
        m_reference = farm_models[tgt_farm]

        eval_models = {
            "FROZEN_SOURCE": m_frozen,
            "TARGET_NORMAL_CALIBRATED": m_calibrated,
            "TARGET_SPECIFIC_REFERENCE": m_reference,
        }

        for cond_name, model in eval_models.items():
            runs_for_cond: list[DatasetEvaluationResult] = []
            rels_for_cond: list[DatasetReliabilityInput] = []

            for d in tgt_datasets:
                pred_split = d["pred_split"]
                preds = model.predict(pred_split)
                status_normal = d["status_normal"]
                ground_truth = d["ground_truth"]
                label = d["label"]

                alarms_count = int(preds.sum())
                crit_series = criticality_series(status_normal, preds)
                max_crit = float(crit_series.max(initial=0.0))
                detected = max_crit >= CRITICALITY_THRESHOLD

                cov = None
                earl = None
                lead_time = None
                if label is CareDatasetLabel.ANOMALY_EVENT and ground_truth.sum() > 0:
                    cov = coverage_fbeta(ground_truth, preds, status_normal, beta=0.5)
                    event_preds = preds[ground_truth]
                    earl = weighted_earliness_score(event_preds)
                    alarm_indices = np.where(ground_truth & (preds == 1))[0]
                    if len(alarm_indices) > 0:
                        first_alarm_idx = alarm_indices[0]
                        lead_time = int(ground_truth.sum()) - int(first_alarm_idx)

                ds_acc = None
                if label is CareDatasetLabel.NORMAL_BEHAVIOR:
                    ds_acc = accuracy_score(preds, status_normal)

                res = DatasetEvaluationResult(
                    source_farm=src_farm,
                    target_farm=tgt_farm,
                    condition=cond_name,
                    dataset_file=d["dataset_file"],
                    event_id=d["event_id"],
                    turbine_id=d["turbine_id"],
                    label=label.value,
                    fault_category=d["description"],
                    alarms_count=alarms_count,
                    event_detected=detected,
                    max_criticality=max_crit,
                    coverage_fbeta=cov,
                    lead_time_steps=lead_time,
                    earliness_ws=earl,
                    accuracy=ds_acc,
                )
                runs_for_cond.append(res)
                all_dataset_runs.append(res)

                rel_inp = DatasetReliabilityInput(
                    label=label,
                    status_normal=status_normal,
                    prediction=preds,
                )
                rels_for_cond.append(rel_inp)

            # Farm-level CARE scoring on target
            anomaly_runs = [r for r in runs_for_cond if r.label == CareDatasetLabel.ANOMALY_EVENT.value]
            normal_runs = [r for r in runs_for_cond if r.label == CareDatasetLabel.NORMAL_BEHAVIOR.value]

            normal_with_alarms = sum(1 for r in normal_runs if r.alarms_count > 0)
            alarm_incidence = normal_with_alarms / max(len(normal_runs), 1)
            valid_accs = [r.accuracy for r in normal_runs if r.accuracy is not None]
            acc = float(np.mean(valid_accs)) if valid_accs else 1.0

            valid_covs = [r.coverage_fbeta for r in anomaly_runs if r.coverage_fbeta is not None]
            mean_cov = float(np.mean(valid_covs)) if valid_covs else None

            valid_earls = [r.earliness_ws for r in anomaly_runs if r.earliness_ws is not None]
            mean_earl = float(np.mean(valid_earls)) if valid_earls else None

            rel_efbeta = event_reliability_fbeta(rels_for_cond, criticality_threshold=CRITICALITY_THRESHOLD, beta=0.5)

            det_count = sum(1 for r in anomaly_runs if r.event_detected)
            miss_count = len(anomaly_runs) - det_count
            det_rate = det_count / max(len(anomaly_runs), 1)

            cov_val = mean_cov if mean_cov is not None else 0.0
            earl_val = mean_earl if mean_earl is not None else 0.0
            any_pred = any(r.alarms_count > 0 for r in runs_for_cond)
            cs = care_score(
                mean_coverage_fbeta=cov_val,
                mean_earliness_ws=earl_val,
                event_reliability=rel_efbeta,
                mean_accuracy=acc,
                any_anomaly_predicted=any_pred,
            )

            lead_times = [r.lead_time_steps for r in anomaly_runs if r.lead_time_steps is not None]
            med_lead = float(np.median(lead_times)) if lead_times else None

            summary = TransferConditionSummary(
                source_farm=src_farm,
                target_farm=tgt_farm,
                condition=cond_name,
                n_total_datasets=n_tgt,
                n_anomaly_datasets=len(anomaly_runs),
                n_normal_datasets=len(normal_runs),
                n_turbines=len(unique_turbines),
                coverage_fbeta=round(mean_cov, 4) if mean_cov is not None else None,
                accuracy=round(acc, 4),
                reliability_efbeta=round(rel_efbeta, 4),
                earliness_ws=round(mean_earl, 4) if mean_earl is not None else None,
                care_score=round(cs, 4),
                n_events_detected=det_count,
                n_events_missed=miss_count,
                event_detection_rate=round(det_rate, 4),
                normal_datasets_with_alarms=normal_with_alarms,
                dataset_alarm_incidence=round(alarm_incidence, 4),
                median_lead_time_steps=med_lead,
            )
            all_condition_summaries.append(summary)

            # Run dependence-aware bootstrap
            boot = turbine_cluster_bootstrap(runs_for_cond, rels_for_cond, n_resamples=BOOTSTRAP_RESAMPLES)
            boot["source_farm"] = src_farm
            boot["target_farm"] = tgt_farm
            boot["condition"] = cond_name
            bootstrap_results.append(boot)

    # 5. Build Transfer Matrix & Deltas Table
    transfer_delta_rows: list[dict[str, Any]] = []

    grouped_summaries: dict[tuple[str, str], dict[str, TransferConditionSummary]] = {}
    for s in all_condition_summaries:
        key = (s.source_farm, s.target_farm)
        grouped_summaries.setdefault(key, {})[s.condition] = s

    for (src, tgt), conds in grouped_summaries.items():
        s_froz = conds["FROZEN_SOURCE"]
        s_cal = conds["TARGET_NORMAL_CALIBRATED"]
        s_ref = conds["TARGET_SPECIFIC_REFERENCE"]

        care_froz = s_froz.care_score
        care_cal = s_cal.care_score
        care_ref = s_ref.care_score

        # Deltas
        delta_transfer = care_froz - care_ref
        delta_calibration = care_cal - care_froz
        residual_gap = care_ref - care_cal

        # Fraction of gap recovered
        denom = care_ref - care_froz
        if abs(denom) > 1e-4:
            pct_recovered = round((care_cal - care_froz) / denom * 100.0, 1)
            pct_str = f"{pct_recovered:.1f}%"
        else:
            pct_str = "NOT_INTERPRETABLE"

        transfer_delta_rows.append({
            "source_farm": src,
            "target_farm": tgt,
            "care_frozen": care_froz,
            "care_calibrated": care_cal,
            "care_reference": care_ref,
            "delta_transfer": round(delta_transfer, 4),
            "delta_calibration_recovery": round(delta_calibration, 4),
            "residual_gap_after_cal": round(residual_gap, 4),
            "fraction_gap_recovered": pct_str,
            "detected_frozen": f"{s_froz.n_events_detected}/{s_froz.n_anomaly_datasets}",
            "detected_calibrated": f"{s_cal.n_events_detected}/{s_cal.n_anomaly_datasets}",
            "detected_reference": f"{s_ref.n_events_detected}/{s_ref.n_anomaly_datasets}",
            "accuracy_frozen": s_froz.accuracy,
            "accuracy_calibrated": s_cal.accuracy,
            "accuracy_reference": s_ref.accuracy,
        })

    # Write Matrix CSV
    matrix_csv_rows = []
    for (src, tgt), d in grouped_summaries.items():
        matrix_csv_rows.append({
            "source_farm": src,
            "target_farm": tgt,
            "frozen_care": d["FROZEN_SOURCE"].care_score,
            "calibrated_care": d["TARGET_NORMAL_CALIBRATED"].care_score,
            "reference_care": d["TARGET_SPECIFIC_REFERENCE"].care_score,
        })
    write_csv_from_dicts(OUT_DIR / "transfer_matrix.csv", matrix_csv_rows)
    write_csv_from_dicts(OUT_DIR / "transfer_deltas.csv", transfer_delta_rows)
    write_csv_from_dicts(OUT_DIR / "bootstrap_uncertainty.csv", bootstrap_results)

    # 6. Output Event Forensics & Missed Events
    event_rows = [asdict(r) for r in all_dataset_runs if r.label == CareDatasetLabel.ANOMALY_EVENT.value]
    write_csv_from_dicts(OUT_DIR / "event_results.csv", event_rows)

    missed_rows = [r for r in event_rows if not r["event_detected"]]
    for m in missed_rows:
        m["failure_classification"] = "not detected under the official CARE event criterion (max criticality < 72)"
    write_csv_from_dicts(OUT_DIR / "missed_events.csv", missed_rows)

    # 7. Output Cross Farm Results (JSON & CSV)
    summaries_dicts = [asdict(s) for s in all_condition_summaries]
    write_csv_from_dicts(OUT_DIR / "cross_farm_results.csv", summaries_dicts)
    (OUT_DIR / "cross_farm_results.json").write_text(json.dumps(summaries_dicts, indent=2), encoding="utf-8")

    # 8. Feature & Protocol Manifest
    feature_manifest = {
        "feature_policy": "CARE_COMMON",
        "description": "Cross-farm aligned semantic triad matching WindADBench Track 4",
        "signals": ["wind_speed", "active_power", "rotor_speed"],
        "farm_mappings": FARM_COMMON_MAPPING,
    }
    (OUT_DIR / "feature_manifest.json").write_text(json.dumps(feature_manifest, indent=2), encoding="utf-8")

    elapsed_total = round(time.perf_counter() - t_start, 2)
    protocol_manifest = {
        "gate": "Gate 5.4 — Cross-Farm Wind Transfer & Target-Normal Calibration",
        "benchmark": "CARE to Compare (Gück et al., 2024)",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": elapsed_total,
        "transfers": [f"{s} -> {t}" for s, t in DIRECTED_TRANSFERS],
        "conditions": list(CONDITIONS),
        "criticality_threshold": CRITICALITY_THRESHOLD,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_unit": "turbine_cluster",
        "random_seed": RANDOM_SEED,
        "seed_classification": "REPRODUCIBILITY_CHOICE",
        "detector_config": {
            "name": "RAIChampionDetector",
            "feature_policy": "CARE_COMMON",
            "expected_power_curve": "Quadratic polynomial P = f(v_wind)",
            "expected_rotor_curve": "Quadratic polynomial Rotor = f(v_wind)",
            "residual_z_threshold": 2.5,
            "persistence_steps": 3,
            "persistence_window_minutes": 30,
        },
    }
    (OUT_DIR / "protocol_manifest.json").write_text(json.dumps(protocol_manifest, indent=2), encoding="utf-8")

    # 9. Summary Markdown
    lines = [
        "# Gate 5.4 — Cross-Farm Wind Transfer & Target-Normal Calibration Summary",
        "",
        "## 1. Executive Transfer Scorecard",
        "",
        f"Evaluated all 6 directed cross-farm transfers across 95 CARE datasets in {elapsed_total}s.",
        "",
        "| Source Farm | Target Farm | Frozen Source CARE | Calibrated CARE | Reference Target CARE | $\\Delta_{\\text{transfer}}$ | $\\Delta_{\\text{calibration}}$ | Gap Recovery |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in transfer_delta_rows:
        lines.append(
            f"| {row['source_farm']} | {row['target_farm']} | **{row['care_frozen']:.4f}** | "
            f"**{row['care_calibrated']:.4f}** | **{row['care_reference']:.4f}** | "
            f"{row['delta_transfer']:+.4f} | {row['delta_calibration_recovery']:+.4f} | {row['fraction_gap_recovered']} |"
        )

    lines.extend([
        "",
        "## 2. Directional Asymmetry Analysis",
        "",
        "| Pair | Forward Transfer ($S \\to T$) | Reverse Transfer ($T \\to S$) | Asymmetry (|$\\Delta$|)",
        "|---|---|---|---|",
    ])
    pairs = [
        (("Wind Farm A", "Wind Farm B"), ("Wind Farm B", "Wind Farm A")),
        (("Wind Farm A", "Wind Farm C"), ("Wind Farm C", "Wind Farm A")),
        (("Wind Farm B", "Wind Farm C"), ("Wind Farm C", "Wind Farm B")),
    ]
    for p_fwd, p_rev in pairs:
        row_fwd = next(r for r in transfer_delta_rows if (r["source_farm"], r["target_farm"]) == p_fwd)
        row_rev = next(r for r in transfer_delta_rows if (r["source_farm"], r["target_farm"]) == p_rev)
        asym = abs(row_fwd["delta_transfer"] - row_rev["delta_transfer"])
        lines.append(
            f"| {p_fwd[0]} $\\leftrightarrow$ {p_fwd[1]} | "
            f"{row_fwd['delta_transfer']:+.4f} (Frozen CARE {row_fwd['care_frozen']:.4f}) | "
            f"{row_rev['delta_transfer']:+.4f} (Frozen CARE {row_rev['care_frozen']:.4f}) | "
            f"**{asym:.4f}** |"
        )

    lines.extend([
        "",
        "## 3. Key Findings & Research Questions Answered",
        "- **Transferability under Frozen Source:** How much performance is lost under direct frozen transfer?",
        "- **Target-Normal Calibration:** Does adapting power/rotor curves on unlabelled normal target operation recover performance?",
        "- **Asymmetry:** Are transfer penalties symmetric or directional?",
        "- **Leakage Isolation:** Zero target fault labels or prediction-split data were accessed during calibration.",
    ])
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    log.info("Gate 5.4 execution completed successfully in %.2fs", elapsed_total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
