"""Solar Expected-Performance Readiness & Ground-Truth Evaluator.

Assesses whether a candidate solar dataset provides the required environmental,
thermal, and electrical channels to fit P_expected = f(G, T, system) and
evaluates the availability and rigor of failure/degradation ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rai.eval.external.solar.inventory import (
    ExpectedPerformanceReadiness,
    FailureGroundTruthType,
    SolarSourceRecord,
)


@dataclass(frozen=True)
class PerformanceReadinessAudit:
    """Audit result for a dataset's readiness to support expected performance modeling."""

    source_id: str
    readiness_status: ExpectedPerformanceReadiness
    has_irradiance_channel: bool
    has_temperature_channel: bool
    has_power_output_channel: bool
    has_string_channel: bool
    has_tracker_channel: bool
    rationale: str
    missing_critical_channels: list[str]


@dataclass(frozen=True)
class DataQualityAuditResult:
    """Audit result for data quality risks and handling policies."""

    source_id: str
    nighttime_zero_policy: str
    pyranometer_drift_risk: str
    clipping_detection_readiness: str
    curtailment_handling_status: str
    missing_value_policy: str


def evaluate_source_readiness(record: SolarSourceRecord) -> PerformanceReadinessAudit:
    """Evaluate whether a solar source has the required signals for P_expected = f(env, system)."""
    has_irrad = record.irradiance_data
    has_temp = record.temperature_data
    has_power = record.power_data or record.inverter_data
    has_string = record.string_data
    has_tracker = record.tracker_data

    missing: list[str] = []
    if not has_irrad:
        missing.append("Irradiance (POA / GHI)")
    if not has_temp:
        missing.append("Temperature (Module / Ambient)")
    if not has_power:
        missing.append("Power Output (AC / DC)")

    if has_irrad and has_temp and has_power:
        status = ExpectedPerformanceReadiness.READY
        rationale = "Source contains synchronized irradiance, temperature, and electrical power generation."
    elif has_irrad or has_power:
        status = ExpectedPerformanceReadiness.PARTIALLY_READY
        rationale = f"Source lacks key channels: {', '.join(missing)}."
    else:
        status = ExpectedPerformanceReadiness.NOT_READY
        rationale = "Source contains neither environmental irradiance nor operational power telemetry."

    return PerformanceReadinessAudit(
        source_id=record.source_id,
        readiness_status=status,
        has_irradiance_channel=has_irrad,
        has_temperature_channel=has_temp,
        has_power_output_channel=has_power,
        has_string_channel=has_string,
        has_tracker_channel=has_tracker,
        rationale=rationale,
        missing_critical_channels=missing,
    )


def audit_data_quality_risks(record: SolarSourceRecord) -> DataQualityAuditResult:
    """Audit known data quality hazards and specify handling rules."""
    return DataQualityAuditResult(
        source_id=record.source_id,
        nighttime_zero_policy="Filter GHI/POA <= 5 W/m^2 and solar elevation <= 0 deg; do not treat zero power at night as equipment failure.",
        pyranometer_drift_risk="Cross-check measured pyranometer against clear-sky model (pvlib.clearsky.ineichen) and satellite reanalysis (NSRDB).",
        clipping_detection_readiness="Inverter AC power saturation at rated nameplate capacity requires dedicated clipping filter to avoid false residual alarms.",
        curtailment_handling_status="Unflagged external grid curtailment causes artificial negative power residuals unless grid_status/curtailment is monitored.",
        missing_value_policy="Linear interpolation permitted for gaps <= 2 intervals during daylight; forward-fill forbidden across day/night boundaries.",
    )


def audit_failure_ground_truth(record: SolarSourceRecord) -> dict[str, Any]:
    """Audit the nature and veracity of failure and degradation evidence."""
    gt_type = record.ground_truth_type
    has_failures = record.failure_labels
    has_degradation = record.degradation_labels
    has_logs = record.maintenance_logs

    if gt_type == FailureGroundTruthType.VERIFIED_FAILURE_TIMELINES:
        veracity = "HIGH_SYNTHETIC" if record.evidence_tier.name == "TIER_5" else "HIGH_EMPIRICAL"
        recommendation = "Use for quantitative precision-recall and lead-time evaluation against exact failure timestamps."
    elif gt_type == FailureGroundTruthType.MAINTENANCE_LOGS:
        veracity = "MEDIUM_QUALITATIVE"
        recommendation = "Use for semi-supervised validation; requires NLP/heuristic extraction of work order dates."
    elif gt_type == FailureGroundTruthType.DEGRADATION_ONLY:
        veracity = "HIGH_STATISTICAL"
        recommendation = "Use for long-term health degradation modeling and soiling loss estimation; not for acute component trip detection."
    else:
        veracity = "NONE"
        recommendation = "Use strictly for normal-operation expected-performance modeling and false-alarm rate calibration."

    return {
        "source_id": record.source_id,
        "ground_truth_type": gt_type.value,
        "has_failure_labels": has_failures,
        "has_degradation_labels": has_degradation,
        "has_maintenance_logs": has_logs,
        "veracity_classification": veracity,
        "recommended_handling": recommendation,
    }
