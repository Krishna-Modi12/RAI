#!/usr/bin/env python3
"""Automated Production & Operational Lifecycle Verification Script.

Tests:
1. Standard Kubernetes/Docker Health Probes (/healthz, /readyz)
2. Closed-Loop Work Order Lifecycle (Propose -> Approve -> Technician Field Feedback)
3. Ground-Truth Operational Feedback Ingestion into Case Retrieval Memory
"""

import sys

from fastapi.testclient import TestClient

from rai.memory.work_orders import export_field_cases_for_retrieval
from services.api.main import app

client = TestClient(app)


def verify_probes():
    print("--> 1. Verifying Standard Health Probes...")

    # Liveness probe
    res = client.get("/healthz")
    assert res.status_code == 200, f"/healthz failed: {res.status_code}"
    data = res.json()
    assert data["status"] == "alive"
    print("    [PASS] /healthz returned 200 OK ('status': 'alive')")

    # Readiness probe
    res = client.get("/readyz")
    assert res.status_code == 200, f"/readyz failed: {res.status_code}"
    ready_data = res.json()
    assert ready_data["status"] == "ready"
    assert "telemetry_store" in ready_data["checks"]
    assert "reasoner" in ready_data["checks"]
    assert ready_data["checks"]["fleet"]["assets_configured"] == 42
    assert "work_orders" in ready_data["checks"]
    print(f"    [PASS] /readyz returned 200 OK ('status': 'ready', checks={list(ready_data['checks'].keys())})")


def verify_work_order_lifecycle():
    print("\n--> 2. Verifying Closed-Loop Work Order Lifecycle...")

    # Step A: Propose work order
    prop_payload = {
        "asset_id": "WT-004",
        "component": "pitch_system",
        "action": "Inspect pitch motor bearing lubrication and check slip rings",
        "deadline_hours": 48,
        "priority": "high",
        "created_by": "rai_agent_verification",
    }
    res = client.post("/api/work-orders/propose", json=prop_payload)
    assert res.status_code == 201, f"Propose failed: {res.status_code} {res.text}"
    ticket = res.json()
    ticket_id = ticket["ticket_id"]
    assert ticket["status"] == "proposed_awaiting_human_approval"
    assert ticket["asset_id"] == "WT-004"
    print(f"    [PASS] Work order proposed: {ticket_id} (status={ticket['status']})")

    # Step B: Operator Approve & Schedule
    act_payload = {
        "action": "approve",
        "actor": "ops_director_modi",
        "deadline_hours": 36,
        "priority": "emergency",
    }
    res = client.post(f"/api/work-orders/{ticket_id}/action", json=act_payload)
    assert res.status_code == 200, f"Approve failed: {res.status_code} {res.text}"
    approved = res.json()
    assert approved["status"] == "approved_scheduled"
    assert approved["approved_by"] == "ops_director_modi"
    assert approved["priority"] == "emergency"
    print(f"    [PASS] Work order approved: {ticket_id} (status={approved['status']}, approved_by={approved['approved_by']})")

    # Step C: Field Technician Feedback & Ground-Truth Findings
    fb_payload = {
        "technician_id": "tech_lead_patel",
        "resolution": "confirmed_fault",
        "findings": "Inspected pitch motor: high friction torque, bearing race spalling verified. Replaced motor and grease seal.",
        "component_inspected": "pitch_motor_bearing",
        "actual_downtime_hours": 3.5,
        "actual_parts_cost_inr": 42500.0,
        "notes": "Turbine test-run completed at full rated pitch speed without tracking error.",
    }
    res = client.post(f"/api/work-orders/{ticket_id}/feedback", json=fb_payload)
    assert res.status_code == 200, f"Feedback failed: {res.status_code} {res.text}"
    completed = res.json()
    assert completed["status"] == "completed"
    assert len(completed["feedback"]) >= 1
    latest_fb = completed["feedback"][-1]
    assert latest_fb["resolution"] == "confirmed_fault"
    assert latest_fb["actual_downtime_hours"] == 3.5
    assert latest_fb["actual_parts_cost_inr"] == 42500.0
    print(f"    [PASS] Ground-truth feedback logged: {ticket_id} (status={completed['status']}, resolution={latest_fb['resolution']})")

    # Step D: List and filter work orders
    res = client.get("/api/work-orders?asset_id=WT-004")
    assert res.status_code == 200
    wos = res.json()
    assert any(w["ticket_id"] == ticket_id for w in wos)
    print(f"    [PASS] /api/work-orders?asset_id=WT-004 listed {len(wos)} records successfully")


def verify_feedback_retrieval_ingestion():
    print("\n--> 3. Verifying Operational Feedback Case Ingestion...")

    field_cases = export_field_cases_for_retrieval()
    assert len(field_cases) >= 1, "Expected at least one exported field case"
    match = next((c for c in field_cases if "WT-004" in c.outcome or "WT-004" in " ".join(c.why_matched)), None)
    assert match is not None, "Exported field cases did not include verified WT-004 feedback"
    assert match.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert match.source_type.value.upper() == "EXTERNAL_REAL"
    print(f"    [PASS] Operational feedback indexed into case library: case_id={match.case_id}, source={match.source_dataset}")


def main():
    print("=" * 72)
    print("RENEWABLE ASSET INTELLIGENCE — PRODUCTION & LIFECYCLE AUDIT VERIFICATION")
    print("=" * 72)
    try:
        verify_probes()
        verify_work_order_lifecycle()
        verify_feedback_retrieval_ingestion()
        print("\n" + "=" * 72)
        print("ALL PRODUCTION READINESS CHECKS PASSED CLEANLY (0 ERRORS)")
        print("=" * 72)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
