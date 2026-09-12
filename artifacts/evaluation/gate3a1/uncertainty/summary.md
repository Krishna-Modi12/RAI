# Gate 3A-1: Dependence-Aware Uncertainty Quantification

## Methodology Audit
Standard row-level (timestamp-level) bootstrap treats thousands of sequential 10-minute telemetry records as independent identically distributed (i.i.d.) observations. Because sequential telemetry is heavily autocorrelated and belongs to the same physical degradation trajectory, timestamp bootstrap produces artificially narrow confidence intervals that underestimate true epistemic uncertainty.

In Gate 3A-1, we enforce **dependence-aware resampling**:
1. **Event-Level Bootstrap:** Resampling unit is the independent failure episode ($N=6$).
2. **Asset-Cluster Bootstrap:** Resampling unit is the physical turbine or inverter ($N=42$).

## Measured Uncertainty Bounds (95% Confidence)

| Metric | Point Estimate | 95% CI (Dependence-Aware) | Resampling Unit | Sample Size ($N$) | Epistemic Assessment |
|---|---|---|---|---|---|
| **event_recall** | `0.83` | `[0.5, 1.0]` | independent_failure_episode | N=6 | N=6 failure episodes is a very small sample. A single missed... |
| **median_lead_time_days** | `5.0` | `[0.0, 6.0]` | independent_failure_episode | N=6 | Resampled over detected episodes. CI spans 2.0 to 6.0 days.... |
| **holdout_pr_auc** | `0.976` | `[0.85, 1.0]` | physical_asset_cluster | N=42 | Cluster bootstrap across 42 assets (6 faulted). Accounts for... |
| **holdout_mcc** | `0.806` | `[0.469, 1.0]` | physical_asset_cluster | N=42 | Asset cluster bootstrap. Bounds reflect false alarm variatio... |
| **rolling_macro_pr_auc** | `0.294` | `[0.042, 0.644]` | chronological_fold | N=4 | Computed across 4 chronological folds. Extremely wide CI [0.... |

## Core Scientific Conclusion
- **The 6 Events are the True Information-Bearing Units:** The 45,360 monitored asset-hours do not represent 45,360 independent experiments; they contain exactly 6 physical failure episodes.
- **Why False Precision is Avoided:** With $N=6$, precision to three decimal places on event metrics is statistically spurious. A single missed detection swings event recall by 16.7 percentage points.
- **Need for External Corpora:** Establishing narrow statistical bounds on early fault detection requires scaling to real multi-year wind SCADA corpora (such as the 89-turbine-year CARE benchmark).