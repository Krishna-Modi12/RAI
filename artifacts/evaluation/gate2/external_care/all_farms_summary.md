# External CARE benchmark - real results

| farm | model | CARE | coverage | earliness | reliability | accuracy | n datasets (anomaly/normal) |
|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 | 11/11 |
| Wind Farm A | zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 | 11/11 |
| Wind Farm B | isolation_forest | 0.532 | 0.236 | 0.079 | 0.556 | 0.896 | 6/9 |
| Wind Farm B | zscore_threshold | 0.401 | 0.008 | 0.002 | 0.000 | 0.999 | 6/9 |
| Wind Farm C | isolation_forest | 0.533 | 0.280 | 0.132 | 0.465 | 0.893 | 27/31 |
| Wind Farm C | zscore_threshold | 0.439 | 0.042 | 0.017 | 0.161 | 0.987 | 27/31 |

## Wind Farm A / isolation_forest - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 68 | anomaly_event | Transformer failure | 0.300 | 0.049 | 45 | False |
| 22 | anomaly_event | Hydraulic group | 0.588 | 0.283 | 5 | False |
| 72 | anomaly_event | Gearbox failure | 0.309 | 0.059 | 5 | False |
| 73 | anomaly_event | Hydraulic group | 0.253 | 0.057 | 8 | False |
| 0 | anomaly_event | Generator bearing failure | 0.376 | 0.136 | 2 | False |
| 26 | anomaly_event | Hydraulic group | 0.263 | 0.075 | 8 | False |
| 40 | anomaly_event | Generator bearing failure | 0.273 | 0.076 | 13 | False |
| 42 | anomaly_event | Hydraulic group | 0.108 | 0.028 | 2 | False |
| 10 | anomaly_event | Gearbox failure | 0.304 | 0.072 | 0 | False |
| 45 | anomaly_event | Hydraulic group | 1.000 | 0.529 | 406 | True |
| 84 | anomaly_event | Hydraulic group | 1.000 | 0.012 | 8 | False |
| 25 | normal_behavior |  | n/a | n/a | 1 | False |
| 69 | normal_behavior |  | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | n/a | n/a | 1 | False |
| 17 | normal_behavior |  | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | n/a | n/a | 1 | False |
| 92 | normal_behavior |  | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | n/a | n/a | 7 | False |

## Wind Farm A / zscore_threshold - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 68 | anomaly_event | Transformer failure | 0.000 | 0.000 | 0 | False |
| 22 | anomaly_event | Hydraulic group | 0.005 | 0.001 | 0 | False |
| 72 | anomaly_event | Gearbox failure | 0.000 | 0.000 | 0 | False |
| 73 | anomaly_event | Hydraulic group | 0.000 | 0.000 | 0 | False |
| 0 | anomaly_event | Generator bearing failure | 0.000 | 0.000 | 0 | False |
| 26 | anomaly_event | Hydraulic group | 0.000 | 0.000 | 0 | False |
| 40 | anomaly_event | Generator bearing failure | 0.000 | 0.000 | 0 | False |
| 42 | anomaly_event | Hydraulic group | 0.000 | 0.000 | 0 | False |
| 10 | anomaly_event | Gearbox failure | 0.000 | 0.000 | 0 | False |
| 45 | anomaly_event | Hydraulic group | 1.000 | 0.292 | 143 | True |
| 84 | anomaly_event | Hydraulic group | 1.000 | 0.000 | 0 | False |
| 25 | normal_behavior |  | n/a | n/a | 0 | False |
| 69 | normal_behavior |  | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | n/a | n/a | 0 | False |
| 17 | normal_behavior |  | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | n/a | n/a | 0 | False |
| 92 | normal_behavior |  | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | n/a | n/a | 0 | False |

## Wind Farm B / isolation_forest - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 34 | anomaly_event | high temperature | 0.145 | 0.045 | 13 | False |
| 7 | anomaly_event | high temperature | 0.092 | 0.027 | 12 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | 0.487 | 0.198 | 111 | True |
| 27 | anomaly_event | Turbine is stopped due to a main bearing damage | 0.260 | 0.084 | 83 | True |
| 19 | anomaly_event | high temperature | 0.132 | 0.036 | 11 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due to rotorbearing damage. | 0.298 | 0.083 | 6 | False |
| 83 | normal_behavior |  | n/a | n/a | 41 | False |
| 52 | normal_behavior |  | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | n/a | n/a | 109 | True |
| 87 | normal_behavior |  | n/a | n/a | 18 | False |
| 74 | normal_behavior |  | n/a | n/a | 6 | False |
| 86 | normal_behavior |  | n/a | n/a | 4 | False |
| 82 | normal_behavior |  | n/a | n/a | 1 | False |

## Wind Farm B / zscore_threshold - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 34 | anomaly_event | high temperature | 0.000 | 0.000 | 0 | False |
| 7 | anomaly_event | high temperature | 0.000 | 0.000 | 0 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | 0.038 | 0.010 | 2 | False |
| 27 | anomaly_event | Turbine is stopped due to a main bearing damage | 0.000 | 0.000 | 0 | False |
| 19 | anomaly_event | high temperature | 0.003 | 0.001 | 0 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due to rotorbearing damage. | 0.004 | 0.001 | 0 | False |
| 83 | normal_behavior |  | n/a | n/a | 0 | False |
| 52 | normal_behavior |  | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | n/a | n/a | 0 | False |
| 87 | normal_behavior |  | n/a | n/a | 0 | False |
| 74 | normal_behavior |  | n/a | n/a | 0 | False |
| 86 | normal_behavior |  | n/a | n/a | 0 | False |
| 82 | normal_behavior |  | n/a | n/a | 0 | False |

## Wind Farm C / isolation_forest - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20_HUB: Wiring blade control system | 0.350 | 0.147 | 12 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18.11. 13:57, Fuse Filter Supply  | 0.439 | 0.239 | 8 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic problemes - Hydraulic pump A disabeld, 2h later turbine back in production - Data shows anomaly in temp_hydraulic_oil_tank_1_average until 15.01.2023 | 0.066 | 0.057 | 15 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + Oil Leakage Gear Oil Supply + 12019: Rotor brake B cannot be closed + P20_yaw carbon brush damaged | 0.273 | 0.073 | 20 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | 0.228 | 0.057 | 19 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Versorgung Rotorbremse) on the 16th in the afternoon. From 17th onwards a longer standstill where we don't know the root cause to.  | 0.299 | 0.054 | 14 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Accumulators_hydraulic system | 0.208 | 0.045 | 20 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005 : Gear oil cooler bypass valve | 0.017 | 0.036 | 13 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis 2, rectified on 23/01 - Anomalie liegt aber länger an als der Fehler, Batterien waren ok | 0.178 | 0.213 | 62 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch resulting in a longer standstill due to a defect pitch encoder (26/02) | 0.596 | 0.211 | 3 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cover-lightning-main-cabinet-hub | 0.179 | 0.069 | 11 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | 0.000 | 0.000 | 5 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch motor | 0.263 | 0.173 | 221 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | 0.676 | 0.317 | 77 | True |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 : P20_Blades_Cabinet Caps missing | 0.838 | 0.493 | 220 | True |
| 44 | anomaly_event | Valve in water cooling system was left in wrong position after maintenance actions on 05-08-2020 | 0.198 | 0.050 | 17 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective coupling between gear oil pump and motor | 0.414 | 0.195 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ring and Beckhoff card | 0.076 | 0.064 | 26 | False |
| 67 | anomaly_event | Turbine has some issues with overpressure on the main transformer | 0.320 | 0.092 | 39 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | 0.218 | 0.067 | 10 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | 0.187 | 0.055 | 14 | False |
| 5 | anomaly_event | WEC in failure - current measurement own consumption | 0.198 | 0.221 | 56 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | 0.126 | 0.039 | 37 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | 0.252 | 0.074 | 12 | False |
| 35 | anomaly_event | Turbine had several short standstills (max 8min) with failure "Schwingungen Umrichter Drehmomenten Level 1" | 0.259 | 0.073 | 2 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger defect | 0.336 | 0.072 | 102 | True |
| 76 | anomaly_event | WEC in failure with pitch battery issues - rewiring | 0.363 | 0.377 | 45 | False |
| 8 | normal_behavior |  | n/a | n/a | 3 | False |
| 85 | normal_behavior |  | n/a | n/a | 4 | False |
| 6 | normal_behavior |  | n/a | n/a | 2 | False |
| 62 | normal_behavior |  | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | n/a | n/a | 4 | False |
| 56 | normal_behavior |  | n/a | n/a | 10 | False |
| 94 | normal_behavior |  | n/a | n/a | 2 | False |
| 54 | normal_behavior |  | n/a | n/a | 44 | False |
| 43 | normal_behavior |  | n/a | n/a | 4 | False |
| 50 | normal_behavior |  | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | n/a | n/a | 8 | False |
| 46 | normal_behavior |  | n/a | n/a | 1 | False |
| 65 | normal_behavior |  | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | n/a | n/a | 2 | False |
| 93 | normal_behavior |  | n/a | n/a | 36 | False |
| 75 | normal_behavior |  | n/a | n/a | 8 | False |
| 41 | normal_behavior |  | n/a | n/a | 11 | False |
| 58 | normal_behavior |  | n/a | n/a | 2 | False |
| 48 | normal_behavior |  | n/a | n/a | 8 | False |
| 88 | normal_behavior |  | n/a | n/a | 23 | False |
| 57 | normal_behavior |  | n/a | n/a | 7 | False |
| 32 | normal_behavior |  | n/a | n/a | 2 | False |
| 89 | normal_behavior |  | n/a | n/a | 5 | False |
| 59 | normal_behavior |  | n/a | n/a | 1 | False |
| 63 | normal_behavior |  | n/a | n/a | 7 | False |
| 80 | normal_behavior |  | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | n/a | n/a | 3 | False |
| 20 | normal_behavior |  | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | n/a | n/a | 54 | False |

## Wind Farm C / zscore_threshold - per-dataset detail

| event_id | label | description | coverage | earliness | max criticality | detected |
|---|---|---|---|---|---|---|
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20_HUB: Wiring blade control system | 0.066 | 0.019 | 1 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18.11. 13:57, Fuse Filter Supply  | 0.604 | 0.173 | 2 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic problemes - Hydraulic pump A disabeld, 2h later turbine back in production - Data shows anomaly in temp_hydraulic_oil_tank_1_average until 15.01.2023 | 0.000 | 0.000 | 0 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + Oil Leakage Gear Oil Supply + 12019: Rotor brake B cannot be closed + P20_yaw carbon brush damaged | 0.000 | 0.000 | 0 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | 0.000 | 0.000 | 0 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Versorgung Rotorbremse) on the 16th in the afternoon. From 17th onwards a longer standstill where we don't know the root cause to.  | 0.000 | 0.001 | 3 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Accumulators_hydraulic system | 0.000 | 0.000 | 0 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005 : Gear oil cooler bypass valve | 0.000 | 0.007 | 4 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis 2, rectified on 23/01 - Anomalie liegt aber länger an als der Fehler, Batterien waren ok | 0.000 | 0.000 | 0 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch resulting in a longer standstill due to a defect pitch encoder (26/02) | 0.000 | 0.000 | 0 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cover-lightning-main-cabinet-hub | 0.000 | 0.000 | 0 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | 0.000 | 0.000 | 0 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch motor | 0.000 | 0.052 | 144 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | 0.171 | 0.035 | 3 | False |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 : P20_Blades_Cabinet Caps missing | 0.242 | 0.052 | 23 | False |
| 44 | anomaly_event | Valve in water cooling system was left in wrong position after maintenance actions on 05-08-2020 | 0.000 | 0.000 | 0 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective coupling between gear oil pump and motor | 0.000 | 0.000 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ring and Beckhoff card | 0.000 | 0.016 | 9 | False |
| 67 | anomaly_event | Turbine has some issues with overpressure on the main transformer | 0.047 | 0.010 | 8 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | 0.000 | 0.000 | 0 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | 0.009 | 0.002 | 3 | False |
| 5 | anomaly_event | WEC in failure - current measurement own consumption | 0.000 | 0.062 | 22 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | 0.000 | 0.000 | 0 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | 0.000 | 0.000 | 0 | False |
| 35 | anomaly_event | Turbine had several short standstills (max 8min) with failure "Schwingungen Umrichter Drehmomenten Level 1" | 0.000 | 0.000 | 0 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger defect | 0.000 | 0.023 | 56 | False |
| 76 | anomaly_event | WEC in failure with pitch battery issues - rewiring | 0.000 | 0.000 | 16 | False |
| 8 | normal_behavior |  | n/a | n/a | 0 | False |
| 85 | normal_behavior |  | n/a | n/a | 0 | False |
| 6 | normal_behavior |  | n/a | n/a | 0 | False |
| 62 | normal_behavior |  | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | n/a | n/a | 0 | False |
| 56 | normal_behavior |  | n/a | n/a | 0 | False |
| 94 | normal_behavior |  | n/a | n/a | 0 | False |
| 54 | normal_behavior |  | n/a | n/a | 14 | False |
| 43 | normal_behavior |  | n/a | n/a | 0 | False |
| 50 | normal_behavior |  | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | n/a | n/a | 1 | False |
| 46 | normal_behavior |  | n/a | n/a | 0 | False |
| 65 | normal_behavior |  | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | n/a | n/a | 0 | False |
| 93 | normal_behavior |  | n/a | n/a | 7 | False |
| 75 | normal_behavior |  | n/a | n/a | 0 | False |
| 41 | normal_behavior |  | n/a | n/a | 1 | False |
| 58 | normal_behavior |  | n/a | n/a | 0 | False |
| 48 | normal_behavior |  | n/a | n/a | 0 | False |
| 88 | normal_behavior |  | n/a | n/a | 0 | False |
| 57 | normal_behavior |  | n/a | n/a | 0 | False |
| 32 | normal_behavior |  | n/a | n/a | 0 | False |
| 89 | normal_behavior |  | n/a | n/a | 4 | False |
| 59 | normal_behavior |  | n/a | n/a | 0 | False |
| 63 | normal_behavior |  | n/a | n/a | 0 | False |
| 80 | normal_behavior |  | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | n/a | n/a | 0 | False |
| 20 | normal_behavior |  | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | n/a | n/a | 30 | False |
