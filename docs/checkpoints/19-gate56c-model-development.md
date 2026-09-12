---
task: gate56c-model-development
phase: 5
status: partial
---

> **STATUS CORRECTION:** This record originally marked `status: complete`. That was wrong.
> **Gate 5.6C has NOT been completed** and must not be described as completed,
> post-completed, validated, or already executed as a finished gate. The work below is real
> — the code ran, the tests pass, the artifacts exist — but it is preliminary
> model-development output that has not been independently verified. Current phase:
> **Post-Gate-5.6B / pre-Gate-5.6C — Backend Intelligence Contracts + Submission Readiness.**
> Gate 5.6B remains the last gate that is actually `COMPLETE` and `FROZEN`. Everything below
> this banner describes what was executed, not a closed gate.

## What was built

- A real `pvlib.pvsystem.PVSystem` + `pvlib.modelchain.ModelChain` physics reference
  (`rai/eval/external/solar/pvlib_modelchain_reference.py`, `PVLibModelChainReference`)
  for the 3 real, `physics_ready=True` PVDAQ development systems (1239, 1283, 34) —
  replacing the invalid hand-rolled `PVLibPhysicsReference` (never imported here). Uses
  only real CEC module/inverter database matches, real tilt/azimuth, and real
  inverter-quantity/module-count metadata already verified in Gate 5.6B's
  `pvlib_readiness.csv`; systems 1430/1433 are intentionally excluded
  (`PARAMETERIZATION_INSUFFICIENT` — no real tracker geometry / no CEC match), enforced
  by a `ValueError` rather than invented parameters.
- A build script (`scratch_gate56a/build_gate56c.py`) that: reuses `build_gate56b.py`'s
  real data loaders/constants, aligns 5 real signals onto the AC-power grid per the frozen
  `alignment_policy.json` (`FASTEST_SIGNAL_GRID_WITH_BACKWARD_HOLD`, exact-or-5min POA
  match, 90-min backward-hold for temperature/wind), applies `apply_quality_filters`
  (nighttime/clipping/curtailment/gap tagging), performs a **temporal-within-system**
  60/20/20 split via `split_system_telemetry` (Gate 5.6B froze cross-system
  Validation=[]), fits `SolarEmpiricalBaseline` and calibrates `RAISolarChampion`
  (both reused unmodified from `models.py`), and writes labeled artifacts.
- A circularity/anti-fabrication tripwire test suite
  (`tests/test_gate56c_model_development.py`, 14 tests): no synthetic-fixture or
  invalid-formula imports; the new physics reference is genuinely temperature- and
  irradiance-nonlinearity-sensitive (not a trivial pass-through); unconfigured systems
  raise instead of fabricating config; artifact labeling is asserted end to end.

## Files

- `rai/eval/external/solar/pvlib_modelchain_reference.py` — new; real ModelChain physics reference + `REAL_MODELCHAIN_CONFIG`.
- `scratch_gate56a/build_gate56c.py` — new; Gate 5.6C build script (imports `build_gate56b` for real data reuse).
- `tests/test_gate56c_model_development.py` — new; 14 tests.
- `artifacts/evaluation/gate56/gate56c_model_development/` — new; `provenance_manifest.json`, `self_consistency_diagnostics.csv`, `predictions_sample.csv`, `summary.md`.

## How it was verified

- `.venv/Scripts/python.exe scratch_gate56a/build_gate56c.py` — real execution against the
  real Gate 5.6A/5.6B acquired+adjudicated PVDAQ parquet data; exit 0, artifacts written
  (only warning output: benign scipy divide-by-zero inside pvlib's CEC single-diode solver
  at zero-irradiance/night rows, which are zeroed out downstream by the night mask).
- `.venv/Scripts/python.exe -m pytest tests/ -q` → **421 passed** (was 407 before this
  task; +14 new Gate 5.6C tests, 0 regressions).
- `.venv/Scripts/python.exe -m ruff check .` → **All checks passed!**
- `npx pyright` (project baseline) → **3 errors, 746 warnings** — same 3 pre-existing
  errors as before this task (`scripts/evaluate.py`, `scripts/evaluate_gate2.py`); no new
  errors from any file touched in this task.

## Measured results

Internal self-consistency diagnostics only (test split, temporal-within-system holdout;
see `self_consistency_diagnostics.csv` / `provenance_manifest.json` for the full table and
the exact `diagnostic_metric_disclaimer`) — **`MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED`,
not validated accuracy, not generalization**:

| System | Model | n (test) | R² | nRMSE (% of rated) |
|---|---|---|---|---|
| 1239 | ModelChain physics | 900 | 0.977 | 3.82% |
| 1239 | Empirical baseline | 900 | 0.985 | 3.04% |
| 1239 | Champion hybrid | 900 | 0.986 | 2.98% |
| 1283 | ModelChain physics | 51,992 | 0.970 | 4.77% |
| 1283 | Empirical baseline | 51,992 | 0.983 | 3.59% |
| 1283 | Champion hybrid | 51,992 | 0.982 | 3.63% |
| 34 | ModelChain physics | 782 | 0.700 | 10.22% |
| 34 | Empirical baseline | 782 | 0.974 | 2.99% |
| 34 | Champion hybrid | 782 | 0.946 | 4.33% |

System 34's physics-only R² (0.70) is notably weaker than 1239/1283's (~0.97) — a real,
undoctored result (not cherry-picked or normalized away), plausibly reflecting the coarser
disclosed simplifications (no direct/diffuse POA decomposition, invariant string-wiring
assumption) interacting differently with its geometry/module type. This asymmetry across
systems is itself evidence against circularity: a formula-identical-to-generator defect
(the original invalidation) would not produce genuine per-system variation like this.

## Limitations

- No real component-failure event labels exist for this cohort (Gate 5.6C decision gate
  finding) — none of the above numbers can be, or are claimed to be, validated accuracy.
- AOI/spectral-mismatch corrections are not modeled (`run_model_from_effective_irradiance`
  with real broadband POA global treated as effective irradiance) because real PVDAQ POA
  sensors do not report decomposed direct/diffuse components.
- `modules_per_string=1` / `strings_per_inverter=<real modules-per-inverter>` is a
  disclosed, power-invariant simplification (real metadata lacks the exact per-inverter
  wiring split); real inverter *quantity* and real total module *count* are otherwise used
  directly.
- System 1239 uses a disclosed `wind_speed=1.0 m/s` standard assumption (`faiman`) because
  its real wind channel is degenerate (Gate 5.6B finding); 1283/34 use real wind speed via
  `sapm` with a `close_mount_glass_glass` racking preset tied to their real "roof" array type.
- Val-split diagnostics were computed but are not tabulated above (test-split only, to
  avoid the false impression of a second independent holdout — see the full CSV for both).

## Next

Reassess remaining master-prompt priorities (wind Kelmarsh benchmark investigation, backend
intelligence contracts, RAG architecture, local-agent/Needle design, economics layer,
frontend data-readiness, repo cleanup, project-wide claim audit) against the ~7:00 AM /
~10:00 AM deadline rule; pick the next highest-value action per the priority function.
