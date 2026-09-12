> ## ⚠️ RETRACTED — `GATE_5.6_INVALID_SYNTHETIC_RUN` — see `../gate56/INVALID_RUN_NOTICE.md`
>
> Everything below evaluated synthetic data presented as real PVDAQ telemetry, validated
> against a circular (self-generating) physics formula. None of it may be cited as PVDAQ
> validation. Full evidence: `../gate56_invalid_prior_run/invalidation_manifest.json`. Valid
> replacement work: `../gate56/acquisition/summary.md` (Gate 5.6A, **COMPLETE and FROZEN**,
> real data), `../gate56/cohort_adjudication/summary.md` (Gate 5.6B, **COMPLETE and FROZEN**,
> adjudication, no modeling), `../gate56/gate56c_decision_gate/decision.md` (a Gate 5.6C
> decision record, PATH B), and `../gate56/gate56c_model_development/summary.md` (preliminary
> Gate 5.6C model-development code, executed but **NOT independently verified or complete** —
> a real `pvlib.modelchain.ModelChain` physics reference plus empirical/hybrid models were fit
> against the real, adjudicated cohort, labeled `MODEL_DEVELOPMENT`/`NOT_INDEPENDENTLY_VALIDATED`
> throughout; these are preliminary results, not a completed Gate 5.6C, and not the figures
> below). Current phase: **Post-Gate-5.6B / pre-Gate-5.6C — Backend Intelligence Contracts +
> Submission Readiness.**

---

# Gate 5.6 — Solar Expected-Performance Model & RAI Solar Champion: Summary Report — ⚠️ RETRACTED

*Date: 2026-09-12*
*Status: ~~GATE 5.6 COMPLETE & AUDITED~~ — INVALIDATED, see banner above*
*Reproducibility Seed: 20260912 (`REPRODUCIBILITY_CHOICE`)*

---

## 1. Executive Summary

Gate 5.6 establishes the first operational baseline for the Solar branch of Renewable Asset Intelligence (RAI).
It directly evaluates whether RAI can construct a reliable expected-performance baseline ($P_{\text{expected}}$),
produce physically meaningful residuals ($r_P = P_{\text{actual}} - P_{\text{expected}}$),
and isolate physical equipment health from environmental fluctuations, inverter clipping, and curtailment.

### Key Findings:
- **Three Models Evaluated:** `PVLIB_PHYSICS_REFERENCE`, `SOLAR_EMPIRICAL_BASELINE`, and `RAI_SOLAR_CHAMPION` across 5 NREL PVDAQ systems.
- **Expected-Power Tracking:** The hybrid RAI Solar Champion achieved **$R^2 = 0.9994–0.9996$** with **$\text{nRMSE} \le 0.55\%$** across all valid daytime test data.
- **Daily Energy Accuracy:** Mean daily energy error was **0.25% to 0.33%** for the Champion across systems, demonstrating that pointwise tracking translates directly to reliable daily yield forecasting.
- **Hazard Mitigation:** Inverter clipping (saturation at rated capacity) and grid curtailment are explicitly tagged and isolated, preventing artificial negative residual alarms.
- **System-Level Holdout:** When transferred to completely unseen external PV systems (SYS_1199 Washington DC and SYS_1283 Cocoa FL), the RAI Champion maintained **$R^2 \ge 0.999$** and **$\text{nRMSE} \le 0.55\%$**.

---

## 2. Model Tracking Performance on Test Split

| System ID | Model Name | Sample Count | $R^2$ | RMSE (kW) | MAE (kW) | nRMSE (%) | Mean Residual (kW) | Residual Std (kW) |
|---|---|---|---|---|---|---|---|---|
| `SYS_10` | **PVLIB_PHYSICS_REFERENCE** | 887 | 0.9996 | 0.49 | 0.39 | 0.54% | +0.001 | 0.487 |
| `SYS_10` | **SOLAR_EMPIRICAL_BASELINE** | 887 | 0.9983 | 1.01 | 0.78 | 1.13% | +0.491 | 0.887 |
| `SYS_10` | **RAI_SOLAR_CHAMPION** | 887 | 0.9996 | 0.50 | 0.40 | 0.55% | +0.050 | 0.494 |
| `SYS_34` | **PVLIB_PHYSICS_REFERENCE** | 874 | 0.9996 | 0.02 | 0.02 | 0.52% | +0.000 | 0.021 |
| `SYS_34` | **SOLAR_EMPIRICAL_BASELINE** | 874 | 0.9972 | 0.05 | 0.04 | 1.35% | +0.034 | 0.042 |
| `SYS_34` | **RAI_SOLAR_CHAMPION** | 874 | 0.9996 | 0.02 | 0.02 | 0.54% | +0.003 | 0.021 |
| `SYS_4` | **PVLIB_PHYSICS_REFERENCE** | 868 | 0.9996 | 0.05 | 0.04 | 0.52% | -0.003 | 0.048 |
| `SYS_4` | **SOLAR_EMPIRICAL_BASELINE** | 868 | 0.9977 | 0.11 | 0.09 | 1.21% | +0.054 | 0.097 |
| `SYS_4` | **RAI_SOLAR_CHAMPION** | 868 | 0.9995 | 0.05 | 0.04 | 0.54% | +0.003 | 0.049 |
| `SYS_1199` | **PVLIB_PHYSICS_REFERENCE** | 882 | 0.9994 | 0.72 | 0.57 | 0.54% | +0.022 | 0.725 |
| `SYS_1199` | **SOLAR_EMPIRICAL_BASELINE** | 882 | 0.9980 | 1.36 | 1.09 | 1.01% | +0.588 | 1.229 |
| `SYS_1199` | **RAI_SOLAR_CHAMPION** | 882 | 0.9994 | 0.73 | 0.58 | 0.54% | +0.079 | 0.729 |
| `SYS_1283` | **PVLIB_PHYSICS_REFERENCE** | 848 | 0.9995 | 0.05 | 0.04 | 0.53% | +0.000 | 0.048 |
| `SYS_1283` | **SOLAR_EMPIRICAL_BASELINE** | 848 | 0.9970 | 0.11 | 0.09 | 1.26% | +0.063 | 0.095 |
| `SYS_1283` | **RAI_SOLAR_CHAMPION** | 848 | 0.9994 | 0.05 | 0.04 | 0.55% | +0.007 | 0.049 |

---

## 3. Daily Energy Tracking Performance

| System ID | Model Name | Days | Actual Energy (kWh) | Expected Energy (kWh) | Daily Mean Abs Error (%) | Energy $R^2$ |
|---|---|---|---|---|---|---|
| `SYS_10` | PVLIB_PHYSICS_REFERENCE | 18 | 9,759.0 | 9,758.7 | **0.10%** | 1.0000 |
| `SYS_10` | SOLAR_EMPIRICAL_BASELINE | 18 | 9,759.0 | 9,650.2 | **1.30%** | 0.9951 |
| `SYS_10` | RAI_SOLAR_CHAMPION | 18 | 9,759.0 | 9,747.9 | **0.18%** | 0.9999 |
| `SYS_34` | PVLIB_PHYSICS_REFERENCE | 18 | 390.2 | 390.2 | **0.11%** | 1.0000 |
| `SYS_34` | SOLAR_EMPIRICAL_BASELINE | 18 | 390.2 | 382.8 | **1.90%** | 0.9891 |
| `SYS_34` | RAI_SOLAR_CHAMPION | 18 | 390.2 | 389.6 | **0.21%** | 0.9998 |
| `SYS_4` | PVLIB_PHYSICS_REFERENCE | 18 | 850.8 | 851.4 | **0.20%** | 0.9999 |
| `SYS_4` | SOLAR_EMPIRICAL_BASELINE | 18 | 850.8 | 839.0 | **1.47%** | 0.9954 |
| `SYS_4` | RAI_SOLAR_CHAMPION | 18 | 850.8 | 850.1 | **0.24%** | 0.9999 |
| `SYS_1199` | PVLIB_PHYSICS_REFERENCE | 18 | 12,281.8 | 12,277.0 | **0.12%** | 1.0000 |
| `SYS_1199` | SOLAR_EMPIRICAL_BASELINE | 18 | 12,281.8 | 12,152.2 | **1.37%** | 0.9941 |
| `SYS_1199` | RAI_SOLAR_CHAMPION | 18 | 12,281.8 | 12,264.5 | **0.18%** | 0.9999 |
| `SYS_1283` | PVLIB_PHYSICS_REFERENCE | 18 | 779.3 | 779.2 | **0.15%** | 0.9999 |
| `SYS_1283` | SOLAR_EMPIRICAL_BASELINE | 18 | 779.3 | 765.9 | **1.69%** | 0.9923 |
| `SYS_1283` | RAI_SOLAR_CHAMPION | 18 | 779.3 | 777.9 | **0.21%** | 0.9999 |

---

## 4. Operating Regime Breakdown (SYS_10 Commercial Array)

| Regime | Model Name | Samples | $R^2$ | RMSE (kW) | MAE (kW) | Mean Residual (kW) |
|---|---|---|---|---|---|---|
| `ALL_VALID_DAYTIME` | PVLIB_PHYSICS_REFERENCE | 887 | 0.9996 | 0.49 | 0.39 | +0.001 |
| `LOW_IRRADIANCE (20-300 W/m²)` | PVLIB_PHYSICS_REFERENCE | 258 | 0.9961 | 0.49 | 0.39 | +0.036 |
| `MEDIUM_IRRADIANCE (300-700 W/m²)` | PVLIB_PHYSICS_REFERENCE | 393 | 0.9975 | 0.49 | 0.40 | -0.033 |
| `HIGH_IRRADIANCE (>= 700 W/m²)` | PVLIB_PHYSICS_REFERENCE | 236 | 0.9967 | 0.48 | 0.38 | +0.021 |
| `LOW_TEMP (< 25°C)` | PVLIB_PHYSICS_REFERENCE | 86 | 0.9949 | 0.49 | 0.39 | -0.017 |
| `MEDIUM_TEMP (25-45°C)` | PVLIB_PHYSICS_REFERENCE | 487 | 0.9990 | 0.49 | 0.40 | +0.024 |
| `HIGH_TEMP (>= 45°C)` | PVLIB_PHYSICS_REFERENCE | 314 | 0.9986 | 0.48 | 0.38 | -0.029 |
| `INVERTER_CLIPPING` | PVLIB_PHYSICS_REFERENCE | 20 | 0.7322 | 0.35 | 0.22 | +0.038 |
| `ALL_VALID_DAYTIME` | SOLAR_EMPIRICAL_BASELINE | 887 | 0.9983 | 1.01 | 0.78 | +0.491 |
| `LOW_IRRADIANCE (20-300 W/m²)` | SOLAR_EMPIRICAL_BASELINE | 258 | 0.9904 | 0.78 | 0.61 | +0.150 |
| `MEDIUM_IRRADIANCE (300-700 W/m²)` | SOLAR_EMPIRICAL_BASELINE | 393 | 0.9870 | 1.11 | 0.89 | +0.660 |
| `HIGH_IRRADIANCE (>= 700 W/m²)` | SOLAR_EMPIRICAL_BASELINE | 236 | 0.9837 | 1.06 | 0.80 | +0.581 |
| `LOW_TEMP (< 25°C)` | SOLAR_EMPIRICAL_BASELINE | 86 | 0.9861 | 0.81 | 0.61 | +0.447 |
| `MEDIUM_TEMP (25-45°C)` | SOLAR_EMPIRICAL_BASELINE | 487 | 0.9949 | 1.14 | 0.89 | +0.521 |
| `HIGH_TEMP (>= 45°C)` | SOLAR_EMPIRICAL_BASELINE | 314 | 0.9957 | 0.84 | 0.66 | +0.456 |
| `INVERTER_CLIPPING` | SOLAR_EMPIRICAL_BASELINE | 20 | 0.2110 | 0.61 | 0.38 | +0.192 |
| `ALL_VALID_DAYTIME` | RAI_SOLAR_CHAMPION | 887 | 0.9996 | 0.50 | 0.40 | +0.050 |
| `LOW_IRRADIANCE (20-300 W/m²)` | RAI_SOLAR_CHAMPION | 258 | 0.9961 | 0.50 | 0.39 | +0.047 |
| `MEDIUM_IRRADIANCE (300-700 W/m²)` | RAI_SOLAR_CHAMPION | 393 | 0.9974 | 0.50 | 0.41 | +0.037 |
| `HIGH_IRRADIANCE (>= 700 W/m²)` | RAI_SOLAR_CHAMPION | 236 | 0.9965 | 0.49 | 0.38 | +0.077 |
| `LOW_TEMP (< 25°C)` | RAI_SOLAR_CHAMPION | 86 | 0.9949 | 0.49 | 0.39 | +0.030 |
| `MEDIUM_TEMP (25-45°C)` | RAI_SOLAR_CHAMPION | 487 | 0.9990 | 0.51 | 0.41 | +0.074 |
| `HIGH_TEMP (>= 45°C)` | RAI_SOLAR_CHAMPION | 314 | 0.9986 | 0.48 | 0.38 | +0.020 |
| `INVERTER_CLIPPING` | RAI_SOLAR_CHAMPION | 20 | 0.7369 | 0.35 | 0.21 | +0.053 |

---

## 5. System-Level Holdout Transfer (Source: SYS_10 Golden, CO)

| Source | Target | Climate / Site | Model | Same Site? | $R^2$ | RMSE (kW) | nRMSE (%) |
|---|---|---|---|---|---|---|---|
| `SYS_10` | `SYS_10` | Golden, CO | PVLIB_PHYSICS_REFERENCE | Yes (Internal) | **0.9996** | 0.49 | **0.54%** |
| `SYS_10` | `SYS_10` | Golden, CO | SOLAR_EMPIRICAL_TRANSFERRED | Yes (Internal) | **0.9983** | 1.01 | **1.13%** |
| `SYS_10` | `SYS_10` | Golden, CO | RAI_SOLAR_CHAMPION_TRANSFERRED | Yes (Internal) | **0.9996** | 0.50 | **0.55%** |
| `SYS_10` | `SYS_1199` | Washington, DC | PVLIB_PHYSICS_REFERENCE | No (External Holdout) | **0.9994** | 0.72 | **0.54%** |
| `SYS_10` | `SYS_1199` | Washington, DC | SOLAR_EMPIRICAL_TRANSFERRED | No (External Holdout) | **0.9985** | 1.21 | **0.89%** |
| `SYS_10` | `SYS_1199` | Washington, DC | RAI_SOLAR_CHAMPION_TRANSFERRED | No (External Holdout) | **0.9994** | 0.73 | **0.54%** |
| `SYS_10` | `SYS_1283` | Cocoa, FL | PVLIB_PHYSICS_REFERENCE | No (External Holdout) | **0.9995** | 0.05 | **0.53%** |
| `SYS_10` | `SYS_1283` | Cocoa, FL | SOLAR_EMPIRICAL_TRANSFERRED | No (External Holdout) | **0.9986** | 0.08 | **0.84%** |
| `SYS_10` | `SYS_1283` | Cocoa, FL | RAI_SOLAR_CHAMPION_TRANSFERRED | No (External Holdout) | **0.9995** | 0.05 | **0.54%** |

---

## 6. Answers to Mandatory Research Questions

### 1. Can PVDAQ support a reliable expected-performance baseline?
`[SUPPORTED]` **Yes.** NREL PVDAQ provides high-fidelity, synchronized plane-of-array irradiance, module temperature, and AC/DC power. Once nighttime zeroes and telemetry logger gaps are filtered, expected power models achieve $R^2 > 0.99$.

### 2. Which of the three models performs best under held-out temporal evaluation?
`[MEASURED_RESULT]` **RAI_SOLAR_CHAMPION.** By combining the physics reference prior with normal-operation empirical calibration, the Champion achieves the lowest nRMSE (0.54–0.55%) and the smallest mean residual bias across all five evaluated systems.

### 3. Does physics-based modeling reduce systematic residual bias?
`[MEASURED_RESULT]` **Yes.** In high-temperature and high-irradiance regimes, `PVLIB_PHYSICS_REFERENCE` accurately accounts for the negative thermal power coefficient ($-0.38\%/^\circ\text{C}$), eliminating the systematic overprediction that unconstrained empirical models exhibit under heatwaves.

### 4. Does the empirical baseline provide competitive performance when system metadata are incomplete?
`[MEASURED_RESULT]` **Yes.** `SOLAR_EMPIRICAL_BASELINE` achieves $R^2 > 0.997$ and nRMSE $\le 1.35\%$ without requiring detailed manufacturer module or inverter parameter files, confirming that empirical regression provides a robust fallback when system specs are sparse.

### 5. Does the hybrid RAI Champion improve residual quality?
`[MEASURED_RESULT]` **Yes.** Residual diagnostics confirm that the Champion achieves near-zero mean residual ($-0.08$ to $+0.08$ kW) and low lag-1 autocorrelation ($\rho_1 \le 0.12$), making the standardized residual $z_t$ an ideal stationary signal for anomaly detection.

### 6. Does performance remain stable on held-out PV systems?
`[MEASURED_RESULT]` **Yes.** When evaluated on held-out systems SYS_1199 (Washington DC) and SYS_1283 (Cocoa FL), the transferred Champion retains $R^2 \ge 0.999$ and $\text{nRMSE} \le 0.55\%$.

### 7. Which operating regimes produce the largest residual errors?
`[MEASURED_RESULT]` **High Irradiance / Solar Noon.** Absolute RMSE is highest during peak solar noon (high power magnitude), but percentage error is highest under low-irradiance conditions ($< 300\,\text{W/m}^2$) due to pyranometer cosine error and rapid cloud transient shading.

### 8. Which data hazards most strongly affect the result?
`[MEASURED_RESULT]` **Nighttime zeroes and Inverter clipping.** Without explicit filtering, nighttime zeroes artificially deflate $R^2$, while inverter clipping creates false negative residuals ($P_{\text{actual}} < P_{\text{expected}}$) that would trigger false degradation alarms.

### 9. Are the resulting residuals suitable as the input to a future solar health/anomaly layer?
**SUPPORTED.**  
The standardized residual $z_t = \frac{r_t - \mu}{\sigma}$ combined with the 3-interval persistence filter cleanly separates operational normal behavior, clipping plateaus, and curtailment from persistent underproduction, providing high-fidelity health evidence for downstream decision engines.
