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


def test_export_field_cases_retrieval():
    wo = propose_work_order("WT-005", "main_bearing", "Acoustic emission scan", 72)
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
    assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert case.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert "early_inspection_prevented_failure" in case.outcome
