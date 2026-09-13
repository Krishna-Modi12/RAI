"""Operational Work Order & Feedback Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rai.memory.work_orders import (
    approve_work_order,
    get_work_order,
    list_work_orders,
    propose_work_order,
    record_feedback,
    reject_work_order,
)
from rai.schemas import FieldResolution, WorkOrderPriority, WorkOrderStatus

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


class ProposeRequest(BaseModel):
    asset_id: str
    component: str
    action: str
    deadline_hours: int = 72
    priority: WorkOrderPriority = WorkOrderPriority.MEDIUM
    created_by: str = "operator"


class ActionRequest(BaseModel):
    action: str = Field(description="'approve' or 'reject'")
    actor: str = Field(description="Operator name or ID")
    deadline_hours: int | None = None
    priority: WorkOrderPriority | None = None
    reason: str | None = Field(default=None, description="Required when action is 'reject'")


class FeedbackRequest(BaseModel):
    technician_id: str
    resolution: FieldResolution
    findings: str
    component_inspected: str | None = None
    actual_downtime_hours: float = 0.0
    actual_parts_cost_inr: float = 0.0
    notes: str = ""


@router.get("")
def get_work_orders(
    asset_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List operational work orders with optional filtering by asset or status."""
    st = None
    if status:
        try:
            st = WorkOrderStatus(status)
        except ValueError:
            st = status  # allow raw string comparison in list_work_orders

    orders = list_work_orders(asset_id=asset_id, status=st, limit=limit)
    return [o.model_dump(mode="json") for o in orders]


@router.get("/dispatch-plan")
def get_dispatch_plan(crews_per_site: int = 2) -> dict[str, Any]:
    """Get the optimized fleet crew dispatch plan considering site weather safety windows."""
    from rai.decision.dispatch_optimizer import generate_fleet_dispatch_plan

    plan = generate_fleet_dispatch_plan(crews_per_site=crews_per_site)
    return plan.to_dict()


@router.get("/closed-loop-metrics")
def get_closed_loop_metrics() -> dict[str, Any]:
    """Aggregate fleet-wide closed-loop maintenance and technician concordance metrics."""
    from rai.memory.library import get_field_feedback_cases
    from rai.memory.real_corpus import get_real_cases
    from rai.memory.work_orders import FieldResolution

    all_orders = list_work_orders(limit=1000)

    total_orders = len(all_orders)
    pending_approval = sum(
        1 for o in all_orders if getattr(o.status, "value", o.status) == WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value
    )
    approved = sum(
        1 for o in all_orders if getattr(o.status, "value", o.status) == WorkOrderStatus.APPROVED.value
    )
    in_progress = sum(
        1 for o in all_orders if getattr(o.status, "value", o.status) == WorkOrderStatus.IN_PROGRESS.value
    )
    completed = sum(
        1 for o in all_orders if getattr(o.status, "value", o.status) == WorkOrderStatus.COMPLETED.value
    )
    rejected = sum(
        1 for o in all_orders if getattr(o.status, "value", o.status) == WorkOrderStatus.REJECTED.value
    )

    feedbacks = [fb for o in all_orders for fb in getattr(o, "feedback", [])]
    total_feedbacks = len(feedbacks)
    confirmed_faults = sum(
        1
        for fb in feedbacks
        if getattr(getattr(fb, "resolution", None), "value", getattr(fb, "resolution", None))
        in {
            FieldResolution.CONFIRMED_FAULT.value,
            FieldResolution.EARLY_INSPECTION_PREVENTED_FAILURE.value,
        }
    )

    concordance_pct = (
        round((confirmed_faults / total_feedbacks) * 100.0, 1)
        if total_feedbacks > 0
        else 100.0
    )

    field_cases = get_field_feedback_cases()
    academic_cases = get_real_cases()

    total_parts_cost = sum(
        float(getattr(fb, "parts_cost_inr", 0.0) or 0.0) for fb in feedbacks
    )
    total_downtime = sum(
        float(getattr(fb, "actual_downtime_hours", 0.0) or 0.0) for fb in feedbacks
    )
    mean_downtime = (
        round(total_downtime / total_feedbacks, 1) if total_feedbacks > 0 else 0.0
    )

    return {
        "total_orders": total_orders,
        "pending_approval": pending_approval,
        "approved": approved,
        "in_progress": in_progress,
        "completed": completed,
        "rejected": rejected,
        "total_feedbacks": total_feedbacks,
        "confirmed_faults": confirmed_faults,
        "concordance_rate_pct": concordance_pct,
        "indexed_field_cases_count": len(field_cases),
        "total_academic_real_cases_count": max(0, len(academic_cases) - len(field_cases)),
        "total_real_retrieval_pool_size": len(academic_cases),
        "total_parts_cost_inr": total_parts_cost,
        "total_downtime_hours": total_downtime,
        "mean_downtime_hours": mean_downtime,
    }


@router.get("/{ticket_id}")
def get_single_work_order(ticket_id: str) -> dict[str, Any]:
    """Retrieve a single operational work order by ticket_id."""
    wo = get_work_order(ticket_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {ticket_id} not found")
    return wo.model_dump(mode="json")


@router.post("/propose", status_code=201)
def create_proposal(req: ProposeRequest) -> dict[str, Any]:
    """Propose a new maintenance work order."""
    try:
        record = propose_work_order(
            asset_id=req.asset_id,
            component=req.component,
            action=req.action,
            deadline_hours=req.deadline_hours,
            priority=req.priority,
            created_by=req.created_by,
        )
        return record.model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{ticket_id}/action")
def action_work_order(ticket_id: str, req: ActionRequest) -> dict[str, Any]:
    """Approve or reject a proposed work order."""
    act = req.action.lower().strip()
    try:
        if act == "approve":
            record = approve_work_order(
                ticket_id=ticket_id,
                approved_by=req.actor,
                scheduled_deadline_hours=req.deadline_hours,
                priority=req.priority,
            )
            return record.model_dump(mode="json")
        elif act == "reject":
            if not req.reason:
                raise HTTPException(status_code=400, detail="Rejection requires a non-empty reason")
            record = reject_work_order(
                ticket_id=ticket_id,
                rejected_by=req.actor,
                reason=req.reason,
            )
            return record.model_dump(mode="json")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{req.action}'. Allowed: 'approve', 'reject'",
            )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{ticket_id}/feedback")
def submit_feedback(ticket_id: str, req: FeedbackRequest) -> dict[str, Any]:
    """Record technician ground-truth inspection findings."""
    try:
        record = record_feedback(
            ticket_id=ticket_id,
            technician_id=req.technician_id,
            resolution=req.resolution,
            findings=req.findings,
            component_inspected=req.component_inspected or "general",
            actual_downtime_hours=req.actual_downtime_hours,
            actual_parts_cost_inr=req.actual_parts_cost_inr,
            notes=req.notes,
        )
        return record.model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
