## Gate 5.1 – Multi-Farm CARE Benchmark

*Generated: 2026-09-12 12:29 UTC*

### Cross-Farm Summary

| Farm | Model | CARE | Coverage | Earliness | Reliability | Accuracy | N datasets (A/N) | Status |
|---|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 | 11/11 | PARTIAL |
| Wind Farm A | zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 | 11/11 | PARTIAL |
| Wind Farm B | isolation_forest | 0.532 | 0.236 | 0.079 | 0.556 | 0.896 | 6/9 | PARTIAL |
| Wind Farm B | zscore_threshold | 0.401 | 0.008 | 0.002 | 0.000 | 0.999 | 6/9 | PARTIAL |
| Wind Farm C | isolation_forest | 0.533 | 0.280 | 0.132 | 0.465 | 0.893 | 27/31 | PARTIAL |
| Wind Farm C | zscore_threshold | 0.439 | 0.042 | 0.017 | 0.161 | 0.987 | 27/31 | PARTIAL |

### Wind Farm A — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 68 | anomaly_event | Transformer failure | isolation_forest | 0.300 | 0.049 | 45 | False |
| 22 | anomaly_event | Hydraulic group | isolation_forest | 0.588 | 0.283 | 5 | False |
| 72 | anomaly_event | Gearbox failure | isolation_forest | 0.309 | 0.059 | 5 | False |
| 73 | anomaly_event | Hydraulic group | isolation_forest | 0.253 | 0.057 | 8 | False |
| 0 | anomaly_event | Generator bearing failure | isolation_forest | 0.376 | 0.136 | 2 | False |
| 26 | anomaly_event | Hydraulic group | isolation_forest | 0.263 | 0.075 | 8 | False |
| 40 | anomaly_event | Generator bearing failure | isolation_forest | 0.273 | 0.076 | 13 | False |
| 42 | anomaly_event | Hydraulic group | isolation_forest | 0.108 | 0.028 | 2 | False |
| 10 | anomaly_event | Gearbox failure | isolation_forest | 0.304 | 0.072 | 0 | False |
| 45 | anomaly_event | Hydraulic group | isolation_forest | 1.000 | 0.529 | 406 | True |
| 84 | anomaly_event | Hydraulic group | isolation_forest | 1.000 | 0.012 | 8 | False |
| 25 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 69 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 17 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 92 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 68 | anomaly_event | Transformer failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 22 | anomaly_event | Hydraulic group | zscore_threshold | 0.005 | 0.001 | 0 | False |
| 72 | anomaly_event | Gearbox failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 73 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 0 | anomaly_event | Generator bearing failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 26 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 40 | anomaly_event | Generator bearing failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 42 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 10 | anomaly_event | Gearbox failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 45 | anomaly_event | Hydraulic group | zscore_threshold | 1.000 | 0.292 | 143 | True |
| 84 | anomaly_event | Hydraulic group | zscore_threshold | 1.000 | 0.000 | 0 | False |
| 25 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 69 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 17 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 92 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |

### Wind Farm B — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 34 | anomaly_event | high temperature | isolation_forest | 0.145 | 0.045 | 13 | False |
| 7 | anomaly_event | high temperature | isolation_forest | 0.092 | 0.027 | 12 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | isolation_forest | 0.487 | 0.198 | 111 | True |
| 27 | anomaly_event | Turbine is stopped due to a main bearing | isolation_forest | 0.260 | 0.084 | 83 | True |
| 19 | anomaly_event | high temperature | isolation_forest | 0.132 | 0.036 | 11 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due | isolation_forest | 0.298 | 0.083 | 6 | False |
| 83 | normal_behavior |  | isolation_forest | n/a | n/a | 41 | False |
| 52 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | isolation_forest | n/a | n/a | 109 | True |
| 87 | normal_behavior |  | isolation_forest | n/a | n/a | 18 | False |
| 74 | normal_behavior |  | isolation_forest | n/a | n/a | 6 | False |
| 86 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 82 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 34 | anomaly_event | high temperature | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 7 | anomaly_event | high temperature | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | zscore_threshold | 0.038 | 0.010 | 2 | False |
| 27 | anomaly_event | Turbine is stopped due to a main bearing | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 19 | anomaly_event | high temperature | zscore_threshold | 0.003 | 0.001 | 0 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due | zscore_threshold | 0.004 | 0.001 | 0 | False |
| 83 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 52 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 87 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 74 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 86 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 82 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |

### Wind Farm C — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20 | isolation_forest | 0.350 | 0.147 | 12 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18. | isolation_forest | 0.439 | 0.239 | 8 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic  | isolation_forest | 0.066 | 0.057 | 15 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + | isolation_forest | 0.273 | 0.073 | 20 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | isolation_forest | 0.228 | 0.057 | 19 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Vers | isolation_forest | 0.299 | 0.054 | 14 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Acc | isolation_forest | 0.208 | 0.045 | 20 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005  | isolation_forest | 0.017 | 0.036 | 13 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis | isolation_forest | 0.178 | 0.213 | 62 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch r | isolation_forest | 0.596 | 0.211 | 3 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cove | isolation_forest | 0.179 | 0.069 | 11 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | isolation_forest | 0.000 | 0.000 | 5 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch moto | isolation_forest | 0.263 | 0.173 | 221 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | isolation_forest | 0.676 | 0.317 | 77 | True |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 | isolation_forest | 0.838 | 0.493 | 220 | True |
| 44 | anomaly_event | Valve in water cooling system was left i | isolation_forest | 0.198 | 0.050 | 17 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective cou | isolation_forest | 0.414 | 0.195 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ri | isolation_forest | 0.076 | 0.064 | 26 | False |
| 67 | anomaly_event | Turbine has some issues with overpressur | isolation_forest | 0.320 | 0.092 | 39 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | isolation_forest | 0.218 | 0.067 | 10 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | isolation_forest | 0.187 | 0.055 | 14 | False |
| 5 | anomaly_event | WEC in failure - current measurement own | isolation_forest | 0.198 | 0.221 | 56 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | isolation_forest | 0.126 | 0.039 | 37 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | isolation_forest | 0.252 | 0.074 | 12 | False |
| 35 | anomaly_event | Turbine had several short standstills (m | isolation_forest | 0.259 | 0.073 | 2 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger def | isolation_forest | 0.336 | 0.072 | 102 | True |
| 76 | anomaly_event | WEC in failure with pitch battery issues | isolation_forest | 0.363 | 0.377 | 45 | False |
| 8 | normal_behavior |  | isolation_forest | n/a | n/a | 3 | False |
| 85 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 6 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 62 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 56 | normal_behavior |  | isolation_forest | n/a | n/a | 10 | False |
| 94 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 54 | normal_behavior |  | isolation_forest | n/a | n/a | 44 | False |
| 43 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 50 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 46 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 65 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 93 | normal_behavior |  | isolation_forest | n/a | n/a | 36 | False |
| 75 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 41 | normal_behavior |  | isolation_forest | n/a | n/a | 11 | False |
| 58 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 48 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 88 | normal_behavior |  | isolation_forest | n/a | n/a | 23 | False |
| 57 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 32 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 89 | normal_behavior |  | isolation_forest | n/a | n/a | 5 | False |
| 59 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 63 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 80 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | isolation_forest | n/a | n/a | 3 | False |
| 20 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | isolation_forest | n/a | n/a | 54 | False |
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20 | zscore_threshold | 0.066 | 0.019 | 1 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18. | zscore_threshold | 0.604 | 0.173 | 2 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic  | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Vers | zscore_threshold | 0.000 | 0.001 | 3 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Acc | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005  | zscore_threshold | 0.000 | 0.007 | 4 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch r | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cove | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch moto | zscore_threshold | 0.000 | 0.052 | 144 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | zscore_threshold | 0.171 | 0.035 | 3 | False |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 | zscore_threshold | 0.242 | 0.052 | 23 | False |
| 44 | anomaly_event | Valve in water cooling system was left i | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective cou | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ri | zscore_threshold | 0.000 | 0.016 | 9 | False |
| 67 | anomaly_event | Turbine has some issues with overpressur | zscore_threshold | 0.047 | 0.010 | 8 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | zscore_threshold | 0.009 | 0.002 | 3 | False |
| 5 | anomaly_event | WEC in failure - current measurement own | zscore_threshold | 0.000 | 0.062 | 22 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 35 | anomaly_event | Turbine had several short standstills (m | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger def | zscore_threshold | 0.000 | 0.023 | 56 | False |
| 76 | anomaly_event | WEC in failure with pitch battery issues | zscore_threshold | 0.000 | 0.000 | 16 | False |
| 8 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 85 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 6 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 62 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 56 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 94 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 54 | normal_behavior |  | zscore_threshold | n/a | n/a | 14 | False |
| 43 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 50 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 46 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 65 | normal_behavior |  | zscore_threshold | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 93 | normal_behavior |  | zscore_threshold | n/a | n/a | 7 | False |
| 75 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 41 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 58 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 48 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 88 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 57 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 32 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 89 | normal_behavior |  | zscore_threshold | n/a | n/a | 4 | False |
| 59 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 63 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 80 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | zscore_threshold | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 20 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | zscore_threshold | n/a | n/a | 30 | False |

### Status Legend

| Status | Criterion |
|---|---|
| PASS | CARE ≥ 0.55 for both models |
| PARTIAL | ≥ 1 model CARE ≥ 0.45, no null |
| INSUFFICIENT_DATA | < 5 datasets or no anomaly events |
| UNRESOLVED | Score obtained but does not meet PARTIAL |

---
