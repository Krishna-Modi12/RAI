# RAI Operational Evaluation Summary & Generalization Benchmark (Phase 3)

**Run Timestamp:** 2026-09-12T10:29:07.085240+00:00  
**Monitored Assets:** 42 (18 wind turbines, 24 solar inverters)  
**Total Monitored Hours:** 45,360.0 h (217,728 timestamps)  
**Independent Failure Events:** 6 discrete degradation episodes  
**Execution Duration:** 114.13 s  

---

## 1. Two-Track Benchmark Summary

* **Track A — RAI Operational Score (CARE-inspired Fleet Evaluation):**
  * Champion Model: `challenger_hybrid_ensemble`
  * Operational CARE Score: **`0.797`**
  * PR-AUC: **`0.822`**
  * Actionable False Alarm Rate: **`0.19 / asset-yr`**
  * Median Detection Lead Time: **`5.0 days`**

* **Track B — External SCADA Reality Benchmark:**
  * Status: **`EXECUTED`** (1 external turbine dataset files, 240.0 SCADA hours)
  * Zero-Shot Power Curve Tracking: **$R^2 =$ `0.9943`**
  * External Normal FA Rate: **`0.00 / yr`**
  * Zero-Shot Physics Transfer: **`VERIFIED`**

---

## 2. Event-Count & Provenance Table

| Asset Class | Fleet Assets | Monitored Hours | Failure Events | Normal Assets | Evaluated Failure Modes |
|---|---|---|---|---|---|
| **Wind Turbines (WT)** | 18 | 19,440.0 h | **4 events** | 14 assets | Gearbox bearing spalling, Generator insulation, Main bearing wear |
| **Solar Inverters (INV)** | 24 | 25,920.0 h | **2 events** | 22 assets | Inverter bridge IGBT thermal fatigue, DC bus capacitor aging |
| **Fleet Total** | **42** | **45,360.0 h** | **6 events** | **36 assets** | **4 major equipment failure families** |

---

## 3. Champion-versus-Challenger Benchmark Table (Track A)

| Model Candidate | Tier | RAI Operational Score (CARE-inspired) | Coverage | Accuracy | Reliability | Earliness | False Alarms/yr | Lead Time (days) | PR-AUC | MCC |
|---|---|---|---|---|---|---|---|---|---|---|
| **baseline_1_physics_rules** | Rule-based | `0.070` | 0.00 | 0.24 | 0.04 | 0.00 | 38.1 | 0.0 d | `0.262` | `0.000` |
| **baseline_2_expected_regression** | Regression | `0.235` | 0.17 | 0.31 | 0.11 | 0.36 | 26.9 | 5.0 d | `0.202` | `0.000` |
| **baseline_3_residual_z** | Statistical | `0.422` | 1.00 | 0.00 | 0.00 | 0.68 | 2473.1 | 9.8 d | `0.126` | `-0.380` |
| **baseline_4_isolation_forest** | Unsupervised ML | `0.691` | 0.33 | 0.98 | 0.98 | 0.46 | 0.2 | 6.5 d | `0.594` | `0.563` |
| **challenger_hybrid_ensemble** | Hybrid Fusion | `0.797` | 0.83 | 0.98 | 0.98 | 0.39 | 0.2 | 5.0 d | `0.822` | `0.690` |

---

## 4. Probabilistic Risk Calibration
* **Brier Score:** `0.0423` *(Proper scoring rule; low score reflects both discrimination and base rate)*
* **Expected Calibration Error (ECE):** `0.1491` *(Average deviation of ~14.9% across 5 probability bins)*
* **Calibration Bins Export:** Saved to `artifacts/evaluation/calibration/bins.csv`.

---

## 5. Empirically Counted Alert Fatigue Reduction Funnel

| Filtering Stage | Annual Fleet Alarms | Elimination Rate | Operational Mechanism |
|---|---|---|---|
| **1. Raw Residual & Physics Exceedances** | `3,456.1 / yr` | `0.0%` | Active filtering gate |
| **2. Temporal Persistence Gate (6h/12h)** | `10.0 / yr` | `99.7%` | Active filtering gate |
| **3. Environmental Context Gate (CAMS Dust/Temp)** | `8.9 / yr` | `11.2%` | Active filtering gate |
| **4. Peer Consensus & Common-Cause Gate** | `5.0 / yr` | `43.5%` | Active filtering gate |
| **5. Evidence & Sensor Health Gate** | `3.9 / yr` | `23.1%` | Active filtering gate |
| **Actionable Work Orders** | **`0.09 / asset-yr`** | **`99.89% overall`** | **High-confidence maintenance dispatch** |

*Note: The funnel is measured by walking all 42 fleet timelines across 45,360 observation hours, counting exact gate removals.*

---

## 6. Decision Regret & Economic Quality

* **Engine Internal Consistency Regret:** Mean = `₹0.00`, Optimal Selection = `100.0%`
* **Stochastic Counterfactual Regret:** Mean = `₹0.00`, Optimal Selection = `100.0%`
* **Evaluation Basis:** Nature's realized failure arrival times simulated via Weibull hazard progression kinetics, verifying that deferral vs. immediate intervention minimizes operational cost.

---

## 7. Generalization & Leakage Audit

* **Level 1 — Temporal Holdout:** 4,212 train / 972 val / 1,152 test rows, 12h purge gap. Leakage-free.
* **Level 2 — Stratified Asset Holdout:** 11 assets held out completely (2 faulted, 9 healthy). **Out-of-sample PR-AUC:** `0.833` if asset_holdout_metrics else 'N/A'.
* **Level 3 — Per-fleet Breakdown:** Kutch Wind PR-AUC `1.000` vs Charanka Solar PR-AUC `0.833`.
* **Level 4 — Out-of-Distribution (OOD) Challenge:**
  * Stress conditions: 1.8x sensor noise, +2.5°C thermal drift, +4.0°C ambient shock.
  * Baseline PR-AUC: `0.822` -> Stressed OOD PR-AUC: `0.822`
  * **PR-AUC Retention:** `100.0%` (Pass threshold: $\ge 70\%$). Status: **`PASS`**.
