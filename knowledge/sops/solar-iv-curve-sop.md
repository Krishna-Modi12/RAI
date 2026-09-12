---
doc_id: solar-iv-curve-sop
title: I-V Curve Tracing and Interpretation
asset_type: solar_inverter
component: dc_string
kind: sop
version: "1.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string-inverter PV
> plant. This is not manufacturer documentation and is not attributable to any OEM. All
> figures are project-defined engineering assumptions unless a section states a measured
> source.

## 1. Scope and trigger conditions

This SOP defines how a technician captures an I-V (current-voltage) curve on a DC source
circuit at the Charanka Solar Park (`INV-001` .. `INV-024`), how that curve is translated to
Standard Test Conditions (STC), and what each curve shape permits the technician to conclude.
I-V tracing is the **confirmatory** measurement in this corpus: it runs only after a string
deficit has survived the rule-out checks in section 3, and its output is the evidence that
authorises a physical intervention.

Trace when a string channel sits more than 5 % below its inverter peer median on normalised
current for 3 consecutive clear-sky days; when an inverter performance-ratio deficit survives
a cleaning cycle; at commissioning or reconnection after a repair; on the annual sample audit
(10 % of circuits per inverter); or when `solar-string-fault-sop` has localised a deficit to a
circuit but not to a cause.

## 2. Reference array constants

| Parameter | Value | Unit |
|---|---|---|
| Inverter AC rating / DC capacity (ratio 1.25) | 250 kW / 312.5 | kWp |
| Monitored string channels per inverter | 20 | - |
| Source-circuit Voc / Vmp / Imp at STC | 820 / 640 / 9.2 | V, V, A |
| Source-circuit Isc at STC, assumed | 9.8 | A |
| Source-circuit MPP power, derived (640 x 9.2) | 5,888 | W |
| Modules in series per circuit, assumed | 22 | - |
| Module class, derived | 268 Wp, Voc 37.3 V, Vmp 29.1 V | - |
| Bypass diodes per module, assumed | 3 | - |
| Fill factor, derived (5,888 / (820 x 9.8)) | 0.733 | - |
| Temperature coefficients: Pmp / Voc / Isc | -0.004 / -0.0030 / +0.0005 | /K |
| NOCT | 45 | degC |
| Solar tariff | 2.45 | INR/kWh |

Nameplate reconciliation, stated because the arithmetic must be reproducible: 312.5 kWp at
5,888 W per source circuit gives **53 source circuits per inverter**, wired into the 20
monitored combiner channels as 13 channels of three circuits and 7 channels of two. SCADA
reports the channel sum; the I-V tracer measures **one isolated source circuit**. Never
compare a raw tracer reading against a SCADA channel current without dividing by the number
of parallel circuits on that channel.

## 3. Rule out first — mandatory before any trace is treated as a fault

An I-V trace is expensive in crew time and it is easy to misread. Complete all three checks
and record the result. If any check is unresolved, **stop**: no equipment fault may be
asserted.

1. **Instrumentation.** Run `scada-sensor-validation-sop`. Verify the plane-of-array
   irradiance sensor against the spare reference cell, the back-of-module RTD against a
   handheld probe, and the string current transducer against a clamp meter. A reference cell
   that has drifted 5 % produces an apparent 5 % Isc deficit on every healthy circuit in the
   plant. Sensor drift is the single most common cause of a fleet-wide "deficit" that is not
   there.
2. **Environment and curtailment.** Confirm no active export limit for the interval under
   review (`grid-curtailment-policy`) and no inverter thermal derate (`solar-inverter-thermal-sop`:
   derate begins above 45 degC heatsink temperature, hard trip at 75 degC). A derating
   inverter displaces its MPP operating point and every string underneath it reads low
   together, with no string-to-string spread.
3. **Soiling.** Check days since the last cleaning and the last rainfall above 4 mm/day.
   At the Charanka dry-season accumulation rate of 0.15 - 0.35 %/day, 30 days without rain is
   a 4.5 - 10.5 % loss **on every string equally**. Uniform loss is a cleaning finding, not a
   string finding — refer to `solar-soiling-cleaning-sop` before tracing.

Only a deficit that is *specific to one circuit or one group of circuits*, after all three
checks pass, justifies a trace for fault diagnosis.

## 4. Equipment and safety

Equipment: I-V curve tracer rated at or above 1,000 V DC / 20 A DC with at least 100 captured
points per sweep; calibrated reference cell of the same cell technology as the array, mounted
coplanar with the modules within 1 m of the circuit under test; adhesive type-K back-of-module
thermocouple; 1,000 V DC clamp meter; 1,000 V insulation resistance tester (used only under
`solar-string-fault-sop`); combiner fuse puller.

Safety rules, non-negotiable:

- PV source circuits are energised whenever illuminated. There is no isolating the module.
- Open the circuit at the combiner **fuse or DC switch**, never by pulling a current-carrying
  connector. DC arcs do not self-extinguish.
- Two persons minimum. Arc-rated gloves and face shield while a combiner door is open.
- Do not trace with wet modules or standing water at the combiner.
- Charanka ambient exceeds 42 degC in May and June. Limit continuous combiner work to 30 min
  and rotate personnel; heat stress, not electricity, causes most incidents on this site.

## 5. Valid measurement conditions

A trace taken outside these bounds is void. Record the conditions with every capture.

| Condition | Requirement | Reason |
|---|---|---|
| Plane-of-array irradiance | >= 700 W/m2 | Translation error grows sharply below this |
| Irradiance stability | +/- 2 % over the 60 s before and during the sweep | Cloud-edge transients distort Isc |
| Sky state | Clear, no cloud within 20 deg of the sun | Prevents irradiance enhancement |
| Time window | 10:00 - 15:00 local; incidence angle < 40 deg | Limits reflection losses |
| Module back-surface temperature | Measured, +/- 2 degC, stable 15 min | Drives the Voc correction |
| Wind speed | < 5 m/s | Keeps module temperature stable during the sweep |
| Surface state | Clean, or soiling state documented | Soiling is indistinguishable from low irradiance in the curve |

## 6. Translation to STC

STC is 1,000 W/m2, 25 degC cell temperature, AM1.5. Apply the simplified translation below
(IEC 60891 procedure 1, with the series-resistance term folded into the fill-factor check
rather than the voltage correction). `G` is measured irradiance in W/m2 and `T` the measured
back-of-module temperature in degC; cell temperature is taken as back-surface temperature
+ 2 K.

```
Isc_STC = Isc_meas x (1000 / G) / (1 + 0.0005 x (T + 2 - 25))
Voc_STC = Voc_meas / (1 - 0.0030 x (T + 2 - 25))
Pmp_STC = Pmp_meas x (1000 / G) / (1 - 0.004 x (T + 2 - 25))
```

Worked example. A trace at G = 880 W/m2 and T = 52 degC (cell 54 degC) returns Isc 8.72 A,
Voc 748 V, Pmp 4,410 W. Translated: Isc_STC = 8.72 x 1.136 / 1.0145 = **9.77 A**;
Voc_STC = 748 / (1 - 0.087) = **819 V**; Pmp_STC = 4,410 x 1.136 / (1 - 0.116) = **5,668 W**.
Against the 5,888 W reference this is a 3.7 % deficit with nominal Isc and Voc — a fill-factor
finding, not a module-count finding.

The translation is trusted to roughly +/- 3 % combined tracer and reference-cell uncertainty.
Deficits inside 3 % are not evidence of anything.

## 7. Shape diagnosis

Read the shape before reading the numbers. The four curve parameters — Isc, Voc, fill factor,
and the presence of steps — map to distinct physical causes.

| Observed shape | Quantitative gate (STC-translated) | Physical cause | Confirming check |
|---|---|---|---|
| Isc reduced, Voc normal, curve shape preserved | Isc < 9.3 A (-5 %), Voc within 2 %, FF >= 0.72 | Uniform soiling, uniform shading, or irradiance/reference-cell mismatch | Clean a 2-module coupon and retrace; if the deficit clears, it is soiling |
| Voc reduced, Isc normal | Voc deficit ~1.5 % per shorted bypass diode, ~4.5 % per failed module | Module failure, shorted bypass diode, or PID | Count the deficit in module steps; PID shows broad Voc **and** FF loss on circuits nearest the negative pole |
| Stepped or double-kneed curve | Any discontinuity > 3 % of Isc | Partial shading, a soiled or cracked substring, or a bypass diode conducting in service | Inspect for shade at trace time; IR scan for a hot substring |
| Fill factor reduced, shallow slope near Isc | Current loss > 4 % between 0 V and 410 V (0.5 x Voc) | Shunt paths: cell cracks, moisture ingress, ground-fault leakage | Measure insulation resistance; a shunt that grows with humidity is moisture ingress |
| Fill factor reduced, steep slope near Voc | Rs_eff > 11 ohm against a 7.0 - 8.5 ohm nominal | Series resistance: corroded connectors, undersized or damaged cable, degraded solder bonds | Thermal-image every connector under load; a hot MC4 is conclusive |
| Isc and Voc both low, FF normal | Both > 5 % low | Invalid measurement conditions, not a fault | Re-check irradiance stability and retrace |

Two notes the agent must respect. First, a stepped curve is only a *fault* if the shade is
not real — trace time and shade survey must both be recorded, because a tower shadow at 15:10
produces a textbook diode step on a healthy circuit. Second, reduced Isc with a perfect curve
shape is a **system-level** finding; it never justifies opening a combiner.

## 8. Pass / fail criteria and repeat measurement

Reference values are the STC source-circuit constants in section 2. Module manufacturing
tolerance is assumed 0 / +3 %, and measurement uncertainty +/- 3 %.

| Result | Pmp_STC | Action |
|---|---|---|
| Pass | >= 5,594 W (within -5 %) | Record and close |
| Watch | 5,417 - 5,594 W (-5 % to -8 %) | Re-trace at the next scheduled visit; no intervention |
| Fail | < 5,417 W (below -8 %) | Refer per section 9 |

Parameter gates applied independently of Pmp: Isc_STC below 9.3 A, Voc_STC below 804 V
(-2 %), or FF below 0.70 each constitute a fail regardless of total power.

Repeat requirement. Capture **three consecutive sweeps within 5 minutes**. If the Pmp spread
exceeds 1.5 %, irradiance was unstable — void all three and retrace. Then trace one known-good
peer circuit on the same inverter within 10 minutes, under the same sky. The paired comparison
cancels most translation and reference-cell error, and the peer ratio, not the absolute
number, is what enters the evidence packet.

## 9. Referral, escalation and economics

- Any parameter fail, step, or suspected open circuit: `solar-string-fault-sop` for isolation,
  fuse, polarity and ground-fault testing.
- Uniform Isc deficit across all traced circuits on an inverter: `solar-soiling-cleaning-sop`.
- Deficit correlating with heatsink temperature or afternoon-only: `solar-inverter-thermal-sop`.
- Alarm routing and owner assignment: `alarm-response-matrix`. Intervention economics:
  `om-economics-policy`.

Decision economics, at 2.45 INR/kWh and an assumed specific yield of 1,750 kWh/kWp/yr. One
source circuit (5.89 kWp) at -8 % loses about 824 kWh/yr, or **INR 2,019/yr** — a scheduled
visit item, never a dedicated mobilisation. A whole inverter (312.5 kWp) at -8 % loses about
43,750 kWh/yr, or **INR 107,000/yr** — act inside 7 days. The order-of-magnitude gap between
these two is why circuit-level findings are batched and inverter-level findings are not.

## 10. Record and evidence

Every trace is stored as an `iv_trace` artifact carrying: asset id, combiner channel and
circuit id, UTC timestamp, G, T, the raw point array, the STC-translated Isc/Voc/Pmp/FF,
Rs_eff, Rsh slope, the three-sweep spread, the peer-circuit ratio, and the section 3 rule-out
results. A trace without the rule-out results attached is not admissible evidence and the
agent must treat it as absent.

## Related documents

- `solar-dc-string-system` — array topology, combiner layout and string constants.
- `solar-inverter-system` — MPPT behaviour and the inverter-side view of a DC deficit.
- `solar-string-fault-sop` — isolation and fault localisation after a failed trace.
- `solar-soiling-cleaning-sop` — soiling rate, cleaning triggers and the coupon method.
- `solar-inverter-thermal-sop` — heatsink derate and thermal confounders.
- `scada-sensor-validation-sop` — run **before** accepting any deficit as real.
- `grid-curtailment-policy` — export limits that mimic a DC fault.
- `om-economics-policy` — intervention cost and loss assumptions.
- `alarm-response-matrix` — owner, response time and escalation path.
- `incident-log-solar-inverter` — recorded cases, including false positives.
