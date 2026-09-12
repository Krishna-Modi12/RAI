# Renewable Asset Intelligence (RAI)

**Predictive Maintenance & Environmental Risk Intelligence for Wind & Solar Fleets.**

Renewable Asset Intelligence (RAI) turns noisy SCADA telemetry and atmospheric composition forecasts into defensible, economically optimal operational interventions. It learns what an asset should be generating under prevailing ambient conditions, measures conditioned residuals, checks CAMS dust plumes, weather transients, curtailment, and peer behavior, retrieves comparable historical episodes, calculates the net financial consequence of waiting, and returns a confidence-gated recommendation for a human operator.

> **Implementation status:** 185 automated tests passing (verified by a direct `pytest` run). Time-ordered, leakage-free splits (`rai/eval/leakage.py`). Champion model, from a real reproducible run of `python scripts/evaluate.py`: **RAI Operational Score (CARE-inspired) = 0.797, PR-AUC = 0.948, FA/yr = 0.19/asset-year, median lead time = 5.0 days, Brier = 0.0439, ECE = 0.0915** across 45,360 monitored asset-hours ($N=6$ independent failure episodes — treat sub-breakdowns of that N as indicative, not decisive). No external benchmark dataset has been ingested or scored against ("Track B" elsewhere in this repo is a recorded dataset shape, not a result). Solar Environmental Intelligence with CAMS atmospheric dust exposure memory ($D(t)$), `pvlib` clear-sky POA normalization, and model-based loss attribution. **Read [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) before [`docs/EVALUATION_FORENSICS.md`](docs/EVALUATION_FORENSICS.md) or [`docs/PHASE_2_JUDGE_PACKAGE.md`](docs/PHASE_2_JUDGE_PACKAGE.md)** — both of the latter contain a "lead time" and an "alert fatigue funnel" figure that were never computed by any code in this repository; the audit report explains exactly which numbers to trust.

[![Quality](https://github.com/Krishna-Modi12/renewable-asset-intelligence/actions/workflows/quality.yml/badge.svg)](https://github.com/Krishna-Modi12/renewable-asset-intelligence/actions/workflows/quality.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](services/api/)
[![Next.js](https://img.shields.io/badge/Next.js-16.3.5-000000?logo=next.js&logoColor=white)](web/package.json)
[![Track A Operational Score](https://img.shields.io/badge/Track%20A%20Score-0.797-success)](docs/EVALUATION.md)
[![Audit Status](https://img.shields.io/badge/Forensics-Verified%20Clean-blue)](docs/EVALUATION_FORENSICS.md)

---

## Contents

- [Why RAI](#why-rai)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Champion–Challenger Operational Scorecard](#championchallenger-operational-scorecard)
- [Solar Environmental Intelligence & Soiling](#solar-environmental-intelligence--soiling)
- [Quick Start](#quick-start)
- [Running Demonstrations](#running-demonstrations)
- [Formal Evaluation](#formal-evaluation)
- [Repository Layout](#repository-layout)
- [Testing & Quality](#testing--quality)
- [Documentation](#documentation)

---

## Why RAI

Low renewable generation is inherently ambiguous. A sudden 20% power loss may be caused by internal mechanical degradation (e.g. high-speed bearing spalling), atmospheric dust ingress (soiling), monsoon cloud transients, grid curtailment directives, or pyranometer drift. A simple power threshold alarm cannot distinguish these root causes, causing either catastrophic component breakdown or costly operator alarm fatigue.

RAI answers three questions in under ten seconds:
1. **What changed:** Quantifies conditioned physical residuals ($z$-scores) against expected normal behavior.
2. **Is it real:** Eliminates environmental explanations (CAMS dust, cloud, rain) and checks fleet peer isolation before asserting an equipment fault.
3. **What does it cost to wait:** Calculates the Net Present Value ($\text{NPV}$) of intervening immediately vs. deferring 3 days vs. deferring 14 days.

---

## Key Features

| Capability | What it provides | Implementation |
|---|---|---|
| **Physics-Grounded Expected Behavior** | Normal generation expectations conditioned on wind speed, irradiance, ambient temperature, and pitch | `rai/models/expected.py` |
| **Residual Anomaly Fusion** | Fuses residual $z$-scores, Isolation Forest, and change-point detection with persistence filtering | `rai/models/anomaly.py` |
| **Fleet Common-Cause & Sensor Health** | Multi-asset correlation suppresses curtailment/storms; sensor validation flags frozen/stuck signals | `rai/models/fleet_common_cause.py`, `rai/models/sensor_health.py` |
| **Solar Environmental Intelligence** | CAMS dust exposure memory $D(t)$, deposition priors, RdTools SRR/CODS, and rain recovery kinetics | `rai/environment/` |
| **Model-Based Loss Attribution** | Decomposes derating into Soiling, Cloud, Thermal, Curtailment, and Equipment with uncertainty intervals | `rai/environment/attribution.py` |
| **Next-Gen Decision Intelligence** | Counterfactual futures, decision regret ($\text{Cost}_{\text{chosen}} - \text{Cost}_{\text{optimal}}$), VOI, and sensitivity bounds | `rai/decision/` |
| **Probabilistic Cleaning Optimizer** | Dynamic opportunity windows & Monte Carlo weather simulations for optimal intervention timing | `rai/environment/cleaning_optimizer.py` |
| **Historical Trajectory Memory** | Cosine similarity KNN retrieval of past degradation signatures with strict retrieval leakage guards | `rai/memory/cases.py` |
| **Technical Knowledge RAG** | SQLite FTS5 BM25 retrieval over 19 maintenance manuals, failure catalogs, and OEM SOPs | `rai/rag/` |
| **Deterministic Reasoning Agent** | Structured diagnosis and confidence-gated escalation with local Needle 2 runtime support | `rai/agent/` |
| **High-Density Instrument Panel** | Bloomberg-terminal density Next.js 16 UI with OKLCH tokens, HeroChart, and Evidence Ledger | `web/src/` |

---

## Architecture

RAI connects raw telemetry to an evidence-backed maintenance decision without allowing raw unverified data to reach the reasoning layer:

```
                         ┌─────────────────────────┐
                         │   LIVE ASSET TELEMETRY  │
                         │ SCADA / Inverter / Meter │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │   DATA QUALITY LAYER    │
                         │ missing / bad sensors /  │
                         │ status / curtailment    │
                         └────────────┬────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
        ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │ HEALTHY-STATE  │  │ ENVIRONMENTAL    │  │ FLEET / PEER     │
        │ MODEL          │  │ CONTEXT ENGINE   │  │ COMPARISON       │
        │ physics + GBM  │  │ CAMS dust/AOD/wx │  │ healthy peers    │
        └───────┬────────┘  └────────┬─────────┘  └────────┬─────────┘
                │                    │                     │
                └──────────────┬─────┴─────────────────────┘
                               ▼
                     ┌─────────────────────┐
                     │ RESIDUAL + ANOMALY  │
                     │     DETECTION       │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ CAUSE ATTRIBUTION   │
                     │ equipment / weather │
                     │ dust / curtailment  │
                     │ sensor / unknown    │
                     └──────────┬──────────┘
                                │
                   ┌────────────┼─────────────┐
                   ▼            ▼             ▼
             ┌──────────┐ ┌──────────┐ ┌──────────────┐
             │ RISK     │ │ HISTORY  │ │ KNOWLEDGE    │
             │ MODEL    │ │ MEMORY   │ │ RAG / SOPs   │
             └────┬─────┘ └────┬─────┘ └──────┬───────┘
                  │            │              │
                  └────────────┼──────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ ECONOMIC CONSEQUENCE │
                    │ repair / defer /     │
                    │ clean / monitor      │
                    └───────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ LOCAL NEEDLE2 AGENT │
                     │ evidence + tools    │
                     └──────────┬──────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ HUMAN-REVIEWED ACTION │
                    │ inspect / clean / wait│
                    │ / escalate            │
                    └────────────────────────┘
```

---

## Two-Track Benchmark & Operational Scorecard

To maintain strict scientific integrity, model evaluation is decoupled into two independent tracks:
1. **Track A — RAI Operational Score (CARE-inspired):** Evaluated on the 42-asset fleet (45,360 monitoring hours, 6 discrete failure episodes). This is the only track this repository actually runs.
2. **Track B — External Wind Benchmark (not run):** `rai/eval/care.py` records the *shape* of the official CARE to Compare dataset (Gück et al., 2024: 36 turbines, 3 farms) so an adapter could be built, but no code in this repository ingests or scores against it. Treat any "Track B" figure elsewhere in this repo as aspirational, not measured.

*Primary Artifacts: [`artifacts/evaluation/summary.md`](artifacts/evaluation/summary.md), [`artifacts/evaluation/results.json`](artifacts/evaluation/results.json) — both from a real, reproducible `python scripts/evaluate.py` run. See [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) before citing [`docs/EVALUATION_FORENSICS.md`](docs/EVALUATION_FORENSICS.md) or [`docs/PHASE_2_JUDGE_PACKAGE.md`](docs/PHASE_2_JUDGE_PACKAGE.md) — both contain figures that were never computed.*

### Sample Size & Event-Count Truth Table
> **Methodological Disclosure:** Evaluation sample size is extensive at the observation level (45,360 hours / 217,728 timestamps), but the independent failure-event count is small ($N=6$). All performance figures reflect these discrete physical failure trajectories.

| Asset Class | Fleet Assets | Monitored Hours | Failure Events | Normal Assets | Injected Fault Families |
|---|---|---|---|---|---|
| **Wind Turbines (WT)** | 18 | 19,440.0 h | **4 events** | 14 assets | Gearbox bearing spalling, Generator insulation, Main bearing wear |
| **Solar Inverters (INV)** | 24 | 25,920.0 h | **2 events** | 22 assets | Inverter bridge IGBT thermal fatigue, DC bus capacitor aging |
| **Fleet Total** | **42** | **45,360.0 h** | **6 events** | **36 assets** | **4 major equipment failure families** |

### Track A — Champion–Challenger Operational Scorecard

| Architecture Candidate | Tier | RAI Operational Score (CARE-inspired) | PR-AUC | Precision | Recall | MCC | False Alarms / Asset-Year | Median Lead Time | Status |
|---|---|---|---|---|---|---|---|---|---|
| **Challenger: Hybrid Ensemble** | Hybrid Fusion | **0.797** | **0.948** | **0.800** | **0.667** | **0.690** | **0.19** | **5.0 days** | **CHAMPION** |
| Baseline 4: Residual + Isolation Forest | Unsupervised ML | 0.761 | 0.644 | 0.714 | 0.833 | 0.730 | 0.19 | 6.0 days | CHALLENGER |
| Baseline 3: Raw Residual Z-Score | Statistical | 0.422 | 0.126 | 0.039 | 0.167 | -0.380 | 3,088.40 | 9.8 days | REJECTED |
| Baseline 2: Expected Behavior Only | Regression | 0.235 | 0.202 | 0.000 | 0.000 | 0.000 | 27.10 | 5.1 days | REJECTED |
| Baseline 1: Physics / Nameplate Rule | Rule-based | 0.070 | 0.262 | 0.000 | 0.000 | 0.000 | 38.10 | 0.0 days | REJECTED |

### Alert Fatigue Reduction Funnel — not computed
An earlier draft showed a five-stage funnel landing on 3,218 → 742 → 93 → 17 → 4 alerts/year.
Those numbers came from four filter ratios hardcoded to reproduce exactly that sequence, not
from measuring anything. The four gates are real (persistence, environmental attribution, peer
consensus, confidence threshold) but nothing yet counts how many raw exceedances each one
removes across the fleet. The one number in this family that **is** measured is the CARE
benchmark's false-alarm rate above: **0.19 false alarms / asset-year** for the champion,
computed from real alarm timestamps.

### Probabilistic Risk Calibration & Decision Regret
* **Brier Score:** `0.0439` *(mixes calibration, resolution, and uncertainty; low base rate drives score — from the risk model's own predictions, not a stand-in probability)*
* **Expected Calibration Error (ECE):** `0.0915` *(evaluated with reliability bins in `artifacts/evaluation/calibration/bins.csv`)*
* **Mean Decision Regret:** `₹0.00`, **100% "optimal"** across the 6 fault events evaluated — but "optimal" here means the decision engine's pick matches the lowest-cost option under the *same* cost model it used to choose, not an independently validated ground truth. This is a self-consistency check, not proof the recommendations are economically optimal in the field.

---

## Solar Environmental Intelligence & Soiling

Solar generation losses are ambiguous. RAI uses Open-Meteo CAMS atmospheric data as an **exposure prior**, not direct panel dirt:
- **Atmospheric Dust Chain:** CAMS Atmospheric Dust $\to$ Cumulative Environmental Exposure Memory $D(t)$ (over 3h, 12h, 24h, 72h, 7d, 14d) $\to$ Deposition Prior $\to$ Observed PV Performance $\to$ Soiling State Estimation.
- **Clear-Sky Normalization:** `pvlib` clear-sky Ineichen/Perez model normalizes plane-of-array (POA) irradiance, filtering cloudy and transient periods.
- **Soiling Baselines:** Evaluates Kimber empirical accumulation against RdTools SRR (Sensor-based Rate of Recovery) and CODS degradation estimators.
- **Model-Based Loss Attribution:** Derating is attributed to Soiling, Cloud Transients, Thermal Derating, Curtailment, and Equipment Degradation with uncertainty confidence intervals.
- **Cementation Risk Hypothesis:** Detects high risk when light precipitation ($<3\,\text{mm}$) interacts with high surface particulate loads ($>100\,\mu\text{g/m}^3$), producing adhered cementation rather than self-cleaning.
- **Probabilistic Cleaning Optimizer:** Dynamic cleaning opportunity detection comparing Clean Now vs. Wait 24h vs. Wait 72h vs. Post-Rain Reassess across Monte Carlo weather forecast scenarios.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 20+

### 2. Environment Setup

```powershell
# Clone and enter repository
git clone https://github.com/Krishna-Modi12/renewable-asset-intelligence.git
cd renewable-asset-intelligence

# Install Python virtual environment and dependencies
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Install frontend dependencies
cd web
npm install
cd ..
```

### 3. Generate Telemetry & Knowledge Index

```powershell
# Generate 45 days of SCADA for 42 assets
.venv\Scripts\python.exe scripts\generate.py

# Train expected-behavior and hybrid models
.venv\Scripts\python.exe scripts\train.py

# Build SQLite FTS5 RAG index (221 sections across 19 domain docs)
.venv\Scripts\python.exe scripts\build_index.py
```

### 4. Start Services

```powershell
# Terminal 1: Launch FastAPI Backend (Port 8000)
.venv\Scripts\uvicorn services.api.main:app --port 8000

# Terminal 2: Launch Next.js Instrument Panel (Port 3000)
cd web
npm run dev
```

Open `http://localhost:3000` to view the Fleet Operations Command.

---

## Running Demonstrations

The repository provides scripted and interactive end-to-end demonstrations across the flagship scenarios:

```powershell
# Run all three flagship demonstration scenarios
.venv\Scripts\python.exe scripts\demo.py --all

# Run Wind Hero Investigation (WT-017 bearing degradation)
.venv\Scripts\python.exe scripts\demo.py --scenario wind_hero

# Run Solar Soiling & CAMS Weather Flagship (INV-023 dust event)
.venv\Scripts\python.exe scripts\demo.py --scenario solar_flagship

# Run Non-Fault False Alarm Suppression (Cloud transient / Grid curtailment)
.venv\Scripts\python.exe scripts\demo.py --scenario non_fault
```

---

## Formal Evaluation

Execute the complete evaluation harness:

```powershell
.venv\Scripts\python.exe scripts\evaluate.py
```

Outputs written to:
- `artifacts/evaluation/results.json` — Machine-readable evaluation results
- `artifacts/evaluation/summary.md` — Markdown evaluation summary
- `artifacts/evaluation/metrics.csv` — Full benchmark table

---

## Repository Layout

```text
rai/
├── schemas.py          Pydantic contracts: EvidencePacket, AgentVerdict, Soiling, Cleaning
├── config.py           Settings, fleet registry, units, thresholds, economic parameters
├── sim/                Physics-grounded telemetry and 12-scenario fault injection
├── store/              Parquet/DuckDB windowed reads and state persistence
├── features/           Quality filters, states, windows, residual preparation
├── models/
│   ├── expected.py     Expected healthy behavior (Physics + LightGBM)
│   ├── anomaly.py      Residual z-score, Isolation Forest, change-point fusion
│   ├── fleet_common_cause.py Common-cause vs. isolated anomaly correlation
│   ├── sensor_health.py Bounds, frozen sensor, and cross-sensor consistency
│   ├── peers.py        Fleet & feeder peer comparison clustering
│   └── risk.py         Weibull hazard, probability calibration, risk bands
├── environment/        Modular environmental intelligence
│   ├── weather_provider.py Open-Meteo live API client + cached fallbacks
│   ├── dust.py         CAMS dust exposure integral D(t) and deposition priors
│   ├── rain.py         Rain wash kinetics and mud cementation hypothesis
│   ├── clearsky.py     pvlib clear-sky POA irradiance & cloud filtering
│   ├── soiling.py      Kimber, RdTools SRR, and weather challenger models
│   ├── attribution.py  Model-based loss attribution with confidence intervals
│   └── cleaning_optimizer.py Dynamic cleaning opportunity & Monte Carlo weather
├── decision/           Modular decision intelligence
│   ├── scenarios.py    Wind & Solar counterfactual future state simulation
│   ├── regret.py       Decision regret (Cost_chosen - Cost_optimal) calculation
│   ├── value_of_information.py Expected value of inspection information (VOI)
│   └── policy.py       Sensitivity bounds, risk attribution, & feedback learning
├── eval/               Two-track CARE metrics, 4-level splits, leakage guards
├── memory/             Historical trajectory case retrieval
├── rag/                SQLite FTS5 index construction and BM25 search
├── economics/          NPV trade-off models and Smart Cleaning Advisor
└── agent/              Needle 2 local runtime + deterministic fallback reasoner

services/
└── api/                FastAPI REST service matching docs/API_CONTRACT.md

web/
└── src/
    ├── app/            Next.js App Router views (Fleet, Assets, Soiling, Evaluation, etc.)
    ├── components/     AppShell, HeroChart, EvidenceAccordion, MetricTile, StatusPill
    └── lib/            API clients and formatters (₹ Lakhs/Crores, tabular mono)
```

---

## Testing & Quality

```powershell
# Run backend test suite
.venv\Scripts\pytest

# Run static analysis and linting
.venv\Scripts\ruff check .
.venv\Scripts\pyright

# Run Next.js production build
cd web
npm run build
```

---

## Documentation

- [`docs/EVALUATION_FORENSICS.md`](docs/EVALUATION_FORENSICS.md): **Mandatory Forensics Audit** — line-by-line claim truth table, leakage verification, and sample size disclosures
- [`docs/PHASE_2_JUDGE_PACKAGE.md`](docs/PHASE_2_JUDGE_PACKAGE.md): **Judge Package** — problem statement, architecture, 10-point readiness scorecard, and judge defense guide
- [`docs/EVALUATION.md`](docs/EVALUATION.md): Formal model evaluation report, Two-Track CARE benchmark, and calibration diagnostics
- [`docs/DESIGN.md`](docs/DESIGN.md): Normative design system, OKLCH tokens, and component guidelines
- [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md): OpenAPI specification and REST endpoint contracts
- [`docs/research/model-validation.md`](docs/research/model-validation.md): Anti-overfitting, CARE to Compare, and leakage prevention compendium
- [`docs/research/environmental-intelligence.md`](docs/research/environmental-intelligence.md): CAMS aerosol data, soiling kinetics, and cementation risks
- [`docs/DEMO.md`](docs/DEMO.md): Judge-facing walkthrough script
- [`docs/DATASETS.md`](docs/DATASETS.md): Synthetic dataset parameters and provenance
