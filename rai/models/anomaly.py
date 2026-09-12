"""Anomaly detection over residuals.

Three detectors vote, and the fusion rule is deliberate:

* **Robust residual z-score** is the always-on primary. It is interpretable, it is the signal
  an engineer can check by hand, and it carries units.
* **Isolation Forest** runs on the multivariate residual vector as a *supporting* signal only.
  It is never allowed to fire an alert alone. On the CARE benchmark of real turbine SCADA,
  Isolation Forest scores near or below random while reconstruction-based methods do well, so
  treating it as an authority would be unjustified.
* **Change-point detection** catches step changes — a string dropping offline, a sensor
  freezing — that a slow-moving z-score smooths over.

Persistence is applied last. Real degradation persists; turbulence does not. Requiring a
sustained exceedance is the single most effective false-alarm control available, and it costs
nothing but a few hours of detection latency on faults that take days to develop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from rai.config import FLEET, MODELS, Asset, settings
from rai.features.build import build_features, monitored_signals, productive_mask
from rai.models.expected import ExpectedModels, asset_training_frame, get_models
from rai.schemas import AnomalyEvidence, DetectorScore, ResidualSignal

log = logging.getLogger(__name__)

IFOREST_PATH = MODELS / "isolation_forest.json"

# Weights for fusing detector scores. The primary carries the most weight; the supporting
# detectors can raise confidence but cannot carry an alert on their own.
FUSION_WEIGHTS = {"residual_z": 0.60, "isolation_forest": 0.18, "changepoint": 0.22}

Z_SATURATION = 6.0  # |z| at which the primary detector is fully saturated
TREND_WINDOW_HOURS = 24
LONG_TREND_WINDOW_HOURS = 168


@dataclass
class ResidualWindow:
    """Residual series for one asset over a trailing window."""

    asset_id: str
    frame: pd.DataFrame
    residuals: dict[str, np.ndarray]
    z_scores: dict[str, np.ndarray]
    expected: dict[str, np.ndarray]

    @property
    def timestamps(self) -> pd.Series:
        return self.frame["ts"]


def compute_residuals(
    asset: Asset, frame: pd.DataFrame, models: ExpectedModels | None = None
) -> ResidualWindow:
    """Residuals and z-scores for every monitored signal over `frame`."""
    models = models or get_models()
    featured = build_features(frame, asset)
    productive = featured[productive_mask(featured)].reset_index(drop=True)
    if productive.empty:
        return ResidualWindow(asset.asset_id, productive, {}, {}, {})

    expected = models.predict_frame(asset, productive)
    residuals: dict[str, np.ndarray] = {}
    z_scores: dict[str, np.ndarray] = {}

    for signal, predicted in expected.items():
        actual = productive[signal].to_numpy(dtype=float)
        residual = actual - predicted
        residuals[signal] = residual
        base = models.baseline(asset.asset_id, signal)
        if base is not None:
            z_scores[signal] = (residual - base["median"]) / base["sigma"]
    return ResidualWindow(asset.asset_id, productive, residuals, z_scores, expected)


# --------------------------------------------------------------------------- detectors


def _robust_recent(values: np.ndarray, n: int) -> float:
    """Median of the most recent n finite values; robust to single-sample spikes."""
    tail = values[-n:] if len(values) > n else values
    tail = tail[np.isfinite(tail)]
    return float(np.median(tail)) if tail.size else 0.0


def _trend_per_day(timestamps: pd.Series, values: np.ndarray, hours: int) -> float | None:
    """Least-squares slope per day over a trailing window."""
    if len(values) < 6:
        return None
    cutoff = timestamps.iloc[-1] - pd.Timedelta(hours=hours)
    mask = (timestamps >= cutoff).to_numpy() & np.isfinite(values)
    if mask.sum() < 6:
        return None
    days = (timestamps[mask] - timestamps[mask].iloc[0]).dt.total_seconds().to_numpy() / 86400.0
    if days.max() <= 0:
        return None
    slope, _ = np.polyfit(days, values[mask], 1)
    return float(slope)


def _persistence_hours(
    timestamps: pd.Series, z_scores: dict[str, np.ndarray], threshold: float
) -> tuple[float, pd.Timestamp | None]:
    """How long the strongest signal has continuously exceeded the z threshold."""
    if not z_scores or timestamps.empty:
        return 0.0, None
    worst = np.zeros(len(timestamps))
    for values in z_scores.values():
        if len(values) == len(worst):
            worst = np.maximum(worst, np.abs(np.nan_to_num(values)))

    exceeded = worst >= threshold
    if not exceeded.any() or not exceeded[-1]:
        return 0.0, None

    start = len(exceeded) - 1
    while start > 0 and exceeded[start - 1]:
        start -= 1
    first = timestamps.iloc[start]
    hours = (timestamps.iloc[-1] - first).total_seconds() / 3600.0
    return float(hours), first


def _changepoint(values: np.ndarray, timestamps: pd.Series) -> tuple[float, pd.Timestamp | None]:
    """Detect a step change in the residual series.

    Uses `ruptures` when available and a cumulative-sum split otherwise, so the detector
    degrades rather than disappearing if the optional dependency is missing.
    """
    finite = np.isfinite(values)
    if finite.sum() < 40:
        return 0.0, None
    series = np.nan_to_num(values[finite])
    stamps = timestamps[finite].reset_index(drop=True)
    scale = np.std(series) or 1.0

    index: int | None = None
    try:
        import ruptures as rpt

        algo = rpt.Binseg(model="l2").fit(series.reshape(-1, 1))
        breaks = algo.predict(n_bkps=1)
        if breaks and breaks[0] < len(series):
            index = int(breaks[0])
    except Exception:  # noqa: BLE001 - optional dependency, fall back silently
        cumulative = np.cumsum(series - series.mean())
        index = int(np.argmax(np.abs(cumulative)))

    if index is None or index < 10 or index > len(series) - 10:
        return 0.0, None

    shift = abs(series[index:].mean() - series[:index].mean())
    score = float(np.clip(shift / (2.5 * scale), 0.0, 1.0))
    return score, stamps.iloc[index]


def train_isolation_forests() -> dict[str, int]:
    """Fit one Isolation Forest per asset on its healthy residual vectors."""
    models = get_models()
    payload: dict[str, dict] = {}

    for asset in FLEET:
        frame = asset_training_frame(asset)
        if frame is None:
            continue
        window = compute_residuals(asset, frame, models)
        signals = sorted(window.z_scores)
        if len(signals) < 2:
            continue
        matrix = np.column_stack([window.z_scores[s] for s in signals])
        matrix = matrix[np.isfinite(matrix).all(axis=1)]
        if len(matrix) < 300:
            continue
        forest = IsolationForest(
            n_estimators=200, contamination=0.01, random_state=17, n_jobs=2
        ).fit(matrix)
        scores = forest.score_samples(matrix)
        payload[asset.asset_id] = {
            "signals": signals,
            "healthy_score_p01": float(np.percentile(scores, 1)),
            "healthy_score_median": float(np.median(scores)),
        }
        import pickle

        with (MODELS / f"iforest_{asset.asset_id}.pkl").open("wb") as fh:
            pickle.dump(forest, fh)

    reset_iforest_cache()
    IFOREST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"assets": len(payload)}
_iforest_cache: dict[str, Any] = {}


def reset_iforest_cache() -> None:
    _iforest_cache.clear()


def _isolation_score(asset_id: str, window: ResidualWindow) -> tuple[float, str | None]:
    """Score the recent residual vector against the asset's healthy manifold."""
    if not IFOREST_PATH.exists():
        return 0.0, "not trained"
    meta = json.loads(IFOREST_PATH.read_text(encoding="utf-8")).get(asset_id)
    if meta is None:
        return 0.0, "not trained for this asset"
    path = MODELS / f"iforest_{asset_id}.pkl"
    if not path.exists():
        return 0.0, "model file missing"

    signals = meta["signals"]
    if any(s not in window.z_scores for s in signals):
        return 0.0, "signals unavailable"
    matrix = np.column_stack([window.z_scores[s] for s in signals])
    matrix = matrix[np.isfinite(matrix).all(axis=1)]
    if len(matrix) < 5:
        return 0.0, "insufficient recent data"

    if asset_id not in _iforest_cache:
        import pickle
        with path.open("rb") as fh:
            _iforest_cache[asset_id] = pickle.load(fh)
    forest = _iforest_cache[asset_id]

    recent = matrix[-max(len(matrix) // 20, 6) :]
    score = float(np.median(forest.score_samples(recent)))
    floor, median = meta["healthy_score_p01"], meta["healthy_score_median"]
    if median <= floor:
        return 0.0, None
    normalised = float(np.clip((median - score) / (median - floor), 0.0, 1.0))
    return normalised, None


# --------------------------------------------------------------------------- assembly


def assess(asset: Asset, frame: pd.DataFrame, models: ExpectedModels | None = None) -> AnomalyEvidence:
    """Run the detector ensemble over a trailing window and fuse the result."""
    models = models or get_models()
    window = compute_residuals(asset, frame, models)
    if window.frame.empty or not window.z_scores:
        return AnomalyEvidence(anomaly_score=0.0, detectors=[], signals=[])

    timestamps = window.timestamps
    interval_min = (
        float(timestamps.diff().median().total_seconds() / 60.0) if len(timestamps) > 1 else 10.0
    )
    recent_steps = max(int(round(6 * 60 / interval_min)), 3)

    units = dict(monitored_signals(asset.asset_id))
    signals: list[ResidualSignal] = []
    recent_z: dict[str, float] = {}

    for signal, residual in window.residuals.items():
        z = window.z_scores.get(signal)
        if z is None:
            continue
        actual = window.frame[signal].to_numpy(dtype=float)
        expected = window.expected[signal]
        base = models.baseline(asset.asset_id, signal)

        z_recent = _robust_recent(z, recent_steps)
        recent_z[signal] = z_recent
        actual_recent = _robust_recent(actual, recent_steps)
        expected_recent = _robust_recent(expected, recent_steps)
        residual_recent = actual_recent - expected_recent

        signals.append(
            ResidualSignal(
                name=signal,
                unit=units.get(signal, ""),
                actual=round(actual_recent, 3),
                expected=round(expected_recent, 3),
                residual=round(residual_recent, 3),
                residual_pct=(
                    round(100.0 * residual_recent / abs(expected_recent), 2)
                    if abs(expected_recent) > 1e-6
                    else None
                ),
                z_score=round(z_recent, 3),
                trend_per_day=_trend_per_day(timestamps, residual, TREND_WINDOW_HOURS),
                trend_7d_per_day=_trend_per_day(timestamps, residual, LONG_TREND_WINDOW_HOURS),
                baseline_sigma=round(base["sigma"], 4) if base else None,
            )
        )

    if not signals:
        return AnomalyEvidence(anomaly_score=0.0, detectors=[], signals=[])

    dominant = max(recent_z, key=lambda s: abs(recent_z[s]))
    peak_z = abs(recent_z[dominant])

    z_score_normalised = float(np.clip(peak_z / Z_SATURATION, 0.0, 1.0))
    iforest_score, iforest_detail = _isolation_score(asset.asset_id, window)
    change_score, change_at = _changepoint(window.residuals[dominant], timestamps)

    persistence, first_seen = _persistence_hours(
        timestamps, window.z_scores, settings.residual_z_alert
    )

    detectors = [
        DetectorScore(
            detector="residual_z",
            score=round(z_score_normalised, 3),
            threshold=round(settings.residual_z_alert / Z_SATURATION, 3),
            fired=peak_z >= settings.residual_z_alert,
            detail=f"{dominant} z={recent_z[dominant]:+.2f}",
        ),
        DetectorScore(
            detector="isolation_forest",
            score=round(iforest_score, 3),
            threshold=0.60,
            fired=iforest_score >= 0.60,
            detail=iforest_detail or "multivariate residual vector",
        ),
        DetectorScore(
            detector="changepoint",
            score=round(change_score, 3),
            threshold=0.50,
            fired=change_score >= 0.50,
            detail=(f"step in {dominant} at {change_at:%Y-%m-%d %H:%M}Z" if change_at else None),
        ),
    ]

    fused = sum(FUSION_WEIGHTS[d.detector] * d.score for d in detectors)

    # Supporting detectors cannot carry an alert alone: without the interpretable primary
    # signal, the fused score is capped below the alert threshold.
    if not detectors[0].fired:
        fused = min(fused, settings.anomaly_score_alert - 0.01)

    # Sustained exceedance is what separates degradation from turbulence.
    if persistence < settings.min_persistence_hours and detectors[0].fired:
        fused *= 0.65

    return AnomalyEvidence(
        anomaly_score=round(float(np.clip(fused, 0.0, 1.0)), 3),
        detectors=detectors,
        signals=sorted(signals, key=lambda s: abs(s.z_score or 0.0), reverse=True),
        persistence_hours=round(persistence, 2),
        first_seen=first_seen.to_pydatetime() if first_seen is not None else None,
        change_point_at=change_at.to_pydatetime() if change_at is not None else None,
        dominant_signal=dominant,
    )
