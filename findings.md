# Forensic Findings & Discoveries — RAI Phase 2

## 1. Evaluation & Metric Claims Audit Findings
- **Claim: "CARE Benchmark Score 0.659"**:
  - The number 0.659 was computed on the synthetic 42-asset fleet using a formula inspired by Gück et al. (2024), NOT on the official CARE to Compare dataset (36 turbines, 44 anomalous intervals, 51 normal intervals).
  - Calling this "CARE Score" risks severe penalty from evaluators. It must be classified as `PARTIALLY VERIFIED` and renamed `RAI Operational Score (CARE-inspired)`.
- **Claim: "PR-AUC = 0.948"**:
  - PR-AUC measures precision vs recall across classification thresholds in an imbalanced setting. It is mathematically verified in our benchmark runner, but must NEVER be equated to "94.8% accuracy".
- **Claim: "Cross-site generalization PR-AUC = 0.894"**:
  - The current split tested between Kutch Wind Farm and Charanka Solar Park. Wind turbines and solar inverters have completely different physics, features, and degradation mechanisms. This is cross-domain transfer, NOT within-domain geographical site generalization.
- **Claim: "45,360 monitoring hours proves fleet reliability"**:
  - 42 assets over 45 days is 45,360 observation hours, but in `rai/store.py` only 6 equipment failure events are injected (WT-017, WT-004, WT-011, INV-009, INV-018, etc.). The sample size of independent failure episodes is 6, not 45,360.
- **Claim: "Brier = 0.017, ECE = 0.1286 proves 80% risk = 80% probability"**:
  - Brier score combines calibration, resolution, and uncertainty. An ECE of 0.1286 indicates ~13% expected calibration deviation across bins, which is modest, not near-perfect. Reliability curves must be plotted with bin counts.
- **Claim: "100% additive loss decomposition"**:
  - An additive identity ($\sum \text{losses} = 100\%$) is mathematically enforced by defining unexplained = total - known. It does not constitute causal identification. Must be labeled "model-based loss attribution" with confidence intervals.

## 2. Environmental Kinetics Findings
- CAMS aerosol optical depth (AOD) and particulate matter (PM10, dust $\mu g/m^3$) measure column and near-surface atmospheric concentration, not physical deposition on tilted PV glass.
- Deposition requires a transfer function modeling wind velocity (stagnation allows settling, high wind causes resuspension), relative humidity (high RH causes adhesion/dew), and cumulative exposure over time.
- Rainfall $< 2-3\text{ mm}$ with heavy antecedent dust can create muddy streaks or cementation, but this is a probabilistic hypothesis depending on tilt angle, ambient temperature, and dust mineralogy, not an absolute deterministic rule.

## 3. Decision Intelligence Findings
- Rather than only deciding "clean now" vs "do nothing", the system must evaluate dynamic opportunity windows: "wait 24h", "wait 72h", "wait for rain".
- Expected cost of action must be compared to the ex-post optimal cost to compute Decision Regret ($\text{Cost}_{\text{chosen}} - \text{Cost}_{\text{optimal}}$).
- Value of Information (VOI) formally justifies when paying for inspection reduces uncertainty enough to outweigh its cost.
