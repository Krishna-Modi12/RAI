# Cross-farm transfer (fit on source, score on target, never refit)

| model | source -> target | feature intersection | n datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy | status |
|---|---|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.600 | 0.665 | 0.374 | 0.714 | 0.623 | COMPUTED |
| zscore_threshold | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.430 | 0.185 | 0.057 | 0.000 | 0.953 | COMPUTED |
| isolation_forest | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | 27/31 | 0.601 | 0.487 | 0.379 | 0.794 | 0.672 | COMPUTED |
| zscore_threshold | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | 27/31 | 0.484 | 0.061 | 0.035 | 0.385 | 0.970 | COMPUTED |