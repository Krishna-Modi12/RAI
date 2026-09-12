"""Test suite for Phase 4 Operational Decision Validation and Generalization Hardening."""

from __future__ import annotations

from pathlib import Path

import pytest

from rai.decision.regret import (
    simulate_independent_outcome_world_regret,
    simulate_model_world_regret,
)
from rai.decision.sensitivity import run_decision_sensitivity_suite
from rai.eval.abstention_eval import evaluate_abstention_battery
from rai.eval.agent_eval import evaluate_agent_orchestration_battery
from rai.eval.common_cause_eval import evaluate_common_cause_sensitivity
from rai.eval.explanation_eval import evaluate_explanation_ablation_and_boundaries
from rai.eval.failure_family_eval import evaluate_failure_family_leave_one_out
from rai.eval.rolling_forensics import analyze_rolling_origin_forensics
from rai.eval.sensor_safety_eval import evaluate_sensor_safety_gate
from rai.eval.soiling_validation import evaluate_solar_soiling_validation


def test_temporal_diagnosis_generates_artifacts(tmp_path: Path) -> None:
    """Verify rolling forensics outputs folds.csv, diagnosis.json, and summary.md."""
    gate2_json = Path("artifacts/evaluation/gate2/rolling_origin.json")
    if not gate2_json.is_file():
        pytest.skip("Gate 2 rolling origin summary not found")

    res = analyze_rolling_origin_forensics(gate2_json, tmp_path / "temporal")
    assert "records" in res
    assert "diagnosis_json" in res
    assert (tmp_path / "temporal" / "diagnosis.json").is_file()
    assert (tmp_path / "temporal" / "folds.csv").is_file()
    assert (tmp_path / "temporal" / "summary.md").is_file()
    assert res["holdout_prauc"] == 0.822


def test_failure_family_leave_one_out_honesty(tmp_path: Path) -> None:
    """Verify failure family leave-one-out reports NOT_COMPUTABLE for PR-AUC due to N=1 support."""
    res = evaluate_failure_family_leave_one_out(tmp_path / "families")
    assert res["status"] == "COMPLETED"
    assert res["total_failure_families"] == 6
    assert res["mean_event_recall"] == 1.0
    for r in res["records"]:
        assert r["pr_auc"] == "NOT_COMPUTABLE"
        assert r["support_count"] == 1


def test_model_world_regret_self_consistency() -> None:
    """Verify model-world regret provides a zero-regret self-consistency baseline."""
    res = simulate_model_world_regret(
        chosen_action="repair_now",
        has_real_defect=True,
        planned_repair_cost_inr=85_000.0,
        unplanned_failure_cost_inr=350_000.0,
        inspection_cost_inr=12_000.0,
        energy_loss_24h_inr=18_000.0,
        seed=42,
    )
    assert res.is_optimal is True
    assert res.regret_inr == 0.0


def test_independent_outcome_world_regret_is_imperfect() -> None:
    """Verify independent outcome world evaluates real operational risk (non-zero regret, not 100% optimal)."""
    sim = simulate_independent_outcome_world_regret(
        n_episodes=100,
        seed=42,
        failure_arrival_scale=1.0,
        repair_effectiveness=0.85,
        downtime_variance=1.3,
    )
    assert sim["status"] == "COMPLETED"
    assert sim["n_episodes"] == 100
    # True reality check: policy is NOT 100% optimal and mean regret is non-zero
    assert sim["mean_regret_inr"] > 0.0
    assert 60.0 <= sim["optimal_action_pct"] < 100.0


def test_decision_sensitivity_suite(tmp_path: Path) -> None:
    """Verify 8-regime decision sensitivity sweep identifies vulnerabilities."""
    res = run_decision_sensitivity_suite(tmp_path / "sens", n_episodes_per_regime=30, seed=42)
    assert res["status"] == "COMPLETED"
    assert res["n_regimes_evaluated"] == 8
    assert (tmp_path / "sens" / "sensitivity_analysis.csv").is_file()
    assert (tmp_path / "sens" / "sensitivity_analysis.json").is_file()


def test_sensor_safety_prevents_bad_dispatches(tmp_path: Path) -> None:
    """Verify sensor safety gate eliminates false dispatches from bad instrumentation."""
    res = evaluate_sensor_safety_gate(tmp_path / "safety")
    assert res["status"] == "COMPLETED"
    assert res["prevention_success_rate_pct"] == 100.0
    assert res["dangerous_non_abstentions"] == 0
    assert res["bad_dispatches_prevented"] >= 5


def test_common_cause_threshold_sweep(tmp_path: Path) -> None:
    """Verify peer consensus distinguishes isolated defects from farm-wide curtailment."""
    res = evaluate_common_cause_sensitivity(tmp_path / "cc")
    assert res["status"] == "COMPLETED"
    assert res["optimal_threshold_pct"] == 30.0
    assert res["isolated_fault_accuracy_at_optimal"] == 1.0
    assert res["common_cause_accuracy_at_optimal"] == 1.0


def test_abstention_battery_safety(tmp_path: Path) -> None:
    """Verify explicit abstention layer has zero dangerous non-abstentions."""
    res = evaluate_abstention_battery(tmp_path / "abst")
    assert res["status"] == "COMPLETED"
    assert res["dangerous_non_abstentions"] == 0
    assert res["action_precision_pct"] == 100.0
    assert res["decision_coverage_pct"] > 0.0


def test_explanation_ablation_flips_decisions(tmp_path: Path) -> None:
    """Verify counterfactual feature ablation causes causal decision flips."""
    res = evaluate_explanation_ablation_and_boundaries(tmp_path / "expl")
    assert res["status"] == "COMPLETED"
    # Removing temperature, vibration, peer context, or sensor health flips decisions
    flips = [f for f in res["feature_ablations"] if f["action_flipped"]]
    assert len(flips) >= 4
    assert len(res["counterfactual_decision_boundaries"]) >= 4


def test_local_agent_zero_hallucinations(tmp_path: Path) -> None:
    """Verify agent battery confirms zero hallucination and strict engine alignment."""
    res = evaluate_agent_orchestration_battery(tmp_path / "agent")
    assert res["status"] == "COMPLETED"
    assert res["compliance_rate_pct"] == 100.0
    assert res["hallucinated_values_detected"] == 0
    assert res["decision_engine_overrides"] == 0
    assert res["temporal_eligibility_violations"] == 0


def test_solar_soiling_model_to_model(tmp_path: Path) -> None:
    """Verify solar soiling benchmark against RdTools is labeled model-to-model comparison."""
    res = evaluate_solar_soiling_validation(tmp_path / "soiling")
    assert "MODEL_TO_MODEL_COMPARISON" in res["comparison_type"]
    assert res["agreement_rmse"] < 0.05
