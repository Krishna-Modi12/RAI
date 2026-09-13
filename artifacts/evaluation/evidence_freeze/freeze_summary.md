# SCIENTIFIC EVIDENCE FREEZE — RENEWABLE ASSET INTELLIGENCE (RAI)

> **Official Evidence Freeze State.** All empirical claims, benchmark figures, demonstration
> capabilities, and architectural features across Renewable Asset Intelligence are formally audited,
> categorized, and frozen. Evidence determines the claim — never the reverse.

**Freeze Date:** 2026-09-13  
**Audit Commit:** `acd214f`  
**Governing Principles:**
1. Never fabricate, infer, or upgrade provenance.
2. Do not reinterpret synthetic/demo/test fixtures as real.
3. Preserve all existing safety and provenance boundaries.
4. Every claim must trace directly to an audited executable artifact.

---

## 1. The Four-Level Capability Taxonomy

Every capability in RAI is assigned exactly one of four formal tiers:

| Level | Formal Definition | Scope in RAI |
|---|---|---|
| **1. VALIDATED** | Measured against an appropriate external dataset or peer-reviewed public benchmark. | Wind Anomaly Detection (CARE A/B/C), Cross-Farm Transfer (Gate 5.4), Solar Data Foundation (Gate 5.6A/B), Kelmarsh Event Association, Historical Case Retrieval (14 external cases). |
| **2. DEMONSTRATED** | Fully implemented and functioning end-to-end, but demonstrated using controlled, synthetic, or internal scenario fixtures. | Simulator Physics Agreement, Local AI Agent Safety Battery, Techno-Economic Decision Support, Work Order Lifecycle, Closed-Loop Ingestion Mechanism, Technician Feedback Capture. |
| **3. ARCHITECTURALLY SUPPORTED** | Implemented and technically bounded in software, but not externally validated against real-world physical outcomes. | Counterevidence & Differential Diagnosis Engine, Safe-Weather Crew Dispatch Optimizer. |
| **4. NOT VALIDATED** | Explicitly not supported by current evidence; must NEVER be claimed as an accomplished capability. | Independent Solar Model Validation (Gate 5.6C), Kelmarsh Failure Prediction / Hardware Damage, Real-Time Commercial Utility Deployment, Autonomous Self-Learning from Live Grid Data. |

---

## 2. Authoritative 13-Capability Scorecard

| Capability | Evidence Source | Formal Level | Real vs Synthetic | External Validation? | Main Limitation |
|---|---|---|---|---|---|
| **Wind Anomaly Detection** | CARE Benchmark (Farms A, B, C; Zenodo 10958775; 36 turbines) | `VALIDATED` | Real External Data | Yes (CARE 0.56-0.60, Normal Acc > 0.995) | Evaluated on specific turbine types; does not guarantee zero-shot accuracy without target-normal calibration. |
| **Cross-Farm Transfer** | CARE Benchmark 6 directed transfers (Gate 5.4) | `VALIDATED` | Real External Data | Yes (106.3% gap recovery via unlabelled SCADA) | Requires unlabelled normal operating SCADA from the target farm; raw uncalibrated zero-shot transfer degrades. |
| **Environmental Discrimination** | CAMS Dust Memory (D(t)), pvlib clear-sky POA, Peer Gating | `DEMONSTRATED` | Simulated & Cached Forecasts | Partial (External CAMS weather data + synthetic injection) | Evaluated on synthetic transient injection and historical atmospheric feeds, not live physical field instrumentation. |
| **Solar Modeling Readiness** | NREL PVDAQ OEDI 450 daily files (Gate 5.6A/B) | `VALIDATED` | Real External Data | Data foundation only (Cohort Development=[1239, 1283, 34], Validation=[]) | Validation cohort is empty (INSUFFICIENT_DATA). Gate 5.6C solar model is NOT INDEPENDENTLY VALIDATED. |
| **Differential Diagnosis** | Counterevidence Engine (rai/models/differential_diagnosis.py) | `ARCHITECTURALLY_SUPPORTED` | Software Invariant | No (11 deterministic invariant tests passing) | Rule-based competing hypothesis elimination; does not validate diagnostic accuracy against unmodelled physical anomalies. |
| **Historical Precedent Retrieval** | 14 External Real Cases (CARE, Kelmarsh, PVDAQ) on 10 deterministic queries | `VALIDATED` | Real External Precedents | Yes (P@1=90.0%, R@3=85.0%, Partition Purity=100%) | Contextual precedent trajectory retrieval only; does NOT prove causal failure diagnosis or ground-truth prediction. |
| **Local AI Agent Reasoning** | Internal 10-fixture evaluation battery (Tasks A-G, Needle 2 benchmark) | `DEMONSTRATED` | Internal Synthetic Battery | No (100% pass on internal deterministic suite; 0.00% unsupported claims) | Bounded reasoning and tool selection on synthetic fixtures; does not prove production conversational field performance. |
| **Economic Decision Support** | Techno-Economic Engine (rai/economics/decision_support.py) | `DEMONSTRATED` | Analytical Mathematical Model | No (Verified against mathematical invariants) | Modelled/projected exposure under stated assumptions; does NOT represent realized cost savings or empirical failure probabilities. |
| **Intervention Recommendation** | Confidence-gated decision policy with explicit abstention (rai/agent/fallback.py) | `DEMONSTRATED` | Software Invariant | No (Deterministic rule engine) | Proposal-only decision support for human operators; system never executes autonomous plant control actions. |
| **Work Order Lifecycle** | Next.js Console (/work-orders) + FastAPI lifecycle routes | `DEMONSTRATED` | Interactive Browser & API | No (End-to-end browser verified with Playwright) | Workflow orchestration and operator approval interface; requires human operator sign-off before dispatch. |
| **Crew Dispatch Optimization** | Safe-Weather Optimizer (rai/decision/dispatch_optimizer.py) | `ARCHITECTURALLY_SUPPORTED` | Simulated Constraints + Weather Cache | No (Deterministic constraint scheduling) | Configured operational heuristics (<12m/s nacelle, 0mm rain); does NOT constitute a certified safety guarantee. |
| **Technician Feedback Capture** | Work Order feedback ledger (artifacts/tickets.jsonl) | `DEMONSTRATED` | Synthetic Demo Fixtures | No (Tested via Playwright & API unit tests) | Tested with simulated technician feedback in demo; zero live commercial utility technicians are currently active. |
| **Closed-Loop Learning** | Feedback-to-Retrieval Ingestion with Dual-Key Promotion Gate | `DEMONSTRATED` | Internal Synthetic Corpus Only | No (Browser verified; dual-key gate programmatically enforced) | Demonstrated operational mechanism on internal fixtures; does NOT prove continuous autonomous learning from live commercial utility data. |

---

## 3. Critical Evidence Boundaries & Negative Declarations

### A. Wind Domain (CARE & Kelmarsh)
- **CARE Benchmark (Zenodo 10958775):** Provides genuine external validation of physics-conditioned residual anomaly detection (Normal Accuracy > 0.995, CARE Operational Score 0.56–0.60 on 36 turbines). Target-normal calibration recovers 106.3% of the cross-farm transfer gap on Farm C->A.
- **Kelmarsh Benchmark (Zenodo 5841834):** Statistically associates RAI continuous anomaly scores with documented operational event windows (cable untwisting, curtailment, scheduled maintenance, calm standstills). **NEGATIVE DECLARATION:** Kelmarsh does NOT validate failure prediction or hardware damage; no mechanical failure ground-truth labels exist in the public record.

### B. Solar Domain (PVDAQ & Gate 5.6)
- **Gate 5.6A/5.6B (Data Foundation):** 450 checksummed telemetry files acquired from NREL PVDAQ OEDI. Adjudicated cohort: Development=`[1239, 1283, 34]`, Validation=`[]` (`INSUFFICIENT_DATA`).
- **Gate 5.6C (Model Development):** pvlib ModelChain physics reference vs empirical baseline vs hybrid champion fit on within-system temporal holdouts ($R^2 = 0.70–0.99$). **NEGATIVE DECLARATION:** Labeled throughout as `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED`. Zero cross-system generalization demonstrated. No independent validation cohort.

### C. Local AI Agent
- Evaluator Tasks A through G passed on 10 deterministic scenario fixtures (Tool Selection = 1.00, Abstention = 1.00, Unsupported Claim Rate = 0.00%, Needle 2 runtime 6451 ms).
- **NEGATIVE DECLARATION:** Demonstrates safety invariants and bounded reasoning on internal synthetic fixtures; does NOT prove production field performance on unmodelled conversational inputs.

### D. Closed-Loop Lifecycle & Learning
- Complete operational lifecycle (Propose -> Approve -> Dispatch -> Feedback -> Case Ingestion) verified in browser across 8 steps and 17 screenshots.
- Dual-key promotion gate (`FeedbackProvenance.EXTERNAL_FIELD_OBSERVED` AND `ObservationLevel.FIELD_VERIFIED`) prevents test/demo tickets from contaminating `EXTERNAL_REAL` retrieval memory.
- **NEGATIVE DECLARATION:** Zero live commercial utility sites are connected. Current tickets are quarantined test fixtures or demo records. Demonstrates workflow mechanics, NOT autonomous learning from live grid data.

### E. Economics & Dispatch
- Decision engine calculates net financial consequences across intervention options using stated cost assumptions.
- **NEGATIVE DECLARATION:** Modelled projected exposure under assumed counterfactuals; does NOT represent realized financial savings. Safe-weather dispatch uses site-specific heuristic constraints, NOT certified legal safety guarantees.

---

## 4. Summary of Frozen Artifacts

The following artifacts in `artifacts/evaluation/evidence_freeze/` form the definitive audit trail:
- `evidence_registry.csv`: Complete metadata for all 14 evidence sources (A through J).
- `evidence_registry.json`: Structured machine-readable registry with full citation references.
- `evidence_matrix.md`: Comprehensive evidence matrix detailing methodologies, scopes, and bounds.
- `claim_to_evidence.csv`: Strict mapping from every public claim to its exact supporting artifact.
- `unsupported_claims.csv`: Log of 6 identified overstatements and their verified remedies.
- `freeze_summary.md`: This executive governance document.