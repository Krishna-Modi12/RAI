"""Peer comparison.

The question this layer answers is narrow and decisive: *is this asset deviating, or is the
whole group deviating together?* A site-wide irradiance drop, a grid curtailment or a passing
squall moves every asset at once. A failing gearbox moves one.

Peer groups come from the physical layout, not from convenience. Row B sits in row A's wake,
so comparing a row-B turbine against row A would manufacture a permanent false deficit.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from rai.config import get_asset, peers_of
from rai.models.expected import ExpectedModels, get_models
from rai.schemas import AssetType, PeerEvidence, PeerVerdict
from rai.store import DataUnavailable, load_window

log = logging.getLogger(__name__)

# The subject must stand this far outside the peer spread to be called asset-specific.
ASSET_SPECIFIC_PERCENTILE = 85.0
FLEET_WIDE_MEDIAN_DEFICIT_PCT = -3.0
MIN_PEERS = 3


def _recent_residual_pct(
    asset_id: str, end: pd.Timestamp, hours: int, models: ExpectedModels
) -> float | None:
    """Median power residual as a percentage of expected, over a trailing window."""
    asset = get_asset(asset_id)
    try:
        frame = load_window(asset_id, end=end, hours=hours)
    except (DataUnavailable, FileNotFoundError):
        return None
    if frame.empty:
        return None

    from rai.models.anomaly import compute_residuals

    window = compute_residuals(asset, frame, models)
    signal = "power_kw" if asset.asset_type is AssetType.WIND_TURBINE else "ac_power_kw"
    if signal not in window.residuals or window.frame.empty:
        return None

    expected = window.expected[signal]
    residual = window.residuals[signal]
    usable = np.isfinite(expected) & np.isfinite(residual) & (expected > 0.05 * asset.rated_power_kw)
    if usable.sum() < 5:
        return None
    return float(np.median(100.0 * residual[usable] / expected[usable]))


def compare(
    asset_id: str,
    end: pd.Timestamp,
    hours: int = 24,
    models: ExpectedModels | None = None,
) -> PeerEvidence:
    """Position this asset against its peer group over the trailing window."""
    models = models or get_models()
    asset = get_asset(asset_id)
    peer_assets = peers_of(asset_id)

    subject = _recent_residual_pct(asset_id, end, hours, models)
    peer_values: list[tuple[str, float]] = []
    for peer in peer_assets:
        value = _recent_residual_pct(peer.asset_id, end, hours, models)
        if value is not None:
            peer_values.append((peer.asset_id, value))

    if subject is None or len(peer_values) < MIN_PEERS:
        return PeerEvidence(
            peer_group=asset.peer_group,
            n_peers=len(peer_values),
            asset_residual_pct=subject,
            verdict=PeerVerdict.NORMAL,
            note="insufficient peer data for comparison",
        )

    values = np.array([v for _, v in peer_values])
    peer_median = float(np.median(values))
    # Percentile of the subject's deviation magnitude within the peer group.
    percentile = float(100.0 * (np.abs(values) < abs(subject)).mean())

    if peer_median <= FLEET_WIDE_MEDIAN_DEFICIT_PCT and abs(subject - peer_median) < 3.0:
        verdict = PeerVerdict.FLEET_WIDE
        note = (
            f"peer median is also {peer_median:+.1f}%, so the deviation is not specific "
            f"to {asset_id}"
        )
    elif percentile >= ASSET_SPECIFIC_PERCENTILE and abs(subject - peer_median) >= 2.5:
        verdict = PeerVerdict.ASSET_SPECIFIC
        within = sum(1 for _, v in peer_values if abs(v) < abs(subject))
        note = (
            f"{within} of {len(peer_values)} peers in {asset.peer_group} deviate less "
            f"under the same conditions"
        )
    else:
        verdict = PeerVerdict.NORMAL
        note = f"within the peer spread (peer median {peer_median:+.1f}%)"

    return PeerEvidence(
        peer_group=asset.peer_group,
        n_peers=len(peer_values),
        asset_residual_pct=round(subject, 2),
        peer_median_residual_pct=round(peer_median, 2),
        deviation_percentile=round(percentile, 1),
        verdict=verdict,
        note=note,
    )


def peer_series(
    asset_id: str, end: pd.Timestamp, hours: int = 24, models: ExpectedModels | None = None
) -> dict:
    """Peer comparison payload for GET /api/assets/{id}/peers."""
    models = models or get_models()
    asset = get_asset(asset_id)
    rows = []
    for candidate in [asset, *peers_of(asset_id)]:
        value = _recent_residual_pct(candidate.asset_id, end, hours, models)
        if value is None:
            continue
        rows.append(
            {
                "asset_id": candidate.asset_id,
                "name": candidate.name,
                "value": round(value, 2),
                "is_subject": candidate.asset_id == asset_id,
            }
        )

    values = np.array([r["value"] for r in rows]) if rows else np.array([])
    for row in rows:
        row["percentile"] = (
            round(float(100.0 * (np.abs(values) < abs(row["value"])).mean()), 1)
            if values.size
            else None
        )

    return {
        "peer_group": asset.peer_group,
        "metric": "power_residual_pct",
        "window_hours": hours,
        "assets": sorted(rows, key=lambda r: r["value"]),
    }
