# RAI Evaluation Summary

Computed: `2026-09-12T08:10:58.216806+00:00`

This report is generated from the local synthetic simulator. It is not a claim of real-world performance.

## Expected-behaviour models

| Model | MAE | RMSE | R² | Test rows |
|---|---:|---:|---:|---:|
| `wind_power` | 11.647244183070864 | 16.616053579639896 | 0.9992263449284952 | 11426 |
| `wind_gearbox_temp` | 0.907850991740207 | 1.200799828944683 | 0.9887971545668344 | 11418 |
| `wind_generator_temp` | 1.4216524793815113 | 1.8516603739965538 | 0.9900034879376018 | 11415 |
| `wind_bearing_temp` | 0.6445798034024829 | 0.8949787146867155 | 0.9883721543096803 | 11415 |
| `wind_vibration` | 0.11574830983570811 | 0.14665984009522445 | 0.9505847976264487 | 11426 |
| `solar_power` | 1.91028425997048 | 3.325146955029172 | 0.997992468688887 | 8997 |
| `solar_dc_power` | 2.0319589220914605 | 3.8347266563375286 | 0.9973844068560208 | 8997 |
| `solar_inverter_temp` | 0.6332064858008964 | 0.819891686185562 | 0.9837681188327625 | 8995 |

## Scenario discrimination

- Definition: scenario-level equipment-vs-non-equipment agreement against simulator flags
- Correct: `12/12`
- Agreement: `1.0`

See `results.json` for per-scenario evidence and provenance.
