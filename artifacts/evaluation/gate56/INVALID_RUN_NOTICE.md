# ⚠️ NOTICE: most files in this directory are `GATE_5.6_INVALID_SYNTHETIC_RUN`

Every `*.csv`/`*.json`/`*.md` file sitting directly in this directory (`dataset_selection.*`,
`split_manifest.json`, `pvlib_model_manifest.json`, `empirical_model_manifest.json`,
`champion_model_manifest.json`, `model_metrics.csv`, `regime_metrics.csv`,
`energy_metrics.csv`, `residual_diagnostics.csv`, `system_holdout_results.csv`,
`predictions_sample.csv`, `provenance_manifest.json`, `protocol_manifest.json`,
`quality_filter_manifest.json`, `summary.md`) was produced by a run that evaluated
**synthetically generated data presented as real NREL PVDAQ telemetry**, and validated its
physics-reference model against a formula algebraically identical to the one that generated
that synthetic data (a circular validation). None of the R², nRMSE, or energy-accuracy figures
in these files may be cited as PVDAQ validation, external solar validation, or RAI Solar
Champion performance.

Full evidence: `../gate56_invalid_prior_run/invalidation_manifest.json` and
`../gate56_audit/gate56_scientific_audit_verdict.md`. A frozen snapshot of these same files
(plus the exact source code that produced them) is preserved at
`../gate56_invalid_prior_run/` as audit history.

These files are kept in place (not deleted) per the project's evidence-preservation policy,
and per the same policy are **not modified in place** — see the retraction banner already
added to `docs/checkpoints/14-solar-expected-performance.md` for a full explanation of why.

**The two subdirectories of this folder are real and unaffected by this notice:**

- `acquisition/` — Gate 5.6A, real NREL PVDAQ telemetry acquired from the public OEDI S3 data
  lake, checksummed. See `acquisition/summary.md`.
- `cohort_adjudication/` — Gate 5.6B, adjudication of that real telemetry (timestamps, target
  signal semantics, unit-scale correctness, physics/empirical readiness). No modeling was
  performed in this gate either — see `cohort_adjudication/summary.md`.

Gate 5.6C — an actual expected-performance model fit against the real, adjudicated cohort —
has not yet been attempted.
