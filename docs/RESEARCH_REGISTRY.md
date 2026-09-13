# Research Registry

This registry records research decisions that change what RAI may claim or implement.
It is intentionally concise: a source is useful only when it changes an engineering
decision.

## RAI-WIND-001 — Kelmarsh independent benchmark route

| Field | Record |
|---|---|
| Question | Does the public Kelmarsh dataset provide event semantics and ground truth strong enough for an independent component-failure benchmark? |
| Hypothesis | Kelmarsh may provide real operational event logs, but its labels may not be manually adjudicated component failures. |
| Sources | Official Zenodo record `10.5281/zenodo.5841834`; OpenWindSCADA dataset inventory, `sltzgs/OpenWindSCADA` README; focused source review on 2026-09-13. |
| Findings | Kelmarsh contains six Senvion MM92 turbines, 10-minute SCADA, and events data extracted from Greenbyte. The OpenWindSCADA inventory marks Kelmarsh `Logs=Yes` and `Labels=No`; its footnotes distinguish manual failure/component-replacement annotations from logs. |
| Reliability | High for dataset contents and the public label/log distinction; insufficient to infer that every event is a confirmed component failure. |
| Decision | **PATH B / PARTIAL:** use Kelmarsh only for an event-log and operating-behaviour benchmark after inspecting event-code semantics. Do not call event rows validated component-failure ground truth, do not reuse event codes as failure labels without adjudication, and do not report independent fault-detection accuracy yet. |
| Next experiment | Acquire a version-pinned release, inventory event-code descriptions, classify events into fault / scheduled maintenance / requested shutdown / environmental / sensor / unknown, and publish the mapping before fitting a detector. |
| Status | `PARTIAL` |

## RAI-WIND-002 — Kelmarsh event / behaviour association

| Field | Record |
|---|---|
| Question | Does RAI's expected-behaviour plus persistence methodology show abnormal operating behaviour around real Kelmarsh operational events without relabelling them as failures? |
| Protocol | Pinned 2019 release; six turbines; chronological 60/40 split; three common signals; statistical z-score, Isolation Forest, and RAI Champion; six-hour pre/event/post windows. |
| Result | 92 test-period operational windows (71 forced outage, 21 scheduled maintenance). Event-window coverage: statistical z-score 1.1%, Isolation Forest 47.8%, RAI Champion 81.5%. Outside-window flag rates: 0.46%, 0.32%, and 1.11%, respectively. |
| Reliability | Moderate for the bounded association question; low for any fault claim because status rows are operational records and event causes are not independently adjudicated. |
| Decision | **PARTIAL:** RAI's scores associate more often with these documented operational windows in this release, but the result is not failure validation, prediction, causation, or production validation. |
| Artifacts | `docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md`; `artifacts/evaluation/kelmarsh_event_behaviour/`. |
| Status | `PARTIAL` |

### Claim boundary

Supported: “Kelmarsh provides real operational SCADA and event records under
CC-BY-4.0.” Unsupported: “RAI is validated on Kelmarsh component-failure ground
truth.” The latter remains blocked until event semantics are independently adjudicated.

## RAI-RAG-001 — Provenance-safe historical case retrieval

| Field | Record |
|---|---|
| Question | What retrieval architecture best supports a small, auditable maintenance-case corpus without treating matches as diagnoses? |
| Sources | SQLite FTS5 documentation (official); bounded review of hybrid retrieval and case-based time-series retrieval patterns on 2026-09-14. |
| Findings | Metadata filtering should constrain candidates before ranking; FTS5 provides deterministic lexical ranking and the existing memory layer provides weighted trajectory similarity. Their scores are not probabilities and must not be silently fused as calibrated confidence. |
| Decision | **IMPLEMENTED:** retain SQLite FTS5 for reviewed maintenance documents and use the existing weighted trajectory retrieval for structured cases, with explicit provenance, evidence states, match/difference explanations, and abstention on missing case IDs. No new embedding dependency is justified by the current small corpus. |
| Corpus | Existing authored incident cases only; labelled `INTERNAL_SYNTHETIC`. No raw SCADA rows and no unadjudicated events are indexed as cases. |
| Limitations | Retrieval evaluation is deterministic and small; no claim of real maintenance-history coverage or diagnosis prediction is supported. |
| Status | `IMPLEMENTED` |

## RAI-ECON-001 — Explicit-assumption economic decision support

| Field | Record |
|---|---|
| Question | How should RAI turn technical evidence into intervention priority without fabricating money or probabilities? |
| Sources | NIST PHM standards and smart-manufacturing performance guidance; focused predictive-maintenance decision-analysis review; existing RAI decision-math audit. |
| Alternatives | Explicit expected-consequence counterfactuals; full EVPI/EVSI/VOI policy; learned cost-sensitive policy. |
| Decision | **IMPLEMENTED / BOUNDED:** retain the existing Python cost engine and add a provenance-labelled adapter returning `INTERVENE`, `INSPECT`, `MONITOR`, `WAIT`, or `ABSTAIN`. Do not apply VOI operationally until inspection test characteristics are established. |
| Inputs | Model risk is `INFERRED`; environmental context is `OBSERVED`; tariff/downtime/component costs are `ASSUMED`; missing values remain `UNKNOWN`. |
| Limitation | No real intervention outcomes, validated inspection sensitivity/specificity, or empirical maintenance-cost distribution is available. No claims of savings, ROI, cost optimization, or failure probability are supported. |
| Artifacts | `rai/economics/decision_support.py`; `docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md`; `tests/test_economic_decision_support.py`. |
| Status | `IMPLEMENTED` |

## RAI-AGENT-001 — Local evidence and tool-boundary evaluation

| Field | Record |
|---|---|
| Question | Does the local agent preserve computed evidence, provenance, abstention, economics, and proposal-only safety at its tool boundary without requiring Needle weights? |
| Protocol | Deterministic fixture battery using the real fallback reasoner, real trajectory retrieval, real SQLite FTS5/economics seams where applicable, injected provider/runtime failures, malformed proposal arguments, and an injectable fake Needle runtime. |
| Result | 24 targeted tests passed. Evaluator tasks A-G passed. Tool selection, argument correctness, provenance, abstention, recommendation validity, and tool-failure handling were each 1.00; unsupported-claim rate was 0.00. Needle runtime response success was 1.00, mean latency was 6451.9 ms, and concurrent safety passed in the measured run. |
| Reliability | High for these local contract and safety invariants; low for model quality, real-world diagnosis, calibration, and generalization because the battery is small and `INTERNAL_SYNTHETIC`. |
| Decision | **IMPLEMENTED / BOUNDED:** retain the deterministic fallback as the testable safety baseline; Needle remains optional and its runtime metrics are not diagnostic-quality claims. No Qwen gateway is justified by this evaluation. |
| Limitations | Tool-selection accuracy here measures deterministic intent-to-tool contracts, not unconstrained Needle selection. No Needle latency or availability claim is made. |
| Artifacts | `tests/test_local_agent_evaluation.py`; `docs/evaluation/LOCAL_AGENT_EVALUATION.md`. |
| Status | `IMPLEMENTED` |

## RAI-RAG-002 — Real historical-case corpus & retrieval validation

| Field | Record |
|---|---|
| Question | Can RAI's existing trajectory and metadata retrieval architecture accurately retrieve relevant real operational and failure events with full provenance preservation and abstention, without confusing operational shutdowns with component failures? |
| Hypothesis | Real historical cases from CARE to Compare, Kelmarsh SCADA/logs, and NREL PVDAQ can be partitioned, adjudicated, and retrieved with structured provenance and why/what-differed explanations without data leakage or conflating operational trips with component failures. |
| Sources | CARE to Compare (Zenodo records 10958775 & 14006163); Kelmarsh Wind Farm (Zenodo record 5841834); NREL PVDAQ OEDI (Systems 34 & 1283). |
| Adjudication | 14 curated real cases across 4 explicit event classes (`REAL_VERIFIED_EVENT`, `REAL_OPERATIONAL_EVENT`, `REAL_MAINTENANCE_EVENT`, `ENVIRONMENTAL_EVENT`). Operational trips (converter trips, fan overloads, midday inverter trips) explicitly typed as operational events with `equipment_fault=False`. |
| Findings | Strict partition separation (`EXTERNAL_REAL` vs `INTERNAL_SYNTHETIC`) prevents synthetic regression failures. Explanations returning `why_matched`, `what_is_similar`, `what_is_different`, and `why_may_not_apply` provide transparent operator reasoning without probability fabrication. |
| Results | 10 deterministic test queries: Mean Precision@1 = 90.0%, Mean Precision@3 = 80.0%, Mean Recall@3 = 85.0%, MRR = 0.950, Provenance Preservation Rate = 100.0%, Partition Purity Rate = 100.0%, Abstention Accuracy = 100.0%. |
| Reliability | High for deterministic ranking, partition purity, and abstention across the adjudicated 14-case corpus; low for statistical generalization or real-world fault diagnosis. |
| Decision | **IMPLEMENTED**: Strictly partitioned case library with explicit `partition="synthetic"|"real"|"all"` parameter (defaulting to `"synthetic"` for backwards compatibility). REST API (`GET /api/assets/{id}/cases?partition=real`) and agent tool `search_similar_cases` expose real cases with provenance. |
| Limitations | Small adjudicated corpus (14 cases); similarity scores are geometric/lexical distances, not empirical failure probabilities; retrieval does not imply causal diagnosis. |
| Artifacts | `rai/memory/real_corpus.py`; `rai/eval/retrieval_eval.py`; `artifacts/retrieval_benchmark_results.json`; `docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md`; `tests/test_real_case_retrieval.py`; `tests/test_real_historical_retrieval.py`. |
| Status | `IMPLEMENTED` |

