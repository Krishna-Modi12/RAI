---
task: gate56a-pvdaq-real-acquisition
phase: 5
status: complete
---

## What was built

- Real acquisition of NREL PVDAQ telemetry from the public OEDI S3 data lake
  (`oedi-data-lake.s3.amazonaws.com`, unauthenticated HTTPS, no API key), replacing the
  in-repo synthetic generator that caused the `GATE_5.6_INVALID_SYNTHETIC_RUN` failure
  (see retraction banner on `docs/checkpoints/14-solar-expected-performance.md` and
  `artifacts/evaluation/gate56_invalid_prior_run/invalidation_manifest.json`).
- Downloaded 450/450 real daily telemetry parquet files (74,517,723 bytes) plus the systems
  metadata table, every file checksummed (SHA-256) and logged in `download_manifest.json` /
  `checksums.csv`.
- Screened 9 candidate systems against a predeclared readiness rule (real POA irradiance +
  real AC power + real temperature + known site metadata) *before* downloading any
  telemetry; selected 5, excluded 4. Locked Development=[1239, 1283, 34], candidate
  Validation=[1430, 1433], disjoint by construction.
- Relocated the synthetic telemetry generator to
  `rai/eval/external/solar/synthetic_fixtures.py` under names that make its synthetic
  nature unmistakable, and added `tests/test_gate56a_data_authenticity.py` to assert the
  real-acquisition code path never imports it.
- Flagged (not resolved) three real data-quality defects for Gate 5.6B to adjudicate: null
  `utc_measured_on` for 100% of records on systems 1430/1433, heterogeneous per-signal
  sampling intervals within the same system, and system 1283 exposing four AC-power
  candidate channels with no plant-level channel present in the real 2019 telemetry.

## Files

- `scratch_gate56a/acquire.py` — real S3 acquisition script.
- `rai/eval/external/solar/pvdaq.py` — quarantine notice added; synthetic generator removed.
- `rai/eval/external/solar/synthetic_fixtures.py` — relocated synthetic generator, clearly labeled.
- `data/raw/pvdaq/` — 450 real downloaded parquet files.
- `artifacts/evaluation/gate56/acquisition/*` — 10 manifests + `summary.md`.
- `tests/test_gate56a_pvdaq_acquisition.py`, `tests/test_gate56a_data_authenticity.py`.

## How it was verified

`pytest tests/test_gate56a_pvdaq_acquisition.py tests/test_gate56a_data_authenticity.py -v`
passed; full `pytest -q` passed; `ruff check .` clean. Real HTTP 200 response and SHA-256
checksums recorded per file in `checksums.csv`, not asserted from memory.

## Measured results

450/450 files acquired, 0 failures. Cohort selection: 3 development systems, 2 validation
candidates, 4 excluded (reasons in `candidate_systems.json`), 0 chosen/discarded by any
model output (no model was run in this gate).

## Limitations

- Validation-candidate status for 1430/1433 was provisional pending Gate 5.6B's timestamp
  adjudication — it was **not** upheld (see checkpoint 16: both were downgraded to
  SECONDARY_ONLY on TIMESTAMP_AMBIGUOUS grounds).
- System 1283's true plant AC-power channel was left unresolved by design — Gate 5.6B's
  job, not this one's.
- No model of any kind (physics, empirical, hybrid) was fit or scored in this gate.

## Next

Gate 5.6B — cohort/timestamp/target-signal adjudication (see checkpoint 16).
