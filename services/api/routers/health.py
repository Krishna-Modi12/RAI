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


@router.get("/healthz", tags=["probes"])
def liveness_probe() -> dict[str, str]:
    """Standard Kubernetes/Docker liveness probe."""
    return {"status": "alive", "service": "renewable-asset-intelligence"}


@router.get("/readyz", tags=["probes"])
def readiness_probe() -> dict[str, Any]:
    """Standard Kubernetes/Docker readiness probe checking core subsystems."""
    checks: dict[str, Any] = {}
    is_ready = True

    # 1. Telemetry store check
    try:
        extent = data_extent()
        checks["telemetry_store"] = {
            "status": "ok",
            "start": extent[0].isoformat() if extent else None,
            "end": extent[1].isoformat() if extent else None,
        }
    except Exception as e:
        checks["telemetry_store"] = {"status": "degraded", "error": str(e)}

    # 2. Agent & Reasoner capabilities
    try:
        cap = probe_capabilities()
        checks["reasoner"] = {
            "status": "ok",
            "needle": cap.needle,
            "evidence": cap.evidence,
        }
    except Exception as e:
        checks["reasoner"] = {"status": "degraded", "error": str(e)}

    # 3. Fleet configuration
    checks["fleet"] = {
        "status": "ok" if len(FLEET) == 42 else "unexpected_count",
        "assets_configured": len(FLEET),
    }

    # 4. Work order ledger check
    try:
        from rai.memory.work_orders import TICKET_LOG

        checks["work_orders"] = {
            "status": "ok",
            "path": str(TICKET_LOG),
            "exists": TICKET_LOG.exists(),
        }
    except Exception as e:
        checks["work_orders"] = {"status": "degraded", "error": str(e)}

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }

