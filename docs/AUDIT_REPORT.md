# RAI Numerical-Honesty Audit Report

**Date:** 2026-09-12
**Scope:** every number the evaluation harness, the live API, and the documentation present as
a measured result, checked against the code path that supposedly produced it.
**Rule being enforced** (`CLAUDE.md`, non-negotiable): *"Never fabricate a metric. If a model
has not been evaluated, the value is `null`, not a plausible-looking number."*
**Method:** for each claimed number, find the function that allegedly computes it, run it, and
compare. Where the function didn't exist, or existed but was never called, or existed and was
called but its output was discarded in favour of a literal — that is recorded below as a
finding, with the fix applied and the real number it produced instead.

This document supersedes the numbers in `docs/EVALUATION_FORENSICS.md` and
`docs/PHASE_2_JUDGE_PACKAGE.md`, both of which rubber-stamped several of the fabrications found
here. `docs/EVALUATION.md` is the up-to-date, kept-in-sync evaluation reference; this report is
the historical record of what was wrong and why.

---

## 1. Summary for judges / reviewers

The core pipeline (simulation → expected-behaviour models → residual fusion → environment
attribution → risk scoring → evidence packet) is real and works: 141/141 backend tests pass,
the frontend builds cleanly, discrimination between real faults and 30 healthy/environmental
look-alikes is 12/12 with 0 false alarms in a live run. **The evaluation *report* built on top
of that pipeline contained multiple fabricated headline numbers** — most importantly a 13.5-day
median lead time and three "generalization gate" PR-AUC values (0.931 / 0.894 / 0.902) that no
function in the repository ever computed. Those have been corrected to real, reproducible
numbers, which are lower but genuine: **5.0-day median lead time, CARE score 0.797.** Every
fabrication found is listed below with its fix. Two "not computed" gaps (Level 4 OOD, the alert
fatigue funnel) were left as `null`/"not computed" rather than patched with a second invented
number, per the project's own honesty rule.

---

## 2. Findings

### 2.1 Lead-time measurement used single-snapshot evaluation, not walk-forward (CRITICAL)

- **Where:** `rai/eval/benchmarks.py`, all five `predict_window` implementations.
- **Symptom:** median lead time reported as 0.01 days for every candidate — a number close to
  zero because each candidate was scored once, at the end of the observation window, not at the
  point in time an operator would actually have seen the alarm fire.
- **A separate, actively-marketed figure of "13.5 days"** appeared in `docs/EVALUATION_FORENSICS.md`
  and `docs/PHASE_2_JUDGE_PACKAGE.md`. Neither the 0.01-day nor the 13.5-day number came from a
  correct walk-forward measurement; 13.5 does not correspond to any code path found in the repo.
- **Fix:** added `_walk_forward_first_alarm()` — for each ground-truth event, steps forward in
  24-hour increments from `onset - 3 days` to `failure`, calling each candidate's detector at
  each timestamp, and records the first timestamp that fires. All five `predict_window`
  signatures now accept `asset_events` and use this when provided.
- **Verified result (real, reproducible via `python scripts/evaluate.py`):**

  | Candidate | Median lead time (old, bogus) | Median lead time (new, real) |
  |---|---:|---:|
  | `baseline_4_isolation_forest` | 0.01 d | **6.0 d** |
  | `challenger_hybrid_ensemble` | 0.01 d | **5.0 d** |

  The champion's CARE score moved from 0.659 to **0.797** as a direct consequence (earliness
  and coverage components both improved once lead time was measured correctly).

### 2.2 Risk calibration used hand-typed synthetic labels, not the trained risk model

- **Where:** `scripts/evaluate.py`.
- **Symptom:** `sim_y_true`/`sim_y_prob` were literal Python lists such as
  `[0.82 if yt == 1 else 0.12 + noise ...]` — a distribution manufactured to produce a good-
  looking Brier score, not sourced from any model.
- **Fix:** calibration is now computed from `build_evidence_packet(asset_id).risk.risk_score`
  for every asset in the fleet, against the real fault/no-fault label.
- **Verified result:** Brier = **0.0439**, ECE = **0.0915** (real, from the trained risk model).
  Caveat carried into `docs/EVALUATION.md`: the independent event count is small (6 events), so
  treat this as a diagnostic, not proof of field calibration.

### 2.3 Decision regret was a tautology (chosen compared against itself)

- **Where:** `scripts/evaluate.py`, decision-regret block.
- **Symptom:** `chosen = dec_res.scenarios[0]` and `opt = dec_res.scenarios[0]` — the same
  object — so `Regret = Cost(chosen) - Cost(opt)` was 0 by construction on every run, and the
  report presented this as "100% optimal policy rate."
- **Fix:** `opt` is now `min(dec_res.scenarios, key=lambda s: s.midpoint_cost_inr)` — a genuine
  argmin over the scenario set rather than an alias.
- **Result is still ₹0 regret, and this is now explained rather than hidden:** the decision
  engine's own top-ranked recommendation is already the argmin under the same cost model it's
  being checked against, so this remains a **self-consistency check on the engine's internal
  ranking**, not an independent validation of decision quality against a realized outcome. A
  real regret measurement needs a ground truth the engine didn't have access to when it made
  the recommendation, which the current harness does not have.
- Also fixed in the same pass: `failure_probability` was a constant `0.75` for every event
  (now `packet.risk.risk_score`, per-asset); wind/solar intervention costs were hardcoded
  constants (now via `economics_for(component)` in `rai/config.py`); the `DecisionEvidence`
  fallback used hardcoded `evidence_score=0.85, confidence=(0.75, 0.90), available_signals=3,
  persistence_hours=14.0` for every asset regardless of its actual evidence (now populated from
  the asset's real evidence packet).

### 2.4 The "Alert Fatigue Reduction Funnel" (3,218 → 742 → 93 → 17 → 4) was reverse-engineered, not measured

- **Where:** found independently hardcoded in **six locations**: `scripts/evaluate.py` (JSON
  payload, markdown table, and print statement — three sub-sites), `services/api/routers/evaluation.py`,
  `docs/EVALUATION_FORENSICS.md`, `docs/PHASE_2_JUDGE_PACKAGE.md`, `README.md`, and
  `docs/EVALUATION.md`.
- **Symptom:** `compute_alert_fatigue_funnel(raw_rate_per_year=3218.4, persistence_filter_ratio=0.2305,
  environmental_filter_ratio=0.1253, peer_consensus_ratio=0.1828, confidence_gating_ratio=0.2353, ...)`
  — four filter ratios chosen so that `3218.4 × 0.2305 × 0.1253 × 0.1828 × 0.2353 ≈` the exact
  sequence 3218 → 742 → 93 → 17 → 4 the report wanted to show. Nothing in the codebase counts
  how many raw residual exceedances actually pass through the persistence, environmental,
  peer-consensus, and confidence gates.
- **Fix:** the call and all four downstream literals were removed from every location listed
  above and replaced with an explicit "not computed" statement, plus a note that the four gates
  themselves are real and exist (`rai/models/anomaly.py` persistence gate, `rai/models/environment.py`
  environmental gate, `rai/models/peers.py` peer-consensus gate, `rai/agent/fallback.py`
  confidence threshold) — only the *counting* of what each gate removes across the fleet was
  never implemented.
- **The one real, load-bearing number that survives:** false-alarm rate for the champion, from
  the CARE benchmark's actual alarm timestamps, is **0.19 / asset-year**. This is genuinely
  measured and is cited in place of the funnel wherever the funnel used to appear.

### 2.5 Live API (`GET /api/evaluation`) served hardcoded fallback numbers, not the evaluation artifact

- **Where:** `services/api/routers/evaluation.py`.
- **Symptom:** the endpoint read `results.json` but pulled fields via
  `data.get("some_key", HARDCODED_NUMBER)` where `some_key` never existed in the file — so the
  hardcoded default fired on every single request, unconditionally. This included a fabricated
  `tracks.track_b` object asserting *"Official CARE Reference... Protocol adapter verified"* —
  i.e., the live API was telling any UI or judge who queried it that an external benchmark had
  been run, when it had not — plus fully invented `decision_regret` and `alert_fatigue_funnel`
  blocks independent of the ones in `scripts/evaluate.py`.
- **Fix:** rewrote `get_evaluation_metrics()` to load `artifacts/evaluation/results.json` and
  return its fields verbatim (dataset stats, benchmark list, champion model, generalization
  levels, calibration bins, latencies), with an honest `{"available": False, "reason": ...}`
  response when the file is missing or unreadable, instead of a schema that always looks
  populated.
- **Verified via a live smoke test** (`fastapi.testclient.TestClient`):
  ```
  GET /api/health      → 200 {'status': 'ok', 'needle_available': True, 'assets': 42, ...}
  GET /api/evaluation   → available: True
  champion_model: {'model': 'challenger_hybrid_ensemble', 'care_score': 0.7968,
                    'pr_auc': 0.9484, 'coverage': 0.8333, 'accuracy': 0.9842,
                    'reliability': 0.984, 'earliness': 0.3857,
                    'false_alarms_per_year': 0.19, 'median_lead_days': 5.0}
  ```
  Every field traces to `results.json`; no invented defaults remain in the response.

### 2.6 Level 2 / Level 3 / Level 4 generalization metrics were invented, not computed

- **Where:** `docs/EVALUATION_FORENSICS.md`, `docs/PHASE_2_JUDGE_PACKAGE.md`, and an earlier
  version of `CHECKPOINT.md`.
- **Symptom:** a table stated Level 2 (asset holdout) PR-AUC 0.931, Level 3 (cross-site) PR-AUC
  0.894, Level 4 (synthetic OOD challenge) PR-AUC 0.902. No function anywhere in the repository
  computes a cross-site transfer score or re-simulates OOD perturbations; `generate_ood_challenge_factors`
  existed but was never called from the evaluation entry point.
- **Fix:** added `score_subset()` to `rai/eval/benchmarks.py`, which re-derives the
  classification battery for a named subset of assets from scores the benchmark suite already
  computed (no re-run of the pipeline needed). Used this for:
  - **Level 2 (asset holdout):** by chance, none of the 6 faulted assets fell into the random
    10-asset holdout set in the current split, so there are zero positive examples in that
    subset — `score_subset` correctly returns `None` rather than a division-by-zero or a
    fabricated value. This is now reported as **"not computed this run"** with the reason
    stated, not silently dropped.
  - **Level 3:** reframed honestly. Wind and solar use disjoint feature schemas by design (a
    gearbox has no module temperature) — there is no single model whose cross-site transfer is
    meaningful to test. Reported instead as **per-fleet fusion-layer performance**: Kutch wind
    PR-AUC 1.000 (n=18, 4 positive), Charanka solar PR-AUC 1.000 (n=24, 2 positive) — both
    explicitly flagged as small-n and indicative, not decisive.
  - **Level 4 (OOD):** left as **"not computed"**, with the withdrawal of the prior 0.902 claim
    stated explicitly rather than silently removed.

### 2.7 Fake external benchmark ("Track B" / CARE to Compare)

- **Where:** `README.md`, `scripts/evaluate.py`'s JSON payload, `docs/EVALUATION_FORENSICS.md`.
- **Symptom:** a "Two-Track Benchmark" narrative implying the real, external *CARE to Compare*
  academic dataset (Gück et al. 2024 — 36 turbines, 3 farms, 44 anomalous frames) had been
  ingested and scored ("Track B... protocol adapter verified"). `rai/eval/care.py` does contain
  `ExternalCAREBenchmarkSpec` and `TwoTrackBenchmarkSummary` dataclasses, but they are
  descriptive metadata only — no ingestion or scoring code exists behind them. That module's own
  `sample_size_summary` field literally carries the string `"217,728 timestamps (large)"` and an
  `honesty_declaration` string asserting things not backed by any execution — the module's
  self-description was itself part of the fabrication.
- **Fix:** removed the `tracks.track_a`/`tracks.track_b` structure from `scripts/evaluate.py`'s
  output and replaced it with an `evaluation_scope` block stating plainly that only the internal
  synthetic fleet has been evaluated, with an `external_benchmark_note` explaining that the
  external CARE dataset is referenced but not run. `README.md`'s "Two-Track Benchmark" section
  was rewritten to say Track B "not run" with the reason.

### 2.8 Cold-path inference latency was measured after cache warm-up

- **Where:** `scripts/evaluate.py`.
- **Symptom:** `compute_asset_state` was timed *after* the benchmark suite had already called it
  (and populated its cache) for the same assets — producing a "0.0 ms" or otherwise
  unrealistically fast reading that had appeared elsewhere as "~3.1ms."
- **Fix:** call `clear_cache()` immediately before each timed call, across 6 sample assets.
- **Verified result (reproducible, varies slightly run to run):** p50 ≈ **676–870 ms**, not 0 ms
  and not 3.1 ms. `docs/EVALUATION.md` and `CHECKPOINT.md` both flag that a live deployment
  should serve from the precomputed `artifacts/state/*.json` snapshots the API already uses, not
  compute this synchronously per request.

### 2.9 Real static-analysis bug: `rai/decision/models.py`

- **Symptom:** `contributors: tuple[dict[str, Any], ...]` used `Any` without importing it —
  a real `NameError`-class bug (F821 under `ruff`), not a fabrication finding but a genuine
  defect surfaced while auditing this module for hardcoded numbers.
- **Fix:** added `from typing import Any`. Verified clean via `ruff check rai/decision/models.py`
  and a standalone `pyright` run.

### 2.10 Documentation accuracy claims that didn't hold up

- **`CHECKPOINT.md` claimed "Pyright clean, 0 errors."** The IDE-integrated pyright instance
  feeding earlier system messages was misconfigured (wrong venv path), producing false
  `reportMissingImports` noise. Running the standalone `pyright` CLI against the project's own
  `pyrightconfig.json` gives the real result: **1 error, 405 warnings** (mostly `X | None`
  attribute access not narrowed before use). Corrected in `CHECKPOINT.md`.
- **Fleet composition was stated backwards** in `CHECKPOINT.md`/`README.md` ("24 wind turbines,
  18 solar inverters") versus `rai/config.py`'s actual `WIND_TURBINE_COUNT = 18,
  SOLAR_INVERTER_COUNT = 24`. Corrected.
- **A stale module reference** (`rai/memory/cases.py`, which doesn't exist) corrected to the
  real files `rai/memory/library.py`, `rai/memory/retrieval.py`.
- **Frontend build claim was checked and found accurate:** `npm run build` in `web/` completes
  cleanly (Next.js 16.3.5 Turbopack, 8 routes). No correction needed — recorded here so this
  claim isn't mistaken for another unverified one.

### 2.11 `needle_available: True` in `/api/health` — checked, found genuine

Given the pattern of fabricated-looking claims found elsewhere, this health-check field was
independently verified rather than assumed. `rai/agent/runtime.py::needle_available()` is a
real `try/except` probe: it imports `needle` and attempts `needle.Needle(system="probe")`,
returning `True` only if construction succeeds, `False` with a reason otherwise, cached for the
process lifetime. A **fresh Python process** (not reusing any warm cache) was run to confirm
this independently:

```
$ python -c "from rai.agent.runtime import needle_available; print(needle_available())"
(True, 'needle 2 session constructed')
```

This is a genuine, non-fabricated result — not a hardcoded value.

---

## 3. What was intentionally left as "not computed" rather than patched

Per the project rule that an unevaluated value is `null`, not a plausible number, the following
remain open and are reported as such everywhere they appear:

| Gap | Where it's marked | Why it wasn't computed here |
|---|---|---|
| Level 4 synthetic OOD challenge | `docs/EVALUATION.md`, `CHECKPOINT.md` | No perturbation-and-rescore code exists; building it is a real implementation task, not a quick fix. |
| Alert fatigue funnel (per-gate exceedance counts) | `docs/EVALUATION.md`, `scripts/evaluate.py` output | The four gates exist but nothing counts flow through each one across the fleet; needs new instrumentation in `rai/models/anomaly.py`/`environment.py`/`peers.py`/`rai/agent/fallback.py`. |
| External CARE-to-Compare benchmark (Track B) | `README.md`, `docs/EVALUATION.md` | No ingestion adapter for the real academic dataset has been built; `rai/eval/care.py` is descriptive metadata only. |
| Independent decision-regret ground truth | `docs/EVALUATION.md` | Requires an outcome the engine didn't see when recommending, which this synthetic harness does not generate. |
| Level 2 asset-holdout PR-AUC (this run) | `CHECKPOINT.md` | Zero positive examples fell into the current random holdout by chance (6 faults across 42 assets); needs either a larger event count or a stratified holdout that guarantees positives on both sides. |

---

## 4. Verified-true claims (for balance — not everything was wrong)

- 141/141 backend unit tests pass (`pytest tests/ -q`), before and after every fix in this audit.
- The soiling/environment discrimination fix from before this audit holds: 12/12 correct
  discrimination between real equipment faults and environmental/peer look-alikes, 0 false
  alarms across 30 healthy assets, verified via a live script run.
- `npm run build` in `web/` completes cleanly.
- The four alert-fatigue gates (persistence, environmental, peer-consensus, confidence) are real
  code, correctly wired into the evidence pipeline — only their *aggregate counting* was
  fabricated, not their existence.
- `needle_available()` in the live API is a genuine probe (§2.11), not a hardcoded value.

---

## 5. Corrected headline numbers (for judges)

| Metric | Previously claimed | Verified (this audit) |
|---|---:|---:|
| Champion CARE score | 0.659 → later inflated elsewhere | **0.797** |
| Champion PR-AUC | — | **0.948** |
| Champion median lead time | **13.5 days** (fabricated) | **5.0 days** |
| Champion false alarms / asset-year | — | **0.19** |
| Risk calibration Brier / ECE | synthetic hand-typed | **0.0439 / 0.0915** (real model output) |
| Cold-path inference latency (p50) | ~3.1 ms (fabricated) / 0 ms (cache bug) | **~676–870 ms** |
| Level 2 asset-holdout PR-AUC | 0.931 (fabricated) | not computed this run (0 positives in holdout) |
| Level 3 cross-site PR-AUC | 0.894 (fabricated, and conceptually incoherent) | per-fleet: wind 1.000 (n=18), solar 1.000 (n=24), small-n |
| Level 4 OOD PR-AUC | 0.902 (fabricated) | not computed |
| Alert fatigue funnel | 3,218→742→93→17→4 (reverse-engineered) | not computed; real FA/yr = 0.19 |
| Decision regret | ₹0, "100% optimal" (tautological) | ₹0, but now a real (if circular) argmin comparison — self-consistency check only |
| External CARE-to-Compare benchmark | "protocol adapter verified" | not run |

---

## 6. Scope limitations of this audit

Stated plainly, per the same honesty standard applied to the rest of this report:

- `docs/EVALUATION_FORENSICS.md` and `docs/PHASE_2_JUDGE_PACKAGE.md` each received a retraction
  notice at the top rather than a full line-by-line rewrite — both documents are long and built
  entirely around the fabricated numbers; correcting every sentence in place would cost more
  time than remained. Treat this report and `docs/EVALUATION.md` as authoritative; treat those
  two documents as historical artifacts with a known-bad core.
- `rai/decision/engine.py`, `policy.py`, `scenarios.py`, `value_of_information.py`,
  `rai/environment/*.py`, and `rai/models/fleet_common_cause.py` were grepped for the same
  `.get(key, HARDCODED_NUMBER)` fabrication pattern (none found) and their tests confirmed
  passing, but were not read end-to-end line by line the way the files in §2 were.
- This audit ran on a shared, actively-developed working tree (multiple concurrent sessions
  committing to the same OneDrive-synced folder throughout). Fixes were re-applied against the
  latest on-disk state whenever a file changed underneath an in-progress edit, and re-verified
  by rerunning tests and the evaluation script afterward — but a reader should treat "verified
  at audit time" as of 2026-09-12, not as a permanent guarantee if the surrounding code moves
  again.

---

## 7. How to reproduce every number in this report

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q          # 141/141
.venv\Scripts\python.exe scripts\evaluate.py           # regenerates artifacts/evaluation/*
.venv\Scripts\python.exe -c "from rai.agent.runtime import needle_available; print(needle_available())"
ruff check .
pyright                                                 # standalone CLI, not an IDE plugin
```

`artifacts/evaluation/results.json`, `summary.md`, and `metrics.csv` are regenerated fresh by
`scripts/evaluate.py` on every run and are the single source of truth `services/api/routers/evaluation.py`
now serves verbatim.
