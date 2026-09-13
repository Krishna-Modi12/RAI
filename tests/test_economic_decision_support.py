from rai.economics.decision_support import EconomicDecision, evaluate_decision_support


def _decision(**overrides):
    values = {
        "asset_id": "WT-017",
        "component": "gearbox",
        "risk_score": 0.82,
        "risk_calibration": "isotonic",
        "risk_window_days": (7, 21),
    }
    values.update(overrides)
    return evaluate_decision_support(**values)


def test_clear_intervention_case_is_explicit_and_assumption_labelled():
    result = _decision()
    assert result.decision is EconomicDecision.INTERVENE
    assert result.status == "ESTIMATED_UNDER_EXPLICIT_ASSUMPTIONS"
    assert result.information_value_inr is None
    assert any(item.state.value == "ASSUMED" for item in result.assumptions)


def test_monitor_and_wait_are_distinct_low_consequence_paths():
    assert _decision(risk_score=0.35).decision is EconomicDecision.MONITOR
    assert _decision(risk_score=0.05).decision is EconomicDecision.WAIT


def test_inspect_first_when_environment_conflicts_or_uncertainty_is_wide():
    assert _decision(environmental_explanation=0.75).decision is EconomicDecision.INSPECT
    assert _decision(confidence_width=0.50).decision is EconomicDecision.INSPECT


def test_insufficient_data_abstains_without_zero_values():
    result = _decision(risk_score=None)
    assert result.decision is EconomicDecision.ABSTAIN
    assert result.status == "ECONOMIC_CONSEQUENCE_NOT_ESTIMABLE"
    assert result.expected_waiting_consequence_inr is None
    assert result.intervention_cost_inr is None


def test_sensor_conflict_abstains_and_preserves_observed_state():
    result = _decision(sensor_health="failed")
    assert result.decision is EconomicDecision.ABSTAIN
    assert any(item.name == "sensor_health" and item.state.value == "OBSERVED" for item in result.assumptions)


def test_unknown_component_abstains():
    result = _decision(component="unrecorded_component")
    assert result.decision is EconomicDecision.ABSTAIN
    assert "component cost basis" in result.uncertainty[0]


def test_zero_risk_is_not_unknown_and_zero_loss_is_not_fabricated():
    result = _decision(risk_score=0.0)
    assert result.decision is EconomicDecision.WAIT
    assert result.expected_waiting_consequence_inr is not None
