---
task: numerical-honesty-audit
phase: 2
status: complete
---

## What was built

- A full numerical-honesty audit of the evaluation stack against CLAUDE.md's "never fabricate
  a metric" rule, covering `scripts/evaluate.py`, `rai/eval/benchmarks.py`,
  `services/api/routers/evaluation.py`, and every doc that cites evaluation numbers.
- Fixed the walk-forward lead-time measurement bug in `rai/eval/benchmarks.py` (single-snapshot
  evaluation was producing a bogus 0.01-day median lead time; added `_walk_forward_first_alarm`
  and `_as_utc`, updated all five `predict_window` signatures to accept `asset_events` and
  detect against a time-stepped window).
- Replaced fabricated risk calibration (`sim_y_true`/`sim_y_prob` hand-typed lists) in
  `scripts/evaluate.py` with the trained risk model's real output via `build_evidence_packet`.
- Fixed the decision-regret tautology (`opt = dec_res.scenarios[0]` compared against itself,
  always zero by construction) — now compares against `min(scenarios, key=cost)`, with an
  explicit caveat that this remains a self-consistency check, not independent ground truth.
- Replaced hardcoded scenario inputs (`failure_probability=0.75`, fixed wind/solar cost splits,
  a hardcoded `DecisionEvidence` fallback) with real per-asset values from the evidence packet.
- Removed the reverse-engineered "alert fatigue funnel" (four filter ratios hand-tuned to
  reproduce 3,218 → 742 → 93 → 17 → 4) everywhere it appeared: `scripts/evaluate.py` (JSON
  payload, markdown table, print statement), `services/api/routers/evaluation.py`,
  `docs/EVALUATION_FORENSICS.md`, `docs/PHASE_2_JUDGE_PACKAGE.md`, `README.md`,
  `docs/EVALUATION.md` — replaced with an honest "not computed" statement in each location.
- Rewrote `services/api/routers/evaluation.py`'s `get_evaluation_metrics()` to serve
  `artifacts/evaluation/results.json` verbatim instead of `.get(key, HARDCODED_NUMBER)`
  fallbacks that always fired (the keys never existed), including removal of a fake
  `tracks.track_b` claiming "Official CARE Reference... Protocol adapter verified."
  - Fixed the cold-path latency measurement (`compute_asset_state` was timed after the
  benchmark suite had already warmed its cache, reading 0.0 ms) by calling `clear_cache()`
  before each timed call.
- Fixed a real static-analysis bug in `rai/decision/models.py` (`Any` used without import).
- Corrected `CHECKPOINT.md`, `README.md`, `docs/EVALUATION.md`, `docs/EVALUATION_FORENSICS.md`,
  `docs/PHASE_2_JUDGE_PACKAGE.md` to state verified numbers plus explicit retraction notices
  where a document's own prior claims were fabricated.
- Wrote `docs/AUDIT_REPORT.md` as the consolidated, authoritative record of every fabrication
  found and every fix applied.

## Files

- `rai/eval/benchmarks.py` — walk-forward lead-time fix, `score_subset()` helper
- `scripts/evaluate.py` — real calibration, real decision-regret comparison, funnel removal
- `services/api/routers/evaluation.py` — rewritten to serve real results verbatim
- `rai/decision/models.py` — missing `Any` import
- `CHECKPOINT.md`, `README.md`, `docs/EVALUATION.md`, `docs/EVALUATION_FORENSICS.md`,
  `docs/PHASE_2_JUDGE_PACKAGE.md`, `docs/AUDIT_REPORT.md` — documentation corrections

## How it was verified

- `pytest tests/ -q` — 141/141 passing, before and after every fix.
- `python scripts/evaluate.py` — run repeatedly end-to-end; numbers stable across reruns
  (CARE 0.797, PR-AUC 0.948, median lead 5.0d for the champion).
- `ruff check .` and a standalone `pyright` run (not the misconfigured IDE instance) against
  the project's own `pyrightconfig.json`.
- A live `fastapi.testclient.TestClient` smoke test against `/api/health` and `/api/evaluation`
  confirming the corrected endpoint serves the same numbers as the results file, no fabricated
  fields.
- A fresh-process check of `rai.agent.runtime.needle_available()` (no shared cache) confirming
  `(True, "needle 2 session constructed")` is a genuine probe result, not a hardcoded value.

## Measured results

See `docs/AUDIT_REPORT.md` for the full before/after table. Headline: champion
(`challenger_hybrid_ensemble`) CARE 0.797, PR-AUC 0.948, median lead time 5.0 days (was a
fabricated 13.5 days), false alarms/asset-year 0.19, Brier 0.0439, ECE 0.0915, cold-path
inference latency p50 ≈ 676–870 ms across runs (was a fabricated ~3ms/0ms).

## Limitations

- `docs/EVALUATION_FORENSICS.md` and `docs/PHASE_2_JUDGE_PACKAGE.md` received a retraction
  notice at the top, not a full line-by-line rewrite — both are long documents built entirely
  around the fabricated numbers, and superseding them in place would take longer than the
  remaining time allowed. `docs/AUDIT_REPORT.md` and `docs/EVALUATION.md` are the sources of
  truth going forward.
- `rai/decision/engine.py`, `policy.py`, `scenarios.py`, `value_of_information.py`,
  `rai/environment/*.py`, `rai/models/fleet_common_cause.py` were spot-checked (grepped for the
  same `.get(key, HARDCODED)` fabrication pattern, none found) but not read end-to-end.
- The decision-regret fix is a correctness fix, not a full remedy: it now compares against the
  true minimum-cost scenario instead of itself, but because the engine's own recommendation is
  already that argmin under the same cost model, regret is still ₹0 by construction. A genuine
  measurement needs an independently derived outcome to compare against, which does not exist
  in this codebase.
- Level 2 (asset-holdout) and Level 4 (OOD) generalization metrics are reported as "not
  computed" / "small-sample, indicative only" rather than replaced with new invented numbers —
  this is honest but means those gates are not actually validated yet.

## Next

External CARE-to-Compare dataset ingestion (to make Track B real) and a genuine walk-forward
alert-fatigue-funnel counter are the two highest-value follow-ups; both are explicitly out of
scope for this audit pass.
