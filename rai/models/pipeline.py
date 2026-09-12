"""Evidence assembly.

This module is the seam between the numerical system and the reasoning system. It runs the
layers in order — residuals, anomaly fusion, environment, peers, soiling, risk — and packages
the result as an `EvidencePacket`.

`build_evidence_packet` is the *only* thing the language model is ever given. It contains
computed evidence and nothing else: no raw telemetry, no long series, no free text from the
data. That boundary is what makes the agent's output auditable, and it is enforced here
rather than by convention.
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from rai.config import Asset, get_asset
from rai.features.build import build_features, productive_mask
from rai.models import environment as env_layer
from rai.models import peers as peer_layer
from rai.models import risk as risk_layer
from rai.models.anomaly import assess as assess_anomaly
from rai.models.anomaly import compute_residuals
from rai.models.expected import ExpectedModels, get_models, healthy_cutoff
from rai.schemas import (
    AnomalyEvidence,
    AssetState,
    AssetType,
    EvidencePacket,
    OperatingState,
    SoilingEvidence,
)
from rai.store import DataUnavailable, load_telemetry, load_window

log = logging.getLogger(__name__)

WINDOW_HOURS = 14 * 24
PEER_WINDOW_HOURS = 24

_packet_cache: dict[tuple[str, str], EvidencePacket] = {}
_state_cache: dict[tuple[str, str], AssetState] = {}


def clear_cache() -> None:
    _packet_cache.clear()
    _state_cache.clear()


def _cache_key(asset_id: str, as_of: pd.Timestamp | None) -> tuple[str, str]:
    return asset_id, as_of.isoformat() if as_of is not None else "latest"


# --------------------------------------------------------------------------- soiling


def estimate_soiling(asset: Asset, frame: pd.DataFrame) -> SoilingEvidence | None:
    """Soiling loss from the performance-ratio trajectory and rainfall history.

    Reported alongside days-since-rain because the distinction that matters operationally is
    whether the loss is recoverable by washing or by a truck roll.
    """
    if asset.asset_type is not AssetType.SOLAR_INVERTER or "performance_ratio" not in frame:
        return None

    day = frame[(frame["poa_wm2"] > 150) & frame["performance_ratio"].notna()]
    if len(day) < 50:
        return None

    recent = day.tail(max(len(day) // 14, 20))
    reference = day.head(max(len(day) // 10, 30))
    reference_pr = float(reference["performance_ratio"].median())
    recent_pr = float(recent["performance_ratio"].median())
    if reference_pr <= 0:
        return None

    ratio = float(np.clip(recent_pr / reference_pr, 0.5, 1.05))
    loss_pct = max(0.0, (1.0 - ratio) * 100.0)

    days_since_rain = None
    if "ts" in frame.columns:
        # Rain is inferred from soiling recovery in the telemetry itself.
        soiling = frame[["ts", "soiling_ratio"]].dropna()
        if len(soiling) > 10:
            jumps = soiling[soiling["soiling_ratio"].diff() > 0.01]
            if not jumps.empty:
                days_since_rain = float(
                    (frame["ts"].max() - jumps["ts"].iloc[-1]).total_seconds() / 86400.0
                )

    span_days = max((day["ts"].max() - day["ts"].min()).total_seconds() / 86400.0, 1.0)
    rate = loss_pct / span_days if loss_pct > 0 else 0.0

    return SoilingEvidence(
        soiling_ratio=round(ratio, 4),
        soiling_loss_pct=round(loss_pct, 2),
        soiling_rate_pct_per_day=round(rate, 4),
        days_since_cleaning=days_since_rain,
        days_since_rain=round(days_since_rain, 1) if days_since_rain is not None else None,
        rain_probability_48h=None,  # requires a live forecast feed; null rather than invented
        method="performance_ratio_trajectory",
    )


# --------------------------------------------------------------------------- health


def health_score(anomaly: AnomalyEvidence, risk_score: float, availability: float) -> float:
    """A single 0-100 figure for triage. Monotone in every input, so it stays interpretable."""
    penalty = 55.0 * risk_score + 20.0 * anomaly.anomaly_score + 15.0 * (1.0 - availability)
    return round(float(np.clip(100.0 - penalty, 0.0, 100.0)), 1)


# --------------------------------------------------------------------------- assembly


def _latest_timestamp(asset_id: str) -> pd.Timestamp:
    from rai.store import latest_row

    row = latest_row(asset_id)
    if row is None:
        raise DataUnavailable(f"no telemetry for {asset_id}")
    return pd.Timestamp(row["ts"])


def _load(asset_id: str, as_of: pd.Timestamp | None, hours: int) -> pd.DataFrame:
    end = as_of if as_of is not None else _latest_timestamp(asset_id)
    frame = load_window(asset_id, end=end, hours=hours)
    if frame.empty:
        raise DataUnavailable(f"no telemetry for {asset_id}")
    return frame


def build_evidence_packet(asset_id: str, as_of: datetime | None = None) -> EvidencePacket:
    """Run the full evidence chain for one asset."""
    stamp = pd.Timestamp(as_of).tz_convert("UTC") if as_of is not None else None
    key = _cache_key(asset_id, stamp)
    if key in _packet_cache:
        return _packet_cache[key]

    asset = get_asset(asset_id)
    models: ExpectedModels = get_models()
    frame = _load(asset_id, stamp, WINDOW_HOURS)

    anomaly = assess_anomaly(asset, frame, models)

    featured = build_features(frame, asset)
    productive = featured[productive_mask(featured)]
    signal = "power_kw" if asset.asset_type is AssetType.WIND_TURBINE else "ac_power_kw"

    expected_series = None
    actual_series = None
    if not productive.empty:
        window = compute_residuals(asset, frame, models)
        if signal in window.expected and not window.frame.empty:
            recent = max(len(window.frame) // 10, 12)
            expected_series = window.expected[signal][-recent:]
            actual_series = window.frame[signal].to_numpy(dtype=float)[-recent:]

    typical = _typical_output(asset, models)
    peak_abs_z = max(
        (abs(s.z_score) for s in anomaly.signals if s.z_score is not None), default=0.0
    )
    step_detected = any(d.detector == "changepoint" and d.fired for d in anomaly.detectors)
    environment = env_layer.attribute(
        asset,
        featured,
        expected_series,
        actual_series,
        typical,
        peak_abs_z=peak_abs_z,
        residual_step_detected=step_detected,
    )
    peers = peer_layer.compare(
        asset_id, end=frame["ts"].max(), hours=PEER_WINDOW_HOURS, models=models
    )
    soiling = estimate_soiling(asset, featured)
    risk = risk_layer.assess(anomaly, peers, environment)

    availability = float(
        (featured["operating_state"] != OperatingState.STOPPED.value).mean()
        if not featured.empty
        else 1.0
    )

    packet = EvidencePacket(
        asset_id=asset_id,
        asset_type=asset.asset_type,
        generated_at=frame["ts"].max().to_pydatetime(),
        health_score=health_score(anomaly, risk.risk_score, availability),
        anomaly=anomaly,
        risk=risk,
        peers=peers,
        environment=environment,
        soiling=soiling,
    )
    _packet_cache[key] = packet
    return packet


def _typical_output(asset: Asset, models: ExpectedModels) -> float | None:
    """The asset's own median productive output on healthy data, as the deficit reference."""
    base = models.baseline(
        asset.asset_id,
        "power_kw" if asset.asset_type is AssetType.WIND_TURBINE else "ac_power_kw",
    )
    return base.get("reference_mean") if base else None


def compute_asset_state(asset_id: str, as_of: datetime | None = None) -> AssetState:
    """Current state of one asset, as the fleet and detail views consume it."""
    stamp = pd.Timestamp(as_of).tz_convert("UTC") if as_of is not None else None
    key = _cache_key(asset_id, stamp)
    if key in _state_cache:
        return _state_cache[key]

    asset = get_asset(asset_id)
    packet = build_evidence_packet(asset_id, as_of)
    frame = _load(asset_id, stamp, 6)
    latest = frame.iloc[-1]

    signal = "power_kw" if asset.asset_type is AssetType.WIND_TURBINE else "ac_power_kw"
    power = float(latest[signal]) if pd.notna(latest.get(signal)) else None
    expected = next(
        (s.expected for s in packet.anomaly.signals if s.name == signal), None
    )

    now = pd.Timestamp.now(tz="UTC")
    freshness = float((now - frame["ts"].max()).total_seconds())

    state = AssetState(
        asset_id=asset_id,
        asset_type=asset.asset_type,
        name=asset.name,
        site=asset.site,
        as_of=frame["ts"].max().to_pydatetime(),
        health_score=packet.health_score,
        operating_state=OperatingState(latest.get("operating_state", "unknown")),
        power_kw=round(power, 2) if power is not None else None,
        expected_power_kw=round(expected, 2) if expected is not None else None,
        capacity_factor=(
            round(power / asset.rated_power_kw, 4) if power is not None else None
        ),
        anomaly=packet.anomaly,
        risk=packet.risk,
        peers=packet.peers,
        environment=packet.environment,
        soiling=packet.soiling,
        data_freshness_s=round(max(freshness, 0.0), 1),
    )
    _state_cache[key] = state
    return state


# --------------------------------------------------------------------------- risk training data


def build_training_snapshots(horizon_days: int = 30, stride_hours: int = 12) -> list[dict]:
    """Interval-level snapshots with ground-truth labels, for fitting the risk model.

    Label is 1 only when a genuine **equipment** fault is developing on that asset at that
    time. Soiling, sensor drift, curtailment, cloud and icing are all labelled 0, so the model
    is trained to separate degradation from its lookalikes rather than to detect novelty.
    """
    from rai.config import FLEET
    from rai.store import load_events

    models = get_models()
    events = {e.asset_id: e for e in load_events()}
    snapshots: list[dict] = []

    for asset in FLEET:
        try:
            full = load_telemetry(asset.asset_id)
        except (DataUnavailable, FileNotFoundError):
            continue
        if full.empty:
            continue

        event = events.get(asset.asset_id)
        cutoff = healthy_cutoff(asset.asset_id)
        start = full["ts"].min() + pd.Timedelta(days=3)
        end = full["ts"].max()

        for stamp in pd.date_range(start, end, freq=f"{stride_hours}h"):
            window = full[(full["ts"] > stamp - pd.Timedelta(hours=WINDOW_HOURS)) & (full["ts"] <= stamp)]
            if len(window) < 100:
                continue
            try:
                anomaly = assess_anomaly(asset, window, models)
            except Exception as exc:  # noqa: BLE001
                log.debug("snapshot failed for %s at %s: %s", asset.asset_id, stamp, exc)
                continue
            if not anomaly.signals:
                continue

            featured = build_features(window, asset)
            environment = env_layer.attribute(asset, featured, None, None, None)
            peers = None  # peer comparison is expensive here; risk features tolerate absence

            label = 0
            if (
                event is not None
                and event.is_equipment_fault
                and cutoff is not None
                and stamp >= pd.Timestamp(event.detectable_from)
            ):
                label = 1

            features = risk_layer.build_features(anomaly, peers, environment)
            snapshots.append(
                {
                    "asset_id": asset.asset_id,
                    "ts": stamp,
                    "label": label,
                    **features.values,
                }
            )
    return snapshots
