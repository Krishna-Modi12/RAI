# Gate 5.6C -- Solar Expected-Performance Model Development

**Status: `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED`.**

This gate builds a real `pvlib.modelchain.ModelChain` physics reference, an empirical
baseline, and a hybrid champion model against the REAL, Gate 5.6B-adjudicated PVDAQ
Development cohort (systems 1239, 1283, 34). Per the Gate 5.6C decision gate
(`../gate56c_decision_gate/decision.md`, PATH B), no real component-failure event
labels exist for this cohort or any integrable alternative -- so every metric below is
an **internal self-consistency diagnostic** (does the model reproduce held-out real
telemetry from the SAME system it was fit on), never a validated-accuracy or
generalization claim. Systems 1430 and 1433 are excluded as
`PARAMETERIZATION_INSUFFICIENT` (no real tracker geometry / no CEC module match
respectively) -- no parameters were invented to force a model for either.

## What changed vs. the invalidated prior run

- Physics reference is a REAL `pvlib.pvsystem.PVSystem` + `pvlib.modelchain.ModelChain`
  (`rai/eval/external/solar/pvlib_modelchain_reference.py`), using only real CEC
  module/inverter database matches, real tilt/azimuth, and real inverter-quantity /
  module-count metadata -- not the hand-rolled formula that caused
  `GATE_5.6_INVALID_SYNTHETIC_RUN`.
- All telemetry is the real, checksummed Gate 5.6A PVDAQ acquisition -- no synthetic
  data anywhere in this code path (enforced by a circularity tripwire test).
- Holdout is temporal-within-system (60/20/20 per system with purge gaps), never
  cross-system, and never described as generalization.

## Per-system results

### System 1239

- Split sizes (records): {'train': 5187, 'val': 1729, 'test': 1721}
- Quality filter result: {'total_records': 8645, 'valid_daytime_count': 4892, 'nighttime_filtered_count': 3675, 'clipping_tagged_count': 23, 'curtailed_tagged_count': 0, 'data_gap_count': 78, 'sensor_anomaly_count': 0, 'valid_daytime_pct': 56.59}
- Champion hybrid blend weight (alpha on physics): 0.1
- Calibrated normal-operation residual: mean=-0.0219 kW, std=0.485 kW

### System 1283

- Split sizes (records): {'train': 302630, 'val': 100876, 'test': 100870}
- Quality filter result: {'total_records': 504384, 'valid_daytime_count': 274729, 'nighttime_filtered_count': 229655, 'clipping_tagged_count': 1568, 'curtailed_tagged_count': 0, 'data_gap_count': 0, 'sensor_anomaly_count': 0, 'valid_daytime_pct': 54.47}
- Champion hybrid blend weight (alpha on physics): 0.1
- Calibrated normal-operation residual: mean=-0.0514 kW, std=12.76 kW

### System 34

- Split sizes (records): {'train': 5184, 'val': 1728, 'test': 1720}
- Quality filter result: {'total_records': 8640, 'valid_daytime_count': 4154, 'nighttime_filtered_count': 2242, 'clipping_tagged_count': 0, 'curtailed_tagged_count': 0, 'data_gap_count': 2244, 'sensor_anomaly_count': 0, 'valid_daytime_pct': 48.08}
- Champion hybrid blend weight (alpha on physics): 0.29677054000168285
- Calibrated normal-operation residual: mean=-3.4933 kW, std=7.6382 kW

## Self-consistency diagnostics (test split, internal only)

| System | Model | n | R2 | RMSE (kW) | nRMSE (% of rated) | MAE (kW) |
|---|---|---|---|---|---|---|
| 1239 | PVLIB_MODELCHAIN_PHYSICS_REFERENCE | 900 | 0.9768 | 0.7694 | 3.8163 | 0.5745 |
| 1239 | SOLAR_EMPIRICAL_BASELINE | 900 | 0.9852 | 0.6135 | 3.0429 | 0.4517 |
| 1239 | RAI_SOLAR_CHAMPION_HYBRID | 900 | 0.9858 | 0.6015 | 2.9836 | 0.44 |
| 1283 | PVLIB_MODELCHAIN_PHYSICS_REFERENCE | 51992 | 0.9695 | 19.4917 | 4.7746 | 14.7084 |
| 1283 | SOLAR_EMPIRICAL_BASELINE | 51992 | 0.9827 | 14.6658 | 3.5924 | 10.9866 |
| 1283 | RAI_SOLAR_CHAMPION_HYBRID | 51992 | 0.9824 | 14.804 | 3.6263 | 11.0401 |
| 34 | PVLIB_MODELCHAIN_PHYSICS_REFERENCE | 782 | 0.7001 | 14.9926 | 10.2241 | 14.356 |
| 34 | SOLAR_EMPIRICAL_BASELINE | 782 | 0.9743 | 4.3885 | 2.9927 | 2.8543 |
| 34 | RAI_SOLAR_CHAMPION_HYBRID | 782 | 0.9461 | 6.3557 | 4.3342 | 5.2372 |

All figures above are `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED` internal
self-consistency diagnostics -- see `provenance_manifest.json`'s
`diagnostic_metric_disclaimer` for the exact scope and limits of this claim.

## Limitations

- No real component-failure event labels exist for this cohort (Gate 5.6C decision
  gate finding) -- these models cannot be validated against real fault ground truth.
- AOI and spectral-mismatch corrections are not modeled (`aoi_model='no_loss'`,
  `spectral_model='no_loss'`): real PVDAQ POA sensors report only broadband global
  irradiance, not decomposed direct/diffuse components `run_model_from_poa` requires,
  so `run_model_from_effective_irradiance` is used instead -- a disclosed simplification.
- Series/parallel wiring split (modules_per_string=1) is a disclosed, power-invariant
  simplification: real metadata gives only total module count and real inverter count,
  not the exact per-inverter string layout.
- System 1239's temperature model uses a disclosed wind_speed=1.0 m/s standard
  assumption (`faiman`) because its real wind channel is degenerate (Gate 5.6B finding).

## STOP RULE compliance

This gate fit and ran real models against real, adjudicated telemetry. It did NOT
claim validated accuracy, generalization, or cite any real fault-event ground truth.
No Gate 5.7, Needle, Qwen, or RAG work was started here.