from datetime import UTC, datetime

from rai.config import FLEET
from rai.memory.retrieval import find_similar_cases, get_case_details
from rai.schemas import (
    AnomalyEvidence,
    DetectorScore,
    EnvironmentEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    PeerEvidence,
    PeerVerdict,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
    SensorHealth,
)


def _packet() -> EvidencePacket:
    asset = next(a for a in FLEET if a.asset_type.value == "wind_turbine")
    return EvidencePacket(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        generated_at=datetime(2026, 9, 12, tzinfo=UTC),
        health_score=68.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.75,
            detectors=[DetectorScore(detector="residual_z", score=0.8, fired=True)],
            signals=[ResidualSignal(
                name="gearbox_oil_temp_c", unit="C", actual=82, expected=65,
                residual=17, z_score=3.8,
            )],
        ),
        peers=PeerEvidence(
            peer_group="kutch-wind", n_peers=8, deviation_percentile=95,
            verdict=PeerVerdict.ASSET_SPECIFIC,
        ),
        environment=EnvironmentEvidence(
            source="site_met", sensor_health=SensorHealth.OK,
            explains_fraction=0.05, verdict=EnvironmentVerdict.NOT_ENVIRONMENTAL,
        ),
        risk=RiskAssessment(risk_score=0.65, risk_band=RiskBand.ELEVATED),
    )


def test_retrieval_preserves_provenance_and_explanation():
    cases = find_similar_cases(_packet(), k=2)
    assert cases
    relevant = {"CASE-W-001", "CASE-W-002", "CASE-W-003", "CASE-W-006"}
    assert sum(case.case_id in relevant for case in find_similar_cases(_packet(), k=3)) / 3 == 1.0
    case = cases[0]
    assert case.source_type.value == "INTERNAL_SYNTHETIC"
    assert case.evidence_states["observed_signature"].value == "OBSERVED"
    assert case.why_matched
    assert case.what_is_different is not None
    assert case.why_may_not_apply


def test_unknown_case_abstains_and_detail_is_bounded():
    assert get_case_details("DOES-NOT-EXIST") is None
    detail = get_case_details("CASE-W-001")
    assert detail is not None
    assert detail.source_type.value == "INTERNAL_SYNTHETIC"
    assert "raw telemetry" not in detail.outcome.lower()
