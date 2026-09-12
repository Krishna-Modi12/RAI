---
task: evaluation-page-cached-indicator
phase: 5
status: complete
---

## What was built

A small, scoped numerical-honesty fix flagged as a limitation in checkpoint 21 but deferred at
the time ("worth a '(cached)' indicator during the post-7AM demo-polish pass if time allows"):
`web/src/app/evaluation/page.tsx`'s champion-model `OPERATIONAL SCORE` and `PR-AUC` figures fall
back to hardcoded snapshot values (`0.797`/`0.822`, real numbers taken from
`artifacts/evaluation/results.json` at the time they were written — not fabricated) whenever
`/api/evaluation` is unreachable or returns `available:false`, but the UI gave no visual signal
that a fallback was showing instead of a live value.

Added a `champIsLive` boolean (`evalData?.champion_model?.care_score != null`) and:
- a `(cached)` suffix on both the `OPERATIONAL SCORE` and `PR-AUC` labels when not live,
- a `title` tooltip on the score badge distinguishing "Live from /api/evaluation" from "API
  unavailable — showing last-known snapshot value".

This directly reflects `docs/checkpoints/23-live-api-smoke-test.md`'s finding that
`/api/evaluation` does serve real, matching data when the backend is up — the gap was only that
the frontend couldn't distinguish "backend down, showing snapshot" from "backend up, this is
live," which matters for a submission demo where the backend's availability may vary.

While fixing this, a grep sweep (`grep -rn "?? [0-9]" web/src/app`) for the same pattern
elsewhere found the same gap on the dashboard homepage (`web/src/app/page.tsx`), the highest-
traffic page in the app: all four headline `MetricTile`s (`Fleet Operational Health`,
`Generation vs Expected`, `Plant Availability`, `Avoidable Revenue Exposure`) silently fall back
to hardcoded numbers (`93.8`, `62450`/`68200`, `97.6`, `485000`) with no live/cached distinction
— a more severe version of the same issue, since these are the first numbers a viewer sees.
Fixed at the component level: added an optional `live` prop (default `true`) to the shared
`MetricTile` component, appending `· cached` to its existing `source` provenance label plus a
tooltip when `live={false}`; wired all four dashboard tiles to `live={overview != null}`
(`overview` is the `FleetOverview` state, `null` until `getFleetOverview()` resolves
successfully). This is a component-level fix, not a per-page one, so any future `MetricTile`
usage inherits the same honesty behavior by default.

## Files

- `web/src/app/evaluation/page.tsx` — added `champIsLive`; two label edits (score badge, PR-AUC
  line) to append `(cached)` and a tooltip when the champion-model figures are not live from the
  API.
- `web/src/components/MetricTile.tsx` — added an optional `live?: boolean` prop (default
  `true`); when `false`, the existing `source` provenance label gets a `· cached` suffix and an
  explanatory tooltip.
- `web/src/app/page.tsx` — wired `live={overview != null}` on all four dashboard `MetricTile`s.

## How it was verified

- `npm run build` in `web/` → **compiled successfully, 8 routes, 0 errors** (unchanged route
  count/shape from the checkpoint 21 baseline), run twice (once after the evaluation-page edit,
  once after the `MetricTile`/dashboard edit).
- Manual read of the diff: the fallback numbers themselves are unchanged (still the real
  snapshot values, not altered) — only a visibility indicator was added, per CLAUDE.md's
  "every number shown in the UI traces to a computed artifact" combined with not overclaiming a
  cached value as live.
- `live` defaults to `true` so no other page or future `MetricTile` usage is silently affected;
  confirmed by grep that `MetricTile` has exactly one call site (`web/src/app/page.tsx`).
- Not re-tested against a live running server in this task (checkpoint 23 already confirmed
  `/api/evaluation` and `/api/fleet`-family endpoints serve real matching data with the backend
  up; this task only needed to confirm the fallback-path UI change compiles and preserves the
  existing numbers).

## Measured results

Not applicable — UI-only change, no computation altered.

## Limitations

- On the evaluation page, only the two champion-model headline figures (`care_score`, `pr_auc`)
  were given the indicator; other hardcoded defaults on the same page (the calibration-bucket
  table around line 156, the per-model `brier`/`ece` fallbacks at lines 115-116, and
  `regretMean`/`regretMedian`/`regretP95` defaults) were not audited or changed — scoped to the
  headline figures checkpoint 21 explicitly flagged, not a full page sweep.
- Cosmetic/wording choice ("(cached)" / "· cached") not reviewed against final demo visual
  design; acceptable for now since the master task's frontend-design pass has not started yet
  (still pre-7:00 AM).

## Next

All items from the "Post-Gate-5.6B / pre-Gate-5.6C" status-correction task list are now
substantively addressed: (1) backend contracts audit — checkpoint 20; (2) evidence/provenance —
checkpoints 20/23 (live HTTP-path assumptions transparency); (3) repository cleanup — checked,
nothing found beyond legitimately gitignored build artifacts; (4) claim audit — checkpoint 21;
(5) documentation coherence — checkpoint 21 plus this iteration's clean grep sweep of
`docs/PRD.md`/`docs/DESIGN.md`/`docs/TECH_STACK.md`/`docs/EVALUATION_FORENSICS.md` (none
mention Gate 5.6C, nothing to correct); (6) reassessment — no unresolved research question is
identified as higher-value than product/submission readiness at this point in the timeline.
With ~421/421 tests passing, ruff clean, pyright at its pre-existing 3-error baseline, and both
`services/api/` (checkpoint 23, live) and `web/` (`npm run build`, this checkpoint) confirmed
working, the codebase is in a stable, honestly-documented state ahead of the ~6:30-7:00 AM
frontend-transition deadline. Continue reassessing for any remaining bounded, high-value
backend/documentation items, or begin frontend-focused work once that transition arrives.
