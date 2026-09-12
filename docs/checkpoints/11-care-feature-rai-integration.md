---
task: care-feature-rai-integration
phase: 5
gate: 5.3
status: complete
---

## What was built

- **CARE Semantic Feature Recovery & Cataloging** (`rai/eval/external/care/features.py`): Full inventory of all 361 sensor descriptions across Farms A (54), B (63), and C (238) mapped into 16 physical domains (`wind_speed`, `active_power`, `rotor_speed`, `reactive_power`, `temperature`, `pitch`, `yaw`, `vibration`, `generator`, `gearbox`, `nacelle`, `electrical`, `hydraulic`, `pressure`, `counters`, `angles`) with explicit exclusion tracking.
- **Three Frozen Feature Policies**:
  - `CARE_2D`: Narrow canonical 2-feature baseline (`wind_speed_ms`, `power_kw`) reproducing Gate 5.1/5.2.
  - `CARE_COMMON`: Cross-farm semantic triad matching WindADBench Track 4 (`wind_speed`, `active_power`, `rotor_speed`).
  - `CARE_NATIVE_SEMANTIC`: Full farm-specific numeric sensor space (81 features in Farm A, 252 in Farm B, 952 in Farm C).
- **Published Isolation Forest Baseline Fidelity** (`rai/eval/external/care/published_if.py`):
  - `CARE_PAPER_IF`: Exact published configuration (Gück et al. 2024 §4.2.1: $n_{\text{estimators}}=100$, $\text{contamination}=0.09$, PCA retaining 99% variance, fixed seed labeled `REPRODUCIBILITY_CHOICE`, train split only).
  - `RAI_COMPAT_IF`: Internal Gate 5.1/5.2 baseline (same trees and contamination, raw features without PCA).
- **RAI Champion Detector Adapter** (`rai/eval/external/care/champion.py`): Operationalized hybrid quadratic expected power curve + rotor speed curve + standardized residual z-score + 3-step persistence filter under official CARE scoring.
- **Full Benchmark Execution** (`scripts/run_gate53_fast.py`): Evaluated all 95 datasets (44 anomaly events) across all 3 farms $\times$ 3 detectors $\times$ 3 feature policies under the official CARE scorer. Emitted 13 primary machine-readable artifacts in `artifacts/evaluation/gate53/`.

## Files

- `rai/eval/external/care/features.py` — feature inventory, domain classifier, and policy extractor.
- `rai/eval/external/care/published_if.py` — published CARE IF (PCA 99%) and RAI-compatible IF implementations.
- `rai/eval/external/care/champion.py` — RAI Champion adapter with representation audit and input manifests.
- `scripts/run_gate53_fast.py` — streaming multi-farm, multi-detector, multi-policy benchmark runner.
- `tests/test_gate53_cross_turbine.py` — 19 comprehensive unit tests verifying features, baseline fidelity, and leakage controls.
- `artifacts/evaluation/gate53/` — 13 machine-readable artifacts (`care_feature_inventory.{csv,json}`, `feature_policy_manifest.json`, `published_if_results.{csv,json}`, `rai_results.{csv,json}`, `feature_policy_comparison.csv`, `event_results.csv`, `missed_events.csv`, `false_alarm_events.csv`, `protocol_manifest.json`, `summary.md`).
- `docs/checkpoints/11-care-feature-rai-integration.md` — this checkpoint.

## How it was verified

1. **Targeted Tests:** `pytest tests/test_gate53_cross_turbine.py -v` (19/19 passing).
2. **Lint Cleanliness:** `ruff check .` (0 errors, `All checks passed!`).
3. **External Benchmark Execution:** `python scripts/run_gate53_fast.py` evaluated all 95 datasets across Farms A, B, and C in 864.3s with zero runtime failures or data leakage.

## Measured Results (Official CARE Benchmark)

| Farm | Detector | Feature Policy | CARE Score | Coverage ($F_{0.5}$) | Accuracy (TNR) | Reliability ($eF_{0.5}$) | Earliness ($WS$) | Detected Events | Alarm Incidence |
|---|---|---|---|---|---|---|---|---|---|
| Wind Farm A | CARE_PAPER_IF | `care_2d` | **0.528** | 0.407 | 0.892 | 0.333 | 0.114 | 1/11 (9.1%) | 11/11 (100.0%) |
| Wind Farm A | CARE_PAPER_IF | `care_common` | **0.616** | 0.450 | 0.929 | 0.652 | 0.121 | 3/11 (27.3%) | 11/11 (100.0%) |
| Wind Farm A | CARE_PAPER_IF | `care_native_semantic` | **0.469** | 0.469 | 0.880 | 0.000 | 0.114 | 0/11 (0.0%) | 11/11 (100.0%) |
| Wind Farm A | RAI_COMPAT_IF | `care_2d` | **0.541** | 0.456 | 0.889 | 0.333 | 0.137 | 1/11 (9.1%) | 11/11 (100.0%) |
| Wind Farm A | RAI_COMPAT_IF | `care_common` | **0.623** | 0.476 | 0.929 | 0.652 | 0.129 | 3/11 (27.3%) | 11/11 (100.0%) |
| Wind Farm A | RAI_COMPAT_IF | `care_native_semantic` | **0.641** | 0.527 | 0.935 | 0.652 | 0.155 | 3/11 (27.3%) | 11/11 (100.0%) |
| Wind Farm A | RAI_CHAMPION | `care_2d` | **0.000** | 0.182 | 1.000 | 0.000 | 0.000 | 0/11 (0.0%) | 0/11 (0.0%) |
| Wind Farm A | RAI_CHAMPION | `care_common` | **0.601** | 0.309 | 0.997 | 0.652 | 0.049 | 3/11 (27.3%) | 10/11 (90.9%) |
| Wind Farm A | RAI_CHAMPION | `care_native_semantic` | **0.601** | 0.309 | 0.997 | 0.652 | 0.049 | 3/11 (27.3%) | 10/11 (90.9%) |
| Wind Farm B | CARE_PAPER_IF | `care_2d` | **0.425** | 0.278 | 0.880 | 0.000 | 0.086 | 0/6 (0.0%) | 9/9 (100.0%) |
| Wind Farm B | CARE_PAPER_IF | `care_common` | **0.583** | 0.149 | 0.966 | 0.769 | 0.066 | 4/6 (66.7%) | 9/9 (100.0%) |
| Wind Farm B | CARE_PAPER_IF | `care_native_semantic` | **0.434** | 0.312 | 0.875 | 0.000 | 0.109 | 0/6 (0.0%) | 9/9 (100.0%) |
| Wind Farm B | RAI_COMPAT_IF | `care_2d` | **0.432** | 0.270 | 0.902 | 0.000 | 0.087 | 0/6 (0.0%) | 9/9 (100.0%) |
| Wind Farm B | RAI_COMPAT_IF | `care_common` | **0.586** | 0.146 | 0.976 | 0.769 | 0.064 | 4/6 (66.7%) | 9/9 (100.0%) |
| Wind Farm B | RAI_COMPAT_IF | `care_native_semantic` | **0.603** | 0.201 | 0.956 | 0.833 | 0.067 | 3/6 (50.0%) | 9/9 (100.0%) |
| Wind Farm B | RAI_CHAMPION | `care_2d` | **0.000** | 0.000 | 1.000 | 0.000 | 0.000 | 0/6 (0.0%) | 0/9 (0.0%) |
| Wind Farm B | RAI_CHAMPION | `care_common` | **0.560** | 0.007 | 0.999 | 0.769 | 0.025 | 4/6 (66.7%) | 8/9 (88.9%) |
| Wind Farm B | RAI_CHAMPION | `care_native_semantic` | **0.560** | 0.007 | 0.999 | 0.769 | 0.025 | 4/6 (66.7%) | 8/9 (88.9%) |
| Wind Farm C | CARE_PAPER_IF | `care_2d` | **0.553** | 0.267 | 0.898 | 0.588 | 0.113 | 6/27 (22.2%) | 31/31 (100.0%) |
| Wind Farm C | CARE_PAPER_IF | `care_common` | **0.618** | 0.165 | 0.940 | 0.826 | 0.220 | 19/27 (70.4%) | 31/31 (100.0%) |
| Wind Farm C | CARE_PAPER_IF | `care_native_semantic` | **0.573** | 0.296 | 0.899 | 0.597 | 0.174 | 8/27 (29.6%) | 31/31 (100.0%) |
| Wind Farm C | RAI_COMPAT_IF | `care_2d` | **0.587** | 0.250 | 0.907 | 0.714 | 0.154 | 9/27 (33.3%) | 31/31 (100.0%) |
| Wind Farm C | RAI_COMPAT_IF | `care_common` | **0.603** | 0.236 | 0.915 | 0.759 | 0.189 | 12/27 (44.4%) | 31/31 (100.0%) |
| Wind Farm C | RAI_COMPAT_IF | `care_native_semantic` | **0.635** | 0.253 | 0.923 | 0.842 | 0.235 | 16/27 (59.3%) | 31/31 (100.0%) |
| Wind Farm C | RAI_CHAMPION | `care_2d` | **0.000** | 0.000 | 1.000 | 0.000 | 0.000 | 0/27 (0.0%) | 0/31 (0.0%) |
| Wind Farm C | RAI_CHAMPION | `care_common` | **0.575** | 0.011 | 0.995 | 0.728 | 0.147 | 15/27 (55.6%) | 22/31 (71.0%) |
| Wind Farm C | RAI_CHAMPION | `care_native_semantic` | **0.575** | 0.011 | 0.995 | 0.728 | 0.147 | 15/27 (55.6%) | 22/31 (71.0%) |

## Key Insights & Failure Analysis

1. **Feature Scope Impact ($\text{CARE\_2D} \to \text{CARE\_COMMON}$):** Expanding from the narrow 2D representation (`wind_speed_ms`, `power_kw`) to the 3D cross-farm semantic triad (+ `rotor_speed`) is the dominant factor resolving detector performance. For `CARE_PAPER_IF`, CARE scores increase by **+0.088 on Farm A**, **+0.158 on Farm B**, and **+0.065 on Farm C**.
2. **High-Dimensional Native PCA Variance Dilution ($\text{CARE\_COMMON} \to \text{CARE\_NATIVE\_SEMANTIC}$):** For `CARE_PAPER_IF`, fitting PCA 99% variance across all 86–952 raw numeric features dilutes event-level anomaly sensitivity. Variance in dominant non-fault signals reduces consecutive alarm duration below the $c \ge 72$ threshold, causing reliability to collapse to 0.000 on Farms A and B.
3. **RAI Champion Specificity & Representation Invariance:** `RAI_CHAMPION` achieves **0.995 to 0.999 normal operation accuracy** (virtually zero false alarms on normal operation), compared to 0.880–0.966 for IF baselines which alarm on every normal dataset (100% dataset-level alarm incidence). Because `RAI_CHAMPION` operates on canonical physical equations, it is invariant between `CARE_COMMON` and `CARE_NATIVE_SEMANTIC` (0.601 in A, 0.560 in B, 0.575 in C).
4. **Event Forensics:** Across all 44 anomaly events, missed events failed the official CARE event criterion (Algorithm 1 criticality counter < 72). No speculative physical explanations are assigned.

## Next

- **Gate 5.4:** Full 6-Way Cross-Farm Transfer Matrix ($A \to B, A \to C, B \to A, B \to C, C \to A, C \to B$) under frozen `CARE_COMMON` feature mapping.
