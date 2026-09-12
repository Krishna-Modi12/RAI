"""Typed inputs and outputs for maintenance counterfactuals.

This package deliberately does not import the frozen application schemas or the existing
economics engine.  A decision is reproducible from the values in these dataclasses alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any


class DecisionAction(str, Enum):
    REPAIR_NOW = "repair_now"
    INSPECT_FIRST = "inspect_first"
    DEFER_24H = "defer_24h"
    DEFER_72H = "defer_72h"
    DO_NOTHING = "do_nothing"
    CLEAN_NOW = "clean_now"
    WAIT_FOR_RAIN = "wait_for_rain"


class DecisionPolicy(str, Enum):
    ACT = "act"
    MONITOR = "monitor"
    DO_NOTHING = "do_nothing"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class NumericRange:
    """Inclusive deterministic range used for uncertain inputs and outputs."""

    low: float
    high: float

    def __post_init__(self) -> None:
        if not isfinite(self.low) or not isfinite(self.high):
            raise ValueError("range bounds must be finite")
        if self.low > self.high:
            raise ValueError("range low must not exceed high")

    @classmethod
    def of(cls, value: NumericRange | float | int) -> NumericRange:
        if isinstance(value, cls):
            return value
        return cls(float(value), float(value))

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2.0

    @property
    def width(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class CounterfactualScenario:
    """One action and the cost inputs needed to evaluate it."""

    action: DecisionAction | str
    delay_hours: int
    intervention_cost_inr: NumericRange | float
    energy_loss_inr: NumericRange | float
    failure_probability: NumericRange | float
    failure_consequence_inr: NumericRange | float
    rationale: str = ""

    def __post_init__(self) -> None:
        try:
            action = DecisionAction(self.action)
        except ValueError as exc:
            raise ValueError(f"unsupported decision action: {self.action!r}") from exc
        if self.delay_hours < 0:
            raise ValueError("delay_hours must be non-negative")
        probability = NumericRange.of(self.failure_probability)
        if probability.low < 0.0 or probability.high > 1.0:
            raise ValueError("failure_probability must be between 0 and 1")
        for name in ("intervention_cost_inr", "energy_loss_inr", "failure_consequence_inr"):
            values = NumericRange.of(getattr(self, name))
            if values.low < 0.0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, values)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "failure_probability", probability)


@dataclass(frozen=True)
class DecisionEvidence:
    """Evidence quality and context used to gate a recommendation."""

    asset_id: str
    asset_type: str
    component: str
    evidence_score: float
    confidence: NumericRange | float
    available_signals: int = 1
    required_signals: int = 1
    persistence_hours: float = 0.0
    required_persistence_hours: float = 0.0
    environmental_explanation: float = 0.0
    sensor_health: str = "ok"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("asset_id is required")
        if not self.asset_type:
            raise ValueError("asset_type is required")
        if not 0.0 <= self.evidence_score <= 1.0:
            raise ValueError("evidence_score must be between 0 and 1")
        confidence = NumericRange.of(self.confidence)
        if confidence.low < 0.0 or confidence.high > 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.available_signals < 0 or self.required_signals < 0:
            raise ValueError("signal counts must be non-negative")
        if self.persistence_hours < 0.0 or self.required_persistence_hours < 0.0:
            raise ValueError("persistence hours must be non-negative")
        if not 0.0 <= self.environmental_explanation <= 1.0:
            raise ValueError("environmental_explanation must be between 0 and 1")
        if self.sensor_health not in {"ok", "suspect", "failed"}:
            raise ValueError("sensor_health must be ok, suspect, or failed")
        object.__setattr__(self, "confidence", confidence)


@dataclass(frozen=True)
class ScenarioEvaluation:
    """Computed cost range and its explainable arithmetic for one scenario."""

    scenario: CounterfactualScenario
    expected_cost_inr: NumericRange
    midpoint_cost_inr: float
    cost_breakdown_inr: Mapping[str, NumericRange]


@dataclass(frozen=True)
class DecisionResult:
    """Final policy decision, including an auditable ranking."""

    policy: DecisionPolicy
    recommended_action: DecisionAction | None
    scenarios: tuple[ScenarioEvaluation, ...]
    abstention_reasons: tuple[str, ...] = field(default_factory=tuple)
    explanation: str = ""

    @property
    def abstained(self) -> bool:
        return self.policy is DecisionPolicy.ABSTAIN


@dataclass(frozen=True)
class DecisionRegretResult:
    """Regret for an individual counterfactual decision against ex-post optimal."""

    scenario_name: str
    chosen_action: str
    optimal_action: str
    chosen_cost_inr: float
    optimal_cost_inr: float
    regret_inr: float
    is_optimal: bool


@dataclass(frozen=True)
class DecisionRegretSummary:
    """Summary statistics for decision regret across multiple operational scenarios."""

    mean_regret_inr: float
    median_regret_inr: float
    p95_regret_inr: float
    max_regret_inr: float
    scenario_count: int
    optimal_decision_pct: float


@dataclass(frozen=True)
class ValueInformationResult:
    """Value of Information (VOI) quantifying economic benefit of pre-repair inspection."""

    expected_cost_without_inspection_inr: float
    expected_cost_with_inspection_inr: float
    inspection_cost_inr: float
    voi_inr: float
    is_inspection_justified: bool
    recommendation: str


@dataclass(frozen=True)
class DecisionSensitivityResult:
    """Sensitivity analysis documenting evidence boundaries that would flip the policy."""

    current_recommendation: str
    stable_under: tuple[str, ...]
    changes_if: tuple[str, ...]


@dataclass(frozen=True)
class RiskAttributionExplanation:
    """Decomposition of why predicted risk increased or decreased between monitoring intervals."""

    asset_id: str
    current_risk: float
    previous_risk: float
    risk_change_pp: float
    contributors: tuple[dict[str, Any], ...]
    summary: str


@dataclass(frozen=True)
class MaintenanceOutcome:
    """Closed-loop feedback record linking recommendation to physical technician findings."""

    asset_id: str
    timestamp: str
    recommended_action: str
    actual_action_taken: str
    technician_finding: str
    actual_downtime_hours: float
    actual_cost_inr: float
    lesson_learned: str

