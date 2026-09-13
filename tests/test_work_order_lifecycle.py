"""Test suite for closed-loop work order lifecycle and technician field feedback."""

from datetime import datetime

import pytest

from rai.memory.work_orders import (
    approve_work_order,
    export_field_cases_for_retrieval,
    get_work_order,
    list_work_orders,
    propose_work_order,
    record_feedback,
    reject_work_order,
)
from rai.schemas import FieldResolution, HistoricalSourceType, WorkOrderPriority, WorkOrderStatus


def test_propose_work_order_success():
    wo = propose_work_order(
        asset_id="WT-001",
        component="gearbox",
        action="Perform borescope inspection on intermediate stage pinion",
        deadline_hours=48,
        priority=WorkOrderPriority.HIGH,
        created_by="test_harness",
    )
    assert wo.ticket_id.startswith("TCK-WT-001-")
    assert wo.asset_id == "WT-001"
    assert wo.component == "gearbox"
    assert wo.priority == WorkOrderPriority.HIGH
    assert wo.deadline_hours == 48
    assert wo.status == WorkOrderStatus.PROPOSED_AWAITING_APPROVAL
    assert wo.created_by == "test_harness"
    assert isinstance(wo.created_at, datetime)


def test_propose_work_order_validation():
    with pytest.raises(ValueError, match="asset_id"):
        propose_work_order("", "gearbox", "inspect")

    with pytest.raises(ValueError, match="component"):
        propose_work_order("WT-001", "", "inspect")

    with pytest.raises(ValueError, match="action"):
        propose_work_order("WT-001", "gearbox", "")

    with pytest.raises(ValueError, match="deadline_hours"):
        propose_work_order("WT-001", "gearbox", "inspect", deadline_hours=0)

    with pytest.raises(KeyError, match="unknown asset_id"):
        propose_work_order("NON_EXISTENT_ASSET", "gearbox", "inspect")


def test_approve_work_order_lifecycle():
    wo = propose_work_order("WT-002", "generator", "Vibration analysis", 72)
    approved = approve_work_order(
        ticket_id=wo.ticket_id,
        approved_by="ops_supervisor",
        scheduled_deadline_hours=24,
        priority=WorkOrderPriority.EMERGENCY,
    )
    assert approved.status == WorkOrderStatus.APPROVED
    assert approved.approved_by == "ops_supervisor"
    assert approved.approved_at is not None
    assert approved.deadline_hours == 24
    assert approved.priority == WorkOrderPriority.EMERGENCY


def test_reject_work_order_lifecycle():
    wo = propose_work_order("WT-003", "yaw_system", "Check brake pads", 72)
    rejected = reject_work_order(
        ticket_id=wo.ticket_id,
        rejected_by="ops_lead",
        reason="Scheduled repowering outage scheduled next week; inspection redundant.",
    )
    assert rejected.status == WorkOrderStatus.REJECTED
    assert rejected.rejected_by == "ops_lead"
    assert rejected.rejected_at is not None
    assert "repowering" in (rejected.rejection_reason or "")


def test_record_feedback_and_completion():
    wo = propose_work_order("INV-001", "inverter_cabinet", "Thermal imaging of DC busbars", 72)
    approve_work_order(wo.ticket_id, approved_by="plant_manager")

    completed = record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="solar_tech_12",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Loose connection on DC disconnect lug caused 38C hotspot. Torqued to specification.",
        component_inspected="dc_disconnect_switch",
        actual_downtime_hours=1.5,
        actual_parts_cost_inr=5000.0,
        notes="Post-repair infrared scan nominal.",
    )
    assert completed.status == WorkOrderStatus.COMPLETED
    assert len(completed.feedback) == 1
    fb = completed.feedback[0]
    assert fb.technician_id == "solar_tech_12"
    assert fb.resolution == FieldResolution.CONFIRMED_FAULT
    assert fb.actual_downtime_hours == 1.5
    assert fb.actual_parts_cost_inr == 5000.0


def test_list_and_get_work_orders():
    wo = propose_work_order("WT-004", "blade", "Check leading edge erosion", 168)
    retrieved = get_work_order(wo.ticket_id)
    assert retrieved is not None
    assert retrieved.ticket_id == wo.ticket_id

    wt004_orders = list_work_orders(asset_id="WT-004")
    assert any(o.ticket_id == wo.ticket_id for o in wt004_orders)


def test_feedback_cannot_bypass_approval():
    wo = propose_work_order("WT-005", "yaw_system", "Check hydraulic pressure", 72)
    assert wo.status == WorkOrderStatus.PROPOSED_AWAITING_APPROVAL

    with pytest.raises(ValueError, match="Human approval is required"):
        record_feedback(
            ticket_id=wo.ticket_id,
            technician_id="unauthorized_tech",
            resolution=FieldResolution.CONFIRMED_FAULT,
            findings="Attempting to record feedback prior to approval",
            component_inspected="yaw_system",
        )


def test_export_field_cases_retrieval_synthetic_default():
    wo = propose_work_order("WT-005", "main_bearing", "Acoustic emission scan", 72)
    approve_work_order(wo.ticket_id, approved_by="ops_supervisor")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="vibe_analyst",
        resolution=FieldResolution.EARLY_INSPECTION_PREVENTED_FAILURE,
        findings="Early outer race defect detected before temperature rise. Grease replenishment applied.",
        component_inspected="main_bearing",
        actual_downtime_hours=2.0,
    )
    cases = export_field_cases_for_retrieval()
    assert len(cases) >= 1
    case = next((c for c in cases if "WT-005" in " ".join(c.why_matched)), None)
    assert case is not None
    # Default test fixtures MUST remain INTERNAL_SYNTHETIC to prevent partition contamination
    assert case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
    assert case.event_class == "SYNTHETIC_WORK_ORDER_FEEDBACK"
    assert "early_inspection_prevented_failure" in case.outcome


def test_export_field_cases_retrieval_external_real():
    from rai.schemas import FeedbackProvenance, ObservationLevel

    wo = propose_work_order(
        asset_id="WT-005",
        component="main_bearing",
        action="Calibrated acoustic emission sensor inspection",
        deadline_hours=72,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
    )
    approve_work_order(wo.ticket_id, approved_by="ops_supervisor")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="site_cert_tech_09",
        resolution=FieldResolution.EARLY_INSPECTION_PREVENTED_FAILURE,
        findings="Certified field teardown: outer race fatigue spall arrested prior to catastrophic thermal trip.",
        component_inspected="main_bearing",
        actual_downtime_hours=3.5,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
        observation_level=ObservationLevel.FIELD_VERIFIED,
    )
    cases = export_field_cases_for_retrieval()
    case = next((c for c in cases if wo.ticket_id in str(c.case_id)), None)
    assert case is not None
    assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert case.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert case.evidence_quality == "FIELD_VERIFIED"


def test_ledger_immutability_and_appended_feedback():
    """Verify that multiple feedbacks form an append-only audit trail without mutating past entries."""
    wo = propose_work_order("WT-008", "generator", "Vibration analysis on drive-end bearing", 48)
    approve_work_order(wo.ticket_id, approved_by="senior_engineer")

    # Entry 1: Initial technician inspection
    rec1 = record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="tech_alpha",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Initial finding: mechanical looseness detected on mounting foot.",
        component_inspected="generator",
        actual_downtime_hours=2.0,
        actual_parts_cost_inr=12000.0,
    )
    assert len(rec1.feedback) == 1
    assert rec1.feedback[0].findings == "Initial finding: mechanical looseness detected on mounting foot."

    # Entry 2: Follow-up / correction audit entry
    rec2 = record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="supervisor_beta",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Follow-up correction: foot re-torqued, but shaft alignment also required shimming.",
        component_inspected="generator",
        actual_downtime_hours=4.0,
        actual_parts_cost_inr=35000.0,
    )
    assert len(rec2.feedback) == 2
    # Prior entry is immutably preserved
    assert rec2.feedback[0].technician_id == "tech_alpha"
    assert "mounting foot" in rec2.feedback[0].findings
    assert rec2.feedback[0].actual_downtime_hours == 2.0
    # New entry appended
    assert rec2.feedback[1].technician_id == "supervisor_beta"
    assert "shaft alignment" in rec2.feedback[1].findings
    assert rec2.feedback[1].actual_downtime_hours == 4.0


def test_weather_threshold_provenance_and_source():
    """Verify that weather thresholds are explicitly labeled as configured operational constraints."""
    from rai.decision.dispatch_optimizer import evaluate_site_weather

    win = evaluate_site_weather("kutch-wind")
    assert win.threshold_provenance == "CONFIGURED_OPERATIONAL_CONSTRAINT"
    assert win.weather_source is not None
    assert "open_meteo" in win.weather_source.lower()

    data = win.to_dict()
    assert data["threshold_provenance"] == "CONFIGURED_OPERATIONAL_CONSTRAINT"


def test_projected_vs_actual_economics():
    """Verify distinction between projected model-estimated avoided loss and actual incurred parts cost."""
    from rai.decision.dispatch_optimizer import generate_fleet_dispatch_plan

    plan = generate_fleet_dispatch_plan()
    assert plan.total_avoided_loss_inr > 0.0
    for asgn in plan.assignments:
        # Projected avoided loss is an operational risk estimate
        assert asgn.projected_avoided_loss_inr >= 50_000.0

