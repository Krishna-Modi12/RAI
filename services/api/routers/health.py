"""Health endpoint complying with docs/API_CONTRACT.md."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from rai.agent.interfaces import probe_capabilities
from rai.config import FLEET
from rai.store.telemetry import data_extent

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def get_health() -> dict[str, Any]:
    cap = probe_capabilities()

    try:
        extent = data_extent()
        data_as_of = extent[1].isoformat().replace("+00:00", "Z") if extent else datetime.now(UTC).isoformat().replace("+00:00", "Z")
    except Exception:
        data_as_of = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    return {
        "status": "ok",
        "version": "0.1.0",
        "data_as_of": data_as_of,
        "needle_available": cap.needle,
        "needle_detail": cap.detail.get("needle", "deterministic reasoner active"),
        "models_loaded": ["wind_expected_power", "solar_expected_power", "risk"],
        "assets": len(FLEET),
    }
