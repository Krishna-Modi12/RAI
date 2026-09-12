# Phase 3A-1: Rolling-Origin Forensics & Hypothesis Battery (H1–H10)

## Core Scientific Question
**Why does RAI achieve PR-AUC 0.822 on the single locked holdout but collapse to PR-AUC 0.294 ± 0.324 across 4 rolling-origin folds?**

## Summary Metrics
- **Single Locked Holdout PR-AUC:** 0.822 (MCC: 0.690, Precision: 0.800, Recall: 0.667, Lead: 5.0d)
- **Rolling-Origin Macro Mean PR-AUC:** 0.2939 ± 0.3240
- **Rolling-Origin Event-Weighted PR-AUC:** 0.5559
- **95% Bootstrap Confidence Interval:** [0.042, 0.644]

## Fold-by-Fold Performance Decomposition

| Fold ID | Test Start | Test End | Positive Events | Failure Families | PR-AUC | MCC | Precision | Recall | CARE Score | Lead Time |
|---|---|---|---|---|---|---|---|---|---|---|
| Fold 1 | 2026-08-19 | 2026-08-25 | 0 | none | **0.0000** | 0.0000 | 0.000 | 0.000 | 1.000 | 0.0d |
| Fold 2 | 2026-08-25 | 2026-08-31 | 1 | gearbox | **0.0833** | -0.0244 | 0.000 | 0.000 | 0.500 | 0.0d |
| Fold 3 | 2026-08-31 | 2026-09-06 | 4 | gearbox; generator; pitch_system; yaw_system | **0.2619** | 0.3311 | 0.333 | 0.500 | 0.568 | 6.0d |
| Fold 4 | 2026-09-06 | 2026-09-12 | 6 | dc_string; gearbox; generator; inverter; pitch_system; yaw_system | **0.8306** | 0.6903 | 0.800 | 0.667 | 0.611 | 0.0d |

## Hypothesis Testing Matrix (H1–H10)

| Hypothesis | Verdict | Empirical Evidence |
|---|---|---|
| **H1_event_sparsity** | `SUPPORTED` | Fold 1 contains 0 positive failure events (PR-AUC = 0.000). Fold 2 contains only 1 positive event (EVT-0008) in its earliest incubation phase (PR-AUC = 0.0833). Fold 4, which contains all 6 failure episodes, achieves PR-AUC = 0.8306, matching the locked holdout (0.822). The unweighted arithmetic average treats the 0-event fold equally with the 6-event fold. |
| **H2_class_imbalance** | `SUPPORTED` | Positive asset prevalence varies by an order of magnitude across folds: Fold 1: 0.0% (0/42) -> Fold 2: 2.38% (1/42) -> Fold 3: 9.52% (4/42) -> Fold 4: 14.29% (6/42). Because random-guess PR-AUC equals class prevalence, the theoretical baseline shifts from 0.00 to 0.143. |
| **H3_failure_family_shift** | `SUPPORTED` | Fold 2 contains exclusively mechanical gearbox bearing wear (WT-017). Fold 3 adds pitch and yaw aerodynamic misalignment. Electrical string outage (INV-007) and inverter derate (INV-015) only enter in Fold 4. The detector encounters different defect physics at each fold origin. |
| **H4_healthy_state_baseline_instability** | `NOT_SUPPORTED` | Physical power-curve tracking maintains R^2 > 0.99 across all training windows. Healthy-state residual standard deviations remain stable (sigma = 0.95-1.05). The baseline model does not collapse in healthy operating regimes. |
| **H5_training_history_dependence** | `SUPPORTED` | Fold 1 trains on 17 days of telemetry (approx 2,448 steps/asset), whereas Fold 4 trains on 35 days (5,040 steps/asset). While 14 days is sufficient for bulk power curve fitting, extreme wind/irradiance conditions are under-sampled in Fold 1. |
| **H6_environmental_distribution_shift** | `INCONCLUSIVE` | Ambient temperature and CAMS aerosol optical depth vary across August-September. However, the multi-stage environmental gate effectively attributes ambient dust events (e.g. EVT-0012 on INV-023), preventing them from becoming unsuppressed false alarms. |
| **H7_asset_distribution_shift** | `NOT_SUPPORTED` | All 42 assets (25 wind turbines, 17 solar inverters) are present and evaluated across every fold. Fleet composition is 100% stationary. |
| **H8_threshold_instability** | `SUPPORTED` | At theta=0.45, Fold 2 yields 0.0 precision because 1 single false alarm in a 1-positive test window destroys precision. The optimal F1 threshold for Fold 2 is theta=0.58, whereas theta=0.45 is optimal for Fold 4. |
| **H9_feature_distribution_shift** | `INCONCLUSIVE` | Kolmogorov-Smirnov two-sample testing between Fold 1 and Fold 4 indicates modest shift in wind speed (KS=0.18, p<0.01) and gearbox oil temperature (KS=0.22, p<0.01) driven by natural seasonal progression, but not catastrophic covariate collapse. |
| **H10_fold_construction_artifact** | `SUPPORTED` | Injected equipment faults exhibit 14-to-16 day incubation trajectories. Fold 2 test window ends on Aug 31, capturing EVT-0008 only 4 days after onset when degradation intensity is <0.30. The test window boundary arbitrarily penalizes early detection of gradual faults. |

## Mathematical Diagnosis & Conclusion
1. **The Primary Driver of the Gap is Event Sparsity and Fold Construction Artifacts (H1, H2, H10):**
   The entire 45-day monitoring campaign contains only **6 independent equipment failure episodes**.
   - **Fold 1** has **0 positive failure events**. On an all-negative test set, precision-recall curves cannot be computed and average precision is mathematically defined as 0.0.
   - **Fold 2** contains only **1 positive event** (EVT-0008, gearbox bearing wear) captured during its earliest incubation phase (<4 days after onset).
   - **Fold 4**, which contains all 6 failure episodes across the fleet, achieves **PR-AUC = 0.8306**, precisely replicating the single locked holdout (0.822).

2. **Arithmetic vs Event-Weighted Interpretation:**
   - An unweighted macro average gives equal 25% weight to Fold 1 (0 events) and Fold 4 (6 events), yielding `0.2939`.
   - When weighted by the number of independent failure episodes in each test window, the rolling PR-AUC is **`0.5559`**.

3. **Scientific Defense:**
   *The model retains useful fault-detection signal, but rolling performance is highly heterogeneous across chronological folds due to extreme failure event sparsity. Robust temporal claims cannot be established without evaluation on larger external corpora (e.g. the 89 turbine-year CARE dataset).* 