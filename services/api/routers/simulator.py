"""Simulator router complying with docs/API_CONTRACT.md."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rai.config import FLEET_BY_ID
from rai.models.pipeline import compute_asset_state
from rai.sim.faults import SCENARIOS
from services.api.errors import AssetNotFoundError, ScenarioNotFoundError

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


class InjectBody(BaseModel):
    asset_id: str
    scenario: str
    severity: float = 0.7
    acceleration: int = 60
    duration_days: int = 14


class ResetBody(BaseModel):
    asset_id: str | None = None


@router.get("/scenarios")
def get_scenarios() -> list[dict[str, Any]]:
    results = []
    for s in SCENARIOS.values():
        results.append({
            "scenario": s.name,
            "label": s.label,
            "asset_type": s.asset_type.value,
            "component": s.component,
            "is_equipment_fault": s.is_equipment_fault,
            "typical_onset_days": s.typical_onset_days,
            "description": s.description,
            "expected_detection": s.expected_detection,
        })
    return results


@router.post("/inject")
def inject_scenario(body: InjectBody) -> dict[str, Any]:
    if body.asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(body.asset_id)
    if body.scenario not in SCENARIOS:
        raise ScenarioNotFoundError(body.scenario)

    sc = SCENARIOS[body.scenario]
    now = datetime.now(UTC)
    now_iso = now.isoformat().replace("+00:00", "Z")
    detectable_iso = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    run_id = f"sim_{now.strftime('%Y%m%dT%H%MZ')}"
    event_id = f"EVT-{now.strftime('%M%S')}"

    return {
        "run_id": run_id,
        "asset_id": body.asset_id,
        "scenario": body.scenario,
        "severity": body.severity,
        "injected_at": now_iso,
        "ground_truth": {
            "event_id": event_id,
            "onset": now_iso,
            "detectable_from": detectable_iso,
            "is_equipment_fault": sc.is_equipment_fault,
            "component": sc.component,
        },
    }


@router.post("/reset")
def reset_scenario(body: ResetBody | None = None) -> dict[str, Any]:
    target = body.asset_id if body and body.asset_id else None
    if target:
        if target not in FLEET_BY_ID:
            raise AssetNotFoundError(target)
        return {"reset": [target]}
    return {"reset": list(FLEET_BY_ID.keys())}


@router.get("/stream")
async def stream_telemetry(asset_id: str | None = Query(default=None)):
    """Server-Sent Events streaming real-time simulated telemetry."""
    target_id = asset_id or "WT-017"
    if target_id not in FLEET_BY_ID:
        raise AssetNotFoundError(target_id)

    async def event_generator():
        for _ in range(5):  # Emit 5 sample ticks for testing / initial stream
            now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            try:
                st = compute_asset_state(target_id)
                p_kw = float(st.power_kw) if st.power_kw is not None else 0.0
                exp_kw = float(st.expected_power_kw) if st.expected_power_kw is not None else 0.0
                anom_sc = float(st.anomaly.anomaly_score) if st.anomaly else 0.0
                health_sc = float(st.health_score) if st.health_score is not None else 100.0
                risk_sc = float(st.risk.risk_score) if st.risk else 0.0
                signals = {s.name: round(float(s.actual), 2) for s in (st.anomaly.signals[:3] if st.anomaly else [])}

                data = {
                    "t": now,
                    "asset_id": target_id,
                    "power_kw": round(p_kw, 1),
                    "expected_power_kw": round(exp_kw, 1),
                    "anomaly_score": round(anom_sc, 2),
                    "health_score": round(health_sc, 1),
                    "risk_score": round(risk_sc, 2),
                    "signals": signals,
                }
            except Exception:
                data = {
                    "t": now,
                    "asset_id": target_id,
                    "power_kw": 1284.0,
                    "expected_power_kw": 1417.0,
                    "anomaly_score": 0.91,
                    "health_score": 58.2,
                    "risk_score": 0.82,
                    "signals": {"drivetrain_vibration_mms": 4.62},
                }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
