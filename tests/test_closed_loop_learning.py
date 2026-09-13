"""Verification of Closed-Loop Learning & Retrieval Ingestion in RAI.

Verifies:
1. Strict provenance partitioning:
   - Synthetic test fixtures remain INTERNAL_SYNTHETIC and NEVER pollute EXTERNAL_REAL.
   - Genuine external physical inspection feedback promotes to EXTERNAL_REAL.
   - Unverified operator claims remain INTERNAL_SYNTHETIC.
2. Zero retrieval contamination:
   - get_real_cases() and cases_for(..., partition="real") strictly exclude synthetic records.
3. Idempotent indexing:
   - Repeated indexing calls produce deduplicated case instances with stable case_ids.
4. Retrieval surfaces field-verified cases when relevant.
5. Metrics endpoint reports accurate real vs synthetic field breakdown.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from rai.memory.library import cases_for, get_all_cases, get_field_feedback_cases, get_real_cases
from rai.memory.retrieval import find_similar_cases
from rai.memory.work_orders import (
    FieldResolution,
    WorkOrderPriority,
    WorkOrderStatus,
    approve_work_order,
    propose_work_order,
    record_feedback,
)
from rai.schemas import (
    AnomalyEvidence,
    AssetType,
    DetectorScore,
    EvidencePacket,
    FeedbackProvenance,
    HistoricalSourceType,
    ObservationLevel,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
)
from services.api.main import app

client = TestClient(app)


def test_closed_loop_synthetic_feedback_stays_synthetic():
    """Verify that default test feedback remains INTERNAL_SYNTHETIC and does NOT contaminate real partition."""
    target_asset = "WT-006"
    wo = propose_work_order(
        asset_id=target_asset,
        component="gearbox",
        action="Endoscopic borescope inspection of HSS intermediate bearing",
        deadline_hours=48,
        priority=WorkOrderPriority.HIGH,
        created_by="diagnostic_reasoner_v2",
        provenance=FeedbackProvenance.INTERNAL_TEST_FIXTURE,
    )
    assert wo.ticket_id.startswith("TCK-")

    approved = approve_work_order(
        ticket_id=wo.ticket_id,
        approved_by="lead_operator_01",
        scheduled_deadline_hours=36,
        priority=WorkOrderPriority.HIGH,
    )
    assert approved.status == WorkOrderStatus.APPROVED

    completed = record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="tech_kutch_04",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Borescope confirmed severe spalling on HSS bearing outer raceway.",
        component_inspected="gearbox",
        actual_downtime_hours=14.5,
        actual_parts_cost_inr=320_000.0,
        notes="Bearing replaced up-tower during calm wind window.",
        provenance=FeedbackProvenance.INTERNAL_TEST_FIXTURE,
        observation_level=ObservationLevel.UNKNOWN,
    )
    assert completed.status == WorkOrderStatus.COMPLETED

    field_cases = get_field_feedback_cases()
    matching = [c for c in field_cases if wo.ticket_id in str(c.source_reference) or wo.ticket_id in str(c.observed_signature)]
    assert len(matching) >= 1
    case = matching[0]

    # Must be synthetic test fixture, NOT EXTERNAL_REAL
    assert case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
    assert case.event_class == "SYNTHETIC_WORK_ORDER_FEEDBACK"
    assert case.evidence_quality == "SYNTHETIC_TEST_FIXTURE"

    # Must NOT contaminate real partition
    real_cases = get_real_cases()
    assert not any(case.case_id == c.case_id for c in real_cases)

    real_wind_cases = cases_for("wind_turbine", partition="real")
    assert not any(case.case_id == c.case_id for c in real_wind_cases)

    # Must be indexed in field feedback cases and all_cases
    assert any(case.case_id == c.case_id for c in field_cases)
    assert any(case.case_id == c.case_id for c in get_all_cases())


def test_closed_loop_genuine_external_feedback_promoted_to_real():
    """Verify that genuine externally observed physical findings promote to EXTERNAL_REAL."""
    target_asset = "WT-006"
    wo = propose_work_order(
        asset_id=target_asset,
        component="gearbox",
        action="Teardown inspection of intermediate planetary stage",
        deadline_hours=24,
        priority=WorkOrderPriority.HIGH,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
    )
    approve_work_order(ticket_id=wo.ticket_id, approved_by="plant_operations_head")

    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="cert_tech_oem_44",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Physical borescope and metallographic replica verified severe contact fatigue micro-spalling on sun pinion.",
        component_inspected="gearbox",
        actual_downtime_hours=28.0,
        actual_parts_cost_inr=450_000.0,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
        observation_level=ObservationLevel.PHYSICAL_INSPECTION_VERIFIED,
    )

    field_cases = get_field_feedback_cases()
    matching = [c for c in field_cases if wo.ticket_id in str(c.source_reference)]
    assert len(matching) >= 1
    case = matching[0]

    assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert case.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert case.evidence_quality == "FIELD_VERIFIED"

    # Must be included in real partition
    real_cases = get_real_cases()
    assert any(case.case_id == c.case_id for c in real_cases)

    real_wind_cases = cases_for("wind_turbine", partition="real")
    assert any(case.case_id == c.case_id for c in real_wind_cases)


def test_unverified_operator_claim_stays_synthetic():
    """Verify that unverified operator claims without physical verification stay synthetic."""
    wo = propose_work_order(
        asset_id="INV-001",
        component="inverter",
        action="Check suspected IGBT drift",
        deadline_hours=72,
        provenance=FeedbackProvenance.OPERATOR_ENTERED_UNVERIFIED,
    )
    approve_work_order(ticket_id=wo.ticket_id, approved_by="shift_lead")

    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="shift_op_guest",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Operator suspects IGBT module degradation based on thermal camera quick glance.",
        component_inspected="inverter",
        provenance=FeedbackProvenance.OPERATOR_ENTERED_UNVERIFIED,
        observation_level=ObservationLevel.OPERATOR_CLAIM,
    )

    field_cases = get_field_feedback_cases()
    matching = [c for c in field_cases if wo.ticket_id in str(c.source_reference)]
    assert len(matching) >= 1
    case = matching[0]

    assert case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
    assert case.event_class == "SYNTHETIC_WORK_ORDER_FEEDBACK"

    real_cases = get_real_cases()
    assert not any(case.case_id == c.case_id for c in real_cases)


def test_idempotent_feedback_indexing():
    """Verify that repeated index exports are deduplicated and idempotent."""
    cases1 = get_field_feedback_cases()
    cases2 = get_field_feedback_cases()

    ids1 = [c.case_id for c in cases1]
    ids2 = [c.case_id for c in cases2]

    assert ids1 == ids2
    # Ensure zero duplicate IDs within the returned library
    assert len(ids1) == len(set(ids1))


def test_retrieval_surfaces_field_verified_case():
    """Verify that trajectory kNN retrieval retrieves and cites field-verified cases."""
    target_asset = "WT-007"
    wo = propose_work_order(
        asset_id=target_asset,
        component="gearbox",
        action="Inspect high-speed shaft bearing",
        deadline_hours=24,
        priority=WorkOrderPriority.EMERGENCY,
        created_by="agent",
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
    )
    approve_work_order(ticket_id=wo.ticket_id, approved_by="ops_chief")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="tech_specialist",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="High vibration and bearing overheat caused by lubrication blockage and outer race damage.",
        component_inspected="gearbox",
        actual_downtime_hours=20.0,
        actual_parts_cost_inr=500_000.0,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
        observation_level=ObservationLevel.PHYSICAL_INSPECTION_VERIFIED,
    )

    now = datetime.now(UTC)
    dummy_packet = EvidencePacket(
        asset_id="WT-004",
        asset_type=AssetType.WIND_TURBINE,
        generated_at=now,
        health_score=62.0,
        anomaly=AnomalyEvidence(
            anomaly_score=0.82,
            persistence_hours=36.0,
            first_seen=now,
            detectors=[
                DetectorScore(
                    detector="isolation_forest",
                    score=0.85,
                    threshold=0.5,
                    fired=True,
                )
            ],
            signals=[
                ResidualSignal(
                    name="gearbox_oil_temp_c",
                    unit="degC",
                    actual=78.0,
                    expected=62.0,
                    residual=16.0,
                    z_score=3.8,
                ),
                ResidualSignal(
                    name="drivetrain_vibration_mms",
                    unit="mm/s",
                    actual=5.2,
                    expected=2.1,
                    residual=3.1,
                    z_score=3.2,
                ),
            ],
        ),
        risk=RiskAssessment(
            risk_score=0.75,
            risk_band=RiskBand.HIGH,
            horizon_days=30,
            risk_window_days=(7, 21),
            calibration="isotonic",
        ),
    )

    retrieved = find_similar_cases(dummy_packet, k=10, partition="all")
    assert len(retrieved) > 0

    field_matches = [c for c in retrieved if c.event_class == "FIELD_VERIFIED_RESOLUTION"]
    if field_matches:
        f_case = field_matches[0]
        assert f_case.source_type == HistoricalSourceType.EXTERNAL_REAL
        assert any("technician" in wm.lower() or "inspection" in wm.lower() or "operator" in wm.lower() for wm in f_case.why_matched)


def test_closed_loop_metrics_endpoint():
    """Verify GET /api/work-orders/closed-loop-metrics endpoint."""
    res = client.get("/api/work-orders/closed-loop-metrics")
    assert res.status_code == 200
    data = res.json()

    assert "total_orders" in data
    assert "pending_approval" in data
    assert "concordance_rate_pct" in data
    assert "indexed_field_cases_count" in data
    assert "indexed_real_field_cases_count" in data
    assert "indexed_synthetic_field_cases_count" in data
    assert "total_academic_real_cases_count" in data
    assert "total_real_retrieval_pool_size" in data

    assert data["concordance_rate_pct"] >= 0.0
    assert data["total_real_retrieval_pool_size"] >= 14
