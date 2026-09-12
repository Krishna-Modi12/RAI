---
task: ood-perturbation-suite
phase: 2
status: complete
---

## What was built

- `rai/eval/ood.py`: a controlled out-of-distribution perturbation suite per the Gate-2
  scientific-validation plan (`docs/evaluation/OOD.md`). Twelve perturbations across six
  categories (sensor noise, missingness, drift, extreme weather, degradation-magnitude
  change, weather permutation), each at two severities, all declared with fixed parameters
  and seeds in `PERTURBATIONS` before the suite was ever run.
- Reruns `rai.eval.benchmarks.run_benchmark_suite` once per perturbation against the real
  42-asset synthetic fleet, plus one unperturbed baseline recomputed in the same process
  (not read from the concurrently-modified `artifacts/evaluation/results.json`).
- Found and fixed a real methodology bug during this work: `ChallengerHybridEnsemble`
  (the champion candidate) does not read the `frame` argument the harness passes it - it
  calls `rai.models.pipeline.compute_asset_state`, which reads fresh from
  `rai.store.load_window` and caches by `(asset_id, as_of)`. Unpatched, every "perturbed" run
  silently re-scored the real unperturbed store data for the champion only, producing a false
  "champion is perfectly robust" result (ΔCARE = +0.000 on all twelve rows on the first run).
  Fixed via `_store_serving()`, which patches `rai.models.pipeline.load_window` and
  `rai.models.peers.load_window` to serve the in-memory (perturbed) telemetry and clears the
  pipeline's state/packet cache before every run, baseline included.
- Writes `artifacts/evaluation/gate2/ood/{results.json,summary.md}`.

## Files

- `rai/eval/ood.py` — new: perturbation registry, store-patching harness, report writer.
- `docs/evaluation/OOD.md` — new: methodology, the caching bug found/fixed, full results table.

## How it was verified

- `.venv\Scripts\python.exe -m rai.eval.ood` — run twice. First run (before the store-patch
  fix) produced a suspicious all-zero-delta table for the champion, which was investigated
  rather than reported (see docs/evaluation/OOD.md §3). Second run (after the fix), completed
  in 839.2s, produced non-zero, direction-sensible deltas for both the champion and the
  isolation-forest baseline.
- `.venv\Scripts\python.exe -m pytest tests/ -q` — 164/164 passing (fleet grew from 141 to
  164 via other concurrent work on this repo; two transient failures seen once mid-session
  disappeared on immediate re-run and were traced to a race with another actively-running
  session rewriting `artifacts/evaluation/results.json`, not to this change - confirmed by
  running the suite with/without the new OOD-unrelated CARE test files and re-running twice).

## Measured results

Baseline (unperturbed): champion CARE 0.797, PR-AUC 0.822, MCC 0.690, FA/asset-yr 0.19,
median lead 5.0 days. Under perturbation, CARE fell as much as 0.52 (severe drift) and false
alarms rose up to ~40x (severe sensor noise, 0.19 -> 7.92/asset-yr); missingness up to 20% was
well tolerated (ΔCARE <= 0.05). Full table in `docs/evaluation/OOD.md` §4.

## Limitations

- One seed per perturbation, one run — this shows sensitivity direction and rough magnitude,
  not a confidence interval (that is Gate 2D's uncertainty/bootstrap work, owned by the other
  session's `rai/eval/rolling_origin.py` per this repo's current parallel work).
- Only the champion and the isolation-forest baseline are reported per perturbation (all five
  candidates still run internally); the other three baselines' perturbation sensitivity was
  not analysed to keep the artifact focused.
- Perturbations corrupt observations only; they do not retrain the expected-behaviour models
  or the risk classifier, matching how the other four baseline candidates are also scored
  (predict-only, not retrain-per-perturbation) - so this measures live-scoring robustness,
  not what a model retrained on corrupted historical data would look like.

## Next

External CARE benchmark (`rai/eval/external/care/`) — metrics and adapter are built and
unit-tested against the paper's own formulas; the runner is pending the ~5.5GB Zenodo archive
finishing its download (in progress at time of writing).
