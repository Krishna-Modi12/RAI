# Renewable Asset Intelligence (RAI)
## Final Live Demo Script (Step-by-Step Evaluator Walkthrough)

**Target Duration:** 4 minutes 30 seconds  
**Prerequisites:**  
1. Backend running: `uvicorn services.api.main:app --port 8000`  
2. Frontend running: `cd web && npm run dev` (Port 3000)  
3. Browser open to: `http://localhost:3000` (1440×900 or 1280×720 recommended)  

---

### Step 1 [0:00 – 0:30] — Fleet Command Dashboard
- **WHAT TO CLICK:** Start on `http://localhost:3000/`. Keep cursor still on top KPI tiles.
- **WHAT TO POINT AT:**
  - `Expected Exposure (30-Day)`: **₹1.21 Cr** (top right KPI tile).
  - `Fleet Operational Health`: **90.6%**.
  - `CARE benchmarked` badge in the header.
- **WHAT TO SAY:**
  > "We begin on the Fleet Operations Command console monitoring 42 generation units across Kutch Wind and Charanka Solar. The system aggregates unmitigated revenue risk into a single metric: ₹1.21 Crores over the next 30 days."
- **WHY IT MATTERS:** Establishes immediately that RAI operates on physical generation and economic exposure rather than count-based alarm spam.

---

### Step 2 [0:30 – 0:50] — Ranked Priority Queue & Asset Selection
- **WHAT TO CLICK:** Scroll smoothly down to the **Priority Queue** table. Click the blue **`Investigate ↗`** button on row **`WT-004`**.
- **WHAT TO POINT AT:**
  - Row `WT-004`: `Turbine 04 · Kutch Wind · Feeder 4B`.
  - Risk score: `0.48`, 14-day exposure: `₹9.51 Lakhs`.
  - Headline anomaly: `generator_winding_temp_c`.
- **WHAT TO SAY:**
  > "Rather than displaying 500 unranked threshold alarms, RAI ranks intervention urgency by expected financial exposure weighted by failure risk. WT-004 sits at the top of the queue with elevated risk on its generator winding. Let's investigate."
- **WHY IT MATTERS:** Demonstrates intelligent operational triage: operators focus their scarce maintenance bandwidth where financial risk is highest.

---

### Step 3 [0:50 – 1:15] — Asset Deep Dive: Signal Residuals
- **WHAT TO CLICK:** Arrive at `http://localhost:3000/assets/WT-004`. Hover briefly over the 168-hour Power Horizon Chart, then scroll to **Section 1: Anomaly Detection & Signal Residuals**.
- **WHAT TO POINT AT:**
  - Chart: Gray expectation envelope vs blue actual generation.
  - Table row 1: `generator_winding_temp_c` showing **`+12.3σ`** residual (+13.7°C above expectation).
  - Table row 2: `active_power_kw` showing **`-8.9σ`** residual.
- **WHAT TO SAY:**
  > "In Section 1, our physics-conditioned gradient boosted model isolates the anomaly. Actual generation dropped -8.9σ, but the root symptom is thermal: the generator winding temperature is running at +12.3σ—or +13.7°C—above expected physical equilibrium."
- **WHY IT MATTERS:** Shows that the anomaly detector doesn't just see a power drop; it identifies the specific physical component driving the deficit.

---

### Step 4 [1:15 – 1:35] — Environmental Attribution: Eliminating Weather
- **WHAT TO CLICK:** Scroll to **Section 2: Environmental Attribution & Weather Context**.
- **WHAT TO POINT AT:**
  - Left card: `Dust & Aerosol Index (AOD)`: `0.18 (LOW)`.
  - Center breakdown: `Weather explains only 24% of power deficit`.
  - Right verdict badge: **`Equipment Deficit Asserted`**.
- **WHAT TO SAY:**
  > "Before blaming equipment, we must check the atmosphere. Section 2 queries CAMS satellite aerosols. Dust optical depth is low, and ambient conditions only explain 24% of the deficit. The system formally asserts an Equipment Deficit, not environmental soiling."
- **WHY IT MATTERS:** Demonstrates false-alarm suppression: weather-driven underproduction is prevented from triggering expensive hardware inspections.

---

### Step 5 [1:35 – 2:00] — Peer Cohort Isolation: Eliminating Curtailment
- **WHAT TO CLICK:** Scroll to **Section 3: Fleet & Peer Cohort Isolation**.
- **WHAT TO POINT AT:**
  - Substation feeder: `Kutch Wind Farm · Feeder 4B (8 peers)`.
  - Metric: `Asset residual: -3.7% vs Peer median: -1.0%`.
  - Ranking badge: `Deviates further than 88% of cohort`.
- **WHAT TO SAY:**
  > "Next, we check for common-cause events. In Section 3, WT-004 is compared against eight identical turbines on the exact same electrical feeder. The peer median is normal, but WT-004 deviates further than 88% of its cohort. This conclusively rules out utility grid curtailment."
- **WHY IT MATTERS:** Differentiates localized physical damage from site-wide or feeder-wide dispatch curtailments.

---

### Step 6 [2:00 – 2:20] — Historical Precedent Retrieval
- **WHAT TO CLICK:** Scroll to **Section 4: Similar Historical Cases**. Click the **`REAL ONLY`** filter button.
- **WHAT TO POINT AT:**
  - Filter badge: `REAL ONLY (14 audited academic cases)`.
  - Top card: `REAL-KEL-1-FORCED-2550 · Kelmarsh Wind Farm · cooling_system`.
  - Similarity score: `80%`.
  - "Why Matched" bullet points vs "What Differs" points.
- **WHAT TO SAY:**
  > "In Section 4, our k-NN vector retriever searches our trajectory memory. We toggle 'REAL ONLY' to restrict search strictly to our 14 audited academic cases. The top match is a generator cooling fan thermal trip from the Kelmarsh dataset matching at 80% similarity, showing contrastive explainability."
- **WHY IT MATTERS:** Shows empirical precedent grounding without hallucination; operators see real-world precedent from public literature.

---

### Step 7 [2:20 – 2:45] — Techno-Economic Trade-Off Engine
- **WHAT TO CLICK:** Scroll to **Section 6: Techno-Economic Intervention Trade-Offs**.
- **WHAT TO POINT AT:**
  - Three comparison cards: `Act Now`, `Defer 3 Days`, `Defer 14 Days`.
  - `Act Now`: `Projected Avoidable Exposure: ₹17.42L`.
  - `Inspection & Repair Cost: ₹1.50L`.
  - `Modelled Net Benefit: +₹9.07L`.
- **WHAT TO SAY:**
  > "In Section 6, the decision engine evaluates the operational trade-off: Act Now vs Defer 3 Days vs Defer 14 Days. Under our stated cost parameters, acting now yields ₹17.42L in avoidable exposure for a net modeled benefit of +₹9.07L. Notice our honest language: we call this modeled benefit, not guaranteed savings."
- **WHY IT MATTERS:** Replaces arbitrary severity labels (High/Medium/Low) with financially defensible, transparent cost modeling.

---

### Step 8 [2:45 – 3:10] — Bounded Local AI & Decision Gating
- **WHAT TO CLICK:** Scroll to **Section 7: Decision Synthesis & Needle Model Gating**.
- **WHAT TO POINT AT:**
  - Confidence bar: `72% (Calibrated Confidence)`.
  - Red alert badge: **`Human Escalation Required`** (threshold is 80%).
  - Text summary: Synthesizes winding anomaly, peer deviation, and cooling precedent.
- **WHAT TO SAY:**
  > "In Section 7, our local quantized Needle 2 agent synthesizes the evidence. Because its calibrated confidence is 72%—below our strict 80% threshold—the system refuses to guess and explicitly mandates Human Escalation. RAI never takes physical equipment offline autonomously."
- **WHY IT MATTERS:** Demonstrates safety invariants: the AI engine is bounded, calibrated, and cannot execute dangerous unsupervised actuation.

---

### Step 9 [3:10 – 3:30] — Propose Work Order
- **WHAT TO CLICK:** Scroll to **Section 8: Operational Work Orders**. Click the blue **`Propose Work Order`** button. In the modal that opens, click **`Submit Proposal`** (or close).
- **WHAT TO POINT AT:**
  - Modal title: `Propose Maintenance Work Order`.
  - Prefilled fields: Asset ID `WT-004`, Priority `HIGH`, Action `Generator Cooling Fan Inspection & Winding Thermal Check`.
- **WHAT TO SAY:**
  > "In Section 8, the operator clicks 'Propose Work Order'. All evidence, recommended tasks, and deadlines are structured into a formal ticket for control room review."
- **WHY IT MATTERS:** Completes the transition from intelligence analysis into actionable enterprise operational maintenance.

---

### Step 10 [3:30 – 3:50] — Operator Approval & Operations Console
- **WHAT TO CLICK:** Click **`Operations`** in the left sidebar (navigates to `/work-orders`).
- **WHAT TO POINT AT:**
  - Top tab: `Active Work Orders (3)`.
  - Table: Lists pending and approved tickets with asset IDs, priorities, and status badges.
- **WHAT TO SAY:**
  > "We are now in the Operations Console where maintenance supervisors review pending tickets. Human approval is mandatory before any field crew is dispatched."
- **WHY IT MATTERS:** Proves strict human-in-the-loop governance.

---

### Step 11 [3:50 – 4:10] — Meteorological Crew Dispatch Planning
- **WHAT TO CLICK:** Click the second tab: **`Crew Dispatch & Weather Windows`**.
- **WHAT TO POINT AT:**
  - Left card: `Kutch Wind Farm` showing **`Safe Window: 6 Hours`** (wind 8.2 m/s < 12 m/s limit).
  - Right card: `Charanka Solar Park` showing **`UNSAFE: 0 Hours`** (rain probability 76% triggers high-voltage lockout).
  - Bottom table: `Optimized Crew Dispatch Schedule` assigning tasks to `Kutch-Crew-1`.
- **WHAT TO SAY:**
  > "Under Crew Dispatch, RAI integrates weather forecasts against configured safety constraints: Kutch Wind has a 6-hour safe window below our 12 m/s climb limit, but Charanka Solar is locked out due to rainfall. Dispatches are automatically routed within safe weather windows."
- **WHY IT MATTERS:** Grounds AI in operational reality: predictive alerts must honor worker safety and meteorological constraints.

---

### Step 12 [4:10 – 4:35] — Closed-Loop Feedback & Quarantine Invariant
- **WHAT TO CLICK:** Click the third tab: **`Closed-Loop Learning Status`**.
- **WHAT TO POINT AT:**
  - Card 1: `Audited Academic Cases: 14`.
  - Card 2: `Verified Field Cases: 0`.
  - Card 3: `Quarantined Test & Demo Records: 122`.
  - Diagram: Dual-key promotion gate.
- **WHAT TO SAY:**
  > "Finally, look at our Closed-Loop Learning architecture: when technicians record physical inspection findings, only records verified with physical teardown can enter the external real corpus. All demo simulations and test tickets are permanently quarantined in `INTERNAL_SYNTHETIC`—currently 122 records—ensuring zero contamination of our 14 academic benchmarks."
- **WHY IT MATTERS:** Proves scientific integrity: closed-loop learning is demonstrated without polluting frozen evaluation benchmarks.

---

### Step 13 [4:35 – 4:45] — Closing Statement
- **WHAT TO DO:** Return cursor to the top header. Look directly at the judges.
- **WHAT TO SAY:**
  > "Renewable Asset Intelligence turns telemetry uncertainty into defensible, human-governed operational decisions. All 554 tests pass offline, our benchmarks are leak-free, and every limitation is disclosed. Thank you."
