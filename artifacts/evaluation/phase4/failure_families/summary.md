# Failure-Family Leave-One-Out Generalization Report (Phase 4)

## Executive Finding: Support Sparsity & Generalization Boundaries

Across the 6 independent physical equipment degradation episodes in the fleet:
- **Total Failure Families Identified:** 6 (`gearbox`, `pitch_system`, `yaw_system`, `generator`, `dc_string`, `inverter`)
- **Support per Family:** Exactly **N = 1** failure episode per family across 45 operating days.
- **Mean Event Recall on Unseen Families:** `100.0%`
- **Mean Lead Time:** `5.0 days`
- **PR-AUC Policy:** Marked **`NOT_COMPUTABLE`** across all families.

> [!IMPORTANT]
> **Why PR-AUC is NOT_COMPUTABLE for Individual Families:**  
> A valid precision-recall curve requires multiple positive cases across varying operating conditions. With only N=1 event per family, PR-AUC either degenerates to a step-function or produces an arbitrary number based on the single event's threshold ranking. Rather than manufacturing an illusory decimal, RAI reports event-level recall and marks PR-AUC as `NOT_COMPUTABLE`.

## Family-by-Family Breakdown

| Family Name | Asset ID | Scenario | Support | Train Events | Test Events | Event Detected | Lead Time | PR-AUC Status |
|---|---|---|---|---|---|---|---|---|
| `gearbox` | `WT-017` | gearbox_bearing_wear | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |
| `pitch_system` | `WT-011` | pitch_misalignment | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |
| `yaw_system` | `WT-015` | yaw_misalignment | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |
| `generator` | `WT-004` | generator_overheating | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |
| `dc_string` | `INV-007` | string_outage | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |
| `inverter` | `INV-015` | inverter_derate | 1 | 5 | 1 | YES | 5.0d | `NOT_COMPUTABLE` |

## Scientific Conclusion
Generalization across failure families is driven by **domain-invariant physical residuals** (e.g., power vs expected curve, thermal rise above ambient, peer divergence) rather than family-specific classification heads. However, claiming statistical family-transfer stability requires scaling to external fleet corpora with dozens of events per family.
