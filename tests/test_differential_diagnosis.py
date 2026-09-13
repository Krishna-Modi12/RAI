"""Comprehensive tests for the Counterevidence & Differential Diagnosis Engine.

Tests:
1. Wind isolated gearbox bearing fault with vibration corroboration and cooling/ambient ruled out.
2. Wind cooling circuit failure with symmetric thermal elevation and vibration ruled out.
3. Wind ambient heatwave where fleet-wide peer consensus refutes equipment breakdown.
4. Wind grid curtailment where peer cluster derate refutes aerodynamic blade damage.
5. Wind competing hypotheses where sensor ambiguity prevents isolated root cause attribution.
6. Solar discrete DC string outage vs gradual array soiling via step-change counterevidence.
7. Solar inverter bridge thermal derating vs optical soiling.
8. End-to-end integration into fallback.diagnose() adjusting confidence and action advice.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rai.agent import fallback
from rai.models.differential import evaluate_differential_diagnosis
from rai.schemas import (
    AnomalyEvidence,
    AssetType,
    DetectorScore,
    DifferentialStatus,
    EnvironmentEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    HypothesisStatus,
    PeerEvidence,
    PeerVerdict,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
    SensorHealth,
    SoilingEvidence,
)


def _build_test_packet(
    asset_id: str = "WT-004",
    asset_type: AssetType = AssetType.WIND_TURBINE,
    signals: list[ResidualSignal] | None = None,
    detectors: list[DetectorScore] | None = None,
    persistence_hours: float = 24.0,
    peers: PeerEvidence | None = None,
    environment: EnvironmentEvidence | None = None,
    soiling: SoilingEvidence | None = None,
) -> EvidencePacket:
    now = datetime(2026, 9, 13, 10, 0, tzinfo=UTC)
    signals = signals or []
    detectors = detectors or [DetectorScore(detector="z", score=0.85, threshold=0.6, fired=True)]

    return EvidencePacket(
        asset_id=asset_id,
        asset_type=asset_type,
        generated_at=now,
        health_score=60.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.85,
            detectors=detectors,
            signals=signals,
            persistence_hours=persistence_hours,
            first_seen=now,
            dominant_signal=signals[0].name if signals else None,
        ),
        risk=RiskAssessment(
            risk_score=0.75,
            risk_band=RiskBand.HIGH,
            horizon_days=30,
            risk_window_days=(7, 21),
            calibration="isotonic",
        ),
        peers=peers,
        environment=environment,
        soiling=soiling,
    )


class TestWindDifferentialDiagnosis:
    """Wind turbine competing hypothesis and counterevidence tests."""

    def test_isolated_gearbox_bearing_fault_resolved(self):
        """High oil temp + high vibration + peers normal -> isolated gearbox bearing confirmed."""
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=86.0, expected=65.0, residual=21.0, z_score=3.2),
            ResidualSignal(name="drivetrain_vibration_mms", unit="mm/s", actual=6.2, expected=2.5, residual=3.7, z_score=2.8),
            ResidualSignal(name="generator_winding_temp_c", unit="°C", actual=70.0, expected=68.0, residual=2.0, z_score=0.3),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=10,
            verdict=PeerVerdict.ASSET_SPECIFIC,
            deviation_percentile=98.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            explains_fraction=0.08,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_SINGLE_FAULT
        assert verdict.dominant_hypothesis == "gearbox_bearing_degradation"
        assert verdict.abstention_rationale is None

        # Confirm competing hypotheses were evaluated and ruled out
        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["gearbox_bearing_degradation"].status == HypothesisStatus.SUPPORTED
        assert h_map["cooling_circuit_failure"].status == HypothesisStatus.RULED_OUT
        assert h_map["ambient_heatwave"].status == HypothesisStatus.RULED_OUT
        assert len(verdict.counterevidence_summary) > 0

    def test_cooling_system_failure_resolved(self):
        """Gearbox + Generator both hot, but vibration normal -> cooling failure, mechanical fault ruled out."""
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=85.0, expected=65.0, residual=20.0, z_score=2.6),
            ResidualSignal(name="generator_winding_temp_c", unit="°C", actual=120.0, expected=90.0, residual=30.0, z_score=2.5),
            ResidualSignal(name="drivetrain_vibration_mms", unit="mm/s", actual=2.6, expected=2.5, residual=0.1, z_score=0.2),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=10,
            verdict=PeerVerdict.ASSET_SPECIFIC,
            deviation_percentile=95.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            explains_fraction=0.10,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_SINGLE_FAULT
        assert verdict.dominant_hypothesis == "cooling_circuit_failure"

        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["cooling_circuit_failure"].status == HypothesisStatus.SUPPORTED
        assert h_map["gearbox_bearing_degradation"].status == HypothesisStatus.RULED_OUT

    def test_fleet_wide_heatwave_rules_out_equipment_fault(self):
        """Fleet-wide thermal elevation rules out isolated gearbox or cooling hardware failure."""
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=82.0, expected=65.0, residual=17.0, z_score=2.2),
            ResidualSignal(name="generator_winding_temp_c", unit="°C", actual=110.0, expected=90.0, residual=20.0, z_score=2.0),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=12,
            verdict=PeerVerdict.FLEET_WIDE,
            deviation_percentile=52.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.ENVIRONMENTAL,
            explains_fraction=0.85,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_ENVIRONMENTAL
        assert verdict.dominant_hypothesis == "ambient_heatwave"

        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["gearbox_bearing_degradation"].status == HypothesisStatus.RULED_OUT
        assert h_map["ambient_heatwave"].status == HypothesisStatus.SUPPORTED

    def test_grid_curtailment_rules_out_blade_fault(self):
        """Peer-wide power ceiling rules out isolated blade aerodynamic fault."""
        signals = [
            ResidualSignal(name="power_kw", unit="kW", actual=1200.0, expected=2000.0, residual=-800.0, z_score=-3.0),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=10,
            verdict=PeerVerdict.FLEET_WIDE,
            deviation_percentile=50.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.ENVIRONMENTAL,
            explains_fraction=0.90,
            curtailment_detected=True,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_OPERATIONAL
        assert verdict.dominant_hypothesis == "grid_curtailment"

        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["grid_curtailment"].status == HypothesisStatus.SUPPORTED
        assert h_map["pitch_system_misalignment"].status == HypothesisStatus.RULED_OUT

    def test_competing_hypotheses_triggers_abstention(self):
        """Gearbox oil high, but vibration missing/neutral and generator normal -> COMPETING_HYPOTHESES."""
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=82.0, expected=65.0, residual=17.0, z_score=2.2),
            # Missing vibration channel, normal generator
            ResidualSignal(name="generator_winding_temp_c", unit="°C", actual=75.0, expected=72.0, residual=3.0, z_score=0.4),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=10,
            verdict=PeerVerdict.ASSET_SPECIFIC,
            deviation_percentile=94.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            explains_fraction=0.10,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        verdict = evaluate_differential_diagnosis(packet)
        # Bearing degradation is contending (needs vibration), cooling is contending/unresolved
        assert verdict.status == DifferentialStatus.COMPETING_HYPOTHESES
        assert verdict.abstention_rationale is not None
        assert "abstaining" in verdict.abstention_rationale.lower() or "inspection" in verdict.abstention_rationale.lower()


class TestSolarDifferentialDiagnosis:
    """Solar inverter competing hypothesis and counterevidence tests."""

    def test_dc_string_step_outage_resolved(self):
        """Discrete step-change in DC current with nominal voltage rules out gradual soiling."""
        signals = [
            ResidualSignal(name="dc_current_a", unit="A", actual=45.0, expected=90.0, residual=-45.0, z_score=-3.1),
            ResidualSignal(name="dc_voltage_v", unit="V", actual=720.0, expected=715.0, residual=5.0, z_score=0.2),
            ResidualSignal(name="ac_power_kw", unit="kW", actual=32.0, expected=64.0, residual=-32.0, z_score=-2.9),
            ResidualSignal(name="inverter_temp_c", unit="°C", actual=48.0, expected=47.0, residual=1.0, z_score=0.2),
        ]
        detectors = [
            DetectorScore(detector="z", score=0.90, threshold=0.6, fired=True),
            DetectorScore(detector="changepoint", score=1.0, threshold=0.5, fired=True),
        ]
        soiling = SoilingEvidence(soiling_loss_pct=2.0, days_since_rain=5.0)
        packet = _build_test_packet(
            asset_type=AssetType.SOLAR_INVERTER,
            signals=signals,
            detectors=detectors,
            soiling=soiling,
        )

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_SINGLE_FAULT
        assert verdict.dominant_hypothesis == "dc_string_outage"

        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["dc_string_outage"].status == HypothesisStatus.SUPPORTED
        assert h_map["photovoltaic_soiling"].status == HypothesisStatus.RULED_OUT
        assert h_map["inverter_thermal_derate"].status == HypothesisStatus.RULED_OUT

    def test_photovoltaic_soiling_accumulation_resolved(self):
        """Gradual 30-day loss without step change and high CAMS dust confirms soiling."""
        signals = [
            ResidualSignal(name="performance_ratio", unit="", actual=0.68, expected=0.82, residual=-0.14, z_score=-2.4),
            ResidualSignal(name="ac_power_kw", unit="kW", actual=780.0, expected=920.0, residual=-140.0, z_score=-2.1),
            ResidualSignal(name="inverter_temp_c", unit="°C", actual=45.0, expected=45.0, residual=0.0, z_score=0.0),
        ]
        detectors = [DetectorScore(detector="z", score=0.80, threshold=0.6, fired=True)]
        soiling = SoilingEvidence(soiling_loss_pct=8.5, days_since_rain=32.0, soiling_rate_pct_per_day=0.25)
        packet = _build_test_packet(
            asset_type=AssetType.SOLAR_INVERTER,
            signals=signals,
            detectors=detectors,
            persistence_hours=720.0,
            soiling=soiling,
        )

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_ENVIRONMENTAL
        assert verdict.dominant_hypothesis == "photovoltaic_soiling"

        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["photovoltaic_soiling"].status == HypothesisStatus.SUPPORTED
        assert h_map["dc_string_outage"].status == HypothesisStatus.RULED_OUT

    def test_pyranometer_drift_resolved(self):
        """Sensor health degradation with nominal array current flags pyranometer drift as sensor anomaly."""
        signals = [
            ResidualSignal(name="ac_power_kw", unit="kW", actual=450.0, expected=500.0, residual=-50.0, z_score=-1.9),
            ResidualSignal(name="dc_current_a", unit="A", actual=90.0, expected=90.0, residual=0.0, z_score=0.0),
            ResidualSignal(name="inverter_temp_c", unit="°C", actual=45.0, expected=45.0, residual=0.0, z_score=0.0),
        ]
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            explains_fraction=0.0,
            sensor_health=SensorHealth.SUSPECT,
        )
        packet = _build_test_packet(
            asset_type=AssetType.SOLAR_INVERTER,
            signals=signals,
            environment=env,
        )

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_SENSOR_ANOMALY
        assert verdict.dominant_hypothesis == "pyranometer_drift"
        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["pyranometer_drift"].status == HypothesisStatus.SUPPORTED

    def test_pitch_system_misalignment_resolved(self):
        """Single-turbine power deficit with step-change when peers/curtailment are normal -> pitch misalignment."""
        signals = [
            ResidualSignal(name="power_kw", unit="kW", actual=1200.0, expected=2000.0, residual=-800.0, z_score=-3.0),
        ]
        detectors = [
            DetectorScore(detector="z", score=0.90, threshold=0.6, fired=True),
            DetectorScore(detector="changepoint", score=1.0, threshold=0.5, fired=True),
        ]
        peers = PeerEvidence(
            peer_group="kutch-cluster-1",
            n_peers=10,
            verdict=PeerVerdict.ASSET_SPECIFIC,
            deviation_percentile=98.0,
        )
        env = EnvironmentEvidence(
            source="open_meteo",
            verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
            explains_fraction=0.05,
            curtailment_detected=False,
            sensor_health=SensorHealth.OK,
        )
        packet = _build_test_packet(
            asset_type=AssetType.WIND_TURBINE,
            signals=signals,
            detectors=detectors,
            peers=peers,
            environment=env,
        )

        verdict = evaluate_differential_diagnosis(packet)
        assert verdict.status == DifferentialStatus.RESOLVED_SINGLE_FAULT
        assert verdict.dominant_hypothesis == "pitch_system_misalignment"
        h_map = {h.name: h for h in verdict.hypotheses}
        assert h_map["pitch_system_misalignment"].status == HypothesisStatus.SUPPORTED
        assert h_map["grid_curtailment"].status == HypothesisStatus.RULED_OUT


class TestAgentFallbackIntegration:
    """Test that fallback.diagnose() seamlessly incorporates the differential engine."""

    def test_diagnose_populates_differential_verdict(self):
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=86.0, expected=65.0, residual=21.0, z_score=3.2),
            ResidualSignal(name="drivetrain_vibration_mms", unit="mm/s", actual=6.2, expected=2.5, residual=3.7, z_score=2.8),
        ]
        peers = PeerEvidence(peer_group="kutch-cluster-1", n_peers=10, verdict=PeerVerdict.ASSET_SPECIFIC)
        env = EnvironmentEvidence(
            source="open_meteo",verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL, explains_fraction=0.05)
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        agent_verdict = fallback.diagnose(packet)
        assert agent_verdict.differential is not None
        assert agent_verdict.differential.status == DifferentialStatus.RESOLVED_SINGLE_FAULT
        assert any("Counterevidence:" in r for r in agent_verdict.evidence_summary)
        assert agent_verdict.confidence > 0.70

    def test_diagnose_abstains_when_competing_hypotheses_exist(self):
        signals = [
            ResidualSignal(name="gearbox_oil_temp_c", unit="°C", actual=80.0, expected=65.0, residual=15.0, z_score=2.1),
        ]
        peers = PeerEvidence(peer_group="kutch-cluster-1", n_peers=10, verdict=PeerVerdict.ASSET_SPECIFIC)
        env = EnvironmentEvidence(
            source="open_meteo",verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL, explains_fraction=0.10)
        packet = _build_test_packet(signals=signals, peers=peers, environment=env)

        agent_verdict = fallback.diagnose(packet)
        assert agent_verdict.differential is not None
        assert agent_verdict.differential.status == DifferentialStatus.COMPETING_HYPOTHESES
        assert agent_verdict.requires_human_review is True
        assert "Inspect first to resolve competing explanations" in agent_verdict.recommended_action
