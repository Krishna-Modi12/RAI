# Kelmarsh event / behaviour benchmark

**Experiment:** `RAI-WIND-002`  
**Status:** `PARTIAL`  
**Claim level:** `EXTERNAL_REAL` + `MODEL_COMPARISON` + `HISTORICAL_AUDIT`

## Decision

The 2019 Kelmarsh release is usable for an operational event-association experiment,
not failure validation. The official Zenodo record identifies six Senvion MM92
turbines, 10-minute SCADA, and Greenbyte status/event records. Status rows have
useful IEC categories, but the dataset does not independently establish that each
row is a confirmed component failure.

The experiment therefore evaluates only `Forced outage` and `Scheduled Maintenance`
windows. `Out of Environmental Specification`, `Out of Electrical Specification`,
`Technical Standby`, communication records, and uncategorised rows are excluded from
the event score. The result means “anomaly behaviour was associated with an
operational event window”, never “RAI predicted a failure”.

## Audit

- Pinned source: Zenodo `10.5281/zenodo.5841834`, file
  `Kelmarsh_SCADA_2019_3085.zip`.
- Archive SHA-256:
  `c2f11578b9a1678be198fd7883a7dfe1b923c5b0565f806bdda5dd9d0097f4dc`.
- Six turbines, 2019, 10-minute SCADA; 299 source columns available.
- Minimum feature policy: wind speed (m/s), active power (kW), rotor speed (RPM).
  Only numeric coercion and missing-value imputation fit on the training interval
  were used.
- Chronological split: first 60% per turbine for fitting, final 40% for evaluation.
- Event windows: six hours before, documented event interval, and six hours after.
- No event category, message, code, timestamp-derived label, turbine identity, or
  future statistic enters model features.
- Rolling/persistence features do not cross the train/test boundary; this benchmark
  uses the existing RAI persistence implementation over the prediction frame.

## Event inventory

Across all six status files, the evaluated classes contain 146 forced-outage rows
and 64 scheduled-maintenance rows. The evaluated test-period windows contain 92
events: 71 forced outages and 21 scheduled-maintenance windows. These are operational
event records, not component-failure labels.

## Results

Event coverage means the fraction of the 92 evaluated event windows containing at
least one anomaly flag. False-alarm rate is the fraction of test timestamps outside
the six-hour event masks that were flagged. These are association diagnostics, not
classification metrics.

| Model | Event windows detected | Event coverage | Outside-window flag rate | Mean pre-event flag rate | Mean event flag rate | Mean post-event flag rate |
|---|---:|---:|---:|---:|---:|---:|
| Statistical z-score | 1/92 | 1.1% | 0.46% | 0.21% | 1.23% | 1.03% |
| Isolation Forest | 44/92 | 47.8% | 0.32% | 6.25% | 42.95% | 4.95% |
| RAI Champion | 75/92 | 81.5% | 1.11% | 12.71% | 81.68% | 22.83% |

The RAI Champion shows stronger event-window association than the two minimal
baselines in this release, while also producing a higher outside-window flag rate.
That is a trade-off, not proof of superior fault detection. The pre/event/post
contrast is temporal association only and cannot establish causation.

## Artifacts

- `artifacts/evaluation/kelmarsh_event_behaviour/reproducibility_manifest.json`
- `artifacts/evaluation/kelmarsh_event_behaviour/event_windows.csv`
- `artifacts/evaluation/kelmarsh_event_behaviour/model_results.csv`
- `artifacts/evaluation/kelmarsh_event_behaviour/leakage_feature_audit.json`
- `artifacts/evaluation/kelmarsh_event_behaviour/summary.json`

The benchmark is intentionally not scored with CARE: Kelmarsh event semantics do
not match CARE's labelled anomaly-sequence contract.

## Limitations and stop boundary

This is one pinned year and one site, with operational event records rather than
independently adjudicated component failures. Events can be repeated, administrative,
or driven by causes not represented in the selected three signals. The benchmark
must not be promoted to failure validation, universal generalization, production
validation, or causal diagnosis.
