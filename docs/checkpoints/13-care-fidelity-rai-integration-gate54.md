---
task: care-fidelity-rai-integration-gate54
phase: 5
status: complete
---

## What was built

- **Feature inventory** (`rai/eval/external/care/feature_inventory.py`): one row per raw
  column per farm, cross-referenced against CARE's own `feature_description.csv` sidecar.
  Found wiring those descriptions into `rai.ingest.care.resolve_columns`'s existing (but
  previously unused by any runner) `sensor_map` parameter recovers 10/15 canonical signals on
  Farm A, 9/15 on Farm B, 13/15 on Farm C - up from 2 (+status_code) under the name-only
  default every existing runner uses. Found and fixed a real correctness bug in the process:
  a cumulative energy counter (Farm A `sensor_50`, "Total active power", unit Wh,
  `is_counter=False`) would silently win the `power_kw` slot away from the physically-correct
  instantaneous-kW column if fed into the sensor_map unfiltered - fixed by excluding any
  description row whose unit is a cumulative-energy unit (`ENERGY_COUNTER_UNITS`) before
  building the map, since CARE's own `is_counter` flag does not reliably catch these.
- **Rejection classification** (same module): every unrecognized sensor column classified as
  `no_canonical_slot` (unsupported semantic type - RAI's 15-signal schema has no matching
  concept), `lost_to_higher_scoring_column_for_<canonical>` (a confirmed implementation
  limitation: `resolve_columns` is winner-take-all per canonical name, `rai/ingest/care.py`
  lines 405-460, so a farm with many same-category sensors - e.g. Farm C's 22 pooled turbines
  each with their own pressure transducer - can only ever surface one), or
  `excluded_cumulative_energy_counter`.
- **Two frozen feature policies** (`rai/eval/external/care/feature_policy.py`): CARE_NARROW
  (`sensor_map=None`, reproduces `farm_a_runner.py` exactly) and CARE_SEMANTIC
  (`sensor_map=feature_inventory.build_safe_sensor_map(...)`), evaluated with the same two
  baselines (`isolation_forest`, `zscore_threshold`) and the same unmodified CARE scorer,
  across all three farms independently.
- **Cross-farm re-check under CARE_SEMANTIC** (`rai/eval/external/care/cross_farm_semantic.py`):
  re-runs the existing A->B/A->C transfer protocol (fit once on source TRAIN rows, score
  unmodified on every target dataset, never refit - reuses `cross_farm.py`'s own
  `_intersected_columns`/`_fit_on_columns`, not reimplemented) with each farm loaded through
  its own CARE_SEMANTIC sensor_map.
- **RAI integration (Phase 5):** verified, did not rebuild - the concurrently-running session
  in this same working directory had already built `rai/eval/external/care/champion.py`
  (`RAIChampionDetector`/`fit_rai_champion`) and computed real, official-CARE-scorer numbers
  (`docs/checkpoints/10-care-fidelity-rai.md`, `11-care-feature-rai-integration.md`). Verified
  its train/prediction boundary, feature lineage, threshold/normalization provenance, and
  determinism by reading the code and re-running its 43 existing tests (all pass), rather than
  building a second, competing adapter. `RAI CARE = COMPUTED` (0.601 A / 0.560 B / 0.575 C,
  `care_common` policy) - not renamed from an internal score, and
  `rai/eval/external/care/metrics.py` (the official scorer) does not appear in `git diff
  --stat` for this working tree, confirming it was not modified by this or the concurrent
  session's work.
- **Doc corrections** (`docs/evaluation/EXTERNAL_GENERALIZATION.md`): withdrew the "WindADBench
  does not resolve to a real, citable benchmark" claim (it is real - verified directly against
  the GitHub API and README, not just re-searched) and the "the benchmark's own anonymisation
  is the bottleneck" framing (substantially an implementation limitation, per the feature
  inventory above); softened cross-farm transfer language to "observed under the implemented
  transfer protocol" with an explicit confound list; added a cross-turbine caveat citing
  published transfer-learning literature on the limits of pooled multi-turbine pretraining.

## Files

- `rai/eval/external/care/feature_inventory.py` - new.
- `rai/eval/external/care/feature_policy.py` - new.
- `rai/eval/external/care/cross_farm_semantic.py` - new.
- `tests/test_gate54_feature_policy.py` - new, 14 tests, synthetic on-disk CSVs, independent
  of the real archive.
- `docs/evaluation/EXTERNAL_GENERALIZATION.md` - corrected (sourcing note, anonymisation
  framing, cross-turbine caveat) and extended (new "Gate 5.4 - CARE Fidelity Audit + RAI
  Integration" section, distinct from the concurrently-developed session's own same-numbered
  "gate54" cross-farm-matrix work - both preserved, disclosed in a scope note).
- `docs/checkpoints/13-care-fidelity-rai-integration-gate54.md` - this checkpoint (numbered 13
  to avoid the pre-existing 10/11/12 collisions from the concurrently-running session's own
  checkpoint files in this shared working directory).
- `artifacts/evaluation/external_care/{feature_inventory.csv,feature_inventory.json,
  feature_policy_comparison.csv,feature_policy_comparison.json,cross_farm_semantic_results.json,
  cross_farm_semantic_summary.md}` - new.
- Not modified: `rai/eval/external/care/{farm_a_runner,cross_turbine,cross_farm,champion,
  published_if,features,metrics}.py`, any file under the concurrent session's `gate51/gate52/
  gate53/gate54` scripts or artifacts.

## How it was verified

- `ruff check .` - 1 pre-existing error in the concurrent session's own in-flight
  `scripts/gate54_cross_farm_transfer.py` (an unused local variable), not touched here per
  the "never overwrite shared benchmark runners" rule; every file this task added or edited
  is individually clean.
- `pyright --pythonpath .venv/Scripts/python.exe` on every new module - 0 errors (a handful of
  `int(Series)` pandas-stub warnings, the same tolerated noise already documented in
  checkpoint 09).
- `pytest tests/ -q` - 278/278 passing (264 pre-existing + 14 new from this task).
- `pytest tests/test_gate52_baselines_and_champion.py tests/test_gate52_care_scorer_audit.py
  tests/test_gate53_cross_turbine.py -q` - 43/43 passing, re-run today to confirm the
  concurrently-built champion/CARE-scorer work this task relies on for Phase 5 is still green.
- Real, full executions, not estimated: CARE_NARROW/CARE_SEMANTIC x 2 models on Farm A (fast),
  Farm B (fast), Farm C (~25 min background job, 957 columns x 58 datasets x 2 policies); A->B
  and A->C semantic cross-farm transfer (~16.5 min background job, dominated by Farm C load
  time). CARE_NARROW numbers reproduced the already-published Farm A/B/C figures exactly
  (0.5345/0.5062, 0.5324/0.4013, 0.5328/0.4388) - a determinism cross-check, not a new result.

## Measured results

**CARE_NARROW vs CARE_SEMANTIC** (`artifacts/evaluation/external_care/feature_policy_comparison.csv`):

| farm | model | CARE_NARROW | CARE_SEMANTIC | delta |
|---|---|---|---|---|
| A | isolation_forest | 0.5345 | 0.6022 | +0.068 |
| A | zscore_threshold | 0.5062 | 0.5308 | +0.025 |
| B | isolation_forest | 0.5324 | 0.5554 | +0.023 |
| B | zscore_threshold | 0.4013 | 0.5349 | +0.134 |
| C | isolation_forest | 0.5328 | 0.6023 | +0.070 |
| C | zscore_threshold | 0.4388 | 0.5725 | +0.134 |

6 of 6 farm/model combinations improve under CARE_SEMANTIC; none regress.

**Cross-farm transfer, CARE_NARROW (§4, pre-existing) vs CARE_SEMANTIC (this task):**

| pair | model | narrow | semantic | direction |
|---|---|---|---|---|
| A->B | isolation_forest | 0.600 | 0.574 | lower |
| A->B | zscore_threshold | 0.430 | 0.557 | higher |
| A->C | isolation_forest | 0.601 | 0.627 | higher |
| A->C | zscore_threshold | 0.484 | 0.295 | lower |

Direction is not consistent across model/pair - reported as observed, not as evidence for or
against generalization (see doc §10.4 for the full confound discussion).

**RAI CARE** (concurrently computed, verified not re-derived): 0.601 (A) / 0.560 (B) / 0.575
(C), `care_common` policy, official CARE scorer, real leakage-checked provenance.

## Limitations

- Feature-policy and cross-farm-semantic runs use the same two deliberately modest baselines
  as every other gate in this document series - not RAI's own champion (that comparison is
  Phase 5's `RAI CARE`, a separate table, never merged with these).
- The `lost_to_higher_scoring_column_for_X` implementation limitation (§10.2) is described but
  not fixed in this gate - the brief explicitly prohibits model/schema architecture changes.
- The `RAI_CHAMPION`/`care_2d` = 0.000 discrepancy found while reading the concurrent
  session's own checkpoints (`11-care-feature-rai-integration.md`) is disclosed, not
  diagnosed - it belongs to code this task does not own and the brief prohibits new
  model-architecture investigation.
- Cross-farm-semantic's feature intersection differs per pair (6 signals for A->B, 9 for A->C)
  because it is computed from the data, not fixed to the global 3-farm common set - correct
  per the module's own design, but means the two rows in that table are not evaluating an
  identical feature count.
- DECISION scoreboard not computed (not required to validate the integration boundary, per
  the brief's own scope rule).

## Next

Candidates, none begun: (a) extend RAI's canonical wind schema to support multiple named
instances per physical-quantity category, which the rejection-reason breakdown (§10.2) shows
would resolve a large share of Farm C's 256 `lost_to_higher_scoring` columns without touching
CARE's anonymisation at all; (b) diagnose the `RAI_CHAMPION`/`care_2d` = 0.000 discrepancy
noted above; (c) the full six-way cross-farm matrix, already in progress under the
concurrently-running session's own "Gate 5.4 - Cross-Farm Wind Transfer & Target-Normal
Calibration" section of the same document - not duplicated here.
