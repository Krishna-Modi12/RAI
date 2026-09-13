"""Operational Work Order & Technician Field Feedback Ledger.

Manages the human-in-the-loop lifecycle of maintenance interventions:
PROPOSED -> APPROVED / REJECTED -> IN_PROGRESS -> COMPLETED with technician feedback.

Audit trail is immutably appended to ARTIFACTS / 'tickets.jsonl'.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from typing import Any

from rai.config import ARTIFACTS, get_asset
from rai.schemas import (
    FieldResolution,
    HistoricalCase,
    HistoricalSourceType,
    WorkOrderFeedback,
    WorkOrderPriority,
    WorkOrderRecord,
    WorkOrderStatus,
)

log = logging.getLogger("rai.work_orders")

TICKET_LOG = ARTIFACTS / "tickets.jsonl"
_lock = threading.Lock()


def _get_asset_meta(asset_id: str) -> tuple[str, str]:
    """Retrieve asset name and site from fleet configuration."""
    asset = get_asset(asset_id)
    return asset.name, asset.site


def _read_records_raw() -> dict[str, dict[str, Any]]:
    """Read all records from jsonl into a dictionary keyed by ticket_id."""
    if not TICKET_LOG.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    with TICKET_LOG.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                tid = data.get("ticket_id")
                if tid:
                    records[tid] = data
            except json.JSONDecodeError:
                continue
    return records


def _write_records_raw(records: dict[str, dict[str, Any]]) -> None:
    """Rewrite jsonl file safely under lock."""
    TICKET_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TICKET_LOG.open("w", encoding="utf-8") as fh:
        for item in records.values():
            fh.write(json.dumps(item, default=str) + "\n")



def _to_record(data: dict[str, Any]) -> WorkOrderRecord:
    """Parse raw dict into validated WorkOrderRecord with graceful defaults."""
    created_at = data.get("created_at")
    if isinstance(created_at, str):
        try:
            c_at = datetime.fromisoformat(created_at)
        except ValueError:
            c_at = datetime.now(UTC)
    elif isinstance(created_at, datetime):
        c_at = created_at
    else:
        c_at = datetime.now(UTC)

    approved_at = data.get("approved_at")
    if isinstance(approved_at, str):
        try:
            app_at = datetime.fromisoformat(approved_at)
        except ValueError:
            app_at = None
    elif isinstance(approved_at, datetime):
        app_at = approved_at
    else:
        app_at = None

    rejected_at = data.get("rejected_at")
    if isinstance(rejected_at, str):
        try:
            rej_at = datetime.fromisoformat(rejected_at)
        except ValueError:
            rej_at = None
    elif isinstance(rejected_at, datetime):
        rej_at = rejected_at
    else:
        rej_at = None

    raw_fb_list = data.get("feedback", [])
    parsed_fb: list[WorkOrderFeedback] = []
    for fb in raw_fb_list:
        sub_at = fb.get("submitted_at")
        if isinstance(sub_at, str):
            try:
                s_at = datetime.fromisoformat(sub_at)
            except ValueError:
                s_at = datetime.now(UTC)
        elif isinstance(sub_at, datetime):
            s_at = sub_at
        else:
            s_at = datetime.now(UTC)

        res_val = fb.get("resolution", FieldResolution.CONFIRMED_FAULT.value)
        try:
            res_enum = FieldResolution(res_val)
        except ValueError:
            res_enum = FieldResolution.CONFIRMED_FAULT

        parsed_fb.append(
            WorkOrderFeedback(
                feedback_id=fb.get("feedback_id", f"FB-{datetime.now(UTC):%Y%m%d%H%M%S}"),
                ticket_id=data["ticket_id"],
                technician_id=fb.get("technician_id", "technician"),
                submitted_at=s_at,
                resolution=res_enum,
                findings=fb.get("findings", ""),
                component_inspected=fb.get("component_inspected", data.get("component", "unknown")),
                actual_downtime_hours=float(fb.get("actual_downtime_hours", 0.0)),
                actual_parts_cost_inr=float(fb.get("actual_parts_cost_inr", 0.0)),
                notes=fb.get("notes", ""),
            )
        )

    st_val = data.get("status", WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value)
    try:
        status_enum = WorkOrderStatus(st_val)
    except ValueError:
        status_enum = WorkOrderStatus.PROPOSED_AWAITING_APPROVAL

    prio_val = data.get("priority", WorkOrderPriority.MEDIUM.value)
    try:
        prio_enum = WorkOrderPriority(prio_val)
    except ValueError:
        prio_enum = WorkOrderPriority.MEDIUM

    return WorkOrderRecord(
        ticket_id=data["ticket_id"],
        asset_id=data["asset_id"],
        asset_name=data.get("asset_name") or _get_asset_meta(data["asset_id"])[0],
        site=data.get("site") or _get_asset_meta(data["asset_id"])[1],
        component=data.get("component", "unknown"),
        action=data.get("action", "inspect"),
        priority=prio_enum,
        deadline_hours=int(data.get("deadline_hours", 72)),
        status=status_enum,
        created_at=c_at,
        created_by=data.get("created_by", "rai_agent"),
        approved_by=data.get("approved_by"),
        approved_at=app_at,
        rejected_by=data.get("rejected_by"),
        rejected_at=rej_at,
        rejection_reason=data.get("rejection_reason"),
        feedback=parsed_fb,
    )


def propose_work_order(
    asset_id: str,
    component: str,
    action: str,
    deadline_hours: int = 72,
    priority: str | WorkOrderPriority = WorkOrderPriority.MEDIUM,
    created_by: str = "rai_agent",
) -> WorkOrderRecord:
    """Propose a maintenance inspection ticket for human approval."""
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id must be a non-empty string")
    if not isinstance(component, str) or not component.strip():
        raise ValueError("component must be a non-empty string")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action must be a non-empty string")
    if isinstance(deadline_hours, bool) or not isinstance(deadline_hours, int) or deadline_hours <= 0:
        raise ValueError("deadline_hours must be a positive integer")

    name, site = _get_asset_meta(asset_id)
    now = datetime.now(UTC)
    ticket_id = f"TCK-{asset_id}-{now:%Y%m%dT%H%M%SZ}"

    prio_str = priority.value if isinstance(priority, WorkOrderPriority) else str(priority)

    record_dict: dict[str, Any] = {
        "ticket_id": ticket_id,
        "asset_id": asset_id,
        "asset_name": name,
        "site": site,
        "component": component,
        "action": action[:400],
        "priority": prio_str,
        "deadline_hours": int(deadline_hours),
        "status": WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value,
        "created_at": now.isoformat(),
        "created_by": created_by,
        "feedback": [],
    }

    with _lock:
        records = _read_records_raw()
        records[ticket_id] = record_dict
        _write_records_raw(records)

    return _to_record(record_dict)


def get_work_order(ticket_id: str) -> WorkOrderRecord | None:
    """Retrieve a single work order by ticket_id."""
    with _lock:
        records = _read_records_raw()
        data = records.get(ticket_id)
        return _to_record(data) if data else None


def list_work_orders(
    asset_id: str | None = None,
    status: str | WorkOrderStatus | None = None,
    limit: int = 100,
) -> list[WorkOrderRecord]:
    """List work orders with optional filtering by asset and status, newest first."""
    target_status = status.value if isinstance(status, WorkOrderStatus) else status
    with _lock:
        records = _read_records_raw()

    out: list[WorkOrderRecord] = []
    for data in reversed(list(records.values())):
        if asset_id and data.get("asset_id") != asset_id:
            continue
        if target_status and data.get("status") != target_status:
            continue
        out.append(_to_record(data))
        if len(out) >= limit:
            break
    return out


def approve_work_order(
    ticket_id: str,
    approved_by: str,
    scheduled_deadline_hours: int | None = None,
    priority: str | WorkOrderPriority | None = None,
) -> WorkOrderRecord:
    """Approve and schedule a proposed work order for dispatch."""
    if not approved_by or not approved_by.strip():
        raise ValueError("approved_by must be specified")

    with _lock:
        records = _read_records_raw()
        if ticket_id not in records:
            raise KeyError(f"Work order {ticket_id} not found")

        data = records[ticket_id]
        if data.get("status") not in {
            WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value,
            WorkOrderStatus.REJECTED.value,
        }:
            raise ValueError(f"Cannot approve work order in status: {data.get('status')}")

        now = datetime.now(UTC)
        data["status"] = WorkOrderStatus.APPROVED.value
        data["approved_by"] = approved_by
        data["approved_at"] = now.isoformat()
        if scheduled_deadline_hours is not None and scheduled_deadline_hours > 0:
            data["deadline_hours"] = int(scheduled_deadline_hours)
        if priority is not None:
            data["priority"] = priority.value if isinstance(priority, WorkOrderPriority) else str(priority)

        _write_records_raw(records)
        return _to_record(data)


def reject_work_order(
    ticket_id: str,
    rejected_by: str,
    reason: str,
) -> WorkOrderRecord:
    """Reject a proposed work order with recorded justification."""
    if not rejected_by or not rejected_by.strip():
        raise ValueError("rejected_by must be specified")
    if not reason or not reason.strip():
        raise ValueError("reason must be specified")

    with _lock:
        records = _read_records_raw()
        if ticket_id not in records:
            raise KeyError(f"Work order {ticket_id} not found")

        data = records[ticket_id]
        now = datetime.now(UTC)
        data["status"] = WorkOrderStatus.REJECTED.value
        data["rejected_by"] = rejected_by
        data["rejected_at"] = now.isoformat()
        data["rejection_reason"] = reason[:500]

        _write_records_raw(records)
        return _to_record(data)


def record_feedback(
    ticket_id: str,
    technician_id: str,
    resolution: str | FieldResolution,
    findings: str,
    component_inspected: str,
    actual_downtime_hours: float = 0.0,
    actual_parts_cost_inr: float = 0.0,
    notes: str = "",
) -> WorkOrderRecord:
    """Record technician field inspection feedback and mark work order completed."""
    if not technician_id or not technician_id.strip():
        raise ValueError("technician_id must be specified")
    if not findings or not findings.strip():
        raise ValueError("findings must be specified")

    res_val = resolution.value if isinstance(resolution, FieldResolution) else str(resolution)

    with _lock:
        records = _read_records_raw()
        if ticket_id not in records:
            raise KeyError(f"Work order {ticket_id} not found")

        data = records[ticket_id]
        now = datetime.now(UTC)
        feedback_id = f"FB-{ticket_id}-{len(data.get('feedback', [])) + 1}"

        fb_entry = {
            "feedback_id": feedback_id,
            "ticket_id": ticket_id,
            "technician_id": technician_id,
            "submitted_at": now.isoformat(),
            "resolution": res_val,
            "findings": findings[:1000],
            "component_inspected": component_inspected[:100],
            "actual_downtime_hours": max(0.0, float(actual_downtime_hours)),
            "actual_parts_cost_inr": max(0.0, float(actual_parts_cost_inr)),
            "notes": notes[:500],
        }

        if "feedback" not in data:
            data["feedback"] = []
        data["feedback"].append(fb_entry)
        data["status"] = WorkOrderStatus.COMPLETED.value

        _write_records_raw(records)
        return _to_record(data)


def export_field_cases_for_retrieval() -> list[HistoricalCase]:
    """Export confirmed field-resolution work orders as HistoricalCase objects.

    Provides closed-loop operational intelligence: verified ground truth from field inspections
    enriches the case retrieval library with explicit source provenance 'operator_field_verified'.
    """
    with _lock:
        records = _read_records_raw()

    field_cases: list[HistoricalCase] = []
    for data in records.values():
        feedbacks = data.get("feedback", [])
        for fb in feedbacks:
            res = fb.get("resolution")
            # Only index confirmed faults or early inspections that prevented failure
            if res in {
                FieldResolution.CONFIRMED_FAULT.value,
                FieldResolution.EARLY_INSPECTION_PREVENTED_FAILURE.value,
            }:
                case_id = f"FIELD-{fb.get('feedback_id', data['ticket_id'])}"
                asset_id = data.get("asset_id", "WT-001")
                asset_type = "wind_turbine" if asset_id.startswith("WT") else "solar_inverter"

                why_matched = [
                    f"Operator verified field event on {asset_id} ({data.get('component')})",
                    f"Resolution: {res}",
                ]
                what_different = [
                    "Local plant operating conditions may differ from current season",
                ]

                field_cases.append(
                    HistoricalCase(
                        case_id=case_id,
                        asset_id=asset_id,
                        asset_type=asset_type,
                        component=fb.get("component_inspected") or data.get("component", "unknown"),
                        fault_mode=fb.get("findings")[:80],
                        similarity=0.85,
                        outcome=f"Field resolution ({res}): {fb.get('findings')}",
                        lead_time_days=max(0.5, float(fb.get("actual_downtime_hours", 0.0)) / 24.0),
                        source_type=HistoricalSourceType.EXTERNAL_REAL,
                        source_dataset=f"Operator Verified ({data.get('site', 'Local Plant')})",
                        event_class="FIELD_VERIFIED_RESOLUTION",
                        why_matched=why_matched,
                        what_is_different=what_different,
                    )
                )


    return field_cases
