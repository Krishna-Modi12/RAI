# Cross-farm transfer (fit on source, score on target, never refit)

| model | source -> target | feature intersection | n datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy | status |
|---|---|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.600 | 0.665 | 0.374 | 0.714 | 0.623 | COMPUTED |
| zscore_threshold | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.430 | 0.185 | 0.057 | 0.000 | 0.953 | COMPUTED |