---
task: deterministic maintenance decision engine
phase: 2
status: complete
---

## What was built

- Added an isolated `rai.decision` package with typed dataclasses for ranges, evidence,
  counterfactual scenarios, rankings, and policy results.
- Added deterministic expected-cost arithmetic with explainable intervention, energy-loss,
  and failure-risk breakdowns.
- Added explicit `act`, `monitor`, `do_nothing`, and `abstain` policies plus wind/solar
  standard action sets.
- Added focused tests covering cost ordering, interval propagation, and evidence abstention.

## Files

- `rai/decision/models.py` — typed decision inputs and outputs.
- `rai/decision/engine.py` — deterministic counterfactual evaluator and action builder.
- `rai/decision/__init__.py` — package exports.
- `tests/test_decision_engine.py` — focused decision-engine tests.

## How it was verified

`.venv\Scripts\python.exe -m pytest tests\ -q` — 132 passed, 1 warning.

`.venv\Scripts\ruff.exe check rai\decision tests\test_decision_engine.py` — all checks passed.

## Measured results

5 focused decision tests passed; the full suite passed with 132 tests.

## Limitations

The package is intentionally not wired into the existing API, schemas, or economics engine;
callers must provide explicit cost and probability assumptions.

## Next

Integrate the decision result into an evidence packet after the API/schema boundary is
explicitly assigned.
