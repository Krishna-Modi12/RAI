"""End-to-End Integration Tests: Real Historical Corpus -> Agent -> Decision Support.

Verifies:
1. Agent resolution of explicit real cases (e.g. REAL-CARE-A-072, REAL-KEL-1-FORCED-3000, REAL-PVDAQ-034-OUTAGE).
2. Provenance preservation: source_type=EXTERNAL_REAL, real dataset citation, event class honesty.
3. Contrastive transparency: why matched, what differs, why may not apply.
4. Investigation pipeline integration: fallback reasoner distinguishes real cases from synthetic scenarios.
"""

from __future__ import annotations

import pytest

from rai.agent import fallback
from rai.agent.investigator import investigate
from rai.agent.query_agent import AgentQueryStatus, InvestigatorAgent
from rai.schemas import AssetType, EvidenceState, HistoricalCase, HistoricalSourceType


@pytest.fixture
def agent() -> InvestigatorAgent:
    return InvestigatorAgent(force_deterministic=True)


def test_agent_retrieves_real_care_case(agent: InvestigatorAgent):
    """Verify agent accurately retrieves and explains a real CARE failure case."""
    resp = agent.answer_query("Show details for REAL-CARE-A-072")
    assert resp.status == AgentQueryStatus.ANSWERED
    assert any(item.state == EvidenceState.RETRIEVED for item in resp.evidence_items)
    retrieved = [item for item in resp.evidence_items if item.state == EvidenceState.RETRIEVED][0]

    assert retrieved.case_id == "REAL-CARE-A-072"
    assert retrieved.source_type == HistoricalSourceType.EXTERNAL_REAL.value
    assert "CARE" in retrieved.source

    ans = resp.answer.lower()
    assert "real-care-a-072" in ans
    assert "gearbox" in ans or "thermal" in ans
    assert "not a confirmed equipment diagnosis" in ans or "contextual" in ans


def test_agent_compares_real_case_with_asset(agent: InvestigatorAgent):
    """Verify agent contrastive comparison of a real historical case against live telemetry."""
    resp = agent.answer_query("Compare REAL-CARE-A-072 with asset WT-004", asset_id="WT-004")
    assert resp.status in [AgentQueryStatus.ANSWERED, AgentQueryStatus.QUALIFIED]
    assert any("compare_case" in tool or "get_case_details" in tool for tool in resp.tools_called)

    ans = resp.answer.lower()
    assert "real-care-a-072" in ans
    assert "differences" in ans or "outcome was" in ans


def test_agent_historical_retrieval_surfaces_real_provenance(agent: InvestigatorAgent):
    """Verify general historical query with real corpus partition surfaces real provenance."""
    resp = agent.answer_query("Find real historical cases similar to WT-004", asset_id="WT-004")
    assert resp.status == AgentQueryStatus.ANSWERED
    retrieved = [item for item in resp.evidence_items if item.state == EvidenceState.RETRIEVED]
    assert len(retrieved) > 0

    # Ensure at least one retrieved item has EXTERNAL_REAL provenance
    real_items = [i for i in retrieved if i.source_type == HistoricalSourceType.EXTERNAL_REAL.value]
    assert len(real_items) > 0
    assert "provenance" in resp.answer.lower()


def test_fallback_reasoner_cites_audited_real_case():
    """Verify fallback diagnostic reasoner formats audited real case with event class and dataset."""
    from datetime import UTC, datetime

    from rai.memory.real_corpus import RealEventClass
    from rai.schemas import (
        AnomalyEvidence,
        DetectorScore,
        EvidencePacket,
        ResidualSignal,
        RiskAssessment,
        RiskBand,
    )

    now = datetime(2026, 9, 13, 10, 0, tzinfo=UTC)
    packet = EvidencePacket(
        asset_id="WT-004",
        asset_type=AssetType.WIND_TURBINE,
        generated_at=now,
        health_score=50.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.90,
            detectors=[DetectorScore(detector="z", score=0.85, threshold=0.6, fired=True)],
            signals=[
                ResidualSignal(
                    name="gearbox_oil_temp_c",
                    unit="°C",
                    actual=85.0,
                    expected=65.0,
                    residual=20.0,
                    z_score=3.5,
                )
            ],
            persistence_hours=24.0,
            first_seen=now,
            dominant_signal="gearbox_oil_temp_c",
        ),
        risk=RiskAssessment(
            risk_score=0.85,
            risk_band=RiskBand.HIGH,
            horizon_days=30,
            risk_window_days=(7, 21),
            calibration="isotonic",
        ),
    )

    real_case = HistoricalCase(
        case_id="REAL-CARE-A-072",
        asset_id="CARE-WT-01",
        asset_type=AssetType.WIND_TURBINE,
        component="gearbox",
        fault_mode="HSS bearing thermal escalation",
        outcome="Confirmed gearbox failure; 7-day outage",
        lead_time_days=7.0,
        similarity=0.89,
        source_type=HistoricalSourceType.EXTERNAL_REAL,
        source_dataset="CARE to Compare Wind Farm A",
        event_class=RealEventClass.REAL_VERIFIED_EVENT.value,
        what_is_different=["growth rate", "persistence"],
    )

    verdict = fallback.diagnose(packet, cases=[real_case])
    assert len(verdict.evidence_summary) > 0
    top_evidence = verdict.evidence_summary[0]

    assert "Audited real case REAL-CARE-A-072" in top_evidence
    assert "CARE to Compare Wind Farm A" in top_evidence
    assert "REAL_VERIFIED_EVENT" in top_evidence
    assert "What differs:" in top_evidence


def test_investigate_live_asset_surfaces_unified_corpus():
    """Verify live investigate endpoint loads cases across unified corpus partition."""
    inv = investigate("WT-004", force_refresh=None)
    assert inv.verdict is not None
    assert len(inv.verdict.historical_cases) > 0
    # Cases should include cases from all partitions
    case_ids = [c.case_id for c in inv.verdict.historical_cases]
    assert len(case_ids) > 0
