# Renewable Asset Intelligence (RAI)
## Final 5-Minute Speaker Script

**Audience:** Technical Judges, Energy Systems Evaluators, Machine Learning Researchers  
**Delivery Style:** Confident, technical, measured, scientifically honest. Avoid marketing hype.  
**Total Target Duration:** 4 minutes 45 seconds  

---

### [0:00 – 0:30] — The Problem: Ambiguous Telemetry & Alarm Fatigue

*(Slide 1: The Problem)*

> "Judges, modern renewable operations suffer from a fundamental problem: generation deficits are ambiguous by construction.
>
> When a wind turbine or solar inverter drops 20% below rated capacity, what caused it? Is it bearing spalling inside the gearbox? Atmospheric dust ingress? A passing monsoon cloud? A utility curtailment order? Or simply a drifting sensor?
>
> Existing SCADA systems rely on static threshold alarms. Because they cannot separate external weather from internal physical degradation, operators face two severe failures: alarm fatigue during routine weather events, and catastrophic forced outages when genuine faults go unaddressed.
>
> Operators don't need more alarms. They need defensible decisions."

---

### [0:30 – 1:05] — The RAI Thesis: The 8-Factor Decision Stack

*(Slide 2: The RAI Difference)*

> "Renewable Asset Intelligence does not stop at detecting an anomaly. It is an operational decision engine that converts noisy SCADA telemetry into defensible, financially quantified interventions.
>
> We do this through an eight-stage sequential pipeline:
> First, we compute physics-grounded expectations conditioned on ambient weather.
> Second, we calculate statistical residuals and persistence.
> Third, we attribute atmospheric dust using CAMS satellite integrals.
> Fourth, we isolate the asset against identical feeder peers to rule out site-wide events.
> Fifth, we query 14 audited academic historical cases with contrastive explanations.
> Sixth, we quantify the Net Present Value of acting now versus deferring.
> Seventh, a bounded local AI explains the evidence under calibrated confidence gating.
> And eighth, a licensed human operator reviews and authorizes the work order for safe crew dispatch."

---

### [1:05 – 1:45] — Architecture: Strict Separation of Math and AI

*(Slide 3: Technical Architecture)*

> "Here is our core engineering architectural principle: *Zero numerical math is performed inside an LLM.*
>
> All physical models, LightGBM predictions, residual z-scores, CAMS aerosol integrals, and economic cash flows are computed deterministically in Python and DuckDB.
>
> Our local AI engine—a quantized Needle 2 model running in-process—receives a strictly structured Evidence Packet. Its role is solely synthesis and explanation. If its calibrated confidence falls below 80%, the system abstains and forces human escalation.
>
> Furthermore, the AI cannot issue physical control setpoints to the plant. All actions are human-governed work orders, dispatched within meteorologically safe windows, and fed back through a quarantined closed loop."

---

### [1:45 – 2:30] — Scientific Evidence: What is Validated vs. Demonstrated

*(Slide 4: Evidence & Scientific Honesty)*

> "Before I show you the running system, let me state plainly what is scientifically validated and what is not:
>
> On wind anomaly detection, our model is **validated** on the peer-reviewed CARE Benchmark across 36 commercial turbines, achieving an out-of-sample normal classification accuracy exceeding 0.995 and an embargoed, leak-free PR-AUC of 0.822.
>
> On cross-farm transfer, our target-normal calibration is **validated**, recovering 106.3% of baseline performance without target retraining.
>
> On historical retrieval, our k-NN vector memory is **validated** across 14 curated academic records from CARE, Kelmarsh, and NREL PVDAQ.
>
> Our local AI reasoner, techno-economics, and closed-loop lifecycle are **demonstrated** on internal operational test fixtures.
>
> And we explicitly disclose what is **not validated**: independent solar component failure prediction is unclosed, and we have zero live commercial plant connections. We do not claim what the data cannot support."

---

### [2:30 – 4:30] — Live System Demonstration: The WT-004 Journey

*(Switch to live browser at `http://localhost:3000`)*

> "Let's see this in action on our 42-asset operational console.
>
> At the top of Fleet Command, our 30-day modeled revenue exposure is ₹1.21 Crores across 42 generation units. Look at the Priority Queue: instead of an unranked alarm flood, assets are sorted by Expected Financial Exposure weighted by risk.
>
> WT-004 is at the top of the queue with an elevated risk score and a dominant generator winding temperature anomaly. Let's click 'Investigate'.
>
> On the WT-004 Deep Dive:
> In Section 1, our physics model expects 1,883 kW. The active power dropped, and the generator winding temperature is deviating at **+12.3σ**, or +13.7°C above expected thermal equilibrium.
>
> But is it weather? In Section 2, the CAMS aerosol check confirms dust exposure is LOW; ambient conditions explain only 24% of the deficit. The engine asserts an *Equipment Deficit*.
>
> Is it grid curtailment? In Section 3, WT-004's residual is -3.7% against a peer median of -1.0% across 8 identical turbines on Feeder 4B. WT-004 deviates further than 88% of the cohort. Site-wide curtailment is ruled out.
>
> Now historical precedent: In Section 4, we toggle 'REAL ONLY' to query our 14 audited academic records. The top match is a real Kelmarsh cooling trip matching at 80% similarity. The card tells the operator exactly *why* it matched and *what differs*.
>
> In Section 6, the Techno-Economic Engine evaluates the operational trade-off: Act Now vs. Defer 3 Days vs. Defer 14 Days. Acting now prevents ₹17.42 Lakhs in projected exposure for a modeled Net Benefit of +₹9.07 Lakhs.
>
> In Section 7, the local reasoner synthesizes the packet. Notice that because calibrated confidence is below our 80% threshold, it flags 'Human Escalation Required'.
>
> I click 'Propose Work Order' in Section 8. The proposal is staged.
>
> In the Operations Console under `/work-orders`, the operator reviews the ticket and authorizes inspection.
>
> Under the 'Crew Dispatch & Weather Windows' tab, RAI checks Open-Meteo forecasts against configured safety limits. Kutch Wind has a 6-hour safe window below our 12 m/s climb limit, while Charanka Solar has a 0-hour window due to rainfall. Crew 1 is assigned.
>
> Finally, in the 'Closed-Loop Learning' tab: when technicians log field teardown findings, only records verified with physical evidence can enter the `EXTERNAL_REAL` partition. All demo and test tickets are quarantined as `INTERNAL_SYNTHETIC`—currently 122 records—ensuring zero contamination of our 14 academic benchmarks."

---

### [4:30 – 5:00] — Impact, Honest Boundaries & Closing

*(Slide 5: Why It Matters)*

> "Judges, the contribution of Renewable Asset Intelligence is not a new deep-learning architecture or an autonomous plant controller.
>
> Its contribution is closing the gap between raw telemetry uncertainty and defensible human decision-making:
> We ground alarms in physics, attribute atmospheric weather, isolate peers, search audited precedents, quantify financial trade-offs, and enforce human governance with clean evidence boundaries.
>
> All 554 tests pass offline. The entire application is fully reproducible from our repository.
>
> Thank you, and I welcome your questions."
