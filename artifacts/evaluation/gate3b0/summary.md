# Gate 3B-0: Benchmark Interpretation Repair & Multi-View Aggregation

## Executive Summary
Gate 3B-0 formally corrects the statistical aggregation semantics and removes over-strong claims from Phase 3A-1:
1. **Zero-Positive Folds Handled Rigorously:** Fold 1 has 0 positive events; its PR-AUC is mathematically indeterminate. It is represented as `null` (`NO_POSITIVE_EVENTS`) rather than arbitrarily coerced to `0.0`.
2. **Three Formal Evaluation Views:**
   - **View A (Macro Valid-Fold):** Averages across the 3 folds with positive events (Folds 2, 3, 4), yielding **`0.3919 ± 0.3186`** (MCC: `0.3323`).
   - **View B (Micro / Pooled PR-AUC):** Pools predictions across valid chronological test windows, yielding **`0.5488`**.
   - **View C (Event-Level Alarm System):** Evaluates physical failure episode detection: **`83.3%`** event recall (5 of 6 episodes) with a median lead time of **`5.0 days`**.
3. **Exploratory Event-Weighted Aggregation:** Weighting by event count yields **`0.5559`**. This is labeled strictly as an exploratory metric.
4. **Holdout vs Fold 4 Temporal Overlap Formally Declared:**
   Fold 4 (Sep 06–12, $\text{PR-AUC} = 0.8306$) and the locked holdout (Sep 06–12, $\text{PR-AUC} = 0.8220$) evaluate the exact same late calendar week where all 6 failures manifest. They are not independent validation experiments.
5. **Scientific Verdict:**
   *Temporal generalization remains `UNRESOLVED`. Event weighting raises the rolling summary to 0.556, but this remains materially below the late-period holdout (0.822). Robust temporal generalization cannot be claimed without external multi-year wind SCADA corpora (CARE / WindADBench).*

---

## Aggregation Comparison Matrix

| Evaluation View | Metric | Value | Interpretation & Methodological Guardrail |
|---|---|---|---|
| **View A: Macro Valid-Fold** | PR-AUC Mean | **`0.3919 ± 0.3186`** | Arithmetic mean across Folds 2, 3, 4 ($N=3$). Fold 1 excluded as `null`. |
| **View A: Macro Valid-Fold** | MCC Mean | **`0.3323`** | Positive correlation preserved across non-empty evaluation folds. |
| *Prior Naive All-Fold* | *Arithmetic Mean* | *`0.2939`* | *Methodologically flawed: arbitrarily coerced Fold 1 (0 events) to 0.0.* |
| **View B: Micro / Pooled** | Pooled PR-AUC | **`0.5488`** | Concatenated prediction vector across valid test windows (11 positive event-windows). |
| **View C: Event-Level Alarm** | Event Recall | **`83.3%`** | 5 of 6 physical failure episodes detected prior to breakdown. |
| **View C: Event-Level Alarm** | Median Lead Time | **`5.0 days`** | Advance warning horizon (IQR: `1.0 days`). |
| **Exploratory Metric** | Event-Weighted PR-AUC | **`0.5559`** | *Exploratory only. Dampens 1-event fold influence; does NOT prove fold artifact.* |
| **Locked Late Holdout** | Holdout PR-AUC | **`0.8220`** | Evaluates Sep 06–12. Overlaps with Fold 4; not an independent confirmation. |

---

## Status Declaration
- **Benchmark Integrity & Evaluation Framing:** `PASS`
- **Temporal Generalization Claim:** `UNRESOLVED`
- **Independent Failure Event Sample:** `INSUFFICIENT_DATA (N=6)`
