"""Undertuned anomaly-score baselines for the external CARE benchmark.

RAI's trained expected-behaviour models are fit on the synthetic 42-asset fleet's specific
schema; they do not transfer to CARE's anonymised sensor columns without a retraining step
this hackathon does not have time for. Rather than force a transfer that would not really be
RAI's own model, these baselines deliberately mirror the CARE paper's own methodology
(section 4.2.1-4.2.2: isolation forest with n_estimators=100, contamination=0.09; a threshold
on a reconstruction/residual-style signal) - so a genuine, modest score on real data, scored
the paper's own way, is what gets reported. See `docs/evaluation/EXTERNAL_CARE.md` for why
this is the honest scope rather than "RAI's champion, transferred".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

#: Canonical wind columns from rai.ingest.care.CANONICAL_WIND_COLUMNS that carry a numeric
#: sensor reading (excludes ts/asset_id/status_code/operating_state).
FEATURE_COLUMNS: tuple[str, ...] = (
    "wind_speed_ms",
    "wind_direction_deg",
    "ambient_temp_c",
    "pressure_hpa",
    "humidity_pct",
    "air_density",
    "power_kw",
    "rotor_rpm",
    "pitch_angle_deg",
    "nacelle_temp_c",
    "gearbox_oil_temp_c",
    "generator_winding_temp_c",
    "main_bearing_temp_c",
    "drivetrain_vibration_mms",
)

_MIN_TRAIN_OBSERVATIONS = 10


def _usable_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLUMNS if c in frame.columns and frame[c].notna().sum() >= _MIN_TRAIN_OBSERVATIONS]


@dataclass(frozen=True)
class IsolationForestBaseline:
    """Mirrors the paper's own mini-benchmark isolation-forest baseline (section 4.2.1)."""

    columns: list[str]
    medians: dict[str, float]
    model: IsolationForest

    def _matrix(self, frame: pd.DataFrame) -> np.ndarray:
        cols = []
        for c in self.columns:
            series = frame[c] if c in frame.columns else pd.Series(np.nan, index=frame.index)
            cols.append(series.fillna(self.medians[c]).to_numpy(dtype=float))
        return np.column_stack(cols) if cols else np.zeros((len(frame), 0))

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Returns a 0/1 anomaly flag per row (1 = flagged anomalous)."""
        if not self.columns or frame.empty:
            return np.zeros(len(frame), dtype=int)
        raw = self.model.predict(self._matrix(frame))  # sklearn convention: -1 anomaly, 1 normal
        return (raw == -1).astype(int)


def fit_isolation_forest(
    train_frame: pd.DataFrame, *, contamination: float = 0.09, n_estimators: int = 100, seed: int = 20260912
) -> IsolationForestBaseline:
    """Fit on the dataset's own labelled-normal training period (never on prediction rows)."""
    cols = _usable_columns(train_frame)
    if not cols:
        raise ValueError("no CARE feature column has enough non-null training observations")
    medians = {c: float(train_frame[c].median(skipna=True)) for c in cols}
    X = np.column_stack([train_frame[c].fillna(medians[c]).to_numpy(dtype=float) for c in cols])
    model = IsolationForest(n_estimators=n_estimators, contamination=contamination, random_state=seed).fit(X)
    return IsolationForestBaseline(columns=cols, medians=medians, model=model)


@dataclass(frozen=True)
class ZScoreThresholdBaseline:
    """A simple residual baseline: flag a row if any channel is `z_threshold` std from its
    own training-period mean. Deliberately naive (no peer comparison, no environmental
    gating) so it is a *weaker* comparator than RAI's internal champion, not a rebrand of it.
    """

    columns: list[str]
    means: dict[str, float]
    stds: dict[str, float]
    z_threshold: float = 3.0

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        if frame.empty:
            return np.zeros(0, dtype=int)
        flags = np.zeros(len(frame), dtype=bool)
        for c in self.columns:
            if c not in frame.columns or self.stds[c] <= 0:
                continue
            z = (frame[c].to_numpy(dtype=float) - self.means[c]) / self.stds[c]
            flags |= np.abs(np.nan_to_num(z, nan=0.0)) >= self.z_threshold
        return flags.astype(int)


def fit_zscore_threshold(train_frame: pd.DataFrame, *, z_threshold: float = 3.0) -> ZScoreThresholdBaseline:
    cols = _usable_columns(train_frame)
    means = {c: float(train_frame[c].mean(skipna=True)) for c in cols}
    stds = {c: float(train_frame[c].std(skipna=True)) for c in cols}
    return ZScoreThresholdBaseline(columns=cols, means=means, stds=stds, z_threshold=z_threshold)
