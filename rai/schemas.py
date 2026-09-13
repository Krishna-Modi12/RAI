"""Core data contracts for Renewable Asset Intelligence.

Every component in the system speaks these types. The rule that matters most:
`EvidencePacket` is the *only* thing handed to the local LLM. It contains computed,
structured evidence — never raw telemetry rows.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AssetType(str, Enum):
    WIND_TURBINE = "wind_turbine"
    SOLAR_INVERTER = "solar_inverter"


class RiskBand(str, Enum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class Severity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperatingState(str, Enum):
    """Why an asset is producing what it is producing."""

    NORMAL = "normal"
    CURTAILED = "curtailed"
    DERATED = "derated"
    STOPPED = "stopped"
    MAINTENANCE = "maintenance"
    BELOW_CUTIN = "below_cutin"
    ABOVE_CUTOUT = "above_cutout"
    NIGHT = "night"
    UNKNOWN = "unknown"


class EnvironmentVerdict(str, Enum):
    ENVIRONMENTAL = "environmental"
    PARTIAL = "partial"
    NOT_ENVIRONMENTAL = "not_environmental"


class PeerVerdict(str, Enum):
    ASSET_SPECIFIC = "asset_specific"
    FLEET_WIDE = "fleet_wide"
    NORMAL = "normal"


class SensorHealth(str, Enum):
    OK = "ok"
    SUSPECT = "suspect"
    FAILED = "failed"


class HistoricalSourceType(str, Enum):
    """Provenance class for historical evidence; never implies diagnostic truth."""

    REAL_EXTERNAL = "REAL_EXTERNAL"
    HISTORICAL_REAL = "HISTORICAL_REAL"
    INTERNAL_SYNTHETIC = "INTERNAL_SYNTHETIC"
    SIMULATED_OUTCOME = "SIMULATED_OUTCOME"
    MODEL_COMPARISON = "MODEL_COMPARISON"
    SOFTWARE_INVARIANT = "SOFTWARE_INVARIANT"


class EvidenceState(str, Enum):
    OBSERVED = "OBSERVED"
    RETRIEVED = "RETRIEVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    ABSTAINED = "ABSTAINED"


# ---------------------------------------------------------------------------
# Asset registry
# ---------------------------------------------------------------------------


class Asset(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: str
    asset_type: AssetType
    name: str
    site: str
    rated_power_kw: float
    commissioned: str
    peer_group: str
    # Wind-specific
    rotor_diameter_m: float | None = None
    hub_height_m: float | None = None
    cut_in_ms: float | None = None
    rated_ms: float | None = None
    cut_out_ms: float | None = None
    # Solar-specific
    dc_capacity_kw: float | None = None
    n_strings: int | None = None
    tilt_deg: float | None = None
    azimuth_deg: float | None = None
    latitude: float | None = None
    longitude: float | None = None


# ---------------------------------------------------------------------------
# Evidence layers
# ---------------------------------------------------------------------------


class ResidualSignal(BaseModel):
    """One monitored signal: what we saw, what we expected, how far off it is.

    `z_score` is normalised against the residual distribution learned on healthy
    training data, so it is comparable across signals with different units.
    """

    name: str
    unit: str
    actual: float | None
    expected: float | None
    residual: float | None
    residual_pct: float | None = None
    z_score: float | None = None
    trend_per_day: float | None = None
    trend_7d_per_day: float | None = None
    baseline_sigma: float | None = None


class DetectorScore(BaseModel):
    detector: str
    score: float = Field(ge=0.0, le=1.0)
    threshold: float | None = None
    fired: bool = False
    detail: str | None = None


class AnomalyEvidence(BaseModel):
    """Fused output of the anomaly layer. Computed in Python, never by the LLM."""

    anomaly_score: float = Field(ge=0.0, le=1.0)
    detectors: list[DetectorScore] = Field(default_factory=list)
    signals: list[ResidualSignal] = Field(default_factory=list)
    persistence_hours: float = 0.0
    first_seen: datetime | None = None
    change_point_at: datetime | None = None
    dominant_signal: str | None = None


class PeerEvidence(BaseModel):
    """Is this asset deviating, or is the whole fleet deviating together?"""

    peer_group: str
    n_peers: int
    asset_residual_pct: float | None = None
    peer_median_residual_pct: float | None = None
    deviation_percentile: float | None = Field(default=None, ge=0.0, le=100.0)
    verdict: PeerVerdict = PeerVerdict.NORMAL
    note: str | None = None


class EnvironmentEvidence(BaseModel):
    """Can weather, curtailment or a broken sensor explain the deviation?"""

    source: str
    conditions: dict[str, float] = Field(default_factory=dict)
    operating_state: OperatingState = OperatingState.UNKNOWN
    curtailment_detected: bool = False
    sensor_health: SensorHealth = SensorHealth.OK
    explains_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    verdict: EnvironmentVerdict = EnvironmentVerdict.NOT_ENVIRONMENTAL
    note: str | None = None


class CleaningAdvisorOption(BaseModel):
    option_id: str  # "clean_now", "wait_24h", "wait_72h", "wait_7d"
    label: str
    delay_hours: int
    cleaning_cost_inr: float
    expected_energy_loss_inr: float
    net_exposure_inr: float
    break_even_days: float
    rain_cleaning_probability: float
    cementation_risk: bool
    summary: str
    assumptions: dict[str, float] = Field(default_factory=dict)


class CleaningAdvisorEvidence(BaseModel):
    recommended_action: str  # "clean_now", "wait_24h", "wait_72h", "wait_7d", "post_rain_reassess"
    recommended_window: str
    confidence: float
    break_even_days: float
    options: list[CleaningAdvisorOption] = Field(default_factory=list)
    current_soiling_loss_pct: float
    dust_risk_level: str
    rationale: str


class SoilingEvidence(BaseModel):
    """Solar-only: how much loss is dirt, and is rain coming?"""

    soiling_ratio: float | None = None
    soiling_loss_pct: float | None = None
    soiling_rate_pct_per_day: float | None = None
    days_since_cleaning: float | None = None
    days_since_rain: float | None = None
    rain_probability_48h: float | None = None
    method: str | None = None
    cleaning_advisor: CleaningAdvisorEvidence | None = None


class HistoricalCase(BaseModel):
    """A provenance-safe historical episode used as contextual evidence."""

    case_id: str
    similarity: float = Field(ge=0.0, le=1.0)
    asset_id: str
    component: str
    fault_mode: str
    observed_signature: list[str] = Field(default_factory=list)
    outcome: str
    lead_time_days: float | None = None
    repair_cost_inr: float | None = None
    source: str = "synthetic_case_library"
    asset_type: AssetType | None = None
    timestamp: datetime | None = None
    operating_regime: dict[str, str | float | bool | None] = Field(default_factory=dict)
    environment: dict[str, str | float | bool | None] = Field(default_factory=dict)
    expected_signals: list[str] = Field(default_factory=list)
    residuals: dict[str, float | None] = Field(default_factory=dict)
    persistence: str | float | None = None
    anomaly_pattern: list[str] = Field(default_factory=list)
    event_type: str = "UNKNOWN"
    diagnostic_hypotheses: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradictory_evidence: list[str] = Field(default_factory=list)
    maintenance_action: str | None = None
    limitations: list[str] = Field(default_factory=list)
    source_type: HistoricalSourceType = HistoricalSourceType.INTERNAL_SYNTHETIC
    evidence_states: dict[str, EvidenceState] = Field(default_factory=dict)
    why_matched: list[str] = Field(default_factory=list)
    what_is_similar: list[str] = Field(default_factory=list)
    what_is_different: list[str] = Field(default_factory=list)
    why_may_not_apply: list[str] = Field(default_factory=list)


class KnowledgeCitation(BaseModel):
    """A retrieved span from the maintenance corpus, with its exact source."""

    doc_id: str
    title: str
    section: str
    snippet: str
    score: float
    retrieval: str = "fts5"


class RiskAssessment(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_band: RiskBand
    horizon_days: int = 30
    risk_window_days: tuple[int, int] | None = None
    calibration: str | None = None
    drivers: dict[str, float] = Field(default_factory=dict)


class EconomicOption(BaseModel):
    """One intervention choice, fully costed. All arithmetic done in Python."""

    option_id: str
    label: str
    delay_days: int
    intervention_cost_inr: float
    energy_loss_inr: float
    failure_escalation_inr: float
    expected_exposure_inr: float
    failure_probability: float
    assumptions: dict[str, float] = Field(default_factory=dict)


class EconomicEvidence(BaseModel):
    options: list[EconomicOption] = Field(default_factory=list)
    recommended_option_id: str | None = None
    avoidable_exposure_inr: float | None = None
    tariff_inr_per_kwh: float | None = None


# ---------------------------------------------------------------------------
# Asset state + the agent's input packet
# ---------------------------------------------------------------------------


class AssetState(BaseModel):
    """Current computed state of one asset. The UI reads this."""

    asset_id: str
    asset_type: AssetType
    name: str
    site: str
    as_of: datetime
    health_score: float = Field(ge=0.0, le=100.0)
    operating_state: OperatingState = OperatingState.UNKNOWN
    power_kw: float | None = None
    expected_power_kw: float | None = None
    capacity_factor: float | None = None
    anomaly: AnomalyEvidence | None = None
    risk: RiskAssessment | None = None
    peers: PeerEvidence | None = None
    environment: EnvironmentEvidence | None = None
    soiling: SoilingEvidence | None = None
    data_freshness_s: float | None = None


class EvidencePacket(BaseModel):
    """THE boundary object handed to the local LLM.

    Contains only computed evidence. No raw telemetry, no long time series.
    Keep it small: Needle 2 operates in a 256-token sliding window.
    """

    asset_id: str
    asset_type: AssetType
    generated_at: datetime
    health_score: float
    anomaly: AnomalyEvidence
    risk: RiskAssessment
    peers: PeerEvidence | None = None
    environment: EnvironmentEvidence | None = None
    soiling: SoilingEvidence | None = None

    def to_agent_dict(self) -> dict:
        """Compact, flat dict for the agent. Deliberately lossy and small."""
        top = sorted(
            [s for s in self.anomaly.signals if s.z_score is not None],
            key=lambda s: abs(s.z_score or 0.0),
            reverse=True,
        )[:4]
        out: dict = {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "health": round(self.health_score, 1),
            "risk": round(self.risk.risk_score, 3),
            "risk_band": self.risk.risk_band.value,
            "anomaly_score": round(self.anomaly.anomaly_score, 3),
            "persistence_hours": round(self.anomaly.persistence_hours, 1),
            "signals": {
                s.name: {
                    "z": round(s.z_score or 0.0, 2),
                    "pct": round(s.residual_pct, 1) if s.residual_pct is not None else None,
                }
                for s in top
            },
        }
        if self.peers:
            out["peer_verdict"] = self.peers.verdict.value
            out["peer_percentile"] = self.peers.deviation_percentile
        if self.environment:
            out["environment_verdict"] = self.environment.verdict.value
            out["weather_explains_fraction"] = round(self.environment.explains_fraction, 2)
            out["curtailed"] = self.environment.curtailment_detected
            out["sensor_health"] = self.environment.sensor_health.value
        if self.soiling and self.soiling.soiling_loss_pct is not None:
            out["soiling_loss_pct"] = round(self.soiling.soiling_loss_pct, 2)
        return out


# ---------------------------------------------------------------------------
# Agent output
# ---------------------------------------------------------------------------


class AgentVerdict(BaseModel):
    """Structured diagnosis. The agent may never return free-form prose instead."""

    asset_id: str
    likely_cause: str
    component: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    recommended_action: str
    action_deadline_hours: int | None = None
    evidence_summary: list[str] = Field(default_factory=list)
    historical_cases: list[HistoricalCase] = Field(default_factory=list)
    citations: list[KnowledgeCitation] = Field(default_factory=list)
    economics: EconomicEvidence | None = None
    model_used: str = "needle2"
    fallback_used: bool = False
    tool_calls: list[str] = Field(default_factory=list)
    latency_ms: float | None = None


class InvestigationStep(BaseModel):
    """One entry in the investigation timeline the UI animates."""

    at: datetime
    stage: str
    label: str
    detail: str | None = None
    status: Literal["pending", "running", "done", "skipped"] = "done"


class Investigation(BaseModel):
    investigation_id: str
    asset_id: str
    started_at: datetime
    completed_at: datetime | None = None
    packet: EvidencePacket
    verdict: AgentVerdict | None = None
    timeline: list[InvestigationStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ground truth (simulator) — used for honest evaluation, never shown as a model output
# ---------------------------------------------------------------------------


class InjectedEvent(BaseModel):
    """Exact ground truth for a simulated fault. Enables lead-time measurement."""

    event_id: str
    asset_id: str
    scenario: str
    component: str
    is_equipment_fault: bool
    onset: datetime
    detectable_from: datetime
    end: datetime | None = None
    severity_final: float
    description: str
