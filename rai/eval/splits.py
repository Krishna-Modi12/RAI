"""Dataset splitting protocols for 4-level generalization validation.

Level 1: Temporal holdout (past -> future with embargo gap)
Level 2: Asset holdout (disjoint turbine / inverter subsets)
Level 3: Site / farm holdout (cross-geography evaluation)
Level 4: Out-of-distribution (OOD) synthetic challenge (unseen progression physics)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from rai.eval.leakage import assert_no_leakage


@dataclass(frozen=True)
class PartitionSplit:
    name: str
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    metadata: dict[str, Any]


PIPELINE_MAX_LOOKBACK_HOURS: float = 336.0  # 14 days (anomaly trailing window)
PIPELINE_THERMAL_LAG_HOURS: float = 6.0      # 360m thermal load window
TARGET_PREDICTION_HORIZON_HOURS: float = 336.0  # 14 days target P-F horizon


def compute_pipeline_embargo_hours(
    lookback_hours: float = PIPELINE_MAX_LOOKBACK_HOURS,
    lag_hours: float = PIPELINE_THERMAL_LAG_HOURS,
) -> float:
    """Compute mathematically justified minimum embargo gap between train and test.

    To ensure that the earliest test sample at t_test cannot read any observation
    from the training interval [t_train_start, t_train_end], the embargo gap must satisfy:
        gap >= lookback_hours + lag_hours
    """
    return float(lookback_hours + lag_hours)


def split_temporal(
    df: pd.DataFrame,
    time_col: str = "ts",
    train_frac: float = 0.55,
    val_frac: float = 0.15,
    gap_hours: float | None = None,
) -> PartitionSplit:
    """Temporal split with enforced mathematically derived embargo gaps between train, val, and test."""
    ordered = df.sort_values(time_col).reset_index(drop=True)
    n = len(ordered)
    if n < 100:
        raise ValueError(f"Insufficient observations for temporal splitting (n={n})")

    t_series = pd.to_datetime(ordered[time_col], utc=True)
    t_min = t_series.min()
    t_max = t_series.max()
    min_embargo = compute_pipeline_embargo_hours()
    actual_gap = gap_hours if gap_hours is not None else min_embargo
    if actual_gap < min_embargo:
        import logging
        logging.getLogger(__name__).warning(
            "Specified gap_hours (%.1f) is below mathematically required embargo (%.1f)",
            actual_gap,
            min_embargo,
        )

    train_end_target = t_min + pd.Timedelta(hours=total_span * train_frac)
    val_start_target = train_end_target + pd.Timedelta(hours=actual_gap)
    val_end_target = val_start_target + pd.Timedelta(hours=total_span * val_frac)
    test_start_target = val_end_target + pd.Timedelta(hours=actual_gap)

    train = ordered[t_series <= train_end_target].copy()
    val = ordered[(t_series >= val_start_target) & (t_series <= val_end_target)].copy()
    test = ordered[t_series >= test_start_target].copy()

    # Verify zero leakage across the partitions
    if not train.empty and not val.empty:
        assert_no_leakage(train, val, time_col=time_col, min_gap_hours=actual_gap)
    if not val.empty and not test.empty:
        assert_no_leakage(val, test, time_col=time_col, min_gap_hours=actual_gap)

    return PartitionSplit(
        name="level_1_temporal_holdout",
        train=train,
        val=val,
        test=test,
        metadata={
            "train_rows": len(train),
            "val_rows": len(val),
            "test_rows": len(test),
            "gap_hours": actual_gap,
            "train_span": f"{train[time_col].min()} to {train[time_col].max()}",
            "test_span": f"{test[time_col].min()} to {test[time_col].max()}",
        },
    )


def generate_rolling_origin_folds(
    df: pd.DataFrame,
    time_col: str = "ts",
    n_folds: int = 4,
    min_train_days: float = 14.0,
    val_days: float = 3.0,
    test_days: float = 4.0,
    embargo_hours: float | None = None,
) -> list[PartitionSplit]:
    """Generate strictly chronological rolling-origin evaluation folds.

    Fold k:
      Train: [t_start, t_k]
      Embargo: gap of embargo_hours
      Validation: [t_k + embargo, t_k + embargo + val_days]
      Embargo: gap of embargo_hours
      Test: [t_val_end + embargo, t_val_end + embargo + test_days]
    """
    eff_embargo = embargo_hours if embargo_hours is not None else compute_pipeline_embargo_hours()
    ordered = df.sort_values(time_col).reset_index(drop=True)
    t_series = pd.to_datetime(ordered[time_col], utc=True)
    t_min = t_series.min()
    t_max = t_series.max()
    total_days = (t_max - t_min).total_seconds() / 86400.0

    folds: list[PartitionSplit] = []
    embargo_delta = pd.Timedelta(hours=eff_embargo)
    val_delta = pd.Timedelta(days=val_days)
    test_delta = pd.Timedelta(days=test_days)

    step_days = max(1.0, (total_days - min_train_days - val_days - test_days - (eff_embargo * 2 / 24.0)) / max(n_folds - 1, 1))

    for k in range(n_folds):
        train_end = t_min + pd.Timedelta(days=min_train_days + k * step_days)
        val_start = train_end + embargo_delta
        val_end = val_start + val_delta
        test_start = val_end + embargo_delta
        test_end = test_start + test_delta

        test_end = min(test_end, t_max)

        train_part = ordered[t_series <= train_end].copy()
        val_part = ordered[(t_series >= val_start) & (t_series <= val_end)].copy()
        test_part = ordered[(t_series >= test_start) & (t_series <= test_end)].copy()

        if len(train_part) < 20 or len(test_part) < 10:
            continue

        folds.append(
            PartitionSplit(
                name=f"rolling_origin_fold_{k + 1}",
                train=train_part,
                val=val_part,
                test=test_part,
                metadata={
                    "fold_index": k + 1,
                    "train_span": f"{train_part[time_col].min()} to {train_part[time_col].max()}",
                    "val_span": f"{val_part[time_col].min()} to {val_part[time_col].max()}" if not val_part.empty else "empty",
                    "test_span": f"{test_part[time_col].min()} to {test_part[time_col].max()}",
                    "embargo_hours": embargo_hours,
                    "train_rows": len(train_part),
                    "val_rows": len(val_part),
                    "test_rows": len(test_part),
                },
            )
        )

    return folds


def split_asset_holdout(
    df: pd.DataFrame,
    asset_col: str = "asset_id",
    test_frac: float = 0.25,
    seed: int = 20260912,
    held_out_assets: list[str] | None = None,
) -> PartitionSplit:
    """Asset holdout split: entire assets are held out completely."""
    all_assets = sorted(df[asset_col].unique())
    n_assets = len(all_assets)

    if held_out_assets is not None:
        test_assets = set(held_out_assets)
        train_val_assets = [a for a in all_assets if a not in test_assets]
    else:
        rng = np.random.default_rng(seed)
        n_test = max(1, int(round(n_assets * test_frac)))
        shuffled = rng.permutation(all_assets)
        test_assets = set(shuffled[:n_test])
        train_val_assets = list(shuffled[n_test:])

    # Split remaining into train (80%) and val (20%)
    n_val = max(1, int(len(train_val_assets) * 0.20))
    val_assets = set(train_val_assets[:n_val])
    train_assets = set(train_val_assets[n_val:])

    train = df[df[asset_col].isin(train_assets)].copy()
    val = df[df[asset_col].isin(val_assets)].copy()
    test = df[df[asset_col].isin(test_assets)].copy()

    # Verify disjointness
    assert len(train_assets.intersection(test_assets)) == 0, "Asset leak detected between train and test"
    assert len(val_assets.intersection(test_assets)) == 0, "Asset leak detected between val and test"

    return PartitionSplit(
        name="level_2_asset_holdout",
        train=train,
        val=val,
        test=test,
        metadata={
            "train_assets": sorted(train_assets),
            "val_assets": sorted(val_assets),
            "test_assets": sorted(test_assets),
            "train_rows": len(train),
            "test_rows": len(test),
        },
    )


def split_site_holdout(
    df: pd.DataFrame,
    test_site: str,
    site_col: str = "site",
) -> PartitionSplit:
    """Site holdout split: evaluates cross-site generalization."""
    if site_col not in df.columns:
        raise ValueError(f"Missing site column '{site_col}'")

    train_val_df = df[df[site_col] != test_site].copy()
    test_df = df[df[site_col] == test_site].copy()

    # Split train_val temporally or by asset
    half = len(train_val_df) // 2
    train = train_val_df.iloc[:half].copy()
    val = train_val_df.iloc[half:].copy()

    return PartitionSplit(
        name=f"level_3_site_holdout_{test_site}",
        train=train,
        val=val,
        test=test_df,
        metadata={
            "held_out_site": test_site,
            "train_rows": len(train),
            "test_rows": len(test_df),
        },
    )


def generate_ood_challenge_factors(
    base_events: list[dict[str, Any]],
    seed: int = 20260912,
) -> list[dict[str, Any]]:
    """Synthesize Level 4 Out-of-Distribution parameter perturbations.

    Alters degradation progression speeds, noise regimes, and weather regimes
    to prove the detector did not merely memorize simulator parameters.
    """
    rng = np.random.default_rng(seed)
    ood_events: list[dict[str, Any]] = []

    for ev in base_events:
        copied = dict(ev)
        # Randomize progression rate: 0.5x (much slower) to 2.5x (much faster)
        rate_multiplier = float(rng.uniform(0.5, 2.5))
        # Randomize noise inflation: 1.2x to 3.0x
        noise_inflation = float(rng.uniform(1.2, 3.0))

        copied["ood_rate_multiplier"] = round(rate_multiplier, 3)
        copied["ood_noise_inflation"] = round(noise_inflation, 3)
        copied["is_ood"] = True
        ood_events.append(copied)

    return ood_events


def split_asset_holdout_stratified(
    df: pd.DataFrame,
    fault_asset_ids: list[str] | set[str],
    asset_col: str = "asset_id",
    test_fault_count: int = 2,
    test_healthy_frac: float = 0.25,
    seed: int = 20260912,
) -> PartitionSplit:
    """Stratified asset holdout: guarantees positive failure events in the held-out test split.

    Avoids the small-sample zero-positive failure trap where random asset holdout leaves
    the test partition with 0 positive cases and uncomputable PR-AUC.
    """
    fault_set = set(fault_asset_ids)
    all_assets = sorted(df[asset_col].unique())
    faulted_in_df = [a for a in all_assets if a in fault_set]
    healthy_in_df = [a for a in all_assets if a not in fault_set]

    rng = np.random.default_rng(seed)
    shuffled_faults = list(rng.permutation(faulted_in_df))
    shuffled_healthy = list(rng.permutation(healthy_in_df))

    n_test_faults = min(max(1, test_fault_count), len(shuffled_faults))
    test_fault_assets = set(shuffled_faults[:n_test_faults])
    train_val_fault_assets = set(shuffled_faults[n_test_faults:])

    n_test_healthy = max(1, int(round(len(shuffled_healthy) * test_healthy_frac)))
    test_healthy_assets = set(shuffled_healthy[:n_test_healthy])
    train_val_healthy_assets = set(shuffled_healthy[n_test_healthy:])

    test_assets = test_fault_assets.union(test_healthy_assets)
    train_val_assets = list(train_val_fault_assets.union(train_val_healthy_assets))

    # Split remaining into train (80%) and val (20%)
    n_val = max(1, int(len(train_val_assets) * 0.20))
    shuffled_tv = list(rng.permutation(train_val_assets))
    val_assets = set(shuffled_tv[:n_val])
    train_assets = set(shuffled_tv[n_val:])

    # Disjointness checks
    assert len(train_assets.intersection(test_assets)) == 0, "Leak: train and test assets overlap"
    assert len(val_assets.intersection(test_assets)) == 0, "Leak: val and test assets overlap"

    train = df[df[asset_col].isin(train_assets)].copy()
    val = df[df[asset_col].isin(val_assets)].copy()
    test = df[df[asset_col].isin(test_assets)].copy()

    return PartitionSplit(
        name="level_2_asset_holdout_stratified",
        train=train,
        val=val,
        test=test,
        metadata={
            "train_assets": sorted(train_assets),
            "val_assets": sorted(val_assets),
            "test_assets": sorted(test_assets),
            "test_fault_assets": sorted(test_fault_assets),
            "test_healthy_assets": sorted(test_healthy_assets),
            "train_rows": len(train),
            "val_rows": len(val),
            "test_rows": len(test),
            "stratified": True,
        },
    )


def generate_stratified_kfold_splits(
    df: pd.DataFrame,
    fault_asset_ids: list[str] | set[str],
    asset_col: str = "asset_id",
    n_folds: int = 3,
    seed: int = 20260912,
) -> list[PartitionSplit]:
    """Generate k-fold cross-validation splits stratified across faulted and healthy assets."""
    fault_set = set(fault_asset_ids)
    all_assets = sorted(df[asset_col].unique())
    faulted_in_df = [a for a in all_assets if a in fault_set]
    healthy_in_df = [a for a in all_assets if a not in fault_set]

    rng = np.random.default_rng(seed)
    shuffled_faults = list(rng.permutation(faulted_in_df))
    shuffled_healthy = list(rng.permutation(healthy_in_df))

    # Partition faults into n_folds
    fault_folds = [shuffled_faults[i::n_folds] for i in range(n_folds)]
    healthy_folds = [shuffled_healthy[i::n_folds] for i in range(n_folds)]

    splits: list[PartitionSplit] = []
    for k in range(n_folds):
        test_assets = set(fault_folds[k] + healthy_folds[k])
        train_val_assets = [a for a in all_assets if a not in test_assets]

        n_val = max(1, len(train_val_assets) // 4)
        val_assets = set(train_val_assets[:n_val])
        train_assets = set(train_val_assets[n_val:])

        train = df[df[asset_col].isin(train_assets)].copy()
        val = df[df[asset_col].isin(val_assets)].copy()
        test = df[df[asset_col].isin(test_assets)].copy()

        splits.append(
            PartitionSplit(
                name=f"stratified_kfold_{k + 1}_of_{n_folds}",
                train=train,
                val=val,
                test=test,
                metadata={
                    "fold_index": k + 1,
                    "n_folds": n_folds,
                    "test_assets": sorted(test_assets),
                    "test_fault_assets": sorted(set(fault_folds[k])),
                    "test_healthy_assets": sorted(set(healthy_folds[k])),
                    "train_assets": sorted(train_assets),
                    "val_assets": sorted(val_assets),
                },
            )
        )
    return splits


def apply_ood_telemetry_perturbations(
    df: pd.DataFrame,
    noise_factor: float = 1.8,
    bias_drift_c: float = 2.5,
    ambient_shock_c: float = 4.0,
    seed: int = 20260912,
) -> pd.DataFrame:
    """Apply physical out-of-distribution stressors to telemetry for robustness evaluation.

    Perturbations include:
    1. Sensor measurement noise amplification.
    2. Subtle calibration drift on thermal channels.
    3. Severe ambient temperature shock (simulating heatwave / cold snap).
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    rng = np.random.default_rng(seed)
    n = len(out)

    # 1. Thermal channels noise & drift
    thermal_cols = [c for c in out.columns if "temp" in c]
    for col in thermal_cols:
        raw_vals = pd.to_numeric(out[col], errors="coerce").to_numpy(dtype=float)
        std_val = float(np.nanstd(raw_vals)) if len(raw_vals) > 1 else 1.0
        # Add scaled Gaussian noise
        noise = rng.normal(0, std_val * (noise_factor - 1.0) * 0.5, size=n)
        # Add linear calibration drift
        drift = np.linspace(0, bias_drift_c, n)
        out[col] = raw_vals + noise + drift

    # 2. Ambient temperature shock
    if "ambient_temp_c" in out.columns:
        amb = pd.to_numeric(out["ambient_temp_c"], errors="coerce").to_numpy(dtype=float)
        out["ambient_temp_c"] = amb + ambient_shock_c

    # 3. Vibration noise
    if "drivetrain_vibration_mms" in out.columns:
        vib = pd.to_numeric(out["drivetrain_vibration_mms"], errors="coerce").to_numpy(dtype=float)
        vib_noise = np.abs(rng.normal(0, 0.25 * noise_factor, size=n))
        out["drivetrain_vibration_mms"] = np.clip(vib + vib_noise, 0.0, 50.0)

    # 4. Inverter active power jitter
    if "active_power_kw" in out.columns:
        pwr = pd.to_numeric(out["active_power_kw"], errors="coerce").to_numpy(dtype=float)
        pwr_noise = rng.normal(0, np.nanstd(pwr) * 0.10 * noise_factor if len(pwr) > 1 else 1.0, size=n)
        out["active_power_kw"] = np.clip(pwr + pwr_noise, 0.0, None)

    out.attrs["is_ood_perturbed"] = True
    out.attrs["noise_factor"] = noise_factor
    out.attrs["bias_drift_c"] = bias_drift_c
    out.attrs["ambient_shock_c"] = ambient_shock_c
    return out
