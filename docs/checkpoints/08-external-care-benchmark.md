---
task: external-care-benchmark
phase: 2
status: complete
---

## What was built

- `rai/eval/external/care/metrics.py`: the published CARE-to-Compare score (Gück, Roelofs &
  Faulstich, 2024), transcribed function-by-function from the paper's equations 1-5 and
  Algorithm 1, each cited in its docstring — Coverage (Eq.1), Accuracy (Eq.2), Reliability
  (Algorithm 1 criticality + Eq.1 at dataset level), Earliness (Eq.3), and the final weighted
  combination (Eq.4-5). Independent of RAI's own internal `rai.eval.care` module.
- `rai/eval/external/care/adapter.py`: two deliberately modest, un-transferred baselines —
  `IsolationForestBaseline` (n_estimators=100, contamination=0.09, matching the paper's own
  mini-benchmark hyperparameters) and `ZScoreThresholdBaseline` (naive 3σ channel threshold).
  RAI's trained champion is not used: it is fit on the synthetic fleet's schema and a
  same-day retrain onto CARE's anonymised columns would not really be "RAI's model".
- `rai/eval/external/care/farm_a_runner.py`: loads every Farm-A dataset via the (now-fixed, see
  below) `rai.ingest.care` loader, splits `train`/`prediction` on the dataset's own
  `train_test` column, builds ground truth for anomaly-event datasets by joining the
  dataset's own sequential `id` column against `event_info.csv`'s `event_start_id`/
  `event_end_id` (see "how it was verified" — CARE's timestamps are anonymised by a random
  per-dataset year shift, so a timestamp join would silently mislabel every dataset), fits
  each baseline on `train` rows, scores `prediction` rows, and combines into the final CARE
  score per model.
- **Fixed a real, pre-existing bug** in `rai/ingest/care.py` (untouched by any other work on
  this repo): `load_care_csv` and `load_event_info` both called `pd.read_csv()` without a
  separator, defaulting to comma. The real Zenodo archive is semicolon-delimited, which
  collapsed every 86-column dataset CSV into one column. Fixed with `sep=";"` at both call
  sites (one-line change each, with an inline comment recording this was verified against
  the archive, not guessed).
- Downloaded the real ~5.5GB CARE-to-Compare archive (Zenodo record 14006163, the corrected
  v6 deposit — the project's existing `rai/ingest/registry.py` entry cites the older,
  superseded 10958775 record; not edited, since updating the registry was out of this task's
  scope and the file is concurrently owned) and extracted Wind Farm A.
- `docs/evaluation/EXTERNAL_CARE.md`: methodology, the bug found/fixed, the id-based join
  rationale, and full real results.

## Files

- `rai/eval/external/care/{__init__,metrics,adapter,farm_a_runner}.py` — new.
- `rai/ingest/care.py` — two one-line fixes (`sep=";"` in `load_care_csv`, `load_event_info`).
- `tests/test_external_care_metrics.py`, `tests/test_external_care_adapter.py` — new,
  synthetic-data unit tests (19 total) written and passing before the real archive finished
  downloading, so metrics/adapter correctness did not depend on the multi-hour download.
- `docs/evaluation/EXTERNAL_CARE.md` — new.
- `data/raw/care/Wind Farm A/` — new real data on disk (gitignored, not committed).

## How it was verified

- `.venv\Scripts\python.exe -m pytest tests/test_external_care_metrics.py tests/test_external_care_adapter.py -q`
  — 19/19 passing, including hand-computed reproductions of the paper's own qualitative
  claims (the "always predict anomaly" and "always predict normal" trivial strategies both
  score CARE = 0).
- Verified the `sep=";"` fix directly: `pd.read_csv(path)` on a real Farm-A dataset CSV gave
  shape `(54358, 1)`; with `sep=";"` it gave `(54358, 86)`, matching the paper's documented
  column count.
- Verified the id-based join is safe before trusting it: confirmed dataset 68's real
  timestamps (`2022-07-29 13:20:00...`) do not match `event_info.csv`'s stated
  `event_start` (`2015-07-29 13:20:00`) for that same event — same month/day/time, different
  year, i.e. a per-dataset year-shift anonymisation, not a data error. Confirmed instead that
  rows with `id` in `[event_start_id, event_end_id]` fall entirely within that dataset's own
  `train_test == "prediction"` split.
- `rai/eval/external/care/farm_a_runner.py::_load_dataset` asserts `rows_in == rows_out` from
  the quality filter on every dataset load (would raise, not silently continue, if a future
  change reintroduced row-dropping and broke the id join) — this assertion held on all 22
  Farm-A datasets in the real run below.
- `.venv\Scripts\python.exe -m rai.eval.external.care.farm_a_runner` — real run against all 22
  Wind Farm A datasets (11 anomaly-event, 11 normal-behavior), both baselines, ~90s wall time
  (run twice: once before, once after moving the file to resolve a filename collision with a
  second concurrent session's own `rai/eval/external/care/runner.py` — see
  `docs/evaluation/EXTERNAL_CARE.md` §0 — both runs produced identical CARE=0.535/0.506).
  Output and artifacts inspected by hand (`artifacts/evaluation/gate2/external_care/`) and
  the final CARE-score arithmetic hand-verified against the printed sub-scores
  (e.g. isolation_forest: `(0.434 + 0.125 + 0.333 + 2*0.890) / 5 = 0.535`, matches).
- `ruff check rai/eval/external/care/farm_a_runner.py` — clean.
- Standalone `pyright` on `farm_a_runner.py` — 0 errors, 8 warnings (all the same
  `int(pandas.Series-typed scalar)` stub noise already tolerated elsewhere in this project).
- After restoring the other session's `runner.py` (`git checkout -- rai/eval/external/care/runner.py`,
  confirmed with an empty `git diff`), `pytest --collect-only` on the full suite succeeded
  (193 tests collected, no import errors) — confirming the accidental overwrite was fully
  undone before anything else was reported.

## Measured results

Wind Farm A, both baselines, real run 2026-09-12:

| model | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|
| isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 |
| zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 |

Only 1 of 11 real, documented anomaly events (a hydraulic-group fault) crossed the
detection-reliability threshold for either baseline — 10 real faults (a transformer failure,
two gearbox failures, two generator-bearing failures, five more hydraulic-group events) were
not reliably flagged. Full per-dataset table: `docs/evaluation/EXTERNAL_CARE.md` §5,
`artifacts/evaluation/gate2/external_care/summary.md`.

## Limitations

- Farm A only (22 datasets). Farms B (~257 cols) and C (~957 cols) were downloaded as part
  of the same archive but not extracted/attempted — each farm anonymises its own sensor
  schema independently, so this is three separate integration efforts, not one bigger run.
- 12 of 15 canonical wind signals could not be resolved from Farm A's anonymised
  `sensor_N_avg` column names (no descriptive alias available to `rai.ingest.care`'s
  resolver); the baselines here score CARE's raw sensor columns directly to work around this,
  but a future task could recover more signal by wiring `feature_description.csv` into a
  `sensor_map`.
- No hyperparameter search on either baseline; RAI's own trained champion was not
  transferred (see rationale in `docs/evaluation/EXTERNAL_CARE.md` §2). This is a real
  external-data reference point for two honest baselines, not a claim about RAI's best model.
- One run, no resampling/bootstrap — Gate 2D's uncertainty work (owned by the other
  concurrently-running session) is the place for confidence intervals, not this task.

## Next

Gate 2 external-CARE and OOD work (this session's assigned split) is now both executed and
documented. Remaining candidates, lower priority given hackathon time: (a) wire
`feature_description.csv` into `rai.ingest.care`'s `sensor_map` to recover more of the 12
unresolved Farm-A signals; (b) attempt Farm B/C once/if time allows; (c) merge these results
into `artifacts/evaluation/gate2/scorecard.json` once the other concurrently-running
session's own Gate 2 script (`scripts/evaluate_gate2.py`) has stabilized — deliberately not
attempted now to avoid colliding with that actively-changing file.
