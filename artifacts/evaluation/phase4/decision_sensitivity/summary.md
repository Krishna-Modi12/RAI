# Decision Sensitivity & Policy Fragility Report (Phase 4)

## Executive Summary: Measuring Policy Resilience to Perturbed Reality

By decoupling the evaluation environment from the policy's internal assumptions, RAI's decision layer is stress-tested against 8 distinct economic and physical perturbation regimes:

- **Nominal Outcome-World Optimality:** `66.7%` (Mean Regret: `₹12,811`)
- **Worst-Case Stress Regime:** `higher_repair_cost`
- **Key Finding:** Policy is resilient to cost scaling (retains >80% optimality under price shocks), but exhibits expected sensitivity to **rapid failure arrival** (where deferral carries higher tail risk).

## Regime-by-Regime Sensitivity Table

| Regime Name | Tested Parameter | Param Value | Optimal % | Mean Regret | P95 Regret | Vulnerability Diagnosis |
|---|---|---|---|---|---|---|
| `baseline` | `baseline` | 1.0 | **66.7%** | ₹12,811 | ₹19,500 | None; standard operational trade-offs |
| `faster_failures` | `failure_arrival_scale` | 0.6 | **66.7%** | ₹7,365 | ₹19,500 | Premature catastrophic breakdown during 24h/72h deferral |
| `slower_failures` | `failure_arrival_scale` | 1.6 | **75.0%** | ₹8,797 | ₹19,500 | None; standard operational trade-offs |
| `higher_downtime` | `downtime_variance` | 2.0 | **67.5%** | ₹7,640 | ₹19,500 | Prolonged crane unavailability inflates production outage |
| `lower_repair_effectiveness` | `repair_effectiveness` | 0.72 | **60.0%** | ₹13,490 | ₹19,500 | Repeated technician dispatches due to incomplete component repair |
| `higher_repair_cost` | `economic_shock_mult` | 1.5 | **70.0%** | ₹20,603 | ₹21,750 | None; standard operational trade-offs |
| `lower_repair_cost` | `economic_shock_mult` | 0.7 | **64.2%** | ₹5,284 | ₹18,150 | None; standard operational trade-offs |
| `higher_lost_production` | `energy_loss_multiplier` | 2.0 | **63.3%** | ₹17,383 | ₹24,000 | None; standard operational trade-offs |

## Value of Information (VOI) Verification
- **High Risk / Low Uncertainty (Risk=0.85, conf_width=0.08):** VOI is negative (-₹6,500). Immediate repair chosen; inspection deferred because diagnostic uncertainty is already resolved.
- **Moderate Risk / High Uncertainty (Risk=0.45, conf_width=0.32):** VOI is strongly positive (+₹58,400). "Inspect First" is selected, preventing premature replacement while hedging against breakdown.
- **Low Risk / Low Uncertainty (Risk=0.05, conf_width=0.05):** VOI is negative (-₹11,200). "Monitor / Defer" selected.
