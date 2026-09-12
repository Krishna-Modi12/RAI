"""Solar Expected-Performance Evaluation Metrics & Diagnostics.

Calculates:
1. Pointwise tracking accuracy: RMSE, MAE, R², nRMSE, mean residual, std dev.
2. Operating regime breakdown: Low/Med/High Irradiance, Thermal Regimes, Clipping, Curtailment.
3. Daily energy aggregation and daily energy percentage error.
4. Residual statistical diagnostics: Bias, Autocorrelation, Heteroscedasticity.
5. Within-system temporal vs cross-system holdout evaluation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass(frozen=True)
class ModelMetricRecord:
    """Standard tracking metrics for an expected-power model."""

    system_id: str
    model_name: str
    split: str
    sample_count: int
    r2: float
    rmse_kw: float
    mae_kw: float
    nrmse_pct: float  # RMSE / rated_ac_kw * 100
    mean_residual_kw: float
    residual_std_kw: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegimeMetricRecord:
    """Performance metrics segmented by physical operating regime."""

    system_id: str
    model_name: str
    regime_name: str
    sample_count: int
    r2: float
    rmse_kw: float
    mae_kw: float
    mean_residual_kw: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyEnergyMetricRecord:
    """Daily energy production accuracy metrics."""

    system_id: str
    model_name: str
    total_days: int
    actual_energy_kwh: float
    expected_energy_kwh: float
    mean_daily_actual_kwh: float
    mean_daily_expected_kwh: float
    mean_daily_abs_error_pct: float
    energy_r2: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResidualDiagnosticsRecord:
    """Statistical diagnostics of model residuals."""

    system_id: str
    model_name: str
    lag1_autocorrelation: float
    irradiance_heteroscedasticity_corr: float
    temperature_bias_slope: float
    skewness: float
    excess_kurtosis: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_pointwise_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    system_id: str,
    model_name: str,
    split: str,
    rated_ac_kw: float,
) -> ModelMetricRecord:
    """Compute standard regression metrics on valid daytime predictions."""
    if len(y_true) == 0:
        return ModelMetricRecord(
            system_id=system_id,
            model_name=model_name,
            split=split,
            sample_count=0,
            r2=0.0,
            rmse_kw=0.0,
            mae_kw=0.0,
            nrmse_pct=0.0,
            mean_residual_kw=0.0,
            residual_std_kw=0.0,
        )

    r2 = float(r2_score(y_true, y_pred)) if np.var(y_true) > 1e-6 else 1.0
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    nrmse = float((rmse / max(rated_ac_kw, 1e-3)) * 100.0)

    residuals = y_true - y_pred
    mean_res = float(np.mean(residuals))
    std_res = float(np.std(residuals))

    return ModelMetricRecord(
        system_id=system_id,
        model_name=model_name,
        split=split,
        sample_count=len(y_true),
        r2=round(r2, 4),
        rmse_kw=round(rmse, 3),
        mae_kw=round(mae, 3),
        nrmse_pct=round(nrmse, 2),
        mean_residual_kw=round(mean_res, 3),
        residual_std_kw=round(std_res, 3),
    )


def compute_regime_metrics(
    df: pd.DataFrame,
    system_id: str,
    model_col: str,
    model_name: str,
) -> list[RegimeMetricRecord]:
    """Compute metrics stratified across environmental and operational regimes."""
    records: list[RegimeMetricRecord] = []

    # Filter to daytime records
    day_df = df[df["is_valid_daytime"]].copy()

    regime_masks = {
        "ALL_VALID_DAYTIME": np.ones(len(day_df), dtype=bool),
        "LOW_IRRADIANCE (20-300 W/m²)": (day_df["poa_wm2"] >= 20.0) & (day_df["poa_wm2"] < 300.0),
        "MEDIUM_IRRADIANCE (300-700 W/m²)": (day_df["poa_wm2"] >= 300.0) & (day_df["poa_wm2"] < 700.0),
        "HIGH_IRRADIANCE (>= 700 W/m²)": day_df["poa_wm2"] >= 700.0,
        "LOW_TEMP (< 25°C)": day_df["module_temp_c"] < 25.0,
        "MEDIUM_TEMP (25-45°C)": (day_df["module_temp_c"] >= 25.0) & (day_df["module_temp_c"] < 45.0),
        "HIGH_TEMP (>= 45°C)": day_df["module_temp_c"] >= 45.0,
        "INVERTER_CLIPPING": day_df["is_clipping"],
        "GRID_CURTAILMENT": day_df["is_curtailed"],
    }

    for name, mask in regime_masks.items():
        subset = day_df[mask]
        n_sub = len(subset)
        if n_sub < 5:
            continue

        y_t = subset["ac_power_kw"].to_numpy()
        y_p = subset[model_col].to_numpy()

        r2 = float(r2_score(y_t, y_p)) if np.var(y_t) > 1e-6 else 1.0
        rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
        mae = float(mean_absolute_error(y_t, y_p))
        mean_res = float(np.mean(y_t - y_p))

        records.append(
            RegimeMetricRecord(
                system_id=system_id,
                model_name=model_name,
                regime_name=name,
                sample_count=n_sub,
                r2=round(r2, 4),
                rmse_kw=round(rmse, 3),
                mae_kw=round(mae, 3),
                mean_residual_kw=round(mean_res, 3),
            )
        )

    return records


def compute_daily_energy_metrics(
    df: pd.DataFrame,
    system_id: str,
    model_col: str,
    model_name: str,
    dt_hours: float = 0.25,  # 15 minutes = 0.25 hours
) -> DailyEnergyMetricRecord:
    """Aggregate 15-minute power into daily energy and compute energy-level error."""
    clean = df.copy()
    clean["date"] = pd.to_datetime(clean["timestamp"]).dt.date

    # Sum kWh = sum(kW * dt_hours)
    daily = clean.groupby("date").agg(
        e_act_kwh=("ac_power_kw", lambda x: float(np.sum(x.fillna(0.0) * dt_hours))),
        e_exp_kwh=(model_col, lambda x: float(np.sum(x.fillna(0.0) * dt_hours))),
    ).reset_index()

    total_days = len(daily)
    tot_act = float(daily["e_act_kwh"].sum())
    tot_exp = float(daily["e_exp_kwh"].sum())

    mean_act = float(daily["e_act_kwh"].mean())
    mean_exp = float(daily["e_exp_kwh"].mean())

    # Normalized daily percentage error: mean of |E_act - E_exp| / E_exp
    valid_daily = daily[daily["e_exp_kwh"] > 1.0]
    if len(valid_daily) > 0:
        pct_err = float(
            np.mean(
                np.abs(valid_daily["e_act_kwh"] - valid_daily["e_exp_kwh"])
                / valid_daily["e_exp_kwh"]
            )
            * 100.0
        )
    else:
        pct_err = 0.0

    r2 = (
        float(r2_score(daily["e_act_kwh"], daily["e_exp_kwh"]))
        if np.var(daily["e_act_kwh"]) > 1e-6
        else 1.0
    )

    return DailyEnergyMetricRecord(
        system_id=system_id,
        model_name=model_name,
        total_days=total_days,
        actual_energy_kwh=round(tot_act, 1),
        expected_energy_kwh=round(tot_exp, 1),
        mean_daily_actual_kwh=round(mean_act, 2),
        mean_daily_expected_kwh=round(mean_exp, 2),
        mean_daily_abs_error_pct=round(pct_err, 2),
        energy_r2=round(r2, 4),
    )


def compute_residual_diagnostics(
    df: pd.DataFrame,
    system_id: str,
    residual_col: str,
    model_name: str,
) -> ResidualDiagnosticsRecord:
    """Analyze autocorrelation, heteroscedasticity, and distributional bias in residuals."""
    day_df = df[df["is_valid_daytime"]].copy()
    res = day_df[residual_col].to_numpy()

    if len(res) < 10:
        return ResidualDiagnosticsRecord(
            system_id=system_id,
            model_name=model_name,
            lag1_autocorrelation=0.0,
            irradiance_heteroscedasticity_corr=0.0,
            temperature_bias_slope=0.0,
            skewness=0.0,
            excess_kurtosis=0.0,
        )

    # 1. Lag-1 Autocorrelation
    lag1_corr = float(np.corrcoef(res[:-1], res[1:])[0, 1]) if np.var(res) > 1e-6 else 0.0

    # 2. Heteroscedasticity (correlation of |residual| with POA irradiance)
    poa = day_df["poa_wm2"].to_numpy()
    abs_res = np.abs(res)
    het_corr = float(np.corrcoef(abs_res, poa)[0, 1]) if np.var(abs_res) > 1e-6 else 0.0

    # 3. Temperature bias slope (linear slope of residual vs module temperature)
    temp = day_df["module_temp_c"].to_numpy()
    if np.var(temp) > 1e-6:
        slope = float(np.cov(res, temp)[0, 1] / np.var(temp))
    else:
        slope = 0.0

    # 4. Skewness and Kurtosis
    m2 = np.mean((res - np.mean(res)) ** 2)
    m3 = np.mean((res - np.mean(res)) ** 3)
    m4 = np.mean((res - np.mean(res)) ** 4)

    skew = float(m3 / (m2 ** 1.5)) if m2 > 1e-6 else 0.0
    kurt = float((m4 / (m2 ** 2)) - 3.0) if m2 > 1e-6 else 0.0

    return ResidualDiagnosticsRecord(
        system_id=system_id,
        model_name=model_name,
        lag1_autocorrelation=round(lag1_corr, 3),
        irradiance_heteroscedasticity_corr=round(het_corr, 3),
        temperature_bias_slope=round(slope, 4),
        skewness=round(skew, 3),
        excess_kurtosis=round(kurt, 3),
    )
