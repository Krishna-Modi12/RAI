# Gate 3A-1 Master Scorecard: Temporal Stability Forensics & Benchmark Integrity

## Executive Overview
Gate 3A-1 successfully audits the software/evaluation harness and explains the mathematical mechanism causing the gap between the locked holdout ($	ext{PR-AUC} = 0.822$) and the 4-fold rolling origin ($	ext{PR-AUC} = 0.294 \pm 0.324$).

- **Execution Runtime:** 1.55 seconds
- **Git Commit:** `a08bf53c3cc9021f59eb4f9779a925f44332c112`
- **Derived Embargo Enforced:** `342.0 hours` ($336	ext{h} + 6	ext{h} = 342	ext{h}$)
- **Status Classification:** `PASS (Software Hardened & Discrepancy Explained)`

---

## Pillar Scorecard

| Audit Pillar | Metric | Measured Value | Benchmark Status | Scientific Assessment |
|---|---|---|---|---|
| **Embargo Math** | Derived Embargo Gap | `342.0h` | `PASS` | Formally derived and boundary-tested ($341.99	ext{h}$ fail / $342.00	ext{h}$ pass). |
| **Documentation Scrub** | Legacy Claim Verification | `100% Verified` | `PASS` | Retracted $3218 	o 4$, $13.5	ext{d}$, $99.99\%$ from documentation and web UI. |
| **Reproducibility** | Frozen Baseline Metadata | `a08bf53c` | `PASS` | Immutable dataset, configuration, schema, and model hashes recorded. |
| **Rolling Backtest** | Macro Arithmetic PR-AUC | `0.294 ± 0.324` | `PARTIAL` | High fold heterogeneity caused by 0 events in Fold 1 and 1 event in Fold 2. |
| **Rolling Backtest** | Event-Weighted PR-AUC | `0.5559` | `EXPLORATORY` | Reduces influence of low-event folds; does NOT establish temporal generalization. |
| **Locked Holdout** | Single Origin PR-AUC | `0.822` | `PASS` | Evaluates Sep 06–12 (overlaps with Fold 4; not an independent confirmation). |
| **Locked Holdout** | Matthews Correlation Coeff | `0.690` | `PASS` | Confirms strong true correlation on multi-event late holdout. |
| **Event Accounting** | Failure Episodes ($N$) | `N = 6` | `PASS` | 4 wind faults, 2 solar faults evaluated as independent physical units. |
| **Event Accounting** | Event Recall | `83.3%` | `PASS` | 5 of 6 episodes detected prior to failure (1 subtle solar DC string missed). |
| **Event Accounting** | Median Detection Lead Time | `5.0 days` | `PASS` | 5.0-day median advance warning (range: 2.0d to 6.0d, IQR: 1.0d). |
| **Uncertainty Bounds** | Event Bootstrap (95% CI) | `[0.50, 1.00]` | `PASS` | Accurately communicates the broad epistemic bounds of an N=6 failure corpus. |
| **Baseline Fit** | Digital Twin Power $R^2$ | `0.9944` | `PASS` | Physical expected-power tracking is completely stable across all folds ($R^2 > 0.99$). |
| **Threshold Stability** | Production vs Optimal | `θ=0.45 vs 0.58` | `PARTIAL` | Fixed threshold $\theta=0.45$ optimal for multi-event folds, suboptimal for 1-event folds. |
| **Failure Families** | Leave-One-Family-Out | `Feasibility: False` | `INSUFFICIENT_DATA` | Sample size ($N=1$ per family) too small for valid cross-validation without CARE. |

---

## Core Forensic Findings
1. **Event Sparsity and Fold Slicing:**
   Fold 1 has 0 events ($\text{PR-AUC} = \text{null}$, `NO_POSITIVE_EVENTS`); Fold 2 has 1 event in incubation ($\text{PR-AUC} = 0.083$); Fold 4 has all 6 events ($\text{PR-AUC} = 0.831$). An unweighted arithmetic mean averages these to $0.294$, while valid-fold macro averaging yields $0.392 \pm 0.319$.
2. **Generalization Status:**
   Event weighting reduces the influence of event-free folds, raising the rolling summary to 0.556; however, this remains materially below the locked late-period holdout (0.822) and does not by itself establish robust temporal generalization. Furthermore, Fold 4 evaluates the exact same period as the locked holdout (Sep 06–12).
3. **Epistemic Honesty:**
   With $N=6$ physical failure episodes, wide confidence intervals are mathematically inevitable. Temporal generalization remains unresolved until evaluated on external multi-year wind SCADA (CARE/WindADBench).
