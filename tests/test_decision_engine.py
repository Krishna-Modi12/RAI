"""Focused tests for deterministic maintenance counterfactuals."""

from rai.decision import (
    CounterfactualScenario,
    DecisionAction,
    DecisionEngine,
    DecisionEvidence,
    DecisionPolicy,
    NumericRange,
    standard_scenarios,
)


def _evidence(**overrides) -> DecisionEvidence:
    values = {
        "asset_id": "WT-017",
        "asset_type": "wind_turbine",
        "component": "gearbox",
        "evidence_score": 0.9,
        "confidence": NumericRange(0.82, 0.90),
        "available_signals": 3,
        "required_signals": 2,
        "persistence_hours": 12.0,
        "required_persistence_hours": 6.0,
    }
    values.update(overrides)
    return DecisionEvidence(**values)


def _scenario(action, intervention, energy, probability, consequence, delay=0):
    return CounterfactualScenario(
        action=action,
        delay_hours=delay,
        intervention_cost_inr=intervention,
        energy_loss_inr=energy,
        failure_probability=probability,
        failure_consequence_inr=consequence,
    )


def test_expected_cost_ordering_selects_repair_now():
    scenarios = [
        _scenario(DecisionAction.REPAIR_NOW, 100_000, 0, 0.0, 1_000_000),
        _scenario(DecisionAction.DEFER_24H, 100_000, 10_000, 0.20, 1_000_000, 24),
        _scenario(DecisionAction.DO_NOTHING, 0, 300_000, 0.80, 1_000_000),
    ]

    result = DecisionEngine().evaluate(_evidence(), scenarios)

    assert result.policy is DecisionPolicy.ACT
    assert result.recommended_action is DecisionAction.REPAIR_NOW
    assert [item.scenario.action for item in result.scenarios] == [
        DecisionAction.REPAIR_NOW,
        DecisionAction.DEFER_24H,
        DecisionAction.DO_NOTHING,
    ]
    assert result.scenarios[1].expected_cost_inr.midpoint == 310_000


def test_uncertainty_is_propagated_without_sampling():
    scenarios = [
        _scenario(
            DecisionAction.INSPECT_FIRST,
            NumericRange(10_000, 20_000),
            NumericRange(1_000, 3_000),
            NumericRange(0.10, 0.30),
            NumericRange(100_000, 200_000),
        )
    ]

    result = DecisionEngine().evaluate(_evidence(), scenarios)
    cost = result.scenarios[0].expected_cost_inr

    assert cost.low == 21_000
    assert cost.high == 83_000
    assert result.recommended_action is DecisionAction.INSPECT_FIRST


def test_abstains_when_evidence_is_insufficient():
    scenarios = [
        _scenario(DecisionAction.REPAIR_NOW, 100_000, 0, 0.0, 1_000_000),
        _scenario(DecisionAction.DO_NOTHING, 0, 0, 0.8, 1_000_000),
    ]

    result = DecisionEngine().evaluate(
        _evidence(
            evidence_score=0.35,
            confidence=NumericRange(0.40, 0.95),
            available_signals=1,
            required_signals=2,
        ),
        scenarios,
    )

    assert result.policy is DecisionPolicy.ABSTAIN
    assert result.recommended_action is None
    assert result.abstained
    assert len(result.abstention_reasons) >= 3


def test_environmental_explanation_blocks_equipment_action():
    scenarios = [
        _scenario(DecisionAction.REPAIR_NOW, 100_000, 0, 0.0, 1_000_000),
        _scenario(DecisionAction.DO_NOTHING, 0, 0, 0.8, 1_000_000),
    ]

    result = DecisionEngine().evaluate(
        _evidence(environmental_explanation=0.8),
        scenarios,
    )

    assert result.policy is DecisionPolicy.ABSTAIN
    assert any("environment explains" in reason for reason in result.abstention_reasons)


def test_defer_policy_is_monitor_and_solar_actions_are_asset_specific():
    evidence = _evidence(asset_id="INV-023", asset_type="solar_inverter", component="soiling")
    scenarios = [
        _scenario(DecisionAction.DEFER_24H, 10_000, 1_000, 0.0, 100_000, 24),
        _scenario(DecisionAction.DO_NOTHING, 0, 30_000, 0.0, 100_000),
    ]
    result = DecisionEngine().evaluate(evidence, scenarios)

    assert result.policy is DecisionPolicy.MONITOR
    assert result.recommended_action is DecisionAction.DEFER_24H

    actions = {scenario.action for scenario in standard_scenarios(
        asset_type="solar_inverter",
        intervention_cost_inr=10_000,
        inspection_cost_inr=2_000,
        failure_consequence_inr=100_000,
        failure_probability=0.2,
        energy_loss_24h_inr=1_000,
        cleaning_cost_inr=3_000,
    )}
    assert {DecisionAction.CLEAN_NOW, DecisionAction.WAIT_FOR_RAIN} <= actions
    assert DecisionAction.REPAIR_NOW not in actions
