---
task: care-fidelity-rai
phase: 5
gate: 5.2
status: complete
---

## What was built

- **CARE Scorer Mathematical Audit Test Suite** (`tests/test_gate52_care_scorer_audit.py`, 18 tests): Formal verification of official CARE equations from Gück, Roelofs & Faulstich (2024), covering Coverage $F_{0.5}$, Accuracy $tn/(fp+tn)$, Algorithm 1 Criticality series, Reliability $EF_{0.5}$, Earliness $WS$, and aggregated CARE score boundary rules (all-normal, all-anomaly, zero predictions, accuracy floor). All 18 tests pass with zero mathematical discrepancies.
- **Published Isolation Forest Baseline Reproduction** (`rai/eval/external/care/published_if.py`): Explicit `CARE_PUBLISHED_IF` baseline reproducing the published protocol ($n_{\text{estimators}}=100$, $\text{contamination}=0.09$, PCA retaining 99% variance, fixed seed, strictly fit on train split).
- **RAI Champion Detector Adapter** (`rai/eval/external/care/champion.py`): Operationalizes RAI's hybrid architecture on external SCADA (quadratic expected power curve $P = f(v_{\text{wind}})$ + rotor speed expected curve + standardized residual z-score + 3-step rolling persistence filter) with zero leakage.
- **Feature Policy Engine & Inventory** (`rai/eval/external/care/features.py`): Standardizes `CARE_COMMON` (semantic triad: wind speed, active power, rotor speed mapped across Farms A, B, and C) and `CARE_NATIVE` (farm-specific numeric sensor schemas), cataloging all 1,300 raw column definitions across Farms A (86 cols), B (257 cols), and C (957 cols).
- **Unit & Property Tests** (`tests/test_gate52_baselines_and_champion.py`, 6 tests): Validates PCA 99% retention, median imputation from train split, power curve underproduction detection, and transient spike suppression via persistence gating.
- **Full External Benchmark Execution** (`scripts/gate52_fidelity_and_champion.py`): Evaluated all 18 configurations across 3 farms $\times$ 3 detectors $\times$ 2 policies on real Zenodo SCADA, generating 8 primary artifacts in `artifacts/evaluation/gate52/`.

## Files

- `tests/test_gate52_care_scorer_audit.py` - new (18 mathematical audit tests).
- `rai/eval/external/care/published_if.py` - new (`CARE_PUBLISHED_IF` baseline with PCA 99%).
- `rai/eval/external/care/champion.py` - new (`RAI_CHAMPION` adapter).
- `rai/eval/external/care/features.py` - new (`CARE_COMMON` and `CARE_NATIVE` policies, feature inventory generator).
- `tests/test_gate52_baselines_and_champion.py` - new (6 unit tests).
- `scripts/gate52_fidelity_and_champion.py` - new (end-to-end benchmark orchestrator).
- `docs/evaluation/EXTERNAL_CARE.md` - modified (added Section 8 documenting Gate 5.2 findings).
- `docs/checkpoints/10-care-fidelity-rai.md` - new.
- `artifacts/evaluation/gate52/` - new (8 primary artifacts: `care_fidelity_report.md`, `feature_inventory.{json,csv}`, `published_if_results.{json,csv}`, `rai_results.{json,csv}`, `event_analysis.csv`, `missed_events.csv`, `detected_events.csv`, `protocol_manifest.json`).

## Measured Results (Official CARE Benchmark)

| Farm | Detector | Feature Policy | CARE Score | Coverage | Accuracy | Reliability | Earliness | Event Detection Rate |
|---|---|---|---|---|---|---|---|---|
| Wind Farm A | CARE_PUBLISHED_IF | care_common | **0.616** | 0.450 | 0.929 | 0.652 | 0.121 | 27.3% (3/11) |
| Wind Farm A | CARE_PUBLISHED_IF | care_native | **0.469** | 0.469 | 0.880 | 0.000 | 0.114 | 0.0% (0/11) |
| Wind Farm A | RAI_CHAMPION | care_common | **0.601** | 0.309 | 0.997 | 0.652 | 0.049 | 27.3% (3/11) |
| Wind Farm A | RAI_CHAMPION | care_native | **0.601** | 0.309 | 0.997 | 0.652 | 0.049 | 27.3% (3/11) |
| Wind Farm A | ZSCORE_REFERENCE | care_common | **0.510** | 0.215 | 0.979 | 0.333 | 0.044 | 9.1% (1/11) |
| Wind Farm A | ZSCORE_REFERENCE | care_native | **0.635** | 0.745 | 0.719 | 0.581 | 0.409 | 45.5% (5/11) |
| Wind Farm B | CARE_PUBLISHED_IF | care_common | **0.583** | 0.149 | 0.966 | 0.769 | 0.066 | 66.7% (4/6) |
| Wind Farm B | CARE_PUBLISHED_IF | care_native | **0.434** | 0.312 | 0.875 | 0.000 | 0.109 | 0.0% (0/6) |
| Wind Farm B | RAI_CHAMPION | care_common | **0.560** | 0.007 | 0.999 | 0.769 | 0.025 | 66.7% (4/6) |
| Wind Farm B | RAI_CHAMPION | care_native | **0.560** | 0.007 | 0.999 | 0.769 | 0.025 | 66.7% (4/6) |
| Wind Farm B | ZSCORE_REFERENCE | care_common | **0.406** | 0.039 | 0.992 | 0.000 | 0.010 | 0.0% (0/6) |
| Wind Farm B | ZSCORE_REFERENCE | care_native | **0.383** | 0.742 | 0.383 | 0.658 | 0.518 | 83.3% (5/6) |
| Wind Farm C | CARE_PUBLISHED_IF | care_common | **0.618** | 0.165 | 0.940 | 0.826 | 0.220 | 70.4% (19/27) |
| Wind Farm C | CARE_PUBLISHED_IF | care_native | **0.573** | 0.296 | 0.899 | 0.597 | 0.174 | 29.6% (8/27) |
| Wind Farm C | RAI_CHAMPION | care_common | **0.575** | 0.011 | 0.995 | 0.728 | 0.147 | 55.6% (15/27) |
| Wind Farm C | RAI_CHAMPION | care_native | **0.575** | 0.011 | 0.995 | 0.728 | 0.147 | 55.6% (15/27) |
| Wind Farm C | ZSCORE_REFERENCE | care_common | **0.469** | 0.082 | 0.972 | 0.286 | 0.036 | 7.4% (2/27) |
| Wind Farm C | ZSCORE_REFERENCE | care_native | **0.073** | 0.688 | 0.073 | 0.767 | 0.979 | 92.6% (25/27) |

## Key Insights & Failure Analysis

1. **False Alarm Suppression:** RAI Champion achieves **0.995 to 0.999 accuracy** on normal-operation datasets across all three farms, demonstrating that expected behavior regression combined with 3-step persistence effectively suppresses false alarms from turbulent wind fluctuations.
2. **Published Isolation Forest Benchmark Fidelity:** Under `care_common`, `CARE_PUBLISHED_IF` scores 0.616 (A), 0.583 (B), and 0.618 (C). Under raw `care_native`, PCA 99% variance compression filters out thousands of noisy components, but unweighted full-dimensional density estimation fails to trigger sufficient consecutive alarms on Farm A and B (reliability = 0.000).
3. **High-Dimensional Native Z-Score Collapse:** Unconstrained native z-score collapses to CARE = 0.073 on Farm C because flagging an alarm if *any* of the 952 noisy sensor channels exceeds 2.5 sigma causes false positives on 92.7% of healthy normal timestamps, triggering CARE Rule 2 ($Accuracy < 0.5$).
4. **Failure Classification:** Out of 44 total CARE anomaly events, RAI Champion detected 22 events (50.0% overall event detection rate; 27.3% in A, 66.7% in B, 55.6% in C). All 22 missed events are classified in `artifacts/evaluation/gate52/missed_events.csv` under the factual description `"not detected under the official CARE event criterion (max criticality < 72)"` without physical speculation.
5. **System Bounding:** CARE evaluates anomaly detection on wind turbine SCADA. It does NOT evaluate root-cause diagnosis, sensor safety checks, RAG retrieval, or economic dispatch decisions.
