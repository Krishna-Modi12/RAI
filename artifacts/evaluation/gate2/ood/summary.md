# OOD Perturbation Suite — Results

Every perturbation is applied to real synthetic-fleet telemetry (never to labels), with severities and seeds fixed in rai/eval/ood.py before this run. The baseline is recomputed in this same process run (not read from a possibly-concurrent artifacts/evaluation/results.json) so deltas are internally consistent.

Assets: 42, events: 6, perturbations: 12, elapsed: 839.2s

## Baseline (unperturbed)

| model | CARE | PR-AUC | MCC | FA/yr | median lead (d) |
|---|---|---|---|---|---|
| baseline_4_isolation_forest | 0.691 | 0.594 | 0.563 | 0.19 | 6.5 |
| challenger_hybrid_ensemble | 0.797 | 0.822 | 0.690 | 0.19 | 5.0 |

## Perturbed runs

| perturbation | severity | model | CARE | ΔCARE | PR-AUC | ΔPR-AUC | FA/yr | median lead (d) |
|---|---|---|---|---|---|---|---|---|
| sensor_noise_moderate | moderate | baseline_4_isolation_forest | 0.276 | -0.415 | 0.162 | -0.432 | 8.12 | 0.0 |
| sensor_noise_moderate | moderate | challenger_hybrid_ensemble | 0.365 | -0.432 | 0.135 | -0.686 | 4.06 | 0.0 |
| sensor_noise_severe | severe | baseline_4_isolation_forest | 0.276 | -0.415 | 0.150 | -0.444 | 8.12 | 0.0 |
| sensor_noise_severe | severe | challenger_hybrid_ensemble | 0.280 | -0.517 | 0.189 | -0.632 | 7.92 | 0.0 |
| missingness_moderate | moderate | baseline_4_isolation_forest | 0.775 | +0.083 | 0.655 | +0.061 | 0.19 | 7.0 |
| missingness_moderate | moderate | challenger_hybrid_ensemble | 0.782 | -0.014 | 0.863 | +0.042 | 0.19 | 5.0 |
| missingness_severe | severe | baseline_4_isolation_forest | 0.651 | -0.041 | 0.502 | -0.092 | 4.06 | 11.0 |
| missingness_severe | severe | challenger_hybrid_ensemble | 0.748 | -0.049 | 0.784 | -0.037 | 0.19 | 4.5 |
| drift_moderate | moderate | baseline_4_isolation_forest | 0.287 | -0.404 | 0.256 | -0.338 | 7.54 | 0.0 |
| drift_moderate | moderate | challenger_hybrid_ensemble | 0.291 | -0.506 | 0.819 | -0.002 | 7.34 | 0.0 |
| drift_severe | severe | baseline_4_isolation_forest | 0.276 | -0.415 | 0.167 | -0.427 | 8.12 | 0.0 |
| drift_severe | severe | challenger_hybrid_ensemble | 0.276 | -0.521 | 0.594 | -0.228 | 8.12 | 0.0 |
| extreme_weather_moderate | moderate | baseline_4_isolation_forest | 0.780 | +0.089 | 0.593 | -0.001 | 0.39 | 6.5 |
| extreme_weather_moderate | moderate | challenger_hybrid_ensemble | 0.815 | +0.018 | 0.856 | +0.034 | 0.19 | 6.0 |
| extreme_weather_severe | severe | baseline_4_isolation_forest | 0.600 | -0.091 | 0.580 | -0.014 | 0.77 | 5.0 |
| extreme_weather_severe | severe | challenger_hybrid_ensemble | 0.737 | -0.060 | 0.749 | -0.073 | 0.58 | 4.5 |
| degradation_weaker | weaker_signal | baseline_4_isolation_forest | 0.355 | -0.336 | 0.235 | -0.359 | 4.44 | 0.0 |
| degradation_weaker | weaker_signal | challenger_hybrid_ensemble | 0.722 | -0.075 | 0.931 | +0.109 | 1.35 | 6.5 |
| degradation_stronger | stronger_signal | baseline_4_isolation_forest | 0.336 | -0.355 | 0.235 | -0.359 | 5.22 | 0.0 |
| degradation_stronger | stronger_signal | challenger_hybrid_ensemble | 0.630 | -0.167 | 0.731 | -0.090 | 2.71 | 5.0 |
| weather_permutation_partial | partial | baseline_4_isolation_forest | 0.784 | +0.092 | 0.640 | +0.046 | 0.19 | 7.0 |
| weather_permutation_partial | partial | challenger_hybrid_ensemble | 0.793 | -0.004 | 0.738 | -0.084 | 0.19 | 5.0 |
| weather_permutation_full | full | baseline_4_isolation_forest | 0.506 | -0.185 | 0.256 | -0.338 | 3.67 | 5.0 |
| weather_permutation_full | full | challenger_hybrid_ensemble | 0.585 | -0.212 | 0.557 | -0.264 | 1.35 | 3.0 |
