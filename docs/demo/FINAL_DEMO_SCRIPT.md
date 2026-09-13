# Renewable Asset Intelligence (RAI) — Final Evaluator Demo Script

**Target Audience:** Technical Hackathon Judges, Energy Systems Evaluators, Machine Learning Researchers  
**Duration:** 3–5 minutes  
**Environment:** Clean-state local environment (`FastAPI` on `http://127.0.0.1:8000`, `Next.js` on `http://localhost:3000`)  
**Scientific Evidence Baseline:** Frozen at `d7a92d1` under the [Four-Level Evidence Taxonomy](../../README.md#scientific-evidence-what-is-actually-validated).

---

## Quick Reference: The 5-Minute Evaluator Journey

```
0:00–0:30 ─── Problem + Thesis (Fleet Command Header & Four KPI Tiles)
0:30–1:15 ─── Fleet Priority Queue → Choose Asset (WT-004 Generator Winding Anomaly)
1:15–2:00 ─── Investigate Anomaly & Environmental Context (168h Horizon & CAMS Dust Check)
2:00–2:40 ─── Historical Case Retrieval & Techno-Economics (14 Audited Cases & Net NPV)
2:40–3:30 ─── Local Reasoner Recommendation & Propose Work Order (Confidence Gating)
3:30–4:15 ─── Control Room Operator Approval & Safe Weather Dispatch Planning
4:15–5:00 ─── Technician Field Findings & Closed-Loop Memory Boundary
```

---

## 0:00–0:30 — Problem Statement & Product Thesis

### Action
1. Open `http://localhost:3000/` in the browser.
2. Observe the top application shell and four primary metric tiles.

### Talk Track
> *"Renewable asset monitoring suffers from a fundamental structural problem: raw power deficit alarms are ambiguous. When an asset underproduces, is it a failing gearbox bearing, an atmospheric dust storm, a utility curtailment order, or a drifting sensor? Threshold alarms cannot tell them apart, causing either crippling alarm fatigue or catastrophic forced outages.*
>
> *Renewable Asset Intelligence (RAI) is not just another anomaly detector. It is a full-lifecycle operational decision engine that conditions SCADA telemetry against physical expectations, attributes atmospheric context, queries 14 external audited academic failure precedents, estimates the net financial consequence of waiting, and enforces human-in-the-loop governance for crew dispatch and feedback."*

### What the Judge Should Notice
- **Top Navigation Bar:** Live status indicators: `Site: Kutch Wind (18) + Charanka Solar (24)`, UTC clock, and `NEEDLE2` active local reasoning engine.
- **Header Badge:** `CARE benchmarked` indicating baseline compliance against the peer-reviewed wind benchmark (Zenodo 14006163).
- **Four Standardized Metric Tiles:**
  1. `Fleet Operational Health`: **90.6%** (Weighted across 42 generation units).
  2. `Generation vs Expected`: **34,302 kW** vs **23,746 kW** expected (Physics + Gradient-Boosted Model expectation).
  3. `Plant Availability`: **100%** (42 active units).
  4. `Expected Exposure (30-Day)`: **₹1.21 Cr** (Modeled economic cost of leaving unaddressed).
- **Honest Provenance Subtitles:** Every tile explicitly displays its mathematical backend origin (e.g. `physics_gbm_expectation`, `rai.economics.engine`).

---

## 0:30–1:15 — Fleet Overview & Asset Selection

### Action
1. Scroll down to the **Ranked Action Queue**.
2. Point out how assets are prioritized by `14-Day Expected Exposure × Risk`.
3. Locate asset **`WT-004`** (Kutch Wind Farm · Sector 3 · Feeder 4B).
4. Click the **`Investigate ↗`** button on `WT-004`.

### Talk Track
> *"Rather than presenting an unranked list of 500 threshold warnings, RAI ranks intervention urgency by combining Weibull failure hazard with unmitigated revenue exposure. Here, WT-004 has an elevated risk score of 48% with ₹9.51 Lakhs projected exposure and a 168-hour intervention deadline. Let’s investigate."*

### What the Judge Should Notice
- **Prioritization Formula:** Priority queue sorts strictly by expected economic exposure weighted by anomaly persistence, not arbitrary alarm thresholds.
- **Component Specificity:** Dominant signal is immediately identified on the queue row (`generator_winding_temp_c`).
- **Smooth Navigation:** Seamless client-side transition directly into `/assets/WT-004`.

---

## 1:15–2:00 — Investigate Anomaly & Environmental Attribution

### Action
1. Inspect the **WT-004 Hero Section** and **Active Power Horizon Chart**.
2. Scroll to **Section 1: Anomaly Detection & Signal Residuals**.
3. Scroll to **Section 2: Environmental Attribution & Weather Context**.
4. Expand/inspect **Section 3: Fleet & Peer Cohort Isolation**.

### Talk Track
> *"On the asset investigation screen, we immediately answer the first three operational questions:*
> 1. **What is wrong?** *The 168-hour power chart shows actual generation tracking normal bounds until recent timestamps. In Section 1, the signal table pinpoints `generator_winding_temp_c` as the dominant anomaly at +12.3σ above physical expectation (+13.7°C residual), while power drops -8.9σ.*
> 2. **Is it the weather?** *In Section 2, RAI checks live CAMS atmospheric composition and satellite weather. Dust exposure is LOW; ambient conditions only explain 24% of the deficit. The attribution verdict is unambiguous: Equipment Deficit.*
> 3. **Is it a common cause across the site?** *In Section 3, WT-004's residual (-3.7%) is isolated against 8 identical turbines on Feeder 4B (peer median -1.0%). WT-004 deviates further than 88% of the cohort, ruling out grid curtailment or site-wide wind shear."*

### What the Judge Should Notice
- **Provenance Labels:** Section 1 is labeled `[OBSERVED]` with source `residual_anomaly_detector`.
- **Deviation Visualizer:** Mini bidirectional ±3σ bars clearly show which physical components are exceeding statistical limits.
- **False Alarm Suppression:** The system explicitly checks environmental and peer factors before accusing physical hardware.

---

## 2:00–2:40 — Historical Precedent & Techno-Economics

### Action
1. Scroll to **Section 4: Similar Historical Cases (Contextual Evidence)**.
2. Click the **`REAL ONLY`** filter button.
3. Review the top matching case: `REAL-KEL-1-FORCED-2550 · cooling_system`.
4. Scroll to **Section 6: Techno-Economic Intervention Trade-Offs**.

### Talk Track
> *"Now we look at historical precedent and economics:*
> - *In Section 4, our k-NN vector retriever searches our trajectory library. Notice the partition toggle: we can filter strictly to `REAL ONLY (14 audited academic cases)` from Kelmarsh and CARE to Compare. The top match is a generator cooling fan thermal protection trip with 80% cosine similarity. Crucially, the UI displays both 'Why Matched' and 'What Differs', with an explicit limitation disclaimer: historical context only; does not prove current diagnosis.*
> - *In Section 6, the Techno-Economic Engine compares three distinct operational paths: Act Now vs. Defer 3 Days vs. Defer 14 Days. Under our stated cost assumptions, acting now yields ₹17.42L in Projected Avoidable Exposure for a Net Benefit of +₹9.07L. Notice our honest language: we never claim 'guaranteed savings' or 'realized ROI' because counterfactual savings cannot be directly measured without a randomized control trial."*

### What the Judge Should Notice
- **Corpus Purity:** Strict demarcation between `EXTERNAL_REAL` (peer-reviewed datasets) and `INTERNAL_SYNTHETIC`.
- **Contrastive Explanations:** The case card lists what features match and what features diverge.
- **De-Hyped Economics:** Wording uses `Projected Avoidable Exposure (Modelled risk estimate)` and `Modelled Net Benefit`.

---

## 2:40–3:30 — Recommendation & Work Order Creation

### Action
1. Scroll to **Section 7: Decision Synthesis & Needle Model Gating**.
2. Note the **80% Confidence Gating Bar**.
3. Scroll to **Section 8: Operational Work Orders & Ground-Truth Field Ledger**.
4. Click **`Propose Work Order`**.
5. In the modal, review the action, deadline (72h), and priority (`HIGH`).
6. Click **`Cancel`** (or submit) to show that governance is maintained.

### Talk Track
> *"In Section 7, our local quantized AI agent synthesizes the evidence. Because the reasoning confidence is evaluated under strict calibration constraints, the consensus verdict flags `Human Escalation Required`. RAI never executes autonomous actuation on the plant; it presents a structured proposal to the licensed human operator.*
>
> *In Section 8, the operator can directly authorize or propose a formal work order with complete audit logging."*

### What the Judge Should Notice
- **Confidence Gate:** Below the 80% calibrated threshold, the system forces human escalation rather than guessing.
- **Traceable Reasoning:** The engine identifies `needle2_agent_evidence_synthesis` with deterministic financial metrics.
- **Human-in-the-Loop:** Safety boundary is visible and enforced.

---

## 3:30–4:15 — Operations Console & Safe Weather Dispatch Planning

### Action
1. Click **`Operations`** in the left sidebar (navigating to `/work-orders`).
2. Review the top operations KPI tiles:
   - `Pending Approval`: 114+ tickets
   - `Active Dispatches`: 42 scheduled
   - `Field Concordance`: 90.4%
   - `Indexed Field Cases`: 122 + 14 academic cases
3. Click the **`Crew Dispatch & Weather Windows`** tab.
4. Review the site weather safety constraints for **Kutch Wind Farm** and **Charanka Solar Park**.
5. Inspect the **Optimized Fleet Crew Dispatch Schedule**.

### Talk Track
> *"On the Operations Command console, we manage fleet maintenance logistics. Notice the 'Crew Dispatch & Weather Windows' tab:*
> *A predictive alert is useless if you dispatch technicians into a thunderstorm. RAI integrates site weather forecasts against configured operational safety constraints:*
> - *At Kutch Wind Farm, wind speeds of 18 m/s approach tower climb limits (12 m/s), granting only a marginal 6-hour ground maintenance window.*
> - *At Charanka Solar Park, rain probability of 76% triggers high-voltage lockout, resulting in an UNSAFE 0-hour window.*
> *The dispatch optimizer automatically routes available crews to safe, high-exposure interventions first."*

### What the Judge Should Notice
- **Weather Constraint Enforcement:** Dispatch honors meteorological safety limits (wind < 12 m/s, precipitation 0 mm).
- **Crew Allocation:** Dispatches are assigned to specific crews (`Kutch-Crew-1`, `Kutch-Crew-2`) with estimated task duration.

---

## 4:15–5:00 — Technician Feedback & Closed-Loop Learning Boundary

### Action
1. Click the **`Closed-Loop Learning Status`** tab.
2. Review the **4-Stage Closed-Loop Operational Architecture**:
   - `Stage 1: AI Anomaly & Reasoner`
   - `Stage 2: Human Gating & Dispatch`
   - `Stage 3: Technician Ground Truth`
   - `Stage 4: LEARN — Strict Provenance RAG Indexing`
3. Inspect the **Corpus Partition Purity Box**:
   - `Audited Academic Cases`: 14
   - `Verified Field Cases`: 0
   - `Synthetic Test Ledger`: 122
4. Conclude the demonstration.

### Talk Track
> *"Finally, we show RAI’s closed-loop learning architecture and our scientific honesty:*
> *When a technician returns from the field, they log physical inspection findings: component condition, actual downtime, and realized parts costs.*
>
> *Most AI demos would claim 'the model continuously retrained in real time.' That is dangerous and scientifically invalid in high-voltage infrastructure. Instead, RAI enforces a strict dual-key promotion gate:*
> - *Only genuine field observations with verified physical teardowns (`EXTERNAL_FIELD_OBSERVED` + `FIELD_VERIFIED`) can ever enter the `EXTERNAL_REAL` retrieval partition.*
> - *Automated test fixtures, demo simulations, and unverified reports remain quarantined as `INTERNAL_SYNTHETIC` (currently 122 records), guaranteeing zero contamination of our external benchmark partition (14 academic cases).*
>
> *RAI provides end-to-end operational intelligence: from noisy telemetry, through physical and economic filtering, to human dispatch and grounded learning."*

### What the Judge Should Notice
- **Zero Hallucinated Claims:** Transparently discloses that `Verified Field Cases = 0` (no live commercial turbines connected).
- **Quarantine Invariant:** Synthetic demo tickets never pollute the real benchmark evaluation partition.
- **Architectural Completeness:** The entire loop from telemetry ingestion to post-repair case indexing is fully functional.

---

## Evaluator Scorecard FAQ

| Judge Question | Where It Is Proven |
|---|---|
| **What is validated vs. demonstrated?** | [README Evidence Taxonomy Table](../../README.md#scientific-evidence-what-is-actually-validated) & `/evaluation` route |
| **Are the benchmarks leak-free?** | `docs/evaluation/GATE2_FORENSIC_AUDIT.md` (342h purge embargo, zero feature leakage) |
| **How does it perform on real external data?** | `docs/evaluation/EXTERNAL_CARE.md` (Wind Farm A, Zenodo 14006163, CARE = 0.535) |
| **Is the local LLM reasoning bounded?** | `rai/agent/needle_engine.py` (Needle 2 quantized, zero external API calls, deterministic math fallback) |
| **Can the system be run completely offline?** | Yes, 554 unit tests pass offline; all SCADA and weather caches are local |
