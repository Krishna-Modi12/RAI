# SCIENTIFIC EVIDENCE FREEZE — RENEWABLE ASSET INTELLIGENCE (RAI)

> **Official Evidence Freeze State.** All empirical claims, benchmark figures, demonstration
> capabilities, and architectural features across Renewable Asset Intelligence are formally
> audited, categorized, and frozen. Evidence determines the claim — never the reverse.

**Freeze Date:** 2026-09-13  
**Audit Base Commit:** `acd214f`  
**Governing Principles:**
1. Never fabricate, infer, or upgrade provenance.
2. Do not reinterpret synthetic/demo/test fixtures as real.
3. Preserve all existing safety and provenance boundaries.
4. Every claim must trace directly to an audited, existing artifact.

---

## 1. The Four-Level Capability Taxonomy

| Level | Formal Definition |
|---|---|
| **VALIDATED** | Measured against an appropriate external dataset or peer-reviewed public benchmark. |
| **DEMONSTRATED** | Fully implemented and functioning end-to-end, but demonstrated on controlled, synthetic, self-graded, or internal fixtures rather than an independent external benchmark. |
| **ARCHITECTURALLY_SUPPORTED** | Implemented and technically bounded in software, but not validated against real-world physical outcomes at all — only against its own invariants. |
| **NOT_VALIDATED** | Explicitly not supported by current evidence; must NEVER be claimed as an accomplished capability. |

## 2. Capability Counts (18 capabilities audited)

| Status | Count |
|---|---|
| VALIDATED | 4 |
| DEMONSTRATED | 9 |
| ARCHITECTURALLY_SUPPORTED | 4 |
| NOT_VALIDATED | 1 |

---

## 3. Final Capability Matrix (judge-readable)

| Capability | Evidence | Status | Real/Synthetic | External/Internal | Validated? | Primary limitation |
|---|---|---|---|---|---|---|
| CARE wind anomaly detection | CARE to Compare benchmark (Fraunhofer IEE), Zenodo 10.5281/zenodo.10958775 — 3 wind farms (A/B/C), 36 turbines, author-labeled failure events | VALIDATED | REAL | EXTERNAL | Yes | Universal zero-shot generalization to uncalibrated fleets or novel turbine models; causal root-cause diagnosis of the detected anomaly. |
| CARE cross-farm transfer | CARE benchmark, 6 directed transfers under frozen CARE_COMMON protocol (Gate 5.4) | VALIDATED | REAL | EXTERNAL | Yes | Raw, uncalibrated zero-shot transfer works without any target-farm telemetry; performance on farms/turbine types outside the CARE benchmark. |
| Kelmarsh benchmark | Kelmarsh Wind Farm open dataset (Plumley), Zenodo 10.5281/zenodo.5841834 — 6 Senvion MM92 turbines, UK | VALIDATED | REAL | EXTERNAL | Yes | Failure prediction or hardware/component-failure detection. Kelmarsh's public record contains zero verified mechanical-failure ground truth; it documents operational status and trips only. |
| Environmental context / discrimination | pvlib clear-sky/POA physics baseline + CAMS/Open-Meteo dust & precipitation forecasts + peer-turbine gating (rai/models/environment_solar.py, rai/models/weather_provider.py) | DEMONSTRATED | MIXED (real external weather data; internal synthetic telemetry for fault/no-fault ground truth) | MIXED (external weather API + internal test scenarios) | No | Real-world misdiagnosis rate on live plant instrumentation; evaluation ground truth is internal-simulator-based, not independently observed field weather/fault co-occurrence. |
| Solar PVDAQ data foundation | NREL PVDAQ Open Energy Data Initiative (OEDI S3) — Systems 34, 1283, 1239, 1430, 1433 | VALIDATED | REAL | EXTERNAL | Yes | Any solar performance or fault model. This gate validates data acquisition only; the validation cohort produced by adjudication is empty, so no model has been independently evaluated on held-out systems. |
| Solar physics layer | pvlib ModelChain physics reference vs polynomial empirical baseline vs hybrid champion model (Gate 5.6C) | NOT_VALIDATED | REAL telemetry; NOT_INDEPENDENTLY_VALIDATED methodology | EXTERNAL data source; INTERNAL model development | No | Independent or cross-system validation. Gate 5.6B's Validation cohort is empty (INSUFFICIENT_DATA); therefore Gate 5.6C cannot be, and is not, independently validated. Zero cross-system generalization has been demonstrated. |
| Diagnosis | Counterevidence & differential diagnosis engine (rai/models/differential_diagnosis.py) + deterministic evidence reasoner (rai/agent/fallback.py) | ARCHITECTURALLY_SUPPORTED | SYNTHETIC (software-invariant test fixtures) | INTERNAL | No | Diagnostic accuracy against real, unmodelled, or multi-fault cascading failures in physical plant operation. No external diagnostic ground truth was used. |
| Historical case retrieval | rai/memory/ trajectory-similarity retrieval over a partitioned real+synthetic case library | DEMONSTRATED | MIXED — strictly partitioned, never merged | MIXED — strictly partitioned, never merged | No | Causal failure diagnosis or ground-truth prediction of the current active fault. The underlying case corpus is real and externally sourced, but the P@1/R@3/MRR retrieval-quality metrics are computed against `relevant_case_ids` authored by the RAI team itself, not an independent or peer-reviewed relevance benchmark — this is a self-graded evaluation of retrieval mechanics, not an externally validated one. The 14 real cases are historical benchmark/open-data evidence, NOT live technician field verification. |
| RAG | SQLite FTS5 + BM25-style ranked keyword retrieval over a curated knowledge corpus (rai/rag/index.py, rai/rag/retrieve.py) | DEMONSTRATED | SYNTHETIC (internally authored, clearly-labelled sample documents) | INTERNAL | No | Retrieval quality on unseen or paraphrased real-world technician queries, or validation against an independent relevance benchmark. The corpus is a small internally curated sample (19 documents), not a comprehensive real maintenance-manual library. |
| Local AI agent | Needle 2 runtime + deterministic fallback reasoner, evaluated via internal agent evaluation battery (rai/eval/agent_eval.py) | DEMONSTRATED | SYNTHETIC (internal deterministic fixtures) | INTERNAL | No | Production field performance, multi-turn conversational robustness on unmodelled real technician inputs, or safety under adversarial user prompts. This is NOT production field validation. |
| Economic consequence analysis | Techno-economic decision-support engine (rai/economics/decision_support.py, rai/economics/engine.py) | DEMONSTRATED | SIMULATED_OUTCOME (analytical model over configured assumptions) | INTERNAL | No | Realized financial savings or empirically validated failure-probability distributions. Results are modeled/projected consequences based on assumptions — they must never be labeled as realized savings. |
| Recommendation engine | Confidence-gated decision policy with explicit human-abstention threshold (rai/agent/fallback.py, rai/decision/engine.py, rai/decision/policy.py) | ARCHITECTURALLY_SUPPORTED | SYNTHETIC (software-invariant + simulator scenarios) | INTERNAL | No | That the recommended action is the objectively correct real-world maintenance decision, or that it improves real operational outcomes relative to an alternative policy. The system never executes autonomous plant control actions — recommendations are proposal-only. |
| Work orders | Work-order lifecycle across FastAPI (services/api/routers/work_orders.py) and the Next.js console (web/src/app/work-orders/) | DEMONSTRATED | SYNTHETIC (internal demo/test tickets) | INTERNAL | No | Operational use by real technicians at a live commercial site. Zero commercial utility deployments currently exist. |
| Dispatch optimization | Safe-weather fleet crew dispatch optimizer (rai/decision/dispatch_optimizer.py) | ARCHITECTURALLY_SUPPORTED | MIXED (real cached weather forecasts; configured heuristic thresholds) | MIXED | No | A certified or legally binding (e.g. OSHA) operational safety guarantee. Thresholds are project-configured operational heuristics, not certified safety standards; forecast accuracy itself is a third-party dependency. |
| Weather-aware scheduling | Meteorological constraint-gating and safety-window classification within the same dispatch optimizer (rai/decision/dispatch_optimizer.py) — the weather-gating facet of dispatch optimization, not a separately built subsystem | ARCHITECTURALLY_SUPPORTED | MIXED (real forecast data; configured thresholds) | MIXED | No | A certified operational safety guarantee. Third-party forecast accuracy is not guaranteed, and following the schedule does not guarantee prevention of all weather-related field incidents. This is the same underlying engine as 'dispatch optimization' above, not an independent capability with separate evidence. |
| Technician feedback | Field-feedback ledger and dual-key promotion gate (rai/memory/library.py get_field_feedback_cases; artifacts/tickets.jsonl) | DEMONSTRATED | SYNTHETIC (demo/test fixtures) | INTERNAL | No | That any real technician has used the system in the field. Zero live commercial utility sites are connected; zero genuine external field observations exist in the live ledger. |
| Closed-loop learning | Feedback-to-retrieval ingestion pipeline with dual-key promotion gate, verified end-to-end in-browser | DEMONSTRATED | SYNTHETIC (internal/demo data) | INTERNAL | No | Production learning from live utility field data. This does NOT establish that the system continuously learns from real operational feedback — zero commercial utility sites are connected. |
| Frontend operational workflow | Next.js operator console (web/) — dashboard, asset deep-dive, evidence accordion, work-orders, dispatch console | DEMONSTRATED | SYNTHETIC (internal demo UI over cached/simulated data) | INTERNAL | No | Usability or effectiveness judged by a real plant operator. No user study, A/B test, or field usability evaluation has been performed. |

---

## 4. Critical Evidence Boundaries & Negative Declarations

- **CARE:** Benchmark evidence for wind anomaly-detection behavior.
- **Kelmarsh:** Evidence about documented operational/maintenance event association. NOT hardware-failure prediction validation.
- **PVDAQ:** Real data acquisition and modeling-readiness evidence. Gate 5.6B has no validation cohort. Therefore Gate 5.6C is NOT independently validated.
- **Local AI:** Tool use, provenance, bounded reasoning, abstention and workflow behavior demonstrated on the internal evaluation corpus. NOT production field validation.
- **Historical retrieval:** 14 external public-source cases exist. They are historical benchmark/open-data evidence. They are NOT live technician field verification. Retrieval-quality metrics are self-graded, not independently benchmarked.
- **Closed loop:** The browser workflow is end-to-end demonstrated. This does NOT establish production learning from utility field data.
- **Economics:** Results are modeled/projected consequences based on assumptions. Never label projected avoidable exposure as realized savings.
- **Dispatch / weather-aware scheduling:** Decision support under configured constraints. Never a certified operational safety guarantee.

---

## 5. Frozen Artifacts

The following artifacts in `artifacts/evaluation/evidence_freeze/` form the definitive audit trail:
- `evidence_registry.csv` / `evidence_registry.json`: 18-capability registry, one row per capability, exact 10-field schema.
- `evidence_matrix.md`: Detailed per-capability methodology, scope, and evidence-boundary profile.
- `claim_to_evidence.csv`: 18 public claims mapped to their exact supporting capability/artifact.
- `unsupported_claims.csv`: 6 identified overstatements and their verified remedies.
- `freeze_summary.md`: This executive governance document.