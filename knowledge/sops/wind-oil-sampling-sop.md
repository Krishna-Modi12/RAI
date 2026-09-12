---
doc_id: wind-oil-sampling-sop
title: Gearbox Oil Sampling and Laboratory Analysis
asset_type: wind_turbine
component: gearbox
kind: sop
version: "1.4"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for gearbox oil sampling and laboratory
> interpretation on a generic 2 MW geared wind turbine. This is not manufacturer
> documentation and is not attributable to any OEM. All figures are project-defined
> engineering assumptions unless a section states a measured source.

## 1. Scope and purpose

This SOP covers extraction of a representative oil sample from the gearbox of `WT-001` ..
`WT-018` at Kutch Wind Farm, the laboratory test suite requested, and the caution and action
limits that convert a laboratory report into a field decision.

The reference lubricant is ISO VG 320 synthetic PAO gear oil in a 320 L sump, filtered
10 um inline and 5 um offline (kidney loop), per `wind-gearbox-system` section 2. Every limit
below is stated against that fill; a different lubricant invalidates section 7.

Oil analysis is a **confirming** modality. It is slow (days) but precise about wear
metallurgy and nearly immune to the environmental confounds that corrupt power and thermal
residuals. Vibration is fast and sensitive but ambiguous. Neither alone authorises a gearbox
intervention.

## 2. Rule out first — before the sample is even scheduled

An oil sample is requested because something looked abnormal. Establish that the abnormality
is real before spending a crew visit on it.

1. **Validate the instrumentation.** Run `scada-sensor-validation-sop` against
   `gearbox_oil_temp_c`, `drivetrain_vibration_mms`, `nacelle_temp_c` and `wind_speed_ms`.
   A frozen RTD, a step-changed accelerometer or a drifting anemometer produces a convincing
   thermal or power residual on a healthy gearbox. A single signal moving alone is a sensor
   hypothesis, not a wear hypothesis.
2. **Rule out the environment and the grid.** Check ambient and nacelle temperature, cooler
   fin fouling, fan state and dust loading. Oil temperature rises roughly 0.35 degC per
   1 degC of ambient rise at constant load; a thermal residual that tracks `nacelle_temp_c`
   and vanishes overnight is a cooling-capacity finding, not wear. Confirm the machine was
   not curtailed or derated over the window, per `grid-curtailment-policy`.
3. **Check the peers.** If several of `WT-001` .. `WT-018` shifted together in the same wind
   and temperature conditions, the cause is site-wide, not one gearbox.
4. **Only then sample.** Record on the request form which checks were completed and their
   outcome. The laboratory result is interpreted against that context, not in isolation.

Contamination is the oil-analysis analogue of a sensor fault: a dirty bottle, an unflushed
valve or an open-sump dip produces a spectacular silicon and particle-count result on a
healthy gearbox. Section 4 exists to prevent that, and a suspect sample is resampled before
it is acted on — see `INC-2025-003-anemometer-drift-false-alarm`.

## 3. Sampling point and equipment

| Item | Specification |
|---|---|
| Primary sampling point | Live-zone minimess valve on the pressurised lubrication return line, downstream of the pump and **upstream** of the 10 um inline filter |
| Secondary point | Offline kidney-loop return line, upstream of the 5 um element |
| Prohibited points | Drain plug, sump top dip, filter housing drain, any static reservoir |
| Bottle | 250 mL clean certified bottle, cleanliness grade at least one ISO 4406 code better than the target |
| Volume | 150 mL primary, 100 mL retained sealed sample |
| Flush volume | 250 - 300 mL discarded before capture |
| Machine state | Running, at least 45 min above 60 % rated power |

The 45 min dwell is one gearbox thermal time constant (~42 min). A cold or recently-started
machine yields settled oil that under-reports suspended wear debris. Never sample a turbine
stopped for more than 30 min; tag it for the next production window. Drain-plug samples are
prohibited because they bias every metric the same way — high particle count, high PQ, high
silicon — and destroy the trend against previous samples.

## 4. Procedure and contamination avoidance

1. Confirm the turbine is running per section 3. Record `power_kw`, `rotor_rpm`,
   `gearbox_oil_temp_c`, `nacelle_temp_c` and operating hours at the moment of capture.
2. Wipe the valve body and fitting clean; remove dust before connecting, not after.
3. Fit a **new** single-use sampling tube to the minimess valve.
4. Flush 250 - 300 mL into a waste container to clear line dead-volume.
5. Without breaking flow, fill the primary bottle to 80 %, then the retained bottle. Cap each
   immediately; never set an open bottle down.
6. Keep bottles upright, out of direct sun, below 50 degC in transit.
7. Label with asset id, UTC date and time, operating hours, oil charge date, oil brand and
   grade, top-up volume since last sample, and the reason for sampling (routine / vibration
   escalation / thermal residual / post-intervention).
8. Dispatch within 24 h of capture.

An unlabelled or partially labelled sample is discarded, not interpreted — trend value
depends entirely on knowing hours-on-oil and hours-on-machine.

## 5. Sampling frequency by condition tier

| Tier | Trigger | Sampling interval | Tests requested |
|---|---|---|---|
| T0 routine | No open finding | 6 months | Full suite |
| T1 watch | Vibration Zone B, or a persistent thermal residual after section 2 clears | Within 7 days, then every 60 days while open | Full suite + on-site screen |
| T2 alarm | Vibration Zone C, or an oil caution limit exceeded | Within 48 h, then every 30 days | Full suite, expedited |
| T3 trip / post-event | Vibration Zone D, chip detector activation, or sustained `gearbox_oil_temp_c` above the 75 degC warning limit | Immediately, machine stopped | Full suite + debris morphology |
| Post-intervention | Oil change, filter change, bearing replacement | At 250 operating hours after return to service | Full suite, new baseline |
| New fill | Any fresh charge | Before commissioning the charge | Viscosity, cleanliness, water, additive fingerprint |

T1 and above are field-visit tiers. Zone definitions and the underlying vibration thresholds
are in `wind-gearbox-system` section 5 and `wind-vibration-analysis-sop`.

## 6. Cleanliness, particle count and ferrous density

Cleanliness is reported as ISO 4406 codes at 4 um / 6 um / 14 um.

| Metric | Target | Caution | Action |
|---|---|---|---|
| ISO 4406 code (in service) | 16/14/11 | 18/16/13 | 19/17/14 |
| ISO 4406 code (new fill, pre-commissioning) | 15/13/10 | 16/14/11 | 17/15/12 |
| PQ index (ferrous density, unitless) | < 20 | 50 | 100 |
| PQ rate of change | < 5 per 30 days | 15 per 30 days | 30 per 30 days |

A 19/17/14 result triggers an inline and offline element change and a resample at 30 days.
A rising particle count with a **flat** PQ index is non-ferrous ingress — breather and seals,
not gears. A rising PQ index with a flat particle count is fine ferrous wear, and is the
result that corroborates a vibration finding.

## 7. Elemental spectroscopy, physical and chemical limits

Elemental results are ppm by ICP. ICP under-reports particles above roughly 5 um, so a low
elemental result never overrides a high PQ index or a chip detector deposit.

| Element | Caution (ppm) | Action (ppm) | Implicates |
|---|---|---|---|
| Fe (iron) | 60 | 100 | Gear tooth and bearing raceway wear; the primary wear metal |
| Cu (copper) | 25 | 40 | Bearing cage, bushing, thrust washer, or oil cooler tube corrosion |
| Cr (chromium) | 8 | 15 | Bearing raceway and roller alloy — with Fe, strongly indicates rolling-element spalling |
| Ni (nickel) | 5 | 10 | Alloy gear steel, deep case wear; rarely rises without Fe and Cr |
| Sn (tin) | 8 | 15 | Bearing overlay or cage plating, often the earliest cage-distress metal |
| Si (silicon) | 25 | 40 | Abrasive dust ingress (Kutch dust season) or anti-foam additive; confirm against breather condition before calling ingress |
| Na (sodium) | 20 | 35 | Coolant or water-borne contamination, or an additive carry-over |

| Property | New-oil reference | Caution | Action |
|---|---|---|---|
| Viscosity at 40 degC | 320 cSt | +/- 10 % (288 - 352) | +/- 20 % (256 - 384) |
| Viscosity at 100 degC | 38 cSt | +/- 10 % | +/- 20 % |
| Viscosity index | 155 | < 140 | < 130 |
| Water content | < 100 ppm | 300 ppm | 500 ppm |
| Acid number (AN) | 0.5 mg KOH/g | +0.3 over new | +0.5 over new, or 1.5 absolute |
| Additive elements (Zn, P, Ca, Mg) | fingerprint of new fill | < 80 % of new | < 70 % of new |

A viscosity **rise** with a rising acid number is oxidative thickening driven by sustained
high oil temperature — check the cooler before blaming the oil. A viscosity **fall** is
unusual in a PAO gear oil; treat it as a suspected wrong-grade top-up and check the top-up
log. Water above 300 ppm halves rolling-element bearing life in the project planning model
and is most often a monsoon-season breather desiccant failure. Additive depletion below 70 %
is an oil-change trigger on its own, independent of every wear metal.

## 8. Reading oil against a vibration finding

This is the table the RAI agent uses to combine the two modalities.

| Vibration | Oil (Fe, Cr, PQ) | Conclusion | Action |
|---|---|---|---|
| Elevated | Elevated | Confirmed mechanical wear | Inspect within 72 h per `wind-gearbox-inspection-sop`; plan per `wind-bearing-replacement-sop` |
| Elevated | Normal | Unconfirmed. Sensor fault, resonance, misalignment, or wear too early to shed measurable debris | Validate sensor, capture a portable spectrum, resample at 30 days. Do not order a gearbox opening |
| Normal | Elevated | Wear present without a broadband signature — early pitting or a slow planetary-stage progression | Escalate sampling to T1, book a spectrum capture, hold the machine in service |
| Normal | Normal | No finding | Return to T0 |
| Either | High Si, normal Fe/Cr | Ingress, not wear | Breather, seals and filter elements; not a drivetrain order |

The second row protects the budget: vibration alone is never sufficient grounds to open a
gearbox — see `incident-log-wind-gearbox`.

## 9. Turnaround, records and escalation

| Step | Expectation |
|---|---|
| Capture to dispatch | 24 h |
| Standard laboratory turnaround (T0, T1) | 5 working days from receipt |
| Expedited turnaround (T2, T3) | 48 h from receipt |
| On-site screen (portable water + ferrous density kit) | Result within 2 h of capture, T1 and above |
| Report to RAI knowledge store | Same day as receipt |
| Retained sample hold period | 12 months |

The on-site screen exists because a 5-day turnaround is too slow for a Zone C decision. It is
indicative only, never overrides the laboratory report, and is recorded as provisional in the
evidence packet.

Escalation follows `wind-gearbox-system` section 8 and `alarm-response-matrix`. Any action
limit exceeded is owned by the site reliability engineer, who orders an inspection within
72 h plus a confirming resample. Two consecutive samples above an action limit, or one action
limit with a corroborating vibration escalation, moves ownership to the O&M manager and
triggers an intervention plan costed under `om-economics-policy`. Laboratory analysis is
assumed at INR 6,500 per sample against an inspection cost of INR 85,000 and an unplanned
gearbox failure cost of INR 4,500,000; the programme pays for itself on a single avoided
unplanned failure across the 18-turbine fleet.

## Related documents

- `wind-gearbox-system` — machine constants, alarm limits, lubrication schedule.
- `wind-gearbox-inspection-sop` — the field inspection this SOP triggers.
- `wind-vibration-analysis-sop` — the modality oil analysis confirms or refutes.
- `wind-bearing-replacement-sop` — the intervention once wear is confirmed.
- `scada-sensor-validation-sop` — run **before** accepting any exceedance as real.
- `alarm-response-matrix` — response times and ownership by alarm class.
- `om-economics-policy` — costing of inspection, planned and unplanned intervention.
- `grid-curtailment-policy` — curtailment context for a power or thermal residual.
- `incident-log-wind-gearbox` — worked cases combining oil and vibration evidence.
