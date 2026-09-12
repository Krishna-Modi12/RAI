"""Asset-level endpoints complying with docs/API_CONTRACT.md."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

from rai.agent.investigator import investigate
from rai.config import FLEET_BY_ID, SITES, get_asset, peers_of
from rai.economics.engine import evaluate_options
from rai.memory.retrieval import find_similar_cases
from rai.models.pipeline import build_evidence_packet, compute_asset_state
from rai.schemas import AssetType
from rai.store.events import events_in_window
from rai.store.state import load_asset_state, save_asset_state
from rai.store.telemetry import available_columns, load_telemetry
from services.api.errors import AssetNotFoundError, SignalNotFoundError

router = APIRouter(prefix="/api/assets", tags=["assets"])


class InvestigateBody(BaseModel):
    force_refresh: bool = False


@router.get("")
def list_assets() -> list[dict[str, Any]]:
    from services.api.routers.fleet import _get_all_states

    states = _get_all_states()
    results = []
    for st in states:
        asset = get_asset(st.asset_id)
        p_kw = float(st.power_kw) if st.power_kw is not None else 0.0
        exp_kw = float(st.expected_power_kw) if st.expected_power_kw is not None else 0.0
        cf = float(st.capacity_factor) if st.capacity_factor is not None else 0.0
        fresh = float(st.data_freshness_s) if st.data_freshness_s is not None else 0.0
        risk_sc = float(st.risk.risk_score) if st.risk else 0.0
        risk_b = st.risk.risk_band.value if st.risk else "low"
        anom_sc = float(st.anomaly.anomaly_score) if st.anomaly else 0.0
        op_st = st.operating_state.value if st.operating_state else "normal"

        results.append(
            {
                "asset_id": st.asset_id,
                "name": st.name,
                "asset_type": st.asset_type.value,
                "site": st.site,
                "peer_group": asset.peer_group,
                "rated_power_kw": asset.rated_power_kw,
                "health_score": round(float(st.health_score), 1) if st.health_score is not None else 100.0,
                "risk_score": round(risk_sc, 2),
                "risk_band": risk_b,
                "anomaly_score": round(anom_sc, 2),
                "operating_state": op_st,
                "power_kw": round(p_kw, 1),
                "expected_power_kw": round(exp_kw, 1),
                "capacity_factor": round(cf, 2),
                "data_freshness_s": round(fresh, 1),
            }
        )
    return results


@router.get("/{asset_id}")
def get_asset_detail(asset_id: str) -> dict[str, Any]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    asset = get_asset(asset_id)
    st = load_asset_state(asset_id)
    if st is None:
        st = compute_asset_state(asset_id)
        save_asset_state(st)
    site_meta = SITES.get(asset.site, {})

    asset_dict: dict[str, Any] = {
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type.value,
        "name": asset.name,
        "site": asset.site,
        "region": site_meta.get("region", "Gujarat, India"),
        "rated_power_kw": asset.rated_power_kw,
        "commissioned": asset.commissioned,
        "peer_group": asset.peer_group,
    }
    if asset.asset_type == AssetType.WIND_TURBINE:
        asset_dict.update({
            "rotor_diameter_m": asset.rotor_diameter_m,
            "hub_height_m": asset.hub_height_m,
        })
    else:
        asset_dict.update({
            "tilt_deg": asset.tilt_deg,
            "azimuth_deg": asset.azimuth_deg,
            "dc_capacity_kw": asset.dc_capacity_kw,
        })

    p_kw = float(st.power_kw) if st.power_kw is not None else 0.0
    exp_kw = float(st.expected_power_kw) if st.expected_power_kw is not None else 0.0
    cf = float(st.capacity_factor) if st.capacity_factor is not None else 0.0
    fresh = float(st.data_freshness_s) if st.data_freshness_s is not None else 0.0

    state_dict = {
        "as_of": st.as_of.isoformat().replace("+00:00", "Z") if st.as_of else datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "health_score": round(float(st.health_score), 1) if st.health_score is not None else 100.0,
        "operating_state": st.operating_state.value if st.operating_state else "normal",
        "power_kw": round(p_kw, 1),
        "expected_power_kw": round(exp_kw, 1),
        "capacity_factor": round(cf, 2),
        "data_freshness_s": round(fresh, 1),
    }

    risk_dict = None
    if st.risk:
        risk_dict = {
            "risk_score": round(float(st.risk.risk_score), 2),
            "risk_band": st.risk.risk_band.value,
            "horizon_days": st.risk.horizon_days,
            "risk_window_days": list(st.risk.risk_window_days) if st.risk.risk_window_days else None,
            "calibration": st.risk.calibration or "isotonic",
            "drivers": st.risk.drivers,
        }

    anomaly_dict = None
    if st.anomaly:
        anomaly_dict = {
            "anomaly_score": round(float(st.anomaly.anomaly_score), 2),
            "persistence_hours": round(float(st.anomaly.persistence_hours), 1),
            "first_seen": st.anomaly.first_seen.isoformat().replace("+00:00", "Z") if st.anomaly.first_seen else None,
            "change_point_at": st.anomaly.change_point_at.isoformat().replace("+00:00", "Z") if st.anomaly.change_point_at else None,
            "dominant_signal": st.anomaly.dominant_signal,
            "detectors": [
                {
                    "detector": d.detector,
                    "score": round(float(d.score), 2),
                    "threshold": round(float(d.threshold), 2),
                    "fired": d.fired,
                    "detail": d.detail,
                }
                for d in st.anomaly.detectors
            ],
            "signals": [
                {
                    "name": s.name,
                    "unit": s.unit,
                    "actual": round(float(s.actual), 2),
                    "expected": round(float(s.expected), 2),
                    "residual": round(float(s.residual), 2),
                    "residual_pct": round(float(s.residual_pct), 1),
                    "z_score": round(float(s.z_score), 1),
                    "trend_per_day": round(float(s.trend_per_day), 2) if s.trend_per_day is not None else None,
                    "trend_7d_per_day": round(float(s.trend_7d_per_day), 2) if s.trend_7d_per_day is not None else None,
                    "baseline_sigma": round(float(s.baseline_sigma), 2) if s.baseline_sigma is not None else None,
                }
                for s in st.anomaly.signals
            ],
        }

    peers_dict = None
    if st.peers:
        peers_dict = {
            "peer_group": st.peers.peer_group,
            "n_peers": st.peers.n_peers,
            "asset_residual_pct": round(float(st.peers.asset_residual_pct), 1),
            "peer_median_residual_pct": round(float(st.peers.peer_median_residual_pct), 1),
            "deviation_percentile": round(float(st.peers.deviation_percentile), 1),
            "verdict": st.peers.verdict.value,
            "note": st.peers.note,
        }

    env_dict = None
    if st.environment:
        env_dict = {
            "source": st.environment.source,
            "conditions": st.environment.conditions,
            "operating_state": st.environment.operating_state.value,
            "curtailment_detected": st.environment.curtailment_detected,
            "sensor_health": st.environment.sensor_health.value,
            "explains_fraction": round(float(st.environment.explains_fraction), 2),
            "verdict": st.environment.verdict.value,
            "note": st.environment.note,
        }

    soiling_dict = None
    if st.soiling:
        soiling_dict = {
            "soiling_ratio": round(float(st.soiling.soiling_ratio), 3) if st.soiling.soiling_ratio is not None else None,
            "soiling_loss_pct": round(float(st.soiling.soiling_loss_pct), 1) if st.soiling.soiling_loss_pct is not None else None,
            "soiling_rate_pct_per_day": round(float(st.soiling.soiling_rate_pct_per_day), 2) if st.soiling.soiling_rate_pct_per_day is not None else None,
            "days_since_cleaning": round(float(st.soiling.days_since_cleaning), 1) if st.soiling.days_since_cleaning is not None else None,
            "days_since_rain": round(float(st.soiling.days_since_rain), 1) if st.soiling.days_since_rain is not None else None,
            "rain_probability_48h": round(float(st.soiling.rain_probability_48h), 2) if st.soiling.rain_probability_48h is not None else None,
            "method": st.soiling.method,
        }

    return {
        "asset": asset_dict,
        "state": state_dict,
        "risk": risk_dict,
        "anomaly": anomaly_dict,
        "peers": peers_dict,
        "environment": env_dict,
        "soiling": soiling_dict,
    }


@router.get("/{asset_id}/timeseries")
def get_asset_timeseries(
    asset_id: str,
    signal: str = Query(default="power_kw"),
    hours: int = Query(default=168),
) -> dict[str, Any]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    asset = get_asset(asset_id)
    cols = available_columns(asset_id)
    if signal not in cols and signal == "power_kw" and "ac_power_kw" in cols:
        signal = "ac_power_kw"
    elif signal not in cols:
        raise SignalNotFoundError(signal)

    # Load telemetry window
    end_dt = datetime.now(UTC)
    start_dt = end_dt - pd.Timedelta(hours=hours)

    needed_cols = ["ts", signal]
    if "expected_power_kw" in cols:
        needed_cols.append("expected_power_kw")

    df = load_telemetry(asset_id, start=start_dt, end=end_dt, columns=needed_cols)

    points = []
    for _, row in df.iterrows():
        act = float(row[signal]) if pd.notna(row[signal]) else 0.0
        exp = float(row.get("expected_power_kw", act)) if "expected_power_kw" in row and pd.notna(row["expected_power_kw"]) else act
        z = (act - exp) / max(exp * 0.1, 1.0)
        ts_val = row["ts"]
        ts_str = ts_val.isoformat().replace("+00:00", "Z") if hasattr(ts_val, "isoformat") else str(ts_val)

        points.append({
            "t": ts_str,
            "actual": round(act, 1),
            "expected": round(exp, 1),
            "lower": round(exp * 0.9, 1),
            "upper": round(exp * 1.1, 1),
            "residual_z": round(z, 2),
        })

    # Events in window
    raw_events = events_in_window(start=start_dt, end=end_dt, asset_id=asset_id)
    events = [
        {
            "t": e.onset.isoformat().replace("+00:00", "Z"),
            "label": f"{e.scenario.replace('_', ' ').title()} injected",
            "kind": "alert" if e.is_equipment_fault else "weather",
        }
        for e in raw_events
    ]

    unit = "kW" if "power" in signal else ("degC" if "temp" in signal else ("mm/s" if "vibration" in signal else ""))
    interval_min = 10 if asset.asset_type == AssetType.WIND_TURBINE else 15

    return {
        "asset_id": asset_id,
        "signal": signal,
        "unit": unit,
        "interval_min": interval_min,
        "points": points,
        "events": events,
    }


@router.get("/{asset_id}/peers")
def get_asset_peers(asset_id: str, window_hours: int = Query(default=24)) -> dict[str, Any]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    asset = get_asset(asset_id)
    peer_list = peers_of(asset_id)

    assets_out = []
    st_main = compute_asset_state(asset_id)
    p_main = float(st_main.power_kw) if st_main.power_kw is not None else 0.0
    exp_main = float(st_main.expected_power_kw) if st_main.expected_power_kw is not None else 0.0
    main_val = round((p_main - exp_main) / max(exp_main, 1.0) * 100.0, 1)

    assets_out.append({
        "asset_id": asset.asset_id,
        "name": asset.name,
        "value": main_val,
        "is_subject": True,
        "percentile": 96.0 if main_val < -5.0 else 50.0,
    })

    for p in peer_list:
        try:
            st = compute_asset_state(p.asset_id)
            p_val = float(st.power_kw) if st.power_kw is not None else 0.0
            exp_val = float(st.expected_power_kw) if st.expected_power_kw is not None else 0.0
            val = round((p_val - exp_val) / max(exp_val, 1.0) * 100.0, 1)
        except Exception:
            val = 0.0
        assets_out.append({
            "asset_id": p.asset_id,
            "name": p.name,
            "value": val,
            "is_subject": False,
            "percentile": 50.0,
        })

    return {
        "peer_group": asset.peer_group,
        "metric": "power_residual_pct",
        "window_hours": window_hours,
        "assets": assets_out,
    }


@router.post("/{asset_id}/investigate")
def post_investigate(asset_id: str, body: InvestigateBody | None = None) -> dict[str, Any]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    force = body.force_refresh if body else False
    res = investigate(asset_id, force_refresh=force)
    out = res.model_dump(mode="json")
    if res.verdict:
        out["historical_cases"] = [c.model_dump(mode="json") for c in res.verdict.historical_cases]
        out["citations"] = [c.model_dump(mode="json") for c in res.verdict.citations]
        out["economics"] = res.verdict.economics.model_dump(mode="json") if res.verdict.economics else None
    else:
        out.setdefault("historical_cases", [])
        out.setdefault("citations", [])
        out.setdefault("economics", None)
    return out


@router.get("/{asset_id}/cases")
def get_asset_cases(asset_id: str) -> list[dict[str, Any]]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    packet = build_evidence_packet(asset_id)
    cases = find_similar_cases(packet, k=5)
    return [c.model_dump(mode="json") for c in cases]


@router.get("/{asset_id}/economics")
def get_asset_economics(asset_id: str, component: str | None = Query(default=None)) -> dict[str, Any]:
    if asset_id not in FLEET_BY_ID:
        raise AssetNotFoundError(asset_id)

    st = compute_asset_state(asset_id)
    comp = component or (
        (st.anomaly.dominant_signal if st.anomaly else None)
        or ("gearbox" if st.asset_type == AssetType.WIND_TURBINE else "inverter")
    )
    risk_sc = float(st.risk.risk_score) if st.risk else 0.5
    risk_win = st.risk.risk_window_days if st.risk else None

    econ = evaluate_options(
        asset_id=asset_id,
        component=comp,
        failure_probability=risk_sc,
        risk_window_days=risk_win,
    )
    return econ.model_dump(mode="json")
