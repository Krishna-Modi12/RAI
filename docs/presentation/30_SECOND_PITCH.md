# Renewable Asset Intelligence (RAI)
## Elevator Pitch Formats (30s, 60s, 90s)

---

### The 30-Second Elevator Pitch
*(Ideal for quick introductions, roving judges, and stage summaries)*

> "Renewable Asset Intelligence turns ambiguous renewable-asset alarms into defensible maintenance decisions.
>
> Instead of stopping at threshold anomaly detection, RAI compares observed generation against physics expectations, atmospheric dust context, feeder peers, and 14 audited academic historical cases. It then models the financial cost of waiting and proposes a human-approved work order for weather-safe crew dispatch.
>
> Our core wind detection is benchmarked on the peer-reviewed CARE dataset with normal accuracy above 0.995; our broader operational decision loop is fully demonstrated with strict evidence boundaries."

---

### The 60-Second Executive Pitch
*(Ideal for 1-minute pitch rounds and formal judge welcomes)*

> "Judges, modern renewable operations suffer from severe alarm fatigue: when a wind turbine or solar inverter underproduces by 20%, fixed-threshold alarms cannot distinguish a failing bearing from a dust storm, a cloud transient, or a grid curtailment order.
>
> Renewable Asset Intelligence solves this by closing the loop between raw telemetry and operational maintenance.
>
> Our pipeline conditions SCADA data against physics expectations, checks satellite aerosol dust levels, isolates the unit against identical feeder peers, and retrieves matching historical cases from 14 audited academic records.
>
> Instead of guessing, our techno-economic engine calculates the Net Present Value of acting now versus deferring, while a bounded local AI synthesizes the evidence under strict calibrated confidence gating. If confidence is below 80%, it forces human escalation.
>
> RAI does not guess, does not hallucinate, and never actuates the plant autonomously: it turns telemetry uncertainty into an auditable, human-governed operational decision."

---

### The 90-Second Technical Pitch
*(Ideal for deep technical Q&A opening and engineering evaluations)*

> "Judges, the central thesis of Renewable Asset Intelligence is that *anomalies are not decisions*.
>
> Most predictive maintenance tools stop at a classifier or an ungrounded LLM wrapper. RAI is an end-to-end, human-in-the-loop operational decision architecture built on strict separation of concerns: **zero numerical math is performed inside an LLM**.
>
> All expected power curves, residual z-scores, CAMS aerosol dust integrals $D(t)$, peer cohort percentiles, and Net Present Value cash flows are computed deterministically in Python.
>
> When turbine WT-004 shows a generator winding anomaly at +12.3σ, RAI checks CAMS atmospheric data to rule out weather, isolates the unit against 8 feeder peers to rule out grid curtailment, and searches 14 audited academic cases to retrieve a matching Kelmarsh protection-trip event at 80% similarity.
>
> Our economic engine models a +₹9.07L net benefit for intervening immediately, and our quantized local Needle 2 reasoner explains the evidence packet to the operator. The operator approves the ticket, which is dispatched strictly within safe meteorological windows.
>
> In terms of validation: our wind anomaly detection is validated on the CARE Benchmark across 36 commercial turbines with out-of-sample normal accuracy above 0.995 (our internal Gate 2 holdout PR-AUC of 0.822 is a separate, self-graded metric on our own fleet, not a CARE figure). Our closed loop enforces dual-key promotion to ensure synthetic test tickets never pollute real benchmark partitions.
>
> All 554 tests pass offline, and the repository is completely reproducible."
