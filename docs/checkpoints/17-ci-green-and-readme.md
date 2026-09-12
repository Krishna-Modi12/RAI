---
task: ci-green-and-readme
phase: 5
status: complete
---

## What was built

- Added the expected-behaviour model training step to the Python quality workflow before tests.
- Added explicit TypeScript types for the knowledge-search response and rendered typed results.
- Documented the retracted Gate 5.6 model claim and the valid Gate 5.6A/5.6B solar data status in the README.
- Included the small real-data fixtures required by the existing provenance and external-benchmark tests.

## Files

- `.github/workflows/quality.yml` — train models during CI before the test suite.
- `web/src/lib/api.ts` — define the knowledge-search response contract.
- `web/src/app/knowledge/page.tsx` — consume typed search results.
- `README.md` — document current solar validation status.
- `docs/checkpoints/17-ci-green-and-readme.md` — task record.

## How it was verified

` .venv\Scripts\python.exe -m pytest tests\ -q` — 407 passed.
` .venv\Scripts\ruff.exe check .` — all checks passed.
` cd web; npm run lint` — 0 errors and 25 existing warnings.
` cd web; npm run build` — production build passed.

## Measured results

407 Python tests passed; frontend production build passed; frontend lint reported 0 errors.

## Limitations

Gate 5.6C has not been attempted; the solar validation cohort remains empty.

## Next

Run the committed quality workflow on `main` and confirm both jobs pass.
