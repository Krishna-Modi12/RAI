"""Transparent economic decision support over the existing Python cost engine.

This module does not estimate failure probability or invent market inputs. It consumes
computed risk and explicitly named configuration assumptions, then returns a decision
with the consequence components and provenance of every input.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from rai.config import COMPONENT_ECONOMICS, economics_for, get_asset, tariff_for
from rai.economics.engine import DEFAULT_CAPACITY_FACTOR, evaluate_options


class EconomicDecision(str, Enum):
    INTERVENE = "INTERVENE"
    INSPECT = "INSPECT"
    MONITOR = "MONITOR"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class InputState(str, Enum):
    OBSERVED = "OBSERVED"
    ASSUMED = "ASSUMED"
    RETRIEVED = "RETRIEVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EconomicInput:
    name: str
    value: float | str | None
    state: InputState
    source: str
    limitation: str | None = None


@dataclass(frozen=True)
class EconomicDecisionResult:
    decision: EconomicDecision
    status: str
    asset_id: str
    component: str | None
    why: str
    assumptions: tuple[EconomicInput, ...]
    uncertainty: tuple[str, ...]
    alternatives: tuple[str, ...]
    energy_loss_inr: float | None
    downtime_cost_inr: float | None
    intervention_cost_inr: float | None
    inspection_cost_inr: float | None
    expected_waiting_consequence_inr: float | None
    information_value_inr: float | None
    recommended_option_id: str | None
    robustness: str
    options: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["decision"] = self.decision.value
        output["assumptions"] = [asdict(item) | {"state": item.state.value} for item in self.assumptions]
        output["uncertainty"] = list(self.uncertainty)
        output["alternatives"] = list(self.alternatives)
        output["options"] = list(self.options)
        return output


def _unknown(
    asset_id: str,
    component: str | None,
    missing: list[str],
    assumptions: tuple[EconomicInput, ...],
) -> EconomicDecisionResult:
    return EconomicDecisionResult(
        decision=EconomicDecision.ABSTAIN,
        status="ECONOMIC_CONSEQUENCE_NOT_ESTIMABLE",
        asset_id=asset_id,
        component=component,
        why=f"Required inputs are unavailable: {', '.join(missing)}.",
        assumptions=assumptions,
        uncertainty=tuple(f"{name} is unknown" for name in missing),
        alternatives=("Collect the missing inputs before ranking intervention options.",),
        energy_loss_inr=None,
        downtime_cost_inr=None,
        intervention_cost_inr=None,
        inspection_cost_inr=None,
        expected_waiting_consequence_inr=None,
        information_value_inr=None,
        recommended_option_id=None,
        robustness="NOT_ESTIMABLE",
    )


def evaluate_decision_support(
    *,
    asset_id: str,
    component: str | None,
    risk_score: float | None,
    risk_calibration: str | None,
    risk_window_days: tuple[int, int] | None,
    environmental_explanation: float | None = None,
    sensor_health: str = "ok",
    confidence_width: float | None = None,
) -> EconomicDecisionResult:
    """Evaluate intervention priority without converting unknowns into zero.

    `risk_score` is retained as an inferred model input, never described as a measured
    failure probability. VOI is intentionally not calculated because inspection
    sensitivity/specificity are not currently established for this fleet.
    """
    asset = get_asset(asset_id)
    selected_component = component or ("generator" if asset.asset_type.value == "wind_turbine" else "inverter")
    assumptions: list[EconomicInput] = [
        EconomicInput("component", selected_component, InputState.ASSUMED, "component mapping"),
        EconomicInput("tariff_inr_per_kwh", tariff_for(asset_id), InputState.ASSUMED, "rai.config.settings"),
    ]
    if risk_score is not None:
        assumptions.append(
            EconomicInput(
                "risk_score",
                round(float(risk_score), 4),
                InputState.INFERRED,
                "rai.models.risk",
                "Risk score is not a calibrated failure probability.",
            )
        )
    else:
        assumptions.append(EconomicInput("risk_score", None, InputState.UNKNOWN, "rai.models.risk"))
    if risk_calibration:
        assumptions.append(EconomicInput("risk_calibration", risk_calibration, InputState.INFERRED, "rai.models.risk"))
    else:
        assumptions.append(EconomicInput("risk_calibration", None, InputState.UNKNOWN, "rai.models.risk"))

    missing: list[str] = []
    if risk_score is None:
        missing.append("risk score")
    if not risk_calibration:
        missing.append("risk calibration")
    if selected_component not in COMPONENT_ECONOMICS:
        missing.append("component cost basis")
    if missing:
        return _unknown(asset_id, selected_component, missing, tuple(assumptions))
    if not 0.0 <= risk_score <= 1.0:
        return _unknown(asset_id, selected_component, ["risk score range"], tuple(assumptions))
    if sensor_health != "ok":
        return _unknown(
            asset_id,
            selected_component,
            ["sensor health"],
            tuple(assumptions)
            + (
                EconomicInput(
                    "sensor_health",
                    sensor_health,
                    InputState.OBSERVED,
                    "rai.models.environment",
                    "Economic attribution is unsafe with suspect or failed sensors.",
                ),
            ),
        )

    evidence = evaluate_options(
        asset_id=asset_id,
        component=selected_component,
        failure_probability=float(risk_score),
        risk_window_days=risk_window_days,
    )
    basis = economics_for(selected_component)
    planned_downtime = basis["planned_downtime_hours"] * (
        get_asset(asset_id).rated_power_kw
        * DEFAULT_CAPACITY_FACTOR[asset.asset_type.value]
        * tariff_for(asset_id)
    )
    intervention_cost = basis["inspection_cost"] + basis["planned_repair_cost"]
    top = evidence.options[0] if evidence.options else None
    wait = next((option for option in evidence.options if option.delay_days == 14), top)
    environmental_explanation = environmental_explanation or 0.0
    uncertainty: list[str] = [
        "Risk score is an inferred model output, not an independently observed failure probability.",
        "Tariff, capacity factor, downtime, and component costs are assumptions from configuration.",
    ]
    if confidence_width is None:
        uncertainty.append("Decision robustness was not sensitivity-tested because no uncertainty range was supplied.")
    if environmental_explanation > 0.0:
        assumptions.append(
            EconomicInput(
                "environmental_explanation",
                round(environmental_explanation, 3),
                InputState.OBSERVED,
                "rai.models.environment",
            )
        )

    if environmental_explanation >= 0.60:
        decision = EconomicDecision.INSPECT
        why = "Environmental evidence explains a substantial share of the deviation; inspect before committing to repair."
    elif confidence_width is not None and confidence_width > 0.35:
        decision = EconomicDecision.INSPECT
        why = "The economic action is sensitive to unresolved risk uncertainty; inspection is the preferred information-gathering action."
    elif risk_score < 0.10:
        decision = EconomicDecision.WAIT
        why = "The inferred risk is low; wait for the planned review window rather than mobilizing intervention."
    elif risk_score < 0.50:
        decision = EconomicDecision.MONITOR
        why = "Evidence supports active monitoring, but the inferred risk does not justify immediate intervention."
    elif evidence.recommended_option_id == "repair_now":
        decision = EconomicDecision.INTERVENE
        why = "The next-window intervention has the lowest computed expected exposure under the stated assumptions."
    else:
        decision = EconomicDecision.WAIT
        why = "Available evidence does not justify immediate intervention; reassess at the planned review window."

    options = tuple(option.model_dump(mode="json") for option in evidence.options)
    return EconomicDecisionResult(
        decision=decision,
        status="ESTIMATED_UNDER_EXPLICIT_ASSUMPTIONS",
        asset_id=asset_id,
        component=selected_component,
        why=why,
        assumptions=tuple(assumptions)
        + (
            EconomicInput("planned_downtime_hours", basis["planned_downtime_hours"], InputState.ASSUMED, "rai.config.COMPONENT_ECONOMICS"),
            EconomicInput("inspection_cost_inr", basis["inspection_cost"], InputState.ASSUMED, "rai.config.COMPONENT_ECONOMICS"),
            EconomicInput("planned_repair_cost_inr", basis["planned_repair_cost"], InputState.ASSUMED, "rai.config.COMPONENT_ECONOMICS"),
        ),
        uncertainty=tuple(uncertainty),
        alternatives=("Monitor and reassess before the next maintenance window.", "Inspect first if attribution remains unresolved."),
        energy_loss_inr=top.energy_loss_inr if top else None,
        downtime_cost_inr=round(planned_downtime, 2),
        intervention_cost_inr=round(intervention_cost, 2),
        inspection_cost_inr=round(basis["inspection_cost"], 2),
        expected_waiting_consequence_inr=wait.expected_exposure_inr if wait else None,
        information_value_inr=None,
        recommended_option_id=evidence.recommended_option_id,
        robustness="NOT_EVALUATED" if confidence_width is None else "SENSITIVITY_REQUIRED",
        options=options,
    )
