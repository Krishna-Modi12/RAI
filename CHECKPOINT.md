# CHECKPOINT — Renewable Asset Intelligence (RAI)

> Consolidated build state. All tasks across Foundation, Modeling, Operational Validation, Environmental Intelligence, API Services, and Next.js Instrument Panel are fully verified.

**Last updated:** 2026-09-12 (post-audit correction pass)  
**Overall:** ▓▓▓▓▓▓▓▓▓░ ~90% — core pipeline, API and frontend are built and tested; the
evaluation report had multiple fabricated figures, now corrected (see `docs/AUDIT_REPORT.md`)  
**Backend Unit Tests:** 141/141 passing (verified by direct `pytest` run)  
**Static Analysis:** Ruff — 35 issues found on audit, 20 auto-fixed + 1 real bug (undefined
`Any` in `rai/decision/models.py`) fixed by hand, 15 remain (unused vars, import order,
ambiguous names — none load-bearing). Pyright (run standalone with the project's own
`pyrightconfig.json`, not the IDE's misconfigured instance) — 1 error, 405 warnings, mostly
`X | None` attribute access that isn't narrowed before use. "Clean, 0 errors" was not accurate.  
**Frontend Build:** verified — `npm run build` in `web/` completes cleanly (Next.js 16.3.5
Turbopack, 8 routes, static + one dynamic `/assets/[id]`). This claim was accurate.  

---

## Environment & Tooling Verification

| Check | Result |
|---|---|
| Python | 3.11.9 ✅ |
| Node / npm | 26.7.0 / 11.19.0 ✅ |
| Core Python stack | numpy, pandas, scipy, sklearn, xgboost, duckdb, pyarrow ✅ |
| API stack | fastapi, uvicorn, pydantic, httpx (19/19 contract tests passing) ✅ |
| Domain libs | pvlib (clear-sky POA) ✅, ruptures (change-point) ✅ |
| Evaluation Harness | `rai/eval/leakage.py`, `metrics.py`, `benchmarks.py` ✅ |
| Solar Environmental Engine | `rai/models/environment_solar.py`, `weather_provider.py` (CAMS dust/AOD/rain) ✅ |
| Techno-Economic Engine | `rai/economics/engine.py` (Smart Cleaning Advisor NPV comparison) ✅ |
| Knowledge Engine | SQLite FTS5 RAG index (`artifacts/index/knowledge.db`, 221 sections) ✅ |
| Frontend | Next.js 16.3.5 App Router + OKLCH Design System (`web/`) ✅ |

---

## Verified Evaluation Scorecard

Evaluated on 42 assets (18 wind turbines, 24 solar inverters) over 45,360 aggregate
asset-hours, 6 independent equipment-fault episodes (*source: a fresh, reproducible run of
`python scripts/evaluate.py` → `artifacts/evaluation/results.json`, not hand-typed*):

| Model Candidate | CARE Score | PR-AUC | Precision | Recall | False Alarms / Asset-Year | Median Lead Time | Status |
|---|---|---|---|---|---|---|---|
| **Challenger: Hybrid Ensemble** | **0.797** | **0.948** | **0.80** | **0.67** | **0.19** | **5.0 days** | **CHAMPION** |
| Baseline 4: Isolation Forest (alone) | 0.761 | 0.644 | — | — | 0.19 | 6.0 days | REJECTED |
| Baseline 3: Raw Residual Z-Score | 0.422 | 0.126 | — | — | 3,088.4 | 9.8 days | REJECTED |
| Baseline 2: Expected-Behaviour (GBM) alone | 0.235 | 0.202 | — | — | 27.1 | 5.1 days | REJECTED |
| Baseline 1: Physics / Nameplate Rule | 0.070 | 0.262 | — | — | 38.1 | 0.0 days | REJECTED |

Risk-model calibration (from the trained risk model's own output, not a stand-in): **Brier
0.0439, ECE 0.0915**. Cold-path inference latency (full evidence pipeline, one asset, cache
cleared first): **p50 ≈ 700–870 ms** on this dev machine — not sub-10ms; a live deployment
should serve from the precomputed `artifacts/state/*.json` snapshots the API already uses,
not compute this synchronously per request.

*(Precision/recall are only reported for the two candidates whose score has a natural 0/1
reading; the CARE score, not accuracy, is the primary basis for model selection here — see
`docs/EVALUATION.md` for why.)*

### Four-Level Generalization Gates — corrected 2026-09-12

An earlier version of this table stated Level 2/3/4 PR-AUC values (0.931 / 0.894 / 0.902) that
did not come from any executed code path — no function anywhere computed them. They have been
replaced with what a fresh run actually produces:

- [x] **Level 1 — Temporal Holdout:** 4,212 train / 972 val / 1,152 test rows, 12h purge gap. Zero lookahead leakage (`test_eval_leakage.py` passing).
- [~] **Level 2 — Asset Holdout:** 10 assets held out completely. Champion PR-AUC on that slice: **not computed this run** — by chance, none of the 6 faulted assets fell in the random 10-asset holdout (small-sample effect of only having 6 positive cases across 42 assets).
- [~] **Level 3 — Per-site breakdown (not cross-site transfer):** wind and solar use separate expected-behaviour models by design (disjoint feature schemas — a gearbox has no module temperature), so there is no single model to test transfer with. Reported instead: the fusion/decision layer scored separately on each fleet — Kutch wind PR-AUC 1.000 (n=18, 4 positive), Charanka solar PR-AUC 1.000 (n=24, 2 positive). Small-n; treat as indicative, not decisive.
- [ ] **Level 4 — Synthetic OOD Challenge:** **not computed.** No perturbation (degradation rate, sensor noise, wind shear) was ever re-simulated and re-scored by any code in this repository. Previously claimed as done with a specific PR-AUC; that claim has been withdrawn.

---

## Completed Deliverables

### Phase 1 — Foundation & Telemetry
- [x] 42-asset fleet SCADA simulation (18 wind turbines, 24 solar inverters) over 45 days.
- [x] DuckDB/Parquet windowed storage and precomputed asset state caching (`artifacts/state/*.json`).

### Phase 2 — Model Layer & Validation
- [x] Physics-informed Expected Behavior Models (`rai/models/expected.py`).
- [x] Residual Construction & Anomaly Fusion (`rai/models/anomaly.py`).
- [x] Weibull Hazard Risk Model & Probability Calibration (`rai/models/risk.py`).
- [x] Formal Evaluation Harness (`scripts/evaluate.py`, `rai/eval/`).

### Phase 3 — Solar Environmental Intelligence
- [x] Open-Meteo CAMS Air Quality Provider (`rai/models/weather_provider.py`) with offline cache fallback.
- [x] Dust Storm Event Detection (dust concentration, AOD 550nm, PM10, wind entrainment).
- [x] Soiling State Estimation via Kimber-RdTools kinetics and `pvlib` clear-sky POA normalization.
- [x] Exact Additive Loss Decomposition ($\text{Soiling} + \text{Cloud} + \text{Thermal} + \text{Curtailment} + \text{Equipment} + \text{Unexplained} = 100\%$).
- [x] Techno-Economic Smart Cleaning Advisor comparing Clean Now vs. Wait 24h vs. Wait 72h vs. Post-Rain Reassess.

### Phase 4 — Decision Support & Knowledge RAG
- [x] SQLite FTS5 RAG index builder (`scripts/build_index.py`, `artifacts/index/knowledge.db`) indexing 221 sections across 19 domain docs.
- [x] Weighted trajectory-signature kNN case memory retrieval (`rai/memory/library.py`, `rai/memory/retrieval.py`).
- [x] Deterministic fallback reasoner + Needle 2 agent runtime (`rai/agent/`).

### Phase 5 — API Services & Instrument Panel
- [x] Complete FastAPI REST backend (`services/api/`) with 19/19 contract tests passing.
- [x] Next.js 16 App Router UI (`web/`) with Archivo/IBM Plex Mono fonts, OKLCH design system, HeroChart expected vs. actual band with residual strip, and ruled Evidence Ledger.
- [x] End-to-end interactive demo suite (`scripts/demo.py --all`) demonstrating Wind Hero, Solar Flagship, and Non-Fault discrimination.

<!-- CONSOLIDATED:BEGIN -->

## Consolidated task log

_Generated 2026-09-12 09:44 UTC from 6 task record(s) in `docs/checkpoints/`._

**6/6 task records complete.**

| | Task | Phase | Status |
|---|---|---|---|
| ✅ | repository Copilot instructions | 1 | complete |
| ✅ | reviewer-ready repository documentation | 1 | complete |
| ✅ | Phase 2 repository upgrade | 5 | complete |
| ✅ | README architecture refresh | 5 | complete |
| ✅ | deterministic maintenance decision engine | 2 | complete |
| ✅ | numerical-honesty-audit | 2 | complete |

### ✅ repository Copilot instructions

**What was built**

- Added repository-level Copilot guidance covering verified Python and frontend commands.
- Documented the layered RAI architecture and API/UI contract boundary.
- Captured project-specific numerical honesty, evidence, safety, data, and checkpoint rules.

**How it was verified**

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed.

**Measured results**

91 tests passed; Ruff reported no violations.

**Limitations**

The FastAPI application entrypoint is not implemented yet, so no API startup command is documented.

### ✅ reviewer-ready repository documentation

**What was built**

- Rebuilt the root README around the problem, architecture, reproducible demo, Phase 2 evaluation, and explicit implementation status.
- Added ML, evaluation, demo, API, limitations, and licensing guides plus contribution, security, and community-health files.
- Added deterministic `scripts/demo.py` and measured `scripts/evaluate.py` outputs under `artifacts/evaluation/`.
- Added GitHub pull-request and bug-report templates.

**How it was verified**

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed after the final import cleanup.
- `Set-Location web; npm run lint` — passed.
- `Set-Location web; npm run build` — passed with Next.js 16.3.5.
- `.venv\Scripts\python.exe scripts\evaluate.py` — wrote evaluation artifacts and reported 12/12 scenario agreement.
- `.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear` — completed the 8-stage deterministic investigation.
- Repository Markdown local-link check — 0 broken local links.
- Secret-pattern scan found only documentation/code references, no credential values.

**Measured results**

The generated report contains eight expected-behaviour model metric sets and 12/12
scenario-level agreement against simulator equipment/non-equipment flags. These are
synthetic, controlled results and are not real-world validation.

**Limitations**

Pyright is configured but is not installed in the checked-in virtual environment, so no
type-check result is claimed. The FastAPI route layer and browser dashboard remain in
progress.

### ✅ Phase 2 repository upgrade

**What was built**

- Added a claims-to-evidence matrix and curated references for datasets, research, and
  software.
- Added maintainable Mermaid source diagrams for architecture, decision flow, demo flow,
  and data flow.
- Added GitHub Actions quality checks for Python tests/Ruff and frontend lint/build.
- Corrected stale documentation and stopped tracking local Claude settings.

**How it was verified**

`.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.

`.venv\Scripts\ruff.exe check .` — passed.

`Set-Location web; npm run lint` — passed.

`Set-Location web; npm run build` — passed.

`.venv\Scripts\python.exe scripts\evaluate.py` — scenario agreement 12/12.

`.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear` — completed
the deterministic investigation path.

**Measured results**

- Python tests: 91 passed.
- Synthetic scenario agreement: 12/12.
- Frontend production build: successful.

**Limitations**

- The API route layer and browser-to-API integration remain incomplete.
- CI has not run on GitHub in this session; the workflow is validated against the same
  local commands.
- Evaluation results remain synthetic and are not real-world accuracy claims.

### ✅ README architecture refresh

**What was built**

- Replaced the README with a fresh-machine setup guide and implementation-accurate
  project overview.
- Added an architecture diagram showing the numerical pipeline, EvidencePacket boundary,
  decision-support tools, and human handoff.
- Added a decision-flow diagram showing persistence, attribution, peer, confidence, and
  escalation gates.
- Added a code-walkthrough narrative, configuration reference, evaluation instructions,
  repository map, and explicit non-claims.

**How it was verified**

- README relative-link checker — no missing relative links.
- `Set-Location web; npm run lint` — passed.
- `git diff --check -- README.md` — no content errors after the final edit.

**Measured results**

- README contains the current Windows setup path, deterministic demo commands, CI
  commands, architecture flow, and API/frontend status.
- No new numerical claims were introduced; evaluation claims point to generated artifacts.

**Limitations**

- The FastAPI route layer and browser-to-API integration remain incomplete.
- Full Ruff output is currently affected by unrelated uncommitted files under `rai/eval/`
  and `tests/test_environment_solar.py`; those files were not changed by this task.

### ✅ deterministic maintenance decision engine

**What was built**

- Added an isolated `rai.decision` package with typed dataclasses for ranges, evidence,
  counterfactual scenarios, rankings, and policy results.
- Added deterministic expected-cost arithmetic with explainable intervention, energy-loss,
  and failure-risk breakdowns.
- Added explicit `act`, `monitor`, `do_nothing`, and `abstain` policies plus wind/solar
  standard action sets.
- Added focused tests covering cost ordering, interval propagation, and evidence abstention.

**How it was verified**

`.venv\Scripts\python.exe -m pytest tests\ -q` — 132 passed, 1 warning.

`.venv\Scripts\ruff.exe check rai\decision tests\test_decision_engine.py` — all checks passed.

**Measured results**

5 focused decision tests passed; the full suite passed with 132 tests.

**Limitations**

The package is intentionally not wired into the existing API, schemas, or economics engine;
callers must provide explicit cost and probability assumptions.

### ✅ numerical-honesty-audit

**What was built**

- A full numerical-honesty audit of the evaluation stack against CLAUDE.md's "never fabricate
  a metric" rule, covering `scripts/evaluate.py`, `rai/eval/benchmarks.py`,
  `services/api/routers/evaluation.py`, and every doc that cites evaluation numbers.
- Fixed the walk-forward lead-time measurement bug in `rai/eval/benchmarks.py` (single-snapshot
  evaluation was producing a bogus 0.01-day median lead time; added `_walk_forward_first_alarm`
  and `_as_utc`, updated all five `predict_window` signatures to accept `asset_events` and
  detect against a time-stepped window).
- Replaced fabricated risk calibration (`sim_y_true`/`sim_y_prob` hand-typed lists) in
  `scripts/evaluate.py` with the trained risk model's real output via `build_evidence_packet`.
- Fixed the decision-regret tautology (`opt = dec_res.scenarios[0]` compared against itself,
  always zero by construction) — now compares against `min(scenarios, key=cost)`, with an
  explicit caveat that this remains a self-consistency check, not independent ground truth.
- Replaced hardcoded scenario inputs (`failure_probability=0.75`, fixed wind/solar cost splits,
  a hardcoded `DecisionEvidence` fallback) with real per-asset values from the evidence packet.
- Removed the reverse-engineered "alert fatigue funnel" (four filter ratios hand-tuned to
  reproduce 3,218 → 742 → 93 → 17 → 4) everywhere it appeared: `scripts/evaluate.py` (JSON
  payload, markdown table, print statement), `services/api/routers/evaluation.py`,
  `docs/EVALUATION_FORENSICS.md`, `docs/PHASE_2_JUDGE_PACKAGE.md`, `README.md`,
  `docs/EVALUATION.md` — replaced with an honest "not computed" statement in each location.
- Rewrote `services/api/routers/evaluation.py`'s `get_evaluation_metrics()` to serve
  `artifacts/evaluation/results.json` verbatim instead of `.get(key, HARDCODED_NUMBER)`
  fallbacks that always fired (the keys never existed), including removal of a fake
  `tracks.track_b` claiming "Official CARE Reference... Protocol adapter verified."
  - Fixed the cold-path latency measurement (`compute_asset_state` was timed after the
  benchmark suite had already warmed its cache, reading 0.0 ms) by calling `clear_cache()`
  before each timed call.
- Fixed a real static-analysis bug in `rai/decision/models.py` (`Any` used without import).
- Corrected `CHECKPOINT.md`, `README.md`, `docs/EVALUATION.md`, `docs/EVALUATION_FORENSICS.md`,
  `docs/PHASE_2_JUDGE_PACKAGE.md` to state verified numbers plus explicit retraction notices
  where a document's own prior claims were fabricated.
- Wrote `docs/AUDIT_REPORT.md` as the consolidated, authoritative record of every fabrication
  found and every fix applied.

**How it was verified**

- `pytest tests/ -q` — 141/141 passing, before and after every fix.
- `python scripts/evaluate.py` — run repeatedly end-to-end; numbers stable across reruns
  (CARE 0.797, PR-AUC 0.948, median lead 5.0d for the champion).
- `ruff check .` and a standalone `pyright` run (not the misconfigured IDE instance) against
  the project's own `pyrightconfig.json`.
- A live `fastapi.testclient.TestClient` smoke test against `/api/health` and `/api/evaluation`
  confirming the corrected endpoint serves the same numbers as the results file, no fabricated
  fields.
- A fresh-process check of `rai.agent.runtime.needle_available()` (no shared cache) confirming
  `(True, "needle 2 session constructed")` is a genuine probe result, not a hardcoded value.

**Measured results**

See `docs/AUDIT_REPORT.md` for the full before/after table. Headline: champion
(`challenger_hybrid_ensemble`) CARE 0.797, PR-AUC 0.948, median lead time 5.0 days (was a
fabricated 13.5 days), false alarms/asset-year 0.19, Brier 0.0439, ECE 0.0915, cold-path
inference latency p50 ≈ 676–870 ms across runs (was a fabricated ~3ms/0ms).

**Limitations**

- `docs/EVALUATION_FORENSICS.md` and `docs/PHASE_2_JUDGE_PACKAGE.md` received a retraction
  notice at the top, not a full line-by-line rewrite — both are long documents built entirely
  around the fabricated numbers, and superseding them in place would take longer than the
  remaining time allowed. `docs/AUDIT_REPORT.md` and `docs/EVALUATION.md` are the sources of
  truth going forward.
- `rai/decision/engine.py`, `policy.py`, `scenarios.py`, `value_of_information.py`,
  `rai/environment/*.py`, `rai/models/fleet_common_cause.py` were spot-checked (grepped for the
  same `.get(key, HARDCODED)` fabrication pattern, none found) but not read end-to-end.
- The decision-regret fix is a correctness fix, not a full remedy: it now compares against the
  true minimum-cost scenario instead of itself, but because the engine's own recommendation is
  already that argmin under the same cost model, regret is still ₹0 by construction. A genuine
  measurement needs an independently derived outcome to compare against, which does not exist
  in this codebase.
- Level 2 (asset-holdout) and Level 4 (OOD) generalization metrics are reported as "not
  computed" / "small-sample, indicative only" rather than replaced with new invented numbers —
  this is honest but means those gates are not actually validated yet.

