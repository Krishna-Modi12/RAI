# SCIENTIFIC EVIDENCE MATRIX — DETAILED CAPABILITY-TO-EVIDENCE MAPPING

**Freeze Date:** 2026-09-13  
**Audit Base Commit:** `acd214f`

This matrix provides the complete audit specification for every one of the 18 named
capabilities in the Evidence Freeze scope. Every row traces to an existing artifact or
report already present in this repository; no number here was computed for this
document — each is copied from the cited artifact.

| Capability | Real/Synthetic | External/Internal | Final Status | Exact Artifact |
|---|---|---|---|---|
| **CARE wind anomaly detection** | REAL | EXTERNAL | `VALIDATED` | artifacts/evaluation/external_care/ ; docs/evaluation/EXTERNAL_CARE.md |
| **CARE cross-farm transfer** | REAL | EXTERNAL | `VALIDATED` | artifacts/evaluation/gate54/ ; docs/checkpoints/14-gate54-cross-farm-wind-transfer.md |
| **Kelmarsh benchmark** | REAL | EXTERNAL | `VALIDATED` | artifacts/evaluation/kelmarsh_event_behaviour/ ; docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md |
| **Environmental context / discrimination** | MIXED (real external weather data; internal synthetic telemetry for fault/no-fault ground truth) | MIXED (external weather API + internal test scenarios) | `DEMONSTRATED` | tests/test_environment_solar.py ; docs/evaluation/GATE2_FORENSIC_AUDIT.md |
| **Solar PVDAQ data foundation** | REAL | EXTERNAL | `VALIDATED` | artifacts/evaluation/gate56/cohort_adjudication/ ; docs/checkpoints/13-solar-data-foundation.md |
| **Solar physics layer** | REAL telemetry; NOT_INDEPENDENTLY_VALIDATED methodology | EXTERNAL data source; INTERNAL model development | `NOT_VALIDATED` | artifacts/evaluation/gate56/gate56c_model_development/ ; docs/evaluation/GATE56C_VERIFICATION.md ; docs/evaluation/SOLAR_EXPECTED_PERFORMANCE.md |
| **Diagnosis** | SYNTHETIC (software-invariant test fixtures) | INTERNAL | `ARCHITECTURALLY_SUPPORTED` | tests/test_differential_diagnosis.py ; docs/checkpoints/22-counterevidence-differential-diagnosis.md |
| **Historical case retrieval** | MIXED — strictly partitioned, never merged | MIXED — strictly partitioned, never merged | `DEMONSTRATED` | artifacts/retrieval_benchmark_results.json ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md ; docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md |
| **RAG** | SYNTHETIC (internally authored, clearly-labelled sample documents) | INTERNAL | `DEMONSTRATED` | tests/test_rag.py |
| **Local AI agent** | SYNTHETIC (internal deterministic fixtures) | INTERNAL | `DEMONSTRATED` | artifacts/evaluation/agent_eval/ ; docs/evaluation/LOCAL_AGENT_EVALUATION.md |
| **Economic consequence analysis** | SIMULATED_OUTCOME (analytical model over configured assumptions) | INTERNAL | `DEMONSTRATED` | tests/test_economic_decision_support.py ; docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md ; docs/evaluation/DECISION_MATH_AUDIT.md |
| **Recommendation engine** | SYNTHETIC (software-invariant + simulator scenarios) | INTERNAL | `ARCHITECTURALLY_SUPPORTED` | tests/test_decision_engine.py ; tests/test_decision_math.py ; docs/evaluation/DECISION_MATH_AUDIT.md |
| **Work orders** | SYNTHETIC (internal demo/test tickets) | INTERNAL | `DEMONSTRATED` | docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md |
| **Dispatch optimization** | MIXED (real cached weather forecasts; configured heuristic thresholds) | MIXED | `ARCHITECTURALLY_SUPPORTED` | artifacts/weather_cache/ ; docs/checkpoints/24-crew-dispatch-weather-optimizer.md |
| **Weather-aware scheduling** | MIXED (real forecast data; configured thresholds) | MIXED | `ARCHITECTURALLY_SUPPORTED` | artifacts/weather_cache/kutch-wind_latest.json ; artifacts/weather_cache/charanka-solar_latest.json |
| **Technician feedback** | SYNTHETIC (demo/test fixtures) | INTERNAL | `DEMONSTRATED` | artifacts/evaluation/real_case_provenance/provenance_summary.json |
| **Closed-loop learning** | SYNTHETIC (internal/demo data) | INTERNAL | `DEMONSTRATED` | docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md |
| **Frontend operational workflow** | SYNTHETIC (internal demo UI over cached/simulated data) | INTERNAL | `DEMONSTRATED` | web/ ; docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md |

---

## Detailed Capability Profiles

### CARE wind anomaly detection
- **Final Status:** `VALIDATED`
- **Evidence Source:** CARE to Compare benchmark (Fraunhofer IEE), Zenodo 10.5281/zenodo.10958775 — 3 wind farms (A/B/C), 36 turbines, author-labeled failure events
- **Dataset / Fixture:** CARE Farms A/B/C SCADA + failure event logs
- **Real vs Synthetic:** REAL
- **External vs Internal:** EXTERNAL
- **Metric / Result:** Normal accuracy 0.995-0.999 across all 3 farms; CARE Operational Score 0.601 (A), 0.560 (B), 0.575 (C); false alarm rate <= 0.005
- **Artifact:** artifacts/evaluation/external_care/ ; docs/evaluation/EXTERNAL_CARE.md
- **What the evidence actually proves:** The physics-conditioned residual anomaly detector discriminates documented real turbine failure events from normal SCADA on an independent public benchmark across 3 farms.
- **What it does NOT prove:** *Universal zero-shot generalization to uncalibrated fleets or novel turbine models; causal root-cause diagnosis of the detected anomaly.*

### CARE cross-farm transfer
- **Final Status:** `VALIDATED`
- **Evidence Source:** CARE benchmark, 6 directed transfers under frozen CARE_COMMON protocol (Gate 5.4)
- **Dataset / Fixture:** CARE Farms A/B/C cross-evaluation (A<->B, A<->C, B<->C)
- **Real vs Synthetic:** REAL
- **External vs Internal:** EXTERNAL
- **Metric / Result:** Target-normal calibration recovers 106.3% of the transfer gap on C->A; B->A normal accuracy restored from 0.5965 to 0.9963
- **Artifact:** artifacts/evaluation/gate54/ ; docs/checkpoints/14-gate54-cross-farm-wind-transfer.md
- **What the evidence actually proves:** Calibrating on a small amount of unlabelled normal SCADA from a new (target) farm recovers cross-farm anomaly-detection performance on the real CARE benchmark.
- **What it does NOT prove:** *Raw, uncalibrated zero-shot transfer works without any target-farm telemetry; performance on farms/turbine types outside the CARE benchmark.*

### Kelmarsh benchmark
- **Final Status:** `VALIDATED`
- **Evidence Source:** Kelmarsh Wind Farm open dataset (Plumley), Zenodo 10.5281/zenodo.5841834 — 6 Senvion MM92 turbines, UK
- **Dataset / Fixture:** Kelmarsh SCADA + Greenbyte operational status/event codes
- **Real vs Synthetic:** REAL
- **External vs Internal:** EXTERNAL
- **Metric / Result:** Statistically significant elevation of RAI anomaly residuals during documented operational/maintenance event windows (cable untwist, curtailment, scheduled maintenance stop, calm-standstill)
- **Artifact:** artifacts/evaluation/kelmarsh_event_behaviour/ ; docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md
- **What the evidence actually proves:** RAI's continuous anomaly score behaves consistently with independently logged operational events on a second, independent real wind farm dataset.
- **What it does NOT prove:** *Failure prediction or hardware/component-failure detection. Kelmarsh's public record contains zero verified mechanical-failure ground truth; it documents operational status and trips only.*

### Environmental context / discrimination
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** pvlib clear-sky/POA physics baseline + CAMS/Open-Meteo dust & precipitation forecasts + peer-turbine gating (rai/models/environment_solar.py, rai/models/weather_provider.py)
- **Dataset / Fixture:** Real cached/live Open-Meteo + CAMS weather feeds applied to internal simulator-generated telemetry; Gate 2 leakage-hardened internal evaluation
- **Real vs Synthetic:** MIXED (real external weather data; internal synthetic telemetry for fault/no-fault ground truth)
- **External vs Internal:** MIXED (external weather API + internal test scenarios)
- **Metric / Result:** Deterministic unit tests passing for clear-sky/soiling/curtailment additive loss decomposition; Gate 2 audit reports false alarm rate 0.19/asset-year post peer-gating on leakage-hardened internal evaluation
- **Artifact:** tests/test_environment_solar.py ; docs/evaluation/GATE2_FORENSIC_AUDIT.md
- **What the evidence actually proves:** The system computes a physics-grounded expected-clean-power baseline from real weather inputs and can rule out environmental causes (irradiance, soiling, curtailment) before asserting an equipment fault, verified deterministically and under a zero-leakage audit.
- **What it does NOT prove:** *Real-world misdiagnosis rate on live plant instrumentation; evaluation ground truth is internal-simulator-based, not independently observed field weather/fault co-occurrence.*

### Solar PVDAQ data foundation
- **Final Status:** `VALIDATED`
- **Evidence Source:** NREL PVDAQ Open Energy Data Initiative (OEDI S3) — Systems 34, 1283, 1239, 1430, 1433
- **Dataset / Fixture:** 450 daily telemetry files, checksum-verified, mapped to canonical 26-signal solar taxonomy
- **Real vs Synthetic:** REAL
- **External vs Internal:** EXTERNAL
- **Metric / Result:** Adjudicated cohort: Development=[1239, 1283, 34], Validation=[] (state INSUFFICIENT_DATA); Systems 1430/1433 excluded (100% null UTC timestamps / no plant-level AC channel)
- **Artifact:** artifacts/evaluation/gate56/cohort_adjudication/ ; docs/checkpoints/13-solar-data-foundation.md
- **What the evidence actually proves:** Real public solar telemetry was acquired, checksum-verified, and mapped to a canonical schema, with documented, evidence-based data-quality exclusions.
- **What it does NOT prove:** *Any solar performance or fault model. This gate validates data acquisition only; the validation cohort produced by adjudication is empty, so no model has been independently evaluated on held-out systems.*

### Solar physics layer
- **Final Status:** `NOT_VALIDATED`
- **Evidence Source:** pvlib ModelChain physics reference vs polynomial empirical baseline vs hybrid champion model (Gate 5.6C)
- **Dataset / Fixture:** Development cohort only (NREL PVDAQ Systems 1239, 1283, 34), temporal within-system holdout split
- **Real vs Synthetic:** REAL telemetry; NOT_INDEPENDENTLY_VALIDATED methodology
- **External vs Internal:** EXTERNAL data source; INTERNAL model development
- **Metric / Result:** Within-system temporal holdout: R^2 = 0.70-0.99, nRMSE = 3-10% of rated capacity
- **Artifact:** artifacts/evaluation/gate56/gate56c_model_development/ ; docs/evaluation/GATE56C_VERIFICATION.md ; docs/evaluation/SOLAR_EXPECTED_PERFORMANCE.md
- **What the evidence actually proves:** Candidate solar expected-performance models fit real PVDAQ telemetry reasonably well on held-out time windows of the SAME systems they were developed on.
- **What it does NOT prove:** *Independent or cross-system validation. Gate 5.6B's Validation cohort is empty (INSUFFICIENT_DATA); therefore Gate 5.6C cannot be, and is not, independently validated. Zero cross-system generalization has been demonstrated.*

### Diagnosis
- **Final Status:** `ARCHITECTURALLY_SUPPORTED`
- **Evidence Source:** Counterevidence & differential diagnosis engine (rai/models/differential_diagnosis.py) + deterministic evidence reasoner (rai/agent/fallback.py)
- **Dataset / Fixture:** 11 targeted invariant tests + internal scenario fixtures (e.g. bearing wear vs lubrication degradation; soiling vs string fault)
- **Real vs Synthetic:** SYNTHETIC (software-invariant test fixtures)
- **External vs Internal:** INTERNAL
- **Metric / Result:** 11/11 targeted tests passing; 100% abstention to COMPETING_HYPOTHESES when counterevidence is symmetric
- **Artifact:** tests/test_differential_diagnosis.py ; docs/checkpoints/22-counterevidence-differential-diagnosis.md
- **What the evidence actually proves:** The system generates competing hypotheses, actively evaluates counterevidence, and abstains rather than asserting a single false cause, per its own coded rule set and ordering (weather/curtailment/sensor health ruled out before equipment fault).
- **What it does NOT prove:** *Diagnostic accuracy against real, unmodelled, or multi-fault cascading failures in physical plant operation. No external diagnostic ground truth was used.*

### Historical case retrieval
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** rai/memory/ trajectory-similarity retrieval over a partitioned real+synthetic case library
- **Dataset / Fixture:** 14 external real cases (rai/memory/real_corpus.py: 12 wind CARE/Kelmarsh + 2 solar PVDAQ) + 14 internal synthetic reference cases (rai/memory/library.py)
- **Real vs Synthetic:** MIXED — strictly partitioned, never merged
- **External vs Internal:** MIXED — strictly partitioned, never merged
- **Metric / Result:** On 10 deterministic test queries: P@1=90.0%, R@3=85.0%, MRR=0.950, partition purity=100%, provenance preservation=100%
- **Artifact:** artifacts/retrieval_benchmark_results.json ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md ; docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md
- **What the evidence actually proves:** Retrieval correctly surfaces topically-relevant precedent cases for a query asset and preserves source-type partition integrity — no synthetic case can leak into the real-case partition or vice versa.
- **What it does NOT prove:** *Causal failure diagnosis or ground-truth prediction of the current active fault. The underlying case corpus is real and externally sourced, but the P@1/R@3/MRR retrieval-quality metrics are computed against `relevant_case_ids` authored by the RAI team itself, not an independent or peer-reviewed relevance benchmark — this is a self-graded evaluation of retrieval mechanics, not an externally validated one. The 14 real cases are historical benchmark/open-data evidence, NOT live technician field verification.*

### RAG
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** SQLite FTS5 + BM25-style ranked keyword retrieval over a curated knowledge corpus (rai/rag/index.py, rai/rag/retrieve.py)
- **Dataset / Fixture:** 19 curated internal documents (manuals, SOPs, incident logs) under knowledge/
- **Real vs Synthetic:** SYNTHETIC (internally authored, clearly-labelled sample documents)
- **External vs Internal:** INTERNAL
- **Metric / Result:** 4/4 deterministic tests passing: capability probe, keyword search relevance (e.g. 'soiling' query), asset/component-filtered search, document list/get integrity (19 documents indexed)
- **Artifact:** tests/test_rag.py
- **What the evidence actually proves:** The FTS5 keyword+BM25 retrieval engine correctly returns relevant curated documents for known queries and correctly respects asset/component filters, over a small internally curated corpus.
- **What it does NOT prove:** *Retrieval quality on unseen or paraphrased real-world technician queries, or validation against an independent relevance benchmark. The corpus is a small internally curated sample (19 documents), not a comprehensive real maintenance-manual library.*

### Local AI agent
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Needle 2 runtime + deterministic fallback reasoner, evaluated via internal agent evaluation battery (rai/eval/agent_eval.py)
- **Dataset / Fixture:** 10 curated deterministic scenario fixtures, Evaluator Tasks A-G
- **Real vs Synthetic:** SYNTHETIC (internal deterministic fixtures)
- **External vs Internal:** INTERNAL
- **Metric / Result:** Tasks A-G passed 100%; tool selection = 1.00; abstention accuracy = 1.00; unsupported-claim rate = 0.00%; Needle 2 latency 6451.9 ms
- **Artifact:** artifacts/evaluation/agent_eval/ ; docs/evaluation/LOCAL_AGENT_EVALUATION.md
- **What the evidence actually proves:** Tool use, provenance preservation, bounded reasoning, mandatory abstention under symmetric evidence, and workflow behavior are demonstrated on the internal evaluation corpus.
- **What it does NOT prove:** *Production field performance, multi-turn conversational robustness on unmodelled real technician inputs, or safety under adversarial user prompts. This is NOT production field validation.*

### Economic consequence analysis
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Techno-economic decision-support engine (rai/economics/decision_support.py, rai/economics/engine.py)
- **Dataset / Fixture:** Configured commercial cost assumptions (tariffs, labor rates, parts costs); NPV comparison across Act Now / Defer 3d / Defer 14d
- **Real vs Synthetic:** SIMULATED_OUTCOME (analytical model over configured assumptions)
- **External vs Internal:** INTERNAL
- **Metric / Result:** Deterministic decision classification (INTERVENE/INSPECT/MONITOR/WAIT/ABSTAIN); mathematical invariants verified in test suite; 100% documented assumption provenance; zero fabricated probabilities
- **Artifact:** tests/test_economic_decision_support.py ; docs/evaluation/ECONOMIC_DECISION_INTELLIGENCE.md ; docs/evaluation/DECISION_MATH_AUDIT.md
- **What the evidence actually proves:** Given stated cost assumptions, the engine deterministically and reproducibly computes net financial consequences across intervention options, with explicit source labeling of every assumption and null-handling for missing inputs.
- **What it does NOT prove:** *Realized financial savings or empirically validated failure-probability distributions. Results are modeled/projected consequences based on assumptions — they must never be labeled as realized savings.*

### Recommendation engine
- **Final Status:** `ARCHITECTURALLY_SUPPORTED`
- **Evidence Source:** Confidence-gated decision policy with explicit human-abstention threshold (rai/agent/fallback.py, rai/decision/engine.py, rai/decision/policy.py)
- **Dataset / Fixture:** Deterministic decision-math and decision-intelligence test suites
- **Real vs Synthetic:** SYNTHETIC (software-invariant + simulator scenarios)
- **External vs Internal:** INTERNAL
- **Metric / Result:** Deterministic mapping of evidence packet + confidence to a bounded action set, verified by tests/test_decision_engine.py, tests/test_decision_intelligence.py, tests/test_decision_math.py
- **Artifact:** tests/test_decision_engine.py ; tests/test_decision_math.py ; docs/evaluation/DECISION_MATH_AUDIT.md
- **What the evidence actually proves:** Given a computed evidence packet, the policy deterministically and reproducibly maps evidence and confidence to one of a fixed, auditable set of recommended actions, and always escalates to human review below the confidence threshold rather than guessing.
- **What it does NOT prove:** *That the recommended action is the objectively correct real-world maintenance decision, or that it improves real operational outcomes relative to an alternative policy. The system never executes autonomous plant control actions — recommendations are proposal-only.*

### Work orders
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Work-order lifecycle across FastAPI (services/api/routers/work_orders.py) and the Next.js console (web/src/app/work-orders/)
- **Dataset / Fixture:** Internal/demo work-order tickets; Playwright browser walkthrough
- **Real vs Synthetic:** SYNTHETIC (internal demo/test tickets)
- **External vs Internal:** INTERNAL
- **Metric / Result:** End-to-end lifecycle (propose -> reject/approve -> dispatch -> feedback) browser-verified across 8 steps and 17 screenshots; API routes covered by unit/integration tests
- **Artifact:** docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md
- **What the evidence actually proves:** The work-order creation, human approval, and dispatch workflow functions correctly end-to-end in a demo/test environment, and always requires explicit human operator sign-off before dispatch.
- **What it does NOT prove:** *Operational use by real technicians at a live commercial site. Zero commercial utility deployments currently exist.*

### Dispatch optimization
- **Final Status:** `ARCHITECTURALLY_SUPPORTED`
- **Evidence Source:** Safe-weather fleet crew dispatch optimizer (rai/decision/dispatch_optimizer.py)
- **Dataset / Fixture:** Configured safety thresholds (wind climb <=12.0 m/s, gust <=18.0 m/s, solar rain=0mm, ambient temp<45C) applied to cached Open-Meteo forecasts
- **Real vs Synthetic:** MIXED (real cached weather forecasts; configured heuristic thresholds)
- **External vs Internal:** MIXED
- **Metric / Result:** Deterministic assignment of approved work orders to valid safety windows; zero safety-lockout violations observed in test scenarios
- **Artifact:** artifacts/weather_cache/ ; docs/checkpoints/24-crew-dispatch-weather-optimizer.md
- **What the evidence actually proves:** Crew dispatch scheduling correctly applies configured safety thresholds against real (cached) weather-forecast data to gate or allow physical field work, and correctly prioritizes and slots approved work orders.
- **What it does NOT prove:** *A certified or legally binding (e.g. OSHA) operational safety guarantee. Thresholds are project-configured operational heuristics, not certified safety standards; forecast accuracy itself is a third-party dependency.*

### Weather-aware scheduling
- **Final Status:** `ARCHITECTURALLY_SUPPORTED`
- **Evidence Source:** Meteorological constraint-gating and safety-window classification within the same dispatch optimizer (rai/decision/dispatch_optimizer.py) — the weather-gating facet of dispatch optimization, not a separately built subsystem
- **Dataset / Fixture:** Live/cached Open-Meteo forecast caches (artifacts/weather_cache/charanka-solar_latest.json, kutch-wind_latest.json)
- **Real vs Synthetic:** MIXED (real forecast data; configured thresholds)
- **External vs Internal:** MIXED
- **Metric / Result:** Deterministic window classification (APPROVED / MARGINAL / LOCKED_OUT) computed from live/cached forecast wind speed, gust, rain probability, and temperature
- **Artifact:** artifacts/weather_cache/kutch-wind_latest.json ; artifacts/weather_cache/charanka-solar_latest.json
- **What the evidence actually proves:** The scheduler correctly classifies field-work safety windows from real forecast inputs using fixed, auditable, documented thresholds.
- **What it does NOT prove:** *A certified operational safety guarantee. Third-party forecast accuracy is not guaranteed, and following the schedule does not guarantee prevention of all weather-related field incidents. This is the same underlying engine as 'dispatch optimization' above, not an independent capability with separate evidence.*

### Technician feedback
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Field-feedback ledger and dual-key promotion gate (rai/memory/library.py get_field_feedback_cases; artifacts/tickets.jsonl)
- **Dataset / Fixture:** 306 tickets inspected, 122 feedback entries; all are quarantined test fixtures or demo simulations
- **Real vs Synthetic:** SYNTHETIC (demo/test fixtures)
- **External vs Internal:** INTERNAL
- **Metric / Result:** 0 tickets promoted to EXTERNAL_REAL; 40 reclassified as quarantined test fixtures; 0 active production field deployments
- **Artifact:** artifacts/evaluation/real_case_provenance/provenance_summary.json
- **What the evidence actually proves:** The feedback-capture UI/API and the dual-key provenance gate (requires both FeedbackProvenance.EXTERNAL_FIELD_OBSERVED and ObservationLevel.FIELD_VERIFIED) function correctly, and correctly refuse to promote unverified or test tickets into the real-case retrieval memory.
- **What it does NOT prove:** *That any real technician has used the system in the field. Zero live commercial utility sites are connected; zero genuine external field observations exist in the live ledger.*

### Closed-loop learning
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Feedback-to-retrieval ingestion pipeline with dual-key promotion gate, verified end-to-end in-browser
- **Dataset / Fixture:** Playwright browser walkthrough of /work-orders and /assets/WT-004 (8-step lifecycle, 17 screenshots)
- **Real vs Synthetic:** SYNTHETIC (internal/demo data)
- **External vs Internal:** INTERNAL
- **Metric / Result:** 8-step operational loop (Anomaly -> Propose WO -> Approve -> Dispatch -> Feedback -> Case Ingestion -> Promotion Gate -> KPI state) verified end-to-end; dual-key gate enforced programmatically
- **Artifact:** docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md
- **What the evidence actually proves:** The full operator workflow from anomaly to technician feedback to candidate case-ingestion is demonstrated end-to-end in the browser, and the promotion gate correctly prevents demo/test feedback from contaminating the real-case retrieval memory.
- **What it does NOT prove:** *Production learning from live utility field data. This does NOT establish that the system continuously learns from real operational feedback — zero commercial utility sites are connected.*

### Frontend operational workflow
- **Final Status:** `DEMONSTRATED`
- **Evidence Source:** Next.js operator console (web/) — dashboard, asset deep-dive, evidence accordion, work-orders, dispatch console
- **Dataset / Fixture:** npm run build, npm run lint, Playwright browser verification screenshots
- **Real vs Synthetic:** SYNTHETIC (internal demo UI over cached/simulated data)
- **External vs Internal:** INTERNAL
- **Metric / Result:** Production build succeeds with zero type errors; lint clean; full operator workflow browser-verified; EvidenceAccordion correctly distinguishes confirmed-failure vs non-fault historical event classes after the provenance-reconciliation fix
- **Artifact:** web/ ; docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md ; docs/evaluation/REAL_CASE_CORPUS_PROVENANCE.md
- **What the evidence actually proves:** The operator-facing UI renders the evidence-backed decision workflow correctly end-to-end, builds and lints cleanly, and correctly represents case provenance and event class in its styling.
- **What it does NOT prove:** *Usability or effectiveness judged by a real plant operator. No user study, A/B test, or field usability evaluation has been performed.*
