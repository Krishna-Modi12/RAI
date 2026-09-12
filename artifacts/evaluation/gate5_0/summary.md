# Gate 5.0: Claim Integrity & Evidentiary Provenance Audit

## Executive Summary
Gate 5.0 completes an exhaustive repository-wide claim audit across **3975** occurrences of sensitive benchmark metrics, causal terminology, sample sizes, and performance claims.

### Evidentiary Tier Breakdown:
- **`INTERNAL_SYNTHETIC`:** 3064 claims (measured on 42-asset fleet, 45 calendar days, N=6 independent failure episodes).
- **`EXTERNAL_REAL`:** 602 claims (real Zenodo CARE Farm A SCADA and commercial zero-shot power tracking R^2 = 0.9943).
- **`SIMULATED_OUTCOME`:** 60 claims (decoupled counterfactual regret and VOI simulations; not field ground truth).
- **`HISTORICAL_AUDIT`:** 9 claims (preserved audit trails of retracted legacy marketing claims).
- **`SOFTWARE_INVARIANT`:** 223 claims (non-anticipative signal lineage X_t = f(D_<=t) and temporal embargo math).
- **`MODEL_COMPARISON`:** 17 claims (RdTools SRR/CODS solar soiling comparisons).

---

## Key Reconciliations Enforced:
1. **0.19 vs 0.09 False Alarm Rates Reconciled:**
   - **`0.19 alerts / asset-year`:** v1 holdout baseline post-persistence (6h) and peer gating.
   - **`0.09 alerts / asset-year`:** v2 production funnel with downstream sensor-health and common-cause suppression (~3.8 alarms/yr fleet).
2. **CARE SCADA Tracking (R^2 = 0.9943) vs CARE Anomaly Detection:**
   - Power curve R^2 = 0.9943 confirms expected-behavior model transfer to an unseen commercial turbine.
   - It is strictly segregated from the **Official CARE Anomaly Benchmark**, which evaluates real anomaly detection on Zenodo callsets (Gate 5.1).
3. **Decision Regret Reality:**
   - Historical ₹0 regret was an internal self-consistency check under policy assumptions.
   - Decoupled outcome-world evaluation yields mean regret ₹9,127, optimal rate 71.0%, p95 ₹19,500.
4. **Causality Language Cleansed:**
   - Retracted "proving genuine causal temporal alignment" in favor of "confirming genuine non-anticipative temporal alignment and dependence".
   - Signal processing lookback guarantees are labeled "non-anticipative filtering".
