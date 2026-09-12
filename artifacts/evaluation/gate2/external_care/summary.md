# External CARE benchmark - real results

| farm | model | CARE | coverage | earliness | reliability | accuracy | n datasets (anomaly/normal) |
|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 | 11/11 |
| Wind Farm A | zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 | 11/11 |

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
