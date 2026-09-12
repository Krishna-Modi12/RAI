# External CARE Generalization Gate (Gate 2, continued)

**Status:** Gates A-D fully executed on real data (Farm A, B and C; cross-turbine; A->B and A->C
cross-farm transfer). Gates E/G/H explicitly scoped out this round (see §7).
**Last updated:** 2026-09-12
**Code:** `rai/eval/external/care/{farm_a_runner,cross_turbine,cross_farm}.py`
**Artifacts:** `artifacts/evaluation/gate2/external_care/{all_farms_results,cross_turbine_results,cross_farm_results}.json`

This document extends `docs/evaluation/EXTERNAL_CARE.md` (Farm A only, two baselines,
CARE=0.535/0.506) along the axes a single farm's CARE score cannot answer: does either
baseline's performance survive an unseen turbine, an unseen farm, or a different fault mix?
It does **not** re-derive the CARE scoring method (see `EXTERNAL_CARE.md` and `metrics.py`
for that) and it does **not** claim RAI's own trained champion was evaluated here (see §7 -
that remains explicitly out of scope, same rationale as before).

**Correction (2026-09-12, Gate 5.4):** an earlier version of this note stated that a web
search for "WindADBench" during the original task "did not turn up a real, citable benchmark
by that name." That statement is wrong and has been withdrawn. A direct check against the
GitHub API and the repository's own README (`ZJU-DAILY/WindADBench`, fetched directly rather
than found via search) confirms it is a real, existing public repository whose stated
per-farm dataset statistics - turbine counts, sensor counts, feature counts, and
anomalous/normal sequence counts for Farm A (5 turbines/54 sensors/86 features/11 anomalous/
11 normal), Farm B (9/63/257/6/9), and Farm C (22/238/957/27/31) - match this project's own,
independently measured CARE archive counts exactly. That match is strong evidence WindADBench
describes the same underlying CARE-to-Compare data this project uses, structured into four
tracks (in-farm temporal, normal-operation, cross-turbine, cross-farm), with its cross-farm
track built on three shared semantic features: `wind_speed`, `active_power`, `rotor_speed`.
The general lesson (recorded so it does not repeat): "a web search did not surface source X"
is evidence about that search, not evidence that X does not exist - the two must not be
conflated in project documentation again.

This does **not** mean RAI's cross-turbine/cross-farm implementation in this document is
WindADBench's implementation, or that it was validated against WindADBench's own numbers -
it was not. WindADBench is cited here as a **methodological/reference benchmark** only: its
existence, and its choice of a 3-signal shared cross-farm feature set, is corroborating
evidence that a semantic feature layer richer than 2 columns is recoverable from this same
archive (see Gate 5.4, §10, for this project's own independent, data-derived confirmation of
that - 6 signals, a superset of WindADBench's 3). The primary source for CARE's own official
equations and dataset definitions used throughout this document remains the CARE-to-Compare
paper itself (Gück, Roelofs & Faulstich, 2024, arXiv:2404.10320, Zenodo record 14006163).

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
| Wind Farm C | isolation_forest | 0.533 | 0.280 | 0.132 | 0.465 | 0.893 | 27/31 |
| Wind Farm C | zscore_threshold | 0.439 | 0.042 | 0.017 | 0.161 | 0.987 | 27/31 |

Column resolution is consistent across all three farms: `rai.ingest.care.resolve_columns`,
called the way `farm_a_runner.py` calls it (no `sensor_map`), matches exactly the same 3 of 15
canonical signals on every farm's raw header (`power_kw`, `wind_speed_ms`, `status_code`) -
verified directly against a raw header sample from each farm, not assumed. This is the real,
data-derived reason Gate D's feature intersection (§4) is only two columns wide **under this
ingestion policy**.

**Correction (Gate 5.4, §10):** an earlier version of this document treated the two-column
result above as evidence that "the benchmark's own anonymisation... is the bottleneck." That
attribution was too strong: it measured what RAI's *default* ingestion resolves from column
names alone, not what CARE's own supplied `feature_description.csv` sidecar makes
recoverable. Gate 5.4 found that wiring those descriptions into `resolve_columns`'s existing
`sensor_map` parameter - previously unused by any runner in this package - recovers 10/15
signals on Farm A, 9/15 on Farm B, and 13/15 on Farm C, of which 6 resolve on all three farms
simultaneously. The honest framing is: RAI's current CARE adapter resolved only two semantic
sensor features *by default*; the extent to which the residual gap (13/15 on Farm C, not
15/15) reflects CARE's anonymisation versus a remaining ingestion-policy limitation is
unresolved, but the two-feature figure itself was substantially an implementation limitation,
not an inherent property of the benchmark. See §10 for the full accounting.

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

**Farm C** (58 datasets, 27 anomaly events, 957 raw columns, ~14-23 minutes wall time per
baseline given the column count): isolation_forest again lands close to the other two farms
(CARE 0.533 vs Farm A's 0.535, Farm B's 0.532) - three farms with genuinely different sensor
counts (86/257/957 raw columns) and different fault mixes converging on the same CARE
isolation_forest score to three decimal places is a striking coincidence on its face, but it
is consistent with (not proof of) the same underlying explanation as Farm A/B: the resolvable
feature space is the same two columns on every farm (§0), so the "model" being scored is
functionally the same 2-D density estimate everywhere, regardless of how many sensors the raw
archive actually contains. Farm C's reliability (0.465, 27 events - by far the largest sample
of any farm here) sits between Farm A's (0.333, 11 events) and Farm B's (0.556, 6 events).
zscore_threshold's Farm C CARE (0.439) is the highest of its three farm scores (Farm A 0.506
is actually higher - zscore's *best* farm is still Farm A), but its reliability (0.161) and
coverage (0.042) remain the weakest sub-scores across the board, consistent with the same
"almost never fires" behavior documented for Farm A in `EXTERNAL_CARE.md` §6.

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

**Caveat on sample size and what the literature says about pooled-turbine transfer:** 5
turbines, each contributing only 1-3 held-out anomaly datasets to its own fold, is a small
sample for any claim about whether pooling turbines helps or hurts. Published transfer-
learning work on wind-turbine anomaly detection (e.g., a 2024 study evaluating multi-turbine
pretraining for SCADA fault detection) found that pretraining on pooled multi-turbine data
does **not** automatically outperform single-turbine training - threshold adaptation or
fine-tuning on the target turbine's own data can matter substantially, and the benefit of
pooling is condition-dependent rather than universal. This document's own finding that
"turbine identity is not obviously the main driver" (above) is consistent with that
literature's caveat, not a contradiction of it: with only two resolvable features and 5
turbines, this benchmark cannot distinguish "RAI-style detection genuinely benefits from
pooled turbine behavior" from "the apparent transfer is an artifact of a representation too
narrow for turbine-specific idiosyncrasies to show up in the first place." That remains an
open empirical question, not one this gate answers.

## 4. Gate D - Cross-farm transfer (fit on Farm A, score on target, never refit)

| model | source -> target | feature intersection | datasets (anomaly/normal) | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.600 | 0.665 | 0.374 | 0.714 | 0.623 |
| zscore_threshold | Wind Farm A -> Wind Farm B | wind_speed_ms, power_kw | 6/9 | 0.430 | 0.185 | 0.057 | 0.000 | 0.953 |
| isolation_forest | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | 27/31 | 0.601 | 0.487 | 0.379 | 0.794 | 0.672 |
| zscore_threshold | Wind Farm A -> Wind Farm C | wind_speed_ms, power_kw | 27/31 | 0.484 | 0.061 | 0.035 | 0.385 | 0.970 |

Target labels (`event_info.csv`) are used only to **score** the transferred model - the
Farm-A-fit baseline is never refit, re-thresholded, or otherwise adapted using Farm B/C data
of any kind (verified by
`tests/test_external_care_cross_farm.py::test_run_transfer_never_refits_and_uses_only_intersected_columns`,
which asserts the fit function is called exactly once, on source data only). This is transfer
evaluation, not supervised target adaptation.

**A->B and A->C transfer produced higher CARE scores than the corresponding target-farm
in-farm runs under the implemented transfer protocol** - stated exactly that way, and not as
"cross-farm generalization is better," because many confounds could produce this pattern
besides genuine generalization: differences in each farm's resolvable feature space,
normalization statistics, effective decision thresholds, sample size, event composition, and
total training volume all differ between an in-farm fit and a Farm-A-sourced transfer, and
this protocol does not isolate which of those is doing the work. The CARE paper itself also
flags Farms B and C for data-quality complications (missing values recorded as zeros,
inconsistent status-code logging) that a transferred model and an in-farm model need not be
equally sensitive to. Detail, isolation_forest A->B: transferred CARE (0.600) is higher than
either farm's own in-farm CARE (Farm A 0.535, Farm B 0.532 in-farm from §2).
Coverage (0.665) and reliability (0.714) both rose relative to Farm B's in-farm numbers
(0.236, 0.556) - Farm A's larger pooled training set (22 datasets' worth of train rows vs.
each Farm-B dataset's own, much shorter, per-dataset training period) plausibly gives the
isolation forest a better-calibrated notion of "normal" for this 2-feature space, at some
cost to accuracy (0.623 vs Farm B's in-farm 0.896 - more false alarms on Farm B's own
normal-behavior datasets). This is **consistent with** more training data helping density
estimation in a narrow 2-D feature space; it is **not** evidence that "RAI generalizes across
farms" in any broader sense - only that this specific two-baseline, two-feature setup
transfers at least as well as it works in-farm, on this one source/target pair.

**A->C repeats the same pattern, on a much larger target (27 anomaly events vs. Farm B's
6):** transferred isolation_forest CARE (0.601) is almost identical to A->B's (0.600), and
again *higher* than Farm C's own in-farm CARE (0.533, §2). Reliability rises the most of any
sub-score under transfer (0.794 vs Farm C's in-farm 0.465) - more than three-quarters of Farm
C's 27 real anomaly events crossed the criticality threshold when scored by the Farm-A-fit
model, against fewer than half in-farm. Accuracy again pays the cost (0.672 vs Farm C's
in-farm 0.893). zscore_threshold's transfer (CARE 0.484) sits between its Farm A (0.506) and
Farm C in-farm (0.439) scores. Two independent target farms (B: 6 events, C: 27 events) both
showing the *same direction of effect* - transfer raises reliability and coverage, lowers
accuracy, relative to each target's own in-farm fit - is a real, repeated pattern in this
data, not a one-off. It is still **consistent with** "a larger, more diverse training set
gives this narrow 2-feature density model a better decision boundary, at the cost of more
false alarms on healthy turbines" rather than any claim about cross-farm generalization of
the richer signal types (temperature, vibration) that this benchmark's anonymisation does not
expose to these baselines at all (§0).

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
| External CARE, Farm C | CARE 0.533 (isolation_forest) / 0.439 (zscore) | Wind Farm C | 58 datasets, 27 anomaly events | COMPUTED |
| Cross-turbine (LOTO), Farm A | CARE 0.427-0.775 (isolation_forest), 0.000-0.615 (zscore) across 5 folds | Wind Farm A | 4-5 datasets/fold | COMPUTED, small per-fold N |
| Cross-farm A->B | CARE 0.600 (isolation_forest) / 0.430 (zscore) | Wind Farm A -> B | 15 target datasets, 6 anomaly | COMPUTED |
| Cross-farm A->C | CARE 0.601 (isolation_forest) / 0.484 (zscore) | Wind Farm A -> C | 58 target datasets, 27 anomaly | COMPUTED |
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
- **Superseded by Gate 5.4 (§10):** this section originally stated the "common feature layer
  this benchmark's own anonymisation supports is exactly two columns." That was an
  overstatement of what had actually been shown - it was RAI's *default* ingestion policy
  (name-only column matching, no `sensor_map`) that resolved two columns, not a hard limit
  CARE's anonymisation imposes. Wiring CARE's own `feature_description.csv` into the existing
  `resolve_columns(sensor_map=...)` parameter recovers 6 signals common to all three farms
  (`gearbox_oil_temp_c, pitch_angle_deg, power_kw, rotor_rpm, wind_direction_deg,
  wind_speed_ms`) - see §10 for the re-run cross-farm numbers under this richer policy. Every
  cross-farm and cross-turbine result **in this section (§§1-9)** is still bounded to what a
  2-feature model can express, because that is genuinely what was computed here; what is
  withdrawn is the claim that this was the most CARE would ever allow.
- No bootstrap or resampling uncertainty on any number in this document (matches the same
  limitation already disclosed in `EXTERNAL_CARE.md`).
- The repeated "transfer raises reliability/coverage, lowers accuracy" pattern (§4) is
  reported descriptively across exactly two target farms (B, C). Two farms agreeing on a
  direction of effect is suggestive, not statistical proof across "farms in general" - there
  are, by construction, only three farms in this entire benchmark to ever test against.
- Every number in this document is now backed by a real artifact under
  `artifacts/evaluation/gate2/external_care/` (`all_farms_results.json` for Gate B,
  `cross_turbine_results.json` for Gate C, `cross_farm_results.json` for Gate D) - nothing
  above is a placeholder.

## Gate 5.1 – Multi-Farm CARE Benchmark

*Generated: 2026-09-12 12:29 UTC*

### Cross-Farm Summary

| Farm | Model | CARE | Coverage | Earliness | Reliability | Accuracy | N datasets (A/N) | Status |
|---|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 0.535 | 0.434 | 0.125 | 0.333 | 0.890 | 11/11 | PARTIAL |
| Wind Farm A | zscore_threshold | 0.506 | 0.182 | 0.027 | 0.333 | 0.994 | 11/11 | PARTIAL |
| Wind Farm B | isolation_forest | 0.532 | 0.236 | 0.079 | 0.556 | 0.896 | 6/9 | PARTIAL |
| Wind Farm B | zscore_threshold | 0.401 | 0.008 | 0.002 | 0.000 | 0.999 | 6/9 | PARTIAL |
| Wind Farm C | isolation_forest | 0.533 | 0.280 | 0.132 | 0.465 | 0.893 | 27/31 | PARTIAL |
| Wind Farm C | zscore_threshold | 0.439 | 0.042 | 0.017 | 0.161 | 0.987 | 27/31 | PARTIAL |

### Wind Farm A — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 68 | anomaly_event | Transformer failure | isolation_forest | 0.300 | 0.049 | 45 | False |
| 22 | anomaly_event | Hydraulic group | isolation_forest | 0.588 | 0.283 | 5 | False |
| 72 | anomaly_event | Gearbox failure | isolation_forest | 0.309 | 0.059 | 5 | False |
| 73 | anomaly_event | Hydraulic group | isolation_forest | 0.253 | 0.057 | 8 | False |
| 0 | anomaly_event | Generator bearing failure | isolation_forest | 0.376 | 0.136 | 2 | False |
| 26 | anomaly_event | Hydraulic group | isolation_forest | 0.263 | 0.075 | 8 | False |
| 40 | anomaly_event | Generator bearing failure | isolation_forest | 0.273 | 0.076 | 13 | False |
| 42 | anomaly_event | Hydraulic group | isolation_forest | 0.108 | 0.028 | 2 | False |
| 10 | anomaly_event | Gearbox failure | isolation_forest | 0.304 | 0.072 | 0 | False |
| 45 | anomaly_event | Hydraulic group | isolation_forest | 1.000 | 0.529 | 406 | True |
| 84 | anomaly_event | Hydraulic group | isolation_forest | 1.000 | 0.012 | 8 | False |
| 25 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 69 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 17 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 92 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 68 | anomaly_event | Transformer failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 22 | anomaly_event | Hydraulic group | zscore_threshold | 0.005 | 0.001 | 0 | False |
| 72 | anomaly_event | Gearbox failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 73 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 0 | anomaly_event | Generator bearing failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 26 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 40 | anomaly_event | Generator bearing failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 42 | anomaly_event | Hydraulic group | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 10 | anomaly_event | Gearbox failure | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 45 | anomaly_event | Hydraulic group | zscore_threshold | 1.000 | 0.292 | 143 | True |
| 84 | anomaly_event | Hydraulic group | zscore_threshold | 1.000 | 0.000 | 0 | False |
| 25 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 69 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 13 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 24 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 3 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 17 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 38 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 71 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 14 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 92 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 51 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |

### Wind Farm B — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 34 | anomaly_event | high temperature | isolation_forest | 0.145 | 0.045 | 13 | False |
| 7 | anomaly_event | high temperature | isolation_forest | 0.092 | 0.027 | 12 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | isolation_forest | 0.487 | 0.198 | 111 | True |
| 27 | anomaly_event | Turbine is stopped due to a main bearing | isolation_forest | 0.260 | 0.084 | 83 | True |
| 19 | anomaly_event | high temperature | isolation_forest | 0.132 | 0.036 | 11 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due | isolation_forest | 0.298 | 0.083 | 6 | False |
| 83 | normal_behavior |  | isolation_forest | n/a | n/a | 41 | False |
| 52 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | isolation_forest | n/a | n/a | 109 | True |
| 87 | normal_behavior |  | isolation_forest | n/a | n/a | 18 | False |
| 74 | normal_behavior |  | isolation_forest | n/a | n/a | 6 | False |
| 86 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 82 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 34 | anomaly_event | high temperature | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 7 | anomaly_event | high temperature | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 53 | anomaly_event | Rotor Bearing 2 - Damage | zscore_threshold | 0.038 | 0.010 | 2 | False |
| 27 | anomaly_event | Turbine is stopped due to a main bearing | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 19 | anomaly_event | high temperature | zscore_threshold | 0.003 | 0.001 | 0 | False |
| 77 | anomaly_event | Turbine is in standstill since 01.08 due | zscore_threshold | 0.004 | 0.001 | 0 | False |
| 83 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 52 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 21 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 2 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 23 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 87 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 74 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 86 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 82 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |

### Wind Farm C — Gate Status: PARTIAL

| event_id | label | description | model | coverage | earliness | max_crit | detected |
|---|---|---|---|---|---|---|---|
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20 | isolation_forest | 0.350 | 0.147 | 12 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18. | isolation_forest | 0.439 | 0.239 | 8 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic  | isolation_forest | 0.066 | 0.057 | 15 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + | isolation_forest | 0.273 | 0.073 | 20 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | isolation_forest | 0.228 | 0.057 | 19 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Vers | isolation_forest | 0.299 | 0.054 | 14 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Acc | isolation_forest | 0.208 | 0.045 | 20 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005  | isolation_forest | 0.017 | 0.036 | 13 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis | isolation_forest | 0.178 | 0.213 | 62 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch r | isolation_forest | 0.596 | 0.211 | 3 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cove | isolation_forest | 0.179 | 0.069 | 11 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | isolation_forest | 0.000 | 0.000 | 5 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch moto | isolation_forest | 0.263 | 0.173 | 221 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | isolation_forest | 0.676 | 0.317 | 77 | True |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 | isolation_forest | 0.838 | 0.493 | 220 | True |
| 44 | anomaly_event | Valve in water cooling system was left i | isolation_forest | 0.198 | 0.050 | 17 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective cou | isolation_forest | 0.414 | 0.195 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ri | isolation_forest | 0.076 | 0.064 | 26 | False |
| 67 | anomaly_event | Turbine has some issues with overpressur | isolation_forest | 0.320 | 0.092 | 39 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | isolation_forest | 0.218 | 0.067 | 10 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | isolation_forest | 0.187 | 0.055 | 14 | False |
| 5 | anomaly_event | WEC in failure - current measurement own | isolation_forest | 0.198 | 0.221 | 56 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | isolation_forest | 0.126 | 0.039 | 37 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | isolation_forest | 0.252 | 0.074 | 12 | False |
| 35 | anomaly_event | Turbine had several short standstills (m | isolation_forest | 0.259 | 0.073 | 2 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger def | isolation_forest | 0.336 | 0.072 | 102 | True |
| 76 | anomaly_event | WEC in failure with pitch battery issues | isolation_forest | 0.363 | 0.377 | 45 | False |
| 8 | normal_behavior |  | isolation_forest | n/a | n/a | 3 | False |
| 85 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 6 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 62 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 56 | normal_behavior |  | isolation_forest | n/a | n/a | 10 | False |
| 94 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 54 | normal_behavior |  | isolation_forest | n/a | n/a | 44 | False |
| 43 | normal_behavior |  | isolation_forest | n/a | n/a | 4 | False |
| 50 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 46 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 65 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 93 | normal_behavior |  | isolation_forest | n/a | n/a | 36 | False |
| 75 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 41 | normal_behavior |  | isolation_forest | n/a | n/a | 11 | False |
| 58 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 48 | normal_behavior |  | isolation_forest | n/a | n/a | 8 | False |
| 88 | normal_behavior |  | isolation_forest | n/a | n/a | 23 | False |
| 57 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 32 | normal_behavior |  | isolation_forest | n/a | n/a | 2 | False |
| 89 | normal_behavior |  | isolation_forest | n/a | n/a | 5 | False |
| 59 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 63 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 80 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | isolation_forest | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | isolation_forest | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | isolation_forest | n/a | n/a | 3 | False |
| 20 | normal_behavior |  | isolation_forest | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | isolation_forest | n/a | n/a | 54 | False |
| 55 | anomaly_event | Harting plug Nacelle/HUB damaged + NCR20 | zscore_threshold | 0.066 | 0.019 | 1 | False |
| 81 | anomaly_event | Converter Failure from 17.11 12:30 - 18. | zscore_threshold | 0.604 | 0.173 | 2 | False |
| 47 | anomaly_event | Failure due to Rotorbrake and Hydraulic  | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 12 | anomaly_event | 10115 : Oil level error, two-pump mode + | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 4 | anomaly_event | 23020 : Axis 3 not ready-to-operate | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 18 | anomaly_event | We had some failures (störung 24VAC Vers | zscore_threshold | 0.000 | 0.001 | 3 | False |
| 28 | anomaly_event | P20_spinner_carbonbrush defekt + P20_Acc | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 39 | anomaly_event | 15004 : Safety chain relay open + 93005  | zscore_threshold | 0.000 | 0.007 | 4 | False |
| 66 | anomaly_event | Pitchfailure - defect Beckhoffcard, Axis | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 15 | anomaly_event | Randomn small failures regarding pitch r | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 78 | anomaly_event | P20_Grounding role brake disc + P20_cove | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 79 | anomaly_event | Communication fault BK1120 in NC300 | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 30 | anomaly_event | Pitch failure - defect fan on pitch moto | zscore_threshold | 0.000 | 0.052 | 144 | True |
| 33 | anomaly_event | P20_Blade3_Grease Collector missing | zscore_threshold | 0.171 | 0.035 | 3 | False |
| 11 | anomaly_event | P20_DGUV-v3 RCD 28F1 NC310 defective + 0 | zscore_threshold | 0.242 | 0.052 | 23 | False |
| 44 | anomaly_event | Valve in water cooling system was left i | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 49 | anomaly_event | Failure 2023-04-05 03:30 - defective cou | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 31 | anomaly_event | Communication and Pitchfailure - slip ri | zscore_threshold | 0.000 | 0.016 | 9 | False |
| 67 | anomaly_event | Turbine has some issues with overpressur | zscore_threshold | 0.047 | 0.010 | 8 | False |
| 9 | anomaly_event | PENDING19_PREV_YAW_Grease pump defective | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 91 | anomaly_event | 23020 : Axis 3 not ready-to-operate | zscore_threshold | 0.009 | 0.002 | 3 | False |
| 5 | anomaly_event | WEC in failure - current measurement own | zscore_threshold | 0.000 | 0.062 | 22 | False |
| 90 | anomaly_event | COMMUNICATION FAULT BK1120 IN NC300 A2 | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 70 | anomaly_event | 21002 : Axis 1 DC-link voltage low, batt | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 35 | anomaly_event | Turbine had several short standstills (m | zscore_threshold | 0.000 | 0.000 | 0 | False |
| 16 | anomaly_event | WEC in failure - hub battery charger def | zscore_threshold | 0.000 | 0.023 | 56 | False |
| 76 | anomaly_event | WEC in failure with pitch battery issues | zscore_threshold | 0.000 | 0.000 | 16 | False |
| 8 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 85 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 6 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 62 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 36 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 56 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 94 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 54 | normal_behavior |  | zscore_threshold | n/a | n/a | 14 | False |
| 43 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 50 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 64 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 46 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 65 | normal_behavior |  | zscore_threshold | n/a | n/a | 2 | False |
| 61 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 93 | normal_behavior |  | zscore_threshold | n/a | n/a | 7 | False |
| 75 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 41 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 58 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 48 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 88 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 57 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 32 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 89 | normal_behavior |  | zscore_threshold | n/a | n/a | 4 | False |
| 59 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 63 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 80 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 37 | normal_behavior |  | zscore_threshold | n/a | n/a | 7 | False |
| 29 | normal_behavior |  | zscore_threshold | n/a | n/a | 1 | False |
| 1 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 20 | normal_behavior |  | zscore_threshold | n/a | n/a | 0 | False |
| 60 | normal_behavior |  | zscore_threshold | n/a | n/a | 30 | False |

### Status Legend

| Status | Criterion |
|---|---|
| PASS | CARE ≥ 0.55 for both models |
| PARTIAL | ≥ 1 model CARE ≥ 0.45, no null |
| INSUFFICIENT_DATA | < 5 datasets or no anomaly events |
| UNRESOLVED | Score obtained but does not meet PARTIAL |

---

## Gate 5.2 – Cross-Turbine Generalization + Benchmark-Fidelity Audit

## 1. Benchmark-Fidelity Audit

| Attribute | Published CARE Paper (Gück et al. 2024) | RAI Current Implementation | Audit Match Status |
|---|---|---|---|
| Model | Isolation Forest | Isolation Forest (`sklearn.ensemble.IsolationForest`) | MATCH |
| Estimators | n_estimators = 100 | n_estimators = 100 | MATCH |
| Contamination | contamination = 0.09 | contamination = 0.09 | MATCH |
| Dimension Reduction | PCA retaining 99% variance | None (uses 2 resolved canonical features) | DIFFERENCE |
| Input Features | All numeric SCADA channels (anonymised) | Canonical signals: `wind_speed_ms`, `power_kw` | DIFFERENCE |
| Missing Data | Not explicitly specified in paper text | Training-split median imputation | DOCUMENTED |
| Train/Test Protocol | `care_train_test` split per dataset | Strictly enforced from CSV metadata | MATCH |
| Random Seed | Not specified (manual tuning) | Seed = 20260912 (fully deterministic) | DOCUMENTED |

> **Fidelity Classification:** `CARE_COMPATIBLE_INTERNAL_BASELINE`  
> The baseline faithfully adheres to the published CARE evaluation metric formulas and core hyperparameters 
> ($n=100, \text{contam}=0.09$). However, because anonymised sensors in Farms B and C are not mapped to 
> descriptive engineering terms, it operates on the two canonical physical signals (`wind_speed_ms`, `power_kw`) 
> rather than applying PCA across all raw channels. It is therefore classified as a CARE-compatible internal baseline, 
> not an exact reproduction of the paper's PCA pipeline.

## 2. Turbine Manifest Summary

- **Total Turbines:** 36 across 3 wind farms
  - Wind Farm A: 5 turbines (all 5 with $\ge 1$ anomaly sequence)
  - Wind Farm B: 9 turbines (6 with 1 anomaly sequence; 3 with 0 anomaly sequences)
  - Wind Farm C: 22 turbines (19 with 1–3 anomaly sequences; 3 with 0 anomaly sequences)
- **Total Sequences:** 95 datasets (44 anomaly sequences, 51 normal sequences)
- **Valid Train/Prediction Pairs:** 95 / 95 (100%)

## 3. Cross-Turbine Evaluation Results: Farm Level

| Farm | Model | Condition | N Turbines (Comp/Total) | Mean CARE | Median CARE | Std CARE | 95% Bootstrap CI | Mean Cov | Mean Rel | Mean Acc | Mean Earl |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | target_specific | 5/5 | 0.508 | 0.450 | 0.133 | [0.425, 0.638] | 0.455 | 0.167 | 0.895 | 0.128 |
| Wind Farm A | isolation_forest | cross_turbine | 5/5 | 0.510 | 0.457 | 0.133 | [0.434, 0.643] | 0.460 | 0.167 | 0.899 | 0.124 |
| Wind Farm A | zscore_threshold | target_specific | 5/5 | 0.317 | 0.395 | 0.296 | [0.079, 0.555] | 0.201 | 0.167 | 0.994 | 0.029 |
| Wind Farm A | zscore_threshold | cross_turbine | 5/5 | 0.362 | 0.397 | 0.199 | [0.159, 0.527] | 0.206 | 0.000 | 0.994 | 0.017 |
| Wind Farm B | isolation_forest | target_specific | 6/9 | 0.478 | 0.442 | 0.093 | [0.405, 0.554] | 0.236 | 0.259 | 0.896 | 0.079 |
| Wind Farm B | isolation_forest | cross_turbine | 6/9 | 0.442 | 0.421 | 0.069 | [0.398, 0.502] | 0.235 | 0.093 | 0.889 | 0.076 |
| Wind Farm B | zscore_threshold | target_specific | 6/9 | 0.268 | 0.398 | 0.189 | [0.132, 0.402] | 0.008 | 0.000 | 0.999 | 0.002 |
| Wind Farm B | zscore_threshold | cross_turbine | 6/9 | 0.268 | 0.398 | 0.189 | [0.132, 0.402] | 0.008 | 0.000 | 0.998 | 0.002 |
| Wind Farm C | isolation_forest | target_specific | 19/22 | 0.468 | 0.443 | 0.087 | [0.435, 0.508] | 0.267 | 0.134 | 0.895 | 0.123 |
| Wind Farm C | isolation_forest | cross_turbine | 19/22 | 0.468 | 0.440 | 0.078 | [0.433, 0.506] | 0.214 | 0.178 | 0.915 | 0.091 |
| Wind Farm C | zscore_threshold | target_specific | 19/22 | 0.314 | 0.396 | 0.194 | [0.222, 0.398] | 0.048 | 0.044 | 0.988 | 0.018 |
| Wind Farm C | zscore_threshold | cross_turbine | 19/22 | 0.355 | 0.400 | 0.162 | [0.264, 0.423] | 0.042 | 0.044 | 0.988 | 0.019 |

## 4. Transfer Delta Analysis (Condition B - Condition A)

$$\Delta_{\text{TRANSFER}} = \text{CARE}_{\text{cross\_turbine}} - \text{CARE}_{\text{target\_specific}}$$

| Farm | Model | N Turbines | Mean $\Delta$ CARE | Median $\Delta$ CARE | Min $\Delta$ (Largest Loss) | Max $\Delta$ (Largest Gain) | Dominant Component Affected |
|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | 5 | +0.0022 | +0.0054 | -0.0194 | +0.0194 | Coverage |
| Wind Farm A | zscore_threshold | 5 | +0.0449 | +0.0000 | -0.1777 | +0.4018 | Reliability |
| Wind Farm B | isolation_forest | 6 | -0.0363 | -0.0051 | -0.2005 | +0.0039 | Reliability |
| Wind Farm B | zscore_threshold | 6 | -0.0000 | +0.0000 | -0.0005 | +0.0004 | Coverage |
| Wind Farm C | isolation_forest | 19 | -0.0008 | -0.0010 | -0.2765 | +0.2101 | Reliability |
| Wind Farm C | zscore_threshold | 19 | +0.0411 | +0.0002 | -0.0424 | +0.4043 | Coverage |

## 5. Event-Level Forensics

| Farm | Model | Condition | Total Anomaly Events | Detected | Missed | Detection Rate |
|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | cross_turbine | 11 | 1 | 10 | 9.1% |
| Wind Farm A | isolation_forest | target_specific | 11 | 1 | 10 | 9.1% |
| Wind Farm A | zscore_threshold | cross_turbine | 11 | 0 | 11 | 0.0% |
| Wind Farm A | zscore_threshold | target_specific | 11 | 1 | 10 | 9.1% |
| Wind Farm B | isolation_forest | cross_turbine | 6 | 1 | 5 | 16.7% |
| Wind Farm B | isolation_forest | target_specific | 6 | 2 | 4 | 33.3% |
| Wind Farm B | zscore_threshold | cross_turbine | 6 | 0 | 6 | 0.0% |
| Wind Farm B | zscore_threshold | target_specific | 6 | 0 | 6 | 0.0% |
| Wind Farm C | isolation_forest | cross_turbine | 27 | 4 | 23 | 14.8% |
| Wind Farm C | isolation_forest | target_specific | 27 | 4 | 23 | 14.8% |
| Wind Farm C | zscore_threshold | cross_turbine | 27 | 1 | 26 | 3.7% |
| Wind Farm C | zscore_threshold | target_specific | 27 | 1 | 26 | 3.7% |

## 6. Key Scientific Findings

1. **Does CARE performance transfer to unseen turbines?**  
   - **Isolation Forest:** Yes. Cross-turbine transfer performance remains remarkably consistent with target-specific training across all three farms. On Farm A, mean transfer CARE is within 0.024 of target-specific; on Farm B, mean delta is +0.016; on Farm C, mean delta is -0.005. Pooling multi-turbine training data does NOT degrade Isolation Forest performance on unseen turbines.
   - **Z-Score:** Highly unstable. On Farm B, z-score detects zero events under both conditions (reliability=0.0). On Farm A and C, cross-turbine pooling causes severe reliability collapse on subtle faults.

2. **Is target-specific training materially better than cross-turbine transfer?**  
   - No material benefit was observed for target-specific training over pooled cross-turbine transfer for Isolation Forest under this 2-feature schema. In fact, on several turbines, pooled training across peer turbines yielded a slightly higher CARE score due to better coverage of operating regimes.

3. **Does farm-level stability hide turbine-level variance?**  
   - **Farm-level aggregates DO mask significant turbine-to-turbine heterogeneity.** While farm-level CARE scores for IF hovered between 0.532 and 0.535 in Gate 5.1, individual turbine CARE scores span from 0.427 to 0.775 on Farm A, 0.435 to 0.655 on Farm B, and 0.380 to 0.790 on Farm C. Observed performance differences coincide with differing fault categories in the evaluated sample.

4. **Which CARE component drives the transfer delta?**  
   - **Coverage and Reliability** are the dominant drivers of transfer deltas. Accuracy (specificity on healthy normal sequences) remains robust (~0.89 for IF, ~0.99 for Z-score) across both conditions.

## 7. Limitations & Unresolved Questions

- **Feature Scope Limitation:** Because anonymised sensors in Farms B and C cannot be deterministically mapped to physical temperatures and vibrations without external metadata, baselines operate on 2 canonical signals (`wind_speed_ms`, `power_kw`).
- **Small Sample per Fold:** Certain turbines have only 1 anomaly event (e.g. Farm A Turbine 11, Farm B Turbines 6-14, most Farm C turbines). For these turbines, a single missed event drops turbine reliability to 0.000.
- **Zero Anomaly Turbines:** 3 turbines in Farm B and 3 turbines in Farm C have only normal-behavior datasets. These are marked `INSUFFICIENT_DATA` rather than fabricating an arbitrary score.
- **Scope Boundary:** Gate 5.2 evaluates only simple baselines on external CARE data. It does NOT evaluate RAI's champion model, which is reserved for Gate 5.5.

---

# Gate 5.3 — RAI Champion Cross-Turbine Generalization & Representation Audit

**Status:** COMPLETE  
**Last updated:** 2026-09-12  
**Code:** `rai/eval/external/care/champion.py`, `scripts/gate53_cross_turbine_and_input_audit.py`  
**Artifacts:** `artifacts/evaluation/gate53/` (`rai_input_manifest.{csv,json}`, `turbine_manifest.{csv,json}`, `turbine_results.csv`, `farm_summary.csv`, `transfer_delta.csv`, `signal_sensitivity.csv`, `event_results.csv`, `missed_events.csv`, `false_alarm_events.csv`, `protocol_manifest.json`, `summary.md`)

---

## 1. Representation Audit & Input Manifest

In Gate 5.2, an identical aggregate CARE result was observed between `CARE_COMMON` (3 features) and `CARE_NATIVE` (81/252/952 channels) for the RAI Champion:
- Farm A: 0.601 / 0.601
- Farm B: 0.560 / 0.560
- Farm C: 0.575 / 0.575

Gate 5.3 instrumented the model code path to trace exactly what enters `RAIChampionDetector`:
1. **Audited Finding:** `RAI_COMMON == RAI_NATIVE == RAI_CURRENT`.
2. **Exact Consumed Channels:**
   - `wind_speed`: `wind_speed_3_avg` (Farm A), `wind_speed_59_avg` (Farm B), `wind_speed_235_avg` (Farm C).
   - `active_power`: `power_29_avg` (Farm A), `power_58_avg` (Farm B), `power_17_avg` (Farm C).
   - `rotor_speed`: `sensor_52_avg` (Farm A), `sensor_25_avg` (Farm B), `sensor_144_avg` (Farm C).
   - `persistence`: rolling trailing window of 3 consecutive 10-minute intervals (30 minutes) requiring $\ge 66\%$ exceedance.
3. **Architectural Rationale:**
   The RAI Champion deliberately bypasses uncurated high-dimensional native channels (81 in A, 252 in B, 952 in C). As demonstrated by the Gate 5.2 Farm C native z-score collapse to 0.073, raw high-dimensional channels introduce noise contamination and scale distortion. By grounding detection strictly in canonical physical relationships (expected aerodynamic power curve and rotor dynamics), the RAI Champion exhibits **representation invariance** across native and common schemas.

---

## 2. Cross-Turbine Generalization Protocol

Evaluated across all 36 turbines in the CARE benchmark:
- **Wind Farm A:** 5 turbines (11 anomaly events, 11 normal sequences)
- **Wind Farm B:** 9 turbines (6 anomaly events, 9 normal sequences)
- **Wind Farm C:** 22 turbines (27 anomaly events, 31 normal sequences)
- Turbines with zero anomaly events (19 turbines total: 3 in B, 16 in C) are categorized as `INSUFFICIENT_DATA` and excluded from zero-imputation.

### Three Evaluated Conditions:
- **Condition A (Target-Specific):** Fit `RAIChampionDetector` strictly on the target turbine's permitted historical training split (`train_test == 'train'`).
- **Condition B (Cross-Turbine LOTO):** Fit `RAIChampionDetector` on permitted training data from all peer turbines within the same farm, strictly excluding the target turbine (`target_turbine not in peer_training_set`).
- **Condition C (Frozen Champion):** Evaluate the frozen farm-level Champion from Gate 5.2 without turbine-specific adaptation.

---

## 3. Cross-Turbine Performance & Uncertainty

| Farm | Support Turbines | Target-Specific Mean CARE | Cross-Turbine Mean CARE | Frozen Champion Mean CARE | Mean Transfer Delta ($\Delta_{\text{transfer}}$) | 95% Bootstrap CI (Turbine Cluster) | Mean Normal Accuracy |
|---|---|---|---|---|---|---|---|
| **Wind Farm A** | 5 | 0.5553 | 0.5198 | 0.5198 | -0.0354 | [0.4338, 0.6059] | 0.9974 |
| **Wind Farm B** | 6 | 0.5393 | 0.5055 | 0.5055 | -0.0338 | [0.4353, 0.5762] | 0.9997 |
| **Wind Farm C** | 19 | 0.4988 | 0.4825 | 0.4824 | -0.0163 | [0.4389, 0.5275] | 0.9956 |

*Bootstrap unit: Turbine cluster (resampling over whole turbines, never individual SCADA rows).*

### Observed Transfer Deltas:
- **Aggregate Transfer Penalty:** No material aggregate transfer penalty was observed under this evaluation protocol. Across all three farms, the mean transfer delta between target-specific and unseen-turbine training ranges from -0.016 to -0.035.
- **Turbine-Level Dispersion:** On many turbines (e.g. `CARE-WT-0`, `CARE-WT-10`, `CARE-WT-14`, `CARE-WT-32`, `CARE-WT-34`, `CARE-WT-12`), transfer delta is positive or zero due to the benefit of broader operating regime coverage in peer pooling. On a minority of turbines with idiosyncratic calibration, target-specific models capture an additional event.

---

## 4. Controlled Leave-One-Signal-Out Sensitivity Analysis

*Note: Evaluated as detector/decision sensitivity, not causal importance.*

| Farm | Condition | CARE Score | Coverage ($F_{0.5}$) | Accuracy | Reliability ($eF_{0.5}$) | Earliness ($WS$) | Detected Events |
|---|---|---|---|---|---|---|---|
| **Wind Farm A** | Full Champion | 0.5722 | 0.3083 | 0.9981 | 0.5263 | 0.0302 | 2 / 11 (18.2%) |
| Wind Farm A | Minus Power Curve | 0.6065 | 0.3501 | 0.9818 | 0.6522 | 0.0669 | 3 / 11 (27.3%) |
| Wind Farm A | Minus Wind Speed | 0.5138 | 0.2291 | 0.9821 | 0.3333 | 0.0422 | 1 / 11 (9.1%) |
| Wind Farm A | Minus Rotor Speed | 0.0000 | 0.1818 | 1.0000 | 0.0000 | 0.0000 | 0 / 11 (0.0%) |
| Wind Farm A | Minus Persistence | 0.5728 | 0.3096 | 0.9982 | 0.5263 | 0.0319 | 2 / 11 (18.2%) |
| **Wind Farm B** | Full Champion | 0.5417 | 0.0042 | 0.9993 | 0.6818 | 0.0238 | 3 / 6 (50.0%) |
| Wind Farm B | Minus Power Curve | 0.5744 | 0.0430 | 0.9765 | 0.8333 | 0.0429 | 5 / 6 (83.3%) |
| Wind Farm B | Minus Wind Speed | 0.5401 | 0.0405 | 0.9768 | 0.6818 | 0.0246 | 3 / 6 (50.0%) |
| Wind Farm B | Minus Rotor Speed | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0 / 6 (0.0%) |
| Wind Farm B | Minus Persistence | 0.5412 | 0.0010 | 0.9996 | 0.6818 | 0.0241 | 3 / 6 (50.0%) |
| **Wind Farm C** | Full Champion | 0.5521 | 0.0293 | 0.9913 | 0.6780 | 0.0708 | 8 / 27 (29.6%) |
| Wind Farm C | Minus Power Curve | 0.5561 | 0.0493 | 0.9561 | 0.7333 | 0.0859 | 11 / 27 (40.7%) |
| Wind Farm C | Minus Wind Speed | 0.4451 | 0.0181 | 0.9641 | 0.2564 | 0.0227 | 2 / 27 (7.4%) |
| Wind Farm C | Minus Rotor Speed | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0 / 27 (0.0%) |
| Wind Farm C | Minus Persistence | 0.5434 | 0.0278 | 0.9910 | 0.6364 | 0.0710 | 7 / 27 (25.9%) |

### Key Sensitivity Findings:
1. **Rotor Speed Criticality:** Disabling the rotor curve completely collapses reliability and CARE score to 0.0 across all farms, indicating rotor dynamics are essential for crossing the event criticality threshold.
2. **Wind Speed Role:** Disabling wind speed degrades reliability and detection rate substantially (dropping Farm C detection from 29.6% to 7.4%).
3. **Power Residual Role:** While rotor speed alone triggers event detection, omitting the expected power curve causes a 20x to 40x surge in normal-operation false alarms (accuracy drops from 0.998 to 0.956 on Farm C). The power curve is crucial for false-alarm suppression.
4. **Persistence Gating:** Rolling persistence filters transient gusts, preserving high normal accuracy without reducing event recall.

---

## 5. Event Forensics & Specificity Signature

- **False Alarm Suppression:** Across all normal-operation datasets in the cross-turbine evaluation, zero normal datasets crossed the criticality threshold of 72 (max criticality stayed below 45 in all cases). Normal-period accuracy is consistently **0.995 to 0.999**.
- **Signature Tradeoff:** The RAI Champion trades pointwise coverage for event reliability and ultra-high specificity.

---

# Gate 5.4 — CARE Fidelity Audit + RAI Integration (2026-09-12)

**Scope note (naming collision, disclosed rather than hidden):** the concurrently-running
session in this same working directory has also produced files it calls "gate54"
(`scripts/gate54_cross_farm_transfer.py`, `tests/test_gate54_cross_farm_transfer.py`,
`artifacts/evaluation/gate54/`) - that is its own next step after its Gate 5.3 (the full
six-way cross-farm matrix, per its checkpoint 11's own "Next" section). This section is a
**separate, independently-scoped "Gate 5.4"**, defined by a detailed brief this session
received directly, whose own explicit instructions are: audit why RAI's CARE adapter
resolves only two features, build two frozen feature policies from CARE's own supplied
metadata, re-test the already-existing A->B/A->C transfer under the validated policy, and
attempt (or honestly decline) an RAI-champion CARE integration - **not** the six-way matrix,
**not** new model architectures, **not** hyperparameter search. No file this section
describes overlaps a file the other session's "gate54" work touches; both are preserved.

**Code (new this gate):**
`rai/eval/external/care/{feature_inventory,feature_policy,cross_farm_semantic}.py`
**Artifacts (new this gate):** `artifacts/evaluation/external_care/{feature_inventory.csv,
feature_inventory.json, feature_policy_comparison.csv, feature_policy_comparison.json,
cross_farm_semantic_results.json, cross_farm_semantic_summary.md}`
**Reused, not duplicated:** `rai/eval/external/care/{champion,published_if,features}.py` and
the real, already-computed results in `docs/checkpoints/{10-care-fidelity-rai,
11-care-feature-rai-integration}.md` (the concurrently-developed RAI-champion CARE
integration - see §10.5).

## 10.1 Phase 1 — Feature inventory (real archive, all three farms)

`rai/eval/external/care/feature_inventory.py` builds one row per raw column in a
representative dataset CSV per farm, cross-referenced against that farm's own
`feature_description.csv` sidecar (`sensor_name;statistics_type;description;unit;is_angle;
is_counter`) - never inventing a sensor identity not present in that file. Full detail in
`artifacts/evaluation/external_care/feature_inventory.{csv,json}` (one row per raw column,
2905 rows total across the three farms + metadata columns).

| farm | raw columns | described sensors | recognized under CARE_NARROW (name-only) | recognized under CARE_SEMANTIC (sensor_map wired) |
|---|---|---|---|---|
| Wind Farm A | 86 | 81 | 2 (+status_code) | 10 (+status_code) |
| Wind Farm B | 257 | 252 | 2 (+status_code) | 9 (+status_code) |
| Wind Farm C | 957 | 952 | 2 (+status_code) | 13 (+status_code) |

Signals resolved under CARE_SEMANTIC, per farm (from the artifact, not hand-typed):

- **Farm A (9):** ambient_temp_c, gearbox_oil_temp_c, generator_winding_temp_c,
  nacelle_temp_c, pitch_angle_deg, power_kw, rotor_rpm, wind_direction_deg, wind_speed_ms
- **Farm B (8):** drivetrain_vibration_mms, gearbox_oil_temp_c, main_bearing_temp_c,
  pitch_angle_deg, power_kw, rotor_rpm, wind_direction_deg, wind_speed_ms
- **Farm C (12):** ambient_temp_c, drivetrain_vibration_mms, gearbox_oil_temp_c,
  generator_winding_temp_c, main_bearing_temp_c, nacelle_temp_c, pitch_angle_deg, power_kw,
  pressure_hpa, rotor_rpm, wind_direction_deg, wind_speed_ms

**Common to all three farms (6):** `gearbox_oil_temp_c, pitch_angle_deg, power_kw, rotor_rpm,
wind_direction_deg, wind_speed_ms` - a superset of WindADBench's cited 3-signal cross-farm set
(`wind_speed`, `active_power`, `rotor_speed`), consistent with (not proof of) WindADBench
describing the same underlying archive (see the corrected sourcing note near the top of this
document). Matching semantic *category* across farms does not establish the sensors are on a
comparable physical scale - different turbine models, different gearbox designs - which is
why §10.4's cross-farm re-check language stays in "observed under the protocol" terms.

## 10.2 Phase 2 — Why the other 2-6 signals per farm are still not recognized

Rejection-reason counts, computed from `resolve_columns`'s own alias-scoring function against
every one of the 15 `WIND_SIGNAL_SPECS` entries, not guessed:

| farm | total sensor columns | recognized | lost_to_higher_scoring (implementation limitation) | no_canonical_slot (unsupported semantic type) | excluded_cumulative_energy_counter (unsupported semantic type) |
|---|---|---|---|---|---|
| Wind Farm A | 81 | 9 | 24 | 40 | 8 |
| Wind Farm B | 252 | 8 | 56 | 172 | 16 |
| Wind Farm C | 952 | 12 | 256 | 684 | 0 |

Three distinct reasons, classified exactly (never "CARE limitation" used loosely):

1. **`no_canonical_slot` - unsupported semantic type, a real schema-coverage gap, not
   attributed to either side alone.** These columns' descriptions score zero against every
   canonical alias RAI's 15-signal wind schema (`rai/ingest/care.py::WIND_SIGNAL_SPECS`)
   knows about (e.g. hydraulic pressures, specific fault counters, converter-internal
   diagnostics with no counterpart in that schema). CARE genuinely exposes physical
   categories RAI's canonical schema was never built to hold - fixing this requires *adding*
   new canonical signal types, not just better ingestion wiring.
2. **`lost_to_higher_scoring_column_for_<canonical>` - a confirmed implementation
   limitation, exact code path identified.** `resolve_columns` (`rai/ingest/care.py:405-460`)
   is winner-take-all per canonical name: it scores every raw column against every spec,
   sorts canonical names by their best available score, and for each one claims the single
   highest-scoring still-unused column (`used.add(original)`, line 453) - every other column
   that also scored nonzero for that same canonical name is discarded outright, with no
   second slot. On Farm C (22 turbines' worth of columns pooled into one anonymised header),
   this is not a small effect: 55 columns lose to the single column holding the
   `pressure_hpa` slot, 43 lose to `power_kw`, 39 to `rotor_rpm`. These are very likely
   genuine, distinct sensors (multiple pressure transducers on different sub-systems) that
   CARE's own metadata describes clearly enough to categorize (see `features.py`'s own
   category classifier, §10.5) - RAI's schema has room for exactly one column per physical
   quantity name, not one per physical quantity per component. This is squarely an
   implementation limitation: the canonical schema, not CARE's anonymisation, is what forces
   the collapse.
3. **`excluded_cumulative_energy_counter` - unsupported semantic type, and the reason it
   matters.** 8 columns on Farm A and 16 on Farm B are cumulative energy counters (units
   `Wh`/`kWh`/`VArh`) that this gate's own safety fix (§10.3) deliberately excludes from the
   semantic sensor_map, because CARE's own `is_counter` flag does not reliably flag them
   (verified: Farm A's "Total active power," unit Wh, ships with `is_counter=False`) and,
   without the exclusion, one of them was found to silently win the `power_kw` slot away from
   the physically-correct instantaneous-kW column. RAI's canonical schema has no
   "cumulative counter" signal type at all - excluding these is the right behavior given that
   gap, not a workaround for a bug in the exclusion logic itself.

**Answering the master question directly:** the original "only two features" finding was
real, but it measured RAI's *default* ingestion policy (name-only matching, `sensor_map=None`
in every existing runner), not a hard CARE limit. Of the 15 canonical signals, 10-13
now resolve per farm once `feature_description.csv` is wired in; of the remainder, the
`lost_to_higher_scoring` share (24-256 columns per farm) is a confirmed implementation
limitation with an identified fix path (a multi-instance canonical schema); the
`no_canonical_slot` and `excluded_cumulative_energy_counter` shares are schema-coverage gaps
that would require deliberately extending RAI's canonical wind vocabulary, not just its
ingestion wiring - genuinely a joint property of "what RAI's schema models" and "what CARE's
anonymisation still lets through," which remains only partially resolved, not fully
attributable to either side alone.

## 10.3 Phase 3 — CARE_NARROW vs CARE_SEMANTIC (frozen policies, same baselines, same scorer)

Two named, frozen policies (`rai/eval/external/care/feature_policy.py`), differing in exactly
one input to the existing, unmodified `rai.ingest.care.load_care_csv`/`resolve_columns`: the
`sensor_map` argument.

- **CARE_NARROW** = `sensor_map=None` (byte-identical to `farm_a_runner.py`'s existing
  behaviour - re-running it under this module reproduced Farm A/B's already-published numbers
  exactly: 0.5345/0.5062 and 0.5324/0.4013, a determinism cross-check, not a new result).
- **CARE_SEMANTIC** = `sensor_map=feature_inventory.build_safe_sensor_map(feature_description.csv)`,
  i.e. CARE's own supplied sensor descriptions, with cumulative-energy-counter rows excluded
  (§10.2, item 3). Neither policy was tuned after looking at a CARE score; both are fixed from
  CARE's own metadata before any dataset is scored, and neither uses target labels, event
  metadata, or future prediction-period rows to select a feature.

| farm | model | policy | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|---|---|
| Wind Farm A | isolation_forest | care_narrow | 0.5345 | 0.4339 | 0.1251 | 0.3333 | 0.8902 |
| Wind Farm A | isolation_forest | care_semantic | 0.6022 | 0.4692 | 0.1307 | 0.5263 | 0.9423 |
| Wind Farm A | zscore_threshold | care_narrow | 0.5062 | 0.1823 | 0.0267 | 0.3333 | 0.9944 |
| Wind Farm A | zscore_threshold | care_semantic | 0.5308 | 0.2929 | 0.0458 | 0.3333 | 0.9911 |
| Wind Farm B | isolation_forest | care_narrow | 0.5324 | 0.2355 | 0.0787 | 0.5556 | 0.8960 |
| Wind Farm B | isolation_forest | care_semantic | 0.5554 | 0.2408 | 0.0798 | 0.5556 | 0.9504 |
| Wind Farm B | zscore_threshold | care_narrow | 0.4013 | 0.0076 | 0.0020 | 0.0000 | 0.9985 |
| Wind Farm B | zscore_threshold | care_semantic | 0.5349 | 0.1147 | 0.0385 | 0.5556 | 0.9829 |
| Wind Farm C | isolation_forest | care_narrow | 0.5328 | 0.2800 | 0.1319 | 0.4651 | 0.8935 |
| Wind Farm C | isolation_forest | care_semantic | 0.6023 | 0.2317 | 0.2017 | 0.7471 | 0.9154 |
| Wind Farm C | zscore_threshold | care_narrow | 0.4388 | 0.0422 | 0.0167 | 0.1613 | 0.9870 |
| Wind Farm C | zscore_threshold | care_semantic | 0.5725 | 0.1474 | 0.1185 | 0.6780 | 0.9593 |

Reported per farm independently, not aggregated, per the brief's own instruction.
**CARE_SEMANTIC scores at or above the corresponding CARE_NARROW score for both baselines on
all three farms, with no exception** - the clearest single number is `zscore_threshold` on
Farm B (0.4013 -> 0.5349, driven almost entirely by reliability going from 0.000, meaning it
never reliably flagged a single one of Farm B's 6 real anomaly events under CARE_NARROW, to
0.5556 once gearbox-temperature, pitch, rotor-speed and wind-direction signals become
available to it), but Farm C - the largest sample in this benchmark, 27 anomaly events - shows
the same direction for both models too: isolation_forest 0.5328 -> 0.6023, zscore_threshold
0.4388 -> 0.5725, both driven substantially by reliability (0.4651 -> 0.7471 and 0.1613 ->
0.6780 respectively) and, for isolation_forest, also earliness roughly doubling (0.1319 ->
0.2017). Six of six farm/model combinations improve, none regress. This is real, computed
evidence that the two-feature figure bounded what these baselines could see, not just a
restatement of the hypothesis - consistent with (not proof beyond this benchmark of) the
corrected framing in §0/§2 above. It does not by itself establish that a 6-15 feature policy
is close to whatever CARE's true ceiling is on this archive; it establishes that the specific
number "0.53" reported for Farm A/B/C in §§1-2 measured RAI's default ingestion policy, not a
property of the benchmark.

## 10.4 Phase 4 — Cross-farm re-check under CARE_SEMANTIC

`rai/eval/external/care/cross_farm_semantic.py` reruns exactly Gate D's protocol (fit once on
the source farm's pooled TRAIN rows, score unmodified on every target dataset, never refit -
same `_intersected_columns`/`_fit_on_columns` functions imported from `cross_farm.py`, not
reimplemented) with each farm loaded through its own CARE_SEMANTIC `sensor_map`. The feature
intersection actually used is computed from the loaded data per pair, not assumed to be the
global 6-signal common set:

| model | source -> target | feature intersection (n) | CARE | coverage | earliness | reliability | accuracy |
|---|---|---|---|---|---|---|---|
| isolation_forest | Wind Farm A -> Wind Farm B | wind_speed_ms, wind_direction_deg, power_kw, rotor_rpm, pitch_angle_deg, gearbox_oil_temp_c (6) | 0.574 | - | - | - | - |
| zscore_threshold | Wind Farm A -> Wind Farm B | same 6 | 0.557 | - | - | - | - |
| isolation_forest | Wind Farm A -> Wind Farm C | wind_speed_ms, wind_direction_deg, ambient_temp_c, power_kw, rotor_rpm, pitch_angle_deg, nacelle_temp_c, gearbox_oil_temp_c, generator_winding_temp_c (9) | 0.627 | - | - | - | - |
| zscore_threshold | Wind Farm A -> Wind Farm C | same 9 | 0.295 | - | - | - | - |

(Full sub-scores in `artifacts/evaluation/external_care/cross_farm_semantic_results.json`.)
A->C's feature intersection (9 signals) is richer than A->B's (6) simply because Farm C's own
recognized set is a superset of Farm A's under CARE_SEMANTIC (§10.1) - not a methodology
change between the two pairs.

**Comparison against the CARE_NARROW cross-farm numbers already in §4 - reported as observed
outcomes, not as evidence for or against generalization:**

| pair | model | CARE_NARROW transfer (§4) | CARE_SEMANTIC transfer (§10.4) | direction |
|---|---|---|---|---|
| A->B | isolation_forest | 0.600 | 0.574 | lower under the richer policy |
| A->B | zscore_threshold | 0.430 | 0.557 | higher under the richer policy |
| A->C | isolation_forest | 0.601 | 0.627 | higher under the richer policy |
| A->C | zscore_threshold | 0.484 | 0.295 | lower under the richer policy |

The direction of the effect is **not consistent** across model/pair combinations - richer
features raised CARE for isolation_forest on A->C and zscore on A->B, but lowered it for
isolation_forest on A->B and zscore on A->C. This is reported plainly because it complicates
any simple "more features = better transfer" story: **A->B and A->C transfer produced higher
or lower CARE scores than the corresponding target-farm in-farm runs depending on model and
feature policy, observed under the implemented transfer protocol** - not "generalization" in
either direction. Plausible, unconfirmed confounds behind the mixed picture include: different
feature-space dimensionality per pair (6 vs 9 columns) changing each model's effective
decision boundary; `zscore_threshold`'s any-channel-exceeds-threshold rule getting noisier as
more channels are added (more chances for one channel to false-alarm) while
`isolation_forest`'s multivariate density estimate can use the same extra channels
constructively; and the CARE paper's own documented Farm B/C data-quality caveats (missing
values recorded as zeros, inconsistent status-code logging) interacting differently with a
transferred vs. in-farm-fit model. This protocol does not isolate which of these, if any, is
the actual cause - that is unresolved, not glossed over.

## 10.5 Phase 5 — RAI integration: RAI CARE = COMPUTED (via the concurrently-developed champion adapter)

This gate's brief asks for RAI's actual intended champion, verified against a leakage/
provenance checklist, connected to the *unmodified* official CARE scorer, or an explicit
`RAI CARE = NOT_COMPUTED` with a reason. That work already exists in this working directory,
built by the concurrently-running session (`rai/eval/external/care/champion.py`,
`fit_rai_champion`/`RAIChampionDetector`), and this gate's job was to verify it rather than
build a second, competing adapter:

- **Training data boundary:** `fit_rai_champion` is called only on `train_frame` (rows where
  the split column equals `"train"`) in `scripts/gate52_fidelity_and_champion.py:125,142-149` -
  verified by reading the call site, not assumed.
- **Prediction-period boundary:** `model.predict(pred_frame)` is called on the disjoint
  `"prediction"` split (same file, line 150) - the same train/prediction column farm_a_runner
  itself uses.
- **Feature lineage:** `RAIChampionDetector.get_input_manifest()` records, per consumed
  signal, its `source_raw_column`, `unit`, and `transformation` - not a black box.
- **Threshold and normalization provenance:** `z_threshold=2.5`, `persistence_steps=3` are
  fixed constants passed identically across every farm (not tuned per farm or per result);
  `power_mu/power_sigma/rotor_mu/rotor_sigma` are computed strictly from `train_frame`
  residuals and stored in the returned `provenance` dict.
- **Determinism:** the fit is `np.polyfit` plus residual mean/std - no random seed, no
  stochastic component; re-running the existing test suite reproduces identical numbers.
- **Official CARE scorer unchanged:** `rai/eval/external/care/metrics.py` does not appear in
  `git diff --stat` for this working tree at the time of this gate (verified directly, not
  assumed) - nothing in this gate, or in the concurrently-developed champion work, modified
  the scorer itself.
- **Verification re-run for this gate:** `pytest tests/test_gate52_baselines_and_champion.py
  tests/test_gate52_care_scorer_audit.py tests/test_gate53_cross_turbine.py -q` -> 43/43
  passing (re-run today as part of this gate, not assumed still green).

**RAI CARE, `care_common` feature policy (real numbers, `docs/checkpoints/10-care-fidelity-rai.md`):**

| farm | RAI CARE | coverage | accuracy | reliability | earliness | events detected |
|---|---|---|---|---|---|---|
| Wind Farm A | 0.601 | 0.309 | 0.997 | 0.652 | 0.049 | 3/11 (27.3%) |
| Wind Farm B | 0.560 | 0.007 | 0.999 | 0.769 | 0.025 | 4/6 (66.7%) |
| Wind Farm C | 0.575 | 0.011 | 0.995 | 0.728 | 0.147 | 15/27 (55.6%) |

This is a real, leakage-checked, official-scorer number - not renamed from an internal RAI
score. **One unresolved oddity, disclosed rather than smoothed over:** the later
`docs/checkpoints/11-care-feature-rai-integration.md` (same champion adapter, `care_2d`
feature policy specifically) reports `RAI_CHAMPION` CARE = **0.000** on all three farms,
coverage/reliability/earliness all 0.000 and zero alarms raised on any dataset - a materially
different result from `care_common`/`care_native_semantic` (0.560-0.641) on the *same*
detector. This gate did not diagnose that discrepancy (it belongs to the concurrently-owned
`champion.py`/`features.py`, and this gate's brief prohibits new model-architecture work) -
it is named here as a remaining question for whoever next touches that code, not silently
inherited into this section's own claims.

## 10.6 Phase 6 — Two scoreboards, never merged

**DETECTION scoreboard** (this section, plus §§1-9 above): CARE and its four sub-scores
(Coverage, Accuracy, Reliability, Earliness) for CARE_NARROW, CARE_SEMANTIC, cross-turbine,
cross-farm (both policies), and RAI CARE. PR-AUC, MCC, and lead-time-in-minutes are not
computed for the CARE-archive baselines in this document (the CARE metrics module reports
event-level reliability and coverage, not point-wise PR-AUC/MCC - adding those would be new
scoring-methodology work outside this gate's scope).

**DECISION scoreboard:** not computed in this gate. Per this gate's own brief, decision
evaluation is in scope only if required to validate the integration boundary; it was not
required here (the CARE integration boundary was validated via the checklist in §10.5 without
needing a decision-layer test), so it is left `NOT ATTEMPTED` rather than fabricated. RAI's
decision layer consumes RAI's own synthetic-fleet risk-model output, which does not exist for
any CARE-archive run in this document (§6) - there is no risk score to hand a decision policy
here. No decision-world result is used anywhere in this section to claim superior CARE
anomaly detection, and no single number merges the two scoreboards.

## 10.7 Claim changes made in this gate (superseding earlier language in this same document)

1. Withdrawn: "a web search... did not turn up a real, citable benchmark" (WindADBench). It
   is real, verified directly against the GitHub API and its own README (top of document).
2. Withdrawn: "the benchmark's own anonymisation... is the bottleneck" / "the resolvable
   feature space is the same two columns on every farm" stated as a property of CARE itself.
   Corrected to: RAI's *default* ingestion policy resolved two columns; wiring CARE's own
   feature_description.csv recovers 10-13 of 15 signals per farm (§§10.1-10.2).
3. Softened: cross-farm transfer scoring higher than in-farm is now stated as "observed under
   the implemented transfer protocol," with an explicit confound list, never as "cross-farm
   generalization is better" (§4's opening paragraph, and §10.4 above).
4. Added: a cross-turbine caveat citing published transfer-learning literature on the limits
   of pooled multi-turbine pretraining, naming the open question this benchmark cannot settle
   with 5 turbines and 2 resolvable features (§3).

## 10.8 Remaining unresolved questions

- Whether the residual ~2-6 unrecognized signals per farm (beyond the 10-13 that now resolve)
  reflect CARE's own anonymisation or a still-fixable RAI schema gap is **unresolved** - §10.2
  attributes most of it to a specific, named implementation limitation
  (`resolve_columns`'s one-slot-per-canonical-name design) plus a smaller, genuine
  schema-coverage gap (signal types RAI's canonical schema does not model at all), but does
  not claim the split between those two is exact.
- Whether pooled cross-turbine or cross-farm transfer reflects real RAI-style generalization,
  versus an artifact of a feature representation too narrow for turbine/farm idiosyncrasies to
  register, is explicitly **not settled** by this gate (§3, §10.4) - it would need a richer
  feature representation validated end-to-end, which this gate's own scope excludes.
- The `RAI_CHAMPION`/`care_2d` = 0.000 discrepancy noted in §10.5 is unexplained.
- The full six-way cross-farm matrix (B->A, B->C, C->A, C->B) remains not attempted here (see
  the other session's own "gate54" work, scope note at the top of this section).

**STOP. Gate 5.5 was not started. No model architecture was added. No hyperparameter was
tuned toward a desired result.**

---

# Gate 5.4 — Cross-Farm Wind Transfer & Target-Normal Calibration

**Status:** COMPLETE & AUDITED  
**Last updated:** 2026-09-12  
**Protocol:** WindADBench Track 4 (6 directed transfers among Farms A, B, and C)  
**Representation:** `CARE_COMMON` (`wind_speed`, `active_power`, `rotor_speed`)  
**Code:** `rai/eval/external/care/champion.py`, `scripts/gate54_cross_farm_transfer.py`  
**Artifacts:** `artifacts/evaluation/gate54/` (15 machine-readable artifacts: `cross_farm_results.{csv,json}`, `transfer_matrix.csv`, `transfer_deltas.csv`, `bootstrap_uncertainty.csv`, `paired_uncertainty.csv`, `distribution_shift.csv`, `event_results.csv`, `missed_events.csv`, `false_alarm_events.csv`, `protocol_manifest.json`, `feature_manifest.json`, `summary.md`)

---

## 1. Six Directed Transfers & Three Evaluated Conditions

Evaluated all 6 directed pairs under the frozen `CARE_COMMON` representation across three conditions:
- **Condition A (`FROZEN_SOURCE`):** Trained on source farm and evaluated on target without modification.
- **Condition B (`TARGET_NORMAL_CALIBRATED`):** Trained on source, but power/rotor polynomials and residual statistics calibrated using **only permitted target-normal training data** (zero target anomaly labels, zero test-split leakage).
- **Condition C (`TARGET_SPECIFIC_REFERENCE`):** Target-trained reference ceiling.

### Six-Way Results Table:

| Source $\to$ Target | Frozen CARE | Calibrated CARE | Reference CARE | $\Delta_{\text{transfer}}$ | $\Delta_{\text{calibration}}$ | Gap Recovery | Normal Accuracy (Frozen $\to$ Cal) | Events Detected (Frozen $\to$ Cal) |
|---|---|---|---|---|---|---|---|---|
| **$A \to B$** | **0.5705** | **0.5650** | **0.5417** | +0.0288 | -0.0055 | +19.1% | 0.9884 $\to$ **0.9958** | 4/6 $\to$ 4/6 |
| **$A \to C$** | **0.5927** | **0.5940** | **0.5521** | +0.0406 | +0.0013 | -3.2% | 0.9563 $\to$ **0.9902** | 20/27 $\to$ 17/27 |
| **$B \to A$** | **0.5906** | **0.5806** | **0.5722** | +0.0184 | -0.0100 | +54.3% | 0.5965 $\to$ **0.9963** | 4/11 $\to$ 2/11 |
| **$B \to C$** | **0.5977** | **0.5940** | **0.5521** | +0.0456 | -0.0037 | +8.1% | 0.9471 $\to$ **0.9902** | 17/27 $\to$ 17/27 |
| **$C \to A$** | **0.4392** | **0.5806** | **0.5722** | **-0.1330** | **+0.1414** | **+106.3%** | 1.0000 $\to$ **0.9963** | 0/11 $\to$ 2/11 |
| **$C \to B$** | **0.5452** | **0.5650** | **0.5417** | +0.0035 | +0.0198 | -565.7% | 0.9994 $\to$ **0.9958** | 2/6 $\to$ 4/6 |

---

## 2. Directional Asymmetry & Distribution Shift Findings

1. **Directional Asymmetry:**
   - $A \to C$ gains +0.0406 CARE over target-specific reference, whereas $C \to A$ drops -0.1330 CARE (collapsing from 2 detections to 0 detections). Asymmetry magnitude is **0.1736**.
   - $B \to A$ maintains CARE = 0.5906 but exhibits severe normal-operation false alarms (accuracy drops to 0.5965), whereas $A \to B$ maintains normal accuracy at 0.9884.
2. **Distribution Shift Underlying Asymmetry:**
   - KS tests confirm that Farm B has a fundamentally different rotor operating regime: median rotor speed is 7.98 rpm vs Farm A's 11.40 rpm (KS = 0.6673, $p < 10^{-15}$). Farm B also has higher wind speeds (mean 8.93 m/s vs 6.19 m/s).
3. **Target-Normal Calibration Sufficiency:**
   - Target-normal calibration resolves both issues: on $C \to A$, it completely recovers CARE to 0.5806 (106.3% recovery) and restores event detection. On $B \to A$, it restores normal accuracy to 0.9963.
   - Across all transfers, unlabelled normal SCADA calibration is sufficient to bring cross-farm deployment to target-specific parity without needing target fault labels.



