# Renewable Asset Intelligence (RAI)
## Final Hackathon Pitch Deck (5 Slides)

---

### SLIDE 1 — THE PROBLEM
## Renewable Assets Don't Need More Alarms. They Need Better Decisions.

Modern SCADA systems trigger alarms whenever generation crosses fixed thresholds (e.g., power < 80% of rating). But in renewable energy, generation deficits are **ambiguous by construction**:

```
                              ┌── Internal Component Degradation (bearing wear, cooling trip)
                              ├── Atmospheric Dust & Soiling (CAMS aerosol optical depth)
Low Generation Deficit ───────┼── Weather Transients & Cloud Passes (monsoon fronts)
                              ├── Utility Grid Curtailment Orders (substation directives)
                              └── Sensor Calibration Drift (anemometer/pyranometer bias)
```

**The Consequence:**
1. **Alarm Fatigue:** Hundreds of unranked warnings during routine cloud cover or dust storms drown out real degradation signals.
2. **Catastrophic Forced Outages:** Genuine mechanical faults evolve unnoticed within ambient variance until a multi-crore component seizes.
3. **Operational Paralysis:** Operators are left staring at unranked trend lines with zero guidance on *cause*, *urgency*, or *financial cost of waiting*.

---

### SLIDE 2 — THE RAI DIFFERENCE
## From Ambiguous Telemetry to a Defensible Decision Loop

RAI does not stop at detecting an anomaly. It turns ambiguous anomalies into an auditable, human-governed operational decision:

```
  SENSE ──> EXPECT ──> DETECT ──> CONTEXTUALIZE ──> COMPARE ──> RETRIEVE ──> QUANTIFY ──> DECIDE ──> ACT & LEARN
```

**The 8-Factor Decision Stack:**
- **Physics-Grounded Expected Behaviour:** LightGBM + physics power curves conditioned on real-time ambient temperature, irradiance, and wind.
- **Statistical Residual Anomaly Detection:** Multi-signal conditioned $z$-score residuals with change-point persistence filtering.
- **Atmospheric Environmental Attribution:** CAMS atmospheric dust integral $D(t)$, clear-sky normalization, and rain wash kinetics.
- **Peer Cohort Isolation:** Compares candidate units against identical turbines/inverters on the same feeder to rule out site-wide events.
- **Audited Historical Precedent:** Trajectory k-NN matching against 14 audited academic cases with contrastive "Why Matched" vs "What Differs" breakdowns.
- **Techno-Economic Quantification:** Compares Net Present Value ($\text{NPV}$) of Act Now vs Defer 3d vs Defer 14d under transparent cost assumptions.
- **Bounded Local AI Explanation:** Quantized Needle 2 local engine explains structured evidence; zero numerical math in LLM; deterministic rule fallback.
- **Human-Governed Execution:** Mandatory operator approval for work orders; weather-safe crew dispatch; quarantined closed-loop memory.

---

### SLIDE 3 — THE TECHNICAL ARCHITECTURE
## Strict Separation: Numerical Engine vs. Bounded Local Reasoner

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & DATA QUALITY                                                           │
│    Raw SCADA Telemetry (10-min) + CAMS Atmospheric Aerosols + Open-Meteo Forecasts      │
│    Data Alignment · Frozen Sensor Detection · Curtailment Regime Identification       │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│ 2. DETERMINISTIC NUMERICAL ENGINE (Python / DuckDB / scikit-learn)                     │
│    • Expected Power: Physics + LightGBM Conditioned Baseline                          │
│    • Residuals: Multi-signal Conditioned Residuals & Anomaly Fusion                    │
│    • Environmental Attribution: Aerosol Dust Integral D(t) Loss Breakdown             │
│    • Peer Isolation: Feeder/Substation Cohort Residual Ranking                        │
│    • Precedent Retrieval: 14-Case Audited Vector Memory (Kelmarsh / CARE / PVDAQ)      │
│    • Techno-Economics: Counterfactual NPV Trade-Off Engine (Act Now vs Defer)         │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │ Structured EvidencePacket (Zero Math in LLM)
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│ 3. BOUNDED LOCAL AI & DECISION GATING (Needle 2 / Deterministic Fallback)             │
│    • Calibrated Confidence Gating (Forces Human Escalation if Confidence < 80%)       │
│    • Zero Plant Actuation: Strict Proposal-Only Work Orders                           │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│ 4. HUMAN-IN-THE-LOOP OPERATIONS & GOVERNANCE (Next.js / FastAPI)                      │
│    • Control Room Operator Review & Authorization                                      │
│    • Weather-Aware Crew Dispatch (Wind < 12 m/s, Rain = 0 mm Constraints)              │
│    • Technician Field Findings Logging (As-Found Condition, Parts Cost, Downtime)      │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│ 5. QUARANTINED CLOSED-LOOP LEARNING GATE                                               │
│    • Dual-Key Promotion Gate: EXTERNAL_FIELD_OBSERVED + FIELD_VERIFIED                │
│    • Zero Benchmark Contamination: Test Fixtures & Demo Tickets Quarantined           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### SLIDE 4 — EVIDENCE & SCIENTIFIC HONESTY
## Authoritative Evidence Taxonomy: What is Validated vs. Demonstrated

RAI maintains an immutable Scientific Evidence Freeze ([`freeze_summary.md`](artifacts/evaluation/evidence_freeze/freeze_summary.md)) to prevent overclaiming:

| Evidence Tier | Capability | Underlying Dataset / Method | What is Actually Proven |
|---|---|---|---|
| **VALIDATED** | **Wind Anomaly Detection** | CARE Benchmark (Zenodo 10958775; Farms A/B/C) | Normal accuracy > 0.995; embargoed leak-free PR-AUC = 0.822, MCC = 0.690 |
| **VALIDATED** | **Cross-Farm Transfer** | CARE Gate 5.4 Protocol | Target-normal calibration recovers 106.3% of performance without retraining |
| **VALIDATED** | **Operational Event Association** | Kelmarsh Wind Farm (Zenodo 5841834) | SCADA anomaly windows statistically associate with recorded Greenbyte log events |
| **VALIDATED** | **Historical Case Retrieval** | 14 Audited Academic Records | High-precision vector retrieval with preserved provenance and contrastive explainability |
| **VALIDATED** | **Solar Data Foundation** | NREL PVDAQ (OEDI 450 daily files; Gate 5.6A/B) | Robust data ingestion, temporal ordering, and quality filters over multi-year solar data |
| **DEMONSTRATED** | **Local AI Agent Reasoning** | Internal Evaluation Battery (Tasks A–G) | 100% tool selection, 100% abstention correctness, 0.00% unsupported claims |
| **DEMONSTRATED** | **Techno-Economic Engine** | Mathematical Decision Engine (`rai/economics/`) | Deterministic NPV calculation under explicit, source-labelled user cost assumptions |
| **DEMONSTRATED** | **Work Order Lifecycle** | Next.js Console & FastAPI Service | Full-lifecycle propose, approve, reject, feedback, and audit tracking |
| **DEMONSTRATED** | **Closed-Loop Feedback Ingestion** | Synthetic Work Order Fixtures | Automated ingestion of completed work orders into queryable memory partitions |
| **ARCHITECTURALLY SUPPORTED** | **Differential Diagnosis** | Rule-Based Counterevidence Matrix | Formal elimination of competing failure hypotheses from sensor signatures |
| **ARCHITECTURALLY SUPPORTED** | **Meteorological Crew Dispatch** | Open-Meteo Window Scheduler | Route optimization respecting user-configured wind (<12 m/s) and rain (0 mm) limits |
| **NOT VALIDATED** | **Independent Solar Failure Model** | Gate 5.6C Independent Audit | Validation cohort empty; solar component failure prediction is **not claimed** |
| **NOT VALIDATED** | **Live Utility Deployment** | None | Zero live commercial utility plant SCADA feeds currently connected |

---

### SLIDE 5 — WHY IT MATTERS
## The WT-004 Journey: From Telemetry Uncertainty to Operational Action

```
[TELEMETRY]        WT-004 power deficit detected (-8.9σ)
      │
[RESIDUAL]         Generator winding temperature deviating at +12.3σ (+13.7°C above physical model)
      │
[ENVIRONMENT]      CAMS dust exposure is LOW; weather explains only 24% of deficit (Equipment Deficit)
      │
[PEER ISOLATION]   Deviates beyond 88% of identical turbines on Feeder 4B (rules out curtailment)
      │
[HISTORY]          Retrieves audited Kelmarsh cooling fan trip (80% similarity; REAL ONLY partition)
      │
[ECONOMICS]        Act Now vs Defer: Projected Avoidable Exposure ₹17.42L, Net Benefit +₹9.07L
      │
[RECOMMENDATION]   Local reasoner flags "Human Escalation Required" (confidence < 80% threshold)
      │
[GOVERNANCE]       Licensed operator reviews structured evidence and approves Inspection Work Order
      │
[DISPATCH]         Enforces safe meteorological window (Kutch 6h safe window vs Charanka rain lockout)
      │
[CLOSED LOOP]      Technician logs fan relay replacement; ticket quarantined in INTERNAL_SYNTHETIC
```

> **"RAI does not guess. It converts telemetry uncertainty into a defensible operational decision."**
