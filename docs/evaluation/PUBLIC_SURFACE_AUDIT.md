# Public-Surface Audit

Adversarial claims audit of every public-facing surface (`README.md`, `docs/presentation/`,
`site/`) against the frozen evidence registry (`artifacts/evaluation/evidence_freeze/`,
commit `acd214f` for real-case provenance, `c8b60f8` for the capability/claims freeze).
Scope: correct wording, labels, currency symbols, and table contents so no public surface
overclaims relative to the registry. No new features, datasets, models, or benchmark results
were added or changed.

## Method

1. One agent read the authoritative registry (18-capability tier counts, the 14-case real
   corpus composition, Gate 5.6C status, closed-loop status, economics framing, Kelmarsh's
   role, local-AI framing) and produced a ground-truth summary.
2. Four parallel agents audited `docs/presentation/` and `site/` (numbers and claims
   separately) against that ground truth.
3. Every candidate issue was independently re-verified by a skeptical agent instructed to
   default to "not real" unless it found the exact text on disk and confirmed it was
   unqualified elsewhere on the page.
4. A fifth agent statically checked `site/` for GitHub Pages subpath correctness (relative
   asset paths, no `localhost` dependency, working internal anchors, correct workflow upload
   path).
5. I manually cross-checked two of the audit's own "ground truth" numbers against current
   code before applying fixes (see Corrections below) and extended the fix set to two files
   the automated pass did not flag, after finding the same confirmed error pattern recurring
   there on manual inspection.

## Surface matrix

| Surface | Status | Claims Checked | Issues Found | Fixed |
|---|---|---:|---:|---:|
| README.md | Already consistent (verified by targeted grep for every stale pattern below; no edits needed) | ~10 patterns | 0 | 0 |
| Presentation (`docs/presentation/`) | Fixed | 29 candidates flagged, 13 confirmed after adversarial verification (5 in `docs/presentation/`) + 4 more found by manual cross-check | 9 | 9 |
| GitHub Pages site (`site/`) | Fixed | 16 confirmed after adversarial verification | 12 | 12 |
| Demo Script (`docs/demo/FINAL_DEMO_SCRIPT.md`) | Not modified — it was the correct source of truth the site's fabricated case-study figures were checked against | n/a | 0 | 0 |

(Site issue count of 12 vs. 16 confirmed findings: several findings pointed at the same two
underlying defects — the evidence-table row/button mismatch and the Economic Exposure badge
— reported once each from more than one audit angle.)

## Real-case corpus provenance (Task B context)

`docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md` (commit `acd214f`) already reconciled the
real-case corpus before this audit ran: **14 external real cases — 12 wind (8 CARE + 4
Kelmarsh) + 2 solar (both NREL PVDAQ)**, of which only 6 (all wind, all CARE) are confirmed
component failures. This audit did not redo that reconciliation; it verified public surfaces
state the corpus correctly and corrected the two presentation files (`JUDGE_QA.md`,
`30_SECOND_PITCH.md`) that still had the earlier, disproven "6 Kelmarsh + 6 CARE" / "failure
cases" wording.

## Corrections made

### Currency, wording, and mis-tiered labels (`docs/presentation/`)

- `FINAL_5_MIN_SPEAKER_SCRIPT.md`, `FINAL_HACKATHON_PITCH.md`, `FINAL_PRESENTATION_CHECKLIST.md`,
  `JUDGE_QA.md`, `30_SECOND_PITCH.md`: "Historical Case Retrieval" was tagged `VALIDATED` in
  four places — the registry places it in `DEMONSTRATED` (self-graded retrieval metric, real
  corpus). Changed to `DEMONSTRATED` in all four.
- Same five files: an internal Gate 2 holdout metric ("PR-AUC 0.822", measured on RAI's own
  42-asset fleet per `docs/evaluation/CLAIM_INTEGRITY_AUDIT.md`) was stated as if it were a
  CARE-benchmark result in **6 separate places** across 5 files. This pattern was caught once
  by the automated audit (`site/index.html:453`) and I found it recurring in
  `FINAL_5_MIN_SPEAKER_SCRIPT.md`, `FINAL_HACKATHON_PITCH.md`, `FINAL_PRESENTATION_CHECKLIST.md`,
  `JUDGE_QA.md`, and twice in `30_SECOND_PITCH.md` by grepping for the same figure after
  seeing the first instance — none of these were in the automated audit's output. All 6 fixed
  to explicitly separate the real CARE metric (normal accuracy > 0.995) from the internal
  metric.
- `FINAL_HACKATHON_PITCH.md`: a "Live Utility Deployment" row was tagged `NOT VALIDATED` in
  the evidence-tier table, inflating that tier from the registry's true count of 1 to an
  apparent 2. Moved the (true) "zero live deployments" disclosure to plain prose outside the
  formal tier table.
- `JUDGE_QA.md`: "14 curated, adjudicated real **failure** cases" (only 6/14 are confirmed
  failures) and a wrong per-source case breakdown ("6 Kelmarsh + 6 CARE", fabricated fault
  types "pitch errors", "pyranometer drift") corrected to the actual 8 CARE + 4 Kelmarsh + 2
  PVDAQ composition and real fault/event types from `rai/memory/real_corpus.py`.
- `30_SECOND_PITCH.md`: "14 audited academic **failure** cases" and an unqualified "Kelmarsh
  cooling trip" match description brought in line with the same corpus-composition fix.

I checked the audit's suggested "554→535 tests" fix (`FINAL_LIVE_DEMO_SCRIPT.md`) against a
live `pytest --collect-only` run before applying it: **current collection is 554**, matching
what the presentation already said. The audit's own cached ground truth (535, sourced from an
older evaluation doc) was stale, not the presentation. That fix was **not applied** — applying
it would have introduced an error rather than removed one.

### GitHub Pages site (`site/index.html`, `site/styles.css`)

- Evidence-tier table had only 13 `<tr>` rows while its own filter buttons claimed the full
  18-capability breakdown (4/9/4/1), and one row ("Live Commercial Utility Deployment") was
  not one of the 18 registry capabilities at all, double-counting the `NOT_VALIDATED` tier.
  Added the 5 missing rows (Environmental Context & Discrimination, RAG Knowledge Retrieval,
  Recommendation Engine, Technician Feedback Ledger, Frontend Operational Workflow) and split
  "Safe-Weather Dispatch Optimizer" into its two registry entries (Dispatch Optimization,
  Weather-Aware Scheduling — documented as the same underlying engine), sourced from
  `evidence_registry.json`. Table is now 18 rows: 4 VALIDATED / 9 DEMONSTRATED /
  4 ARCHITECTURAL / 1 NOT_VALIDATED, verified live by clicking every filter button.
  Removed the fabricated deployment row from the formal table; its true content ("zero live
  commercial deployments") now reads as plain prose below the table (new `.deployment-note`
  style added to `styles.css`).
- "VALIDATED ON CARE · PR-AUC 0.822" badge on the Residuals product panel — same internal/CARE
  metric conflation as above. Relabeled `DEMONSTRATED · INTERNAL HOLDOUT PR-AUC 0.822`.
- Currency symbol: `&pound;` (£) used for all NPV/cost figures in the WT-004 case study
  (3 places), contradicting `CLAUDE.md`'s "Money is INR" rule and the "Lakh" unit used right
  next to it. Replaced with `&#8377;` (₹) throughout.
- The case study's itemized cost breakdown ("£45,000 inspection cost", "£1,350,000
  catastrophic-failure cost") did not trace to any computed artifact anywhere in the repo.
  Replaced with the actually-sourced figures from `docs/presentation/SCREENSHOT_GUIDE.md` /
  `docs/demo/FINAL_DEMO_SCRIPT.md` (₹1.50L inspection & repair cost, ₹17.42L projected
  avoidable exposure).
- "Search 14 partitioned real academic **failure** cases" (Stage 06 of the 10-stage loop) —
  same failure-mislabel pattern; only 6/14 are confirmed failures. Corrected.
- WT-004 case-study timeline stated several absolute readings (108.4°C, 8.2 m/s, 18.2°C
  ambient, aerosol D(t)=0.08, 68–74°C peer range, 94% confidence, ticket `WO-2026-004`) with
  no source anywhere in the repo, alongside one genuinely sourced figure (+12.3σ). Added an
  explicit "illustrative composite walkthrough" qualifier above the timeline rather than
  deleting the narrative or inventing a fake source for the absolute values.
- "FEEDER ISOLATED" and "ACT NOW BENEFIT" badges used the `badge-validated` (green,
  externally-benchmarked) visual class for capabilities the page's own evidence table
  correctly tags `DEMONSTRATED` elsewhere. Changed both to `badge-demonstrated`.
- "KELMARSH COOLING TRIP" badge and timeline text asserting the matched Kelmarsh record
  involved "cooling airflow blockage and winding thermal trip" — the real record
  (`REAL-KEL-1-FORCED-2550`) is a generator-fan thermal protection trip with **no confirmed
  hardware damage**; "airflow blockage" and "winding thermal trip" are not in the source
  record. Badge relabeled "KELMARSH PROTECTION TRIP"; timeline text now says "protection-
  trip/operational event (SCADA-logged downtime; no confirmed mechanical root cause)".
  (Left two other "Kelmarsh cooling trip" mentions in `docs/presentation/` untouched after
  checking `rai/memory/real_corpus.py` directly — that record's own `fault_mode` field says
  "Generator cooling fan 1 thermal protection trip", so "cooling trip" is accurate
  terminology there, not an overclaim.)

## Technical (GitHub Pages subpath) check

Static-code review of `site/` found no defects: all asset references use relative paths
(`./styles.css`, `./app.js`, `./assets/images/...`), `app.js` makes zero network calls, the
only `127.0.0.1` reference is inert instructional text in a code block, every internal anchor
target exists, and the deploy workflow's `path: './site'` matches the actual directory. No
changes were needed for `/RAI/` subpath correctness.

## Browser verification

Served `site/` locally (`python -m http.server`) and verified in Chrome at 1440×900:
evidence-table filter buttons (`All Capabilities (18)`, `Validated (4)`, `Demonstrated (9)`,
`Architecturally Supported (4)`, `Not Validated (1)`) each render the exact row count their
label claims; the WT-004 case study shows the corrected ₹ currency, badges, and disclaimer
text; zero console messages and zero failed network requests on page load (4/4 requests
200 OK). Mobile-viewport (390×844) resize did not visually apply in this browser-automation
session (a tooling limitation of this pass, not a site defect) — the edits made here are
text/label/attribute-only against existing CSS classes, so they carry negligible responsive-
layout risk; the site's structural responsive behavior was already verified in an earlier
pass (`docs/presentation/STATIC_WEBSITE_REPORT.md`) that this audit did not need to repeat.

## Authoritative evidence commit

`acd214f` (real-case corpus provenance reconciliation) → `c8b60f8` (18-capability freeze +
claims-audit downgrades, this repository's HEAD at the time of this audit).

## Public-site deployment status

Not deployed as of this audit. `origin/main` was 6 commits behind local `main` (tip
`5ba4c85`) and `gh api repos/Krishna-Modi12/RAI/pages` returned 404 — GitHub Pages has never
been enabled for this repository. Pushing and triggering a live deployment is a separate,
externally-visible action outside this audit's scope; see the conversation for the explicit
go/no-go check before that step.

## Stale claims found vs. corrected

29 candidates flagged automatically, 22 confirmed after adversarial re-verification; 7
rejected as already-correctly-qualified or not found verbatim. An additional 6 instances of
one recurring error pattern (CARE/internal-metric conflation) were found by manual follow-up
after the automated pass caught only 1 instance of it, across 2 files the automated pass did
not select. Total: 21 distinct corrections applied across 6 files (5 `docs/presentation/`
files, `site/index.html` + `site/styles.css`).
