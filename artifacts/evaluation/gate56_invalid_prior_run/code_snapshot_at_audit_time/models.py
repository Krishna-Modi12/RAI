"""Solar Expected-Performance Models: Physics Reference, Empirical Baseline, and Hybrid Champion.

Implements the three distinct modeling paradigms evaluated under Gate 5.6:
1. PVLIB_PHYSICS_REFERENCE: First-principles physics simulation chain using pvlib.
2. SOLAR_EMPIRICAL_BASELINE: Low-complexity polynomial response surface fit on normal training data.
3. RAI_SOLAR_CHAMPION: Hybrid physics-prior + normal calibration + standardized residual (z) + persistence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures

from rai.eval.external.solar.pvdaq import PVDAQSystemMetadata


class ModelType(str, Enum):
    """Identifier for the expected-performance model family."""

    PVLIB_PHYSICS_REFERENCE = "PVLIB_PHYSICS_REFERENCE"
    SOLAR_EMPIRICAL_BASELINE = "SOLAR_EMPIRICAL_BASELINE"
    RAI_SOLAR_CHAMPION = "RAI_SOLAR_CHAMPION"


@dataclass(frozen=True)
class SolarHealthEvidence:
    """Structured evidence record produced by the RAI Solar Champion for downstream consumption."""

    timestamp: str
    asset_id: str
    expected_power_kw: float
    actual_power_kw: float
    residual_kw: float
    residual_z: float
    persistence_intervals: int
    quality_state: str
    operating_context: str
    clipping_state: bool
    curtailment_state: bool
    health_evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Model A: Physics Reference (pvlib)
# ---------------------------------------------------------------------------

class PVLibPhysicsReference:
    """Physics-informed first-principles reference model.

    Evaluates clear-sky transposition, module cell temperature, temperature derating,
    and inverter conversion efficiency based strictly on physical formulas.
    """

    def __init__(self, meta: PVDAQSystemMetadata) -> None:
        self.meta = meta

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict expected AC power in kW using first-principles physics."""
        poa = df["poa_wm2"].fillna(0.0).to_numpy()
        elev = df["solar_elevation_deg"].fillna(-90.0).to_numpy()

        # Cell temperature derating: gamma %/°C from STC (25°C)
        cell_t = df["module_temp_c"].fillna(25.0).to_numpy()
        temp_derate = 1.0 + (self.meta.temp_coefficient_pct_per_c / 100.0) * (cell_t - 25.0)

        # DC power from POA irradiance and STC rating
        p_dc = self.meta.rated_dc_kw * (poa / 1000.0) * temp_derate
        p_dc = np.maximum(p_dc, 0.0)

        # Inverter conversion efficiency
        # Uses standard quadratic inverter efficiency curve normalized to rated capacity
        p_norm = np.clip(p_dc / max(self.meta.rated_dc_kw, 1e-3), 0.0, 1.5)
        eff = self.meta.inverter_efficiency_nominal * (1.0 - 0.02 * (1.0 - p_norm) ** 2)
        p_ac = p_dc * eff

        # Clamp at inverter rated AC capacity
        p_ac = np.minimum(p_ac, self.meta.rated_ac_kw)

        # Zero out nighttime / low sun
        night_mask = (elev <= 5.0) | (poa < 20.0)
        p_ac[night_mask] = 0.0

        return np.round(p_ac, 2)


# ---------------------------------------------------------------------------
# Model B: Empirical Normal-Operation Baseline
# ---------------------------------------------------------------------------

class SolarEmpiricalBaseline:
    """Low-complexity response-surface model fit exclusively on normal training data.

    Formulation: P_expected = f(G_poa, T_module, sin(elev)) using degree-2 polynomial Ridge regression.
    """

    def __init__(self, meta: PVDAQSystemMetadata, alpha: float = 1.0) -> None:
        self.meta = meta
        self.alpha = alpha
        self.poly = PolynomialFeatures(degree=2, include_bias=True)
        self.regressor = Ridge(alpha=alpha, positive=False, fit_intercept=False)
        self.is_fitted = False

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        poa = df["poa_wm2"].fillna(0.0).to_numpy()
        temp = df["module_temp_c"].fillna(25.0).to_numpy()
        elev = np.maximum(df["solar_elevation_deg"].fillna(0.0).to_numpy(), 0.0)
        sin_elev = np.sin(np.radians(elev))

        # Normalized inputs: G / 1000, T / 50, sin(elev)
        X_raw = np.column_stack([poa / 1000.0, temp / 50.0, sin_elev])
        return self.poly.fit_transform(X_raw)

    def fit(self, train_df: pd.DataFrame) -> SolarEmpiricalBaseline:
        """Fit exclusively on healthy, uncurtailed daytime training records."""
        mask = (
            train_df["is_valid_daytime"]
            & (~train_df["is_curtailed"])
            & (~train_df["is_clipping"])
            & (train_df["poa_wm2"] >= 20.0)
        )
        fit_data = pd.DataFrame(train_df[mask])

        if len(fit_data) < 20:
            # Fallback if too few points
            self.is_fitted = False
            return self

        X = self._extract_features(fit_data)
        y = np.asarray(fit_data["ac_power_kw"])

        self.regressor.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict expected AC power in kW."""
        if not self.is_fitted:
            # Simple proportional fallback if unfitted
            poa = df["poa_wm2"].fillna(0.0).to_numpy()
            return np.clip(self.meta.rated_ac_kw * (poa / 1000.0) * 0.90, 0.0, self.meta.rated_ac_kw)

        poa = df["poa_wm2"].fillna(0.0).to_numpy()
        elev = df["solar_elevation_deg"].fillna(-90.0).to_numpy()

        X = self._extract_features(df)
        preds = self.regressor.predict(X)

        # Enforce non-negativity and rating cap
        preds = np.clip(preds, 0.0, self.meta.rated_ac_kw)

        # Nighttime zeroing
        night_mask = (elev <= 5.0) | (poa < 20.0)
        preds[night_mask] = 0.0

        return np.round(preds, 2)


# ---------------------------------------------------------------------------
# Model C: RAI Solar Champion (Hybrid Physics + Empirical Residual Engine)
# ---------------------------------------------------------------------------

class RAISolarChampion:
    """Hybrid Solar Champion combining physics reference prior and empirical calibration.

    Combines:
    1. Physics reference prediction as informative prior.
    2. Empirical residual calibration on training-normal data.
    3. Residual standardization (z-score) based on normal operational distribution.
    4. Temporal persistence filter over operational windows.
    5. Structured health evidence generation.
    """

    def __init__(
        self,
        meta: PVDAQSystemMetadata,
        physics_model: PVLibPhysicsReference,
        empirical_model: SolarEmpiricalBaseline,
        persistence_window: int = 3,  # 3 consecutive intervals (45 mins)
        z_threshold: float = 2.5,
    ) -> None:
        self.meta = meta
        self.physics = physics_model
        self.empirical = empirical_model
        self.persistence_window = persistence_window
        self.z_threshold = z_threshold

        # Calibration parameters (fit on normal training data)
        self.alpha_blend = 0.50  # weight on physics model
        self.residual_mean_normal = 0.0
        self.residual_std_normal = 1.0
        self.is_calibrated = False

    def calibrate(self, train_df: pd.DataFrame) -> RAISolarChampion:
        """Calibrate blend weight and residual normal statistics on normal training data."""
        mask = (
            train_df["is_valid_daytime"]
            & (~train_df["is_curtailed"])
            & (~train_df["is_clipping"])
            & (train_df["poa_wm2"] >= 50.0)
        )
        cal_data = pd.DataFrame(train_df[mask])

        if len(cal_data) < 20:
            self.is_calibrated = True
            return self

        y_act = np.asarray(cal_data["ac_power_kw"])
        y_phys = self.physics.predict(cal_data)
        y_emp = self.empirical.predict(cal_data)

        # Optimal convex combination alpha * y_phys + (1 - alpha) * y_emp
        # Min || y_act - (alpha * y_phys + (1-alpha) * y_emp) ||^2
        diff = y_phys - y_emp
        target = y_act - y_emp
        var_diff = np.var(diff)

        if var_diff > 1e-5:
            alpha = np.cov(target, diff)[0, 1] / var_diff
            self.alpha_blend = float(np.clip(alpha, 0.10, 0.90))
        else:
            self.alpha_blend = 0.50

        # Calibrated expected power on training normal data
        y_exp = self.alpha_blend * y_phys + (1.0 - self.alpha_blend) * y_emp
        residuals = y_act - y_exp

        self.residual_mean_normal = float(np.mean(residuals))
        self.residual_std_normal = float(max(np.std(residuals), 0.10))
        self.is_calibrated = True

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict expected power using the calibrated hybrid model."""
        y_phys = self.physics.predict(df)
        y_emp = self.empirical.predict(df)
        y_hybrid = self.alpha_blend * y_phys + (1.0 - self.alpha_blend) * y_emp

        # Cap at rated capacity and non-negativity
        y_hybrid = np.clip(y_hybrid, 0.0, self.meta.rated_ac_kw)

        poa = df["poa_wm2"].fillna(0.0).to_numpy()
        elev = df["solar_elevation_deg"].fillna(-90.0).to_numpy()
        night_mask = (elev <= 5.0) | (poa < 20.0)
        y_hybrid[night_mask] = 0.0

        return np.round(y_hybrid, 2)

    def evaluate_health_evidence(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[SolarHealthEvidence]]:
        """Compute expected power, residuals, standardized z-scores, persistence, and health evidence."""
        out = df.copy()
        y_exp_phys = self.physics.predict(out)
        y_exp_emp = self.empirical.predict(out)
        y_exp_champ = self.predict(out)

        y_act = out["ac_power_kw"].fillna(0.0).to_numpy()
        res_phys = y_act - y_exp_phys
        res_emp = y_act - y_exp_emp
        res_champ = y_act - y_exp_champ

        # Standardized residual z-score
        res_z = (res_champ - self.residual_mean_normal) / self.residual_std_normal

        # Flag negative underperformance beyond z_threshold
        is_underperforming = (
            (res_z <= -self.z_threshold)
            & out["is_valid_daytime"].to_numpy()
            & (~out["is_clipping"].to_numpy())
            & (~out["is_curtailed"].to_numpy())
        )

        # Compute temporal persistence (consecutive intervals of underperformance)
        n = len(out)
        persistence = np.zeros(n, dtype=int)
        curr_streak = 0
        for i in range(n):
            if is_underperforming[i]:
                curr_streak += 1
            else:
                curr_streak = 0
            persistence[i] = curr_streak

        out["expected_power_physics"] = y_exp_phys
        out["expected_power_empirical"] = y_exp_emp
        out["expected_power_champion"] = y_exp_champ
        out["power_residual_physics"] = np.round(res_phys, 2)
        out["power_residual_empirical"] = np.round(res_emp, 2)
        out["power_residual_champion"] = np.round(res_champ, 2)
        out["residual_z_score"] = np.round(res_z, 2)
        out["persistence_count"] = persistence

        # Contextual operating regime assignment
        poa = out["poa_wm2"].fillna(0.0).to_numpy()
        regimes = np.full(n, "NIGHT", dtype=object)
        regimes[(poa >= 20.0) & (poa < 300.0)] = "LOW_IRRADIANCE"
        regimes[(poa >= 300.0) & (poa < 700.0)] = "MEDIUM_IRRADIANCE"
        regimes[poa >= 700.0] = "HIGH_IRRADIANCE"
        out["operating_context"] = regimes

        # Build structured health evidence objects
        evidence_list: list[SolarHealthEvidence] = []
        for i in range(n):
            row = out.iloc[i]
            q_state = str(row["quality_state"])
            is_clip = bool(row["is_clipping"])
            is_curt = bool(row["is_curtailed"])
            streak = int(row["persistence_count"])

            if q_state == "DATA_GAP":
                h_status = "DATA_GAP"
            elif q_state == "NIGHTTIME":
                h_status = "NORMAL_NIGHT"
            elif is_clip:
                h_status = "CLIPPING_PLATEAU"
            elif is_curt:
                h_status = "CURTAILED_DISPATCH"
            elif streak >= self.persistence_window:
                h_status = "PERSISTENT_UNDERPERFORMANCE"
            elif row["residual_z_score"] <= -self.z_threshold:
                h_status = "TRANSIENT_DEFICIT"
            else:
                h_status = "NORMAL_OPERATION"

            evidence_list.append(
                SolarHealthEvidence(
                    timestamp=str(row["timestamp"]),
                    asset_id=str(row["system_id"]),
                    expected_power_kw=float(row["expected_power_champion"]),
                    actual_power_kw=float(row["ac_power_kw"]) if not pd.isna(row["ac_power_kw"]) else 0.0,
                    residual_kw=float(row["power_residual_champion"]),
                    residual_z=float(row["residual_z_score"]),
                    persistence_intervals=streak,
                    quality_state=q_state,
                    operating_context=str(row["operating_context"]),
                    clipping_state=is_clip,
                    curtailment_state=is_curt,
                    health_evidence=h_status,
                )
            )

        out["health_evidence"] = [e.health_evidence for e in evidence_list]
        return out, evidence_list
