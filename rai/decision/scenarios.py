"""Counterfactual scenario builders for wind and solar assets."""

from __future__ import annotations

from rai.decision.models import (
    CounterfactualScenario,
    DecisionAction,
    NumericRange,
)


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
