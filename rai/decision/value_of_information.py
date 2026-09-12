"""Value of Information (VOI) engine for pre-repair inspection.

Quantifies the economic value of dispatching a diagnostic inspection before committing
to an expensive major overhaul or replacement:

VOI = E[cost without information] - E[cost with information] - inspection_cost

Provides formal mathematical justification for 'INSPECT FIRST' vs 'REPAIR IMMEDIATELY'.
"""

from __future__ import annotations

import logging

from rai.decision.models import ValueInformationResult

log = logging.getLogger(__name__)


def compute_value_of_information(
    prior_failure_probability: float,
    repair_cost_inr: float,
    failure_consequence_inr: float,
    inspection_cost_inr: float,
    energy_loss_deferral_inr: float = 5000.0,
    inspection_sensitivity: float = 0.95,  # P(pos | fault)
    inspection_specificity: float = 0.92,  # P(neg | healthy)
) -> ValueInformationResult:
    """Calculate Value of Information (VOI) for pre-repair diagnostic inspection."""
    p = max(0.001, min(0.999, prior_failure_probability))

    # 1. Expected cost without inspection:
    # Decision is between immediate repair or deferral/monitoring
    cost_immediate_repair = repair_cost_inr
    cost_deferral = (p * failure_consequence_inr) + energy_loss_deferral_inr
    cost_without_info = min(cost_immediate_repair, cost_deferral)

    # 2. Probability of inspection test outcomes:
    # P(pos) = p * sensitivity + (1-p) * (1 - specificity)
    p_pos = (p * inspection_sensitivity) + ((1.0 - p) * (1.0 - inspection_specificity))
    p_neg = 1.0 - p_pos

    # Posterior probabilities given test outcome:
    p_fault_given_pos = (p * inspection_sensitivity) / p_pos if p_pos > 0 else 1.0
    p_fault_given_neg = (p * (1.0 - inspection_sensitivity)) / p_neg if p_neg > 0 else 0.0

    # Decision conditional on positive test (almost always repair)
    cost_given_pos = min(repair_cost_inr, (p_fault_given_pos * failure_consequence_inr) + energy_loss_deferral_inr)

    # Decision conditional on negative test (monitor/defer without repair)
    cost_given_neg = min(repair_cost_inr, (p_fault_given_neg * failure_consequence_inr) + energy_loss_deferral_inr)

    expected_cost_with_info = (p_pos * cost_given_pos) + (p_neg * cost_given_neg)

    # Net VOI after paying the inspection fee
    voi = cost_without_info - (expected_cost_with_info + inspection_cost_inr)
    is_justified = (voi > 0.0)

    if is_justified:
        rec = (
            f"INSPECT FIRST is justified: VOI of ₹{voi:,.0f}. "
            f"Pre-repair inspection resolves uncertainty and avoids unnecessary ₹{repair_cost_inr:,.0f} overhaul."
        )
    elif cost_immediate_repair < cost_deferral:
        rec = (
            f"REPAIR IMMEDIATELY: VOI is negative (-₹{abs(voi):,.0f}). "
            f"High prior risk ({p:.1%}) makes immediate replacement cheaper than inspecting first."
        )
    else:
        rec = (
            f"MONITOR / DEFER: VOI is negative (-₹{abs(voi):,.0f}). "
            f"Low prior risk ({p:.1%}) does not justify the ₹{inspection_cost_inr:,.0f} inspection fee."
        )

    return ValueInformationResult(
        expected_cost_without_inspection_inr=round(cost_without_info, 2),
        expected_cost_with_inspection_inr=round(expected_cost_with_info, 2),
        inspection_cost_inr=round(inspection_cost_inr, 2),
        voi_inr=round(voi, 2),
        is_inspection_justified=is_justified,
        recommendation=rec,
    )
