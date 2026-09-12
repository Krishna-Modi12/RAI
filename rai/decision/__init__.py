"""Deterministic counterfactual maintenance decisions & decision intelligence."""

from .engine import DecisionEngine, evaluate_counterfactuals, standard_scenarios
from .models import (
    CounterfactualScenario,
    DecisionAction,
    DecisionEvidence,
    DecisionPolicy,
    DecisionRegretResult,
    DecisionRegretSummary,
    DecisionResult,
    DecisionSensitivityResult,
    MaintenanceOutcome,
    NumericRange,
    RiskAttributionExplanation,
    ScenarioEvaluation,
    ValueInformationResult,
)
from .policy import (
    analyze_decision_sensitivity,
    explain_risk_change,
    record_maintenance_feedback,
)
from .regret import (
    compute_scenario_regret,
    summarize_decision_regret,
)
from .scenarios import standard_scenarios as build_standard_scenarios
from .value_of_information import compute_value_of_information

__all__ = [
    "CounterfactualScenario",
    "DecisionAction",
    "DecisionEngine",
    "DecisionEvidence",
    "DecisionPolicy",
    "DecisionRegretResult",
    "DecisionRegretSummary",
    "DecisionResult",
    "DecisionSensitivityResult",
    "MaintenanceOutcome",
    "NumericRange",
    "RiskAttributionExplanation",
    "ScenarioEvaluation",
    "ValueInformationResult",
    "analyze_decision_sensitivity",
    "build_standard_scenarios",
    "compute_scenario_regret",
    "compute_value_of_information",
    "evaluate_counterfactuals",
    "explain_risk_change",
    "record_maintenance_feedback",
    "standard_scenarios",
    "summarize_decision_regret",
]
