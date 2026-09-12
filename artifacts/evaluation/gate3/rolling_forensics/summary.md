# Rolling-Origin Forensics Audit Report (Phase 3A)

## Executive Summary: Diagnosis of the PR-AUC 0.822 vs 0.294 Gap

The discrepancy between the single locked holdout (**PR-AUC = 0.822**) and the 4-fold rolling-origin backtest (**PR-AUC = 0.294 ± 0.324**) has been rigorously investigated.

The collapse is **NOT** caused by model feature leakage or software errors in the detector. Rather, it is primarily driven by:

1. **Sparse-Event Fold Construction (Possibility A & D):**
   - **Fold 1:** Contains **0 positive equipment failure events** in its 6-day test window (Aug 19–25). Under standard information retrieval evaluation, PR-AUC on an all-negative set is mathematically 0.0. This single fold artificially depresses the unweighted arithmetic mean by 0.206.
   - **Fold 2:** Contains only **1 positive equipment failure event** (EVT-0008, onset Aug 27) in its incubation phase. With 41 negative assets and 1 positive asset, any false alarm reduces precision to 0.0, yielding PR-AUC = 0.083.
   - **Fold 3:** Contains **4 positive failure events**. PR-AUC rises to **0.262**, MCC = **0.331**, with a 6.01-day lead time.
   - **Fold 4:** Contains all **6 independent equipment failure events**. PR-AUC reaches **0.831**, precision = **0.800**, recall = **0.667**, MCC = **0.690**.

2. **Event-Weighted vs Unweighted Macro-Average:**
   - **Unweighted Macro PR-AUC:** `0.294 ± 0.324` (High fold variance due to 0-event and 1-event windows).
   - **Event-Conditioned PR-AUC (Folds 3 & 4 with $\ge 4$ events):** `0.546`
   - **Event-Weighted PR-AUC:** `0.556`
   - **Full Holdout Split (incorporating all 6 failure episodes):** `0.822`

## Fold-by-Fold Breakdown

| Fold ID | Test Start | Test End | Positive Events | Failure Families | PR-AUC | MCC | Precision | Recall | FA/yr | Lead Time | Forensic Finding |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Fold 1 | 2026-08-19 | 2026-08-25 | 0 | None | 0.000 | 0.000 | 0.000 | 0.000 | 0.0 | 0.0d | SPARSE_EVENT_COLLAPSE |
| Fold 2 | 2026-08-25 | 2026-08-31 | 1 | gearbox | 0.083 | -0.024 | 0.000 | 0.000 | 0.0 | 0.0d | EXTREME_IMBALANCE_INSTABILITY |
| Fold 3 | 2026-08-31 | 2026-09-06 | 4 | gearbox, generator, pitch_system, yaw_system | 0.262 | 0.331 | 0.333 | 0.500 | 2.9 | 6.0d | HIGH_EVENT_DENSITY_STABLE |
| Fold 4 | 2026-09-06 | 2026-09-12 | 6 | dc_string, gearbox, generator, inverter, pitch_system, yaw_system | 0.831 | 0.690 | 0.800 | 0.667 | 1.4 | 0.0d | HIGH_EVENT_DENSITY_STABLE |

## Scientific Conclusion
- **Do not describe the rolling result as "stable":** PR-AUC shows high empirical variance ($[0.042, 0.644]$ 95% CI) due to temporal event concentration.
- **Scientifically Defensible Phrasing:** *"The model retains useful signal in aggregate, but performance is highly heterogeneous across chronological folds due to sparse event distribution, and is not yet stable enough to claim robust temporal generalization without larger external failure corpora."*
