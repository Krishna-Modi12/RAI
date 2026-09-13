# Renewable Asset Intelligence (RAI)
## Verified Screenshot Guide for Presentations & Slidedecks

This guide documents the **5 strongest verified visual assets** captured from the live application and preserved in [`artifacts/evaluation/demo_audit/`](../../artifacts/evaluation/demo_audit/).

---

### Screenshot 1: Fleet Operations Command Dashboard
- **Filename:** [`artifacts/evaluation/demo_audit/01_home_fleet_command.png`](../../artifacts/evaluation/demo_audit/01_home_fleet_command.png)
- **Presentation Location:** Slide 1 / Demo Step 1 (`http://localhost:3000/`)
- **Visual Subject:** Full Fleet Command view with the 4 standard KPI tiles and the exposure-weighted Priority Queue.
- **What the Audience Should Notice:**
  - `Expected Exposure (30-Day)`: **₹1.21 Cr** (quantified financial urgency rather than alarm counts).
  - `Fleet Operational Health`: **90.6%** across 42 generation units.
  - Priority Queue ranking: Asset `WT-004` is at the very top of the queue with risk `0.48` and ₹9.51 Lakhs 14-day exposure.
  - Subtle provenance labels under every tile (e.g., `physics_gbm_expectation`, `rai.economics.engine`).
- **What NOT to Explain:** Do not explain the raw column headers or every secondary asset in the bottom table. Focus exclusively on how the Priority Queue orders interventions by *financial risk*.

---

### Screenshot 2: Asset Deep Dive & Component Signal Residuals
- **Filename:** [`artifacts/evaluation/demo_audit/03_asset_section1_residuals.png`](../../artifacts/evaluation/demo_audit/03_asset_section1_residuals.png)
- **Presentation Location:** Slide 2 / Demo Step 3 (`/assets/WT-004`)
- **Visual Subject:** Section 1 Component Residuals table showing multi-signal conditioned deviations.
- **What the Audience Should Notice:**
  - `generator_winding_temp_c` deviating at **`+12.3σ`** (+13.7°C above physical expectation).
  - `active_power_kw` dropping at **`-8.9σ`** (-378.2 kW deficit).
  - Mini bidirectional ±3σ deviation bars providing instant visual intuition of statistical significance.
  - Section header labeled `[OBSERVED]` with source `residual_anomaly_detector`.
- **What NOT to Explain:** Do not get bogged down in the exact LightGBM hyper-parameters or the change-point algorithm details. Point out that the anomaly detector isolates the *exact physical component* driving the generation deficit.

---

### Screenshot 3: Atmospheric Attribution & Feeder Peer Isolation
- **Filename:** [`artifacts/evaluation/demo_audit/04_asset_section2_3_environment_peers.png`](../../artifacts/evaluation/demo_audit/04_asset_section2_3_environment_peers.png)
- **Presentation Location:** Slide 2 / Demo Steps 4 & 5 (`/assets/WT-004`)
- **Visual Subject:** Section 2 Environmental Attribution side-by-side with Section 3 Peer Cohort Isolation.
- **What the Audience Should Notice:**
  - Section 2: CAMS dust aerosol index is `0.18 (LOW)`, weather only explains 24% of power deficit, and the verdict states `Equipment Deficit Asserted`.
  - Section 3: WT-004 residual (-3.7%) is compared against 8 identical turbines on Feeder 4B (peer median -1.0%), deviating beyond 88% of its cohort.
- **What NOT to Explain:** Do not recite weather coordinates or raw pyranometer equations. Highlight the twin operational takeaways: *weather does not explain the deficit, and identical peers are generating normally (ruling out grid curtailment).*

---

### Screenshot 4: Techno-Economic Intervention Trade-Offs & Decision Synthesis
- **Filename:** [`artifacts/evaluation/demo_audit/06_asset_section6_7_economics_decision.png`](../../artifacts/evaluation/demo_audit/06_asset_section6_7_economics_decision.png)
- **Presentation Location:** Slide 3 / Demo Steps 7 & 8 (`/assets/WT-004`)
- **Visual Subject:** Section 6 Three-way economic trade-off cards and Section 7 Bounded Local AI Decision Synthesis.
- **What the Audience Should Notice:**
  - Economic comparison: `Act Now` vs `Defer 3 Days` vs `Defer 14 Days`.
  - Stated financial metrics: `Projected Avoidable Exposure: ₹17.42L`, `Inspection & Repair Cost: ₹1.50L`, `Modelled Net Benefit: +₹9.07L`.
  - Honest terminology: `Modelled Net Benefit` and `Projected Avoidable Exposure` (never "guaranteed ROI").
  - Section 7: Calibrated confidence is 72% (<80% threshold), triggering the red **`Human Escalation Required`** banner.
- **What NOT to Explain:** Do not debate specific rupee tariff rates or replacement parts invoices. Emphasize that the economic engine calculates counterfactual trade-offs deterministically before the local AI explains them.

---

### Screenshot 5: Meteorological Crew Dispatch & Closed-Loop Memory Status
- **Filename:** [`artifacts/evaluation/demo_audit/09_crew_dispatch_weather_windows.png`](../../artifacts/evaluation/demo_audit/09_crew_dispatch_weather_windows.png)
- **Presentation Location:** Slide 5 / Demo Steps 11 & 12 (`/work-orders`)
- **Visual Subject:** Operations Console showing site-specific safe weather windows and optimized crew allocation.
- **What the Audience Should Notice:**
  - Meteorological constraints: Kutch Wind shows a **`Safe Window: 6 Hours`** (wind 8.2 m/s < 12 m/s limit), while Charanka Solar shows an **`UNSAFE: 0 Hours`** lockout due to 76% rain probability.
  - Crew routing table: `Kutch-Crew-1` assigned to `WT-004` during the validated 6-hour weather window.
  - Labeling: Explicitly labeled as `Configured Operational Constraints` rather than legal OSHA guarantees.
- **What NOT to Explain:** Do not explain the detailed crew shift timings or vehicle dispatch logic. Focus on the core message: *predictive maintenance is useless if you dispatch crews into unsafe weather; RAI schedules work only when atmospheric conditions permit safe execution.*
