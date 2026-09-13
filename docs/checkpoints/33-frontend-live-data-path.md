---
task: Fixing frontend live-data browser path
phase: 5
status: complete
---

## What was built

- Routed browser API calls through a same-origin Next.js proxy by default.
- Replaced misleading pre-fetch fallback metrics with explicit loading placeholders.
- Added loading/unavailable/cached states for work orders and the fleet asset count.
- Preserved real fallback snapshots while making their provenance visible.

## Files

- `web/next.config.ts` — `/backend-api/*` rewrite to the FastAPI origin.
- `web/src/lib/api.ts` — same-origin browser API default.
- `web/src/app/page.tsx` — loading lifecycle and honest fleet/work-order states.
- `web/src/components/AppShell.tsx` — no fabricated pre-fetch site counts.
- `tests/test_frontend_runtime_contract.py` — regression checks for the proxy and loading contract.

## How it was verified

- `Set-Location web; npm run lint` — 0 errors, 5 pre-existing warnings.
- `Set-Location web; npm run build` — Next.js 16.3.5 production build passed.
- `.venv\Scripts\python.exe -m pytest tests\test_frontend_runtime_contract.py -q` — 1 passed.
- Fresh dev server on port 3101 and production-like server on port 3100 both returned
  `/backend-api/assets` with HTTP 200 and rendered 42 assets including WT-017.
- Browser rehearsal reached `/assets/WT-017`; timeseries, anomaly evidence, historical
  cases, economics, and recommendation sections rendered. No console/network errors were
  observed in the fresh dev or production-like sessions.

## Measured results

Fleet rendering: 42 of 42 assets; 7 active work orders; WT-017 present.

## Limitations

The existing shared API fallback snapshots remain available when the backend is unavailable
and are labelled cached. Existing lint warnings in `HeroChart.tsx` and unrelated `api.ts`
catch variables remain.

## Next

No follow-on roadmap phase starts until this submission blocker is accepted.
