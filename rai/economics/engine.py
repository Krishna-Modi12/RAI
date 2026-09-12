"""The economic decision engine.

Every rupee in this system is computed here. The language model is given the finished options
and their totals and is asked to choose and justify — it never multiplies a cost by a
probability, because a 45M-parameter model doing arithmetic in a 256-token window is a
liability, not a feature.

The model being evaluated is a simple one, stated explicitly so a reviewer can disagree with
it precisely:

    exposure(delay) = intervention_cost
                    + energy_loss_during_downtime
                    + P(failure before the intervention) x escalation_cost

where `escalation_cost` is what the failure costs *beyond* the planned repair — the difference
between an unplanned failure and a planned one, including the secondary damage multiplier and
the much longer unplanned outage. Deferring does not change the repair cost; it changes the
probability that you no longer get to choose when to do the repair.

**Failure probability grows with the delay.** A hazard that is flat in time would make
deferral free, which is both wrong and the single easiest way to build a maintenance optimiser
that always says "wait". The hazard here is taken as constant over the risk window, so the
survival function is exponential and the probability of failing within `d` days is
`1 - exp(-lambda d)` with `lambda` calibrated so the risk model's probability is reproduced at
the centre of its own risk window. That calibration is the honest part: the engine does not
invent a hazard rate, it inherits the one the risk model already committed to.
"""

from __future__ import annotations

import logging
import math

from rai.config import (
    COMPONENT_ECONOMICS,
    economics_for,
    get_asset,
    settings,
    tariff_for,
)
from rai.schemas import EconomicEvidence, EconomicOption

log = logging.getLogger(__name__)

# The three choices an operations planner actually has. Deliberately not a continuous
# optimisation: a planner schedules against a crane window and a crew roster, not a real number.
OPTIONS: list[tuple[str, str, int]] = [
    ("repair_now", "Intervene at the next available window", 0),
    ("defer_3d", "Defer 3 days, monitor daily", 3),
    ("defer_14d", "Defer 14 days to the next planned outage", 14),
]

# Capacity factor used to value lost energy. Measured from the simulated fleet rather than
# assumed: see `artifacts/evaluation.json`. Falls back to these figures when unavailable.
DEFAULT_CAPACITY_FACTOR = {"wind_turbine": 0.32, "solar_inverter": 0.21}

# A deferral is only free if nothing degrades while you wait. Partial output loss during the
# deferral is the cost of running a known-degraded machine.
DEGRADED_OUTPUT_LOSS_FRAC = 0.03


def _capacity_factor(asset_type: str) -> float:
    return DEFAULT_CAPACITY_FACTOR.get(asset_type, 0.25)


def _hazard_rate(failure_probability: float, risk_window_days: tuple[int, int] | None) -> float:
    """Constant hazard reproducing the risk model's probability at the centre of its window.

    Returns lambda in units of 1/day. A zero or near-certain probability is clamped: an
    infinite hazard would make every option identical at the ceiling, which hides the decision
    rather than informing it.
    """
    if risk_window_days is not None and len(risk_window_days) == 2:
        centre = (float(risk_window_days[0]) + float(risk_window_days[1])) / 2.0
    else:
        centre = 30.0
    centre = max(centre, 1.0)

    p = min(max(float(failure_probability), 1e-4), 0.98)
    # p = 1 - exp(-lambda * centre)  =>  lambda = -ln(1 - p) / centre
    return -math.log(1.0 - p) / centre


def _failure_probability_within(days: float, hazard: float) -> float:
    return 1.0 - math.exp(-hazard * max(days, 0.0))


def evaluate_options(
    asset_id: str,
    component: str,
    failure_probability: float,
    risk_window_days: tuple[int, int] | None = None,
) -> EconomicEvidence:
    """Cost every intervention option for one asset and recommend the cheapest exposure.

    `failure_probability` is the calibrated risk score from `rai.models.risk`. If the risk
    model is running uncalibrated, that fact is already recorded on the `RiskAssessment` and
    travels with the packet — this engine costs whatever probability it is handed and does not
    second-guess it.
    """
    asset = get_asset(asset_id)
    econ = economics_for(component)
    tariff = tariff_for(asset_id)
    capacity_factor = _capacity_factor(asset.asset_type.value)

    hazard = _hazard_rate(failure_probability, risk_window_days)

    # Energy value per hour of full outage, and per day of running degraded.
    energy_kwh_per_outage_hour = asset.rated_power_kw * capacity_factor
    value_per_outage_hour = energy_kwh_per_outage_hour * tariff
    value_per_degraded_day = (
        asset.rated_power_kw * capacity_factor * 24.0 * DEGRADED_OUTPUT_LOSS_FRAC * tariff
    )

    planned_downtime_cost = econ["planned_downtime_hours"] * value_per_outage_hour
    unplanned_downtime_cost = econ["unplanned_downtime_hours"] * value_per_outage_hour

    # What the failure costs *over and above* doing the same job on your own schedule.
    escalation_cost = (
        econ["unplanned_failure_cost"] * econ["secondary_damage_multiplier"]
        + unplanned_downtime_cost
    ) - (econ["planned_repair_cost"] + planned_downtime_cost)
    escalation_cost = max(escalation_cost, 0.0)

    options: list[EconomicOption] = []
    for option_id, label, delay_days in OPTIONS:
        p_fail = _failure_probability_within(delay_days, hazard)

        # Inspection is only bought once, at the point of intervention.
        intervention_cost = econ["inspection_cost"] + econ["planned_repair_cost"]
        energy_loss = planned_downtime_cost + value_per_degraded_day * delay_days
        escalation = p_fail * escalation_cost

        options.append(
            EconomicOption(
                option_id=option_id,
                label=label,
                delay_days=delay_days,
                intervention_cost_inr=round(intervention_cost, 2),
                energy_loss_inr=round(energy_loss, 2),
                failure_escalation_inr=round(escalation, 2),
                expected_exposure_inr=round(intervention_cost + energy_loss + escalation, 2),
                failure_probability=round(p_fail, 4),
                assumptions={
                    "tariff_inr_per_kwh": tariff,
                    "capacity_factor": round(capacity_factor, 3),
                    "hazard_per_day": round(hazard, 5),
                    "planned_downtime_hours": econ["planned_downtime_hours"],
                    "unplanned_downtime_hours": econ["unplanned_downtime_hours"],
                    "escalation_cost_inr": round(escalation_cost, 2),
                    "degraded_output_loss_frac": DEGRADED_OUTPUT_LOSS_FRAC,
                },
            )
        )

    best = min(options, key=lambda o: o.expected_exposure_inr)
    worst = max(options, key=lambda o: o.expected_exposure_inr)

    return EconomicEvidence(
        options=options,
        recommended_option_id=best.option_id,
        avoidable_exposure_inr=round(worst.expected_exposure_inr - best.expected_exposure_inr, 2),
        tariff_inr_per_kwh=tariff,
    )


def do_nothing_exposure(
    asset_id: str,
    component: str,
    failure_probability: float,
    horizon_days: int = 30,
) -> float:
    """Exposure if no intervention happens at all within the horizon.

    Used by the fleet view to state what the recommendation is worth against inaction, which is
    the comparison an operator actually cares about. Kept separate from `evaluate_options`
    because "do nothing" is not a maintenance option a planner can schedule.
    """
    asset = get_asset(asset_id)
    econ = economics_for(component)
    tariff = tariff_for(asset_id)
    capacity_factor = _capacity_factor(asset.asset_type.value)

    hazard = _hazard_rate(failure_probability, None)
    p_fail = _failure_probability_within(horizon_days, hazard)

    unplanned_downtime_cost = (
        econ["unplanned_downtime_hours"] * asset.rated_power_kw * capacity_factor * tariff
    )
    failure_cost = econ["unplanned_failure_cost"] * econ["secondary_damage_multiplier"]
    degraded = (
        asset.rated_power_kw
        * capacity_factor
        * 24.0
        * DEGRADED_OUTPUT_LOSS_FRAC
        * tariff
        * horizon_days
    )
    return round(p_fail * (failure_cost + unplanned_downtime_cost) + degraded, 2)


def component_cost_table() -> list[dict[str, float | str]]:
    """The full cost basis, for the UI's assumptions panel and for `docs/`.

    Publishing the basis is not decoration. A cost model whose inputs are hidden cannot be
    argued with, and a maintenance recommendation nobody can argue with does not get followed.
    """
    rows: list[dict[str, float | str]] = []
    for component, values in COMPONENT_ECONOMICS.items():
        rows.append({"component": component, **{k: float(v) for k, v in values.items()}})
    return rows


def settings_snapshot() -> dict[str, float]:
    """Economic constants in force, so a reported figure can be reproduced later."""
    return {
        "wind_tariff_inr_per_kwh": settings.tariff_wind_inr_per_kwh,
        "solar_tariff_inr_per_kwh": settings.tariff_solar_inr_per_kwh,
        "degraded_output_loss_frac": DEGRADED_OUTPUT_LOSS_FRAC,
        "wind_capacity_factor": DEFAULT_CAPACITY_FACTOR["wind_turbine"],
        "solar_capacity_factor": DEFAULT_CAPACITY_FACTOR["solar_inverter"],
    }
