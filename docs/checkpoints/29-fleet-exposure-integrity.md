---
task: fleet-exposure-integrity
phase: 5
status: complete
---

## What was built

- Completed the fleet exposure transition from instantaneous power deficit to the deterministic
  `do_nothing_exposure` economic engine.
- Removed the frontend's fabricated exposure fallback so unavailable data renders as not evaluated.
- Updated the design contract to use the modeled 30-day exposure field.
- Tightened fleet error handling: expected data/economic failures are explicit and logged.

## Files

- `services/api/routers/fleet.py` — modeled exposure and typed failure handling.
- `web/src/app/page.tsx` — null-safe exposure rendering without a numeric fallback.
- `docs/DESIGN.md` — current fleet metric contract.
- `tests/test_fleet_exposure_integrity.py` — regression coverage for modeled exposure behavior.

## How it was verified

`.venv\Scripts\python.exe -m pytest tests\ -q` → 426 passed, 24 warnings.

## Measured results

426 backend tests passed. No new metric was evaluated by this documentation/integrity pass.

## Limitations

Gate 5.6C solar-model development remains `NOT_INDEPENDENTLY_VALIDATED` (Gate 5.6B's
Validation cohort is empty) and must not be represented as independently validated or complete.

## Next

Commit or review the complete financial-exposure contract change as one backend/frontend unit.
