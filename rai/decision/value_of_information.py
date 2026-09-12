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
    """Calculate Value of Information (VOI) and EVPI for pre-repair diagnostic inspection.

    Mathematical Formulation (Cost Minimization):
    Let theta in {fault, healthy}, a in {repair, defer}.
    1. Without Information:
       E[C(repair)] = repair_cost_inr
       E[C(defer)]  = p * (failure_consequence_inr + energy_loss_deferral_inr)
       C_without    = min_a E[C(a, theta)] = min(E[C(repair)], E[C(defer)])

    2. Expected Value of Perfect Information (EVPI):
       E[min_a C(a, theta)] = p * min(repair_cost_inr, failure_consequence_inr + energy_loss_deferral_inr)
                              + (1-p) * 0.0
       EVPI = min_a E[C(a, theta)] - E[min_a C(a, theta)] >= 0

    3. Expected Value of Sample Information (EVSI / Gross VOI):
       E_Y[C*(Y)] = P(pos)*C*(pos) + P(neg)*C*(neg)
       EVSI = C_without - E_Y[C*(Y)], where 0 <= EVSI <= EVPI

    4. Net Value of Information (Net VOI):
       Net VOI = EVSI - inspection_cost_inr = C_without - (E_Y[C*(Y)] + inspection_cost_inr)
       Inspection is economically justified iff Net VOI > 0.
    """
    p = max(0.001, min(0.999, prior_failure_probability))
    catastrophic_deferral_cost = failure_consequence_inr + energy_loss_deferral_inr

    # 1. Expected cost without inspection
    cost_immediate_repair = repair_cost_inr
    cost_deferral = p * catastrophic_deferral_cost
    cost_without_info = min(cost_immediate_repair, cost_deferral)

    # 2. Expected cost with perfect information and EVPI
    cost_fault_perfect = min(repair_cost_inr, catastrophic_deferral_cost)
    cost_healthy_perfect = 0.0
    expected_cost_perfect_info = (p * cost_fault_perfect) + ((1.0 - p) * cost_healthy_perfect)
    evpi = max(0.0, cost_without_info - expected_cost_perfect_info)

    # 3. Probability of inspection test outcomes (Sample Information)
    p_pos = (p * inspection_sensitivity) + ((1.0 - p) * (1.0 - inspection_specificity))
    p_neg = max(1e-6, 1.0 - p_pos)
    p_pos = max(1e-6, p_pos)

    # Posterior probabilities given test outcome
    p_fault_given_pos = (p * inspection_sensitivity) / p_pos
    p_fault_given_neg = (p * (1.0 - inspection_sensitivity)) / p_neg

    # Decision conditional on positive test (repair vs defer)
    cost_given_pos = min(repair_cost_inr, p_fault_given_pos * catastrophic_deferral_cost)

    # Decision conditional on negative test (repair vs defer)
    cost_given_neg = min(repair_cost_inr, p_fault_given_neg * catastrophic_deferral_cost)

    expected_cost_with_sample_info = (p_pos * cost_given_pos) + (p_neg * cost_given_neg)

    # EVSI (Gross value of imperfect inspection, bounded by EVPI)
    evsi = max(0.0, min(evpi, cost_without_info - expected_cost_with_sample_info))

    # Net VOI after paying the inspection fee
    expected_cost_with_info = expected_cost_with_sample_info + inspection_cost_inr
    net_voi = cost_without_info - expected_cost_with_info
    is_justified = (net_voi > 0.0)

    if is_justified:
        rec = (
            f"INSPECT FIRST is justified: Net VOI of ₹{net_voi:,.0f} (EVSI: ₹{evsi:,.0f}, EVPI: ₹{evpi:,.0f}). "
            f"Pre-repair inspection resolves uncertainty and avoids unnecessary ₹{repair_cost_inr:,.0f} overhaul."
        )
    elif cost_immediate_repair < cost_deferral:
        rec = (
            f"REPAIR IMMEDIATELY: Net VOI is negative (-₹{abs(net_voi):,.0f}). "
            f"High prior risk ({p:.1%}) makes immediate replacement cheaper than inspecting first."
        )
    else:
        rec = (
            f"MONITOR / DEFER: Net VOI is negative (-₹{abs(net_voi):,.0f}). "
            f"Low prior risk ({p:.1%}) does not justify the ₹{inspection_cost_inr:,.0f} inspection fee."
        )

    return ValueInformationResult(
        expected_cost_without_inspection_inr=round(cost_without_info, 2),
        expected_cost_with_inspection_inr=round(expected_cost_with_sample_info, 2),
        inspection_cost_inr=round(inspection_cost_inr, 2),
        voi_inr=round(net_voi, 2),
        is_inspection_justified=is_justified,
        recommendation=rec,
        evpi_inr=round(evpi, 2),
        evsi_inr=round(evsi, 2),
    )
