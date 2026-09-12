"""Unit tests for next-generation decision intelligence features.

Tests:
1. Decision Regret calculation (mean, median, p95)
2. Value of Information (VOI) for pre-repair inspection
3. Decision sensitivity analysis ('What evidence would change the decision?')
4. Risk attribution change explanation ('Why did risk increase?')
5. Closed-loop maintenance feedback logging
"""

from __future__ import annotations

import pytest

from rai.decision import (
    DecisionEngine,
    DecisionEvidence,
    NumericRange,
    analyze_decision_sensitivity,
    compute_scenario_regret,
    compute_value_of_information,
    explain_risk_change,
    standard_scenarios,
    summarize_decision_regret,
)


def _sample_evidence() -> DecisionEvidence:
    return DecisionEvidence(
        asset_id="WT-017",
        asset_type="wind_turbine",
        component="gearbox",
        evidence_score=0.88,
        confidence=NumericRange(0.80, 0.92),
        available_signals=3,
        required_signals=2,
        persistence_hours=14.0,
        required_persistence_hours=6.0,
    )


def test_decision_regret_computation():
    scenarios = standard_scenarios(
        asset_type="wind_turbine",
        intervention_cost_inr=80_000,
        inspection_cost_inr=10_000,
        failure_consequence_inr=850_000,
        failure_probability=0.25,
        energy_loss_24h_inr=15_000,
    )
    result = DecisionEngine().evaluate(_sample_evidence(), scenarios)
    evals = result.scenarios

    # Optimal scenario is evals[0] (lowest expected cost)
    optimal = evals[0]
    suboptimal = evals[-1]

    # Regret for choosing optimal should be zero
    reg_opt = compute_scenario_regret(chosen=optimal, optimal=optimal, scenario_name="test_opt")
    assert reg_opt.regret_inr == 0.0
    assert reg_opt.is_optimal is True

    # Regret for choosing suboptimal should be positive
    reg_sub = compute_scenario_regret(chosen=suboptimal, optimal=optimal, scenario_name="test_sub")
    assert reg_sub.regret_inr > 0.0
    assert reg_sub.is_optimal is False

    # Summary statistics
    summary = summarize_decision_regret([reg_opt, reg_sub])
    assert summary.scenario_count == 2
    assert summary.optimal_decision_pct == 0.5
    assert summary.mean_regret_inr == pytest.approx(reg_sub.regret_inr / 2.0, abs=1.0)


def test_value_of_information_justifies_inspection():
    # Moderate prior risk (20%), overhaul costs ₹150,000, failure consequence ₹1,200,000, inspection ₹12,000
    voi = compute_value_of_information(
        prior_failure_probability=0.20,
        repair_cost_inr=150_000,
        failure_consequence_inr=1_200_000,
        inspection_cost_inr=12_000,
        energy_loss_deferral_inr=5_000,
    )

    # In this regime, inspecting resolves uncertainty without committing to ₹150k overhaul
    assert voi.voi_inr > 0.0
    assert voi.is_inspection_justified is True
    assert "INSPECT FIRST is justified" in voi.recommendation


def test_value_of_information_high_risk_immediate_repair():
    # Very high prior risk (85%): inspection unlikely to clear asset, repair immediately
    voi = compute_value_of_information(
        prior_failure_probability=0.85,
        repair_cost_inr=150_000,
        failure_consequence_inr=1_200_000,
        inspection_cost_inr=25_000,
    )
    assert voi.is_inspection_justified is False
    assert "REPAIR IMMEDIATELY" in voi.recommendation


def test_analyze_decision_sensitivity():
    sens = analyze_decision_sensitivity(
        current_action="inspect_first",
        asset_type="wind_turbine",
        risk_score=0.68,
        thermal_z_score=3.2,
    )
    assert sens.current_recommendation == "inspect_first"
    assert len(sens.stable_under) >= 2
    assert any("MONITOR" in trigger for trigger in sens.changes_if)


def test_explain_risk_change_numeric():
    expl = explain_risk_change(
        asset_id="WT-017",
        current_risk=0.68,
        previous_risk=0.42,
        thermal_residual_delta=2.1,
        persistence_delta_hours=12.0,
        peer_isolation_score=0.85,
        historical_case_similarity=0.72,
        environmental_explanation=0.10,
    )
    assert expl.risk_change_pp == pytest.approx(26.0, abs=0.1)
    assert len(expl.contributors) >= 4
    # Thermal divergence should be a primary driver
    assert expl.contributors[0]["factor"] == "Thermal Residual Divergence"
    assert expl.contributors[0]["direction"] == "elevating"
