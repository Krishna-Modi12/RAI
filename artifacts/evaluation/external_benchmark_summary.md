# Track B: External SCADA Reality & Generalization Benchmark

**Status:** EXECUTED  
**Timestamp:** 2026-09-12T10:29:07.083232+00:00  
**External Files Evaluated:** 1  
**Total SCADA Hours Monitored:** 240.0 hours  

## Zero-Shot Cross-Turbine Generalization Summary

| Metric | Measured Value | Threshold | Status |
|---|---:|---:|---|
| **Mean Power Curve $R^2$ (Zero-Shot)** | **0.9943** | $\ge 0.85$ | PASS |
| **Annualized False Alarm Rate** | **0.00/yr** | $\le 5.0$/yr | PASS |
| **Zero-Shot Physics Transfer** | **VERIFIED** | Validated | CONFIRMED |

## Evaluated External Files

### `external_turbine_sample.csv`
- **Monitored Hours:** 240.0 h (1440 intervals of 10-min SCADA)
- **Resolved Signals:** 5 canonical signals mapped
- **Power Model Zero-Shot:** $R^2 = 0.9943$, RMSE = 57.68 kW (2.78%)
- **Bearing Thermal Model:** Mean Residual = N/A°C, Max = N/A°C
- **Detection Lead Time:** 0.0 days (Degradation confirmed: False)
- **False Alarms in Normal Period:** 0 (0.0/asset-year)
