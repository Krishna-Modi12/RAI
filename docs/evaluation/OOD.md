# Controlled Out-of-Distribution (OOD) Perturbation Suite (Gate 2)

**Status:** Executed, real results below
**Last updated:** 2026-09-12
**Code:** `rai/eval/ood.py`
**Artifacts:** `artifacts/evaluation/gate2/ood/results.json`, `artifacts/evaluation/gate2/ood/summary.md`

---

## 1. Why this exists

An earlier iteration of this project reported an OOD generalization PR-AUC of **0.902** that
traced to no executed code at all — see `docs/AUDIT_REPORT.md` §2.6. That number has been
withdrawn. This document and its code are what makes a real OOD number possible: nothing
here is reported unless a perturb-and-rescore experiment actually ran, per CLAUDE.md's
numerical-honesty rule.

## 2. Method

Twelve perturbations (six categories × two severities) are declared in `PERTURBATIONS` inside
`rai/eval/ood.py` — fixed, with their seeds, **before** this suite was ever run against a real
result, so no severity was picked after looking at an output number:

| category | moderate | severe |
|---|---|---|
| `sensor_noise` | Gaussian noise, σ = 0.5× each channel's own std | σ = 1.5× |
| `missingness` | 5% of cells nulled (MCAR) | 20% of cells nulled |
| `drift` | linear ramp 0→1.0× std on temperature channels | 0→3.0× std |
| `extreme_weather` | 10% contiguous block forced to 1st/99th percentile | 30% block |
| `degradation_magnitude` | temp/vibration channels compressed ×0.6 (weaker fault) | expanded ×1.6 (stronger fault) |
| `weather_permutation` | 30% of rows' weather columns shuffled against the timeline | 100% shuffled |

Every perturbation corrupts sensor **observations** only — the ground-truth event list is
never touched, so scoring afterwards measures "does the detector survive corrupted
telemetry", not "did we relabel the problem."

Each of the 12 perturbations, plus one unperturbed baseline, reruns
`rai.eval.benchmarks.run_benchmark_suite` against the real 42-asset synthetic fleet. The
baseline is recomputed inside the same process run rather than read from
`artifacts/evaluation/results.json`, which may be concurrently rewritten by another
evaluation run in this actively-developed repository.

## 3. A methodology bug found and fixed during this work

The first execution of this suite reported **zero measurable effect on the champion for
every single perturbation, including severe ones** (`ΔCARE = +0.000` on all twelve rows).
That result was not trusted and not reported — a detector that is bit-for-bit invariant to
1.5×-std sensor noise, a 3×-std thermal drift, *and* both a 0.6× and 1.6× fault-magnitude
change is not "robust", it is almost certainly not seeing the perturbation at all.

Root cause: `ChallengerHybridEnsemble.predict_window` (`rai/eval/benchmarks.py`) does not
read the `frame` argument `run_benchmark_suite` passes it. It calls
`rai.models.pipeline.compute_asset_state(asset_id, as_of=...)`, which loads telemetry itself
via `rai.store.load_window` (and, for peer comparison, `rai.models.peers` does the same) and
caches the result by `(asset_id, as_of)` in a module-level dict never cleared between runs.
The four baseline candidates score the passed-in `frame` directly and were never affected by
this — only the champion, the one candidate whose OOD behaviour actually matters, was
silently scoring the real unperturbed store data every time.

Fix (`rai/eval/ood.py::_store_serving`): for the duration of each `run_benchmark_suite` call,
`rai.models.pipeline.load_window` and `rai.models.peers.load_window` are patched to serve the
in-memory (possibly perturbed) telemetry dict instead of the on-disk store, and
`rai.models.pipeline.clear_cache()` is called immediately before every run — baseline
included, so the comparison is apples-to-apples. Re-running after this fix produced the
materially different, non-zero deltas in the table below; the fix itself is covered by the
suite completing and the champion's PR-AUC/CARE actually moving per perturbation (a silent
regression back to the caching bug would reproduce the all-zero table).

## 4. Results (real run, 2026-09-12)

42 assets, 6 independent fault events, 839.2s wall time for all 13 runs (baseline +
12 perturbations).

**Baseline (unperturbed):**

| model | CARE | PR-AUC | MCC | FA/asset-yr | median lead (d) |
|---|---|---|---|---|---|
| baseline_4_isolation_forest | 0.691 | 0.594 | 0.563 | 0.19 | 6.5 |
| **challenger_hybrid_ensemble** | **0.797** | **0.822** | **0.690** | **0.19** | **5.0** |

**Champion under perturbation** (full table with both candidates and all deltas in
`artifacts/evaluation/gate2/ood/summary.md`):

| perturbation | severity | CARE | ΔCARE | PR-AUC | ΔPR-AUC | FA/yr | median lead (d) |
|---|---|---|---|---|---|---|---|
| sensor_noise | moderate | 0.365 | −0.432 | 0.135 | −0.686 | 4.06 | 0.0 |
| sensor_noise | severe | 0.280 | −0.517 | 0.189 | −0.632 | 7.92 | 0.0 |
| missingness | moderate | 0.782 | −0.014 | 0.863 | +0.042 | 0.19 | 5.0 |
| missingness | severe | 0.748 | −0.049 | 0.784 | −0.037 | 0.19 | 4.5 |
| drift | moderate | 0.291 | −0.506 | 0.819 | −0.002 | 7.34 | 0.0 |
| drift | severe | 0.276 | −0.521 | 0.594 | −0.228 | 8.12 | 0.0 |
| extreme_weather | moderate | 0.815 | +0.018 | 0.856 | +0.034 | 0.19 | 6.0 |
| extreme_weather | severe | 0.737 | −0.060 | 0.749 | −0.073 | 0.58 | 4.5 |
| degradation_magnitude | weaker signal (0.6×) | 0.722 | −0.075 | 0.931 | +0.109 | 1.35 | 6.5 |
| degradation_magnitude | stronger signal (1.6×) | 0.630 | −0.167 | 0.731 | −0.090 | 2.71 | 5.0 |
| weather_permutation | partial (30%) | 0.793 | −0.004 | 0.738 | −0.084 | 0.19 | 5.0 |
| weather_permutation | full (100%) | 0.585 | −0.212 | 0.557 | −0.264 | 1.35 | 3.0 |

## 5. Reading these numbers honestly

- **Sensor noise and drift are the champion's worst failure modes**: CARE drops by
  0.43–0.52 and false-alarm rate rises 20–40×. A live deployment should treat a sudden rise
  in raw sensor noise or a slowly drifting thermocouple as a data-quality problem to flag
  before trusting the detector's output during that period — this is not currently gated.
- **Missingness (even 20% MCAR) is well tolerated** (ΔCARE ≤ 0.05), which is a genuinely
  reassuring result given real SCADA feeds routinely drop samples.
- **`degradation_weaker` raising PR-AUC (+0.109) while CARE falls (−0.075) and false alarms
  rise (0.19 → 1.35) is a real, non-monotone result**, not a copy-paste error: PR-AUC only
  scores rank-ordering of the asset-level score, while CARE's reliability/false-alarm
  component penalises the extra alarms directly. Weakening the fault signal moved the
  detector's scores in a way that preserved ranking but tripped the alarm-persistence gate on
  more healthy assets. This is exactly the kind of finding a synthetic single-run OOD suite is
  for — it would have been invisible from PR-AUC alone.
- **This is one run, one seed per perturbation, on a synthetic fleet.** It shows sensitivity
  *direction* and rough *magnitude* honestly; it is not a confidence interval and not a claim
  about real SCADA data (see `docs/evaluation/EXTERNAL_CARE.md` for the real-data track).

## 6. Reproduce

```
.venv\Scripts\python.exe -m rai.eval.ood
```

Writes `artifacts/evaluation/gate2/ood/results.json` (full per-run detail, including seeds
and the pre-registered `expected_physical_consequence` for each perturbation) and
`artifacts/evaluation/gate2/ood/summary.md`.
