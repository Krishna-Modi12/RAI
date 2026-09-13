"""Scientific Evidence Freeze Generator for Renewable Asset Intelligence (RAI).

Produces the definitive evidence registry, claim-to-evidence matrix,
unsupported claims ledger, evidence matrix, and freeze summary under:
artifacts/evaluation/evidence_freeze/
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "artifacts" / "evaluation" / "evidence_freeze"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# 1. Evidence Registry (Items A through J)
# ----------------------------------------------------------------------

EVIDENCE_REGISTRY = [
    {
        "evidence_id": "EVID-CARE-01",
        "system_or_feature": "Wind Anomaly Detection Baseline",
        "technology": "Wind Turbines",
        "dataset_or_source": "CARE Benchmark (Zenodo 10.5281/zenodo.10958775)",
        "source_provenance": "Academic open benchmark from 3 operational wind farms (Farms A, B, C; 36 turbines total)",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "Multi-farm anomaly detection accuracy, Coverage, Reliability (CARE Algorithm 1), and Earliness on published SCADA and failure event logs. Evaluated on 36 turbines.",
        "metric_or_result": "Normal accuracy 0.995-0.999 across all 3 farms; CARE Operational Score 0.601 (Farm A), 0.560 (Farm B), 0.575 (Farm C); false alarm rate <= 0.005.",
        "what_it_does_NOT_prove": "Does not prove universal zero-shot generalization to uncalibrated fleets or novel turbine models. Does not prove causal root-cause diagnosis.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-WIND-01", "CLAIM-CARE-01"],
        "artifact_path": "artifacts/evaluation/external_care/",
        "report_path": "docs/evaluation/EXTERNAL_CARE.md",
    },
    {
        "evidence_id": "EVID-CARE-02",
        "system_or_feature": "Cross-Farm Wind Transfer & Calibration",
        "technology": "Wind Turbines",
        "dataset_or_source": "CARE Benchmark (Zenodo 10.5281/zenodo.10958775)",
        "source_provenance": "Cross-farm evaluation between Wind Farms A, B, and C under frozen CARE_COMMON input protocol",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "All 6 directed transfers (A->B, A->C, B->A, B->C, C->A, C->B) across 3 conditions (FROZEN_SOURCE, TARGET_NORMAL_CALIBRATED, TARGET_SPECIFIC_REFERENCE). Kolmogorov-Smirnov distribution shift quantification.",
        "metric_or_result": "Target-normal calibration using unlabelled SCADA completely recovers the transfer gap (106.3% recovery on C->A; normal accuracy restored from 0.5965 to 0.9963 on B->A).",
        "what_it_does_NOT_prove": "Does not prove that zero-shot uncalibrated transfer works across disparate turbine kinematics without unlabelled target telemetry.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-WIND-02", "CLAIM-TRANSFER-01"],
        "artifact_path": "artifacts/evaluation/gate54/",
        "report_path": "docs/checkpoints/14-gate54-cross-farm-wind-transfer.md",
    },
    {
        "evidence_id": "EVID-KEL-01",
        "system_or_feature": "Wind Operational Event Window Association",
        "technology": "Wind Turbines",
        "dataset_or_source": "Kelmarsh Wind Farm (Zenodo 10.5281/zenodo.5841834)",
        "source_provenance": "Open-access operational SCADA and Greenbyte status logs from 6 Senvion MM92 turbines in the UK",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "Association between RAI continuous anomaly scores and documented operational event periods (cable untwisting, curtailment, scheduled maintenance, environmental calm standstills).",
        "metric_or_result": "Statistically significant elevation of anomaly residuals during operational event intervals vs normal generation periods.",
        "what_it_does_NOT_prove": "MUST NOT be described as failure prediction or hardware failure validation. Public Kelmarsh dataset contains operational and maintenance logs, but NO verified component-failure labels.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-KELMARSH-01"],
        "artifact_path": "artifacts/evaluation/kelmarsh_event_behaviour/",
        "report_path": "docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md",
    },
    {
        "evidence_id": "EVID-PVDAQ-01",
        "system_or_feature": "Solar Data Foundation & Telemetry Acquisition",
        "technology": "Solar PV",
        "dataset_or_source": "NREL PVDAQ Open Energy Data Initiative (OEDI S3)",
        "source_provenance": "Public solar telemetry from NREL public data lake (Systems 34, 1283, 1239, 1430, 1433)",
        "evidence_class": "EXTERNAL_REAL",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "450 daily telemetry files downloaded and checksum-verified; 26-signal canonical solar taxonomy mapping; timestamp monotonicity, unit scale, and sensor quality audited (Gate 5.6A & 5.6B).",
        "metric_or_result": "Adjudicated cohort: Development=[1239, 1283, 34], Validation=[], State=INSUFFICIENT_DATA. Flagged that 1430/1433 have 100% null UTC timestamps and 1283 has no plant-level AC channel.",
        "what_it_does_NOT_prove": "Does not validate any solar performance or failure model. Validation cohort was explicitly empty.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-SOLAR-01"],
        "artifact_path": "artifacts/evaluation/gate56/cohort_adjudication/",
        "report_path": "docs/checkpoints/16-gate56b-cohort-adjudication.md",
    },
    {
        "evidence_id": "EVID-PVDAQ-02",
        "system_or_feature": "Solar Expected-Performance Model Development",
        "technology": "Solar PV",
        "dataset_or_source": "NREL PVDAQ Telemetry (Systems 1239, 1283, 34)",
        "source_provenance": "Development cohort telemetry fit with temporal within-system split",
        "evidence_class": "MODEL_COMPARISON",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "ModelChain physics reference vs polynomial empirical baseline vs hybrid champion on temporal holdouts within Systems 1239, 1283, 34 (Gate 5.6C).",
        "metric_or_result": "Within-system test split R² = 0.70-0.99, nRMSE = 3-10% of rated capacity. Labeled throughout as MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED.",
        "what_it_does_NOT_prove": "Zero cross-system generalization demonstrated. No independent validation cohort. Does NOT prove solar failure detection or operational field accuracy.",
        "validation_status": "NOT_VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-SOLAR-02"],
        "artifact_path": "artifacts/evaluation/gate56/gate56c_model_development/",
        "report_path": "docs/evaluation/GATE56C_VERIFICATION.md",
    },
    {
        "evidence_id": "EVID-AGENT-01",
        "system_or_feature": "Local AI Agent Safety & Reasoning Battery",
        "technology": "Software / LLM Integration",
        "dataset_or_source": "Internal Deterministic Agent Evaluation Suite",
        "source_provenance": "10 curated scenario fixtures from rai/eval/agent_eval.py",
        "evidence_class": "INTERNAL_SYNTHETIC",
        "real_vs_synthetic": "INTERNAL_SYNTHETIC",
        "what_was_actually_tested": "Agent tool selection, provenance preservation, mandatory abstention under symmetric evidence, schema validity, recommendation bounds, unsupported claim rate, and Needle 2 runtime performance.",
        "metric_or_result": "Evaluator Tasks A-G passed 100%; Tool selection = 1.00; Abstention accuracy = 1.00; Unsupported claim rate = 0.00%; Needle 2 runtime benchmark: 6451.9 ms latency, concurrency safe.",
        "what_it_does_NOT_prove": "Does not prove production field performance, reasoning on unstructured edge cases, or multi-turn conversational robustness under unmodelled field anomalies.",
        "validation_status": "DEMONSTRATED",
        "claim_ids_relying_on_it": ["CLAIM-AGENT-01"],
        "artifact_path": "artifacts/evaluation/agent_eval/",
        "report_path": "docs/evaluation/LOCAL_AGENT_EVALUATION.md",
    },
    {
        "evidence_id": "EVID-RAG-01",
        "system_or_feature": "Historical Precedent Case Retrieval",
        "technology": "Memory & Retrieval System",
        "dataset_or_source": "14 External Real Cases (CARE, Kelmarsh, PVDAQ) + 14 Synthetic Reference Scenarios",
        "source_provenance": "Curated benchmark cases with complete provenance tracking in rai/memory/real_corpus.py",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "10 deterministic search queries evaluating Precision@1, Precision@3, Recall@3, MRR, Partition Purity, Provenance Preservation, and Abstention on out-of-scope queries.",
        "metric_or_result": "Mean Precision@1 = 90.0%, Recall@3 = 85.0%, MRR = 0.950, Partition Purity = 100.0%, Provenance Preservation = 100.0%, Abstention Accuracy = 100.0%.",
        "what_it_does_NOT_prove": "Retrieval of past similar episodes is contextual precedent matching only. It does NOT prove causal failure diagnosis or ground-truth prediction of the current active fault.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-RAG-01"],
        "artifact_path": "artifacts/retrieval_benchmark_results.json",
        "report_path": "docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md",
    },
    {
        "evidence_id": "EVID-LOOP-01",
        "system_or_feature": "Closed-Loop Operational Ingestion & Promotion Gate",
        "technology": "Full-Stack System Workflow",
        "dataset_or_source": "Simulated Work Order Lifecycle in Browser & API",
        "source_provenance": "End-to-end browser walkthrough with Playwright across /work-orders and /assets/WT-004",
        "evidence_class": "DEMONSTRATION_ONLY",
        "real_vs_synthetic": "INTERNAL_SYNTHETIC",
        "what_was_actually_tested": "8-step operational loop: Anomaly -> Propose WO -> Reject -> Approve -> Dispatch -> Record Feedback -> Closed-Loop Case Ingestion -> Dual-Key Promotion Gate -> KPI Empty State.",
        "metric_or_result": "17 captured browser screenshots; complete lifecycle idempotency; dual-key promotion gate strictly enforces that demo/test tickets remain INTERNAL_SYNTHETIC and never contaminate EXTERNAL_REAL.",
        "what_it_does_NOT_prove": "Does not prove that autonomous continuous learning is occurring from live commercial utility data. Zero commercial utility sites are currently connected.",
        "validation_status": "DEMONSTRATED",
        "claim_ids_relying_on_it": ["CLAIM-LOOP-01"],
        "artifact_path": "browser_verification/",
        "report_path": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md",
    },
    {
        "evidence_id": "EVID-DISPATCH-01",
        "system_or_feature": "Safe-Weather Fleet Crew Dispatch Optimizer",
        "technology": "Operations & Logistics",
        "dataset_or_source": "Configured Meteorological Thresholds + Weather API Cache",
        "source_provenance": "Simulated and live-cached Open-Meteo forecasts for Charanka Solar and Kutch Wind",
        "evidence_class": "SIMULATED_OUTCOME",
        "real_vs_synthetic": "SIMULATED_OUTCOME",
        "what_was_actually_tested": "Wind nacelle climb speed gating (< 12 m/s), solar enclosure rain lockout (0 mm rain), work order priority sorting, window slot assignment.",
        "metric_or_result": "Zero safety lockout violations during high wind (>12m/s) or rain; deterministic assignment of approved work orders to valid weather windows.",
        "what_it_does_NOT_prove": "Does not represent a certified legal or OSHA operational safety guarantee. Thresholds are site-specific configured heuristics.",
        "validation_status": "ARCHITECTURALLY_SUPPORTED",
        "claim_ids_relying_on_it": ["CLAIM-DISPATCH-01"],
        "artifact_path": "artifacts/weather_cache/",
        "report_path": "docs/checkpoints/24-crew-dispatch-weather-optimizer.md",
    },
    {
        "evidence_id": "EVID-SIM-01",
        "system_or_feature": "Physics-Based Telemetry & Fault Simulator",
        "technology": "Simulation Engine",
        "dataset_or_source": "rai/sim/ synthetic generation engine",
        "source_provenance": "Internal physics models for 18 wind turbines and 24 solar inverters",
        "evidence_class": "INTERNAL_SYNTHETIC",
        "real_vs_synthetic": "INTERNAL_SYNTHETIC",
        "what_was_actually_tested": "Telemetry generation under 12 injected failure and environmental scenarios (bearing wear, pitch imbalance, soiling, curtailment, cloud transients).",
        "metric_or_result": "12/12 scenario-level equipment/non-equipment agreement; realistic diurnal cycles, wind power curves, and thermal curves.",
        "what_it_does_NOT_prove": "Synthetic scenario agreement is NOT real-world predictive accuracy. Internal simulator cannot validate operational reliability in the field.",
        "validation_status": "DEMONSTRATED",
        "claim_ids_relying_on_it": ["CLAIM-SIM-01"],
        "artifact_path": "artifacts/evaluation/results.json",
        "report_path": "docs/AUDIT_REPORT.md",
    },
    {
        "evidence_id": "EVID-ECON-01",
        "system_or_feature": "Techno-Economic Decision Support Engine",
        "technology": "Decision Economics",
        "dataset_or_source": "Analytical NPV Decision Models (rai/economics/decision_support.py)",
        "source_provenance": "Configured commercial cost assumptions (tariffs, labor rates, parts costs)",
        "evidence_class": "MODEL_COMPARISON",
        "real_vs_synthetic": "SIMULATED_OUTCOME",
        "what_was_actually_tested": "Net present value calculation across intervention strategies (Act Now, Defer 3d, Defer 14d); explicit source labeling of assumptions, uncertainty components, and null handling.",
        "metric_or_result": "Deterministic decision classification (INTERVENE, INSPECT, MONITOR, WAIT, ABSTAIN) with 100% documented assumptions and zero fabricated probabilities.",
        "what_it_does_NOT_prove": "Economic outputs are modelled projections under assumed counterfactuals. They do NOT prove realized financial savings or verified failure probability distributions.",
        "validation_status": "DEMONSTRATED",
        "claim_ids_relying_on_it": ["CLAIM-ECON-01"],
        "artifact_path": "tests/test_economic_decision_support.py",
        "report_path": "docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md",
    },
    {
        "evidence_id": "EVID-COUNTER-01",
        "system_or_feature": "Counterevidence & Differential Diagnosis Engine",
        "technology": "Diagnostic Logic",
        "dataset_or_source": "rai/models/differential_diagnosis.py",
        "source_provenance": "Rule-based competing hypothesis generator for wind and solar assets",
        "evidence_class": "SOFTWARE_INVARIANT",
        "real_vs_synthetic": "SOFTWARE_INVARIANT",
        "what_was_actually_tested": "Systematic generation of competing hypotheses (e.g. bearing wear vs lubrication degradation; soiling vs string fault); active counterevidence evaluation; symmetric abstention.",
        "metric_or_result": "11/11 targeted tests passing; 100% abstention to COMPETING_HYPOTHESES when counterevidence is symmetric.",
        "what_it_does_NOT_prove": "Does not prove diagnostic accuracy against unmodelled failure modes or complex multi-fault cascaded failures in physical plant operations.",
        "validation_status": "ARCHITECTURALLY_SUPPORTED",
        "claim_ids_relying_on_it": ["CLAIM-DIAG-01"],
        "artifact_path": "tests/test_differential_diagnosis.py",
        "report_path": "docs/checkpoints/22-counterevidence-differential-diagnosis.md",
    },
    {
        "evidence_id": "EVID-OOD-01",
        "system_or_feature": "Out-of-Distribution Robustness Suite",
        "technology": "Wind Anomaly Detection",
        "dataset_or_source": "Controlled Synthetic Perturbation Suite",
        "source_provenance": "Synthetic sensor drift, white noise, and scaling perturbations applied to SCADA",
        "evidence_class": "SIMULATED_OUTCOME",
        "real_vs_synthetic": "SIMULATED_OUTCOME",
        "what_was_actually_tested": "Model resilience under sensor calibration loss, anemometer bias, and extreme temperature noise.",
        "metric_or_result": "Quantified degradation boundaries: CARE score drops from 0.797 to 0.520 and false alarms increase ~40x under severe sensor drift.",
        "what_it_does_NOT_prove": "Does not prove resilience under unmodelled non-Gaussian environmental shifts or novel aerodynamic conditions.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-OOD-01"],
        "artifact_path": "artifacts/evaluation/phase4/",
        "report_path": "docs/evaluation/OOD.md",
    },
    {
        "evidence_id": "EVID-REALCASES-01",
        "system_or_feature": "External Real Historical Precedent Corpus",
        "technology": "Memory Library",
        "dataset_or_source": "14 Audited Cases (8 CARE, 4 Kelmarsh, 2 NREL PVDAQ OEDI)",
        "source_provenance": "Public benchmark datasets and open energy data lakes with verified DOIs and S3 paths",
        "evidence_class": "EXTERNAL_REAL",
        "real_vs_synthetic": "REAL_EXTERNAL_DATA",
        "what_was_actually_tested": "Source provenance lineage, physical event types, and non-fault operational event classification.",
        "metric_or_result": "Exactly 14 records verified; 8 confirmed equipment failures (CARE), 4 operational/maintenance events without damage (Kelmarsh), 2 environmental derates (PVDAQ).",
        "what_it_does_NOT_prove": "They are historical open-data benchmark precedents, NOT technician-verified live commercial utility deployment observations.",
        "validation_status": "VALIDATED",
        "claim_ids_relying_on_it": ["CLAIM-RAG-01", "CLAIM-REAL-01"],
        "artifact_path": "artifacts/evaluation/real_case_provenance/",
        "report_path": "docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md",
    },
]

# ----------------------------------------------------------------------
# 2. Claim-to-Evidence Matrix
# ----------------------------------------------------------------------

CLAIM_TO_EVIDENCE = [
    {
        "claim_id": "CLAIM-WIND-01",
        "claim_statement": "RAI reliably detects wind turbine anomalous behavior using physics-conditioned residual models against normal generation benchmarks.",
        "evidence_id": "EVID-CARE-01",
        "exact_artifact": "artifacts/evaluation/external_care/",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "scope": "Evaluated on 36 turbines across 3 commercial wind farms on the public CARE benchmark (Zenodo 10958775).",
        "limitation": "Evaluated on specific turbine types; does not guarantee zero-shot performance on uncalibrated turbine architectures.",
        "capability_level": "VALIDATED",
    },
    {
        "claim_id": "CLAIM-WIND-02",
        "claim_statement": "Target-normal calibration using unlabelled SCADA telemetry recovers cross-farm wind transfer performance.",
        "evidence_id": "EVID-CARE-02",
        "exact_artifact": "artifacts/evaluation/gate54/",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "scope": "Evaluated across all 6 directed pairs between CARE Farms A, B, and C under frozen CARE_COMMON protocol.",
        "limitation": "Requires at least 1-3 months of unlabelled normal operating SCADA from the target farm for calibration.",
        "capability_level": "VALIDATED",
    },
    {
        "claim_id": "CLAIM-KELMARSH-01",
        "claim_statement": "RAI anomaly scores associate with documented operational event windows at Kelmarsh Wind Farm.",
        "evidence_id": "EVID-KEL-01",
        "exact_artifact": "artifacts/evaluation/kelmarsh_event_behaviour/",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "scope": "Evaluated against operational and Greenbyte status logs from 6 Senvion MM92 turbines.",
        "limitation": "Does NOT constitute failure prediction or hardware failure validation. Kelmarsh logs document operational status and trips, not component mechanical failures.",
        "capability_level": "VALIDATED",
    },
    {
        "claim_id": "CLAIM-SOLAR-01",
        "claim_statement": "Real public solar plant telemetry was acquired, parsed, and audited for data-foundation readiness.",
        "evidence_id": "EVID-PVDAQ-01",
        "exact_artifact": "artifacts/evaluation/gate56/cohort_adjudication/",
        "evidence_class": "EXTERNAL_REAL",
        "scope": "450 daily telemetry files from NREL PVDAQ OEDI data lake across 5 candidate systems.",
        "limitation": "Data foundation and acquisition audit only; Validation cohort is empty (INSUFFICIENT_DATA); zero models validated in this step.",
        "capability_level": "VALIDATED",
    },
    {
        "claim_id": "CLAIM-SOLAR-02",
        "claim_statement": "Solar expected-performance model is independently validated for commercial production deployment.",
        "evidence_id": "EVID-PVDAQ-02",
        "exact_artifact": "artifacts/evaluation/gate56/gate56c_model_development/",
        "evidence_class": "NOT_VALIDATED",
        "scope": "Temporal within-system holdout on NREL Systems 1239, 1283, 34.",
        "limitation": "NOT INDEPENDENTLY VALIDATED. Gate 5.6C results represent preliminary model development only; no independent cross-system validation cohort exists.",
        "capability_level": "NOT_VALIDATED",
    },
    {
        "claim_id": "CLAIM-AGENT-01",
        "claim_statement": "Local AI agent operates within deterministic safety boundaries, enforces tool provenance, and abstains under symmetric evidence.",
        "evidence_id": "EVID-AGENT-01",
        "exact_artifact": "artifacts/evaluation/agent_eval/",
        "evidence_class": "INTERNAL_SYNTHETIC",
        "scope": "10 deterministic scenario fixtures evaluated across Tasks A through G.",
        "limitation": "Evaluated on internal synthetic test fixtures; does NOT prove production field conversational performance or unconstrained open-domain reasoning.",
        "capability_level": "DEMONSTRATED",
    },
    {
        "claim_id": "CLAIM-RAG-01",
        "claim_statement": "Historical case retrieval provides contextual precedent matches with complete provenance tracking and partition separation.",
        "evidence_id": "EVID-RAG-01",
        "exact_artifact": "artifacts/retrieval_benchmark_results.json",
        "evidence_class": "EXTERNAL_BENCHMARK",
        "scope": "10 deterministic test queries evaluated against 14 external real cases and 14 synthetic cases.",
        "limitation": "Contextual trajectory similarity only. Does NOT prove causal failure diagnosis or ground-truth prediction of the active asset fault.",
        "capability_level": "VALIDATED",
    },
    {
        "claim_id": "CLAIM-LOOP-01",
        "claim_statement": "Technician field feedback is captured through a closed-loop workflow and safely ingested into retrieval memory with strict provenance gating.",
        "evidence_id": "EVID-LOOP-01",
        "exact_artifact": "browser_verification/",
        "evidence_class": "DEMONSTRATION_ONLY",
        "scope": "End-to-end browser verification of /work-orders and /assets/WT-004 operational lifecycle in Next.js.",
        "limitation": "Demonstrated using internal synthetic and demo tickets. Zero commercial utility sites are currently connected; does NOT prove live autonomous learning.",
        "capability_level": "DEMONSTRATED",
    },
    {
        "claim_id": "CLAIM-DISPATCH-01",
        "claim_statement": "Fleet crew dispatch schedules work orders into meteorological safety windows considering wind speed and rain limits.",
        "evidence_id": "EVID-DISPATCH-01",
        "exact_artifact": "artifacts/weather_cache/",
        "evidence_class": "SIMULATED_OUTCOME",
        "scope": "Simulated and weather-cached wind (<12 m/s) and solar (0 mm rain) constraint scheduler.",
        "limitation": "Configured operational heuristics for decision support; does NOT constitute a certified legal or OSHA safety guarantee.",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "claim_id": "CLAIM-SIM-01",
        "claim_statement": "Simulator accurately reproduces physical SCADA failure dynamics and environmental transients across wind and solar fleets.",
        "evidence_id": "EVID-SIM-01",
        "exact_artifact": "artifacts/evaluation/results.json",
        "evidence_class": "INTERNAL_SYNTHETIC",
        "scope": "12 injected failure scenarios across 18 wind turbines and 24 solar inverters.",
        "limitation": "Synthetic agreement is not real-world predictive accuracy. Internal simulator models cannot validate real-world operational reliability.",
        "capability_level": "DEMONSTRATED",
    },
    {
        "claim_id": "CLAIM-ECON-01",
        "claim_statement": "Techno-economic decision engine outputs actionable intervention advice based on explicit cost assumptions.",
        "evidence_id": "EVID-ECON-01",
        "exact_artifact": "tests/test_economic_decision_support.py",
        "evidence_class": "MODEL_COMPARISON",
        "scope": "NPV comparison across Act Now vs Defer strategies with source-labeled assumptions.",
        "limitation": "Modelled projected exposure under assumed counterfactuals; does NOT represent realized cost savings or empirically validated failure probabilities.",
        "capability_level": "DEMONSTRATED",
    },
    {
        "claim_id": "CLAIM-DIAG-01",
        "claim_statement": "Differential diagnosis engine systematically generates competing hypotheses and rules out false single faults.",
        "evidence_id": "EVID-COUNTER-01",
        "exact_artifact": "tests/test_differential_diagnosis.py",
        "evidence_class": "SOFTWARE_INVARIANT",
        "scope": "Rule-based competing hypothesis elimination across wind and solar subsystems.",
        "limitation": "Deterministic heuristic logic; does not prove accuracy against unmodelled failure modes or complex multi-fault cascaded failures.",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "claim_id": "CLAIM-PROD-01",
        "claim_statement": "RAI is fully deployed and continuously validated on live commercial utility plants in production.",
        "evidence_id": "EVID-LOOP-01",
        "exact_artifact": "docs/CLAIMS.md",
        "evidence_class": "NOT_VALIDATED",
        "scope": "No live commercial plant telemetry feed or operational utility integration exists in this repository.",
        "limitation": "NOT VALIDATED. Live commercial production deployment is a future roadmap milestone, not a current capability.",
        "capability_level": "NOT_VALIDATED",
    },
]

# ----------------------------------------------------------------------
# 3. Unsupported Claims / Downgrade Ledger
# ----------------------------------------------------------------------

UNSUPPORTED_CLAIMS = [
    {
        "unsupported_claim_id": "UNSUP-01",
        "original_wording": "16 real adjudicated cases (10 wind + 6 solar from PVPMC)",
        "source_location": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md, CHECKPOINT.md",
        "evidence_gap_reason": "Corpus contains 14 external real cases (12 wind + 2 solar). The 6 solar cases are internal synthetic scenarios in library.py, not from Sandia PVPMC.",
        "remedy_or_downgrade": "Corrected count to 14 external real cases (12 wind, 2 solar) + 14 reference synthetic scenarios. Removed false attribution to Sandia PVPMC.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-02",
        "original_wording": "Kelmarsh provides an independent component-failure benchmark for RAI",
        "source_location": "docs/CLAIMS.md (Line 18)",
        "evidence_gap_reason": "Public Kelmarsh dataset inventory confirms component failure ground-truth labels are unavailable; logs reflect operational status and trips only.",
        "remedy_or_downgrade": "Explicitly declared NOT_VALIDATED for failure prediction. Re-scoped strictly to operational event window association.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-03",
        "original_wording": "Solar expected-performance model is independently validated (Gate 5.6C)",
        "source_location": "docs/CLAIMS.md (Line 17)",
        "evidence_gap_reason": "Gate 5.6B Validation cohort was empty (INSUFFICIENT_DATA). Gate 5.6C models were tested on temporal within-system holdouts only.",
        "remedy_or_downgrade": "Explicitly declared NOT_VALIDATED for independent validation. Labeled throughout as MODEL_DEVELOPMENT.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-04",
        "original_wording": "Realized cost savings / Avoided Loss (financial KPI)",
        "source_location": "web/src/app/work-orders/page.tsx, EvidenceAccordion.tsx",
        "evidence_gap_reason": "Counterfactual cost savings cannot be directly observed without a randomized control trial in the field.",
        "remedy_or_downgrade": "Re-labeled UI headers to 'Projected Avoidable Exposure (Modelled risk estimate)'. Separated modelled exposure from realised parts costs.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-05",
        "original_wording": "Continuous learning from live utility operational feedback",
        "source_location": "Closed-loop narrative drafts",
        "evidence_gap_reason": "Zero live commercial sites are currently connected; all feedback tickets in tickets.jsonl are test fixtures or demo simulations.",
        "remedy_or_downgrade": "Re-scoped to 'Demonstrated operational lifecycle on internal synthetic fixtures'. Dual-key promotion gate strictly enforces quarantine of test tickets.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-06",
        "original_wording": "Certified meteorological safety guarantee for crew dispatch",
        "source_location": "Dispatch narrative drafts",
        "evidence_gap_reason": "Safety window optimization is a heuristic decision-support engine using configured thresholds and third-party weather forecasts.",
        "remedy_or_downgrade": "Re-labeled as 'Configured Operational Constraints (Site Dispatch Heuristics)'. Explicitly disclaimed as an OSHA or certified legal safety guarantee.",
        "status": "REMEDIED",
    },
]

# ----------------------------------------------------------------------
# 4. Final 13-Capability Scorecard
# ----------------------------------------------------------------------

CAPABILITY_SCORECARD = [
    {
        "capability": "Wind Anomaly Detection",
        "evidence": "CARE Benchmark (Farms A, B, C; Zenodo 10958775; 36 turbines)",
        "status": "VALIDATED",
        "real_vs_synthetic": "Real External Data",
        "external_validation": "Yes (CARE 0.56-0.60, Normal Acc > 0.995)",
        "main_limitation": "Evaluated on specific turbine types; does not guarantee zero-shot accuracy without target-normal calibration.",
    },
    {
        "capability": "Cross-Farm Transfer",
        "evidence": "CARE Benchmark 6 directed transfers (Gate 5.4)",
        "status": "VALIDATED",
        "real_vs_synthetic": "Real External Data",
        "external_validation": "Yes (106.3% gap recovery via unlabelled SCADA)",
        "main_limitation": "Requires unlabelled normal operating SCADA from the target farm; raw uncalibrated zero-shot transfer degrades.",
    },
    {
        "capability": "Environmental Discrimination",
        "evidence": "CAMS Dust Memory (D(t)), pvlib clear-sky POA, Peer Gating",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Simulated & Cached Forecasts",
        "external_validation": "Partial (External CAMS weather data + synthetic injection)",
        "main_limitation": "Evaluated on synthetic transient injection and historical atmospheric feeds, not live physical field instrumentation.",
    },
    {
        "capability": "Solar Modeling Readiness",
        "evidence": "NREL PVDAQ OEDI 450 daily files (Gate 5.6A/B)",
        "status": "VALIDATED",
        "real_vs_synthetic": "Real External Data",
        "external_validation": "Data foundation only (Cohort Development=[1239, 1283, 34], Validation=[])",
        "main_limitation": "Validation cohort is empty (INSUFFICIENT_DATA). Gate 5.6C solar model is NOT INDEPENDENTLY VALIDATED.",
    },
    {
        "capability": "Differential Diagnosis",
        "evidence": "Counterevidence Engine (rai/models/differential_diagnosis.py)",
        "status": "ARCHITECTURALLY_SUPPORTED",
        "real_vs_synthetic": "Software Invariant",
        "external_validation": "No (11 deterministic invariant tests passing)",
        "main_limitation": "Rule-based competing hypothesis elimination; does not validate diagnostic accuracy against unmodelled physical anomalies.",
    },
    {
        "capability": "Historical Precedent Retrieval",
        "evidence": "14 External Real Cases (CARE, Kelmarsh, PVDAQ) on 10 deterministic queries",
        "status": "VALIDATED",
        "real_vs_synthetic": "Real External Precedents",
        "external_validation": "Yes (P@1=90.0%, R@3=85.0%, Partition Purity=100%)",
        "main_limitation": "Contextual precedent trajectory retrieval only; does NOT prove causal failure diagnosis or ground-truth prediction.",
    },
    {
        "capability": "Local AI Agent Reasoning",
        "evidence": "Internal 10-fixture evaluation battery (Tasks A-G, Needle 2 benchmark)",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Internal Synthetic Battery",
        "external_validation": "No (100% pass on internal deterministic suite; 0.00% unsupported claims)",
        "main_limitation": "Bounded reasoning and tool selection on synthetic fixtures; does not prove production conversational field performance.",
    },
    {
        "capability": "Economic Decision Support",
        "evidence": "Techno-Economic Engine (rai/economics/decision_support.py)",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Analytical Mathematical Model",
        "external_validation": "No (Verified against mathematical invariants)",
        "main_limitation": "Modelled/projected exposure under stated assumptions; does NOT represent realized cost savings or empirical failure probabilities.",
    },
    {
        "capability": "Intervention Recommendation",
        "evidence": "Confidence-gated decision policy with explicit abstention (rai/agent/fallback.py)",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Software Invariant",
        "external_validation": "No (Deterministic rule engine)",
        "main_limitation": "Proposal-only decision support for human operators; system never executes autonomous plant control actions.",
    },
    {
        "capability": "Work Order Lifecycle",
        "evidence": "Next.js Console (/work-orders) + FastAPI lifecycle routes",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Interactive Browser & API",
        "external_validation": "No (End-to-end browser verified with Playwright)",
        "main_limitation": "Workflow orchestration and operator approval interface; requires human operator sign-off before dispatch.",
    },
    {
        "capability": "Crew Dispatch Optimization",
        "evidence": "Safe-Weather Optimizer (rai/decision/dispatch_optimizer.py)",
        "status": "ARCHITECTURALLY_SUPPORTED",
        "real_vs_synthetic": "Simulated Constraints + Weather Cache",
        "external_validation": "No (Deterministic constraint scheduling)",
        "main_limitation": "Configured operational heuristics (<12m/s nacelle, 0mm rain); does NOT constitute a certified safety guarantee.",
    },
    {
        "capability": "Technician Feedback Capture",
        "evidence": "Work Order feedback ledger (artifacts/tickets.jsonl)",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Synthetic Demo Fixtures",
        "external_validation": "No (Tested via Playwright & API unit tests)",
        "main_limitation": "Tested with simulated technician feedback in demo; zero live commercial utility technicians are currently active.",
    },
    {
        "capability": "Closed-Loop Learning",
        "evidence": "Feedback-to-Retrieval Ingestion with Dual-Key Promotion Gate",
        "status": "DEMONSTRATED",
        "real_vs_synthetic": "Internal Synthetic Corpus Only",
        "external_validation": "No (Browser verified; dual-key gate programmatically enforced)",
        "main_limitation": "Demonstrated operational mechanism on internal fixtures; does NOT prove continuous autonomous learning from live commercial utility data.",
    },
]


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_freeze_summary_md() -> str:
    lines = [
        "# SCIENTIFIC EVIDENCE FREEZE — RENEWABLE ASSET INTELLIGENCE (RAI)",
        "",
        "> **Official Evidence Freeze State.** All empirical claims, benchmark figures, demonstration",
        "> capabilities, and architectural features across Renewable Asset Intelligence are formally audited,",
        "> categorized, and frozen. Evidence determines the claim — never the reverse.",
        "",
        "**Freeze Date:** 2026-09-13  ",
        "**Audit Commit:** `acd214f`  ",
        "**Governing Principles:**",
        "1. Never fabricate, infer, or upgrade provenance.",
        "2. Do not reinterpret synthetic/demo/test fixtures as real.",
        "3. Preserve all existing safety and provenance boundaries.",
        "4. Every claim must trace directly to an audited executable artifact.",
        "",
        "---",
        "",
        "## 1. The Four-Level Capability Taxonomy",
        "",
        "Every capability in RAI is assigned exactly one of four formal tiers:",
        "",
        "| Level | Formal Definition | Scope in RAI |",
        "|---|---|---|",
        "| **1. VALIDATED** | Measured against an appropriate external dataset or peer-reviewed public benchmark. | Wind Anomaly Detection (CARE A/B/C), Cross-Farm Transfer (Gate 5.4), Solar Data Foundation (Gate 5.6A/B), Kelmarsh Event Association, Historical Case Retrieval (14 external cases). |",
        "| **2. DEMONSTRATED** | Fully implemented and functioning end-to-end, but demonstrated using controlled, synthetic, or internal scenario fixtures. | Simulator Physics Agreement, Local AI Agent Safety Battery, Techno-Economic Decision Support, Work Order Lifecycle, Closed-Loop Ingestion Mechanism, Technician Feedback Capture. |",
        "| **3. ARCHITECTURALLY SUPPORTED** | Implemented and technically bounded in software, but not externally validated against real-world physical outcomes. | Counterevidence & Differential Diagnosis Engine, Safe-Weather Crew Dispatch Optimizer. |",
        "| **4. NOT VALIDATED** | Explicitly not supported by current evidence; must NEVER be claimed as an accomplished capability. | Independent Solar Model Validation (Gate 5.6C), Kelmarsh Failure Prediction / Hardware Damage, Real-Time Commercial Utility Deployment, Autonomous Self-Learning from Live Grid Data. |",
        "",
        "---",
        "",
        "## 2. Authoritative 13-Capability Scorecard",
        "",
        "| Capability | Evidence Source | Formal Level | Real vs Synthetic | External Validation? | Main Limitation |",
        "|---|---|---|---|---|---|",
    ]

    for item in CAPABILITY_SCORECARD:
        lines.append(
            f"| **{item['capability']}** | {item['evidence']} | `{item['status']}` | {item['real_vs_synthetic']} | {item['external_validation']} | {item['main_limitation']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Critical Evidence Boundaries & Negative Declarations",
        "",
        "### A. Wind Domain (CARE & Kelmarsh)",
        "- **CARE Benchmark (Zenodo 10958775):** Provides genuine external validation of physics-conditioned residual anomaly detection (Normal Accuracy > 0.995, CARE Operational Score 0.56–0.60 on 36 turbines). Target-normal calibration recovers 106.3% of the cross-farm transfer gap on Farm C->A.",
        "- **Kelmarsh Benchmark (Zenodo 5841834):** Statistically associates RAI continuous anomaly scores with documented operational event windows (cable untwisting, curtailment, scheduled maintenance, calm standstills). **NEGATIVE DECLARATION:** Kelmarsh does NOT validate failure prediction or hardware damage; no mechanical failure ground-truth labels exist in the public record.",
        "",
        "### B. Solar Domain (PVDAQ & Gate 5.6)",
        "- **Gate 5.6A/5.6B (Data Foundation):** 450 checksummed telemetry files acquired from NREL PVDAQ OEDI. Adjudicated cohort: Development=`[1239, 1283, 34]`, Validation=`[]` (`INSUFFICIENT_DATA`).",
        "- **Gate 5.6C (Model Development):** pvlib ModelChain physics reference vs empirical baseline vs hybrid champion fit on within-system temporal holdouts ($R^2 = 0.70–0.99$). **NEGATIVE DECLARATION:** Labeled throughout as `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED`. Zero cross-system generalization demonstrated. No independent validation cohort.",
        "",
        "### C. Local AI Agent",
        "- Evaluator Tasks A through G passed on 10 deterministic scenario fixtures (Tool Selection = 1.00, Abstention = 1.00, Unsupported Claim Rate = 0.00%, Needle 2 runtime 6451 ms).",
        "- **NEGATIVE DECLARATION:** Demonstrates safety invariants and bounded reasoning on internal synthetic fixtures; does NOT prove production field performance on unmodelled conversational inputs.",
        "",
        "### D. Closed-Loop Lifecycle & Learning",
        "- Complete operational lifecycle (Propose -> Approve -> Dispatch -> Feedback -> Case Ingestion) verified in browser across 8 steps and 17 screenshots.",
        "- Dual-key promotion gate (`FeedbackProvenance.EXTERNAL_FIELD_OBSERVED` AND `ObservationLevel.FIELD_VERIFIED`) prevents test/demo tickets from contaminating `EXTERNAL_REAL` retrieval memory.",
        "- **NEGATIVE DECLARATION:** Zero live commercial utility sites are connected. Current tickets are quarantined test fixtures or demo records. Demonstrates workflow mechanics, NOT autonomous learning from live grid data.",
        "",
        "### E. Economics & Dispatch",
        "- Decision engine calculates net financial consequences across intervention options using stated cost assumptions.",
        "- **NEGATIVE DECLARATION:** Modelled projected exposure under assumed counterfactuals; does NOT represent realized financial savings. Safe-weather dispatch uses site-specific heuristic constraints, NOT certified legal safety guarantees.",
        "",
        "---",
        "",
        "## 4. Summary of Frozen Artifacts",
        "",
        "The following artifacts in `artifacts/evaluation/evidence_freeze/` form the definitive audit trail:",
        "- `evidence_registry.csv`: Complete metadata for all 14 evidence sources (A through J).",
        "- `evidence_registry.json`: Structured machine-readable registry with full citation references.",
        "- `evidence_matrix.md`: Comprehensive evidence matrix detailing methodologies, scopes, and bounds.",
        "- `claim_to_evidence.csv`: Strict mapping from every public claim to its exact supporting artifact.",
        "- `unsupported_claims.csv`: Log of 6 identified overstatements and their verified remedies.",
        "- `freeze_summary.md`: This executive governance document.",
    ])

    return "\n".join(lines)


def generate_evidence_matrix_md() -> str:
    lines = [
        "# SCIENTIFIC EVIDENCE MATRIX — DETAILED METHODOLOGY & PROVENANCE",
        "",
        "This matrix provides the complete audit specification for every evidence source in RAI.",
        "",
        "| Evidence ID | Feature / System | Source Dataset | Evidence Class | Reality Status | Validation Status | Exact Artifact |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in EVIDENCE_REGISTRY:
        lines.append(
            f"| `{item['evidence_id']}` | {item['system_or_feature']} | {item['dataset_or_source']} | `{item['evidence_class']}` | `{item['real_vs_synthetic']}` | `{item['validation_status']}` | `{item['artifact_path']}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Evidence Item Profiles",
        "",
    ])

    for item in EVIDENCE_REGISTRY:
        lines.extend([
            f"### `{item['evidence_id']}`: {item['system_or_feature']}",
            f"- **Technology:** {item['technology']}",
            f"- **Source Dataset:** {item['dataset_or_source']}",
            f"- **Source Provenance:** {item['source_provenance']}",
            f"- **Evidence Class:** `{item['evidence_class']}`",
            f"- **Real vs Synthetic:** `{item['real_vs_synthetic']}`",
            f"- **Validation Status:** `{item['validation_status']}`",
            f"- **Artifact Path:** [`{item['artifact_path']}`]({item['artifact_path']})",
            f"- **Report Path:** [`{item['report_path']}`]({item['report_path']})",
            f"- **What Was Tested:** {item['what_was_actually_tested']}",
            f"- **Metric / Result:** {item['metric_or_result']}",
            f"- **What It Does NOT Prove:** *{item['what_it_does_NOT_prove']}*",
            f"- **Claim IDs:** {', '.join(item['claim_ids_relying_on_it'])}",
            "",
        ])

    return "\n".join(lines)


def main():
    print("Generating Scientific Evidence Freeze artifacts...")

    # 1. evidence_registry.csv & json
    write_csv(OUT_DIR / "evidence_registry.csv", EVIDENCE_REGISTRY)
    with open(OUT_DIR / "evidence_registry.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "freeze_date": "2026-09-13",
                "total_evidence_sources": len(EVIDENCE_REGISTRY),
                "evidence_sources": EVIDENCE_REGISTRY,
                "capability_scorecard": CAPABILITY_SCORECARD,
            },
            f,
            indent=2,
        )

    # 2. claim_to_evidence.csv
    write_csv(OUT_DIR / "claim_to_evidence.csv", CLAIM_TO_EVIDENCE)

    # 3. unsupported_claims.csv
    write_csv(OUT_DIR / "unsupported_claims.csv", UNSUPPORTED_CLAIMS)

    # 4. evidence_matrix.md
    with open(OUT_DIR / "evidence_matrix.md", "w", encoding="utf-8") as f:
        f.write(generate_evidence_matrix_md())

    # 5. freeze_summary.md
    with open(OUT_DIR / "freeze_summary.md", "w", encoding="utf-8") as f:
        f.write(generate_freeze_summary_md())

    print(f"Successfully generated all evidence freeze artifacts in {OUT_DIR}")


if __name__ == "__main__":
    main()
