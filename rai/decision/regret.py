"""Decision regret calculation and operational summary metrics.

Defines:
Regret = Cost(chosen_policy) - Cost(ex-post_optimal_policy)

Allows direct evaluation of the decision-intelligence layer in currency units (INR),
distinguishing trivial errors (₹200) from catastrophic misallocations (₹2,00,000).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from rai.decision.models import (
    DecisionRegretResult,
    DecisionRegretSummary,
    ScenarioEvaluation,
)

log = logging.getLogger(__name__)


def compute_scenario_regret(
    chosen: ScenarioEvaluation,
    optimal: ScenarioEvaluation,
    scenario_name: str = "operational_evaluation",
) -> DecisionRegretResult:
    """Compute decision regret for an individual scenario."""
    chosen_cost = chosen.midpoint_cost_inr
    optimal_cost = optimal.midpoint_cost_inr
    regret = max(0.0, chosen_cost - optimal_cost)
    is_opt = (chosen.scenario.action == optimal.scenario.action) or (regret <= 1.0)

    return DecisionRegretResult(
        scenario_name=scenario_name,
        chosen_action=chosen.scenario.action.value if hasattr(chosen.scenario.action, "value") else str(chosen.scenario.action),
        optimal_action=optimal.scenario.action.value if hasattr(optimal.scenario.action, "value") else str(optimal.scenario.action),
        chosen_cost_inr=round(chosen_cost, 2),
        optimal_cost_inr=round(optimal_cost, 2),
        regret_inr=round(regret, 2),
        is_optimal=is_opt,
    )


def summarize_decision_regret(
    results: Sequence[DecisionRegretResult],
) -> DecisionRegretSummary:
    """Compute mean, median, p95, and max regret across a battery of operational decisions."""
    if not results:
        return DecisionRegretSummary(
            mean_regret_inr=0.0,
            median_regret_inr=0.0,
            p95_regret_inr=0.0,
            max_regret_inr=0.0,
            scenario_count=0,
            optimal_decision_pct=1.0,
        )

    regrets = [r.regret_inr for r in results]
    optimal_count = sum(1 for r in results if r.is_optimal)

    return DecisionRegretSummary(
        mean_regret_inr=round(float(np.mean(regrets)), 2),
        median_regret_inr=round(float(np.median(regrets)), 2),
        p95_regret_inr=round(float(np.percentile(regrets, 95)), 2),
        max_regret_inr=round(float(np.max(regrets)), 2),
        scenario_count=len(results),
        optimal_decision_pct=round(optimal_count / len(results), 3),
    )


def simulate_stochastic_decision_regret(
    chosen_action: str,
    has_real_defect: bool,
    planned_repair_cost_inr: float,
    unplanned_failure_cost_inr: float,
    inspection_cost_inr: float,
    energy_loss_24h_inr: float,
    simulated_hours_to_failure: float | None = None,
    seed: int = 20260912,
) -> DecisionRegretResult:
    """Evaluate decision quality against nature's realized stochastic outcome.

    Breaks the circularity of evaluating a decision engine against its own internal cost model.
    Simulates whether deferral succeeded or led to catastrophic breakdown based on realized
    failure arrival times.
    """
    rng = np.random.default_rng(seed)

    # Nature's true time to functional failure if defective
    if simulated_hours_to_failure is not None:
        t_fail = simulated_hours_to_failure
    elif has_real_defect:
        # Weibull random failure time: median ~72h, min ~12h, max ~300h
        t_fail = float(rng.weibull(1.8) * 72.0)
    else:
        t_fail = float("inf")

    # Realized ex-post cost for each operational action:
    possible_actions = ["repair_now", "defer_24h", "defer_72h", "inspect_first", "monitor", "do_nothing"]
    realized_costs: dict[str, float] = {}

    for action in possible_actions:
        if action == "repair_now":
            # Fixes defect immediately; incurs planned repair cost
            realized_costs[action] = planned_repair_cost_inr if has_real_defect else (planned_repair_cost_inr * 0.3)
        elif action == "defer_24h":
            if has_real_defect and t_fail < 24.0:
                # Catastrophic breakdown occurred during deferral!
                realized_costs[action] = unplanned_failure_cost_inr + (energy_loss_24h_inr * 3.0)
            elif has_real_defect:
                # Survived deferral window; planned repair executed
                realized_costs[action] = planned_repair_cost_inr + (energy_loss_24h_inr * 0.8)
            else:
                realized_costs[action] = 0.0
        elif action == "defer_72h":
            if has_real_defect and t_fail < 72.0:
                # Catastrophic breakdown
                realized_costs[action] = unplanned_failure_cost_inr + (energy_loss_24h_inr * 5.0)
            elif has_real_defect:
                realized_costs[action] = (planned_repair_cost_inr * 0.90) + (energy_loss_24h_inr * 1.5)
            else:
                realized_costs[action] = 0.0
        elif action == "inspect_first":
            if has_real_defect:
                # Inspection accurately reveals defect; planned repair scheduled before failure
                realized_costs[action] = inspection_cost_inr + planned_repair_cost_inr
            else:
                # Inspection proves healthy; spares repair cost
                realized_costs[action] = inspection_cost_inr
        elif action in ("monitor", "do_nothing"):
            if has_real_defect:
                # Asset left unaddressed; suffers full unplanned failure
                realized_costs[action] = unplanned_failure_cost_inr + (energy_loss_24h_inr * 7.0)
            else:
                realized_costs[action] = 0.0

    norm_chosen = chosen_action.lower().replace("-", "_").replace(" ", "_")
    # Match action if variant name used
    matched_chosen = next((a for a in possible_actions if a in norm_chosen), "repair_now")

    chosen_cost = realized_costs[matched_chosen]
    best_action = min(realized_costs, key=lambda a: realized_costs[a])
    optimal_cost = realized_costs[best_action]

    regret = max(0.0, chosen_cost - optimal_cost)
    is_optimal = (matched_chosen == best_action) or (regret <= (planned_repair_cost_inr * 0.05))

    return DecisionRegretResult(
        scenario_name=f"model_world_realization_{'fault' if has_real_defect else 'healthy'}",
        chosen_action=matched_chosen,
        optimal_action=best_action,
        chosen_cost_inr=round(chosen_cost, 2),
        optimal_cost_inr=round(optimal_cost, 2),
        regret_inr=round(regret, 2),
        is_optimal=is_optimal,
    )


# Alias for backwards compatibility
simulate_model_world_regret = simulate_stochastic_decision_regret


@dataclass(frozen=True)
class IndependentOutcomeEpisode:
    """Detailed record of a single decision episode in the independent outcome world."""

    episode_id: int
    predicted_state: str
    selected_action: str
    realized_failure_time_h: float
    realized_repair_time_h: float
    realized_production_loss_inr: float
    realized_maintenance_cost_inr: float
    total_realized_cost_inr: float
    ex_post_optimal_action: str
    ex_post_optimal_cost_inr: float
    regret_inr: float
    is_optimal: bool


def simulate_independent_outcome_world_regret(
    n_episodes: int = 100,
    seed: int = 20260912,
    failure_arrival_scale: float = 1.0,
    repair_effectiveness: float = 0.88,
    downtime_variance: float = 1.25,
    economic_shock_mult: float = 1.0,
) -> dict[str, Any]:
    """Evaluate decision quality against an independent, perturbed outcome world.

    Crucially decouples the decision ranking logic from the realization world:
    - Independent stochastic Weibull failure times with perturbed scale
    - Imperfect repair effectiveness (requiring rework when maintenance is imperfect)
    - Stochastic downtime variance and variable lost production costs
    - Imperfect inspection accuracy (10% false negatives in sensing/inspection)

    This breaks circular self-consistency and allows the decision policy to fail,
    measuring true operational risk and non-zero regret.
    """
    rng = np.random.default_rng(seed)
    episodes: list[IndependentOutcomeEpisode] = []

    for i in range(n_episodes):
        # 1. State generation: 40% real fault, 40% healthy, 10% ambiguous, 10% sensor failure
        state_roll = rng.uniform(0.0, 1.0)
        if state_roll < 0.40:
            pred_state = "high_risk_fault"
            has_defect = True
            perceived_risk = rng.uniform(0.70, 0.95)
            sensor_healthy = True
        elif state_roll < 0.75:
            pred_state = "healthy_normal"
            has_defect = False
            perceived_risk = rng.uniform(0.01, 0.15)
            sensor_healthy = True
        elif state_roll < 0.90:
            pred_state = "ambiguous_incubation"
            has_defect = rng.choice([True, False], p=[0.6, 0.4])
            perceived_risk = rng.uniform(0.35, 0.65)
            sensor_healthy = True
        else:
            pred_state = "sensor_malfunction"
            has_defect = False
            perceived_risk = rng.uniform(0.80, 0.99)
            sensor_healthy = False

        # Base economic costs in INR
        base_repair = 85_000.0 * economic_shock_mult
        base_catastrophic = 350_000.0 * economic_shock_mult
        base_inspect = 12_000.0
        hourly_energy_loss = (18_000.0 / 24.0) * economic_shock_mult

        # Nature's independent outcome parameters (decoupled from policy assumptions)
        if has_defect:
            # Independent Weibull: scale perturbed by failure_arrival_scale
            # Shape=1.5 has heavier tail than policy's assumed 1.8
            t_fail = float(rng.weibull(1.4) * (60.0 * failure_arrival_scale))
        else:
            t_fail = float("inf")

        # Realized repair duration in hours (lognormally distributed)
        realized_repair_hours = float(np.exp(rng.normal(np.log(8.0 * downtime_variance), 0.30)))
        # Repair execution success
        repair_succeeded = bool(rng.uniform(0.0, 1.0) <= repair_effectiveness)
        rework_penalty = 0.50 * base_repair if not repair_succeeded else 0.0
        rework_downtime = 12.0 if not repair_succeeded else 0.0

        # Inspection accuracy (10% false negative rate)
        inspection_accurate = bool(rng.uniform(0.0, 1.0) <= 0.90)

        # 2. Ex-post realized costs for all actions:
        realized_costs: dict[str, tuple[float, float, float]] = {}  # action -> (total, maint, prod_loss)

        # Action: repair_now
        maint = base_repair + rework_penalty
        prod = (realized_repair_hours + rework_downtime) * hourly_energy_loss
        realized_costs["repair_now"] = (maint + prod, maint, prod)

        # Action: inspect_first
        if has_defect:
            if inspection_accurate:
                # Discovered: repaired safely
                maint_insp = base_inspect + base_repair + rework_penalty
                prod_insp = (3.0 + realized_repair_hours + rework_downtime) * hourly_energy_loss
            else:
                # Missed: deferred to catastrophic failure
                maint_insp = base_inspect + base_catastrophic
                prod_insp = (72.0 * hourly_energy_loss)
        else:
            # Inspection verifies asset is healthy; saves repair
            maint_insp = base_inspect
            prod_insp = 3.0 * hourly_energy_loss
        realized_costs["inspect_first"] = (maint_insp + prod_insp, maint_insp, prod_insp)

        # Action: defer_24h
        if has_defect and t_fail < 24.0:
            maint_d24 = base_catastrophic
            prod_d24 = 72.0 * hourly_energy_loss
        elif has_defect:
            maint_d24 = base_repair + rework_penalty
            prod_d24 = (24.0 + realized_repair_hours + rework_downtime) * hourly_energy_loss
        else:
            maint_d24 = 0.0
            prod_d24 = 0.0
        realized_costs["defer_24h"] = (maint_d24 + prod_d24, maint_d24, prod_d24)

        # Action: defer_72h
        if has_defect and t_fail < 72.0:
            maint_d72 = base_catastrophic
            prod_d72 = 120.0 * hourly_energy_loss
        elif has_defect:
            maint_d72 = base_repair + rework_penalty
            prod_d72 = (72.0 + realized_repair_hours + rework_downtime) * hourly_energy_loss
        else:
            maint_d72 = 0.0
            prod_d72 = 0.0
        realized_costs["defer_72h"] = (maint_d72 + prod_d72, maint_d72, prod_d72)

        # Action: monitor
        if has_defect:
            maint_mon = base_catastrophic
            prod_mon = 168.0 * hourly_energy_loss
        else:
            maint_mon = 0.0
            prod_mon = 0.0
        realized_costs["monitor"] = (maint_mon + prod_mon, maint_mon, prod_mon)

        # Action: abstain (triggers manual investigation / conservative standby)
        if has_defect:
            # Defect remains unaddressed; leads to catastrophic failure
            maint_abs = 15_000.0 + base_catastrophic
            prod_abs = 96.0 * hourly_energy_loss
        else:
            maint_abs = 15_000.0
            prod_abs = 6.0 * hourly_energy_loss
        realized_costs["abstain"] = (maint_abs + prod_abs, maint_abs, prod_abs)

        # Ex-post optimal action and cost (prefer monitor on tie for zero-cost healthy assets)
        sorted_action_preference = ["monitor", "defer_24h", "defer_72h", "inspect_first", "repair_now", "abstain"]
        best_act = min(sorted_action_preference, key=lambda a: realized_costs[a][0])
        best_cost = realized_costs[best_act][0]

        # 3. Policy selects action based only on state at decision time t:
        if not sensor_healthy:
            selected_action = "abstain"
        elif perceived_risk >= 0.75:
            selected_action = "repair_now"
        elif perceived_risk >= 0.35:
            selected_action = "inspect_first"
        elif perceived_risk >= 0.15:
            selected_action = "defer_24h"
        else:
            selected_action = "monitor"

        chosen_total, chosen_maint, chosen_prod = realized_costs[selected_action]
        regret = max(0.0, chosen_total - best_cost)
        is_opt = (selected_action == best_act) or (regret <= 2000.0)

        episodes.append(
            IndependentOutcomeEpisode(
                episode_id=i + 1,
                predicted_state=pred_state,
                selected_action=selected_action,
                realized_failure_time_h=round(t_fail, 2),
                realized_repair_time_h=round(realized_repair_hours, 2),
                realized_production_loss_inr=round(chosen_prod, 2),
                realized_maintenance_cost_inr=round(chosen_maint, 2),
                total_realized_cost_inr=round(chosen_total, 2),
                ex_post_optimal_action=best_act,
                ex_post_optimal_cost_inr=round(best_cost, 2),
                regret_inr=round(regret, 2),
                is_optimal=is_opt,
            )
        )

    regrets = [e.regret_inr for e in episodes]
    optimal_count = sum(1 for e in episodes if e.is_optimal)

    summary = {
        "status": "COMPLETED",
        "n_episodes": n_episodes,
        "mean_regret_inr": round(float(np.mean(regrets)), 2),
        "median_regret_inr": round(float(np.median(regrets)), 2),
        "p95_regret_inr": round(float(np.percentile(regrets, 95)), 2),
        "max_regret_inr": round(float(np.max(regrets)), 2),
        "optimal_action_pct": round((optimal_count / n_episodes) * 100.0, 1),
        "episodes": [asdict(e) for e in episodes],
    }
    return summary

