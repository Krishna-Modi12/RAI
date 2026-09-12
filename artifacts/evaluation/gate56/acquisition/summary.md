# Gate 5.6A -- Real PVDAQ Acquisition, Cohort Lock & Solar Evidence Expansion

## Data-readiness classification: **READY**

## 1. Did real PVDAQ access succeed?
Yes. Unauthenticated HTTPS GET against `oedi-data-lake.s3.amazonaws.com` succeeded on the
first attempt (HTTP 200 for the systems table). No API key or account was needed. See
`access_attempts.md` for the full first-mandatory-check log.

## 2. Exact files and checksums
450/450 real daily telemetry parquet files downloaded
(74,517,723 bytes total). Every file's SHA-256, size, HTTP status and retrieval
timestamp is recorded in `download_manifest.json` and `checksums.csv`. The systems
metadata table (`systems_20250729.csv`, 383,559 bytes) has
sha256=`54ddbd1ef044a7eb822ddf8bf3e53f319606598cc37b20d05c96b4631e03d65c`.

## 3. Exact systems selected and why
Development: [1239, 1283, 34] (Presque Isle ME, NREL RSF II Golden CO, Andre Agassi Bldg A Las Vegas NV).
Validation: [1430, 1433] (NREL Mesa 1-axis tracker Golden CO, NREL RSF1 Golden CO).
All 5 passed the predeclared readiness screen (real POA irradiance + real AC power + real
temperature + known site metadata) before any telemetry was downloaded. See
`cohort_manifest.json` for the exact rule order applied and `candidate_systems.json` for
the full 9-candidate screening record (5 selected, 4 excluded).

## 4. Are development and validation systems disjoint?
Yes. Intersection of development and validation system IDs is empty: [].

## 5. What signals are available / unavailable per system?
See `candidate_systems.json` (`has_irradiance_poa`, `has_ac_power`, `has_dc_power`,
`has_ambient_temp`, `has_module_temp`, `has_cumulative_energy_field` per candidate) and
`timestamp_quality.csv` for per-signal record counts and sampling intervals actually
observed in the downloaded files.

## 6. Data-quality issues found in the real data
Per-system raw physical-sanity audit counts (flagged, NOT removed -- filtering is a Gate
5.6B decision) are in `quality_filter_manifest.json`. Two real-data findings worth calling
out explicitly:
- Systems 1430/1433's systems-table metadata claims coverage through 2024, but their real
  S3 `pvdata` parquet partitions stop at 2017 and 2018 respectively -- a genuine archive
  metadata/data inconsistency, documented in `cohort_manifest.json` and
  `access_attempts.md` and corrected by re-verifying an actually-present window (2017)
  before downloading, rather than by inferring or fabricating 2019 data for them.
- Different metrics for the same system are recorded at different native sampling
  intervals within the same file (e.g. system 1239's module-temperature channel at ~60min
  vs. its metered-AC-power channel at ~15min) -- see `timestamp_quality.csv`
  `modal_interval_minutes` per signal. This must be handled explicitly (per-metric
  pivot/resample) in Gate 5.6B; it is documented here, not silently harmonized.
- **Both validation systems (1430, 1433) have a null `utc_measured_on` field for
  100% of every metric across the entire acquired window** (their local `measured_on`
  timestamps ARE populated; the declared local timezone for both is `America/Denver`,
  per `systems_20250729.csv`). Confirmed as a real archive defect (not a loader bug) by
  reading a single raw parquet file directly. `timestamp_quality.csv` audits these two
  systems using `measured_on` (local time, explicitly labeled
  `timestamp_basis_used=measured_on`) as a documented fallback rather than silently
  reconstructing UTC. The AC-power nighttime-value sanity check was explicitly SKIPPED
  (not silently zeroed) for both systems -- see `night_check_skipped_reason` in
  `quality_filter_manifest.json`. Gate 5.6B must decide how to obtain real UTC alignment
  for these two systems (e.g. localizing `measured_on` to `America/Denver` and
  converting, with that transformation explicitly documented) before running any
  irradiance-dependent model against them.
- System 1283 exposes four AC-power-classified channels in the real data
  (`ac_power_metered_kW`=1040, `ac_meter_2_power_kW`=1042, `inv1_ac_power_kW`=1043,
  `inv2_ac_power_kW`=1047); the plant-level `ac_power`/`ac_meter_1_power_kW` channels
  cataloged in its metrics dictionary are NOT present in the actual downloaded 2019
  telemetry at all. Of the channels that ARE present, the metered-first candidate
  (`ac_power_metered_kW`) has 39.5% negative readings (min -900) over the window, while
  `inv1_ac_power_kW` is constant zero throughout. See
  `quality_filter_manifest.json` -> `real_data_audit_findings.per_system.1283` for the full
  counts and the other present-channel list. This is flagged, not resolved -- Gate 5.6B
  must explicitly choose and justify which channel is the true plant AC output.

## 7. Is the acquired data independent of the future model implementation?
Yes. Every value in every downloaded file is real NREL PVDAQ sensor telemetry (long-format
`measured_on, utc_measured_on, metric_id, value` rows read directly from S3 parquet
objects). No RAI code, pvlib model, or synthetic generator produced any value in
`data/raw/pvdaq/`. The synthetic generator that caused the original Gate 5.6 circularity
failure has been relocated to `rai/eval/external/solar/synthetic_fixtures.py` and cannot
be imported from any module in the real-acquisition code path (`pvdaq.py`,
`scratch_gate56a/acquire.py`, or this builder) -- verified in
`tests/test_gate56a_data_authenticity.py`.

## 8. PVPMC resources reserved for later gates
Documented for provenance only in `pvpmc_followup_sources.json` -- the tracker-fault time
series, soiling, and degradation resources were NOT downloaded or evaluated in Gate 5.6A.

## 9. Was the prior invalid run touched?
No. `artifacts/evaluation/gate56_invalid_prior_run/` (GATE_5.6_INVALID_SYNTHETIC_RUN) was
not read from, written to, or used as a source of any value in this acquisition. All Gate
5.6A artifacts live under a separate `acquisition/` subdirectory.

## 10. Circularity check
`DATA_SOURCE != MODEL_GENERATOR` holds: no model of any kind (physics, empirical, or
hybrid) was run, fit, or scored during Gate 5.6A. See the ABSOLUTE STOP RULE compliance
note below.

## 11. Was any system chosen or discarded based on performance?
No. Every selection/exclusion decision in `candidate_systems.json` traces to a signal-
availability, metadata-completeness, redundancy, or file-integrity reason -- never to a
computed R², residual, or any other model output, because no model was run.

## ABSOLUTE STOP RULE compliance
No ModelChain run, no empirical model fit, no RAI Solar Champion, no threshold tuning, no
anomaly detection, no Gate 5.7, no Needle, no Qwen, and no RAG work was performed in this
task. This gate stops here pending the user's audit of the frozen cohort.