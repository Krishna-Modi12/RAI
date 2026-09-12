# Task Plan — RAI Phase 2 Hardening, Scientific Validation & Next-Generation Decision Intelligence

## Goal
Transform the Renewable Asset Intelligence (RAI) system from a prototype with potentially over-claimed numbers into a scientifically rigorous, defensible, leak-free decision system with two-track evaluation, modularized environmental and decision intelligence, and complete forensic audit.

## Architecture Vision
```
RENEWABLE ASSET INTELLIGENCE
  │
  ├── ASSET TELEMETRY + SENSOR HEALTH (stuck, drift, impossible, missing)
  │     ▼
  ├── ENVIRONMENTAL CONTEXT (Weather / CAMS / Dust integral / Rain / Clear-sky)
  │     ▼
  ├── PERSONALIZED DIGITAL TWIN (Expected Behavior + Residuals + Peer Consensus)
  │     ▼
  ├── ANOMALY ENGINE + COMMON-CAUSE FILTER (Asset-specific vs Fleet-wide Event)
  │     ▼
  ├── ATTRIBUTION DECOMPOSITION (Model-based loss attribution with CI)
  │     ▼
  ├── RISK + PROBABILISTIC CALIBRATION (Brier, ECE, Reliability Diagram)
  │     ▼
  ├── HISTORICAL CASE MEMORY + RAG (Leakage-free k-NN, FTS5)
  │     ▼
  ├── COUNTERFACTUAL ENGINE (Maintenance actions + Environmental weather scenarios)
  │     ▼
  ├── ECONOMIC OPTIMIZER (Expected cost, Decision Regret, Value of Information)
  │     ▼
  └── LOCAL AGENT + HUMAN-REVIEWED ACTION (Evidence Graph + Ledger)
```

## Execution Gates

Work through these gates in order. Do not add new product features until Gate 1 and Gate 2 are stable.

- [x] **Gate 1A: Repo reality check**
  - Verified current repository contains telemetry store, simulation, expected behavior, anomaly/risk, environment, decision, RAG, API, frontend, and evaluation modules.
  - Identified documentation drift: some docs still over-claim compared with actual `artifacts/evaluation/results.json`.
  - Added `docs/research/optimal-rai-architecture-2026-09-12.md` with current research-backed build gates.
- [x] **Gate 1B: Honest baseline artifact structure**
  - `scripts/evaluate.py` now writes top-level evaluation artifacts and copies the same baseline run into `artifacts/evaluation/baseline/`.
  - Calibration bins are exported to `artifacts/evaluation/calibration/bins.csv`.
  - `docs/EVALUATION.md` now separates measured values from planned external/OOD validation.
- [ ] **Gate 1C: Run and preserve current baseline**
  - Run `python scripts/evaluate.py`.
  - Confirm creation of baseline results, metrics, summary, and calibration bins.
  - Do not tune models based on these results.
- [ ] **Gate 2: Leakage-safe model evaluation**
  - Add scaler, threshold, calibration, event, and retrieval leakage guards.
  - Create tests proving held-out cases cannot retrieve themselves and future cases remain inaccessible.
- [ ] **Gate 3: Model improvement**
  - Compare physics, expected regression, residual, isolation forest, changepoint, and hybrid under the same split protocol.
  - Select champion using leakage-free, false-alarm-aware, lead-time-aware policy.
- [ ] **Gate 4: Environmental intelligence**
  - Validate dust exposure, soiling estimation, rain cleaning, clear-sky normalization, and cleaning regret.
  - Add environmental ablations.
- [ ] **Gate 5: Decision intelligence**
  - Validate historical retrieval, counterfactual scenarios, do-nothing/wait policy, economics, and regret.
- [ ] **Gate 6: Agent and RAG**
  - Use only stable numerical evidence and retrieved sources.
  - Measure schema validity, evidence coverage, unsupported claims, correct escalation, and latency.
- [ ] **Gate 7: UI**
  - Align pages to actual backend outputs and measured evaluation status.
- [ ] **Gate 8: Optional operations**
  - Add route optimization only after the above gates are stable.

## Original Phase Backlog

- [ ] **Phase 1: Evaluation Forensics Audit (`docs/EVALUATION_FORENSICS.md`)**
  - Audit all reported claims (CARE=0.659, PR-AUC=0.948, FA/yr=0.19, Brier=0.017, ECE=0.1286, 13.5d lead time, 0.931 unseen-asset, 0.894 site-transfer, 0.902 OOD, 100% additive decomposition).
  - Classify each claim: VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / INCORRECT.
  - Build Event-Count table (45,360 hours vs 6 equipment failure events).
- [ ] **Phase 2: Modularize Environmental Intelligence (`rai/environment/`)**
  - Refactor into `weather_provider.py`, `dust.py`, `rain.py`, `clearsky.py`, `soiling.py`, `attribution.py`, `cleaning_optimizer.py`.
  - Add cumulative dust exposure integral (3h, 12h, 24h, 72h, 7d, 14d).
  - Model-based attribution with confidence intervals.
  - Maintain backwards-compatible aliases in `rai/models/environment_solar.py`.
- [ ] **Phase 3: Decision Intelligence Hardening (`rai/decision/`)**
  - Modularize into `scenarios.py`, `regret.py`, `value_of_information.py`, `policy.py`.
  - Implement decision regret ($\text{Regret} = \text{Cost}_{\text{chosen}} - \text{Cost}_{\text{optimal}}$).
  - Implement Value of Information ($\text{VOI}$).
  - Implement sensitivity analysis ("what would change the decision?") and risk attribution ("why did risk change?").
- [ ] **Phase 4: Fleet Intelligence (Common-Cause & Sensor Health)**
  - Implement fleet-wide simultaneous event detection (`rai/models/common_cause.py`).
  - Implement sensor health gating (`rai/models/sensor_health.py`).
  - Implement Alert Fatigue Reduction Funnel (Raw -> Persistence -> Environmental -> Peers -> Gated).
- [ ] **Phase 5: Two-Track Evaluation Harness (`rai/eval/`, `scripts/evaluate.py`)**
  - Track A: RAI Fleet Benchmark (`RAI Operational Score (CARE-inspired)`).
  - Track B: External Wind Benchmark (Official CARE framework reference & protocol).
  - Proper within-domain site holdout vs cross-domain transfer documentation.
  - Calibration reliability diagram bin export (`calibration/bins.csv`, `summary.md`).
  - Decision regret metrics computation.
- [ ] **Phase 6: API & UI Alignment**
  - Update FastAPI endpoints for updated metrics and decision regret.
  - Update Next.js frontend (`evaluation`, `soiling`) with honest labels, alert funnel, and calibration charts.
  - Verify `npm run build`.
- [ ] **Phase 7: Judge Package & Documentation Hardening**
  - Generate `docs/PHASE_2_JUDGE_PACKAGE.md`.
  - Update `README.md` and `docs/EVALUATION.md`.
- [ ] **Phase 8: Complete Verification & Test Battery**
  - Run `pytest` (all existing + new tests passing).
  - Run `ruff check .` & `pyright`.
  - Run `python scripts/evaluate.py`.
  - Run `python scripts/demo.py --all`.
