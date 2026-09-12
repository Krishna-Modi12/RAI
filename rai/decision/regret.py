"""Decision regret calculation and operational summary metrics.

Defines:
Regret = Cost(chosen_policy) - Cost(ex-post_optimal_policy)

Allows direct evaluation of the decision-intelligence layer in currency units (INR),
distinguishing trivial errors (₹200) from catastrophic misallocations (₹2,00,000).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

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
        scenario_name=f"stochastic_realization_{'fault' if has_real_defect else 'healthy'}",
        chosen_action=matched_chosen,
        optimal_action=best_action,
        chosen_cost_inr=round(chosen_cost, 2),
        optimal_cost_inr=round(optimal_cost, 2),
        regret_inr=round(regret, 2),
        is_optimal=is_optimal,
    )
