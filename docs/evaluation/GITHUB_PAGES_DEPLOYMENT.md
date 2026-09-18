# GitHub Pages Live Deployment Report

## Deployment date

2026-09-18 (UTC).

## Repository

`Krishna-Modi12/RAI` (public).

## Workflow

`.github/workflows/deploy-pages.yml` ("Deploy GitHub Pages"). Standard Actions-based
Pages flow: `actions/checkout` → `actions/configure-pages` → `actions/upload-pages-artifact`
(`path: ./site`) → `actions/deploy-pages`. Triggers on push to `main` touching `site/**`,
plus `workflow_dispatch`. No changes were made to this file — it was already correct.

## Deployment source

GitHub Pages configured via `gh api --method POST repos/Krishna-Modi12/RAI/pages
-f build_type=workflow` (Pages had never been enabled before this task — the API returned
404 prior to this call). Source: Actions workflow output, branch `main`, directory `./site`.

## Public URL

**https://krishna-modi12.github.io/RAI/**

## Commit deployed

`25895440b654e8e1d29bba3eb51b7886e7f16bcf` (`2589544`) — confirmed via the GitHub
Deployments API (`sha` field on the `github-pages` environment's latest deployment) and via
`git rev-parse HEAD`, which match exactly.

## Push

Fast-forward only, no force. Pre-push checks: `git status` clean of anything but two
incidental weather-cache files and one unrelated notebook (neither staged/committed);
`git log --oneline origin/main..main` showed 7 commits, all legitimate RAI documentation/
site/app work (`git diff --stat origin/main..main` — 43 files, presentation docs, `site/`,
one API contract fix, checkpoint records, README); grepped the full diff for secret patterns
(API keys, tokens, private keys) — no matches. `git rev-list --left-right --count
origin/main...main` was `0 7` before push (clean fast-forward), confirmed `0 0` after both
pushes. `git push origin main` used both times (no `--force`).

## GitHub Actions

| Run | Commit | Trigger | Result |
|---|---|---|---|
| [35335919095](https://github.com/Krishna-Modi12/RAI/actions/runs/35335919095) | `1e5623d` | push (initial deploy) | ✅ success, 18s |
| [35336464711](https://github.com/Krishna-Modi12/RAI/actions/runs/35336464711) | `2589544` | push (commit-stamp fix) | ✅ success |

Both runs auto-triggered by the push (workflow watches `site/**`) — no manual
`workflow_dispatch` was needed. Only informational annotations (Node 20 deprecation notice,
`ubuntu-latest` image migration notice); no warnings or failures.

## Live browser audit

Verified against the real public URL (not localhost) via Chrome automation, and
cross-checked with `curl` to rule out any client-side cache interference.

- **HTTP status:** 200 (`curl -s -o /dev/null -w "%{http_code}"` → `200`).
- **Console:** 0 messages of any kind (log/warn/error) on page load.
- **Network:** 4/4 requests 200 OK (`index.html`, `styles.css`, one product-tab PNG,
  `app.js`) — no failed requests, no calls to `localhost` or any backend. `app.js` makes zero
  network calls of its own.
- **Subpath correctness:** all asset references are relative (`./styles.css`, `./app.js`,
  `./assets/images/...`) and resolve correctly under the `/RAI/` subpath — confirmed both by
  the 200s above and by the earlier static review in `docs/evaluation/PUBLIC_SURFACE_AUDIT.md`.
- **Navigation / tabs:** clicked through product tabs 1–5 (Fleet Command → Work Orders &
  Dispatch); each switches content and loads its screenshot correctly (one PNG appeared
  briefly black immediately after tab-switch — confirmed to be normal image-load latency, not
  a broken asset, on a follow-up screenshot 2s later).
- **Evidence filters:** clicked "Not Validated (1)" and "Demonstrated (9)" — each renders
  exactly the row count its label claims (1 and 9 respectively), matching the frozen registry.
- **CTAs:** "GitHub" link resolves to `https://github.com/Krishna-Modi12/RAI` (correct,
  external); "Run Demo"/"Run the Demo" target `#quickstart` (in-page, present); nav links
  target existing in-page anchors.
- **Case study content:** WT-004 walkthrough shows the corrected ₹1.50L/₹17.42L/+₹9.07L
  figures, "FEEDER ISOLATED (DEMONSTRATED)" and "KELMARSH PROTECTION TRIP" badges, and the
  "illustrative composite walkthrough" disclaimer — all from the prior audit session,
  confirmed still correct on the live deployment.
- **Mobile navigation:** window-resize to 390×844 did not visually apply in this
  browser-automation session (see Limitations) — content was inspected via full-page text
  extraction instead, which found no rendering-breaking issues, but true mobile-viewport
  visual confirmation was not obtained live.

No broken images, no broken links, no overlapping/clipped elements were observed at the
viewport sizes that did render (desktop). Full-page text extraction (`get_page_text`) was
used as a live content fact-check (see below) in place of a third visual viewport pass.

## Content / evidence consistency (live fact-check)

Extracted the full rendered text of the live page and checked it against the current
authoritative state:

| Check | Live page | Match |
|---|---|---|
| Capability count | "18" (filter buttons: 4/9/4/1) | ✅ |
| Real case count | "14 Real Academic Cases Partitioned" / "14 partitioned real academic cases (6 confirmed equipment failures, plus operational, maintenance, and environmental events)" | ✅ |
| Live commercial connections | "Zero Live Commercial Plant Connections" (explicit limitations section) + deployment-note prose | ✅ (0) |
| Solar failure validation | "Solar Physics Failure Model (Gate 5.6C) — NOT VALIDATED"; "Solar Failure Validation Is Unclosed" | ✅ |
| Kelmarsh framing | Explicit limitations heading: "Kelmarsh Operational Events ≠ Hardware Failure" | ✅ |
| Economics framing | "Modeled Economic Projections... must never be interpreted as realized, guaranteed accounting savings" | ✅ (modeled/projected) |
| Closed-loop framing | "Demonstrated in-browser; zero commercial utility sites connected" | ✅ (demonstrated, not live) |
| Stale phrases ("13 capabilities", "16 real cases", "field verified", "production ready", "live deployment", "guaranteed ROI", "independently validated solar", "autonomous control") | None found as active claims — "autonomous control" and "guaranteed" only appear negated (e.g. "Zero Autonomous Plant Actuation", "not... guaranteed") | ✅ |

No previously corrected claim from `docs/evaluation/PUBLIC_SURFACE_AUDIT.md` had regressed.

## Fixes made (this task)

Only one, found during live verification — a genuine deployment-provenance defect, not a
content/claims fix (those were already completed and verified in the prior audit task):

- **Stale "Frozen Release Commit" stamp.** The hero telemetry bar and footer hardcoded
  `4e80839d` (the original static-site build commit, 6 commits stale) while the page
  actually live was built from `1e5623d`. Updated both the short and full hash
  (`site/index.html`, 2 lines) to the commit that was actually deployed. Committed
  (`2589544`), pushed, redeployed (run `35336464711`, success), and re-verified live via
  both `curl` (cache-bypass) and a hard browser reload — confirmed correct.
  - **Residual limitation:** a hand-maintained commit stamp in a static file is inherently
    unable to name its own commit hash (the hash is only computed after the commit is
    created). This fix reduces staleness to that unavoidable one-commit minimum; fully
    closing it would require a build-time stamping step, which is a new feature and out of
    scope for this deployment task.

No RAI application code was touched. No new features, redesigns, or scope beyond this one
provenance correction.

## Deployed commit

`25895440b654e8e1d29bba3eb51b7886e7f16bcf` (`2589544`)

## Git status (post-deployment)

```
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
	modified:   artifacts/weather_cache/charanka-solar_latest.json
	modified:   artifacts/weather_cache/kutch-wind_latest.json

Untracked files:
	lab5_KF_.ipynb
```

`origin/main` and local `main` are synchronized (`git rev-list --left-right --count
origin/main...main` → `0 0`). The two weather-cache files (timestamp-only telemetry-cache
refreshes) and the unrelated notebook are pre-existing, incidental, and were correctly never
staged or committed by this task. No secrets, no temporary artifacts.

## Limitations

- Mobile-viewport (390×844) resize did not visually apply in this browser-automation
  session — the same tooling limitation observed and documented in the prior local-site
  audit (`docs/evaluation/PUBLIC_SURFACE_AUDIT.md`). No edits in this task touched responsive
  CSS, and the site's structural responsive behavior was verified in an earlier pass
  (`docs/presentation/STATIC_WEBSITE_REPORT.md`); this remains an environment limitation of
  this Chrome-automation session, not a claim of full live mobile verification.
- The "Frozen Release Commit" stamp will again read one commit behind as soon as any future
  commit touches `site/index.html`, for the structural reason described above. Not a defect
  introduced by this task — an inherent property of a hardcoded (non-templated) build stamp.
- `artifacts/evaluation/github_pages_live/` screenshots were not captured as separate files
  in this pass; live verification evidence here is the Chrome session's in-context
  screenshots plus the `curl`/API checks recorded above, not saved image artifacts.

## Final recommendation

**LIVE AND VERIFIED.** The public GitHub Pages deployment at
https://krishna-modi12.github.io/RAI/ is live, serves HTTP 200, matches the current
authoritative evidence state exactly (18 capabilities, 4/9/4/1, 14 real cases, 0 live
deployments, correct Kelmarsh/solar/economics/closed-loop framing), has 0 console errors and
0 failed network requests, and its one discovered defect (a stale release-commit stamp) was
fixed, redeployed, and re-verified live within this task. No further action is required
unless a full third-viewport (mobile) visual pass or a build-time commit-stamping mechanism
is explicitly requested as separate, future work.
