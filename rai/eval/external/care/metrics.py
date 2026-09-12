"""The CARE score, implemented exactly as defined in Gück, Roelofs & Faulstich (2024).

Every function here corresponds to one named equation or algorithm in the paper, cited in
its docstring, so a reviewer can check this against the source instead of trusting a
paraphrase. Nothing in this file is fit to RAI's synthetic fleet or tuned against any result
- it is a direct transcription of the published scoring method.

Terminology carried over from the paper:

* A "dataset" is one CARE CSV (one turbine, one labelled period): either an "anomaly event"
  dataset (contains a labelled fault run-up) or a "normal behavior" dataset (does not).
* "Normal status" / "abnormal status" refers to the turbine's own status-ID at each
  timestamp (table 3.3 of the paper), not to the anomaly label. A `status_normal` array of
  `True`/`False` is what every function below expects - `True` means the turbine's own
  status-ID says it was operating normally at that timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class CareDatasetLabel(str, Enum):
    ANOMALY_EVENT = "anomaly_event"
    NORMAL_BEHAVIOR = "normal_behavior"


def _fbeta(tp: int, fp: int, fn: int, beta: float) -> float:
    """Eq. 1: F_beta(g, p) = (1+b^2) tp / ((1+b^2) tp + b^2 fn + fp)."""
    b2 = beta * beta
    denom = (1 + b2) * tp + b2 * fn + fp
    if denom == 0:
        # No positives predicted or present: by convention (matching the paper's use of the
        # score on datasets that could contain zero of either), a perfect absence of both
        # false alarms and misses scores 1.0, not 0/0.
        return 1.0
    return (1 + b2) * tp / denom


def _confusion(g: np.ndarray, p: np.ndarray) -> tuple[int, int, int, int]:
    g = g.astype(bool)
    p = p.astype(bool)
    tp = int(np.sum(g & p))
    fp = int(np.sum(~g & p))
    fn = int(np.sum(g & ~p))
    tn = int(np.sum(~g & ~p))
    return tp, fp, fn, tn


def coverage_fbeta(
    ground_truth: np.ndarray, prediction: np.ndarray, status_normal: np.ndarray, beta: float = 0.5
) -> float:
    """Eq. 1 (Coverage). Pointwise F_beta on an anomaly-event dataset, normal-status points only.

    `ground_truth` and `prediction` are 0/1 (or bool) arrays over every timestamp in the
    dataset's prediction time frame; `status_normal[i]` selects the subset the paper scores
    on ("all data points with an abnormal status-ID... are ignored").
    """
    mask = status_normal.astype(bool)
    g, p = np.asarray(ground_truth)[mask], np.asarray(prediction)[mask]
    tp, fp, fn, _ = _confusion(g, p)
    return _fbeta(tp, fp, fn, beta)


def accuracy_score(prediction: np.ndarray, status_normal: np.ndarray) -> float:
    """Eq. 2 (Accuracy). tn / (fp + tn) on a normal-behavior dataset, normal-status points only.

    Ground truth is implicitly all-normal (0) for a normal-behavior dataset, so only the
    prediction is needed: a 1 is a false positive, a 0 is a true negative.
    """
    mask = status_normal.astype(bool)
    p = np.asarray(prediction)[mask].astype(bool)
    fp = int(np.sum(p))
    tn = int(np.sum(~p))
    return tn / (fp + tn) if (fp + tn) > 0 else 1.0


def criticality_series(status_normal: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    """Algorithm 1. A counter that only moves during abnormal-status timestamps.

    crit[i] = crit[i-1] + 1        if status is abnormal and an anomaly was predicted
    crit[i] = max(crit[i-1]-1, 0)  if status is abnormal and no anomaly was predicted
    crit[i] = crit[i-1]            if status is normal (frozen either way)
    """
    status_normal = np.asarray(status_normal).astype(bool)
    prediction = np.asarray(prediction).astype(bool)
    n = len(status_normal)
    crit = np.zeros(n, dtype=np.int64)
    running = 0
    for i in range(n):
        if not status_normal[i]:
            running = running + 1 if prediction[i] else max(running - 1, 0)
        crit[i] = running
    return crit


@dataclass(frozen=True)
class DatasetReliabilityInput:
    """One dataset's inputs to the event-based reliability score."""

    label: CareDatasetLabel
    status_normal: np.ndarray
    prediction: np.ndarray


def event_reliability_fbeta(
    datasets: list[DatasetReliabilityInput], criticality_threshold: float = 72.0, beta: float = 0.5
) -> float:
    """Eq. 1 applied at the event/dataset level (Reliability, "EF_beta").

    Each dataset becomes exactly one detected/not-detected decision: does its maximum
    criticality (Algorithm 1) exceed `criticality_threshold` (72 in the paper, i.e. ~12h of
    consecutive detections during an abnormal-status run, for 10-minute data)? That decision
    is then compared, across *all* datasets (event and normal alike), to the true dataset
    label with F_beta.
    """
    g = np.array([1 if d.label is CareDatasetLabel.ANOMALY_EVENT else 0 for d in datasets])
    p = np.array(
        [
            1 if (criticality_series(d.status_normal, d.prediction).max(initial=0) >= criticality_threshold) else 0
            for d in datasets
        ]
    )
    tp, fp, fn, _ = _confusion(g, p)
    return _fbeta(tp, fp, fn, beta)


def weighted_earliness_score(prediction: np.ndarray) -> float:
    """Eq. 3 (Earliness / WS), applied to one anomaly event's consecutive timestamps.

    `prediction` covers exactly the event's own timestamps (already sliced by the caller to
    the labelled anomaly window), in chronological order. Weight is 1.0 for the first half of
    the event (relative position <= 0.5) and decreases linearly to 0.0 at the event's end,
    per the paper's figure 1.
    """
    p = np.asarray(prediction).astype(float)
    m = len(p)
    if m == 0:
        return 0.0
    if m == 1:
        weights = np.array([1.0])
    else:
        rel = np.arange(m) / (m - 1)
        weights = np.where(rel <= 0.5, 1.0, np.clip(2.0 * (1.0 - rel), 0.0, 1.0))
    total_weight = weights.sum()
    if total_weight == 0:
        return 0.0
    return float(np.sum(weights * p) / total_weight)


def care_score(
    mean_coverage_fbeta: float,
    mean_earliness_ws: float,
    event_reliability: float,
    mean_accuracy: float,
    any_anomaly_predicted: bool,
    weights: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 2.0),
) -> float:
    """Eq. 4-5. Combine the four sub-scores into the final CARE score.

    Special cases, in order (the paper defines them this way, not as a smooth blend):
    1. If the model predicted zero anomalies across the entire evaluation, CARE = 0.
    2. Else if mean accuracy < 0.5 (worse than random on normal data), CARE = mean accuracy.
    3. Else CARE is the weights-normalised average of (coverage, earliness, reliability,
       2x accuracy).
    """
    if not any_anomaly_predicted:
        return 0.0
    if mean_accuracy < 0.5:
        return mean_accuracy
    w1, w2, w3, w4 = weights
    return (w1 * mean_coverage_fbeta + w2 * mean_earliness_ws + w3 * event_reliability + w4 * mean_accuracy) / (
        w1 + w2 + w3 + w4
    )
