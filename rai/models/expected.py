"""Expected-behaviour (normal-behaviour) models.

For every monitored signal we learn what a *healthy* asset would do under the conditions
actually present, then monitor the residual. This is the layer that lets the system say
"down 9% for these conditions" instead of "down 9%", and that distinction is the entire
difference between an alarm that means something and one that fires every cloudy afternoon.

Design choices worth knowing:

* **One fleet model per asset type, plus a per-asset residual baseline.** Training one model
  per asset wastes data and overfits each machine's noise. Training one shared model and then
  calibrating the residual distribution per asset keeps the statistical power while still
  absorbing each machine's individual efficiency and sensor offsets.
* **Physics baseline alongside the learned model.** The density-corrected power curve is kept
  as an interpretable reference so a reviewer can see the learned model is not inventing a
  different machine.
* **Trained exclusively on healthy, productive intervals** taken from the chronological
  training window. A normal-behaviour model that has seen the fault is no longer a
  normal-behaviour model.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

from rai.config import FLEET, MODELS, Asset, get_asset
from rai.features.build import (
    Split,
    build_features,
    chronological_split,
    productive_mask,
    solar_power_features,
    thermal_features,
    vibration_features,
    wind_power_features,
)
from rai.schemas import AssetType
from rai.store import DataUnavailable, load_events, load_telemetry

log = logging.getLogger(__name__)

MODEL_DIR = MODELS
BASELINES_PATH = MODEL_DIR / "baselines.json"
METADATA_PATH = MODEL_DIR / "metadata.json"

XGB_PARAMS: dict[str, Any] = {
    "n_estimators": 400,
    "max_depth": 5,
    "learning_rate": 0.06,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "min_child_weight": 8,
    "reg_lambda": 2.0,
    "random_state": 17,
    "n_jobs": 4,
    "early_stopping_rounds": 40,
}


@dataclass
class ModelSpec:
    key: str
    target: str
    features: list[str]
    asset_type: str
    unit: str


def model_specs() -> list[ModelSpec]:
    return [
        ModelSpec("wind_power", "power_kw", wind_power_features(), "wind_turbine", "kW"),
        ModelSpec(
            "wind_gearbox_temp",
            "gearbox_oil_temp_c",
            thermal_features(AssetType.WIND_TURBINE),
            "wind_turbine",
            "°C",
        ),
        ModelSpec(
            "wind_generator_temp",
            "generator_winding_temp_c",
            thermal_features(AssetType.WIND_TURBINE),
            "wind_turbine",
            "°C",
        ),
        ModelSpec(
            "wind_bearing_temp",
            "main_bearing_temp_c",
            thermal_features(AssetType.WIND_TURBINE),
            "wind_turbine",
            "°C",
        ),
        ModelSpec(
            "wind_vibration",
            "drivetrain_vibration_mms",
            vibration_features(),
            "wind_turbine",
            "mm/s",
        ),
        ModelSpec("solar_power", "ac_power_kw", solar_power_features(), "solar_inverter", "kW"),
        ModelSpec(
            "solar_dc_power",
            "dc_power_kw",
            solar_power_features(),
            "solar_inverter",
            "kW",
        ),
        ModelSpec(
            "solar_inverter_temp",
            "inverter_temp_c",
            thermal_features(AssetType.SOLAR_INVERTER),
            "solar_inverter",
            "°C",
        ),
    ]


SPEC_BY_KEY = {s.key: s for s in model_specs()}

# Which model explains which signal, for the evidence layer.
SIGNAL_MODEL = {
    "power_kw": "wind_power",
    "gearbox_oil_temp_c": "wind_gearbox_temp",
    "generator_winding_temp_c": "wind_generator_temp",
    "main_bearing_temp_c": "wind_bearing_temp",
    "drivetrain_vibration_mms": "wind_vibration",
    "ac_power_kw": "solar_power",
    "dc_power_kw": "solar_dc_power",
    "inverter_temp_c": "solar_inverter_temp",
}


# --------------------------------------------------------------------------- training data


def healthy_cutoff(asset_id: str) -> pd.Timestamp | None:
    """Earliest injected onset for an asset. Training must stop before it."""
    events = load_events(asset_id)
    if not events:
        return None
    return min(pd.Timestamp(e.onset) for e in events)


def asset_training_frame(asset: Asset) -> pd.DataFrame | None:
    """Feature frame restricted to healthy, productive intervals for one asset."""
    try:
        raw = load_telemetry(asset.asset_id)
    except (DataUnavailable, FileNotFoundError):
        return None
    if raw.empty:
        return None

    features = build_features(raw, asset)
    features = features[productive_mask(features)]
    cutoff = healthy_cutoff(asset.asset_id)
    if cutoff is not None:
        features = features[features["ts"] < cutoff]
    return features if not features.empty else None


def assemble(asset_type: AssetType) -> tuple[pd.DataFrame, Split] | None:
    """Pooled healthy training frame for one asset type, plus the chronological split."""
    frames = []
    for asset in FLEET:
        if asset.asset_type is not asset_type:
            continue
        frame = asset_training_frame(asset)
        if frame is not None:
            frames.append(frame)
    if not frames:
        return None
    pooled = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    split = chronological_split(pd.DatetimeIndex(pooled["ts"]))
    return pooled, split


# --------------------------------------------------------------------------- training


def _fit(spec: ModelSpec, pooled: pd.DataFrame, split: Split) -> dict[str, Any] | None:
    columns = [*spec.features, spec.target, "ts"]
    available = [c for c in columns if c in pooled.columns]
    if spec.target not in available:
        return None

    frame = pooled[available].dropna()
    if len(frame) < 500:
        log.warning("%s: only %d usable rows, skipping", spec.key, len(frame))
        return None

    features = [f for f in spec.features if f in frame.columns]
    train = frame[frame.ts <= split.train_end]
    val = frame[(frame.ts > split.train_end) & (frame.ts <= split.val_end)]
    test = frame[frame.ts > split.val_end]
    if train.empty or val.empty or test.empty:
        return None

    model = XGBRegressor(**XGB_PARAMS)
    model.fit(
        train[features],
        train[spec.target],
        eval_set=[(val[features], val[spec.target])],
        verbose=False,
    )

    predictions = model.predict(test[features])
    metrics = {
        "mae": float(mean_absolute_error(test[spec.target], predictions)),
        "rmse": float(np.sqrt(np.mean((test[spec.target].to_numpy() - predictions) ** 2))),
        "r2": float(r2_score(test[spec.target], predictions)),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "unit": spec.unit,
    }
    model.save_model(MODEL_DIR / f"{spec.key}.json")
    log.info("%s: MAE %.3f %s, R2 %.4f", spec.key, metrics["mae"], spec.unit, metrics["r2"])
    return {"metrics": metrics, "features": features}


def train_all() -> dict[str, Any]:
    """Train every expected-behaviour model and write artifacts. Returns real metrics."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"models": {}, "splits": {}}

    pooled_by_type: dict[AssetType, tuple[pd.DataFrame, Split]] = {}
    for asset_type in (AssetType.WIND_TURBINE, AssetType.SOLAR_INVERTER):
        assembled = assemble(asset_type)
        if assembled is None:
            log.warning("no training data for %s", asset_type.value)
            continue
        pooled_by_type[asset_type] = assembled
        report["splits"][asset_type.value] = assembled[1].describe()

    trained_features: dict[str, list[str]] = {}
    for spec in model_specs():
        asset_type = (
            AssetType.WIND_TURBINE if spec.asset_type == "wind_turbine" else AssetType.SOLAR_INVERTER
        )
        if asset_type not in pooled_by_type:
            continue
        pooled, split = pooled_by_type[asset_type]
        outcome = _fit(spec, pooled, split)
        if outcome is not None:
            report["models"][spec.key] = outcome["metrics"]
            trained_features[spec.key] = outcome["features"]

    METADATA_PATH.write_text(
        json.dumps(
            {
                "specs": {k: asdict(v) for k, v in SPEC_BY_KEY.items()},
                "trained_features": trained_features,
                "report": report,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    report["baselines"] = fit_residual_baselines()
    return report


# --------------------------------------------------------------------------- residual baselines


def fit_residual_baselines() -> dict[str, int]:
    """Per-asset residual location and scale, measured on the healthy window only.

    Uses median and MAD rather than mean and standard deviation: a handful of outliers in
    real SCADA would otherwise inflate the scale and mask the very deviations we are looking
    for. The 1.4826 factor makes MAD a consistent estimator of sigma for normal data.
    """
    models = ExpectedModels.load()
    baselines: dict[str, dict[str, dict[str, float]]] = {}

    for asset in FLEET:
        frame = asset_training_frame(asset)
        if frame is None:
            continue
        predictions = models.predict_frame(asset, frame)
        entry: dict[str, dict[str, float]] = {}
        for signal, predicted in predictions.items():
            if signal not in frame.columns:
                continue
            residual = frame[signal].to_numpy(dtype=float) - predicted
            residual = residual[np.isfinite(residual)]
            if residual.size < 100:
                continue
            median = float(np.median(residual))
            mad = float(np.median(np.abs(residual - median)))
            sigma = max(mad * 1.4826, 1e-6)
            entry[signal] = {
                "median": median,
                "sigma": sigma,
                "n": int(residual.size),
                "reference_mean": float(np.mean(np.abs(frame[signal].to_numpy(dtype=float)))),
            }
        if entry:
            baselines[asset.asset_id] = entry

    BASELINES_PATH.write_text(json.dumps(baselines, indent=2), encoding="utf-8")
    return {"assets": len(baselines)}


# --------------------------------------------------------------------------- inference


class ExpectedModels:
    """Loaded models plus per-asset residual baselines."""

    def __init__(
        self,
        boosters: dict[str, XGBRegressor],
        features: dict[str, list[str]],
        baselines: dict[str, dict[str, dict[str, float]]],
    ) -> None:
        self.boosters = boosters
        self.features = features
        self.baselines = baselines

    @classmethod
    def load(cls) -> ExpectedModels:
        if not METADATA_PATH.exists():
            raise FileNotFoundError(
                "expected-behaviour models not trained; run scripts/train.py"
            )
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        features = metadata.get("trained_features", {})

        boosters: dict[str, XGBRegressor] = {}
        for key in features:
            path = MODEL_DIR / f"{key}.json"
            if not path.exists():
                continue
            booster = XGBRegressor()
            booster.load_model(path)
            boosters[key] = booster

        baselines = {}
        if BASELINES_PATH.exists():
            baselines = json.loads(BASELINES_PATH.read_text(encoding="utf-8"))
        return cls(boosters, features, baselines)

    def available(self) -> list[str]:
        return sorted(self.boosters)

    def predict_frame(self, asset: Asset, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        """Expected value for every monitored signal of this asset, aligned to `frame`."""
        out: dict[str, np.ndarray] = {}
        for signal, key in SIGNAL_MODEL.items():
            if key not in self.boosters or signal not in frame.columns:
                continue
            spec = SPEC_BY_KEY[key]
            expected_type = (
                AssetType.WIND_TURBINE
                if spec.asset_type == "wind_turbine"
                else AssetType.SOLAR_INVERTER
            )
            if asset.asset_type is not expected_type:
                continue
            columns = self.features.get(key, spec.features)
            if any(c not in frame.columns for c in columns):
                continue
            matrix = frame[columns].astype(float)
            out[signal] = self.boosters[key].predict(matrix)
        return out

    def baseline(self, asset_id: str, signal: str) -> dict[str, float] | None:
        return self.baselines.get(asset_id, {}).get(signal)

    def z_score(self, asset_id: str, signal: str, residual: float) -> float | None:
        base = self.baseline(asset_id, signal)
        if base is None or not np.isfinite(residual):
            return None
        return float((residual - base["median"]) / base["sigma"])


_cached: ExpectedModels | None = None


def get_models() -> ExpectedModels:
    global _cached
    if _cached is None:
        _cached = ExpectedModels.load()
    return _cached


def reset_cache() -> None:
    global _cached
    _cached = None


def physics_expected_power(asset_id: str, frame: pd.DataFrame) -> np.ndarray | None:
    """Interpretable reference curve, for comparison against the learned model."""
    asset = get_asset(asset_id)
    if asset.asset_type is not AssetType.WIND_TURBINE:
        return None
    from rai.sim.wind import expected_power_reference

    if "wind_speed_ms" not in frame.columns:
        return None
    return expected_power_reference(
        frame["wind_speed_ms"].to_numpy(dtype=float),
        frame["air_density"].to_numpy(dtype=float),
        asset,
    )
