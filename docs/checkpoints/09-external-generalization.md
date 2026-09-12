---
task: external-generalization
phase: 2
status: complete
---

## What was built

- Extracted Wind Farm B (15 datasets, 257 raw columns) and Wind Farm C (58 datasets, 957 raw
  columns) from the same already-downloaded CARE-to-Compare archive Farm A came from
  (`data/raw/care/CARE_To_Compare.zip`, Zenodo 14006163). Both gitignored, same as Farm A.
- `rai/eval/external/care/cross_turbine.py` (new): leave-one-turbine-out evaluation within
  Farm A. For each of Farm A's 5 turbines, fits a baseline on the pooled TRAIN rows of the
  *other* 4 turbines only, then scores it on the held-out turbine's own datasets with the
  same CARE metrics `farm_a_runner.py` uses.
- `rai/eval/external/care/cross_farm.py` (new): fit-on-source, score-on-target transfer. Fits
  one baseline on a source farm's pooled TRAIN rows (restricted to the data-derived feature
  intersection with the target), scores it on every target-farm dataset, never refits.
- `rai/eval/external/care/farm_a_runner.py`: **not modified** except one docstring paragraph
  noting `run_farm` is farm-agnostic and reused as-is for Farm B/C - its own `FARMS`/`run_all`/
  CLI entrypoint remain Farm-A-only by design, preserving existing behavior per this task's
  own instruction not to change a frozen baseline unless required.
- `docs/evaluation/EXTERNAL_GENERALIZATION.md` (new): Gates A (recap), B (Farm B+C), C
  (cross-turbine), D (cross-farm A->B, A->C) with real numbers and honest, non-causal
  interpretation. Gates E (RAI vs baselines on CARE), G (decision-policy benchmark) and H
  (sensor-safety red-team) are explicitly scoped out with rationale (§6-7), not faked.
- `docs/evaluation/EXTERNAL_CARE.md`: added a 4-line pointer to the new document; no other
  change - the original Farm-A-only content is untouched.
- Investigated the "WindADBench" citation from the task brief via web search; it did not
  resolve to a real, citable benchmark. Not used as a methodology source anywhere in the new
  document (see `EXTERNAL_GENERALIZATION.md`'s "A note on sourcing").

## Files

- `rai/eval/external/care/{cross_turbine,cross_farm}.py` - new.
- `rai/eval/external/care/farm_a_runner.py` - one docstring paragraph added, no behavior change.
- `tests/test_external_care_cross_turbine.py`, `tests/test_external_care_cross_farm.py` - new,
  8 tests total, synthetic-data only (independent of the real archive).
- `docs/evaluation/EXTERNAL_GENERALIZATION.md` - new.
- `docs/evaluation/EXTERNAL_CARE.md` - added a pointer to the new document.
- `data/raw/care/Wind Farm B/`, `data/raw/care/Wind Farm C/` - new real data on disk
  (gitignored, not committed).
- `artifacts/evaluation/gate2/external_care/{all_farms_results,all_farms_summary,
  cross_turbine_results,cross_turbine_summary,cross_farm_results,cross_farm_summary,
  farm_c_results}.{json,md}` - new.

## How it was verified

- `ruff check rai/eval/external/care/ tests/test_external_care_cross_turbine.py
  tests/test_external_care_cross_farm.py` - clean.
- `pyright --pythonpath .venv/Scripts/python.exe rai/eval/external/care/{cross_turbine,
  cross_farm,farm_a_runner}.py` - 0 errors, 24 warnings (same tolerated pandas-stub
  `int(Series)` noise already documented in checkpoint 08).
- `.venv\Scripts\python.exe -m pytest tests/ -q` - 212/212 passing (204 baseline + 8 new).
- Column resolution verified directly against a raw header sample from each of the three
  farms (not assumed): all three resolve exactly the same 3/15 canonical signals
  (`power_kw`, `wind_speed_ms`, `status_code`) - this is the data-derived reason the
  cross-farm feature intersection is two columns, not an assumption carried over from the
  task brief's "wind_speed/active_power/rotor_speed" suggestion (rotor_rpm does not resolve
  on any of the three farms from the source headers alone).
- Cross-turbine's "never trains on the held-out turbine's own rows" guarantee is a direct
  unit-test assertion (`test_leave_one_turbine_out_never_trains_on_the_held_out_turbines_own_rows`),
  not just documentation.
- Cross-farm's "fits exactly once, never refits per target dataset" guarantee is likewise a
  direct unit-test assertion (`test_run_transfer_never_refits_and_uses_only_intersected_columns`).
- Full real runs executed, not estimated: Farm B (both baselines, ~100s), Farm C (both
  baselines, 1399s total - a single Farm-C dataset load measured directly at ~17s given its
  957 raw columns), cross-turbine on Farm A (both baselines, all 5 folds, <60s), cross-farm
  A->B and A->C (both baselines each, ~1500-2000s each dominated by Farm-C load time).
  Farm B was re-run a second time while consolidating artifacts and reproduced identical
  numbers (CARE=0.532/0.401) - a determinism check, not just a rerun.
- Final CARE arithmetic spot-checked by hand for one row (Farm C isolation_forest:
  `(0.280 + 0.132 + 0.465 + 2*0.893) / 5 = 0.533`, matches the reported value).

## Measured results

All real, all in `docs/evaluation/EXTERNAL_GENERALIZATION.md` in full with sub-scores;
headline CARE numbers only, here:

| axis | isolation_forest | zscore_threshold |
|---|---|---|
| Farm A (recap) | 0.535 | 0.506 |
| Farm B | 0.532 | 0.401 |
| Farm C | 0.533 | 0.439 |
| Cross-turbine Farm A, 5 folds | 0.427-0.775 | 0.000-0.615 |
| Cross-farm A->B | 0.600 | 0.430 |
| Cross-farm A->C | 0.601 | 0.484 |

Two findings worth flagging explicitly (both in the doc, both hedged with "consistent with,"
never "causal" or "generalizes"):

1. All three farms land within 0.002 of each other on isolation_forest CARE (0.535/0.532/
   0.533) despite 86/257/957 raw columns and different fault mixes - consistent with the
   resolvable feature space being the same two columns (`wind_speed_ms`, `power_kw`) on every
   farm, not evidence of a farm-invariant detector.
2. Cross-farm transfer (fit on Farm A, score on B or C) scores *higher* CARE than each
   target's own in-farm fit, in both B and C independently - consistent with Farm A's larger
   pooled training set giving a better-calibrated 2-D density estimate, at a real cost to
   accuracy (more false alarms on the target's healthy turbines).

## Limitations

- Two deliberately modest, off-the-shelf baselines throughout - not RAI's own trained model
  (Gate E explicitly not attempted; same rationale as `EXTERNAL_CARE.md` §2).
- Cross-turbine folds carry 1-3 anomaly datasets each - point estimates, not confidence
  intervals.
- Only 2 of 15 canonical wind signals ever contribute to any score in this document
  (`wind_speed_ms`, `power_kw`) - every result here is bounded by what a 2-feature model can
  express, on every farm.
- No bootstrap/resampling uncertainty anywhere (matches `EXTERNAL_CARE.md`'s own limitation).
- Full 6-way cross-farm matrix (B->A, B->C, C->A, C->B) not attempted - A->B and A->C were
  prioritized per the task brief's own stated ranking; time was the binding constraint, not a
  finding that made the rest uninteresting.
- Gates G (decision-policy benchmark) and H (sensor-safety red-team) were not extended to
  CARE data: RAI's decision layer consumes RAI's own risk-model output, which does not exist
  for these un-transferred baselines - there is no risk score to hand it. What already exists
  for those gates (owned by the concurrently-running session) is referenced, not duplicated.

## Next

Candidates, roughly in the order the task brief itself ranked them, none begun: (a) the
6-way cross-farm matrix (B->A, B->C, C->A, C->B); (b) wiring `feature_description.csv` into
`rai.ingest.care`'s `sensor_map` so more than 2 features resolve per farm, which would make
every result in this document richer without changing the methodology; (c) once RAI's own
champion has a CARE-compatible schema (out of this task's scope), a genuine Gate-E "RAI vs
baseline" comparison on real external data becomes possible for the first time.
