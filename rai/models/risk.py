"""Failure-risk scoring.

A deliberate modelling choice: this is **logistic regression with isotonic calibration**, not
a gradient-boosted tree. The dataset contains six independent equipment-failure episodes.
Interval-level rows from those episodes number in the thousands, but the *effective* sample
size is six, and a boosted tree given thousands of correlated rows from six episodes will
produce an impressive-looking score that is memorising six machines. Logistic regression on a
handful of engineered trajectory features is the honest capacity for the data available, and
its coefficients double as the risk drivers the interface displays.

Validation is leave-one-asset-out. Splitting these rows at random would place the same
episode on both sides of the split and report near-perfect performance, which would be
meaningless.

The non-equipment scenarios — soiling, sensor drift, curtailment, cloud, icing — are labelled
**negative**. The model is therefore trained to distinguish degradation from the things that
merely look like it, rather than to detect "something is unusual".
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from rai.config import FLEET, MODELS, settings
from rai.schemas import (
    AnomalyEvidence,
    EnvironmentEvidence,
    EnvironmentVerdict,
    PeerEvidence,
    PeerVerdict,
    RiskAssessment,
    RiskBand,
    SensorHealth,
)

log = logging.getLogger(__name__)

RISK_MODEL_PATH = MODELS / "risk_model.json"

FEATURE_NAMES = [
    "peak_abs_z",
    "thermal_z",
    "vibration_z",
    "power_residual_pct",
    "trend_per_day_norm",
    "persistence_hours",
    "changepoint_score",
    "peer_specific",
    "environment_unexplained",
    "sensor_ok",
]

BAND_THRESHOLDS = [
    (0.75, RiskBand.CRITICAL),
    (0.50, RiskBand.HIGH),
    (0.25, RiskBand.ELEVATED),
]


@dataclass
class RiskFeatures:
    values: dict[str, float]

    def vector(self) -> np.ndarray:
        return np.array([self.values.get(name, 0.0) for name in FEATURE_NAMES], dtype=float)


def build_features(
    anomaly: AnomalyEvidence,
    peers: PeerEvidence | None,
    environment: EnvironmentEvidence | None,
) -> RiskFeatures:
    """Trajectory features. Every one is computable at time t from data at or before t."""
    by_name = {s.name: s for s in anomaly.signals}

    def z_of(*names: str) -> float:
        values = [abs(by_name[n].z_score or 0.0) for n in names if n in by_name]
        return max(values) if values else 0.0

    power_signal = by_name.get("power_kw") or by_name.get("ac_power_kw")
    dominant = by_name.get(anomaly.dominant_signal or "")

    trend = abs(dominant.trend_per_day or 0.0) if dominant else 0.0
    sigma = (dominant.baseline_sigma or 1.0) if dominant else 1.0
    changepoint = next(
        (d.score for d in anomaly.detectors if d.detector == "changepoint"), 0.0
    )

    return RiskFeatures(
        {
            "peak_abs_z": min(z_of(*by_name.keys()), 10.0),
            "thermal_z": min(
                z_of("gearbox_oil_temp_c", "generator_winding_temp_c", "main_bearing_temp_c",
                     "inverter_temp_c"),
                10.0,
            ),
            "vibration_z": min(z_of("drivetrain_vibration_mms"), 10.0),
            "power_residual_pct": float(
                np.clip(-(power_signal.residual_pct or 0.0) if power_signal else 0.0, -30, 30)
            ),
            "trend_per_day_norm": float(np.clip(trend / max(sigma, 1e-6), 0.0, 10.0)),
            "persistence_hours": float(np.clip(anomaly.persistence_hours, 0.0, 240.0)),
            "changepoint_score": float(changepoint),
            "peer_specific": (
                1.0
                if peers and peers.verdict is PeerVerdict.ASSET_SPECIFIC
                else (-1.0 if peers and peers.verdict is PeerVerdict.FLEET_WIDE else 0.0)
            ),
            "environment_unexplained": (
                1.0 - environment.explains_fraction if environment else 0.5
            ),
            "sensor_ok": (
                1.0 if (environment is None or environment.sensor_health is SensorHealth.OK) else 0.0
            ),
        }
    )


# --------------------------------------------------------------------------- heuristic path


def _heuristic_score(features: RiskFeatures) -> float:
    """Transparent fallback used until a calibrated model exists.

    Weights are declared, not fitted, and the function is monotone in every input, so its
    behaviour is fully predictable. It is labelled as uncalibrated wherever it is surfaced.
    """
    v = features.values
    score = 0.0
    score += 0.085 * min(v["peak_abs_z"], 8.0)
    score += 0.055 * min(v["thermal_z"], 8.0)
    score += 0.050 * min(v["vibration_z"], 8.0)
    score += 0.010 * np.clip(v["power_residual_pct"], 0.0, 25.0)
    score += 0.030 * min(v["trend_per_day_norm"], 6.0)
    score += 0.0016 * min(v["persistence_hours"], 120.0)
    score += 0.12 * v["changepoint_score"]
    score += 0.12 * v["peer_specific"]
    score += 0.18 * (v["environment_unexplained"] - 0.5)
    score -= 0.35 * (1.0 - v["sensor_ok"])
    return float(np.clip(score, 0.0, 0.99))


# --------------------------------------------------------------------------- scoring


class RiskModel:
    def __init__(
        self,
        scaler: StandardScaler | None = None,
        classifier: LogisticRegression | None = None,
        calibrator: IsotonicRegression | None = None,
        metrics: dict | None = None,
    ) -> None:
        self.scaler = scaler
        self.classifier = classifier
        self.calibrator = calibrator
        self.metrics = metrics or {}

    @property
    def is_fitted(self) -> bool:
        return self.classifier is not None and self.scaler is not None

    def probability(self, features: RiskFeatures) -> tuple[float, str]:
        if not self.is_fitted:
            return _heuristic_score(features), "uncalibrated_heuristic"
        matrix = self.scaler.transform(features.vector().reshape(1, -1))
        raw = float(self.classifier.predict_proba(matrix)[0, 1])
        if self.calibrator is not None:
            return float(self.calibrator.predict([raw])[0]), "isotonic"
        return raw, "logistic_uncalibrated"

    def drivers(self, features: RiskFeatures) -> dict[str, float]:
        """Normalised contribution of each feature, for the interface's driver bars."""
        if not self.is_fitted:
            v = features.values
            raw = {
                "vibration_trend": 0.050 * min(v["vibration_z"], 8.0)
                + 0.030 * min(v["trend_per_day_norm"], 6.0),
                "thermal_residual": 0.055 * min(v["thermal_z"], 8.0),
                "power_residual": 0.010 * np.clip(v["power_residual_pct"], 0.0, 25.0),
                "persistence": 0.0016 * min(v["persistence_hours"], 120.0),
                "peer_isolation": max(0.12 * v["peer_specific"], 0.0),
                "environment_ruled_out": max(0.18 * (v["environment_unexplained"] - 0.5), 0.0),
            }
        else:
            scaled = self.scaler.transform(features.vector().reshape(1, -1))[0]
            contributions = scaled * self.classifier.coef_[0]
            raw = {
                name: float(max(value, 0.0))
                for name, value in zip(FEATURE_NAMES, contributions, strict=True)
            }
        total = sum(raw.values())
        if total <= 0:
            return {}
        return {k: round(v / total, 3) for k, v in sorted(raw.items(), key=lambda kv: -kv[1])[:5]}

    @classmethod
    def load(cls) -> RiskModel:
        if not RISK_MODEL_PATH.exists():
            return cls()
        import pickle

        payload = json.loads(RISK_MODEL_PATH.read_text(encoding="utf-8"))
        blob = MODELS / "risk_model.pkl"
        if not blob.exists():
            return cls(metrics=payload.get("metrics", {}))
        with blob.open("rb") as fh:
            parts = pickle.load(fh)
        return cls(
            scaler=parts.get("scaler"),
            classifier=parts.get("classifier"),
            calibrator=parts.get("calibrator"),
            metrics=payload.get("metrics", {}),
        )


_cached: RiskModel | None = None


def get_model() -> RiskModel:
    global _cached
    if _cached is None:
        _cached = RiskModel.load()
    return _cached


def reset_cache() -> None:
    global _cached
    _cached = None


def band_for(score: float) -> RiskBand:
    for threshold, band in BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return RiskBand.LOW


def risk_window(score: float, features: RiskFeatures) -> tuple[int, int] | None:
    """Coarse projected failure window. Deliberately wide — a narrow one would be false precision."""
    if score < 0.25:
        return None
    trend = features.values.get("trend_per_day_norm", 0.0)
    if score >= 0.75:
        return (3, 10) if trend > 2.0 else (5, 14)
    if score >= 0.50:
        return (7, 21) if trend > 1.0 else (10, 30)
    return (21, 60)


def assess(
    anomaly: AnomalyEvidence,
    peers: PeerEvidence | None,
    environment: EnvironmentEvidence | None,
) -> RiskAssessment:
    """Score failure risk from the evidence layers."""
    features = build_features(anomaly, peers, environment)
    model = get_model()
    probability, calibration = model.probability(features)

    # Hard suppressions. These are policy, not statistics: a commanded reduction or a lying
    # sensor must never present as equipment risk, whatever the residuals look like.
    if environment is not None:
        if environment.curtailment_detected:
            probability = min(probability, 0.05)
        elif environment.sensor_health is SensorHealth.FAILED:
            probability = min(probability, 0.12)
        elif environment.verdict is EnvironmentVerdict.ENVIRONMENTAL:
            probability = min(probability, 0.15)
    if anomaly.persistence_hours < settings.min_persistence_hours:
        probability = min(probability, 0.45)

    return RiskAssessment(
        risk_score=round(float(np.clip(probability, 0.0, 1.0)), 3),
        risk_band=band_for(probability),
        horizon_days=30,
        risk_window_days=risk_window(probability, features),
        calibration=calibration,
        drivers=model.drivers(features),
    )


# --------------------------------------------------------------------------- training


def train_risk_model(horizon_days: int = 30) -> dict:
    """Fit and honestly validate the risk model with leave-one-asset-out grouping."""
    from rai.models.pipeline import build_training_snapshots

    snapshots = build_training_snapshots(horizon_days=horizon_days)
    if not snapshots:
        return {"status": "no_snapshots", "calibration": None}

    frame = pd.DataFrame(snapshots)
    positives = int(frame.label.sum())
    episodes = frame[frame.label == 1].asset_id.nunique()

    if positives < 50 or episodes < 3:
        log.warning(
            "risk model not fitted: %d positive rows from %d episodes is too thin",
            positives, episodes,
        )
        return {
            "status": "insufficient_data",
            "positive_rows": positives,
            "episodes": episodes,
            "note": "heuristic scorer remains active and is reported as uncalibrated",
            "calibration": None,
        }

    X = frame[FEATURE_NAMES].to_numpy(dtype=float)
    y = frame.label.to_numpy(dtype=int)
    groups = frame.asset_id.to_numpy()

    # Leave-one-asset-out: an episode never appears on both sides of the split.
    oof = np.full(len(y), np.nan)
    for asset_id in np.unique(groups):
        test = groups == asset_id
        if test.all() or len(np.unique(y[~test])) < 2:
            continue
        scaler = StandardScaler().fit(X[~test])
        clf = LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced")
        clf.fit(scaler.transform(X[~test]), y[~test])
        oof[test] = clf.predict_proba(scaler.transform(X[test]))[:, 1]

    evaluated = np.isfinite(oof)
    metrics: dict = {
        "n_rows": int(len(y)),
        "positive_rows": positives,
        "episodes": int(episodes),
        "validation": "leave_one_asset_out",
    }
    if evaluated.sum() > 0 and len(np.unique(y[evaluated])) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y[evaluated], oof[evaluated])), 4)
        metrics["brier_score"] = round(float(brier_score_loss(y[evaluated], oof[evaluated])), 4)

    # Final model on all data, calibrated on the out-of-fold predictions so the calibration
    # itself is not fitted on in-sample scores.
    scaler = StandardScaler().fit(X)
    classifier = LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced")
    classifier.fit(scaler.transform(X), y)

    calibrator = None
    if evaluated.sum() > 100 and len(np.unique(y[evaluated])) > 1:
        calibrator = IsotonicRegression(out_of_bounds="clip").fit(oof[evaluated], y[evaluated])
        metrics["calibration"] = "isotonic"
    else:
        metrics["calibration"] = "logistic_uncalibrated"

    import pickle

    with (MODELS / "risk_model.pkl").open("wb") as fh:
        pickle.dump(
            {"scaler": scaler, "classifier": classifier, "calibrator": calibrator}, fh
        )
    RISK_MODEL_PATH.write_text(
        json.dumps(
            {
                "features": FEATURE_NAMES,
                "coefficients": dict(
                    zip(FEATURE_NAMES, classifier.coef_[0].round(4).tolist(), strict=True)
                ),
                "metrics": metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    reset_cache()
    metrics["status"] = "fitted"
    return metrics


def fleet_assets() -> list[str]:
    return [a.asset_id for a in FLEET]
