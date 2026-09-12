"""Deterministic expected-cost decision engine.

The engine evaluates each counterfactual as:

    intervention cost + energy-loss cost
    + failure probability * failure consequence

All inputs may be ranges.  Since every term is non-negative, the lower and upper expected
costs are computed by the corresponding lower and upper endpoints.  No sampling or model
inference is involved.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    CounterfactualScenario,
    DecisionAction,
    DecisionEvidence,
    DecisionPolicy,
    DecisionResult,
    NumericRange,
    ScenarioEvaluation,
)


def _expected_cost(scenario: CounterfactualScenario) -> ScenarioEvaluation:
    intervention = NumericRange.of(scenario.intervention_cost_inr)
    energy = NumericRange.of(scenario.energy_loss_inr)
    probability = NumericRange.of(scenario.failure_probability)
    consequence = NumericRange.of(scenario.failure_consequence_inr)
    failure_low = probability.low * consequence.low
    failure_high = probability.high * consequence.high
    expected = NumericRange(
        intervention.low + energy.low + failure_low,
        intervention.high + energy.high + failure_high,
    )
    return ScenarioEvaluation(
        scenario=scenario,
        expected_cost_inr=expected,
        midpoint_cost_inr=expected.midpoint,
        cost_breakdown_inr={
            "intervention_cost_inr": intervention,
            "energy_loss_inr": energy,
            "failure_risk_cost_inr": NumericRange(failure_low, failure_high),
        },
    )


def _policy_for(action: DecisionAction) -> DecisionPolicy:
    if action is DecisionAction.DO_NOTHING:
        return DecisionPolicy.DO_NOTHING
    if action in {
        DecisionAction.DEFER_24H,
        DecisionAction.DEFER_72H,
        DecisionAction.WAIT_FOR_RAIN,
    }:
        return DecisionPolicy.MONITOR
    return DecisionPolicy.ACT


@dataclass(frozen=True)
class DecisionEngine:
    """Evaluate scenarios and abstain when the evidence gate is not met."""

    minimum_evidence_score: float = 0.60
    minimum_confidence: float = 0.70
    maximum_confidence_width: float = 0.35
    maximum_environmental_explanation: float = 0.60

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_evidence_score <= 1.0:
            raise ValueError("minimum_evidence_score must be between 0 and 1")
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if self.maximum_confidence_width < 0.0:
            raise ValueError("maximum_confidence_width must be non-negative")
        if not 0.0 <= self.maximum_environmental_explanation <= 1.0:
            raise ValueError("maximum_environmental_explanation must be between 0 and 1")

    def _insufficiency_reasons(self, evidence: DecisionEvidence) -> list[str]:
        reasons: list[str] = []
        if evidence.evidence_score < self.minimum_evidence_score:
            reasons.append(
                f"evidence score {evidence.evidence_score:.2f} is below "
                f"{self.minimum_evidence_score:.2f}"
            )
        if evidence.confidence.low < self.minimum_confidence:
            reasons.append(
                f"confidence lower bound {evidence.confidence.low:.2f} is below "
                f"{self.minimum_confidence:.2f}"
            )
        if evidence.confidence.width > self.maximum_confidence_width:
            reasons.append(
                f"confidence range width {evidence.confidence.width:.2f} exceeds "
                f"{self.maximum_confidence_width:.2f}"
            )
        if evidence.available_signals < evidence.required_signals:
            reasons.append(
                f"only {evidence.available_signals} of {evidence.required_signals} "
                "required signals are available"
            )
        if evidence.persistence_hours < evidence.required_persistence_hours:
            reasons.append(
                f"persistence {evidence.persistence_hours:.1f}h is below the required "
                f"{evidence.required_persistence_hours:.1f}h"
            )
        if evidence.environmental_explanation > self.maximum_environmental_explanation:
            reasons.append(
                f"environment explains {evidence.environmental_explanation:.0%} of the "
                "deviation"
            )
        if evidence.sensor_health != "ok":
            reasons.append(f"sensor health is {evidence.sensor_health}")
        return reasons

    def evaluate(
        self,
        evidence: DecisionEvidence,
        scenarios: tuple[CounterfactualScenario, ...] | list[CounterfactualScenario],
    ) -> DecisionResult:
        """Return the cheapest counterfactual, or an explicit abstention."""
        if not scenarios:
            return DecisionResult(
                policy=DecisionPolicy.ABSTAIN,
                recommended_action=None,
                scenarios=(),
                abstention_reasons=("no counterfactual scenarios were supplied",),
                explanation="No action can be selected without at least one costed scenario.",
            )

        evaluations = tuple(
            sorted(
                (_expected_cost(scenario) for scenario in scenarios),
                key=lambda item: (item.midpoint_cost_inr, item.scenario.action.value),
            )
        )
        reasons = self._insufficiency_reasons(evidence)
        if reasons:
            return DecisionResult(
                policy=DecisionPolicy.ABSTAIN,
                recommended_action=None,
                scenarios=evaluations,
                abstention_reasons=tuple(reasons),
                explanation="Evidence is insufficient for an automatic maintenance policy.",
            )

        selected = evaluations[0].scenario.action
        selected_cost = evaluations[0].expected_cost_inr
        policy = _policy_for(selected)
        return DecisionResult(
            policy=policy,
            recommended_action=selected,
            scenarios=evaluations,
            explanation=(
                f"{selected.value} has the lowest midpoint expected cost "
                f"({selected_cost.midpoint:,.2f} INR), with a range of "
                f"{selected_cost.low:,.2f}-{selected_cost.high:,.2f} INR."
            ),
        )


def evaluate_counterfactuals(
    evidence: DecisionEvidence,
    scenarios: tuple[CounterfactualScenario, ...] | list[CounterfactualScenario],
) -> DecisionResult:
    """Convenience wrapper using the default evidence gate."""
    return DecisionEngine().evaluate(evidence, scenarios)


def standard_scenarios(
    *,
    asset_type: str,
    intervention_cost_inr: float,
    inspection_cost_inr: float,
    failure_consequence_inr: float,
    failure_probability: NumericRange | float,
    energy_loss_24h_inr: float,
    cleaning_cost_inr: float | None = None,
    rain_failure_probability: NumericRange | float = 0.0,
) -> tuple[CounterfactualScenario, ...]:
    """Build a small, asset-specific action set from explicit cost assumptions.

    Wind assets receive repair/inspection actions. Solar assets receive cleaning/rain actions.
    Deferral and do-nothing are included for both, so the policy always has a monitor and a
    no-intervention counterfactual to compare against.
    """
    common = [
        CounterfactualScenario(
            action=DecisionAction.DEFER_24H,
            delay_hours=24,
            intervention_cost_inr=intervention_cost_inr,
            energy_loss_inr=energy_loss_24h_inr,
            failure_probability=NumericRange.of(failure_probability),
            failure_consequence_inr=failure_consequence_inr,
            rationale="defer one day and monitor",
        ),
        CounterfactualScenario(
            action=DecisionAction.DEFER_72H,
            delay_hours=72,
            intervention_cost_inr=intervention_cost_inr,
            energy_loss_inr=energy_loss_24h_inr * 3.0,
            failure_probability=NumericRange.of(failure_probability),
            failure_consequence_inr=failure_consequence_inr,
            rationale="defer three days and monitor",
        ),
        CounterfactualScenario(
            action=DecisionAction.DO_NOTHING,
            delay_hours=0,
            intervention_cost_inr=0.0,
            energy_loss_inr=energy_loss_24h_inr * 30.0,
            failure_probability=NumericRange.of(failure_probability),
            failure_consequence_inr=failure_consequence_inr,
            rationale="accept the risk without an intervention",
        ),
    ]
    if asset_type.lower() in {"solar", "solar_inverter", "inverter"}:
        clean_cost = intervention_cost_inr if cleaning_cost_inr is None else cleaning_cost_inr
        common.extend(
            [
                CounterfactualScenario(
                    action=DecisionAction.CLEAN_NOW,
                    delay_hours=0,
                    intervention_cost_inr=clean_cost,
                    energy_loss_inr=0.0,
                    failure_probability=0.0,
                    failure_consequence_inr=failure_consequence_inr,
                    rationale="clean at the next available shift",
                ),
                CounterfactualScenario(
                    action=DecisionAction.WAIT_FOR_RAIN,
                    delay_hours=48,
                    intervention_cost_inr=0.0,
                    energy_loss_inr=energy_loss_24h_inr * 2.0,
                    failure_probability=rain_failure_probability,
                    failure_consequence_inr=failure_consequence_inr,
                    rationale="wait for natural washing and reassess",
                ),
            ]
        )
    else:
        common.extend(
            [
                CounterfactualScenario(
                    action=DecisionAction.REPAIR_NOW,
                    delay_hours=0,
                    intervention_cost_inr=intervention_cost_inr,
                    energy_loss_inr=0.0,
                    failure_probability=0.0,
                    failure_consequence_inr=failure_consequence_inr,
                    rationale="repair at the next available window",
                ),
                CounterfactualScenario(
                    action=DecisionAction.INSPECT_FIRST,
                    delay_hours=8,
                    intervention_cost_inr=inspection_cost_inr,
                    energy_loss_inr=energy_loss_24h_inr / 3.0,
                    failure_probability=NumericRange.of(failure_probability),
                    failure_consequence_inr=failure_consequence_inr,
                    rationale="inspect before committing to repair",
                ),
            ]
        )
    return tuple(common)
