---
task: frontend-live-cached-honesty-pass
phase: 5
status: complete
---

## What was built

Completed the frontend-transition work checkpoint 26 found in progress (a concurrent editor
wrapping every API client call in `LiveResult<T>{data, live}` and aligning frontend types to
real backend contracts). This task finished that transition across every remaining page and
fixed several fabrication/contract defects the transition had not yet reached:

- **`web/src/app/assets/[id]/page.tsx` + `EvidenceAccordion.tsx`**: rewired to the real
  `InvestigationEvidence` shape (`peers.subject_residual_pct`/`peer_median_residual_pct`
  instead of a fabricated `peer_z_score`/`distribution`; `environment.explains_fraction`
  instead of an invented `loss_breakdown` object; `economics.avoidable_exposure_inr` instead of
  a `daily_exposure_inr` the API never sent). Removed a fabricated "calibrated Brier: 0.017"
  line with no backing computation. Severity now drives `StatusPill` via the real
  `evidence.anomaly.severity` instead of hardcoded per-asset-ID logic.
- **`web/src/app/evaluation/page.tsx`**: fixed a build-breaking field rename
  (`expected_calibration_error` → `.ece`, per checkpoint 26's contract check). Replaced the
  `defaultModels` fallback's fabricated precision/recall/brier/ece for the three rejected
  baselines with `null` (CHECKPOINT.md's own scorecard reports `—` for these — no baseline
  precision/recall was ever computed for them). Found and fixed a second, independent
  fabrication in the **live** data-mapping branch: `brier`/`ece` were hardcoded to `0.08`/`0.25`
  for every non-champion row regardless of what the live API returned — confirmed via a direct
  `curl /api/evaluation` that `EvaluationData.benchmarks[]` carries no per-model brier/ece field
  at all, so these were never real. Changed both to `null`.
- **`web/src/app/simulator/page.tsx`**: rewrote to the real `ScenarioItem` shape
  (`scenario`/`label`/`typical_onset_days`, not the guessed `id`/`name`/`category`/
  `duration_hours`) and wired "Inject Fault"/"Reset" to the real
  `POST /api/simulator/inject` / `/reset` endpoints with error handling, replacing a decorative
  "SSE Stream: Connected" badge that was never backed by a stream.
- **`web/src/app/soiling/page.tsx` + `web/src/lib/types.ts`/`api.ts`**: replaced an entirely
  fabricated per-asset soiling model (`dust_concentration_ug_m3`, `aod_550`, `advisor_options`
  with invented confidence scores, a hardcoded prose paragraph) with the real, site-level
  `GET /api/soiling` contract, including the `cleaning_options` field checkpoint 25 added to the
  backend but left unwired on the frontend. `cleaning_options` is optional in the type and the
  page renders an honest "not evaluated" message when the field is absent, rather than assuming
  it is always present.
- **`web/src/app/knowledge/page.tsx` + `api.ts`**: replaced a hardcoded 7-document stub and a
  "FTS5 BM25 RETRIEVER ACTIVE" eyebrow badge with a real `getKnowledgeDocs()` call and fixed
  `KnowledgeSearchResult`'s fields (`section`/`score`/`retrieval`, not the guessed
  `section_id`/`category`/`similarity`) against the real `GET /api/knowledge/search` contract.
- **`web/src/lib/api.ts` — `getAssetTimeseries()` (this task's specific starting point)**: the
  real `GET /api/assets/{id}/timeseries` response is an object —
  `{asset_id, signal, unit, interval_min, points, events}` — not the bare `TimeseriesPoint[]`
  the function assumed. `fetchWithFallback`'s generic `res.json() as T` cast trusted that
  assumption blindly, so a live response landed in state as the wrapper object and
  `HeroChart`'s internal `.map()` threw `TypeError: data.map is not a function`, crashing the
  entire Asset Deep-Dive page whenever the backend was actually reachable. Added
  `normalizeTimeseries()`, mirroring the existing `normalizeInvestigation()` adapter pattern:
  maps each real point (`t`, `actual`, `expected`, `lower`, `upper`, `residual_z`) onto
  `TimeseriesPoint`'s fields, computing `residual = actual - expected` (the direct definition of
  the term — the real API has no raw `residual` field, only `residual_z`) rather than inventing
  one.
- Removed several banned-per-`docs/DESIGN.md` patterns encountered along the way: two
  all-caps middle-dot eyebrow badges in `evaluation/page.tsx`
  (`"DEPENDENCE-AWARE · LEAKAGE-FREE EVALUATION"`, `"TRACKING PASSED (R²=0.994) ·
  ANOMALY BENCHMARK PENDING"`) rewritten as sentence-case prose.
- Removed a dead, never-rendered `loading` state in `assets/[id]/page.tsx` flagged by lint after
  the surrounding rewrite.

## Files

- `web/src/components/EvidenceAccordion.tsx`
- `web/src/app/assets/[id]/page.tsx`
- `web/src/app/evaluation/page.tsx`
- `web/src/app/simulator/page.tsx`
- `web/src/app/soiling/page.tsx`
- `web/src/app/knowledge/page.tsx`
- `web/src/lib/api.ts`
- `web/src/lib/types.ts`

## How it was verified

- `npm run build` (Next.js 16.3.5 / Turbopack) → clean, 0 errors, all 7 routes compile
  (`/`, `/assets/[id]`, `/evaluation`, `/knowledge`, `/simulator`, `/soiling`, `/_not-found`).
- `npm run lint` → 0 errors; only pre-existing unused-var warnings remain in files this task
  did not substantially touch (`app/page.tsx`'s `Filter`, `HeroChart.tsx`'s `minResidualZ`,
  three `err`/`risk` bindings in unrelated `api.ts` functions).
- `.venv/Scripts/python.exe -m pytest tests/ -q` → **421 passed**, 24 warnings — matches the
  count already cited in `README.md`; no backend change was made this task.
- Live browser verification (Chrome, `localhost:3000`) against a locally running
  `uvicorn services.api.main:app`, cross-checked against direct `curl` calls to the same
  endpoints, for every page touched:
  - `/assets/WT-017`: with the backend live, `curl /api/assets/WT-017/timeseries` confirmed
    `{points: [902 entries], events: [...]}`; after the fix the page renders the real 902-point
    HeroChart plus a live `EvidenceAccordion` (signal residuals, environmental attribution,
    peer comparison, historical case retrieval) with a `LIVE` badge and zero console errors —
    the crash is gone. With the backend down (it segfaulted mid-session, see Limitations), the
    same page falls back cleanly to the synthetic dataset with a `CACHED · LAST-KNOWN SNAPSHOT`
    badge and no crash either way — both code paths verified, not just the happy path.
  - `/evaluation`: screenshot before the live-branch fix showed identical fabricated
    `0.080`/`0.2500` brier/ece values repeated across different baseline rows; after the fix,
    rejected baselines show `—` and the champion shows the real `0.0423`/`0.1491` from
    `calibration_bins`.
  - `/simulator`: clicked "Inject Fault" on "Gearbox bearing wear" → confirmed a real
    `POST /api/simulator/inject` call succeeded, UI updated to "(injected)" and the card marked
    `ACTIVE`, no console errors.
  - `/soiling`: rendered output matched a direct `curl /api/soiling` field-for-field (dust risk,
    rain probability, days since rain, site soiling %, zone table); the live response had no
    `cleaning_options` field at the time of the check, and the page correctly showed the honest
    "No cleaning options computed... not evaluated" message rather than a blank table or a
    fabricated one.
  - `/knowledge`: header's document/section counts and search results matched a direct
    `curl /api/knowledge/docs` and `/api/knowledge/search?q=...` call.
  - `/` (Fleet Command): re-verified after all other changes; renders live fleet data with no
    console errors. Its `₹0/day` revenue-at-risk and per-row `₹0` exposure figures were checked
    against `curl /api/fleet/priority` directly — genuine live backend output, not a frontend
    bug, and left untouched.
  - Dark mode: spot-checked on `/` and `/assets/[id]` — OKLCH tokens repaint correctly, no
    contrast or unstyled-element issues observed.

## Measured results

Not a modeling change. The two frontend fabrications this task found and removed — the
live-branch hardcoded `0.08`/`0.25` brier/ece in `evaluation/page.tsx`, and the entirely
invented soiling/knowledge fallback data — never had a "correct" number to begin with; the fix
is displaying `null`/the real field instead of a plausible-looking invented one.

## Limitations

- **Backend stability (out of scope, not fixed):** the FastAPI/uvicorn process segfaulted
  three times during this task's browser-verification loop (`Segmentation fault
  nohup .venv/Scripts/python.exe -m uvicorn ...`), each time within a few minutes of a restart.
  This is a native-level crash in `services/api/`/`rai/`, outside this task's `web/`-scoped
  surface, and was worked around by restarting rather than debugged. It should be investigated
  separately — it is the reason several of the live-verification screenshots above show
  `CACHED` rather than `LIVE`.
- **Mobile-width (~390px) responsive check inconclusive:** attempted via the browser
  automation's window-resize tool; the reported viewport did not reliably reach 390px in this
  environment (partial resizes to ~1195px still rendered correctly, but true phone-width was
  not confirmed). Not treated as verified either way.
- **Cross-doc discrepancy flagged, not fixed:** `CHECKPOINT.md`'s own Brier/ECE
  (`0.0439`/`0.0915`) disagrees with the live API's actual served value
  (`0.0423`/`0.1491`, confirmed by direct curl) — `README.md` already documents this exact
  discrepancy and cites the source file alongside the number, so no change was needed there;
  noted here only so it isn't mistaken for a new finding.
- `cleaning_options`'s intermittent absence from the live `/api/soiling` response (first noted
  in checkpoint 25) was not root-caused — `services/api/routers/soiling.py` was read in full and
  always appears to set the field, so the omission's cause (version skew, a caching layer, or
  something else) remains unknown. The frontend handles the absence honestly either way.

## Next

The frontend `LiveResult<T>` transition checkpoint 26 found in progress is now complete across
every page (`/`, `/assets/[id]`, `/evaluation`, `/knowledge`, `/simulator`, `/soiling`), with the
one crash-causing contract mismatch (`getAssetTimeseries`) fixed and verified against a live
backend. Remaining candidates for a future task, in priority order: (1) root-cause the backend
segfault, since it currently makes "LIVE" the exception rather than the default state during
manual testing; (2) properly verify true phone-width responsiveness with a more reliable
viewport-sizing method than this session's browser-automation resize call; (3) root-cause why
`cleaning_options` is sometimes absent from `/api/soiling`'s live response.
