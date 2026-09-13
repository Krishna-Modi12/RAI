"""Tests for Fleet Crew Dispatch and Weather Safety Window Optimizer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from rai.decision.dispatch_optimizer import (
    WeatherSafetyStatus,
    evaluate_site_weather,
    generate_fleet_dispatch_plan,
)
from rai.memory.work_orders import (
    WorkOrderPriority,
    approve_work_order,
    propose_work_order,
)
from services.api.main import app

client = TestClient(app)


def test_evaluate_site_weather_wind():
    """Verify meteorological safety evaluation for wind farm site."""
    win = evaluate_site_weather("kutch-wind")
    assert win.site == "kutch-wind"
    assert win.asset_type == "wind_turbine"
    assert win.current_wind_speed_ms >= 0.0
    assert win.safe_window_hours >= 0.0
    assert win.status in {WeatherSafetyStatus.SAFE, WeatherSafetyStatus.MARGINAL, WeatherSafetyStatus.UNSAFE}
    assert len(win.safety_rationale) > 0


def test_evaluate_site_weather_solar():
    """Verify meteorological safety evaluation for solar park site."""
    win = evaluate_site_weather("charanka-solar")
    assert win.site == "charanka-solar"
    assert win.asset_type == "solar_inverter"
    assert win.current_ambient_temp_c is not None
    assert win.safe_window_hours >= 0.0
    assert win.status in {WeatherSafetyStatus.SAFE, WeatherSafetyStatus.MARGINAL, WeatherSafetyStatus.UNSAFE}
    assert len(win.safety_rationale) > 0


def test_generate_fleet_dispatch_plan_prioritization():
    """Verify crew dispatch planning, prioritizing emergency/high items and calculating avoided loss."""
    # Propose and approve an emergency order
    wo1 = propose_work_order(
        asset_id="WT-006",
        component="gearbox",
        action="Emergency gearbox endoscope inspection",
        deadline_hours=12,
        priority=WorkOrderPriority.EMERGENCY,
        created_by="test_harness",
    )
    approve_work_order(ticket_id=wo1.ticket_id, approved_by="dispatch_lead")

    propose_work_order(
        asset_id="INV-008",
        component="inverter",
        action="Routine filter and IGBT check",
        deadline_hours=96,
        priority=WorkOrderPriority.LOW,
        created_by="test_harness",
    )

    plan = generate_fleet_dispatch_plan(crews_per_site=2)

    assert plan.generated_at is not None
    assert "kutch-wind" in plan.site_windows
    assert "charanka-solar" in plan.site_windows
    assert plan.active_crews_count == 4
    assert plan.total_avoided_loss_inr > 0

    # Ensure assignments exist and the emergency order is scheduled
    assigned_tickets = [a.ticket_id for a in plan.assignments]
    assert wo1.ticket_id in assigned_tickets

    # Emergency order on WT-006 should be scheduled with READY_IMMEDIATE (if safe) or AWAITING_WEATHER_WINDOW
    wt_assignment = next(a for a in plan.assignments if a.ticket_id == wo1.ticket_id)
    assert wt_assignment.priority == "emergency"
    assert wt_assignment.projected_avoided_loss_inr >= 1_000_000.0


def test_dispatch_plan_api_endpoint():
    """Verify GET /api/work-orders/dispatch-plan endpoint returns valid plan."""
    res = client.get("/api/work-orders/dispatch-plan?crews_per_site=2")
    assert res.status_code == 200
    data = res.json()

    assert "generated_at" in data
    assert "site_windows" in data
    assert "assignments" in data
    assert "active_crews_count" in data
    assert data["active_crews_count"] == 4
    assert "total_avoided_loss_inr" in data
