# Gate 3B-0 Forensic Scorecard: Benchmark Interpretation Repair & Multi-View Aggregation

**Gate:** Gate 3B-0 (Foundational Gate of Phase 3B)  
**Status:** `PASS (Framing & Aggregation Repaired)`  
**Scientific Verdict:** `Temporal Generalization Unresolved`  
**Execution Runtime:** 0.00 seconds  

---

## 1. Why Gate 3B-0 Was Required
In Phase 3A-1, the forensic decomposition discovered that:
- Fold 1 contains 0 events ($	ext{PR-AUC} = 0.0$)
- Fold 2 contains 1 event ($	ext{PR-AUC} = 0.0833$)
- Fold 3 contains 4 events ($	ext{PR-AUC} = 0.2619$)
- Fold 4 contains 6 events ($	ext{PR-AUC} = 0.8306$)

However, two critical methodological errors were identified:
1. **Coercing Undefined Metrics to Zero:**  
   Fold 1 has zero positive events. In binary classification, Precision-Recall curves require positive samples to define recall $	ext{TP} / P$. When $P = 0$, PR-AUC is mathematically indeterminate. Forcing Fold 1 to $0.0$ artificially dragged down the macro average.
2. **Over-Strong Claims Regarding Event Weighting:**  
   The statement that event-weighted PR-AUC ($0.5559$) "confirms that the collapse is an evaluation fold artifact" was scientifically unjustifiable. $0.5559$ is materially lower than $0.8220$; it demonstrates that event scarcity plays a role, but it does **not** prove temporal generalization.
3. **Unacknowledged Temporal Overlap:**  
   Fold 4 evaluates Sep 06–12, 2026. The locked holdout evaluates Sep 06–12, 2026. Treating both as independent confirmations was an error of double-counting.

---

## 2. Multi-View Aggregation Results

### View A: Macro Valid-Fold Evaluation
When folds without positive events are represented as `null`, the macro average over valid folds ($N=3$: Folds 2, 3, 4) is:
$$\text{Macro Valid-Fold PR-AUC} = \frac{0.0833 + 0.2619 + 0.8306}{3} = \mathbf{0.3919 \pm 0.3186}$$
$$\text{Macro Valid-Fold MCC} = \frac{-0.0244 + 0.3311 + 0.6903}{3} = \mathbf{0.3323}$$

### View B: Micro / Pooled PR-AUC Evaluation
Pooling the predicted risk scores and true event labels across the 126 asset-windows of Folds 2, 3, and 4 yields:
$$\text{Pooled Micro PR-AUC} = \mathbf{0.5488}$$

### View C: Event-Level Alarm System Evaluation
Treating the 6 physical failure episodes as the primary evaluation units:
- **Event Recall:** **`83.3%`** (5 of 6 episodes detected early)
- **Median Advance Warning:** **`5.0 days`** (IQR: 1.0 days; range: 2.0d to 6.0d)
- **False Alarm Rate:** $0.19/\text{asset-year}$ (Holdout) / $0.026/\text{asset-year}$ (Rolling average)

### Exploratory Aggregation:
- **Event-Weighted PR-AUC:** **`0.5559`**  
  *Qualification: Non-standard exploratory metric. Weighting folds by event count mitigates the impact of 1-event windows, but 0.556 remains far below 0.822.*

---

## 3. Demarcation of Fold 4 vs Locked Holdout Overlap
- **Fold 4 Evaluation Window:** `2026-09-06T07:50:00Z` to `2026-09-12T07:50:00Z` ($\text{PR-AUC} = 0.8306$)
- **Locked Holdout Window:** `2026-09-06T00:00:00Z` to `2026-09-12T00:00:00Z` ($\text{PR-AUC} = 0.8220$)

Both evaluate the final week of the 45-day campaign, where all 6 defect episodes have developed high-amplitude anomalies. They reflect essentially the same underlying event population.

---

## 4. Scientific Verdict & Gate Conclusion
- **Evaluation Framing & Methodology:** `PASS`
- **Temporal Generalization:** `UNRESOLVED`
- **Data Limitations:** $N=6$ independent failure episodes is insufficient for robust temporal guarantees.
- **Next Gate:** Proceed to **Gate 3B-1 (Proper Temporal Robustness & Stratification)** before attempting external CARE ingestion.
