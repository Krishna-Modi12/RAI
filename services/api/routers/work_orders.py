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
