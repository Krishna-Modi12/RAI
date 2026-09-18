---
task: public-surface-audit
phase: 5
status: complete
---

## What was built

- Adversarial claims audit of `docs/presentation/` and `site/` against the authoritative
  evidence registry (18 capabilities, 4/9/4/1 tier counts, 14-case real corpus provenance
  from `docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md`, commit `acd214f`). 4 parallel reader
  agents flagged 29 candidate issues; independent skeptical re-verification (default to
  "not real" unless found verbatim and unqualified) confirmed 22.
- Found, by manual follow-up after the automated pass, that one confirmed error pattern
  (an internal Gate-2 holdout metric "PR-AUC 0.822" stated as if it were a CARE-benchmark
  result) recurred **6 times** across 5 presentation files the automated pass only caught
  once (in `site/index.html`). Verified the true source via
  `docs/evaluation/CLAIM_INTEGRITY_AUDIT.md` before fixing all 6.
- Caught the audit's own ground truth being stale in one case: it suggested changing "554
  tests" to "535" in a demo script. Ran `pytest --collect-only` directly — current count is
  554 — and did **not** apply that fix; applying it would have introduced an error.
- Fixed the evidence-tier table on `site/index.html`: it had only 13 rows while its own
  filter buttons claimed the full 18-capability, 4/9/4/1 breakdown, and included one
  fabricated row ("Live Commercial Utility Deployment") that double-counted the
  `NOT_VALIDATED` tier. Added the 5 missing rows (sourced field-for-field from
  `evidence_registry.json`), split the combined dispatch row into its two registry entries
  with the shared-subsystem note preserved, and moved the true "zero live deployments"
  disclosure to plain prose outside the formal registry table.
- Fixed a currency-unit bug on the same page: three NPV/cost figures used `&pound;` (£)
  instead of INR, and one accompanying cost breakdown (£45,000/£1,350,000) traced to no
  computed artifact anywhere in the repo — replaced with the actually-sourced ₹1.50L/₹17.42L
  figures from `docs/presentation/SCREENSHOT_GUIDE.md`.
- Fixed 3 badges using the `badge-validated` (externally-benchmarked) visual class for
  capabilities the page's own evidence table correctly tags `DEMONSTRATED` elsewhere
  (Economic Exposure, Feeder Isolation, the PR-AUC residuals panel).
- Fixed a fabricated Kelmarsh mechanical-cause claim ("cooling airflow blockage and winding
  thermal trip") after checking the actual record in `rai/memory/real_corpus.py`
  (`REAL-KEL-1-FORCED-2550`: a generator-fan thermal protection trip, explicitly "not a
  component failure") — while leaving two other "Kelmarsh cooling trip" mentions elsewhere
  in `docs/presentation/` untouched, since that phrase matches the record's own `fault_mode`
  field and is not an overclaim.
- Verified the fixed `site/index.html` live in Chrome (served locally): all 5 evidence-table
  filter buttons render the exact row count their label claims, corrected currency/badges/
  disclaimer text render correctly, 0 console messages, 0 failed network requests (4/4 200
  OK). Static-code review confirmed no GitHub Pages `/RAI/` subpath defects (relative asset
  paths, no localhost dependency, working anchors, correct workflow upload path) — no changes
  needed there.
- Confirmed via `git status`/`git log` that `origin/main` is 6 commits behind local `main`
  and GitHub Pages has never been deployed (`gh api repos/.../pages` → 404) — this task did
  not push or trigger a deployment; that remains a separate, explicitly-confirmed step.

## Files

- `docs/presentation/30_SECOND_PITCH.md` — fixed CARE/internal-metric conflation (2 places),
  "failure cases" mislabel, unqualified Kelmarsh match description.
- `docs/presentation/FINAL_5_MIN_SPEAKER_SCRIPT.md` — fixed CARE/internal-metric conflation,
  historical retrieval VALIDATED→DEMONSTRATED mistier.
- `docs/presentation/FINAL_HACKATHON_PITCH.md` — fixed CARE/internal-metric conflation,
  historical retrieval mistier, removed fabricated "Live Utility Deployment" tier row.
- `docs/presentation/FINAL_PRESENTATION_CHECKLIST.md` — fixed CARE/internal-metric
  conflation, historical retrieval mistier (judge Q&A cheat-sheet).
- `docs/presentation/JUDGE_QA.md` — fixed CARE/internal-metric conflation, "failure cases"
  mislabel, wrong CARE/Kelmarsh case-count breakdown, unqualified Kelmarsh fault attribution.
- `site/index.html` — evidence table expanded 13→18 rows matching registry; fabricated
  deployment row removed to prose; 3 currency fixes; fabricated cost breakdown replaced;
  3 badge-tier fixes; fabricated case-study absolute readings qualified as illustrative;
  fabricated Kelmarsh mechanical-cause claim corrected.
- `site/styles.css` — added `.deployment-note` style for the relocated deployment disclosure.
- `docs/evaluation/PUBLIC_SURFACE_AUDIT.md` — new; full audit method, surface matrix, and
  corrections list.
- `docs/checkpoints/36-public-surface-audit.md` — this record.

## How it was verified

- `pytest --collect-only -q` → `554 tests collected in 5.31s` (used to catch and reject a
  stale "535" fix the audit's own ground truth suggested).
- `grep -rn "&pound;" site/index.html` (post-fix) → no matches.
- `grep -o 'data-tier="[A-Z_]*"' site/index.html | sort | uniq -c` → `4 ARCHITECTURAL, 9
  DEMONSTRATED, 1 NOT_VALIDATED, 4 VALIDATED` (18 total), matching the filter-button labels
  and the registry exactly.
- Live Chrome verification against `http://localhost:8123/` (site served via `python -m
  http.server`): clicked "Not Validated (1)" and "Architecturally Supported (4)" filters and
  visually confirmed each shows exactly that many rows; screenshotted the WT-004 case study
  showing corrected ₹ currency and badge labels; `read_console_messages` → 0 messages;
  `read_network_requests` → 4/4 requests 200 OK.
- No Python/web-app code was touched (only `docs/*.md`, `site/*.html`, `site/*.css`), so
  `pytest -q` (full suite), `ruff check`, and `npm run build`/`lint` in `web/` were not
  re-run — nothing in their scope changed.

## Measured results

29 candidates flagged, 22 confirmed by adversarial re-verification, 7 rejected. 6 additional
confirmed instances of one error pattern found by manual follow-up (not counted in the
22, since they weren't in the automated audit's output). 1 suggested fix rejected as based on
stale ground truth. Net: 21 distinct corrections applied across 6 files.

## Limitations

- Mobile-viewport (390×844) resize did not visually apply in this browser-automation session
  — a tooling limitation of Chrome window resizing in this environment, not a site defect.
  The edits made are text/label/attribute-only against pre-existing CSS classes, so
  responsive-layout risk is low; full responsive behavior was verified in an earlier pass
  (`docs/presentation/STATIC_WEBSITE_REPORT.md`) not re-run here.
- This audit covered `docs/presentation/` and `site/` only, per its scope. `README.md` was
  spot-checked with targeted greps for every stale pattern named in the task and found
  already consistent (fixed by earlier concurrent work) — not re-audited exhaustively.
- Did not push to `origin/main` or trigger a GitHub Pages deployment. `origin/main` remains
  6 commits behind local `main`, and Pages has never been enabled for this repository.

## Next

None initiated by this task. If a live GitHub Pages deployment is wanted, that requires an
explicit, separate confirmed step (pushing to a public repo and triggering a real deployment
is externally visible and hard to reverse) — not undertaken here.
