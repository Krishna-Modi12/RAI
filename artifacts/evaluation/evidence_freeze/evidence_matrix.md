# SCIENTIFIC EVIDENCE MATRIX — DETAILED METHODOLOGY & PROVENANCE

This matrix provides the complete audit specification for every evidence source in RAI.

| Evidence ID | Feature / System | Source Dataset | Evidence Class | Reality Status | Validation Status | Exact Artifact |
|---|---|---|---|---|---|---|
| `EVID-CARE-01` | Wind Anomaly Detection Baseline | CARE Benchmark (Zenodo 10.5281/zenodo.10958775) | `EXTERNAL_BENCHMARK` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/evaluation/external_care/` |
| `EVID-CARE-02` | Cross-Farm Wind Transfer & Calibration | CARE Benchmark (Zenodo 10.5281/zenodo.10958775) | `EXTERNAL_BENCHMARK` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/evaluation/gate54/` |
| `EVID-KEL-01` | Wind Operational Event Window Association | Kelmarsh Wind Farm (Zenodo 10.5281/zenodo.5841834) | `EXTERNAL_BENCHMARK` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/evaluation/kelmarsh_event_behaviour/` |
| `EVID-PVDAQ-01` | Solar Data Foundation & Telemetry Acquisition | NREL PVDAQ Open Energy Data Initiative (OEDI S3) | `EXTERNAL_REAL` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/evaluation/gate56/cohort_adjudication/` |
| `EVID-PVDAQ-02` | Solar Expected-Performance Model Development | NREL PVDAQ Telemetry (Systems 1239, 1283, 34) | `MODEL_COMPARISON` | `REAL_EXTERNAL_DATA` | `NOT_VALIDATED` | `artifacts/evaluation/gate56/gate56c_model_development/` |
| `EVID-AGENT-01` | Local AI Agent Safety & Reasoning Battery | Internal Deterministic Agent Evaluation Suite | `INTERNAL_SYNTHETIC` | `INTERNAL_SYNTHETIC` | `DEMONSTRATED` | `artifacts/evaluation/agent_eval/` |
| `EVID-RAG-01` | Historical Precedent Case Retrieval | 14 External Real Cases (CARE, Kelmarsh, PVDAQ) + 14 Synthetic Reference Scenarios | `EXTERNAL_BENCHMARK` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/retrieval_benchmark_results.json` |
| `EVID-LOOP-01` | Closed-Loop Operational Ingestion & Promotion Gate | Simulated Work Order Lifecycle in Browser & API | `DEMONSTRATION_ONLY` | `INTERNAL_SYNTHETIC` | `DEMONSTRATED` | `browser_verification/` |
| `EVID-DISPATCH-01` | Safe-Weather Fleet Crew Dispatch Optimizer | Configured Meteorological Thresholds + Weather API Cache | `SIMULATED_OUTCOME` | `SIMULATED_OUTCOME` | `ARCHITECTURALLY_SUPPORTED` | `artifacts/weather_cache/` |
| `EVID-SIM-01` | Physics-Based Telemetry & Fault Simulator | rai/sim/ synthetic generation engine | `INTERNAL_SYNTHETIC` | `INTERNAL_SYNTHETIC` | `DEMONSTRATED` | `artifacts/evaluation/results.json` |
| `EVID-ECON-01` | Techno-Economic Decision Support Engine | Analytical NPV Decision Models (rai/economics/decision_support.py) | `MODEL_COMPARISON` | `SIMULATED_OUTCOME` | `DEMONSTRATED` | `tests/test_economic_decision_support.py` |
| `EVID-COUNTER-01` | Counterevidence & Differential Diagnosis Engine | rai/models/differential_diagnosis.py | `SOFTWARE_INVARIANT` | `SOFTWARE_INVARIANT` | `ARCHITECTURALLY_SUPPORTED` | `tests/test_differential_diagnosis.py` |
| `EVID-OOD-01` | Out-of-Distribution Robustness Suite | Controlled Synthetic Perturbation Suite | `SIMULATED_OUTCOME` | `SIMULATED_OUTCOME` | `VALIDATED` | `artifacts/evaluation/phase4/` |
| `EVID-REALCASES-01` | External Real Historical Precedent Corpus | 14 Audited Cases (8 CARE, 4 Kelmarsh, 2 NREL PVDAQ OEDI) | `EXTERNAL_REAL` | `REAL_EXTERNAL_DATA` | `VALIDATED` | `artifacts/evaluation/real_case_provenance/` |

---

## Detailed Evidence Item Profiles

### `EVID-CARE-01`: Wind Anomaly Detection Baseline
- **Technology:** Wind Turbines
- **Source Dataset:** CARE Benchmark (Zenodo 10.5281/zenodo.10958775)
- **Source Provenance:** Academic open benchmark from 3 operational wind farms (Farms A, B, C; 36 turbines total)
- **Evidence Class:** `EXTERNAL_BENCHMARK`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/external_care/`](artifacts/evaluation/external_care/)
- **Report Path:** [`docs/evaluation/EXTERNAL_CARE.md`](docs/evaluation/EXTERNAL_CARE.md)
- **What Was Tested:** Multi-farm anomaly detection accuracy, Coverage, Reliability (CARE Algorithm 1), and Earliness on published SCADA and failure event logs. Evaluated on 36 turbines.
- **Metric / Result:** Normal accuracy 0.995-0.999 across all 3 farms; CARE Operational Score 0.601 (Farm A), 0.560 (Farm B), 0.575 (Farm C); false alarm rate <= 0.005.
- **What It Does NOT Prove:** *Does not prove universal zero-shot generalization to uncalibrated fleets or novel turbine models. Does not prove causal root-cause diagnosis.*
- **Claim IDs:** CLAIM-WIND-01, CLAIM-CARE-01

### `EVID-CARE-02`: Cross-Farm Wind Transfer & Calibration
- **Technology:** Wind Turbines
- **Source Dataset:** CARE Benchmark (Zenodo 10.5281/zenodo.10958775)
- **Source Provenance:** Cross-farm evaluation between Wind Farms A, B, and C under frozen CARE_COMMON input protocol
- **Evidence Class:** `EXTERNAL_BENCHMARK`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/gate54/`](artifacts/evaluation/gate54/)
- **Report Path:** [`docs/checkpoints/14-gate54-cross-farm-wind-transfer.md`](docs/checkpoints/14-gate54-cross-farm-wind-transfer.md)
- **What Was Tested:** All 6 directed transfers (A->B, A->C, B->A, B->C, C->A, C->B) across 3 conditions (FROZEN_SOURCE, TARGET_NORMAL_CALIBRATED, TARGET_SPECIFIC_REFERENCE). Kolmogorov-Smirnov distribution shift quantification.
- **Metric / Result:** Target-normal calibration using unlabelled SCADA completely recovers the transfer gap (106.3% recovery on C->A; normal accuracy restored from 0.5965 to 0.9963 on B->A).
- **What It Does NOT Prove:** *Does not prove that zero-shot uncalibrated transfer works across disparate turbine kinematics without unlabelled target telemetry.*
- **Claim IDs:** CLAIM-WIND-02, CLAIM-TRANSFER-01

### `EVID-KEL-01`: Wind Operational Event Window Association
- **Technology:** Wind Turbines
- **Source Dataset:** Kelmarsh Wind Farm (Zenodo 10.5281/zenodo.5841834)
- **Source Provenance:** Open-access operational SCADA and Greenbyte status logs from 6 Senvion MM92 turbines in the UK
- **Evidence Class:** `EXTERNAL_BENCHMARK`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/kelmarsh_event_behaviour/`](artifacts/evaluation/kelmarsh_event_behaviour/)
- **Report Path:** [`docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md`](docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md)
- **What Was Tested:** Association between RAI continuous anomaly scores and documented operational event periods (cable untwisting, curtailment, scheduled maintenance, environmental calm standstills).
- **Metric / Result:** Statistically significant elevation of anomaly residuals during operational event intervals vs normal generation periods.
- **What It Does NOT Prove:** *MUST NOT be described as failure prediction or hardware failure validation. Public Kelmarsh dataset contains operational and maintenance logs, but NO verified component-failure labels.*
- **Claim IDs:** CLAIM-KELMARSH-01

### `EVID-PVDAQ-01`: Solar Data Foundation & Telemetry Acquisition
- **Technology:** Solar PV
- **Source Dataset:** NREL PVDAQ Open Energy Data Initiative (OEDI S3)
- **Source Provenance:** Public solar telemetry from NREL public data lake (Systems 34, 1283, 1239, 1430, 1433)
- **Evidence Class:** `EXTERNAL_REAL`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/gate56/cohort_adjudication/`](artifacts/evaluation/gate56/cohort_adjudication/)
- **Report Path:** [`docs/checkpoints/16-gate56b-cohort-adjudication.md`](docs/checkpoints/16-gate56b-cohort-adjudication.md)
- **What Was Tested:** 450 daily telemetry files downloaded and checksum-verified; 26-signal canonical solar taxonomy mapping; timestamp monotonicity, unit scale, and sensor quality audited (Gate 5.6A & 5.6B).
- **Metric / Result:** Adjudicated cohort: Development=[1239, 1283, 34], Validation=[], State=INSUFFICIENT_DATA. Flagged that 1430/1433 have 100% null UTC timestamps and 1283 has no plant-level AC channel.
- **What It Does NOT Prove:** *Does not validate any solar performance or failure model. Validation cohort was explicitly empty.*
- **Claim IDs:** CLAIM-SOLAR-01

### `EVID-PVDAQ-02`: Solar Expected-Performance Model Development
- **Technology:** Solar PV
- **Source Dataset:** NREL PVDAQ Telemetry (Systems 1239, 1283, 34)
- **Source Provenance:** Development cohort telemetry fit with temporal within-system split
- **Evidence Class:** `MODEL_COMPARISON`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `NOT_VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/gate56/gate56c_model_development/`](artifacts/evaluation/gate56/gate56c_model_development/)
- **Report Path:** [`docs/evaluation/GATE56C_VERIFICATION.md`](docs/evaluation/GATE56C_VERIFICATION.md)
- **What Was Tested:** ModelChain physics reference vs polynomial empirical baseline vs hybrid champion on temporal holdouts within Systems 1239, 1283, 34 (Gate 5.6C).
- **Metric / Result:** Within-system test split R² = 0.70-0.99, nRMSE = 3-10% of rated capacity. Labeled throughout as MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED.
- **What It Does NOT Prove:** *Zero cross-system generalization demonstrated. No independent validation cohort. Does NOT prove solar failure detection or operational field accuracy.*
- **Claim IDs:** CLAIM-SOLAR-02

### `EVID-AGENT-01`: Local AI Agent Safety & Reasoning Battery
- **Technology:** Software / LLM Integration
- **Source Dataset:** Internal Deterministic Agent Evaluation Suite
- **Source Provenance:** 10 curated scenario fixtures from rai/eval/agent_eval.py
- **Evidence Class:** `INTERNAL_SYNTHETIC`
- **Real vs Synthetic:** `INTERNAL_SYNTHETIC`
- **Validation Status:** `DEMONSTRATED`
- **Artifact Path:** [`artifacts/evaluation/agent_eval/`](artifacts/evaluation/agent_eval/)
- **Report Path:** [`docs/evaluation/LOCAL_AGENT_EVALUATION.md`](docs/evaluation/LOCAL_AGENT_EVALUATION.md)
- **What Was Tested:** Agent tool selection, provenance preservation, mandatory abstention under symmetric evidence, schema validity, recommendation bounds, unsupported claim rate, and Needle 2 runtime performance.
- **Metric / Result:** Evaluator Tasks A-G passed 100%; Tool selection = 1.00; Abstention accuracy = 1.00; Unsupported claim rate = 0.00%; Needle 2 runtime benchmark: 6451.9 ms latency, concurrency safe.
- **What It Does NOT Prove:** *Does not prove production field performance, reasoning on unstructured edge cases, or multi-turn conversational robustness under unmodelled field anomalies.*
- **Claim IDs:** CLAIM-AGENT-01

### `EVID-RAG-01`: Historical Precedent Case Retrieval
- **Technology:** Memory & Retrieval System
- **Source Dataset:** 14 External Real Cases (CARE, Kelmarsh, PVDAQ) + 14 Synthetic Reference Scenarios
- **Source Provenance:** Curated benchmark cases with complete provenance tracking in rai/memory/real_corpus.py
- **Evidence Class:** `EXTERNAL_BENCHMARK`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/retrieval_benchmark_results.json`](artifacts/retrieval_benchmark_results.json)
- **Report Path:** [`docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md`](docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md)
- **What Was Tested:** 10 deterministic search queries evaluating Precision@1, Precision@3, Recall@3, MRR, Partition Purity, Provenance Preservation, and Abstention on out-of-scope queries.
- **Metric / Result:** Mean Precision@1 = 90.0%, Recall@3 = 85.0%, MRR = 0.950, Partition Purity = 100.0%, Provenance Preservation = 100.0%, Abstention Accuracy = 100.0%.
- **What It Does NOT Prove:** *Retrieval of past similar episodes is contextual precedent matching only. It does NOT prove causal failure diagnosis or ground-truth prediction of the current active fault.*
- **Claim IDs:** CLAIM-RAG-01

### `EVID-LOOP-01`: Closed-Loop Operational Ingestion & Promotion Gate
- **Technology:** Full-Stack System Workflow
- **Source Dataset:** Simulated Work Order Lifecycle in Browser & API
- **Source Provenance:** End-to-end browser walkthrough with Playwright across /work-orders and /assets/WT-004
- **Evidence Class:** `DEMONSTRATION_ONLY`
- **Real vs Synthetic:** `INTERNAL_SYNTHETIC`
- **Validation Status:** `DEMONSTRATED`
- **Artifact Path:** [`browser_verification/`](browser_verification/)
- **Report Path:** [`docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md`](docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md)
- **What Was Tested:** 8-step operational loop: Anomaly -> Propose WO -> Reject -> Approve -> Dispatch -> Record Feedback -> Closed-Loop Case Ingestion -> Dual-Key Promotion Gate -> KPI Empty State.
- **Metric / Result:** 17 captured browser screenshots; complete lifecycle idempotency; dual-key promotion gate strictly enforces that demo/test tickets remain INTERNAL_SYNTHETIC and never contaminate EXTERNAL_REAL.
- **What It Does NOT Prove:** *Does not prove that autonomous continuous learning is occurring from live commercial utility data. Zero commercial utility sites are currently connected.*
- **Claim IDs:** CLAIM-LOOP-01

### `EVID-DISPATCH-01`: Safe-Weather Fleet Crew Dispatch Optimizer
- **Technology:** Operations & Logistics
- **Source Dataset:** Configured Meteorological Thresholds + Weather API Cache
- **Source Provenance:** Simulated and live-cached Open-Meteo forecasts for Charanka Solar and Kutch Wind
- **Evidence Class:** `SIMULATED_OUTCOME`
- **Real vs Synthetic:** `SIMULATED_OUTCOME`
- **Validation Status:** `ARCHITECTURALLY_SUPPORTED`
- **Artifact Path:** [`artifacts/weather_cache/`](artifacts/weather_cache/)
- **Report Path:** [`docs/checkpoints/24-crew-dispatch-weather-optimizer.md`](docs/checkpoints/24-crew-dispatch-weather-optimizer.md)
- **What Was Tested:** Wind nacelle climb speed gating (< 12 m/s), solar enclosure rain lockout (0 mm rain), work order priority sorting, window slot assignment.
- **Metric / Result:** Zero safety lockout violations during high wind (>12m/s) or rain; deterministic assignment of approved work orders to valid weather windows.
- **What It Does NOT Prove:** *Does not represent a certified legal or OSHA operational safety guarantee. Thresholds are site-specific configured heuristics.*
- **Claim IDs:** CLAIM-DISPATCH-01

### `EVID-SIM-01`: Physics-Based Telemetry & Fault Simulator
- **Technology:** Simulation Engine
- **Source Dataset:** rai/sim/ synthetic generation engine
- **Source Provenance:** Internal physics models for 18 wind turbines and 24 solar inverters
- **Evidence Class:** `INTERNAL_SYNTHETIC`
- **Real vs Synthetic:** `INTERNAL_SYNTHETIC`
- **Validation Status:** `DEMONSTRATED`
- **Artifact Path:** [`artifacts/evaluation/results.json`](artifacts/evaluation/results.json)
- **Report Path:** [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md)
- **What Was Tested:** Telemetry generation under 12 injected failure and environmental scenarios (bearing wear, pitch imbalance, soiling, curtailment, cloud transients).
- **Metric / Result:** 12/12 scenario-level equipment/non-equipment agreement; realistic diurnal cycles, wind power curves, and thermal curves.
- **What It Does NOT Prove:** *Synthetic scenario agreement is NOT real-world predictive accuracy. Internal simulator cannot validate operational reliability in the field.*
- **Claim IDs:** CLAIM-SIM-01

### `EVID-ECON-01`: Techno-Economic Decision Support Engine
- **Technology:** Decision Economics
- **Source Dataset:** Analytical NPV Decision Models (rai/economics/decision_support.py)
- **Source Provenance:** Configured commercial cost assumptions (tariffs, labor rates, parts costs)
- **Evidence Class:** `MODEL_COMPARISON`
- **Real vs Synthetic:** `SIMULATED_OUTCOME`
- **Validation Status:** `DEMONSTRATED`
- **Artifact Path:** [`tests/test_economic_decision_support.py`](tests/test_economic_decision_support.py)
- **Report Path:** [`docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md`](docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md)
- **What Was Tested:** Net present value calculation across intervention strategies (Act Now, Defer 3d, Defer 14d); explicit source labeling of assumptions, uncertainty components, and null handling.
- **Metric / Result:** Deterministic decision classification (INTERVENE, INSPECT, MONITOR, WAIT, ABSTAIN) with 100% documented assumptions and zero fabricated probabilities.
- **What It Does NOT Prove:** *Economic outputs are modelled projections under assumed counterfactuals. They do NOT prove realized financial savings or verified failure probability distributions.*
- **Claim IDs:** CLAIM-ECON-01

### `EVID-COUNTER-01`: Counterevidence & Differential Diagnosis Engine
- **Technology:** Diagnostic Logic
- **Source Dataset:** rai/models/differential_diagnosis.py
- **Source Provenance:** Rule-based competing hypothesis generator for wind and solar assets
- **Evidence Class:** `SOFTWARE_INVARIANT`
- **Real vs Synthetic:** `SOFTWARE_INVARIANT`
- **Validation Status:** `ARCHITECTURALLY_SUPPORTED`
- **Artifact Path:** [`tests/test_differential_diagnosis.py`](tests/test_differential_diagnosis.py)
- **Report Path:** [`docs/checkpoints/22-counterevidence-differential-diagnosis.md`](docs/checkpoints/22-counterevidence-differential-diagnosis.md)
- **What Was Tested:** Systematic generation of competing hypotheses (e.g. bearing wear vs lubrication degradation; soiling vs string fault); active counterevidence evaluation; symmetric abstention.
- **Metric / Result:** 11/11 targeted tests passing; 100% abstention to COMPETING_HYPOTHESES when counterevidence is symmetric.
- **What It Does NOT Prove:** *Does not prove diagnostic accuracy against unmodelled failure modes or complex multi-fault cascaded failures in physical plant operations.*
- **Claim IDs:** CLAIM-DIAG-01

### `EVID-OOD-01`: Out-of-Distribution Robustness Suite
- **Technology:** Wind Anomaly Detection
- **Source Dataset:** Controlled Synthetic Perturbation Suite
- **Source Provenance:** Synthetic sensor drift, white noise, and scaling perturbations applied to SCADA
- **Evidence Class:** `SIMULATED_OUTCOME`
- **Real vs Synthetic:** `SIMULATED_OUTCOME`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/phase4/`](artifacts/evaluation/phase4/)
- **Report Path:** [`docs/evaluation/OOD.md`](docs/evaluation/OOD.md)
- **What Was Tested:** Model resilience under sensor calibration loss, anemometer bias, and extreme temperature noise.
- **Metric / Result:** Quantified degradation boundaries: CARE score drops from 0.797 to 0.520 and false alarms increase ~40x under severe sensor drift.
- **What It Does NOT Prove:** *Does not prove resilience under unmodelled non-Gaussian environmental shifts or novel aerodynamic conditions.*
- **Claim IDs:** CLAIM-OOD-01

### `EVID-REALCASES-01`: External Real Historical Precedent Corpus
- **Technology:** Memory Library
- **Source Dataset:** 14 Audited Cases (8 CARE, 4 Kelmarsh, 2 NREL PVDAQ OEDI)
- **Source Provenance:** Public benchmark datasets and open energy data lakes with verified DOIs and S3 paths
- **Evidence Class:** `EXTERNAL_REAL`
- **Real vs Synthetic:** `REAL_EXTERNAL_DATA`
- **Validation Status:** `VALIDATED`
- **Artifact Path:** [`artifacts/evaluation/real_case_provenance/`](artifacts/evaluation/real_case_provenance/)
- **Report Path:** [`docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md`](docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md)
- **What Was Tested:** Source provenance lineage, physical event types, and non-fault operational event classification.
- **Metric / Result:** Exactly 14 records verified; 8 confirmed equipment failures (CARE), 4 operational/maintenance events without damage (Kelmarsh), 2 environmental derates (PVDAQ).
- **What It Does NOT Prove:** *They are historical open-data benchmark precedents, NOT technician-verified live commercial utility deployment observations.*
- **Claim IDs:** CLAIM-RAG-01, CLAIM-REAL-01
