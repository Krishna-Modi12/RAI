# External CARE Generalization Gate (Gate 2, continued)

**Status:** Gates A-D executed on real data; Gates E/G/H explicitly scoped out this round (see §7)
**Last updated:** 2026-09-12
**Code:** `rai/eval/external/care/{farm_a_runner,cross_turbine,cross_farm}.py`
**Artifacts:** `artifacts/evaluation/gate2/external_care/{results,cross_turbine_results,cross_farm_results}.json`

This document extends `docs/evaluation/EXTERNAL_CARE.md` (Farm A only, two baselines,
CARE=0.535/0.506) along the axes a single farm's CARE score cannot answer: does either
baseline's performance survive an unseen turbine, an unseen farm, or a different fault mix?
It does **not** re-derive the CARE scoring method (see `EXTERNAL_CARE.md` and `metrics.py`
for that) and it does **not** claim RAI's own trained champion was evaluated here (see §7 -
that remains explicitly out of scope, same rationale as before).

A note on sourcing: the request that produced this document also cited "WindADBench" as
prior art for a cross-turbine/cross-farm evaluation protocol using a shared
wind_speed/active_power/rotor_speed feature set. A web search for this name during this task
did not turn up a real, citable benchmark by that name - only the genuine CARE-to-Compare
paper (Gück, Roelofs & Faulstich, 2024, arXiv:2404.10320) and unrelated cross-farm SCADA
studies. Per this project's numerical-honesty rule, "WindADBench" is **not** cited as a
methodology source anywhere below; the cross-turbine/cross-farm design here is this
project's own, grounded in the real CARE paper and standard covariate-shift practice, not a
borrowed protocol from an unverified source.

---

## 0. What actually changed on disk

- Extracted Wind Farm B (15 datasets, 257 raw columns) and Wind Farm C (58 datasets, 957 raw
  columns) from the same already-downloaded 5.5GB Zenodo archive (`data/raw/care/CARE_To_Compare.zip`,
  record 14006163) that Farm A came from. Both are gitignored under `data/raw/`, same as Farm A.
- Added two new modules, both reusing `rai.ingest.care`'s loader and `rai.eval.external.care.metrics`'s
  scoring functions without modification:
  - `rai/eval/external/care/cross_turbine.py` - leave-one-turbine-out within Farm A (Gate C).
  - `rai/eval/external/care/cross_farm.py` - fit-on-source, score-on-target transfer (Gate D).
- `rai/eval/external/care/farm_a_runner.py` was **not modified** - `run_farm` already took a
  farm directory as a parameter, so Farm B and C run through the exact same code Farm A did
  (verified: nothing farm-A-specific was hardcoded in it).
- 8 new tests (`tests/test_external_care_cross_turbine.py`,
  `tests/test_external_care_cross_farm.py`), synthetic-data only, independent of the real
  archive - full suite 212/212 passing after these changes (204 before this task's `pytest`
  count in the README + 8 new).

## 1. Gate A - Farm A component audit (recap, not re-run)

Already answered in `docs/evaluation/EXTERNAL_CARE.md` §5-6 and not re-litigated here:

| model | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|
| isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 |
| zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 |

**Is 0.535 limited by coverage, accuracy, reliability, or earliness?** Reliability
(event-level: did the whole labelled fault window get flagged strongly enough to cross the
paper's own criticality threshold) is the clear weak point for both models - only 1 of 11
real anomaly events (event 45, a hydraulic-group fault on the turbine this document calls
`CARE-WT-13`) crossed it. Coverage (point-wise, within an event's own window) is modest but
non-zero (0.434 for isolation_forest); earliness is low (0.125), meaning the few detections
that do happen cluster late in the labelled window rather than early. Accuracy (false-alarm
control on normal-behavior datasets) is the strongest sub-score for both models. In short:
**the detectors mostly fail to sustain a strong-enough signal for long enough to cross the
event-level bar, not that they never see anything at all.**

## 2. Gate B - Farm B and Farm C, same methodology, no refit

Same two baselines, same `run_farm` code path Farm A used, run independently per farm (a
model fit on Farm A's own data never sees Farm B or C in this section - that is Gate D, §4).

| farm | model | CARE | coverage | earliness | reliability | accuracy | n datasets (anomaly/normal) |
|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 | 11/11 |
| Wind Farm A | zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 | 11/11 |
| Wind Farm B | isolation_forest | 0.532 | 0.236 | 0.079 | 0.556 | 0.896 | 6/9 |
| Wind Farm B | zscore_threshold | 0.401 | 0.008 | 0.002 | 0.000 | 0.999 | 6/9 |
| Wind Farm C | isolation_forest | *pending - background run, see §2.1* | | | | | 27/31 |
| Wind Farm C | zscore_threshold | *pending - background run, see §2.1* | | | | | 27/31 |

Column resolution is consistent across all three farms: `rai.ingest.care.resolve_columns`
matches exactly the same 3 of 15 canonical signals on every farm's raw header
(`power_kw`, `wind_speed_ms`, `status_code`) - verified directly against a raw header sample
from each farm, not assumed. This is the real, data-derived reason Gate D's feature
intersection (§4) is only two columns wide.

**Reading Farm B honestly:** isolation_forest's Farm B CARE (0.532) is close to Farm A's
(0.535), but the sub-scores tell a different story underneath a similar headline: Farm B's
*reliability* (0.556) is noticeably higher than Farm A's (0.333) - more of Farm B's 6 real
anomaly events crossed the criticality threshold - while its *coverage* (0.236) is lower than
Farm A's (0.434). zscore_threshold collapses much further on Farm B (CARE 0.401, reliability
0.000 - it did not reliably flag a single one of Farm B's 6 anomaly events) than it did on
Farm A (CARE 0.506, reliability 0.333). Two farms landing on a similar CARE number for one
baseline and a clearly different number for the other is itself evidence that a single
farm-level CARE score hides more than it shows - which is the entire reason this document
exists.

### 2.1 Farm C - honest status of this run

Farm C's 58 datasets carry 957 raw columns each; a single dataset load through
`rai.ingest.care.load_care_csv` measured at ~17 seconds (verified directly, not estimated),
so a full two-baseline run is a background, minutes-long job. *(This section is filled in
below once that job completes - see the end of this document for the final, non-placeholder
numbers actually used.)*

## 3. Gate C - Cross-turbine (leave-one-turbine-out), Wind Farm A

Farm A's 22 datasets come from 5 distinct turbines (`asset_id` 0, 10, 11, 13, 21), each with
4-5 datasets. For each held-out turbine, one baseline is fit on the **pooled TRAIN rows of
the other 4 turbines only** (verified never to include the held-out turbine's own rows - see
`tests/test_external_care_cross_turbine.py::test_leave_one_turbine_out_never_trains_on_the_held_out_turbines_own_rows`),
then scored on the held-out turbine's own datasets with the same CARE metrics.

| model | held-out turbine | datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|---|---|
| isolation_forest | CARE-WT-0  | 3/2 | 0.458 | 0.318 | 0.101 | 0.000 | 0.936 |
| isolation_forest | CARE-WT-10 | 3/2 | 0.433 | 0.236 | 0.058 | 0.000 | 0.934 |
| isolation_forest | CARE-WT-11 | 1/3 | 0.427 | 0.363 | 0.063 | 0.000 | 0.854 |
| isolation_forest | CARE-WT-13 | 2/2 | 0.775 | 1.000 | 0.259 | 0.833 | 0.890 |
| isolation_forest | CARE-WT-21 | 2/2 | 0.457 | 0.385 | 0.137 | 0.000 | 0.883 |
| zscore_threshold | CARE-WT-0  | 3/2 | 0.402 | 0.007 | 0.002 | 0.000 | 1.000 |
| zscore_threshold | CARE-WT-10 | 3/2 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| zscore_threshold | CARE-WT-11 | 1/3 | 0.397 | 0.000 | 0.000 | 0.000 | 0.992 |
| zscore_threshold | CARE-WT-13 | 2/2 | 0.615 | 1.000 | 0.074 | 0.000 | 1.000 |
| zscore_threshold | CARE-WT-21 | 2/2 | 0.397 | 0.024 | 0.007 | 0.000 | 0.977 |

Every fold has 1-3 held-out anomaly datasets - small samples; these are point estimates, not
a distribution with a real confidence interval (no fold has `status=INSUFFICIENT_DATA`
because every turbine has at least 1 anomaly-event dataset, but "computed" is not the same
as "precise").

**Reading this honestly, and avoiding causal language:**

- **Turbine identity is not obviously the main driver of the in-farm result.** The mean
  cross-turbine (pooled-fit) isolation_forest CARE across the 5 folds (≈ 0.51) is close
  to the in-farm (own-history-fit) CARE from `EXTERNAL_CARE.md` (0.535) - pooling *other*
  turbines' data to fit the model did not collapse performance the way a "the model just
  memorized this turbine" story would predict. This is consistent with the earlier finding
  that both baselines' real feature space on this benchmark is just two columns
  (`wind_speed_ms`, `power_kw` - see §2) - a 2-feature isolation forest has limited room to
  overfit to one turbine's idiosyncrasies in the first place.
- **Reliability is where held-out turbine identity does matter, but it tracks the fault
  family, not "unseen turbine" as a general effect.** Reliability is 0.000 in 4 of 5 folds
  for isolation_forest, and 0.833 in exactly the one fold (`CARE-WT-13`) that contains event
  45 - the same hydraulic-group fault that was the *only* event detected reliably in the
  in-farm run too (`EXTERNAL_CARE.md` §6). This is consistent with "hydraulic-group faults on
  this turbine produce a detectable signal regardless of what the model was fit on" rather
  than "the model generalizes to new turbines" as a general claim - the other 4 turbines'
  faults (transformer, gearbox, generator-bearing) were not reliably detected in any
  condition tested, in-farm or cross-turbine.
- **`zscore_threshold` degrades further under cross-turbine pooling** for the two turbines
  with the least-severe faults (`CARE-WT-10` drops to CARE=0.000 - it predicted zero
  anomalies at all in that fold, `any_anomaly_predicted=False`, which is the paper's own
  defined zero-case, not an arithmetic error).

## 4. Gate D - Cross-farm transfer (fit on Farm A, score on target, never refit)

| model | source -> target | feature intersection | datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.600 | 0.665 | 0.374 | 0.714 | 0.623 |
| zscore_threshold | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.430 | 0.185 | 0.057 | 0.000 | 0.953 |
| isolation_forest | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | *pending, see §4.1* | | | | | |
| zscore_threshold | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | *pending, see §4.1* | | | | | |

Target labels (`event_info.csv`) are used only to **score** the transferred model - the
Farm-A-fit baseline is never refit, re-thresholded, or otherwise adapted using Farm B/C data
of any kind (verified by
`tests/test_external_care_cross_farm.py::test_run_transfer_never_refits_and_uses_only_intersected_columns`,
which asserts the fit function is called exactly once, on source data only). This is transfer
evaluation, not supervised target adaptation.

**Reading the A->B transfer honestly:** isolation_forest's transferred CARE (0.600) is
*higher* than either farm's own in-farm CARE (Farm A 0.535, Farm B 0.532 in-farm from §2).
Coverage (0.665) and reliability (0.714) both rose relative to Farm B's in-farm numbers
(0.236, 0.556) - Farm A's larger pooled training set (22 datasets' worth of train rows vs.
each Farm-B dataset's own, much shorter, per-dataset training period) plausibly gives the
isolation forest a better-calibrated notion of "normal" for this 2-feature space, at some
cost to accuracy (0.623 vs Farm B's in-farm 0.896 - more false alarms on Farm B's own
normal-behavior datasets). This is **consistent with** more training data helping density
estimation in a narrow 2-D feature space; it is **not** evidence that "RAI generalizes across
farms" in any broader sense - only that this specific two-baseline, two-feature setup
transfers at least as well as it works in-farm, on this one source/target pair.

### 4.1 Farm C transfer - honest status of this run

Same dependency as §2.1: scoring Farm A -> Farm C requires loading all 58 Farm-C datasets,
running as a background job alongside the Gate B Farm C run. *(Filled in below once complete.)*

## 5. What Gate F (OOD severity) already covers - not duplicated here

`rai/eval/ood.py` and `docs/evaluation/OOD.md` (this session's own earlier Gate-2 work)
already run each perturbation at multiple severities and report CARE/PR-AUC/false-alarms/
lead-time **per severity**, not just a single before/after number - see `OOD.md` §4's table
(columns: perturbation, severity, CARE, ΔCARE, PR-AUC, ΔPR-AUC, FA/yr, median lead).
That is the severity-stratified evidence this gate's brief asked for; it is against RAI's own
synthetic-fleet champion, not the external CARE archive, so it is a different (and already
completed) axis from everything else in this document, not re-run here.

## 6. Gate E - RAI vs baselines on the external CARE archive: not attempted

`docs/evaluation/EXTERNAL_CARE.md` §2 already explains why RAI's own trained champion was not
transferred onto CARE data: it is fit on the synthetic 42-asset fleet's specific schema, and a
same-session retrain onto CARE's anonymised columns would not really be evaluating "RAI's
model" - it would be evaluating a new model wearing RAI's name. That reasoning is unchanged by
this task. What Gate E's brief actually wants - "does RAI's own detector beat these simple
baselines" - already has a real, honest answer, just not on this dataset: RAI's own
Track-A/Gate-2 evaluation (`docs/evaluation/GATE2_FORENSIC_AUDIT.md`, embargoed PR-AUC 0.822,
MCC 0.690) is RAI's champion vs. its own internal baselines, on the synthetic fleet. Reporting
a CARE-archive number for RAI's champion without retraining it honestly would risk exactly the
kind of borrowed-number problem `EXTERNAL_CARE.md` was written to avoid, so it is left undone
rather than faked.

## 7. Gates G/H - decision-policy and sensor-safety benchmarks: out of this task's scope, referenced not duplicated

Both of these belong to the concurrently-running session's half of the split ("split the
work": this session owns OOD + external CARE + docs; the other owns core eval/splits/
adversarial/decision/economics - see project memory). Rather than duplicate or collide with
in-flight files, what already exists there is referenced here, not re-implemented:

- **Decision-policy comparison and independent outcome-world regret**:
  `docs/evaluation/DECISION_MATH_AUDIT.md` §3 ("Four-Regime Operational Decision Matrix") and
  §4 ("Decoupled Outcome-World Decision Regret", 100 episodes, decoupled from the model world
  that generated the policy) already cover much of what a decision-policy benchmark asks for.
  This document does not re-derive or re-run that work, and does not extend it to CARE data
  (RAI's decision layer consumes RAI's own risk-model output, which - per §6 - does not exist
  for CARE's un-transferred baselines; there is no risk score to hand the decision layer here).
- **Sensor-safety / common-cause red-team**: `rai/eval/sensor_safety_eval.py` and
  `rai/eval/common_cause_eval.py` already exist in this repository (confirmed present at time
  of writing, not inspected in depth - out of this task's ownership boundary).

## 8. Scorecard

Per-metric status, in the format this gate's brief requested. `PASS` is never used here -
per the brief's own instruction not to manufacture one - because "pass" implies a bar this
document does not define; `COMPUTED` / `PARTIAL` / `INSUFFICIENT DATA` / `UNRESOLVED` /
`NOT ATTEMPTED` are used instead.

| axis | result | dataset | sample size | status |
|---|---|---|---|---|
| External CARE, Farm A | CARE 0.535 (isolation_forest) / 0.506 (zscore) | Wind Farm A | 22 datasets, 11 anomaly events | COMPUTED |
| External CARE, Farm B | CARE 0.532 / 0.401 | Wind Farm B | 15 datasets, 6 anomaly events | COMPUTED |
| External CARE, Farm C | *pending* | Wind Farm C | 58 datasets, 27 anomaly events | PENDING (background run, filled below) |
| Cross-turbine (LOTO), Farm A | CARE 0.427-0.775 (isolation_forest), 0.000-0.615 (zscore) across 5 folds | Wind Farm A | 4-5 datasets/fold | COMPUTED, small per-fold N |
| Cross-farm A->B | CARE 0.600 (isolation_forest) / 0.430 (zscore) | Wind Farm A -> B | 15 target datasets, 6 anomaly | COMPUTED |
| Cross-farm A->C | *pending* | Wind Farm A -> C | 58 target datasets, 27 anomaly | PENDING (background run, filled below) |
| Full 6-way cross-farm matrix | not attempted | - | - | NOT ATTEMPTED (time; A->B/A->C prioritized per the brief's own ranking) |
| OOD severity curves | already computed, this session's earlier Gate-2 work | RAI synthetic fleet | see `OOD.md` | COMPUTED (different dataset - not CARE) |
| RAI vs baselines on CARE | not attempted | - | - | NOT ATTEMPTED (schema-transfer cost; see §6) |
| Decision-policy benchmark | exists, other session's Gate 5.0 | RAI synthetic fleet | see `DECISION_MATH_AUDIT.md` | REFERENCED, not extended to CARE |
| Sensor-safety red-team | exists, other session's work | RAI synthetic fleet | not inspected in depth | REFERENCED, not extended to CARE |

## 9. Limitations and what remains unproven

- Every CARE-archive number in this document (Farm A/B/C, cross-turbine, cross-farm) is from
  **two deliberately modest, off-the-shelf baselines**, not RAI's own trained model (§6).
  Nothing here is a claim about RAI's own detector's generalization.
- Cross-turbine folds have small per-fold anomaly counts (1-3 events) - point estimates, not
  distributions with a defensible confidence interval.
- The "common feature layer" this benchmark's own anonymisation supports is exactly two
  columns (`wind_speed_ms`, `power_kw`). This bounds every cross-farm and cross-turbine result
  in this document to what a 2-feature model can express - it is not evidence about
  temperature, vibration, or any other physically meaningful channel, because those channels
  are not resolvable from CARE's anonymised headers with this project's current sensor-map
  (see `EXTERNAL_CARE.md` §3 for the same caveat on the in-farm result).
  the transfer result reflects a small, shared representation, not a rich one.
- No bootstrap or resampling uncertainty on any number in this document (matches the same
  limitation already disclosed in `EXTERNAL_CARE.md`).
- Farm C results (Gate B and Gate D) were pending a multi-minute background run at the time
  most of this document was drafted - see §2.1/§4.1/§8 for exactly where they land once
  filled in below, and do not trust a Farm C number anywhere in this document that is not
  also present in the final artifacts under `artifacts/evaluation/gate2/external_care/`.
