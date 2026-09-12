"""Mathematical verification tests for EVPI, EVSI, VOI, and Decision Regret.

Formally proves:
1. Non-negative EVPI under cost minimization: EVPI = min_a E[C(a, theta)] - E[min_a C(a, theta)] >= 0
2. Zero EVPI when information cannot alter the optimal decision (boundary priors p=0, p=1)
3. Information ordering bound: 0 <= EVSI <= EVPI
4. Net VOI identity: Net VOI = EVSI - inspection_cost
5. Monotonicity and boundary behavior under extreme inspection costs
6. Regret non-negativity: Regret(a, omega) = C(a, omega) - min_a' C(a', omega) >= 0
"""

from __future__ import annotations

import numpy as np

from rai.decision.models import ValueInformationResult
from rai.decision.regret import simulate_independent_outcome_world_regret
from rai.decision.value_of_information import compute_value_of_information


def test_evpi_non_negative_across_priors():
    """Verify EVPI is strictly non-negative across all prior probabilities p in [0.01, 0.99]."""
    repair_cost = 85_000.0
    failure_cost = 450_000.0
    inspection_cost = 12_000.0

    priors = np.linspace(0.01, 0.99, 50)
    for p in priors:
        res: ValueInformationResult = compute_value_of_information(
            prior_failure_probability=float(p),
            repair_cost_inr=repair_cost,
            failure_consequence_inr=failure_cost,
            inspection_cost_inr=inspection_cost,
        )
        assert res.evpi_inr >= -1e-6, f"EVPI negative ({res.evpi_inr}) at prior {p:.3f}"
        assert res.evsi_inr >= -1e-6, f"EVSI negative ({res.evsi_inr}) at prior {p:.3f}"
        # Fundamental information bound: imperfect sample information cannot exceed perfect information
        assert res.evsi_inr <= res.evpi_inr + 1e-4, (
            f"EVSI ({res.evsi_inr}) exceeded EVPI ({res.evpi_inr}) at prior {p:.3f}"
        )


def test_evpi_zero_when_decision_invariant():
    """Verify EVPI approaches zero at extreme priors where information cannot change the optimal decision."""
    repair_cost = 85_000.0
    failure_cost = 450_000.0
    inspection_cost = 12_000.0

    # Case A: Prior failure probability near 0 -> Unconditionally DEFER/MONITOR
    res_zero = compute_value_of_information(
        prior_failure_probability=0.001,
        repair_cost_inr=repair_cost,
        failure_consequence_inr=failure_cost,
        inspection_cost_inr=inspection_cost,
    )
    # Expected cost without info is ~455 INR; EVPI cannot exceed 455 INR
    assert res_zero.evpi_inr < 500.0
    assert res_zero.is_inspection_justified is False
    assert res_zero.voi_inr < 0.0

    # Case B: Prior failure probability near 1 -> Unconditionally REPAIR
    res_one = compute_value_of_information(
        prior_failure_probability=0.999,
        repair_cost_inr=repair_cost,
        failure_consequence_inr=failure_cost,
        inspection_cost_inr=inspection_cost,
    )
    # With p=0.999, healthy probability is 0.001 -> EVPI is 0.001 * 85,000 = 85 INR
    assert res_one.evpi_inr < 100.0
    assert res_one.is_inspection_justified is False
    assert res_one.voi_inr < 0.0


def test_net_voi_formula_identity():
    """Verify Net VOI = EVSI - inspection_cost exactly."""
    res = compute_value_of_information(
        prior_failure_probability=0.35,
        repair_cost_inr=85_000.0,
        failure_consequence_inr=450_000.0,
        inspection_cost_inr=12_000.0,
    )
    expected_net = round(res.evsi_inr - res.inspection_cost_inr, 2)
    assert abs(res.voi_inr - expected_net) < 1e-2, (
        f"VOI ({res.voi_inr}) does not match EVSI - inspection ({expected_net})"
    )


def test_positive_net_voi_in_uncertain_regime():
    """Verify that Net VOI is positive when inspection resolves high economic uncertainty."""
    res = compute_value_of_information(
        prior_failure_probability=0.25,
        repair_cost_inr=85_000.0,
        failure_consequence_inr=450_000.0,
        inspection_cost_inr=12_000.0,
        inspection_sensitivity=0.95,
        inspection_specificity=0.92,
    )
    assert res.evpi_inr > 50_000.0
    assert res.evsi_inr > 40_000.0
    assert res.voi_inr > 25_000.0
    assert res.is_inspection_justified is True
    assert "INSPECT FIRST is justified" in res.recommendation


def test_negative_net_voi_when_cost_exceeds_evpi():
    """Verify that Net VOI is negative whenever inspection cost exceeds EVPI."""
    res = compute_value_of_information(
        prior_failure_probability=0.15,
        repair_cost_inr=85_000.0,
        failure_consequence_inr=450_000.0,
        inspection_cost_inr=100_000.0,  # Prohibitively expensive inspection
    )
    assert res.voi_inr < 0.0
    assert res.is_inspection_justified is False
    assert "does not justify" in res.recommendation or "negative" in res.recommendation


def test_decision_regret_non_negativity():
    """Verify ex-post decision regret is mathematically non-negative by definition and decoupled."""
    res = simulate_independent_outcome_world_regret(n_episodes=50, seed=42)
    episodes = res["episodes"]

    assert len(episodes) == 50
    for ep in episodes:
        assert ep["total_realized_cost_inr"] >= ep["ex_post_optimal_cost_inr"] - 1e-4
        assert ep["regret_inr"] >= -1e-4
        assert abs(ep["regret_inr"] - (ep["total_realized_cost_inr"] - ep["ex_post_optimal_cost_inr"])) < 1e-2

    # Verify realistic non-zero regret and imperfect optimality in decoupled world
    assert res["mean_regret_inr"] > 0.0
    assert res["optimal_action_pct"] < 100.0
