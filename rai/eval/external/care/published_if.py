"""Published CARE Isolation Forest baseline reproduction.

Reproduces the exact baseline methodology from Gück, Roelofs & Faulstich (2024), §4.2.1:
- Model: Isolation Forest
- n_estimators = 100
- contamination = 0.09
- PCA = Retains 99% of total variance
- Seed = Pinned for exact reproducibility
- Train/Test separation: Fitted solely on the dataset's 'train' split
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishedIsolationForestBaseline:
    """Published CARE Isolation Forest baseline (PCA 99% + IF 100 trees, 0.09 contamination)."""

    columns: list[str]
    medians: dict[str, float]
    pca: PCA | None
    model: IsolationForest
    provenance: dict[str, Any]

    def _prepare_matrix(self, frame: pd.DataFrame) -> np.ndarray:
        if not self.columns or frame.empty:
            return np.zeros((len(frame), 0), dtype=float)
        cols_data: list[np.ndarray] = []
        for c in self.columns:
            if c in frame.columns:
                s = frame[c].to_numpy(dtype=float)
                # Fill missing with train median
                med = self.medians.get(c, 0.0)
                s = np.where(np.isfinite(s), s, med)
            else:
                s = np.full(len(frame), self.medians.get(c, 0.0), dtype=float)
            cols_data.append(s)
        return np.column_stack(cols_data)

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Return binary anomaly flags (1=anomaly, 0=normal) on the prediction frame."""
        if not self.columns or frame.empty:
            return np.zeros(len(frame), dtype=int)

        X = self._prepare_matrix(frame)
        X_trans = self.pca.transform(X) if self.pca is not None else X

        # sklearn convention: -1 indicates anomaly, 1 indicates normal
        raw_pred = self.model.predict(X_trans)
        return (raw_pred == -1).astype(int)


def fit_published_isolation_forest(
    train_frame: pd.DataFrame,
    columns: list[str],
    *,
    contamination: float = 0.09,
    n_estimators: int = 100,
    seed: int = 20260912,
    feature_policy: str = "care_common",
) -> PublishedIsolationForestBaseline:
    """Fit published Isolation Forest with PCA 99% variance retention on train split."""
    if not columns:
        raise ValueError("At least one column required to fit PublishedIsolationForestBaseline")

    # Filter columns with sufficient valid numeric observations
    valid_cols = [
        c
        for c in columns
        if c in train_frame.columns
        and pd.api.types.is_numeric_dtype(train_frame[c])
        and train_frame[c].notna().sum() >= 5
    ]
    if not valid_cols:
        raise ValueError("No valid numeric columns with >= 5 observations found in train_frame")

    medians: dict[str, float] = {}
    cols_data: list[np.ndarray] = []
    for c in valid_cols:
        s = train_frame[c].to_numpy(dtype=float)
        med = float(np.nanmedian(s)) if np.isfinite(s).any() else 0.0
        medians[c] = med
        s_filled = np.where(np.isfinite(s), s, med)
        cols_data.append(s_filled)

    X = np.column_stack(cols_data)

    # PCA 99% variance policy: only applied if > 1 feature and non-zero variance exists
    pca_model: PCA | None = None
    n_components_retained = X.shape[1]
    variance_explained = 1.0

    if X.shape[1] > 1 and np.var(X, axis=0).sum() > 1e-8:
        try:
            # When n_components is float in (0, 1), selects the number of components
            # such that the amount of variance that needs to be explained is greater than the percentage
            pca = PCA(n_components=0.99, svd_solver="full", random_state=seed)
            X_pca = pca.fit_transform(X)
            pca_model = pca
            n_components_retained = int(X_pca.shape[1])
            variance_explained = float(np.sum(pca.explained_variance_ratio_))
            X_fit = X_pca
        except Exception as e:
            log.warning("PCA 99% variance fit fallback to raw features due to: %s", e)
            X_fit = X
    else:
        X_fit = X

    iso_model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=seed,
    ).fit(X_fit)

    provenance = {
        "baseline_name": "CARE_PUBLISHED_IF",
        "reference": "Gück, Roelofs & Faulstich (2024), Section 4.2.1",
        "sklearn_version": sklearn.__version__,
        "pca_policy": "retain_99_pct_variance",
        "pca_components_retained": n_components_retained,
        "pca_variance_explained": round(variance_explained, 4),
        "raw_features_count": len(valid_cols),
        "n_estimators": n_estimators,
        "contamination": contamination,
        "random_seed": seed,
        "seed_classification": "REPRODUCIBILITY_CHOICE",
        "feature_policy": feature_policy,
    }

    return PublishedIsolationForestBaseline(
        columns=valid_cols,
        medians=medians,
        pca=pca_model,
        model=iso_model,
        provenance=provenance,
    )


def fit_rai_compat_isolation_forest(
    train_frame: pd.DataFrame,
    columns: list[str],
    *,
    contamination: float = 0.09,
    n_estimators: int = 100,
    seed: int = 20260912,
    feature_policy: str = "care_2d",
) -> PublishedIsolationForestBaseline:
    """Fit RAI-compatible Isolation Forest baseline (uncompressed raw features, no PCA).

    This reproduces the internal baseline used in Gates 5.1 and 5.2.
    """
    if not columns:
        raise ValueError("At least one column required to fit RAI-compatible Isolation Forest")

    valid_cols = [
        c
        for c in columns
        if c in train_frame.columns
        and pd.api.types.is_numeric_dtype(train_frame[c])
        and train_frame[c].notna().sum() >= 5
    ]
    if not valid_cols:
        raise ValueError("No valid numeric columns with >= 5 observations found in train_frame")

    medians: dict[str, float] = {}
    cols_data: list[np.ndarray] = []
    for c in valid_cols:
        s = train_frame[c].to_numpy(dtype=float)
        med = float(np.nanmedian(s)) if np.isfinite(s).any() else 0.0
        medians[c] = med
        s_filled = np.where(np.isfinite(s), s, med)
        cols_data.append(s_filled)

    X = np.column_stack(cols_data)

    iso_model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=seed,
    ).fit(X)

    provenance = {
        "baseline_name": "RAI_COMPAT_IF",
        "reference": "Gate 5.1 / 5.2 internal baseline",
        "sklearn_version": sklearn.__version__,
        "pca_policy": "none",
        "raw_features_count": len(valid_cols),
        "n_estimators": n_estimators,
        "contamination": contamination,
        "random_seed": seed,
        "seed_classification": "REPRODUCIBILITY_CHOICE",
        "feature_policy": feature_policy,
    }

    return PublishedIsolationForestBaseline(
        columns=valid_cols,
        medians=medians,
        pca=None,
        model=iso_model,
        provenance=provenance,
    )

