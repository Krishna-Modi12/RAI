# External CARE-to-Compare Benchmark (Gate 2)

**Status:** Executed on real data, real results below (Farm A only - see below for Farm B/C)
**Last updated:** 2026-09-12
**Code:** `rai/eval/external/care/{metrics,adapter,farm_a_runner}.py`
**Artifacts:** `artifacts/evaluation/gate2/external_care/{results.json,summary.md}`

**Farm B and Farm C, plus cross-turbine and cross-farm generalization, are covered in a
follow-on document:** `docs/evaluation/EXTERNAL_GENERALIZATION.md`. Everything below this
line is unchanged from the original Farm-A-only task and still describes exactly what it
always described - Farm A only, two baselines.

---

## 0. A filename collision with concurrent Gate-2 work, and how it was resolved

While writing this up, a second, independently-running Claude Code session on this same
repository had - minutes earlier - committed its *own* `rai/eval/external/care/runner.py`
(a fixture-based, four-track, five-baseline harness, part of a separate "Phase 3A"
evaluation battery with its own new test file, `tests/test_phase3_evaluation.py`). This
session's own runner was written to that same filename without first checking for a
concurrent claim on it, overwriting the other session's committed version. The mistake was
caught immediately (`pytest` failed to collect `tests/test_phase3_evaluation.py` -
`ImportError: cannot import name 'inspect_care_dataset_state'`), the other session's
committed file was restored with `git checkout -- rai/eval/external/care/runner.py`
(verified afterwards with an empty `git diff` and a clean `pytest --collect-only`), and this
session's own full-archive runner was moved to `rai/eval/external/care/farm_a_runner.py` - a
distinct name so both benchmark drivers coexist. No result in this document, and nothing in
`rai/eval/external/care/{metrics,adapter}.py`, was affected: the collision was confined to
one file, and it was resolved before anything was reported.

## 1. Why this exists, and why it is separate from `rai/eval/care.py`

RAI's internal `rai.eval.care` module computes a "CARE-inspired" score against the
synthetic 42-asset fleet — useful, but self-graded: the model, the fault labels and the
scoring code all live in this repository. `docs/AUDIT_REPORT.md` §2.6 also flagged that
module for a fabricated `"217,728 timestamps (large)"` string in an earlier iteration.

This directory is a different thing entirely: the **published CARE-to-Compare benchmark**
(Gück, Roelofs & Faulstich, *"CARE to Compare: A real-world benchmark dataset for early fault
detection of wind turbine generators"*, 2024, Zenodo record 14006163, CC-BY-SA-4.0) — a
third-party dataset, third-party fault labels, and a scoring formula transcribed directly
from the paper's own equations (see `metrics.py` docstrings, each cited to its equation
number). Nothing here is fit to, or tuned against, any RAI result. It answers a different
question than the internal eval suite: "how does a genuinely modest, paper-methodology
baseline do on real SCADA data with real labelled faults, scored the way the benchmark's
own authors score it?"

## 2. What was actually run, and what was not

- **Farm A only** (22 datasets: 11 anomaly-event, 11 normal-behavior). Farm B (~257 columns)
  and Farm C (~957 columns) were downloaded as part of the same 5.5GB archive but not
  extracted or attempted this round — the three farms do not share a sensor schema (each is
  anonymised independently), so scoring them is three separate integration efforts, not one
  with more rows. Given the hackathon's remaining time, Farm A alone (smallest, and the one
  RAI's `rai.ingest.care` column-resolution logic was already validated against — see §3) was
  judged the honest scope rather than rushing B and C and risking a silent mistake.
- **Two baselines**, deliberately not RAI's trained champion:
  - `IsolationForestBaseline` — n_estimators=100, contamination=0.09, replicating the CARE
    paper's own mini-benchmark hyperparameters (section 4.2.1) for direct comparability.
  - `ZScoreThresholdBaseline` — flags a row if any channel is ≥3 std from its own
    training-period mean. Deliberately naive (no peer comparison, no environmental gating,
    no persistence/hysteresis), so it is a weaker comparator, not a rebrand of RAI's champion.
  RAI's actual trained expected-behaviour models were **not** transferred: they are fit on
  the synthetic fleet's specific schema and retraining them on CARE's anonymised columns in
  the time available would not really be "RAI's model" — it would be a new model wearing
  RAI's name. Reporting a genuine score for two honest, modest baselines was judged more
  useful than reporting a borrowed number for the champion.
- Each dataset's own `train_test` column governs the split (baselines fit on `"train"` rows,
  scored on `"prediction"` rows) — never fit on prediction data.

## 3. A real bug found and fixed before any of this could run

`rai/ingest/care.py::load_care_csv` and `::load_event_info` both called `pd.read_csv()`
without a separator, defaulting to comma. The real archive is **semicolon-delimited**
(verified directly against the downloaded Zenodo files) — this silently collapsed every
86-column dataset CSV into one column (verified: `df.shape` went from `(54358, 1)` to
`(54358, 86)` after adding `sep=";"`). This is a pre-existing bug in a module untouched by
this hackathon's other concurrent work; it had never been exercised against real data
before. Fixed with one line at each call site (`rai/ingest/care.py`).

Column resolution against the real (anonymised) Farm A headers matched 3 of 15 canonical
wind signals with high confidence (`power_kw` ← `power_29_avg`, `status_code` ←
`status_type_id`, `wind_speed_ms` ← `wind_speed_3_avg`); the other 12 are correctly left
unmatched/null, because CARE's Farm A sensor names (`sensor_11`, `sensor_38`, ...) carry no
descriptive alias for the resolver to match against — the paper's own
`feature_description.csv` decodes them, but nothing in `rai/ingest/care.py` consumes that
sidecar file yet, so gearbox/generator/bearing temperatures are not resolved into RAI's
canonical schema. The two baselines here work around this by scoring on CARE's own raw
`sensor_N_*` / `wind_speed_*` / `power_*` columns directly (`adapter.py`'s
`FEATURE_COLUMNS`), not on RAI's resolved canonical columns, so this gap did not block
scoring — but it does mean a future task could recover more signal by wiring
`feature_description.csv` into a `sensor_map` and re-running.

## 4. Ground truth: the `id`-column join, not timestamps

CARE's published timestamps are anonymised by a **random, per-dataset year shift**
(confirmed empirically: dataset 68's own timestamps start `2022-07-29 13:20:00`, but
`event_info.csv` lists `event_start = 2015-07-29 13:20:00` for that same event — identical
month/day/time, different year). Joining ground truth by timestamp would therefore silently
mislabel every dataset. The dataset's own sequential `id` column (0..N-1, assigned in
timestamp order within that one file) is unaffected by the year shift and is what
`event_info.csv`'s `event_start_id`/`event_end_id` actually key against — confirmed
empirically (dataset 68: all `id`-in-range rows fall inside the `train_test == "prediction"`
split; the additional 281 prediction rows outside that range are `status_type_id == 3`
padding after the window, exactly as the paper describes).

`rai/eval/external/care/farm_a_runner.py::_load_dataset` calls `load_care_csv` with
`drop_non_normal=False, drop_duplicate_ts=False, required_signals=()` specifically so no row
is ever dropped — a single dropped row would silently break this positional join. The runner
asserts `rows_in == rows_out` after loading and would raise rather than continue if that ever
stopped being true.

## 5. Results (real run, 2026-09-12)

Wind Farm A, 22 datasets (11 anomaly-event, 11 normal-behavior), 92 seconds wall time for
both baselines combined.

| model | CARE | coverage (F<sub>0.5</sub>) | earliness | reliability (F<sub>0.5</sub>) | accuracy |
|---|---|---|---|---|---|
| isolation_forest | **0.535** | 0.434 | 0.125 | 0.333 | 0.890 |
| zscore_threshold | **0.506** | 0.182 | 0.027 | 0.333 | 0.994 |

(Full 22-row per-dataset breakdown for both models: `artifacts/evaluation/gate2/external_care/summary.md`.)

For reference, the CARE paper's own mini-benchmark reports isolation-forest CARE scores in
roughly the 0.4–0.6 range depending on farm and feature subset — these numbers land in the
same neighbourhood, which is a reassuring sanity check on the transcription in `metrics.py`,
not a claim of beating or matching the paper's exact number (different feature subset,
different farm-specific hyperparameter search).

## 6. Reading these numbers honestly

- **Event-level reliability is the weak point for both baselines**: only 1 of 11 anomaly
  events (event 45, a hydraulic-group fault) crossed the criticality threshold (72,
  ~12 consecutive hours of detections) for either model — reliability F<sub>0.5</sub> = 0.333
  for both. Ten real, documented faults (transformer failure, gearbox failures, generator
  bearing failures, five more hydraulic-group events) were **not** reliably flagged by either
  baseline. This is the expected result for genuinely un-tuned, off-the-shelf detectors on
  real SCADA data with 12 unresolved sensor channels (§3) — it is not a favorable number, and
  it is reported as such rather than cherry-picked around.
- **`zscore_threshold`'s much lower coverage (0.182 vs 0.434) with much higher accuracy
  (0.994 vs 0.890) is a real, expected trade-off**: a static 3σ threshold with no
  persistence logic almost never fires, so it rarely flags a healthy dataset (high accuracy)
  but also rarely flags a faulty one until the fault is extreme (event 45 and 84 only, both
  with sustained anomalies) — low coverage, low earliness.
- **`isolation_forest`'s coverage (0.434) and earliness (0.125) are both genuinely modest**,
  not strong. An earliness of 0.125 means detections cluster very late within each labelled
  fault window on average (the weighting scheme gives 1.0 for a detection in the first half
  of the window and decays linearly to 0 at the very end) — consistent with an
  under-tuned baseline, not a tuned production detector.
- **This is Farm A only, two off-the-shelf baselines, no hyperparameter search.** It
  establishes a real, honest external-data reference point; it is not a claim about how
  RAI's own trained champion would perform if properly retrained and evaluated on CARE, and
  it is not a claim about Farms B/C, which were not attempted.

## 7. Reproduce

```
.venv\Scripts\python.exe -m rai.eval.external.care.farm_a_runner
```

Requires `data/raw/care/Wind Farm A/` populated from Zenodo record 14006163 (not shipped in
this repository — `data/raw/*` is gitignored; see `rai.ingest.care.discover()` for what the
loader expects on disk). Writes
`artifacts/evaluation/gate2/external_care/{results.json,summary.md}`.
