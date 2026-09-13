# Renewable Asset Intelligence (RAI)

**Predictive Maintenance & Environmental Risk Intelligence for Wind & Solar Fleets.**

Renewable Asset Intelligence (RAI) turns noisy SCADA telemetry and atmospheric composition forecasts into defensible, economically optimal operational interventions. It learns what an asset should be generating under prevailing ambient conditions, measures conditioned residuals, checks CAMS dust plumes, weather transients, curtailment, and peer behavior, retrieves comparable historical episodes, calculates the net financial consequence of waiting, and returns a confidence-gated recommendation for a human operator.

> **Implementation status:** 421 automated tests passing (verified by a direct `pytest` run on 2026-09-13; this repository is under active multi-session development, so re-verify before citing). Time-ordered, leakage-free splits (`rai/eval/leakage.py`), a 342-hour purge embargo, and a frozen decision threshold (`docs/evaluation/GATE2_FORENSIC_AUDIT.md`). Champion model, first measured by a reproducible run of `python scripts/evaluate.py` and re-measured leak-free under embargo: **RAI Operational Score (CARE-inspired) = 0.797, embargoed PR-AUC = 0.822, MCC = 0.690, FA/yr = 0.19/asset-year, median lead time = 5.0 days** across 45,360 monitored asset-hours ($N=6$ independent failure episodes — treat sub-breakdowns of that N as indicative, not decisive). Real external validation now exists in two independent forms: a **controlled out-of-distribution perturbation suite** (`docs/evaluation/OOD.md`) and a **real external benchmark run against the published CARE-to-Compare dataset** (`docs/evaluation/EXTERNAL_CARE.md`, Zenodo 14006163, Wind Farm A, genuine off-the-shelf baselines, CARE = 0.535). A separate rolling-origin temporal-generalization study (`docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md`) concluded that finding is **honestly unresolved** at $N=6$ events, not swept under a bigger number. Solar Environmental Intelligence with CAMS atmospheric dust exposure memory ($D(t)$), `pvlib` clear-sky POA normalization, and model-based loss attribution. **Start with [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md)** for the history of what was fabricated and fixed in this repository's evaluation stack, then [`docs/evaluation/GATE2_FORENSIC_AUDIT.md`](docs/evaluation/GATE2_FORENSIC_AUDIT.md) for the current leak-free numbers — [`docs/EVALUATION_FORENSICS.md`](docs/EVALUATION_FORENSICS.md) and [`docs/PHASE_2_JUDGE_PACKAGE.md`](docs/PHASE_2_JUDGE_PACKAGE.md) still carry an early retraction notice and should not be cited on their own.

[![Quality](https://github.com/Krishna-Modi12/renewable-asset-intelligence/actions/workflows/quality.yml/badge.svg)](https://github.com/Krishna-Modi12/renewable-asset-intelligence/actions/workflows/quality.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](services/api/)
[![Next.js](https://img.shields.io/badge/Next.js-16.3.5-000000?logo=next.js&logoColor=white)](web/package.json)
[![Tests](https://img.shields.io/badge/tests-421%20passing-success)](CHECKPOINT.md)
[![Embargoed PR--AUC](https://img.shields.io/badge/embargoed%20PR--AUC-0.822-success)](docs/evaluation/GATE2_FORENSIC_AUDIT.md)
[![External CARE](https://img.shields.io/badge/external%20CARE%20(Farm%20A)-0.535-blueviolet)](docs/evaluation/EXTERNAL_CARE.md)
[![Audit Status](https://img.shields.io/badge/Forensics-Verified%20Clean-blue)](docs/EVALUATION_FORENSICS.md)

---

## Read this before anything else

RAI is a research and hackathon build, not a deployed product. Six things are true at once,
and none of them are hidden in fine print below:

- **The benchmark is a wind anomaly benchmark first.** The internal 0.797 operational score
  and the external 0.535 CARE score are both measured on wind SCADA data (18 turbines
  internally; one real farm, Wind Farm A, externally). Solar gets its own, much narrower,
  validation story below.
- **Solar failure validation is not complete.** Gate 5.6C — fitting and validating a solar
  expected-performance model against real acquired PVDAQ telemetry — is explicitly
  **not closed**. See [Solar External Data Status](#solar-external-data-status).
- **One external farm is not proof of universal generalization.** CARE = 0.535 on Wind Farm A
  is a real result against a real, independently-labelled dataset — and it is one evaluated
  pair (this model, that farm), not evidence the model transfers to arbitrary sites.
- **A model that looks well-calibrated on its own targets can still miss under distribution
  shift.** The OOD suite shows CARE falling to 0.52 and false alarms rising ~40× under severe
  synthetic sensor drift/noise — see [Gate 2 — OOD robustness](#scientific-validation-five-gates-not-one-number).
- **The local AI explains and escalates; it does not invent evidence or run unattended.**
  See [Local reasoning: what's real vs. architectural target](#local-reasoning-whats-real-vs-architectural-target).
- **Every economic figure depends on stated cost assumptions**, disclosed next to the number
  in the UI, not buried in a config file.

None of this is a hedge added after the fact — it is the same discipline
[`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) exists to enforce throughout the repository.

---

## The problem in one paragraph

A wind turbine's power output depends on wind speed; a solar inverter's depends on irradiance
and temperature. So a raw "power is low" reading is ambiguous by construction — it could be a
failing gearbox bearing, a dust storm, a grid curtailment order, a cloud bank, or a stuck
sensor, and a fixed threshold alarm cannot tell them apart. Two failure modes follow from that
ambiguity: **alarm fatigue** (every weather event pages a technician) or **missed faults**
(a real degradation hides inside normal weather-driven variance until it is a forced outage).
Most SCADA alarm layers stop at the threshold and leave that disambiguation to a human staring
at a trend chart.

### Where a threshold alarm stops and where RAI keeps going

| | Fixed-threshold alarm | RAI |
|---|---|---|
| **Trigger** | Power below a fixed % of nameplate | Residual against a physics + gradient-boosted expected-behavior model, conditioned on live wind/irradiance/temperature |
| **Environmental causes** | Not distinguished — a dust storm and a bearing failure look identical | Checked first: CAMS dust exposure, weather transients, curtailment flags, and fleet-peer isolation must all fail to explain the deviation before an equipment fault is asserted (`rai/models/fleet_common_cause.py`, `rai/environment/`) |
| **Evidence behind an alert** | A single number crossed a line | An evidence ledger: residual z-scores, peer comparison, environmental attribution, historical case match, OEM/SOP citation (`rai/schemas.py: EvidencePacket`) |
| **Economic framing** | None — every alarm looks equally urgent | Net-present-value comparison of act-now vs. defer-3-days vs. defer-14-days, with assumptions shown (`rai/economics/`) |
| **Confidence handling** | Binary alarm / no-alarm | Confidence-gated: below the calibrated threshold, the system escalates to a human instead of asserting a verdict (`rai/agent/`) |
| **When it doesn't know** | Silent — a threshold either fires or it doesn't | Explicit `UNKNOWN` / `requires_human_review` states surfaced in the UI, not smoothed over |

---

## The RAI intelligence loop

Ten stages, each backed by a real module — not a diagram drawn before the code existed:

```
 SENSE           NORMALIZE        COMPARE          DIAGNOSE         PREDICT
 SCADA/inverter  physics+GBM      residual z /     environment /    Weibull hazard,
 telemetry in    expected value   isolation forest peer / sensor    calibrated risk
 rai/store/      rai/models/      fusion           gating           band
                 expected.py      rai/models/      rai/models/      rai/models/
                                  anomaly.py        fleet_common_    risk.py
                                                     cause.py,
                                                     sensor_health.py
     │                │                │                │                │
     ▼                ▼                ▼                ▼                ▼
 RETRIEVE         QUANTIFY         PRIORITIZE       ACT              LEARN
 similar past     NPV of act-now   rank by risk ×   confidence-      technician
 failure cases    vs. defer,       exposure across  gated recom-     outcome logged
 rai/memory/      OEM SOP cites    the fleet        mendation via    for audit
 library.py       rai/economics/,  services/api/    local reasoner   rai/decision/
                  rai/rag/                           rai/agent/       policy.py
```

This loop is the operating model behind the app you can run locally (`web/`), not a separate
narrative layered on top of it — every box above is a module you can open and read. **One
honest caveat on the last stage:** `record_maintenance_feedback` appends a technician's actual
finding to a JSONL log (`artifacts/state/maintenance_outcomes.jsonl`) for later audit — nothing
in this repository yet reads that log back into the retrieval index, so "LEARN" here means
"captured for a human to review," not a closed loop that automatically improves future
retrieval.

---

## Local reasoning: what's real vs. architectural target

**What's implemented today:** every number a user sees — residuals, risk scores, NPV, avoided
exposure — is computed in Python and handed to the reasoning layer as a structured
`EvidencePacket`. A deterministic rule-based reasoner (`rai/agent/fallback.py`) always
produces a schema-valid, evidence-cited verdict. Where a local Needle 2 runtime is available
(`cactus-needle`, a 45M-parameter, ~14 MB tool-calling model that runs in ~28 MB of RAM —
small enough for an edge gateway next to the SCADA historian), it can additionally drive tool
calls and improve the natural-language explanation — but it never computes the numbers itself,
and a low-confidence or contradictory model output falls back to the deterministic verdict
rather than being shown at face value (`rai/agent/runtime.py: verdict_from_needle`).

**What this is not:** a fully autonomous agent that acts on the fleet unattended. The agent has
read-only tools plus ticket creation — it never issues a physical control command — and its
internal reasoning trace is not exposed as a performance for the user; what's shown is the
cited evidence and the final verdict, not manufactured chain-of-thought. Below the confidence
threshold, or when local weights aren't available at all, the system says so and escalates
rather than guessing.

**Feasibility note:** because the detection, economics, and fallback-reasoning path has no
required external API call, the core pipeline runs fully offline on a single machine — the
Needle 2 layer is the only part that benefits from (and is designed to eventually run
entirely within) an edge device with no cloud round-trip, which matters for a SCADA
environment that may not have reliable outbound connectivity.

---

## Contents

- [Read this before anything else](#read-this-before-anything-else)
- [The problem in one paragraph](#the-problem-in-one-paragraph)
- [The RAI intelligence loop](#the-rai-intelligence-loop)
- [Local reasoning: what's real vs. architectural target](#local-reasoning-whats-real-vs-architectural-target)
- [Why RAI](#why-rai)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Champion–Challenger Operational Scorecard](#track-a--championchallenger-operational-scorecard)
- [Scientific Validation: Five Gates, Not One Number](#scientific-validation-five-gates-not-one-number)
- [Solar External Data Status](#solar-external-data-status)
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
| **Historical Trajectory Memory** | Cosine similarity KNN retrieval of past degradation signatures with strict retrieval leakage guards | `rai/memory/library.py` |
| **Technical Knowledge RAG** | SQLite FTS5 BM25 retrieval over 19 maintenance manuals, failure catalogs, and OEM SOPs | `rai/rag/` |
| **Deterministic Reasoning Agent** | Structured diagnosis and confidence-gated escalation with local Needle 2 runtime support | `rai/agent/` |
| **High-Density Instrument Panel** | Bloomberg-terminal density Next.js 16 UI with OKLCH tokens, HeroChart, and Evidence Ledger. Every API client call returns `{data, live}`, and the UI shows a `LIVE`/`CACHED` badge rather than presenting a last-known snapshot with full visual authority | `web/src/lib/api.ts` |
| **Controlled OOD Robustness Suite** | 12 pre-registered sensor perturbations (noise, missingness, drift, extreme weather, fault-magnitude, weather permutation) rerun end-to-end against the live pipeline, not a mocked score | `rai/eval/ood.py` |
| **Real External Benchmark (CARE-to-Compare)** | Genuine, un-tuned baselines scored on the published Gück et al. (2024) wind SCADA dataset, formulas transcribed equation-by-equation from the paper | `rai/eval/external/care/` |
| **Rolling-Origin Temporal Diagnosis** | Fold-by-fold root-cause analysis of why naive temporal CV collapses on rare-event data, with three honest re-aggregations instead of one convenient number | `docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md` |
| **Decision-Math & Claim-Integrity Audit** | Formal EVPI/EVSI sign-convention proofs plus an independent outcome-world regret simulation decoupled from the policy's own cost model | `docs/evaluation/DECISION_MATH_AUDIT.md` |

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
1. **Track A — RAI Operational Score (CARE-inspired):** Evaluated on the 42-asset fleet (45,360 monitoring hours, 6 discrete failure episodes). This is RAI's own synthetic-fleet score — model, labels, and scoring code all live in this repository.
2. **Track B — External Wind Benchmark (now run, Farm A only):** the official CARE to Compare dataset (Gück et al., 2024: 36 turbines, 3 farms, Zenodo 14006163) has been downloaded and scored against genuine, un-tuned baselines on Wind Farm A — CARE = 0.535 (isolation forest) / 0.506 (z-score threshold), real third-party data and labels throughout. See [`docs/evaluation/EXTERNAL_CARE.md`](docs/evaluation/EXTERNAL_CARE.md) and the [Scientific Validation](#scientific-validation-five-gates-not-one-number) section below. Farms B and C were downloaded but not yet extracted or scored — treat any Farm B/C figure elsewhere in this repo as aspirational, not measured.

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
* **Mean Decision Regret (model-world):** `₹0.00`, **100% "optimal"** across the 6 fault events evaluated — but "optimal" here means the decision engine's pick matches the lowest-cost option under the *same* cost model it used to choose, not an independently validated ground truth. This is a self-consistency check, not proof the recommendations are economically optimal in the field. This limitation is now addressed directly — see the **independent outcome-world regret simulation** below.

---

## Scientific Validation: Five Gates, Not One Number

A single headline metric is easy to cherry-pick and hard to trust. Following this project's
own [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) — which found and withdrew several fabricated
figures from an earlier iteration — every evaluation claim below is scoped to the exact document
and code path that produced it, and an "unresolved" verdict is reported as such rather than
replaced with a more convenient number. This is a layered validation story, built across several
work sessions on this repository; some gates close a question, others open one honestly.

| Gate | Question it answers | Headline result | Source |
|---|---|---|---|
| **Gate 1 — Leakage** | Does the model see the future during training? | Zero lookahead leakage across a 342h purge embargo; time-ordered splits only | [`rai/eval/leakage.py`](rai/eval/leakage.py), [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) |
| **Gate 2 — Forensic re-audit** | What does the champion score under a *frozen* threshold and embargo, not a permissive static split? | PR-AUC **0.822**, MCC 0.690, precision 0.800, recall 0.667; 5/5 adversarial stress probes passed (label permutation, random feature, temporal label shift, future-sentinel injection, asset-identity shuffle) | [`docs/evaluation/GATE2_FORENSIC_AUDIT.md`](docs/evaluation/GATE2_FORENSIC_AUDIT.md) |
| **Gate 2 — OOD robustness** | Does the champion degrade *sensibly* under corrupted sensor data, or is it silently blind to it? | CARE falls up to **0.52** under severe drift; false alarms rise up to **~40×** under severe sensor noise; 20% missingness is well tolerated (ΔCARE ≤ 0.05). A caching bug that made the champion look falsely "perfectly robust" was found and fixed before any number was reported | [`docs/evaluation/OOD.md`](docs/evaluation/OOD.md) |
| **Gate 2 — External CARE benchmark** | How does a genuine, un-tuned baseline do on a real, independently-labelled wind SCADA dataset? | **CARE = 0.535** (isolation forest) / **0.506** (z-score) on real Wind Farm A data (Gück, Roelofs & Faulstich, 2024); only 1 of 11 real documented faults reliably detected by either baseline — reported as a modest result, not a favorable one | [`docs/evaluation/EXTERNAL_CARE.md`](docs/evaluation/EXTERNAL_CARE.md) |
| **Gate 3 — Temporal generalization** | Does the champion generalize across *time*, not just across a single train/test cut? | **Honestly unresolved.** A naive 4-fold rolling-origin CV collapses to PR-AUC 0.294 (CI95 [0.04, 0.64]); root-caused to event sparsity (one fold has zero positive events) and a calendar-overlap artifact, not model instability (the underlying power curve is stable, R²=0.994, across folds). Re-aggregated honestly three ways — macro valid-fold PR-AUC 0.392±0.319, micro/pooled PR-AUC 0.648, event-level recall 83.3% (5/6 episodes) — none of which is treated as a replacement for more failure events | [`docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md`](docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md), [`docs/evaluation/GATE3B0_SCORECARD.md`](docs/evaluation/GATE3B0_SCORECARD.md) |
| **Gate 5 — Decision-math & claim integrity** | Is "100% optimal, ₹0 regret" actually a meaningful economic claim? | Formally proved EVPI ≥ 0 and 0 ≤ EVSI ≤ EVPI hold under this project's sign convention, then measured regret **independently of the policy's own cost model** via a 100-episode outcome-world simulation with mismatched Weibull failure parameters: mean regret **₹9,127**, median ₹0, P95 ₹19,500, optimal-action rate **71.0%** — the honest number, once the model-world tautology above is decoupled from the world it is judged against | [`docs/evaluation/DECISION_MATH_AUDIT.md`](docs/evaluation/DECISION_MATH_AUDIT.md) |

**Two numbers for PR-AUC exist in this repository on purpose, not by accident**: `0.948` is the
original static-split measurement (`scripts/evaluate.py`, `docs/EVALUATION.md`); `0.822` is the
same champion re-measured under a 342h purge embargo and a threshold frozen *before* seeing the
test fold (`docs/evaluation/GATE2_FORENSIC_AUDIT.md`). The embargoed number is the one to cite —
the static one is kept in the record because silently replacing a number, rather than showing the
before/after and why it changed, is exactly the kind of thing [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md)
exists to catch. Similarly, calibration figures differ slightly between `CHECKPOINT.md`
(Brier 0.0439 / ECE 0.0915, naive) and `docs/evaluation/GATE2_FORENSIC_AUDIT.md`
(Brier 0.0423 / ECE 0.1491, out-of-fold) — cite the source file alongside the number, not the
number alone.

---

## Solar External Data Status

The original Gate 5.6 solar-model result is **retracted**: it used repository-generated
synthetic telemetry presented as NREL PVDAQ data and a circular physics comparison. Its
metrics must not be cited as external validation or RAI Solar Champion performance.

The valid replacement work is deliberately narrower:

- **Gate 5.6A:** 450/450 real PVDAQ daily parquet files were acquired and checksummed; the
  acquisition is preserved in `artifacts/evaluation/gate56/acquisition/`.
- **Gate 5.6B:** 3 systems are frozen for development, 2 are secondary-only, and the
  validation cohort is empty because the remaining systems have ambiguous timestamps or
  severe missingness. No model was fit in this adjudication gate.
- **Gate 5.6C:** **not complete.** A decision record (PATH B — no real component-failure
  labels exist for this cohort) and preliminary model-development code (a real
  `pvlib.modelchain.ModelChain` physics reference plus empirical/hybrid models) were executed
  against the real, adjudicated cohort, but the results have not been independently verified
  and the gate has not been closed. Every result is labeled `MODEL_DEVELOPMENT` /
  `NOT_INDEPENDENTLY_VALIDATED`. Current phase: **Post-Gate-5.6B / pre-Gate-5.6C**.

See [`docs/checkpoints/14-solar-expected-performance.md`](docs/checkpoints/14-solar-expected-performance.md),
[`docs/checkpoints/15-gate56a-pvdaq-real-acquisition.md`](docs/checkpoints/15-gate56a-pvdaq-real-acquisition.md),
[`docs/checkpoints/16-gate56b-cohort-adjudication.md`](docs/checkpoints/16-gate56b-cohort-adjudication.md),
[`docs/checkpoints/18-gate56c-decision-gate.md`](docs/checkpoints/18-gate56c-decision-gate.md),
and [`docs/checkpoints/19-gate56c-model-development.md`](docs/checkpoints/19-gate56c-model-development.md) (status: `partial`).

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
├── eval/               Internal CARE metrics, 4-level splits, leakage guards, adversarial probes
│   ├── ood.py          Controlled OOD perturbation suite (12 perturbations, pre-registered seeds)
│   ├── rolling_origin.py, benchmarks.py, splits.py, adversarial.py — Gate 1/2 CV & stress harness
│   └── external/care/  Real external CARE-to-Compare benchmark (independent of rai/eval/care.py)
│       ├── metrics.py  Paper's own Eq. 1-5 + Algorithm 1, transcribed and cited per function
│       ├── adapter.py  Genuine, un-tuned isolation-forest / z-score baselines (not RAI's champion)
│       └── farm_a_runner.py End-to-end runner against the real downloaded Wind Farm A archive
├── ingest/             Real-dataset adapters (CARE SCADA, Kaggle solar, NASA POWER)
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

**Start here for evaluation claims (in this order):**
- [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md): the consolidated record of every fabricated figure found in this repository's history and the fix applied — read this before citing any number below it
- [`docs/CLAIMS.md`](docs/CLAIMS.md): the claims-to-evidence matrix — every public claim tagged **demonstrated** (reproducible locally), **specified** (contract exists, not fully implemented), or **future** (research direction)
- [`docs/evaluation/GATE2_FORENSIC_AUDIT.md`](docs/evaluation/GATE2_FORENSIC_AUDIT.md): the current leak-free scorecard — embargoed PR-AUC, adversarial stress-probe results, rolling-origin CI
- [`docs/evaluation/OOD.md`](docs/evaluation/OOD.md): the controlled out-of-distribution perturbation suite, including a methodology bug found and fixed mid-study
- [`docs/evaluation/EXTERNAL_CARE.md`](docs/evaluation/EXTERNAL_CARE.md): the real external CARE-to-Compare benchmark run (Wind Farm A) — also documents a filename collision between two concurrent work sessions and how it was resolved
- [`docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md`](docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md) & [`docs/evaluation/GATE3B0_SCORECARD.md`](docs/evaluation/GATE3B0_SCORECARD.md): why naive rolling-origin CV collapses on rare-event data, and three honest re-aggregations
- [`docs/evaluation/DECISION_MATH_AUDIT.md`](docs/evaluation/DECISION_MATH_AUDIT.md): formal EVPI/EVSI proofs and an independent outcome-world decision-regret simulation
- [`docs/evaluation/FEATURE_LINEAGE.md`](docs/evaluation/FEATURE_LINEAGE.md): the temporal-isolation ledger — which features are computed from past-only data, verified column by column
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md): explicit non-claims — what the synthetic data spine cannot tell you, stated plainly rather than left implicit

**Everything else:**
- [`docs/EVALUATION_FORENSICS.md`](docs/EVALUATION_FORENSICS.md) / [`docs/PHASE_2_JUDGE_PACKAGE.md`](docs/PHASE_2_JUDGE_PACKAGE.md): earlier judge-facing packages — both carry a retraction notice at the top; superseded by the Gate 2+ docs above for numbers
- [`docs/EVALUATION.md`](docs/EVALUATION.md): the original formal model evaluation report and calibration diagnostics
- [`docs/DESIGN.md`](docs/DESIGN.md): Normative design system, OKLCH tokens, and component guidelines
- [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md): OpenAPI specification and REST endpoint contracts
- [`docs/research/model-validation.md`](docs/research/model-validation.md): Anti-overfitting, CARE to Compare, and leakage prevention compendium
- [`docs/research/environmental-intelligence.md`](docs/research/environmental-intelligence.md): CAMS aerosol data, soiling kinetics, and cementation risks
- [`docs/DEMO.md`](docs/DEMO.md): Judge-facing walkthrough script
- [`docs/DATASETS.md`](docs/DATASETS.md): Synthetic dataset parameters and provenance
- [`CHECKPOINT.md`](CHECKPOINT.md): consolidated, auto-generated build state across every completed task record in `docs/checkpoints/`
