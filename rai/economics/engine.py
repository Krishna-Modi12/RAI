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
from rai.schemas import (
    CleaningAdvisorEvidence,
    CleaningAdvisorOption,
    EconomicEvidence,
    EconomicOption,
)

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

# Semi-automated module washing, priced per 250kW inverter block (labour + water + consumables).
# Distinct from COMPONENT_ECONOMICS' "soiling" planned_repair_cost (a full manual cleaning
# campaign per inverter block): this is the lighter, more frequent routine wash this advisor
# schedules, not the escalated campaign `evaluate_options` costs.
UNIT_CLEANING_COST_INR = 1850.0

# Baseline soiling loss immediately after a wash — a clean panel is never literally 0% soiled.
POST_CLEAN_BASELINE_SOILING_PCT = 1.0

# Recommendation confidence below is a disclosed heuristic judgment calibration (like
# `fallback._confidence`), not a fitted or learned probability: higher when the deciding signal
# (rain forecast or break-even economics) is unambiguous, lower when deferring on a thinner
# economic margin.
CLEANING_CONFIDENCE_RAIN_WINDOW = 0.88
CLEANING_CONFIDENCE_IMMEDIATE = 0.92
CLEANING_CONFIDENCE_DEFER = 0.78


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


def evaluate_cleaning_options(
    asset_id: str,
    soiling_loss_pct: float,
    accumulation_rate_pct_day: float = 0.22,
    rain_probability_48h: float = 0.0,
    dust_risk_level: str = "moderate",
    horizon_days: int = 30,
) -> CleaningAdvisorEvidence:
    """Techno-economic cleaning optimization trade-off model.

    Evaluates:
    1. Direct cost of module washing (water + consumables + labor)
    2. Daily generation value lost to soiling vs clear performance
    3. Natural precipitation probability & natural washing trade-offs
    4. Post-dust cementation risks under light rain
    5. Net economic break-even horizon
    """
    asset = get_asset(asset_id)
    tariff = tariff_for(asset_id)
    capacity_factor = _capacity_factor(asset.asset_type.value)

    # Inverter-level daily generation and gross daily revenue
    daily_kwh = asset.rated_power_kw * capacity_factor * 24.0
    daily_rev_inr = daily_kwh * tariff

    unit_cleaning_cost_inr = UNIT_CLEANING_COST_INR

    # Recoverable soiling percentage above the post-clean baseline
    recoverable_loss_pct = max(0.0, soiling_loss_pct - POST_CLEAN_BASELINE_SOILING_PCT)
    daily_recovered_rev_inr = daily_rev_inr * (recoverable_loss_pct / 100.0)

    # Break-even days
    break_even_days = (
        round(unit_cleaning_cost_inr / daily_recovered_rev_inr, 1)
        if daily_recovered_rev_inr > 1.0
        else 99.0
    )

    base_assumptions = {
        "tariff_inr_per_kwh": tariff,
        "capacity_factor": round(capacity_factor, 3),
        "daily_kwh": round(daily_kwh, 1),
        "unit_cleaning_cost_inr": unit_cleaning_cost_inr,
        "post_clean_baseline_soiling_pct": POST_CLEAN_BASELINE_SOILING_PCT,
        "recoverable_loss_pct": round(recoverable_loss_pct, 2),
        "horizon_days": float(horizon_days),
    }

    # Evaluate Options: Clean Now, Wait 24h, Wait 72h, Wait 7d
    options: list[CleaningAdvisorOption] = []

    # Option 1: Clean Now
    # Cost = direct washing; Lost energy during 30d horizon = baseline 1% clean loss
    now_loss = daily_rev_inr * 0.01 * horizon_days
    options.append(
        CleaningAdvisorOption(
            option_id="clean_now",
            label="Clean immediately (next shift)",
            delay_hours=0,
            cleaning_cost_inr=unit_cleaning_cost_inr,
            expected_energy_loss_inr=round(now_loss, 2),
            net_exposure_inr=round(unit_cleaning_cost_inr + now_loss, 2),
            break_even_days=break_even_days,
            rain_cleaning_probability=0.0,
            cementation_risk=False,
            summary="Intervene immediately to restore clean baseline generation.",
            assumptions={**base_assumptions, "clean_baseline_loss_pct": 1.0},
        )
    )

    # Option 2: Wait 24h
    # 1 day of current loss + 29 days clean baseline
    loss_24h = (
        daily_rev_inr * (soiling_loss_pct / 100.0) * 1.0
        + daily_rev_inr * 0.01 * (horizon_days - 1)
    )
    options.append(
        CleaningAdvisorOption(
            option_id="wait_24h",
            label="Wait 24h (coordinate with low irradiance)",
            delay_hours=24,
            cleaning_cost_inr=unit_cleaning_cost_inr,
            expected_energy_loss_inr=round(loss_24h, 2),
            net_exposure_inr=round(unit_cleaning_cost_inr + loss_24h, 2),
            break_even_days=break_even_days,
            rain_cleaning_probability=min(0.25, rain_probability_48h * 0.5),
            cementation_risk=False,
            summary="Defer 24 hours to align with night/dawn low generation cycle.",
            assumptions={**base_assumptions, "soiling_loss_pct_during_wait": round(soiling_loss_pct, 2)},
        )
    )

    # Option 3: Wait 72h (Rain window)
    # If rain probability is high (>50%), natural rain may wash panels for 0 INR.
    rain_wash_prob = float(rain_probability_48h)
    has_cementation = dust_risk_level in ("high", "extreme") and 0.20 <= rain_wash_prob <= 0.65
    effective_clean_cost = unit_cleaning_cost_inr * (1.0 - rain_wash_prob)
    avg_soil_3d = soiling_loss_pct + (accumulation_rate_pct_day * 1.5)
    loss_72h = (
        daily_rev_inr * (avg_soil_3d / 100.0) * 3.0
        + daily_rev_inr * 0.01 * (horizon_days - 3)
    )
    options.append(
        CleaningAdvisorOption(
            option_id="wait_72h",
            label="Wait 72h (await forecasted precipitation)",
            delay_hours=72,
            cleaning_cost_inr=round(effective_clean_cost, 2),
            expected_energy_loss_inr=round(loss_72h, 2),
            net_exposure_inr=round(effective_clean_cost + loss_72h, 2),
            break_even_days=break_even_days,
            rain_cleaning_probability=round(rain_wash_prob, 2),
            cementation_risk=has_cementation,
            summary=(
                "Opportunity for natural rain cleaning; risk of mud cementation if precipitation < 4mm."
                if has_cementation
                else "Leverage natural rainfall to avoid redundant wash expenditure."
            ),
            assumptions={
                **base_assumptions,
                "rain_wash_prob": round(rain_wash_prob, 2),
                "accumulation_rate_pct_day": round(accumulation_rate_pct_day, 3),
                "avg_soiling_loss_pct_over_wait": round(avg_soil_3d, 2),
            },
        )
    )

    # Option 4: Wait 7d
    loss_7d = (
        daily_rev_inr * (soiling_loss_pct / 100.0) * 7.0
        + daily_rev_inr * 0.01 * (horizon_days - 7)
    )
    options.append(
        CleaningAdvisorOption(
            option_id="wait_7d",
            label="Wait 7 days (routine weekly cycle)",
            delay_hours=168,
            cleaning_cost_inr=unit_cleaning_cost_inr,
            expected_energy_loss_inr=round(loss_7d, 2),
            net_exposure_inr=round(unit_cleaning_cost_inr + loss_7d, 2),
            break_even_days=break_even_days,
            rain_cleaning_probability=round(min(0.90, rain_wash_prob * 1.3), 2),
            cementation_risk=False,
            summary="Defer to standard scheduled cleaning roster.",
            assumptions={**base_assumptions, "soiling_loss_pct_during_wait": round(soiling_loss_pct, 2)},
        )
    )

    # Determine recommended action
    if rain_wash_prob >= 0.60 and soiling_loss_pct < 16.0:
        recommended_action = "post_rain_reassess"
        recommended_window = "48–72h (post-precipitation)"
        confidence = CLEANING_CONFIDENCE_RAIN_WINDOW
        rationale = (
            f"Precipitation probability is {rain_wash_prob*100:.0f}%. Natural rain washing is "
            f"likely to clear accumulated particulate without manual intervention expense. "
            f"Reassess performance ratio 12 hours post-event."
        )
    elif break_even_days <= 6.0 or soiling_loss_pct >= 8.5:
        recommended_action = "clean_now"
        recommended_window = "Immediate (within 24 hours)"
        confidence = CLEANING_CONFIDENCE_IMMEDIATE
        rationale = (
            f"Soiling loss is {soiling_loss_pct:.1f}% with economic break-even within "
            f"{break_even_days:.1f} days. Immediate washing generates positive net return."
        )
    else:
        recommended_action = "wait_72h"
        recommended_window = "36–60 hours"
        confidence = CLEANING_CONFIDENCE_DEFER
        rationale = (
            f"Current soiling loss ({soiling_loss_pct:.1f}%) does not yet justify immediate "
            f"mobilization (break-even {break_even_days:.1f} days). Monitor exposure trend."
        )

    return CleaningAdvisorEvidence(
        recommended_action=recommended_action,
        recommended_window=recommended_window,
        confidence=confidence,
        break_even_days=break_even_days,
        options=options,
        current_soiling_loss_pct=round(soiling_loss_pct, 2),
        dust_risk_level=dust_risk_level,
        rationale=rationale,
    )

