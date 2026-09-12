"""Decision policy intelligence: sensitivity analysis, risk attribution, and feedback learning.

Implements:
1. Sensitivity Analysis ('What evidence would change the decision?')
2. Risk Attribution Decomposition ('Why did risk change?')
3. Closed-Loop Maintenance Feedback Learning (technician findings & ground truth capture)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rai.config import ARTIFACTS
from rai.decision.models import (
    DecisionAction,
    DecisionSensitivityResult,
    MaintenanceOutcome,
    RiskAttributionExplanation,
)

log = logging.getLogger(__name__)

FEEDBACK_STORE = ARTIFACTS / "state" / "maintenance_outcomes.jsonl"
FEEDBACK_STORE.parent.mkdir(parents=True, exist_ok=True)


def analyze_decision_sensitivity(
    current_action: str | DecisionAction,
    asset_type: str,
    risk_score: float,
    rain_prob_48h: float = 0.0,
    dust_risk_level: str = "low",
    thermal_z_score: float = 0.0,
) -> DecisionSensitivityResult:
    """Determine what changes in evidence or operational conditions would flip the decision."""
    act_str = current_action.value if hasattr(current_action, "value") else str(current_action)

    stable_conditions: list[str] = []
    change_triggers: list[str] = []

    if act_str in {"repair_now", "inspect_first"}:
        stable_conditions.append(f"Risk score remains above 45% (currently {risk_score:.1%})")
        stable_conditions.append(f"Thermal anomaly persists (> 2.5 sigma, currently {thermal_z_score:.1f}σ)")
        stable_conditions.append("Peer consensus confirms isolated asset deviation")

        change_triggers.append("Decision would flip to MONITOR if thermal residual drops below 1.5σ")
        change_triggers.append("Decision would flip to MONITOR if predicted risk falls below 25%")
        change_triggers.append("Decision would flip to REPAIR_NOW if pre-inspection endoscope confirms spalling")

    elif act_str in {"wait_for_rain", "wait_24h", "wait_72h"}:
        stable_conditions.append(f"Rain probability remains elevated (currently {rain_prob_48h:.0f}%)")
        stable_conditions.append(f"Atmospheric dust event is transient ({dust_risk_level} risk)")

        change_triggers.append("Decision would flip to CLEAN_NOW if rain probability drops below 35%")
        change_triggers.append("Decision would flip to CLEAN_NOW if dust front clears earlier than forecasted")
        change_triggers.append("Decision would flip to DO_NOTHING if off-taker declares extended grid curtailment")

    elif act_str == "clean_now":
        stable_conditions.append(f"No significant rain forecasted in next 7 days ({rain_prob_48h:.0f}% chance)")
        stable_conditions.append("Dust front has fully passed")

        change_triggers.append("Decision would flip to WAIT_FOR_RAIN if rainfall forecast exceeds 60%")
        change_triggers.append("Decision would flip to WAIT_24H if an unexpected sandstorm warning is issued")

    else:  # do_nothing or monitor
        stable_conditions.append(f"Asset metrics remain within nominal baseline bounds (risk {risk_score:.1%})")
        change_triggers.append("Decision would flip to INSPECT if multi-channel residual exceeds 3.0σ for > 12h")
        change_triggers.append("Decision would flip to CLEAN_NOW if soiling generation loss exceeds ₹15,000/week")

    return DecisionSensitivityResult(
        current_recommendation=act_str,
        stable_under=tuple(stable_conditions),
        changes_if=tuple(change_triggers),
    )


def explain_risk_change(
    asset_id: str,
    current_risk: float,
    previous_risk: float,
    thermal_residual_delta: float = 0.0,
    persistence_delta_hours: float = 0.0,
    peer_isolation_score: float = 0.0,
    historical_case_similarity: float = 0.0,
    environmental_explanation: float = 0.0,
) -> RiskAttributionExplanation:
    """Deterministically attribute risk change across telemetry, fleet peers, and environment."""
    diff_pp = (current_risk - previous_risk) * 100.0

    contributors: list[dict[str, Any]] = []

    if abs(diff_pp) > 0.001:
        # 1. Thermal residual contribution
        c_thermal = round(thermal_residual_delta * 4.5, 1)
        contributors.append({
            "factor": "Thermal Residual Divergence",
            "contribution_pp": c_thermal,
            "direction": "elevating" if c_thermal > 0 else "reducing",
        })

        # 2. Degradation persistence
        c_persist = round(min(12.0, persistence_delta_hours * 0.8), 1)
        contributors.append({
            "factor": "Fault Persistence Duration",
            "contribution_pp": c_persist,
            "direction": "elevating" if c_persist > 0 else "neutral",
        })

        # 3. Peer consensus isolation
        c_peer = round(peer_isolation_score * 8.0, 1)
        contributors.append({
            "factor": "Peer Fleet Isolation",
            "contribution_pp": c_peer,
            "direction": "elevating" if c_peer > 0 else "suppressing",
        })

        # 4. Historical case retrieval match
        c_hist = round(historical_case_similarity * 6.0, 1)
        contributors.append({
            "factor": "Historical Failure Trajectory Match",
            "contribution_pp": c_hist,
            "direction": "elevating" if c_hist > 0 else "neutral",
        })

        # 5. Environmental dampening explanation
        c_env = round(-1.0 * environmental_explanation * 10.0, 1)
        contributors.append({
            "factor": "Environmental Weather Explanation",
            "contribution_pp": c_env,
            "direction": "suppressing" if c_env < 0 else "neutral",
        })

    summary = (
        f"Risk shifted by {diff_pp:+.1f} percentage points ({previous_risk:.1%} -> {current_risk:.1%}). "
        f"Primary driver: {contributors[0]['factor'] if contributors else 'Nominal variance'}."
    )

    return RiskAttributionExplanation(
        asset_id=asset_id,
        current_risk=round(current_risk, 3),
        previous_risk=round(previous_risk, 3),
        risk_change_pp=round(diff_pp, 1),
        contributors=tuple(contributors),
        summary=summary,
    )


def record_maintenance_feedback(outcome: MaintenanceOutcome) -> None:
    """Record physical maintenance technician findings for closed-loop learning."""
    record = {
        "asset_id": outcome.asset_id,
        "timestamp": outcome.timestamp,
        "recommended_action": outcome.recommended_action,
        "actual_action_taken": outcome.actual_action_taken,
        "technician_finding": outcome.technician_finding,
        "actual_downtime_hours": outcome.actual_downtime_hours,
        "actual_cost_inr": outcome.actual_cost_inr,
        "lesson_learned": outcome.lesson_learned,
    }
    try:
        with open(FEEDBACK_STORE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        log.info("Logged maintenance feedback for %s: %s", outcome.asset_id, outcome.technician_finding)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to append maintenance outcome: %s", exc)
