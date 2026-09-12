---
task: soiling-api-cleaning-options-surface
phase: 5
status: complete
---

## What was built

Closes the second limitation flagged in checkpoint 20: `evaluate_cleaning_options()` already
returns a full `CleaningAdvisorEvidence.options: list[CleaningAdvisorOption]`, each carrying an
`assumptions` dict (the fix from checkpoint 20), but `GET /api/soiling` only ever surfaced the
single recommended action's `rationale`/`breakeven_days` — the per-option cost breakdown and its
assumption transparency existed in the Python layer but was never serialized into any API
response, so it could not reach the frontend or be inspected by a client.

Added `"cleaning_options": [option.model_dump() for option in advisor.options]` to
`services/api/routers/soiling.py`'s response. This exposes all evaluated options (`clean_now`,
`wait_24h`, `wait_72h`, `wait_7d` — whichever the evaluator produced), each with its full cost
breakdown (`cleaning_cost_inr`, `expected_energy_loss_inr`, `net_exposure_inr`,
`break_even_days`) and its `assumptions` dict (`tariff_inr_per_kwh`, `capacity_factor`,
`daily_kwh`, `unit_cleaning_cost_inr`, `post_clean_baseline_soiling_pct`, etc.) — the same
evidence-transparency pattern already live on `/api/assets/{id}/investigate`'s
`economics.options[].assumptions` (confirmed real in checkpoint 23's live smoke test).

## Files

- `services/api/routers/soiling.py` — added the `cleaning_options` field to
  `get_soiling_summary()`'s response.
- `docs/API_CONTRACT.md` — documented the new `cleaning_options` field under `GET /api/soiling`
  with a representative example and a one-line pointer to checkpoint 20's assumptions-
  transparency rationale.

## How it was verified

- `.venv/Scripts/python.exe -m pytest tests/ -q` → **421 passed**, 24 warnings — unchanged
  (no existing test asserts a closed key set on the `/api/soiling` response, confirmed by
  reading `tests/test_api_contract.py::test_api_soiling`, so the additive field is safe).
- `.venv/Scripts/python.exe -m ruff check rai/schemas.py rai/economics/engine.py
  services/api/routers/soiling.py` → **All checks passed!**
- Direct function call (no server needed):
  `from services.api.routers.soiling import get_soiling_summary; get_soiling_summary()` —
  confirmed `cleaning_options[0]` is real, non-fabricated data:
  `{"option_id": "clean_now", "cleaning_cost_inr": 1850.0, "expected_energy_loss_inr": 926.1,
  "net_exposure_inr": 2776.1, "break_even_days": 59.9, "assumptions": {"tariff_inr_per_kwh":
  2.45, "capacity_factor": 0.21, "daily_kwh": 1260.0, "unit_cleaning_cost_inr": 1850.0,
  "post_clean_baseline_soiling_pct": 1.0, "recoverable_loss_pct": 1.0, "horizon_days": 30.0,
  "clean_baseline_loss_pct": 1.0}}` — every figure traces to either a named constant in
  `rai/economics/engine.py` or a live weather/soiling input, none hidden.

## Measured results

Not a modeling change — no metrics altered. The new field is a direct serialization of an
already-computed, already-tested object; the numbers were already exercised by
`tests/test_economics_memory.py::test_evaluate_cleaning_options_*`.

## Limitations

- The frontend `web/src/app/soiling/page.tsx` was not updated in this task to display the new
  `cleaning_options` array — this closes the *backend/API* transparency gap only. Wiring it into
  the soiling page's UI (e.g., an expandable per-option assumptions table, mirroring
  `EvidenceAccordion.tsx`'s economics display) is a frontend task, appropriately deferred to the
  post-7:00-AM frontend phase rather than done piecemeal now.
- `rai/environment/cleaning_optimizer.py`'s separate `cleaning_cost_per_mw_inr` (noted
  unreconciled in checkpoint 20) remains unreconciled — still out of scope, different call site.

## Next

Backend intelligence-contract gaps identified in checkpoint 20 are now fully closed (both the
magic-number fix and the API-surface visibility gap). Per the user's explicit instruction this
iteration, begin committing accumulated work to `main` (checkpoints 18-25 plus all associated
code/doc changes) and keep `README.md` current as commits land, rather than leaving a large
uncommitted working tree.
