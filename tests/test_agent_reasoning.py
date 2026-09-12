"""Tests for the diagnostic rule chain.

These encode the project's central claim: an equipment fault is asserted only after weather,
curtailment, sensor health and fleet-wide behaviour have been ruled out. If these tests pass,
the system does not cry wolf on a cloudy afternoon or a drifting anemometer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rai.agent import fallback
from rai.config import settings
from rai.schemas import (
    AnomalyEvidence,
    AssetType,
    DetectorScore,
    EnvironmentEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    HistoricalCase,
    OperatingState,
    PeerEvidence,
    PeerVerdict,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
    SensorHealth,
    Severity,
    SoilingEvidence,
)

NOW = datetime(2026, 9, 12, 6, 40, tzinfo=UTC)


def _signal(name: str, unit: str, z: float, pct: float | None = None, trend: float = 0.0):
    return ResidualSignal(
        name=name,
        unit=unit,
        actual=100.0,
        expected=90.0,
        residual=10.0,
        residual_pct=pct,
        z_score=z,
        trend_per_day=trend,
        baseline_sigma=1.0,
    )


def _packet(
    *,
    asset_id: str = "WT-017",
    asset_type: AssetType = AssetType.WIND_TURBINE,
    signals: list[ResidualSignal] | None = None,
    dominant: str | None = "drivetrain_vibration_mms",
    persistence: float = 18.5,
    detectors_fired: int = 3,
    risk_band: RiskBand = RiskBand.HIGH,
    risk_score: float = 0.82,
    peers: PeerEvidence | None = None,
    environment: EnvironmentEvidence | None = None,
    soiling: SoilingEvidence | None = None,
) -> EvidencePacket:
    detectors = [
        DetectorScore(detector=name, score=0.8, threshold=0.6, fired=i < detectors_fired)
        for i, name in enumerate(["residual_z", "isolation_forest", "changepoint"])
    ]
    return EvidencePacket(
        asset_id=asset_id,
        asset_type=asset_type,
        generated_at=NOW,
        health_score=58.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.91,
            detectors=detectors,
            signals=signals
            if signals is not None
            else [
                _signal("drivetrain_vibration_mms", "mm/s", 3.4, 29.1, 0.18),
                _signal("gearbox_oil_temp_c", "°C", 4.1, 12.0, 0.4),
                _signal("power_kw", "kW", -2.6, -9.4),
            ],
            persistence_hours=persistence,
            first_seen=NOW - timedelta(hours=persistence),
            change_point_at=NOW - timedelta(hours=persistence, minutes=30),
            dominant_signal=dominant,
        ),
        risk=RiskAssessment(
            risk_score=risk_score,
            risk_band=risk_band,
            horizon_days=30,
            risk_window_days=(7, 21),
            calibration="isotonic",
        ),
        peers=peers
        if peers is not None
        else PeerEvidence(
            peer_group="kutch-row-b",
            n_peers=8,
            asset_residual_pct=-9.4,
            peer_median_residual_pct=-0.8,
            deviation_percentile=96.0,
            verdict=PeerVerdict.ASSET_SPECIFIC,
        ),
        environment=environment
        if environment is not None
        else EnvironmentEvidence(
            source="test",
            conditions={"wind_speed_ms": 9.1},
            operating_state=OperatingState.NORMAL,
            curtailment_detected=False,
            sensor_health=SensorHealth.OK,
            explains_fraction=0.08,
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
        ),
        soiling=soiling,
    )


# --------------------------------------------------------------------------- equipment faults


def test_gearbox_wear_is_diagnosed_as_equipment_fault():
    verdict = fallback.diagnose(_packet())
    assert verdict.component == "gearbox"
    assert "gearbox" in verdict.likely_cause.lower()
    assert verdict.severity is Severity.HIGH
    assert verdict.action_deadline_hours == 72
    assert verdict.confidence >= settings.needle_confidence_threshold
    assert verdict.requires_human_review is False
    assert verdict.fallback_used is True
    assert verdict.model_used == "deterministic_reasoner"


def test_vibration_plus_thermal_signature_overrides_dominant_signal():
    # Dominant signal says power, but the vibration+thermal pair is the drivetrain pattern.
    verdict = fallback.diagnose(_packet(dominant="power_kw"))
    assert verdict.component == "gearbox"


def test_generator_signal_maps_to_generator_component():
    verdict = fallback.diagnose(
        _packet(
            signals=[_signal("generator_winding_temp_c", "°C", 4.5, 15.0, 0.5)],
            dominant="generator_winding_temp_c",
        )
    )
    assert verdict.component == "generator"


def test_evidence_summary_cites_real_numbers():
    verdict = fallback.diagnose(_packet())
    joined = " ".join(verdict.evidence_summary)
    assert "z=" in joined
    assert "peers" in joined.lower()
    assert "%" in joined


# --------------------------------------------------------------- the discrimination guarantees


def test_curtailment_is_never_an_equipment_fault():
    verdict = fallback.diagnose(
        _packet(
            environment=EnvironmentEvidence(
                source="test",
                operating_state=OperatingState.CURTAILED,
                curtailment_detected=True,
                sensor_health=SensorHealth.OK,
                explains_fraction=0.1,
                verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            )
        )
    )
    assert verdict.component == "none"
    assert verdict.severity is Severity.INFORMATIONAL
    assert "curtail" in verdict.likely_cause.lower()
    assert "no maintenance action" in verdict.recommended_action.lower()


def test_failed_sensor_blames_the_sensor_not_the_drivetrain():
    verdict = fallback.diagnose(
        _packet(
            environment=EnvironmentEvidence(
                source="test",
                operating_state=OperatingState.NORMAL,
                sensor_health=SensorHealth.FAILED,
                explains_fraction=0.05,
                verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            )
        )
    )
    assert verdict.component == "anemometer"
    assert "sensor" in verdict.likely_cause.lower()
    assert "gearbox" not in verdict.likely_cause.lower()
    assert "recalibrate" in verdict.recommended_action.lower()


def test_suspect_sensor_escalates_to_human_review():
    verdict = fallback.diagnose(
        _packet(
            environment=EnvironmentEvidence(
                source="test",
                operating_state=OperatingState.NORMAL,
                sensor_health=SensorHealth.SUSPECT,
                explains_fraction=0.05,
                verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            )
        )
    )
    assert verdict.requires_human_review is True
    assert verdict.component == "anemometer"


@pytest.mark.parametrize("explains", [0.60, 0.75, 0.95])
def test_environmentally_explained_deviation_raises_no_equipment_alert(explains: float):
    verdict = fallback.diagnose(
        _packet(
            environment=EnvironmentEvidence(
                source="test",
                operating_state=OperatingState.NORMAL,
                sensor_health=SensorHealth.OK,
                explains_fraction=explains,
                verdict=EnvironmentVerdict.ENVIRONMENTAL,
            )
        )
    )
    assert verdict.component == "none"
    assert verdict.severity is Severity.INFORMATIONAL


def test_fleet_wide_deviation_is_not_blamed_on_one_asset():
    verdict = fallback.diagnose(
        _packet(
            peers=PeerEvidence(
                peer_group="kutch-row-b",
                n_peers=8,
                asset_residual_pct=-9.0,
                peer_median_residual_pct=-8.4,
                deviation_percentile=52.0,
                verdict=PeerVerdict.FLEET_WIDE,
            )
        )
    )
    assert verdict.component == "none"
    assert "fleet-wide" in verdict.likely_cause.lower()
    assert verdict.requires_human_review is True


def test_soiling_is_recoverable_loss_not_a_defect():
    verdict = fallback.diagnose(
        _packet(
            asset_id="INV-023",
            asset_type=AssetType.SOLAR_INVERTER,
            dominant="performance_ratio",
            signals=[_signal("performance_ratio", "ratio", 3.1, -8.4)],
            soiling=SoilingEvidence(
                soiling_ratio=0.916,
                soiling_loss_pct=8.4,
                soiling_rate_pct_per_day=0.31,
                days_since_rain=19.0,
                rain_probability_48h=0.23,
                method="kimber+pr_ratio",
            ),
        )
    )
    assert verdict.component == "soiling"
    assert verdict.severity is Severity.MEDIUM
    assert "cleaning" in verdict.recommended_action.lower()


# --------------------------------------------------------------------------- gating behaviour


def test_short_lived_transient_is_downgraded():
    sustained = fallback.diagnose(_packet(persistence=30.0))
    transient = fallback.diagnose(_packet(persistence=1.0))
    assert sustained.severity is Severity.HIGH
    assert transient.severity is Severity.LOW
    assert transient.confidence < sustained.confidence


def test_single_detector_is_less_confident_than_three():
    one = fallback.diagnose(_packet(detectors_fired=1))
    three = fallback.diagnose(_packet(detectors_fired=3))
    assert one.confidence < three.confidence


def test_low_confidence_forces_human_review():
    verdict = fallback.diagnose(_packet(detectors_fired=1, persistence=2.0))
    assert verdict.confidence < settings.needle_confidence_threshold
    assert verdict.requires_human_review is True


def test_critical_severity_always_requires_human_review():
    verdict = fallback.diagnose(_packet(risk_band=RiskBand.CRITICAL, risk_score=0.96))
    assert verdict.severity is Severity.CRITICAL
    assert verdict.requires_human_review is True


def test_confidence_is_bounded():
    for fired in (0, 1, 2, 3):
        for persistence in (0.0, 5.0, 48.0):
            v = fallback.diagnose(_packet(detectors_fired=fired, persistence=persistence))
            assert 0.0 < v.confidence <= 0.97


# --------------------------------------------------------------------------- corroboration


def test_agreeing_historical_case_raises_confidence():
    packet = _packet(detectors_fired=2)
    base = fallback.diagnose(packet)
    corroborated = fallback.diagnose(
        packet,
        cases=[
            HistoricalCase(
                case_id="CASE-0031",
                similarity=0.93,
                asset_id="WT-004",
                component="gearbox",
                fault_mode="bearing_spalling",
                outcome="Planned bearing replacement at 14 days",
                lead_time_days=11.0,
                repair_cost_inr=950000.0,
            )
        ],
    )
    assert corroborated.confidence > base.confidence
    assert any("CASE-0031" in line for line in corroborated.evidence_summary)


def test_contradicting_historical_case_lowers_confidence():
    packet = _packet(detectors_fired=2)
    base = fallback.diagnose(packet)
    contradicted = fallback.diagnose(
        packet,
        cases=[
            HistoricalCase(
                case_id="CASE-0099",
                similarity=0.91,
                asset_id="WT-002",
                component="generator",
                fault_mode="winding_insulation",
                outcome="Generator rewind",
                lead_time_days=6.0,
            )
        ],
    )
    assert contradicted.confidence < base.confidence


def test_verdict_survives_a_minimal_packet():
    # Degraded input must not crash the reasoner: no peers, no environment, no signals.
    packet = _packet(signals=[], dominant=None, peers=None, environment=None)
    verdict = fallback.diagnose(packet)
    assert verdict.asset_id == "WT-017"
    assert verdict.recommended_action
    assert verdict.requires_human_review is True
