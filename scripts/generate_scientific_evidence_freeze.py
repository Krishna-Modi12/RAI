"""Scientific Evidence Freeze Generator for Renewable Asset Intelligence (RAI).

Produces the authoritative capability-to-evidence registry, claim-to-evidence matrix,
unsupported-claims ledger, evidence matrix, and freeze summary under:
artifacts/evaluation/evidence_freeze/

Every row traces to an existing, previously-generated artifact or report already present in
this repository. This script assembles and formats that evidence; it does not compute new
metrics, run new evaluations, or invent numbers. See docs/evaluation/ and artifacts/evaluation/
for the underlying source material cited in each row's `artifact` / `dataset_or_fixture` field.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "artifacts" / "evaluation" / "evidence_freeze"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FREEZE_DATE = "2026-09-13"
AUDIT_COMMIT = "acd214f"

# ----------------------------------------------------------------------
# 1. Capability Evidence Registry
#
# One row per named capability in the Evidence Freeze audit scope. Fields match the
# scientific-evidence-freeze specification exactly:
#   capability, evidence_source, dataset_or_fixture, real_or_synthetic,
#   external_or_internal, metric_or_result, artifact,
#   what_the_evidence_actually_proves, what_it_does_NOT_prove, final_status
#
# final_status is exactly one of: VALIDATED, DEMONSTRATED, ARCHITECTURALLY_SUPPORTED,
# NOT_VALIDATED.
# ----------------------------------------------------------------------

CAPABILITY_REGISTRY = [
    {
        "capability": "CARE wind anomaly detection",
        "evidence_source": "CARE to Compare benchmark (Fraunhofer IEE), Zenodo 10.5281/zenodo.10958775 — 3 wind farms (A/B/C), 36 turbines, author-labeled failure events",
        "dataset_or_fixture": "CARE Farms A/B/C SCADA + failure event logs",
        "real_or_synthetic": "REAL",
        "external_or_internal": "EXTERNAL",
        "metric_or_result": "Normal accuracy 0.995-0.999 across all 3 farms; CARE Operational Score 0.601 (A), 0.560 (B), 0.575 (C); false alarm rate <= 0.005",
        "artifact": "artifacts/evaluation/external_care/ ; docs/evaluation/EXTERNAL_CARE.md",
        "what_the_evidence_actually_proves": "The physics-conditioned residual anomaly detector discriminates documented real turbine failure events from normal SCADA on an independent public benchmark across 3 farms.",
        "what_it_does_NOT_prove": "Universal zero-shot generalization to uncalibrated fleets or novel turbine models; causal root-cause diagnosis of the detected anomaly.",
        "final_status": "VALIDATED",
    },
    {
        "capability": "CARE cross-farm transfer",
        "evidence_source": "CARE benchmark, 6 directed transfers under frozen CARE_COMMON protocol (Gate 5.4)",
        "dataset_or_fixture": "CARE Farms A/B/C cross-evaluation (A<->B, A<->C, B<->C)",
        "real_or_synthetic": "REAL",
        "external_or_internal": "EXTERNAL",
        "metric_or_result": "Target-normal calibration recovers 106.3% of the transfer gap on C->A; B->A normal accuracy restored from 0.5965 to 0.9963",
        "artifact": "artifacts/evaluation/gate54/ ; docs/checkpoints/14-gate54-cross-farm-wind-transfer.md",
        "what_the_evidence_actually_proves": "Calibrating on a small amount of unlabelled normal SCADA from a new (target) farm recovers cross-farm anomaly-detection performance on the real CARE benchmark.",
        "what_it_does_NOT_prove": "Raw, uncalibrated zero-shot transfer works without any target-farm telemetry; performance on farms/turbine types outside the CARE benchmark.",
        "final_status": "VALIDATED",
    },
    {
        "capability": "Kelmarsh benchmark",
        "evidence_source": "Kelmarsh Wind Farm open dataset (Plumley), Zenodo 10.5281/zenodo.5841834 — 6 Senvion MM92 turbines, UK",
        "dataset_or_fixture": "Kelmarsh SCADA + Greenbyte operational status/event codes",
        "real_or_synthetic": "REAL",
        "external_or_internal": "EXTERNAL",
        "metric_or_result": "Statistically significant elevation of RAI anomaly residuals during documented operational/maintenance event windows (cable untwist, curtailment, scheduled maintenance stop, calm-standstill)",
        "artifact": "artifacts/evaluation/kelmarsh_event_behaviour/ ; docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md",
        "what_the_evidence_actually_proves": "RAI's continuous anomaly score behaves consistently with independently logged operational events on a second, independent real wind farm dataset.",
        "what_it_does_NOT_prove": "Failure prediction or hardware/component-failure detection. Kelmarsh's public record contains zero verified mechanical-failure ground truth; it documents operational status and trips only.",
        "final_status": "VALIDATED",
    },
    {
        "capability": "Environmental context / discrimination",
        "evidence_source": "pvlib clear-sky/POA physics baseline + CAMS/Open-Meteo dust & precipitation forecasts + peer-turbine gating (rai/models/environment_solar.py, rai/models/weather_provider.py)",
        "dataset_or_fixture": "Real cached/live Open-Meteo + CAMS weather feeds applied to internal simulator-generated telemetry; Gate 2 leakage-hardened internal evaluation",
        "real_or_synthetic": "MIXED (real external weather data; internal synthetic telemetry for fault/no-fault ground truth)",
        "external_or_internal": "MIXED (external weather API + internal test scenarios)",
        "metric_or_result": "Deterministic unit tests passing for clear-sky/soiling/curtailment additive loss decomposition; Gate 2 audit reports false alarm rate 0.19/asset-year post peer-gating on leakage-hardened internal evaluation",
        "artifact": "tests/test_environment_solar.py ; docs/evaluation/GATE2_FORENSIC_AUDIT.md",
        "what_the_evidence_actually_proves": "The system computes a physics-grounded expected-clean-power baseline from real weather inputs and can rule out environmental causes (irradiance, soiling, curtailment) before asserting an equipment fault, verified deterministically and under a zero-leakage audit.",
        "what_it_does_NOT_prove": "Real-world misdiagnosis rate on live plant instrumentation; evaluation ground truth is internal-simulator-based, not independently observed field weather/fault co-occurrence.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Solar PVDAQ data foundation",
        "evidence_source": "NREL PVDAQ Open Energy Data Initiative (OEDI S3) — Systems 34, 1283, 1239, 1430, 1433",
        "dataset_or_fixture": "450 daily telemetry files, checksum-verified, mapped to canonical 26-signal solar taxonomy",
        "real_or_synthetic": "REAL",
        "external_or_internal": "EXTERNAL",
        "metric_or_result": "Adjudicated cohort: Development=[1239, 1283, 34], Validation=[] (state INSUFFICIENT_DATA); Systems 1430/1433 excluded (100% null UTC timestamps / no plant-level AC channel)",
        "artifact": "artifacts/evaluation/gate56/cohort_adjudication/ ; docs/checkpoints/13-solar-data-foundation.md",
        "what_the_evidence_actually_proves": "Real public solar telemetry was acquired, checksum-verified, and mapped to a canonical schema, with documented, evidence-based data-quality exclusions.",
        "what_it_does_NOT_prove": "Any solar performance or fault model. This gate validates data acquisition only; the validation cohort produced by adjudication is empty, so no model has been independently evaluated on held-out systems.",
        "final_status": "VALIDATED",
    },
    {
        "capability": "Solar physics layer",
        "evidence_source": "pvlib ModelChain physics reference vs polynomial empirical baseline vs hybrid champion model (Gate 5.6C)",
        "dataset_or_fixture": "Development cohort only (NREL PVDAQ Systems 1239, 1283, 34), temporal within-system holdout split",
        "real_or_synthetic": "REAL telemetry; NOT_INDEPENDENTLY_VALIDATED methodology",
        "external_or_internal": "EXTERNAL data source; INTERNAL model development",
        "metric_or_result": "Within-system temporal holdout: R^2 = 0.70-0.99, nRMSE = 3-10% of rated capacity",
        "artifact": "artifacts/evaluation/gate56/gate56c_model_development/ ; docs/evaluation/GATE56C_VERIFICATION.md ; docs/evaluation/SOLAR_EXPECTED_PERFORMANCE.md",
        "what_the_evidence_actually_proves": "Candidate solar expected-performance models fit real PVDAQ telemetry reasonably well on held-out time windows of the SAME systems they were developed on.",
        "what_it_does_NOT_prove": "Independent or cross-system validation. Gate 5.6B's Validation cohort is empty (INSUFFICIENT_DATA); therefore Gate 5.6C cannot be, and is not, independently validated. Zero cross-system generalization has been demonstrated.",
        "final_status": "NOT_VALIDATED",
    },
    {
        "capability": "Diagnosis",
        "evidence_source": "Counterevidence & differential diagnosis engine (rai/models/differential_diagnosis.py) + deterministic evidence reasoner (rai/agent/fallback.py)",
        "dataset_or_fixture": "11 targeted invariant tests + internal scenario fixtures (e.g. bearing wear vs lubrication degradation; soiling vs string fault)",
        "real_or_synthetic": "SYNTHETIC (software-invariant test fixtures)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "11/11 targeted tests passing; 100% abstention to COMPETING_HYPOTHESES when counterevidence is symmetric",
        "artifact": "tests/test_differential_diagnosis.py ; docs/checkpoints/22-counterevidence-differential-diagnosis.md",
        "what_the_evidence_actually_proves": "The system generates competing hypotheses, actively evaluates counterevidence, and abstains rather than asserting a single false cause, per its own coded rule set and ordering (weather/curtailment/sensor health ruled out before equipment fault).",
        "what_it_does_NOT_prove": "Diagnostic accuracy against real, unmodelled, or multi-fault cascading failures in physical plant operation. No external diagnostic ground truth was used.",
        "final_status": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "capability": "Historical case retrieval",
        "evidence_source": "rai/memory/ trajectory-similarity retrieval over a partitioned real+synthetic case library",
        "dataset_or_fixture": "14 external real cases (rai/memory/real_corpus.py: 12 wind CARE/Kelmarsh + 2 solar PVDAQ) + 14 internal synthetic reference cases (rai/memory/library.py)",
        "real_or_synthetic": "MIXED — strictly partitioned, never merged",
        "external_or_internal": "MIXED — strictly partitioned, never merged",
        "metric_or_result": "On 10 deterministic test queries: P@1=90.0%, R@3=85.0%, MRR=0.950, partition purity=100%, provenance preservation=100%",
        "artifact": "artifacts/retrieval_benchmark_results.json ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md ; docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md",
        "what_the_evidence_actually_proves": "Retrieval correctly surfaces topically-relevant precedent cases for a query asset and preserves source-type partition integrity — no synthetic case can leak into the real-case partition or vice versa.",
        "what_it_does_NOT_prove": "Causal failure diagnosis or ground-truth prediction of the current active fault. The underlying case corpus is real and externally sourced, but the P@1/R@3/MRR retrieval-quality metrics are computed against `relevant_case_ids` authored by the RAI team itself, not an independent or peer-reviewed relevance benchmark — this is a self-graded evaluation of retrieval mechanics, not an externally validated one. The 14 real cases are historical benchmark/open-data evidence, NOT live technician field verification.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "RAG",
        "evidence_source": "SQLite FTS5 + BM25-style ranked keyword retrieval over a curated knowledge corpus (rai/rag/index.py, rai/rag/retrieve.py)",
        "dataset_or_fixture": "19 curated internal documents (manuals, SOPs, incident logs) under knowledge/",
        "real_or_synthetic": "SYNTHETIC (internally authored, clearly-labelled sample documents)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "4/4 deterministic tests passing: capability probe, keyword search relevance (e.g. 'soiling' query), asset/component-filtered search, document list/get integrity (19 documents indexed)",
        "artifact": "tests/test_rag.py",
        "what_the_evidence_actually_proves": "The FTS5 keyword+BM25 retrieval engine correctly returns relevant curated documents for known queries and correctly respects asset/component filters, over a small internally curated corpus.",
        "what_it_does_NOT_prove": "Retrieval quality on unseen or paraphrased real-world technician queries, or validation against an independent relevance benchmark. The corpus is a small internally curated sample (19 documents), not a comprehensive real maintenance-manual library.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Local AI agent",
        "evidence_source": "Needle 2 runtime + deterministic fallback reasoner, evaluated via internal agent evaluation battery (rai/eval/agent_eval.py)",
        "dataset_or_fixture": "10 curated deterministic scenario fixtures, Evaluator Tasks A-G",
        "real_or_synthetic": "SYNTHETIC (internal deterministic fixtures)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "Tasks A-G passed 100%; tool selection = 1.00; abstention accuracy = 1.00; unsupported-claim rate = 0.00%; Needle 2 latency 6451.9 ms",
        "artifact": "artifacts/evaluation/agent_eval/ ; docs/evaluation/LOCAL_AGENT_EVALUATION.md",
        "what_the_evidence_actually_proves": "Tool use, provenance preservation, bounded reasoning, mandatory abstention under symmetric evidence, and workflow behavior are demonstrated on the internal evaluation corpus.",
        "what_it_does_NOT_prove": "Production field performance, multi-turn conversational robustness on unmodelled real technician inputs, or safety under adversarial user prompts. This is NOT production field validation.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Economic consequence analysis",
        "evidence_source": "Techno-economic decision-support engine (rai/economics/decision_support.py, rai/economics/engine.py)",
        "dataset_or_fixture": "Configured commercial cost assumptions (tariffs, labor rates, parts costs); NPV comparison across Act Now / Defer 3d / Defer 14d",
        "real_or_synthetic": "SIMULATED_OUTCOME (analytical model over configured assumptions)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "Deterministic decision classification (INTERVENE/INSPECT/MONITOR/WAIT/ABSTAIN); mathematical invariants verified in test suite; 100% documented assumption provenance; zero fabricated probabilities",
        "artifact": "tests/test_economic_decision_support.py ; docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md ; docs/evaluation/DECISION_MATH_AUDIT.md",
        "what_the_evidence_actually_proves": "Given stated cost assumptions, the engine deterministically and reproducibly computes net financial consequences across intervention options, with explicit source labeling of every assumption and null-handling for missing inputs.",
        "what_it_does_NOT_prove": "Realized financial savings or empirically validated failure-probability distributions. Results are modeled/projected consequences based on assumptions — they must never be labeled as realized savings.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Recommendation engine",
        "evidence_source": "Confidence-gated decision policy with explicit human-abstention threshold (rai/agent/fallback.py, rai/decision/engine.py, rai/decision/policy.py)",
        "dataset_or_fixture": "Deterministic decision-math and decision-intelligence test suites",
        "real_or_synthetic": "SYNTHETIC (software-invariant + simulator scenarios)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "Deterministic mapping of evidence packet + confidence to a bounded action set, verified by tests/test_decision_engine.py, tests/test_decision_intelligence.py, tests/test_decision_math.py",
        "artifact": "tests/test_decision_engine.py ; tests/test_decision_math.py ; docs/evaluation/DECISION_MATH_AUDIT.md",
        "what_the_evidence_actually_proves": "Given a computed evidence packet, the policy deterministically and reproducibly maps evidence and confidence to one of a fixed, auditable set of recommended actions, and always escalates to human review below the confidence threshold rather than guessing.",
        "what_it_does_NOT_prove": "That the recommended action is the objectively correct real-world maintenance decision, or that it improves real operational outcomes relative to an alternative policy. The system never executes autonomous plant control actions — recommendations are proposal-only.",
        "final_status": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "capability": "Work orders",
        "evidence_source": "Work-order lifecycle across FastAPI (services/api/routers/work_orders.py) and the Next.js console (web/src/app/work-orders/)",
        "dataset_or_fixture": "Internal/demo work-order tickets; Playwright browser walkthrough",
        "real_or_synthetic": "SYNTHETIC (internal demo/test tickets)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "End-to-end lifecycle (propose -> reject/approve -> dispatch -> feedback) browser-verified across 8 steps and 17 screenshots; API routes covered by unit/integration tests",
        "artifact": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md",
        "what_the_evidence_actually_proves": "The work-order creation, human approval, and dispatch workflow functions correctly end-to-end in a demo/test environment, and always requires explicit human operator sign-off before dispatch.",
        "what_it_does_NOT_prove": "Operational use by real technicians at a live commercial site. Zero commercial utility deployments currently exist.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Dispatch optimization",
        "evidence_source": "Safe-weather fleet crew dispatch optimizer (rai/decision/dispatch_optimizer.py)",
        "dataset_or_fixture": "Configured safety thresholds (wind climb <=12.0 m/s, gust <=18.0 m/s, solar rain=0mm, ambient temp<45C) applied to cached Open-Meteo forecasts",
        "real_or_synthetic": "MIXED (real cached weather forecasts; configured heuristic thresholds)",
        "external_or_internal": "MIXED",
        "metric_or_result": "Deterministic assignment of approved work orders to valid safety windows; zero safety-lockout violations observed in test scenarios",
        "artifact": "artifacts/weather_cache/ ; docs/checkpoints/24-crew-dispatch-weather-optimizer.md",
        "what_the_evidence_actually_proves": "Crew dispatch scheduling correctly applies configured safety thresholds against real (cached) weather-forecast data to gate or allow physical field work, and correctly prioritizes and slots approved work orders.",
        "what_it_does_NOT_prove": "A certified or legally binding (e.g. OSHA) operational safety guarantee. Thresholds are project-configured operational heuristics, not certified safety standards; forecast accuracy itself is a third-party dependency.",
        "final_status": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "capability": "Weather-aware scheduling",
        "evidence_source": "Meteorological constraint-gating and safety-window classification within the same dispatch optimizer (rai/decision/dispatch_optimizer.py) — the weather-gating facet of dispatch optimization, not a separately built subsystem",
        "dataset_or_fixture": "Live/cached Open-Meteo forecast caches (artifacts/weather_cache/charanka-solar_latest.json, kutch-wind_latest.json)",
        "real_or_synthetic": "MIXED (real forecast data; configured thresholds)",
        "external_or_internal": "MIXED",
        "metric_or_result": "Deterministic window classification (APPROVED / MARGINAL / LOCKED_OUT) computed from live/cached forecast wind speed, gust, rain probability, and temperature",
        "artifact": "artifacts/weather_cache/kutch-wind_latest.json ; artifacts/weather_cache/charanka-solar_latest.json",
        "what_the_evidence_actually_proves": "The scheduler correctly classifies field-work safety windows from real forecast inputs using fixed, auditable, documented thresholds.",
        "what_it_does_NOT_prove": "A certified operational safety guarantee. Third-party forecast accuracy is not guaranteed, and following the schedule does not guarantee prevention of all weather-related field incidents. This is the same underlying engine as 'dispatch optimization' above, not an independent capability with separate evidence.",
        "final_status": "ARCHITECTURALLY_SUPPORTED",
    },
    {
        "capability": "Technician feedback",
        "evidence_source": "Field-feedback ledger and dual-key promotion gate (rai/memory/library.py get_field_feedback_cases; artifacts/tickets.jsonl)",
        "dataset_or_fixture": "306 tickets inspected, 122 feedback entries; all are quarantined test fixtures or demo simulations",
        "real_or_synthetic": "SYNTHETIC (demo/test fixtures)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "0 tickets promoted to EXTERNAL_REAL; 40 reclassified as quarantined test fixtures; 0 active production field deployments",
        "artifact": "artifacts/evaluation/real_case_provenance/provenance_summary.json",
        "what_the_evidence_actually_proves": "The feedback-capture UI/API and the dual-key provenance gate (requires both FeedbackProvenance.EXTERNAL_FIELD_OBSERVED and ObservationLevel.FIELD_VERIFIED) function correctly, and correctly refuse to promote unverified or test tickets into the real-case retrieval memory.",
        "what_it_does_NOT_prove": "That any real technician has used the system in the field. Zero live commercial utility sites are connected; zero genuine external field observations exist in the live ledger.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Closed-loop learning",
        "evidence_source": "Feedback-to-retrieval ingestion pipeline with dual-key promotion gate, verified end-to-end in-browser",
        "dataset_or_fixture": "Playwright browser walkthrough of /work-orders and /assets/WT-004 (8-step lifecycle, 17 screenshots)",
        "real_or_synthetic": "SYNTHETIC (internal/demo data)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "8-step operational loop (Anomaly -> Propose WO -> Approve -> Dispatch -> Feedback -> Case Ingestion -> Promotion Gate -> KPI state) verified end-to-end; dual-key gate enforced programmatically",
        "artifact": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md",
        "what_the_evidence_actually_proves": "The full operator workflow from anomaly to technician feedback to candidate case-ingestion is demonstrated end-to-end in the browser, and the promotion gate correctly prevents demo/test feedback from contaminating the real-case retrieval memory.",
        "what_it_does_NOT_prove": "Production learning from live utility field data. This does NOT establish that the system continuously learns from real operational feedback — zero commercial utility sites are connected.",
        "final_status": "DEMONSTRATED",
    },
    {
        "capability": "Frontend operational workflow",
        "evidence_source": "Next.js operator console (web/) — dashboard, asset deep-dive, evidence accordion, work-orders, dispatch console",
        "dataset_or_fixture": "npm run build, npm run lint, Playwright browser verification screenshots",
        "real_or_synthetic": "SYNTHETIC (internal demo UI over cached/simulated data)",
        "external_or_internal": "INTERNAL",
        "metric_or_result": "Production build succeeds with zero type errors; lint clean; full operator workflow browser-verified; EvidenceAccordion correctly distinguishes confirmed-failure vs non-fault historical event classes after the provenance-reconciliation fix",
        "artifact": "web/ ; docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md",
        "what_the_evidence_actually_proves": "The operator-facing UI renders the evidence-backed decision workflow correctly end-to-end, builds and lints cleanly, and correctly represents case provenance and event class in its styling.",
        "what_it_does_NOT_prove": "Usability or effectiveness judged by a real plant operator. No user study, A/B test, or field usability evaluation has been performed.",
        "final_status": "DEMONSTRATED",
    },
]

assert len(CAPABILITY_REGISTRY) == 18, "Capability registry must cover all 18 named capabilities in the audit scope"

_VALID_STATUSES = {"VALIDATED", "DEMONSTRATED", "ARCHITECTURALLY_SUPPORTED", "NOT_VALIDATED"}
for _row in CAPABILITY_REGISTRY:
    assert _row["final_status"] in _VALID_STATUSES, f"Invalid final_status for {_row['capability']}"

# ----------------------------------------------------------------------
# 2. Claim-to-Evidence Matrix
#
# One row per major public-facing claim, mapped to the capability/evidence that supports it.
# ----------------------------------------------------------------------

CLAIM_TO_EVIDENCE = [
    {
        "claim_id": "CLAIM-CARE-DETECT",
        "claim_statement": "RAI detects abnormal wind turbine behavior using physics-conditioned residual models, benchmarked on real SCADA with documented failure events.",
        "capability": "CARE wind anomaly detection",
        "exact_artifact": "artifacts/evaluation/external_care/",
        "capability_level": "VALIDATED",
        "limitation": "Evaluated on 3 CARE farms / 36 turbines; does not guarantee zero-shot performance on uncalibrated fleets.",
    },
    {
        "claim_id": "CLAIM-CARE-TRANSFER",
        "claim_statement": "Detection performance transfers across wind farms when calibrated on unlabelled target-farm SCADA.",
        "capability": "CARE cross-farm transfer",
        "exact_artifact": "artifacts/evaluation/gate54/",
        "capability_level": "VALIDATED",
        "limitation": "Requires unlabelled normal-operating telemetry from the target farm; raw zero-shot transfer is not validated.",
    },
    {
        "claim_id": "CLAIM-KELMARSH",
        "claim_statement": "RAI's anomaly scoring is consistent with independently logged wind-farm operational events (Kelmarsh benchmark).",
        "capability": "Kelmarsh benchmark",
        "exact_artifact": "artifacts/evaluation/kelmarsh_event_behaviour/",
        "capability_level": "VALIDATED",
        "limitation": "Must NOT be described as failure prediction or hardware-failure validation; no component-failure ground truth exists in the public Kelmarsh record.",
    },
    {
        "claim_id": "CLAIM-ENV-DISCRIM",
        "claim_statement": "An environmental explanation is ruled out (weather, curtailment, soiling) before an equipment fault is asserted.",
        "capability": "Environmental context / discrimination",
        "exact_artifact": "tests/test_environment_solar.py",
        "capability_level": "DEMONSTRATED",
        "limitation": "Ground truth for fault/no-fault windows is internal-simulator-based, not independently observed field data.",
    },
    {
        "claim_id": "CLAIM-SOLAR-FOUNDATION",
        "claim_statement": "Real public solar telemetry was acquired and audited as a modeling-ready data foundation.",
        "capability": "Solar PVDAQ data foundation",
        "exact_artifact": "artifacts/evaluation/gate56/cohort_adjudication/",
        "capability_level": "VALIDATED",
        "limitation": "Data-acquisition and audit only; the adjudicated Validation cohort is empty (INSUFFICIENT_DATA).",
    },
    {
        "claim_id": "CLAIM-SOLAR-PHYSICS",
        "claim_statement": "RAI's solar expected-performance model is validated.",
        "capability": "Solar physics layer",
        "exact_artifact": "artifacts/evaluation/gate56/gate56c_model_development/",
        "capability_level": "NOT_VALIDATED",
        "limitation": "NOT INDEPENDENTLY VALIDATED. Fit and tested only on within-system temporal holdouts of the Development cohort; Validation cohort is empty.",
    },
    {
        "claim_id": "CLAIM-DIAGNOSIS",
        "claim_statement": "RAI performs differential diagnosis, ruling out competing hypotheses before concluding an equipment fault.",
        "capability": "Diagnosis",
        "exact_artifact": "tests/test_differential_diagnosis.py",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
        "limitation": "Rule-based logic verified by invariant tests only; not validated against real unmodelled or multi-fault failures.",
    },
    {
        "claim_id": "CLAIM-CASE-RETRIEVAL",
        "claim_statement": "RAI retrieves relevant historical precedent cases, including real documented failures, to support a maintenance decision.",
        "capability": "Historical case retrieval",
        "exact_artifact": "artifacts/retrieval_benchmark_results.json",
        "capability_level": "DEMONSTRATED",
        "limitation": "14 external cases are historical benchmark/open-data evidence, NOT live technician field verification. Retrieval-quality metrics (P@1/R@3/MRR) are computed against self-authored relevance judgments, not an independent benchmark.",
    },
    {
        "claim_id": "CLAIM-RAG",
        "claim_statement": "RAI cites relevant maintenance manuals, SOPs, and incident documents to support its explanations.",
        "capability": "RAG",
        "exact_artifact": "tests/test_rag.py",
        "capability_level": "DEMONSTRATED",
        "limitation": "Corpus is 19 internally curated sample documents, not a comprehensive real maintenance-manual library; no independent relevance benchmark.",
    },
    {
        "claim_id": "CLAIM-LOCAL-AGENT",
        "claim_statement": "RAI's local AI agent reasons over evidence with bounded, auditable tool use and abstains when evidence is insufficient.",
        "capability": "Local AI agent",
        "exact_artifact": "artifacts/evaluation/agent_eval/",
        "capability_level": "DEMONSTRATED",
        "limitation": "Evaluated on 10 internal deterministic fixtures; NOT production field validation.",
    },
    {
        "claim_id": "CLAIM-ECONOMICS",
        "claim_statement": "RAI quantifies the economic consequence of a detected fault to support the intervention decision.",
        "capability": "Economic consequence analysis",
        "exact_artifact": "tests/test_economic_decision_support.py",
        "capability_level": "DEMONSTRATED",
        "limitation": "Outputs are modeled/projected consequences under stated assumptions. Never realized savings.",
    },
    {
        "claim_id": "CLAIM-RECOMMEND",
        "claim_statement": "RAI recommends a bounded maintenance action based on evidence and confidence, deferring to a human below a confidence threshold.",
        "capability": "Recommendation engine",
        "exact_artifact": "tests/test_decision_engine.py",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
        "limitation": "Deterministic rule engine verified by tests only; does not prove real-world decision-quality improvement. Proposal-only — never executes autonomous control actions.",
    },
    {
        "claim_id": "CLAIM-WORKORDERS",
        "claim_statement": "RAI supports the full work-order lifecycle from proposal through technician dispatch.",
        "capability": "Work orders",
        "exact_artifact": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md",
        "capability_level": "DEMONSTRATED",
        "limitation": "Demonstrated in a demo/test environment; zero live commercial deployments.",
    },
    {
        "claim_id": "CLAIM-DISPATCH",
        "claim_statement": "RAI schedules crew dispatch within safe weather windows.",
        "capability": "Dispatch optimization",
        "exact_artifact": "artifacts/weather_cache/",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
        "limitation": "Configured heuristic thresholds, not a certified operational safety guarantee.",
    },
    {
        "claim_id": "CLAIM-WEATHER-SCHED",
        "claim_statement": "RAI's scheduling is weather-aware, using live/cached forecasts to gate physical field work.",
        "capability": "Weather-aware scheduling",
        "exact_artifact": "artifacts/weather_cache/kutch-wind_latest.json",
        "capability_level": "ARCHITECTURALLY_SUPPORTED",
        "limitation": "Same underlying engine as dispatch optimization; forecast accuracy is a third-party dependency.",
    },
    {
        "claim_id": "CLAIM-TECH-FEEDBACK",
        "claim_statement": "RAI captures technician field feedback and gates it before it can influence future retrieval.",
        "capability": "Technician feedback",
        "exact_artifact": "artifacts/evaluation/real_case_provenance/provenance_summary.json",
        "capability_level": "DEMONSTRATED",
        "limitation": "All current tickets are quarantined test fixtures or demo simulations; zero live commercial technicians are active.",
    },
    {
        "claim_id": "CLAIM-CLOSED-LOOP",
        "claim_statement": "RAI closes the loop from anomaly to technician feedback to candidate case ingestion.",
        "capability": "Closed-loop learning",
        "exact_artifact": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md",
        "capability_level": "DEMONSTRATED",
        "limitation": "Browser-workflow demonstrated end-to-end; does NOT establish production learning from live utility field data.",
    },
    {
        "claim_id": "CLAIM-FRONTEND",
        "claim_statement": "RAI's operator console presents the evidence-backed decision workflow end-to-end.",
        "capability": "Frontend operational workflow",
        "exact_artifact": "web/",
        "capability_level": "DEMONSTRATED",
        "limitation": "No real-operator usability study has been performed.",
    },
]

assert len(CLAIM_TO_EVIDENCE) == 18

# ----------------------------------------------------------------------
# 3. Unsupported Claims / Downgrade Ledger
#
# Seeded with discrepancies already identified and remedied in prior audits
# (docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md) plus this freeze's own claims-wording
# audit. Additional rows from the claims-audit workflow are appended by
# scripts/apply_evidence_freeze_claim_downgrades.py after adversarial verification.
# ----------------------------------------------------------------------

UNSUPPORTED_CLAIMS = [
    {
        "unsupported_claim_id": "UNSUP-01",
        "original_wording": "16 real adjudicated cases (10 wind + 6 solar from PVPMC)",
        "source_location": "docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md (historical), CHECKPOINT.md (historical)",
        "evidence_gap_reason": "Corpus contains 14 external real cases (12 wind + 2 solar). The 6 solar cases are internal synthetic scenarios in library.py, not from Sandia PVPMC.",
        "remedy_or_downgrade": "Corrected to 14 external real cases (12 wind, 2 solar) + 14 internal synthetic reference cases. False attribution to Sandia PVPMC removed. Already remedied in acd214f.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-02",
        "original_wording": "Kelmarsh provides an independent component-failure benchmark for RAI",
        "source_location": "docs/CLAIMS.md (historical)",
        "evidence_gap_reason": "Public Kelmarsh dataset inventory confirms component-failure ground-truth labels are unavailable; logs reflect operational status and trips only.",
        "remedy_or_downgrade": "Re-scoped strictly to operational event-window association; explicitly declared NOT a failure-prediction validation.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-03",
        "original_wording": "Solar expected-performance model is independently validated (Gate 5.6C)",
        "source_location": "docs/CLAIMS.md (historical)",
        "evidence_gap_reason": "Gate 5.6B's Validation cohort is empty (INSUFFICIENT_DATA). Gate 5.6C was tested on within-system temporal holdouts only.",
        "remedy_or_downgrade": "Declared NOT_VALIDATED for independent validation; labeled MODEL_DEVELOPMENT throughout.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-04",
        "original_wording": "Historical case retrieval is independently validated (P@1/R@3 treated as an external benchmark result)",
        "source_location": "This evidence freeze's own capability classification pass",
        "evidence_gap_reason": "Retrieval precision/recall metrics are computed against `relevant_case_ids` authored by the RAI team itself, not an independent or peer-reviewed relevance benchmark. The underlying 14-case corpus is real, but the retrieval-quality evaluation is self-graded.",
        "remedy_or_downgrade": "Historical case retrieval capability status downgraded from VALIDATED to DEMONSTRATED in evidence_registry.csv/json; self-grading limitation stated explicitly in claim_to_evidence.csv.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-05",
        "original_wording": "Continuous learning from live utility operational feedback",
        "source_location": "Closed-loop narrative (historical drafts)",
        "evidence_gap_reason": "Zero live commercial sites are currently connected; all feedback tickets in tickets.jsonl are test fixtures or demo simulations.",
        "remedy_or_downgrade": "Re-scoped to 'demonstrated operational lifecycle on internal synthetic fixtures'; dual-key promotion gate enforces quarantine of test tickets.",
        "status": "REMEDIED",
    },
    {
        "unsupported_claim_id": "UNSUP-06",
        "original_wording": "Certified meteorological safety guarantee for crew dispatch",
        "source_location": "Dispatch narrative (historical drafts)",
        "evidence_gap_reason": "Safety-window optimization is a heuristic decision-support engine using configured thresholds and third-party weather forecasts, not a certified safety system.",
        "remedy_or_downgrade": "Re-labeled as configured operational constraints (site dispatch heuristics); explicitly disclaimed as an OSHA or certified legal safety guarantee.",
        "status": "REMEDIED",
    },
]

# ----------------------------------------------------------------------
# 4. Final Capability Matrix (judge-readable, exactly 7 columns per spec)
# ----------------------------------------------------------------------

FINAL_MATRIX_COLUMNS = [
    "Capability", "Evidence", "Status", "Real/Synthetic", "External/Internal", "Validated?", "Primary limitation",
]


def _validated_flag(status: str) -> str:
    return "Yes" if status == "VALIDATED" else "No"


def build_final_matrix_rows():
    rows = []
    for item in CAPABILITY_REGISTRY:
        rows.append({
            "Capability": item["capability"],
            "Evidence": item["evidence_source"],
            "Status": item["final_status"],
            "Real/Synthetic": item["real_or_synthetic"],
            "External/Internal": item["external_or_internal"],
            "Validated?": _validated_flag(item["final_status"]),
            "Primary limitation": item["what_it_does_NOT_prove"],
        })
    return rows


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_evidence_matrix_md() -> str:
    lines = [
        "# SCIENTIFIC EVIDENCE MATRIX — DETAILED CAPABILITY-TO-EVIDENCE MAPPING",
        "",
        f"**Freeze Date:** {FREEZE_DATE}  ",
        f"**Audit Base Commit:** `{AUDIT_COMMIT}`",
        "",
        "This matrix provides the complete audit specification for every one of the 18 named",
        "capabilities in the Evidence Freeze scope. Every row traces to an existing artifact or",
        "report already present in this repository; no number here was computed for this",
        "document — each is copied from the cited artifact.",
        "",
        "| Capability | Real/Synthetic | External/Internal | Final Status | Exact Artifact |",
        "|---|---|---|---|---|",
    ]

    for item in CAPABILITY_REGISTRY:
        lines.append(
            f"| **{item['capability']}** | {item['real_or_synthetic']} | {item['external_or_internal']} | `{item['final_status']}` | {item['artifact']} |"
        )

    lines.extend(["", "---", "", "## Detailed Capability Profiles", ""])

    for item in CAPABILITY_REGISTRY:
        lines.extend([
            f"### {item['capability']}",
            f"- **Final Status:** `{item['final_status']}`",
            f"- **Evidence Source:** {item['evidence_source']}",
            f"- **Dataset / Fixture:** {item['dataset_or_fixture']}",
            f"- **Real vs Synthetic:** {item['real_or_synthetic']}",
            f"- **External vs Internal:** {item['external_or_internal']}",
            f"- **Metric / Result:** {item['metric_or_result']}",
            f"- **Artifact:** {item['artifact']}",
            f"- **What the evidence actually proves:** {item['what_the_evidence_actually_proves']}",
            f"- **What it does NOT prove:** *{item['what_it_does_NOT_prove']}*",
            "",
        ])

    return "\n".join(lines)


def generate_freeze_summary_md() -> str:
    counts = {}
    for item in CAPABILITY_REGISTRY:
        counts[item["final_status"]] = counts.get(item["final_status"], 0) + 1

    lines = [
        "# SCIENTIFIC EVIDENCE FREEZE — RENEWABLE ASSET INTELLIGENCE (RAI)",
        "",
        "> **Official Evidence Freeze State.** All empirical claims, benchmark figures, demonstration",
        "> capabilities, and architectural features across Renewable Asset Intelligence are formally",
        "> audited, categorized, and frozen. Evidence determines the claim — never the reverse.",
        "",
        f"**Freeze Date:** {FREEZE_DATE}  ",
        f"**Audit Base Commit:** `{AUDIT_COMMIT}`  ",
        "**Governing Principles:**",
        "1. Never fabricate, infer, or upgrade provenance.",
        "2. Do not reinterpret synthetic/demo/test fixtures as real.",
        "3. Preserve all existing safety and provenance boundaries.",
        "4. Every claim must trace directly to an audited, existing artifact.",
        "",
        "---",
        "",
        "## 1. The Four-Level Capability Taxonomy",
        "",
        "| Level | Formal Definition |",
        "|---|---|",
        "| **VALIDATED** | Measured against an appropriate external dataset or peer-reviewed public benchmark. |",
        "| **DEMONSTRATED** | Fully implemented and functioning end-to-end, but demonstrated on controlled, synthetic, self-graded, or internal fixtures rather than an independent external benchmark. |",
        "| **ARCHITECTURALLY_SUPPORTED** | Implemented and technically bounded in software, but not validated against real-world physical outcomes at all — only against its own invariants. |",
        "| **NOT_VALIDATED** | Explicitly not supported by current evidence; must NEVER be claimed as an accomplished capability. |",
        "",
        f"## 2. Capability Counts ({len(CAPABILITY_REGISTRY)} capabilities audited)",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| VALIDATED | {counts.get('VALIDATED', 0)} |",
        f"| DEMONSTRATED | {counts.get('DEMONSTRATED', 0)} |",
        f"| ARCHITECTURALLY_SUPPORTED | {counts.get('ARCHITECTURALLY_SUPPORTED', 0)} |",
        f"| NOT_VALIDATED | {counts.get('NOT_VALIDATED', 0)} |",
        "",
        "---",
        "",
        "## 3. Final Capability Matrix (judge-readable)",
        "",
        "| " + " | ".join(FINAL_MATRIX_COLUMNS) + " |",
        "|" + "---|" * len(FINAL_MATRIX_COLUMNS),
    ]

    for row in build_final_matrix_rows():
        lines.append("| " + " | ".join(str(row[c]) for c in FINAL_MATRIX_COLUMNS) + " |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Critical Evidence Boundaries & Negative Declarations",
        "",
        "- **CARE:** Benchmark evidence for wind anomaly-detection behavior.",
        "- **Kelmarsh:** Evidence about documented operational/maintenance event association. NOT hardware-failure prediction validation.",
        "- **PVDAQ:** Real data acquisition and modeling-readiness evidence. Gate 5.6B has no validation cohort. Therefore Gate 5.6C is NOT independently validated.",
        "- **Local AI:** Tool use, provenance, bounded reasoning, abstention and workflow behavior demonstrated on the internal evaluation corpus. NOT production field validation.",
        "- **Historical retrieval:** 14 external public-source cases exist. They are historical benchmark/open-data evidence. They are NOT live technician field verification. Retrieval-quality metrics are self-graded, not independently benchmarked.",
        "- **Closed loop:** The browser workflow is end-to-end demonstrated. This does NOT establish production learning from utility field data.",
        "- **Economics:** Results are modeled/projected consequences based on assumptions. Never label projected avoidable exposure as realized savings.",
        "- **Dispatch / weather-aware scheduling:** Decision support under configured constraints. Never a certified operational safety guarantee.",
        "",
        "---",
        "",
        "## 5. Frozen Artifacts",
        "",
        "The following artifacts in `artifacts/evaluation/evidence_freeze/` form the definitive audit trail:",
        f"- `evidence_registry.csv` / `evidence_registry.json`: {len(CAPABILITY_REGISTRY)}-capability registry, one row per capability, exact 10-field schema.",
        "- `evidence_matrix.md`: Detailed per-capability methodology, scope, and evidence-boundary profile.",
        f"- `claim_to_evidence.csv`: {len(CLAIM_TO_EVIDENCE)} public claims mapped to their exact supporting capability/artifact.",
        f"- `unsupported_claims.csv`: {len(UNSUPPORTED_CLAIMS)} identified overstatements and their verified remedies.",
        "- `freeze_summary.md`: This executive governance document.",
    ])

    return "\n".join(lines)


def main():
    print("Generating Scientific Evidence Freeze artifacts...")

    write_csv(OUT_DIR / "evidence_registry.csv", CAPABILITY_REGISTRY)
    with open(OUT_DIR / "evidence_registry.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "freeze_date": FREEZE_DATE,
                "audit_base_commit": AUDIT_COMMIT,
                "total_capabilities_audited": len(CAPABILITY_REGISTRY),
                "capabilities": CAPABILITY_REGISTRY,
                "final_matrix": build_final_matrix_rows(),
            },
            f,
            indent=2,
        )

    write_csv(OUT_DIR / "claim_to_evidence.csv", CLAIM_TO_EVIDENCE)
    write_csv(OUT_DIR / "unsupported_claims.csv", UNSUPPORTED_CLAIMS)

    with open(OUT_DIR / "evidence_matrix.md", "w", encoding="utf-8") as f:
        f.write(generate_evidence_matrix_md())

    with open(OUT_DIR / "freeze_summary.md", "w", encoding="utf-8") as f:
        f.write(generate_freeze_summary_md())

    print(f"Successfully generated all evidence freeze artifacts in {OUT_DIR}")


if __name__ == "__main__":
    main()
