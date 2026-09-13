"""Fleet overview and priority queue endpoints complying with docs/API_CONTRACT.md."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from rai.config import FLEET
from rai.economics.engine import do_nothing_exposure
from rai.models.pipeline import compute_asset_state
from rai.schemas import AssetType, RiskBand
from rai.store import DataUnavailable
from rai.store.state import load_all_asset_states, save_asset_state

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["fleet"])

# Horizon for the fleet-level summary figure. Matches RiskAssessment's own default
# horizon_days (rai/schemas.py) rather than an invented number.
FLEET_SUMMARY_HORIZON_DAYS = 30

# Horizon for the per-asset priority queue figure. Matches this endpoint's existing,
# already-documented framing (docs/API_CONTRACT.md, deadline_hours below).
PRIORITY_QUEUE_HORIZON_DAYS = 14


def _component_for(dominant_signal: str | None, asset_type: AssetType) -> str:
    """Map a dominant anomaly signal to a COMPONENT_ECONOMICS key.

    Mirrors the mapping used to build the priority queue's headline/recommended_action so the
    exposure estimate and the displayed narrative are always costing the same component.
    """
    dominant = dominant_signal or ""
    if "gearbox" in dominant or "vibration" in dominant:
        return "gearbox"
    return "inverter" if asset_type == AssetType.SOLAR_INVERTER else "generator"


def _expected_consequence_inr(st, horizon_days: int) -> float | None:
    """Expected cost of leaving `st` unaddressed for `horizon_days`.

    Uses rai.economics.engine.do_nothing_exposure — the validated engine already built for
    exactly this purpose (see its docstring) — rather than the instantaneous
    `expected_power_kw - power_kw` proxy this endpoint used previously, which read exactly ₹0
    whenever current output wasn't below baseline even for assets flagged critical by other
    signals (thermal/vibration residuals). This is driven by the calibrated risk score and the
    component's cost table, not by the asset's current power deficit, so it stays non-zero for
    a genuinely high-risk asset regardless of what its output looks like at this instant.
    Returns None (not a fabricated 0) if the estimate cannot be computed from available data.
    """
    if st.risk is None:
        return None
    comp = _component_for(st.anomaly.dominant_signal if st.anomaly else None, st.asset_type)
    try:
        return do_nothing_exposure(
            asset_id=st.asset_id,
            component=comp,
            failure_probability=st.risk.risk_score,
            horizon_days=horizon_days,
        )
    except (KeyError, TypeError, ValueError):
        log.warning("could not compute economic exposure for %s", st.asset_id, exc_info=True)
        return None


def _get_all_states():
    cached = load_all_asset_states()
    if len(cached) == len(FLEET):
        return cached
    cached_ids = {s.asset_id for s in cached}
    states = list(cached)
    for a in FLEET:
        if a.asset_id not in cached_ids:
            try:
                st = compute_asset_state(a.asset_id)
                save_asset_state(st)
                states.append(st)
            except DataUnavailable:
                log.warning("telemetry unavailable for fleet asset %s", a.asset_id)
    return states


@router.get("")
def get_fleet_summary() -> dict[str, Any]:
    states = _get_all_states()
    if not states:
        return {
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "fleet_health": 100.0,
            "expected_yield_pct": 100.0,
            "assets_total": len(FLEET),
            "assets_at_risk": 0,
            "assets_offline": 0,
            "generation_kw": 0.0,
            "expected_generation_kw": 0.0,
            "availability_pct": 100.0,
            "revenue_at_risk_inr_30d": 0.0,
            "by_type": [
                {"asset_type": "wind_turbine", "count": 18, "health": 100.0, "generation_kw": 0.0},
                {"asset_type": "solar_inverter", "count": 24, "health": 100.0, "generation_kw": 0.0},
            ],
        }

    total_gen = sum(st.power_kw for st in states)
    total_exp = sum(st.expected_power_kw for st in states)
    avg_health = sum(st.health_score for st in states) / len(states)
    yield_pct = (total_gen / total_exp * 100.0) if total_exp > 0 else 100.0

    at_risk = sum(1 for st in states if st.risk.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL))
    offline = sum(1 for st in states if st.operating_state.value in ("stopped", "maintenance"))
    avail_pct = ((len(states) - offline) / len(states) * 100.0) if states else 100.0

    # Expected 30-day cost of leaving every currently at-risk asset unaddressed (INR).
    # See _expected_consequence_inr: driven by calibrated risk, not by whether the asset
    # happens to be underperforming at this instant.
    rev_at_risk = 0.0
    for st in states:
        if st.risk.risk_band in (RiskBand.ELEVATED, RiskBand.HIGH, RiskBand.CRITICAL):
            exposure = _expected_consequence_inr(st, FLEET_SUMMARY_HORIZON_DAYS)
            if exposure is not None:
                rev_at_risk += exposure

    # Group by type
    wind_states = [st for st in states if st.asset_type == AssetType.WIND_TURBINE]
    solar_states = [st for st in states if st.asset_type == AssetType.SOLAR_INVERTER]

    by_type = [
        {
            "asset_type": "wind_turbine",
            "count": len(wind_states),
            "health": round(sum(s.health_score for s in wind_states) / max(len(wind_states), 1), 1),
            "generation_kw": round(sum(s.power_kw for s in wind_states), 1),
        },
        {
            "asset_type": "solar_inverter",
            "count": len(solar_states),
            "health": round(sum(s.health_score for s in solar_states) / max(len(solar_states), 1), 1),
            "generation_kw": round(sum(s.power_kw for s in solar_states), 1),
        },
    ]

    latest_ts = max((st.as_of for st in states if st.as_of), default=datetime.now(UTC))
    as_of_str = latest_ts.isoformat().replace("+00:00", "Z")

    return {
        "updated_at": as_of_str,
        "fleet_health": round(avg_health, 1),
        "expected_yield_pct": round(yield_pct, 1),
        "assets_total": len(states),
        "assets_at_risk": at_risk,
        "assets_offline": offline,
        "generation_kw": round(total_gen, 1),
        "expected_generation_kw": round(total_exp, 1),
        "availability_pct": round(avail_pct, 1),
        "revenue_at_risk_inr_30d": round(rev_at_risk, 0),
        "by_type": by_type,
    }


@router.get("/priority")
def get_fleet_priority() -> list[dict[str, Any]]:
    """Ranked action queue ordered by revenue_at_risk_inr * risk_score descending."""
    states = _get_all_states()
    queue = []

    for st in states:
        risk_score = st.risk.risk_score

        if risk_score > 0.35 or st.anomaly.anomaly_score > 0.50:
            dominant = st.anomaly.dominant_signal or "power_kw"
            comp = _component_for(dominant, st.asset_type)
            rev_at_risk = _expected_consequence_inr(st, PRIORITY_QUEUE_HORIZON_DAYS)
            if rev_at_risk is not None:
                rev_at_risk = round(rev_at_risk, 0)
            headline = f"{comp.title()} anomaly signature"
            rec_action = f"Inspect {comp} condition within 72 hours"
            deadline = 72 if st.risk.risk_band == RiskBand.HIGH else 168

            queue.append(
                {
                    "asset_id": st.asset_id,
                    "name": st.name,
                    "asset_type": st.asset_type.value,
                    "site": st.site,
                    "headline": headline,
                    "component": comp,
                    "health_score": round(st.health_score, 1),
                    "risk_score": round(risk_score, 2),
                    "risk_band": st.risk.risk_band.value,
                    "risk_window_days": list(st.risk.risk_window_days) if st.risk.risk_window_days else [7, 21],
                    "revenue_at_risk_inr": rev_at_risk,
                    "recommended_action": rec_action,
                    "deadline_hours": deadline,
                    "requires_human_review": risk_score > 0.85,
                    "dominant_signal": dominant,
                    "_rank_weight": (rev_at_risk or 0.0) * risk_score,
                }
            )

    queue.sort(key=lambda x: x["_rank_weight"], reverse=True)
    # Remove internal sort key
    for q in queue:
        q.pop("_rank_weight", None)

    return queue
