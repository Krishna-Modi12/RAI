---
task: gate56b-cohort-adjudication
phase: 5
status: complete
---

## What was built

Adjudication-only gate (no modeling performed) resolving the three real data-quality
issues Gate 5.6A flagged, plus two additional integrity defects found during this gate's
own verification pass:

- **Timestamps:** systems 1239/1283/34 have real ground-truth `utc_measured_on` (0% null).
  Systems 1430/1433 have it 100% null; classified `TIMESTAMP_AMBIGUOUS` (a circumstantial
  analogy to sibling system 1283's own UTC ground truth was used as evidence, not treated
  as proof for 1430/1433 themselves).
- **Target-signal semantics:** all 5 systems resolved to a trustworthy power-target
  classification (`VALID_GENERATION_POWER` or `VALID_SIGNED_POWER`); system 1283's
  39.5%-negative channel investigated and classified as legitimate nighttime
  station-service/parasitic draw on a bidirectional net meter (100% coincident with real
  POA=0), not a data defect.
- **Unit-scale defect (found this gate, not inherited):** systems 1430/1433's AC power
  channels required reapplying the metrics dictionary's `calc_scale` to reach true Watts
  (proven via real AC/DC power ratio at matched peak-generation timestamps for 1430;
  capacity-plausibility argument for 1433) — the dictionary's `calc_scale`/`units` metadata
  is not reliably informative on its own and was verified per-system against physical
  plausibility. See `unit_scale_audit.csv`.
- **Degenerate channels (found this gate):** system 1239's `wind_speed` (flatlined,
  range 0.000–0.078) and system 1283's `dc_power` (exactly 0.0 for all 504,384 records)
  carry no real signal despite 0% missingness by record count.
- **Missingness disqualification:** system 1433's AC-power target is 74.7% missing,
  which flips `empirical_ready` to `False` via a 50%-severe-missingness threshold —
  independent of, and in addition to, its timestamp issue.
- **pvlib readiness:** verified module/inverter parameter matches against pvlib's real CEC
  databases (21,535 modules, 3,264 inverters) rather than asserting a match; no invented
  tilt/azimuth/temperature-coefficient parameters.
- Final frozen cohort: Development=[1239, 1283, 34], Validation=[] (`INSUFFICIENT_DATA`,
  no padding applied), Secondary-only=[1430, 1433].

## Files

- `scratch_gate56a/build_gate56b.py` — artifact-generation script.
- `artifacts/evaluation/gate56/cohort_adjudication/*` — 13 artifacts including
  `cohort_adjudication.csv/json`, `cohort_freeze_v2.json`, `pvlib_readiness.csv`,
  `target_signal_manifest.csv`, `timestamp_adjudication.csv`, `unit_scale_audit.csv`,
  `system_1283_power_semantics.md`, `alignment_policy.json`, `summary.md`.
- `tests/test_gate56b_cohort_adjudication.py` — 63 tests across 16 verification topics.

## How it was verified

`pytest tests/test_gate56b_cohort_adjudication.py -v` — 63 passed. Full `pytest -q` — 407
passed. `ruff check .` — all checks passed. `pyright` — 3 errors, all pre-existing and
unrelated to this gate's files (`scripts/evaluate.py`, `scripts/evaluate_gate2.py`); 0 new
errors in any Gate 5.6B file.

## Measured results

Per-system classification: 1239/1283/34 = `READY` (`final_role=DEVELOPMENT`); 1430/1433 =
`READY_WITH_LIMITATIONS` (`final_role=SECONDARY_ONLY`). Validation cohort is empty —
system-level external holdout is **not** currently statistically meaningful; Gate 5.6C
must design and justify its own fallback (e.g. a temporal holdout within the 3 development
systems) rather than treat this as resolved.

## Limitations

- This gate produced zero model fits, zero `ModelChain` runs, zero residuals — adjudication
  only, by explicit design.
- Physics-readiness assumes pvlib's standard preset tables (AOI, temperature model) as a
  disclosed modeling assumption where no per-system measured coefficient exists — this is
  not the same as a measured parameter.
- Validation cohort is `INSUFFICIENT_DATA`; Gate 5.6C cannot claim a system-level external
  holdout without first solving this gap honestly.

## Next

Gate 5.6C is a decision gate, not an automatic next step: before building any solar
expected-performance model, determine whether a genuinely defensible validation route
exists (real fault/event labels), or whether solar modeling must proceed as
`MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED` only.
