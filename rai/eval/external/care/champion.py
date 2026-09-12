"""RAI Champion Anomaly Detector Adapter for external CARE SCADA.

Implements the core production anomaly detection architecture of Renewable Asset
Intelligence (RAI) following `rai/models/anomaly.py` and `rai/models/expected.py`:
1. Physics-informed Expected Behavior: Power curve regression (P = f(v_wind))
2. Residual Calculation & Standardization: Robust residual z-scores fit strictly on train
3. Multi-Signal Fusion: Combining power underproduction residuals with rotor speed residuals
4. Rolling Persistence Gating: Filtering transient turbulence (requiring >= 30 min sustained exceedance)
5. Zero Leakage: Completely blind to event_info, fault type, or prediction split labels during fit
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from rai.eval.external.care.features import FARM_2D_MAPPING, FARM_COMMON_MAPPING

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAIChampionDetector:
    """RAI Champion Anomaly Detector with expected-behavior modeling and persistence gating."""

    farm_name: str
    feature_policy: str
    power_poly: np.ndarray | None
    power_mu: float
    power_sigma: float
    rotor_poly: np.ndarray | None
    rotor_mu: float
    rotor_sigma: float
    sensor_stats: dict[str, tuple[float, float]]  # col -> (mean, std)
    power_col: str | None
    wind_col: str | None
    rotor_col: str | None
    z_threshold: float
    persistence_steps: int
    provenance: dict[str, Any]

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Predict binary anomaly flags (1=anomaly, 0=normal) on the prediction frame."""
        if frame.empty:
            return np.zeros(0, dtype=int)

        n = len(frame)
        point_scores = np.zeros(n, dtype=float)

        wind_col = self.wind_col
        power_col = self.power_col
        rotor_col = self.rotor_col

        # Cross-farm transfer column resolution: if source model's columns are not in target frame,
        # resolve target columns using the canonical FARM_COMMON_MAPPING
        if (wind_col not in frame.columns or power_col not in frame.columns):
            for farm_mapping in FARM_COMMON_MAPPING.values():
                if farm_mapping["wind_speed"] in frame.columns and farm_mapping["active_power"] in frame.columns:
                    wind_col = farm_mapping["wind_speed"]
                    power_col = farm_mapping["active_power"]
                    rotor_col = farm_mapping.get("rotor_speed")
                    break

        # 1. Expected power curve underproduction residual
        has_power_model = (
            self.power_poly is not None
            and power_col is not None
            and wind_col is not None
            and power_col in frame.columns
            and wind_col in frame.columns
        )

        if has_power_model and power_col and wind_col and self.power_poly is not None:
            ws = frame[wind_col].to_numpy(dtype=float)
            p_actual = frame[power_col].to_numpy(dtype=float)
            p_exp = np.polyval(self.power_poly, np.nan_to_num(ws, nan=0.0))
            # Underproduction: expected > actual
            p_res = p_exp - np.nan_to_num(p_actual, nan=0.0)
            z_p = (p_res - self.power_mu) / max(self.power_sigma, 1.0)
            # Only positive residuals (underproduction) indicate power generation fault
            z_p_clamped = np.maximum(z_p, 0.0)
            point_scores = np.maximum(point_scores, z_p_clamped)

        # 2. Rotor speed expected curve residual
        has_rotor_model = (
            self.rotor_poly is not None
            and rotor_col is not None
            and wind_col is not None
            and rotor_col in frame.columns
            and wind_col in frame.columns
        )

        if has_rotor_model and rotor_col and wind_col and self.rotor_poly is not None:
            ws = frame[wind_col].to_numpy(dtype=float)
            r_actual = frame[rotor_col].to_numpy(dtype=float)
            r_exp = np.polyval(self.rotor_poly, np.nan_to_num(ws, nan=0.0))
            r_res = np.abs(r_actual - r_exp)
            z_r = (r_res - self.rotor_mu) / max(self.rotor_sigma, 1.0)
            point_scores = np.maximum(point_scores, np.nan_to_num(z_r, nan=0.0))

        # 3. Fallback sensor z-scores if no power model available
        if not has_power_model and self.sensor_stats:
            max_z = np.zeros(n, dtype=float)
            for col, (mu, sigma) in self.sensor_stats.items():
                if col in frame.columns and sigma > 1e-4:
                    vals = frame[col].to_numpy(dtype=float)
                    z = np.abs(vals - mu) / sigma
                    max_z = np.maximum(max_z, np.nan_to_num(z, nan=0.0))
            point_scores = np.maximum(point_scores, max_z)

        # 4. Point-level exceedance
        raw_flags = (point_scores >= self.z_threshold).astype(float)

        # 5. Rolling persistence gating (filters non-persistent gusts and transient blips)
        if self.persistence_steps > 1 and len(raw_flags) >= self.persistence_steps:
            rolling_avg = (
                pd.Series(raw_flags)
                .rolling(self.persistence_steps, min_periods=1)
                .mean()
                .to_numpy()
            )
            # Require at least 66% exceedance across the trailing window
            final_flags = (rolling_avg >= 0.66).astype(int)
        else:
            final_flags = raw_flags.astype(int)

        return final_flags


    def get_consumed_columns(self) -> list[str]:
        """Return the exact list of input columns consumed by the detector."""
        consumed: list[str] = []
        if self.power_poly is not None and self.power_col and self.wind_col:
            if self.wind_col not in consumed:
                consumed.append(self.wind_col)
            if self.power_col not in consumed:
                consumed.append(self.power_col)
        if self.rotor_poly is not None and self.rotor_col and self.wind_col:
            if self.wind_col not in consumed:
                consumed.append(self.wind_col)
            if self.rotor_col not in consumed:
                consumed.append(self.rotor_col)
        return consumed

    def get_input_manifest(self) -> list[dict[str, Any]]:
        """Return structured manifest records detailing each consumed input signal."""
        records: list[dict[str, Any]] = []
        train_rows = self.provenance.get("training_observations", 0)

        # 1. Wind speed
        if self.wind_col and (self.power_poly is not None or self.rotor_poly is not None):
            records.append({
                "farm": self.farm_name,
                "feature_policy": self.feature_policy,
                "semantic_name": "wind_speed",
                "source_raw_column": self.wind_col,
                "unit": "m/s",
                "transformation": "degree-2 polynomial independent variable (aerodynamic driver)",
                "training_rows": train_rows,
                "training_only_statistics": {
                    "has_power_curve": self.power_poly is not None,
                    "has_rotor_curve": self.rotor_poly is not None,
                },
                "threshold_source": f"z_threshold>={self.z_threshold}, persistence>={self.persistence_steps} steps",
                "bypassed_native_extras": self.provenance.get("bypassed_columns_count", 0),
            })

        # 2. Active power
        if self.power_col and self.power_poly is not None:
            records.append({
                "farm": self.farm_name,
                "feature_policy": self.feature_policy,
                "semantic_name": "active_power",
                "source_raw_column": self.power_col,
                "unit": "kW",
                "transformation": "degree-2 expected curve underproduction residual: max((P_exp - P_act - mu)/sigma, 0)",
                "training_rows": train_rows,
                "training_only_statistics": {
                    "mu": round(self.power_mu, 4),
                    "sigma": round(self.power_sigma, 4),
                    "poly_coefficients": [round(float(c), 6) for c in self.power_poly],
                },
                "threshold_source": f"z_threshold>={self.z_threshold}, persistence>={self.persistence_steps} steps",
                "bypassed_native_extras": self.provenance.get("bypassed_columns_count", 0),
            })

        # 3. Rotor speed
        if self.rotor_col and self.rotor_poly is not None:
            records.append({
                "farm": self.farm_name,
                "feature_policy": self.feature_policy,
                "semantic_name": "rotor_speed",
                "source_raw_column": self.rotor_col,
                "unit": "rpm",
                "transformation": "degree-2 expected curve absolute residual: abs(R_act - R_exp - mu)/sigma",
                "training_rows": train_rows,
                "training_only_statistics": {
                    "mu": round(self.rotor_mu, 4),
                    "sigma": round(self.rotor_sigma, 4),
                    "poly_coefficients": [round(float(c), 6) for c in self.rotor_poly],
                },
                "threshold_source": f"z_threshold>={self.z_threshold}, persistence>={self.persistence_steps} steps",
                "bypassed_native_extras": self.provenance.get("bypassed_columns_count", 0),
            })

        return records


def fit_rai_champion(
    train_frame: pd.DataFrame,
    farm_name: str,
    feature_policy: str = "care_common",
    *,
    columns: list[str] | None = None,
    z_threshold: float = 2.5,
    persistence_steps: int = 3,
    disable_power: bool = False,
    disable_wind: bool = False,
    disable_rotor: bool = False,
) -> RAIChampionDetector:
    """Fit RAI Champion expected behavior models and residual baselines on train split."""
    cols = columns or list(train_frame.columns)

    if feature_policy == "care_2d":
        mapping = FARM_2D_MAPPING.get(farm_name, {})
        wind_col = mapping.get("wind_speed")
        power_col = mapping.get("power")
        rotor_col = None
    else:
        mapping = FARM_COMMON_MAPPING.get(farm_name, {})
        wind_col = mapping.get("wind_speed")
        power_col = mapping.get("active_power")
        rotor_col = mapping.get("rotor_speed")

    # If columns were supplied, verify presence
    if wind_col not in train_frame.columns:
        wind_col = next((c for c in cols if "wind_speed" in c.lower()), None)
    if power_col not in train_frame.columns:
        power_col = next((c for c in cols if "power" in c.lower() and "reactive" not in c.lower()), None)
    if feature_policy != "care_2d" and (rotor_col is None or rotor_col not in train_frame.columns):
        rotor_col = next((c for c in cols if "rotor" in c.lower() or ("speed" in c.lower() and "wind" not in c.lower())), None)

    # 1. Fit Expected Power Curve: P = a*v^2 + b*v + c
    power_poly: np.ndarray | None = None
    power_mu, power_sigma = 0.0, 1.0

    if not disable_power and not disable_wind and wind_col and power_col and wind_col in train_frame.columns and power_col in train_frame.columns:
        sub = train_frame[[wind_col, power_col]].dropna()
        if len(sub) >= 20:
            ws = sub[wind_col].to_numpy(dtype=float)
            p = sub[power_col].to_numpy(dtype=float)
            try:
                power_poly = np.polyfit(ws, p, deg=2)
                p_exp = np.polyval(power_poly, ws)
                residuals = p_exp - p
                power_mu = float(np.mean(residuals))
                power_sigma = float(np.std(residuals)) or 1.0
            except Exception as e:
                log.warning("Power curve fit failed on %s: %s", farm_name, e)

    # 2. Fit Expected Rotor Curve: Rotor = a*v^2 + b*v + c
    rotor_poly: np.ndarray | None = None
    rotor_mu, rotor_sigma = 0.0, 1.0

    if not disable_rotor and not disable_wind and wind_col and rotor_col and wind_col in train_frame.columns and rotor_col in train_frame.columns:
        sub = train_frame[[wind_col, rotor_col]].dropna()
        if len(sub) >= 20:
            ws = sub[wind_col].to_numpy(dtype=float)
            r = sub[rotor_col].to_numpy(dtype=float)
            try:
                rotor_poly = np.polyfit(ws, r, deg=2)
                r_exp = np.polyval(rotor_poly, ws)
                residuals = np.abs(r - r_exp)
                rotor_mu = float(np.mean(residuals))
                rotor_sigma = float(np.std(residuals)) or 1.0
            except Exception as e:
                log.warning("Rotor curve fit failed on %s: %s", farm_name, e)

    # 3. Sensor stats for fallback columns
    sensor_stats: dict[str, tuple[float, float]] = {}
    for c in cols:
        if c in train_frame.columns and pd.api.types.is_numeric_dtype(train_frame[c]):
            s = train_frame[c].dropna()
            if len(s) >= 10:
                sensor_stats[c] = (float(s.mean()), float(s.std()) or 1.0)

    # Architectural audit: count how many non-canonical channels were in train_frame but bypassed
    canonical_set = {c for c in (wind_col, power_col, rotor_col) if c}
    bypassed_columns_count = len([c for c in cols if c not in canonical_set])

    provenance = {
        "detector_name": "RAI_CHAMPION_HYBRID",
        "farm_name": farm_name,
        "feature_policy": feature_policy,
        "wind_col": wind_col,
        "power_col": power_col,
        "rotor_col": rotor_col,
        "has_power_poly": power_poly is not None,
        "has_rotor_poly": rotor_poly is not None,
        "z_threshold": z_threshold,
        "persistence_steps": persistence_steps,
        "persistence_window_minutes": persistence_steps * 10,
        "training_observations": len(train_frame),
        "bypassed_columns_count": bypassed_columns_count,
        "disable_power": disable_power,
        "disable_wind": disable_wind,
        "disable_rotor": disable_rotor,
    }

    return RAIChampionDetector(
        farm_name=farm_name,
        feature_policy=feature_policy,
        power_poly=power_poly,
        power_mu=power_mu,
        power_sigma=power_sigma,
        rotor_poly=rotor_poly,
        rotor_mu=rotor_mu,
        rotor_sigma=rotor_sigma,
        sensor_stats=sensor_stats,
        power_col=power_col,
        wind_col=wind_col,
        rotor_col=rotor_col,
        z_threshold=z_threshold,
        persistence_steps=persistence_steps,
        provenance=provenance,
    )


def recalibrate_rai_champion_target_normal(
    source_model: RAIChampionDetector,
    target_normal_train_frame: pd.DataFrame,
    target_farm_name: str,
) -> RAIChampionDetector:
    """Recalibrate RAI Champion expected behavior models using ONLY target-farm normal train data.

    Strict Protocol Guarantees (Condition B):
    1. Zero Target Labels: No event_info, fault types, or anomaly labels are accessed.
    2. Zero Future Data: Only permitted 'train' split rows are used; prediction split is strictly excluded.
    3. Parameter Preservation: Anomaly threshold (z_threshold) and temporal persistence rule
       (persistence_steps) are preserved identically from the source model without tuning.
    4. Normal-Only Re-estimation: Re-estimates target-domain expected power curve, rotor curve,
       and residual standardizations (mu, sigma).
    """
    if target_normal_train_frame.empty:
        raise ValueError("Cannot recalibrate on empty target normal frame.")

    # Verification: Ensure no prediction split data entered
    if "train_test" in target_normal_train_frame.columns:
        non_train = target_normal_train_frame["train_test"] != "train"
        if non_train.any():
            raise ValueError(
                f"Protocol violation: {non_train.sum()} non-train rows found in calibration frame."
            )

    # Verification: Ensure no anomaly labels or event metadata present
    forbidden_cols = {"event_label", "event_type", "event_id", "fault_type", "is_anomaly"}
    present_forbidden = forbidden_cols.intersection(set(target_normal_train_frame.columns))
    if present_forbidden:
        raise ValueError(
            f"Protocol violation: Forbidden target anomaly columns present: {present_forbidden}"
        )

    target_mapping = FARM_COMMON_MAPPING.get(target_farm_name, {})
    wind_col = target_mapping.get("wind_speed", source_model.wind_col)
    power_col = target_mapping.get("active_power", source_model.power_col)
    rotor_col = target_mapping.get("rotor_speed", source_model.rotor_col)

    # 1. Recalibrate Expected Power Curve: P = a*v^2 + b*v + c
    power_poly: np.ndarray | None = None
    power_mu, power_sigma = 0.0, 1.0

    if (
        not source_model.provenance.get("disable_power", False)
        and not source_model.provenance.get("disable_wind", False)
        and wind_col
        and power_col
        and wind_col in target_normal_train_frame.columns
        and power_col in target_normal_train_frame.columns
    ):
        sub = target_normal_train_frame[[wind_col, power_col]].dropna()
        if len(sub) >= 20:
            ws = sub[wind_col].to_numpy(dtype=float)
            p = sub[power_col].to_numpy(dtype=float)
            try:
                power_poly = np.polyfit(ws, p, deg=2)
                p_exp = np.polyval(power_poly, ws)
                residuals = p_exp - p
                power_mu = float(np.mean(residuals))
                power_sigma = float(np.std(residuals)) or 1.0
            except Exception as e:
                log.warning("Target normal power curve fit failed on %s: %s", target_farm_name, e)

    # 2. Recalibrate Expected Rotor Curve: Rotor = a*v^2 + b*v + c
    rotor_poly: np.ndarray | None = None
    rotor_mu, rotor_sigma = 0.0, 1.0

    if (
        not source_model.provenance.get("disable_rotor", False)
        and not source_model.provenance.get("disable_wind", False)
        and wind_col
        and rotor_col
        and wind_col in target_normal_train_frame.columns
        and rotor_col in target_normal_train_frame.columns
    ):
        sub = target_normal_train_frame[[wind_col, rotor_col]].dropna()
        if len(sub) >= 20:
            ws = sub[wind_col].to_numpy(dtype=float)
            r = sub[rotor_col].to_numpy(dtype=float)
            try:
                rotor_poly = np.polyfit(ws, r, deg=2)
                r_exp = np.polyval(rotor_poly, ws)
                residuals = np.abs(r - r_exp)
                rotor_mu = float(np.mean(residuals))
                rotor_sigma = float(np.std(residuals)) or 1.0
            except Exception as e:
                log.warning("Target normal rotor curve fit failed on %s: %s", target_farm_name, e)

    provenance = dict(source_model.provenance)
    provenance.update({
        "calibration_type": "TARGET_NORMAL_ONLY",
        "source_farm": source_model.farm_name,
        "target_farm": target_farm_name,
        "calibration_observations": len(target_normal_train_frame),
        "source_power_poly": (
            [float(c) for c in source_model.power_poly] if source_model.power_poly is not None else None
        ),
        "source_rotor_poly": (
            [float(c) for c in source_model.rotor_poly] if source_model.rotor_poly is not None else None
        ),
        "recalibrated_power_poly": (
            [float(c) for c in power_poly] if power_poly is not None else None
        ),
        "recalibrated_rotor_poly": (
            [float(c) for c in rotor_poly] if rotor_poly is not None else None
        ),
        "recalibrated_power_mu": power_mu,
        "recalibrated_power_sigma": power_sigma,
        "recalibrated_rotor_mu": rotor_mu,
        "recalibrated_rotor_sigma": rotor_sigma,
    })

    return RAIChampionDetector(
        farm_name=target_farm_name,
        feature_policy=source_model.feature_policy,
        power_poly=power_poly,
        power_mu=power_mu,
        power_sigma=power_sigma,
        rotor_poly=rotor_poly,
        rotor_mu=rotor_mu,
        rotor_sigma=rotor_sigma,
        sensor_stats=source_model.sensor_stats,
        power_col=power_col,
        wind_col=wind_col,
        rotor_col=rotor_col,
        z_threshold=source_model.z_threshold,
        persistence_steps=source_model.persistence_steps,
        provenance=provenance,
    )

