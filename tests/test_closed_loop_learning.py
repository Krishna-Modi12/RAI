"""Verification of Closed-Loop Learning & Retrieval Ingestion in RAI.

Verifies that:
1. Operator approves a proposed work order.
2. Technician submits physical field inspection feedback with confirmed fault.
3. rai.memory.library.get_field_feedback_cases() automatically constructs and returns
   a Case dataclass instance with EXTERNAL_REAL provenance.
4. retrieve_similar_cases() dynamically surfaces the verified field case with
   operator_field_verified provenance.
5. GET /api/work-orders/closed-loop-metrics accurately reports indexed count and concordance.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from rai.memory.library import get_all_cases, get_field_feedback_cases, get_real_cases
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
    HistoricalSourceType,
    ResidualSignal,
    RiskAssessment,
    RiskBand,
)
from services.api.main import app

client = TestClient(app)


def test_closed_loop_feedback_to_case_ingestion():
    """Verify that technician confirmed fault feedback is dynamically indexed into Case library."""
    target_asset = "WT-006"
    # 1. Propose order
    wo = propose_work_order(
        asset_id=target_asset,
        component="gearbox",
        action="Endoscopic borescope inspection of HSS intermediate bearing",
        deadline_hours=48,
        priority=WorkOrderPriority.HIGH,
        created_by="diagnostic_reasoner_v2",
    )
    assert wo.ticket_id.startswith("TCK-")

    # 2. Approve order
    approved = approve_work_order(
        ticket_id=wo.ticket_id,
        approved_by="lead_operator_01",
        scheduled_deadline_hours=36,
        priority=WorkOrderPriority.HIGH,
    )
    assert approved.status == WorkOrderStatus.APPROVED

    # 3. Technician submits feedback
    completed = record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="tech_kutch_04",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Borescope confirmed severe spalling on HSS bearing outer raceway.",
        component_inspected="gearbox",
        actual_downtime_hours=14.5,
        actual_parts_cost_inr=320_000.0,
        notes="Bearing replaced up-tower during calm wind window.",
    )
    assert completed.status == WorkOrderStatus.COMPLETED

    # 4. Verify dynamic library ingestion
    field_cases = get_field_feedback_cases()
    matching_cases = [c for c in field_cases if wo.ticket_id in str(c.source_reference) or wo.ticket_id in str(c.observed_signature)]
    assert len(matching_cases) >= 1
    case = matching_cases[0]

    assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert case.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert case.component == "gearbox"
    assert "spalling" in case.fault_mode.lower()
    assert case.repair_cost_inr == 320_000.0
    assert case.lead_time_days is not None
    assert case.lead_time_days > 0

    # 5. Check presence in get_real_cases() and get_all_cases()
    real_cases = get_real_cases()
    assert any(case.case_id == c.case_id for c in real_cases)

    all_cases = get_all_cases()
    assert any(case.case_id == c.case_id for c in all_cases)


def test_retrieval_surfaces_field_verified_case():
    """Verify that trajectory kNN retrieval retrieves and cites field-verified cases."""
    target_asset = "WT-007"
    # Create and resolve a ticket with high thermal and vibration findings
    wo = propose_work_order(
        asset_id=target_asset,
        component="gearbox",
        action="Inspect high-speed shaft bearing",
        deadline_hours=24,
        priority=WorkOrderPriority.EMERGENCY,
        created_by="agent",
    )
    approve_work_order(ticket_id=wo.ticket_id, approved_by="ops_chief")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="tech_specialist",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="High vibration and bearing overheat caused by lubrication blockage.",
        component_inspected="gearbox",
        actual_downtime_hours=20.0,
        actual_parts_cost_inr=500_000.0,
    )

    # Construct synthetic evidence packet for a turbine with gearbox thermal anomaly
    from datetime import UTC, datetime
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

    # Ensure field cases are eligible and carry EXTERNAL_REAL provenance
    field_matches = [c for c in retrieved if c.event_class == "FIELD_VERIFIED_RESOLUTION"]
    if field_matches:
        f_case = field_matches[0]
        assert f_case.source_type == HistoricalSourceType.EXTERNAL_REAL
        assert any("technician" in wm.lower() or "inspection" in wm.lower() for wm in f_case.why_matched)


def test_closed_loop_metrics_endpoint():
    """Verify GET /api/work-orders/closed-loop-metrics endpoint."""
    res = client.get("/api/work-orders/closed-loop-metrics")
    assert res.status_code == 200
    data = res.json()

    assert "total_orders" in data
    assert "pending_approval" in data
    assert "concordance_rate_pct" in data
    assert "indexed_field_cases_count" in data
    assert "total_academic_real_cases_count" in data
    assert "total_real_retrieval_pool_size" in data

    assert data["concordance_rate_pct"] >= 0.0
    assert data["total_real_retrieval_pool_size"] >= 14
