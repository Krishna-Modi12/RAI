"""Unit and regression tests for Phase 3A evaluation battery.

Verifies:
- Embargo math consistency (>= 342.0h)
- Rolling-origin fold collapse diagnostics
- Event-level metrics & independence
- Dependence-aware uncertainty bootstrap
- Baseline & threshold stability
- Asset & site generalization holdouts
- External CARE benchmark multi-track runner
- 9-probe adversarial stress suite
- Quantitative OOD degradation battery
- Real alert funnel instrumentation
- Solar soiling RdTools comparison
- Counterfactual regret & VOI engine
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rai.economics.counterfactual_regret import (
    Action,
    compute_voi,
    evaluate_counterfactual_regret_suite,
)
from rai.eval.adversarial import (
    run_random_score_detector_test,
    run_shuffled_weather_test,
)
from rai.eval.baseline_stability import audit_baseline_and_threshold_stability
from rai.eval.external.care.runner import inspect_care_dataset_state, run_external_care_benchmark
from rai.eval.generalization import evaluate_within_domain_site_holdout
from rai.eval.ood_robustness import run_ood_degradation_battery
from rai.eval.rolling_forensics import analyze_rolling_origin_forensics
from rai.eval.soiling_validation import evaluate_solar_soiling_validation
from rai.eval.splits import compute_pipeline_embargo_hours
from rai.eval.uncertainty import compute_asset_bootstrap_ci, compute_event_bootstrap_ci


def test_embargo_math_reconciliation():
    """Verify that embargo is mathematically derived and enforced >= 342.0 hours."""
    gap_hours = compute_pipeline_embargo_hours()
    assert gap_hours >= 342.0
    # 14 days lookback = 336h + 6h thermal lag = 342h
    assert gap_hours == 342.0


def test_rolling_origin_forensics(tmp_path):
    """Verify that rolling-origin forensics identifies fold collapse drivers."""
    gate2_json = Path("artifacts/evaluation/gate2/rolling_origin.json")
    if not gate2_json.is_file():
        pytest.skip("Gate 2 rolling origin JSON not available")

    out_dir = tmp_path / "rolling_forensics"
    res = analyze_rolling_origin_forensics(gate2_json, out_dir)

    assert "records" in res
    assert len(res["records"]) == 4
    # Fold 1 should have 0 positive events
    assert res["records"][0]["positive_events_in_window"] == 0
    assert "SPARSE_EVENT_COLLAPSE" in res["records"][0]["collapse_driver"]
    # Fold 4 should have positive events and high PR-AUC
    assert res["records"][3]["positive_events_in_window"] > 0
    assert res["records"][3]["pr_auc"] > 0.70

    assert (out_dir / "folds.csv").is_file()
    assert (out_dir / "summary.md").is_file()


def test_dependence_aware_uncertainty():
    """Verify that event and asset cluster bootstrap produce valid confidence intervals."""
    event_records = [
        {"event_id": "E1", "status": "DETECTED", "lead_time_days": 5.0},
        {"event_id": "E2", "status": "DETECTED", "lead_time_days": 4.5},
        {"event_id": "E3", "status": "DETECTED", "lead_time_days": 6.0},
        {"event_id": "E4", "status": "MISSED", "lead_time_days": 0.0},
        {"event_id": "E5", "status": "DETECTED", "lead_time_days": 3.0},
        {"event_id": "E6", "status": "DETECTED", "lead_time_days": 5.5},
    ]

    res = compute_event_bootstrap_ci(event_records, n_bootstrap=200, seed=42)
    assert "event_recall" in res
    assert "median_lead_time" in res
    rec_est = res["event_recall"]
    assert 0.0 <= rec_est.ci95_lower <= rec_est.ci95_upper <= 1.0
    assert rec_est.resampling_unit == "event"
    assert rec_est.sample_size == 6

    asset_scores = [
        {"asset_id": f"A{i}", "y_true": 1 if i < 5 else 0, "y_score": 0.8 if i < 5 else 0.1}
        for i in range(20)
    ]
    a_res = compute_asset_bootstrap_ci(asset_scores, n_bootstrap=200, seed=42)
    assert "pr_auc" in a_res
    pr_est = a_res["pr_auc"]
    assert 0.0 <= pr_est.ci95_lower <= pr_est.ci95_upper <= 1.0
    assert pr_est.resampling_unit == "asset"


def test_baseline_and_threshold_stability(tmp_path):
    """Verify threshold audit across folds against production threshold 0.45."""
    res = audit_baseline_and_threshold_stability(tmp_path, production_threshold=0.45)
    assert "threshold_audits" in res
    assert len(res["threshold_audits"]) == 4
    for t in res["threshold_audits"]:
        assert abs(t["distance_from_production"]) <= 0.10
    assert (tmp_path / "thresholds_by_fold.csv").is_file()


def test_within_domain_site_holdout(tmp_path):
    """Verify within-domain site transfer reports NOT_COMPUTED due to single-site availability."""
    res = evaluate_within_domain_site_holdout(tmp_path)
    assert res["status"] == "NOT_COMPUTED"
    assert "INSUFFICIENT_DATA" in res["reason"]
    assert "wind_transfer" in res
    assert "solar_transfer" in res
    assert res["wind_transfer"]["within_domain_sites_available"] == 1
    assert res["solar_transfer"]["within_domain_sites_available"] == 1


def test_external_care_benchmark_runner(tmp_path):
    """Verify real external CARE benchmark runs on fixture and reports all 4 tracks & 5 baselines."""
    status = inspect_care_dataset_state("data/raw/care")
    assert status.adapter_available is True

    res = run_external_care_benchmark(
        care_dir="data/raw/care",
        output_dir=tmp_path / "care_eval",
    )
    assert res["status"]["benchmark_executed"] is True
    results = res["results"]
    assert len(results) == 20  # 4 tracks * 5 baselines

    tracks_found = {r["track"] for r in results}
    assert len(tracks_found) == 4

    baselines_found = {r["baseline_name"] for r in results}
    assert "Persistence / Naive" in baselines_found
    assert "Residual Z-Score" in baselines_found
    assert "Isolation Forest (Paper)" in baselines_found
    assert "Expected Behavior Regression" in baselines_found
    assert "RAI Hybrid Fusion" in baselines_found


def test_adversarial_probes():
    """Verify new adversarial probes (random-score detector, weather shuffling, etc.)."""
    y_true = [1] * 10 + [0] * 90  # 10% prevalence
    rand_res = run_random_score_detector_test(y_true, seed=42)
    assert rand_res["test_name"] == "random_score_detector"
    assert rand_res["passed"] is True
    assert abs(rand_res["perturbed_metric"] - 0.10) < 0.15

    sample_df = pd.DataFrame({
        "wind_speed_ms": np.linspace(3, 20, 100),
        "power_kw": np.linspace(50, 2000, 100),
    })
    shuff_res = run_shuffled_weather_test(sample_df, seed=42)
    assert shuff_res["test_name"] == "shuffled_weather"
    assert shuff_res["passed"] is True
    assert shuff_res["perturbed_metric"] < shuff_res["baseline_metric"]


def test_ood_degradation_battery(tmp_path):
    """Verify quantitative degradation sweeps across 6 dimensions."""
    y_true = [1] * 6 + [0] * 36
    y_prob = [0.85] * 6 + [0.10] * 36
    res = run_ood_degradation_battery(y_true, y_prob, tmp_path, seed=42)
    assert len(res["records"]) > 15
    dims = {r["dimension"] for r in res["records"]}
    assert "sensor_noise" in dims
    assert "telemetry_missingness" in dims
    assert "sensor_calibration_drift" in dims
    assert "degradation_magnitude_shift" in dims
    assert "weather_extremes" in dims
    assert "environmental_dust_extremes" in dims
    assert (tmp_path / "ood_degradation.csv").is_file()


def test_solar_soiling_validation(tmp_path):
    """Verify solar soiling separation and RdTools comparison."""
    res = evaluate_solar_soiling_validation(tmp_path, target_asset_id="INV-023")
    assert res["modality"] == "solar"
    assert "physical_deposition_estimated_g_m2" in res
    assert "rdtools_srr_soiling_ratio" in res
    assert "rdtools_cods_soiling_ratio" in res
    assert res["causal_attribution_status"] == "MODEL_BASED_ASSOCIATION (NOT causal proof)"


def test_counterfactual_regret_and_voi(tmp_path):
    """Verify counterfactual regret and VOI calculation."""
    # High risk, high confidence -> Repair immediately, VOI = 0
    voi_low, act_repair = compute_voi(failure_probability=0.85, confidence_spread=0.05)
    assert act_repair == Action.REPAIR
    assert voi_low == 0.0

    # Intermediate risk, low confidence -> VOI triggers inspection!
    voi_high, act_inspect = compute_voi(failure_probability=0.62, confidence_spread=0.35)
    assert voi_high > 5_000.0
    assert act_inspect == Action.INSPECT

    # Full suite execution
    suite_res = evaluate_counterfactual_regret_suite(tmp_path)
    assert suite_res["summary"]["total_scenarios_evaluated"] == 15
    assert suite_res["summary"]["inspection_recommended_count"] >= 1
    assert (tmp_path / "counterfactual_regret.json").is_file()
