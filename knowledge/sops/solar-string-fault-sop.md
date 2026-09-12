---
doc_id: solar-string-fault-sop
title: String Outage and DC Fault Diagnosis
asset_type: solar_inverter
component: dc_string
kind: sop
version: "1.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string inverter and its
> DC array. This is not manufacturer documentation and is not attributable to any OEM. All
> figures are project-defined engineering assumptions unless a section states a measured source.

## 1. Scope and reference array

This SOP covers locating a DC-side fault on the Charanka Solar Park inverters
(`INV-001` .. `INV-024`): string outage, partial string degradation, ground fault, high
resistance joints and arc faults. It ends at the point where the defect is identified and the
channel is safely restored or locked out.

| Parameter | Value | Unit |
|---|---|---|
| Inverter AC rating | 250 | kW |
| DC/AC ratio | 1.25 | - |
| DC array per inverter | 312.5 | kWp |
| Monitored string channels per inverter | 20 | - |
| DC capacity per channel | 15.6 | kWp |
| Source circuit Voc at STC | 820 | V |
| Source circuit MPP voltage | 640 | V |
| Source circuit current at STC | 9.2 | A |
| Array MPP current at STC (312.5 kWp / 640 V) | 488 | A |
| Module power temperature coefficient | -0.004 | /K |
| NOCT | 45 | degC |

**Array build assumption.** A *channel* is one monitored combiner position group, 1/20 of the
array. A *source circuit* is one series string of modules, 9.2 A at STC. Each channel parallels
two or three source circuits to make up its 15.6 kWp; the average per-channel STC current is
therefore 24.4 A. Losing one source circuit removes 9.2 A of 488 A, or **1.9 %** of array
current. Losing a whole channel removes **5.0 %**, which is 15.6 kWp DC and 12.5 kW AC at
clear-sky peak. This assumption exists so the worked criteria below are reproducible; see
`solar-dc-string-system` for the array topology.

Voc rises as the module cools. A project assumption of -0.0030 /K for Voc gives roughly 860 V
at a 10 degC winter-morning module temperature. **Treat every DC conductor as live at 860 V.**

## 2. Rule out first — mandatory before any DC work

Do not open a combiner box on the strength of a power deficit alone. Four non-fault causes
produce a convincing DC current deficit on a healthy array. Clear all four, in writing, first.

| Candidate cause | Check | Discriminating observation |
|---|---|---|
| Dead string-current sensor | `scada-sensor-validation-sop` | One `string_current_a` channel reads 0 A but total `dc_current_a` and `ac_power_kw` did **not** fall by the matching 5 %. The channel is healthy; the shunt or Hall sensor is dead. This is the most common false string outage. |
| Soiling or dust event | Soiling trend, last rainfall, peer inverters | Common-mode loss across all 20 channels and across neighbouring inverters. See section 3 and `solar-soiling-cleaning-sop`. |
| Grid curtailment or power setpoint | `grid-curtailment-policy` | All channels fall together **and** `dc_voltage_v` moves *up* off MPP toward Voc. A string outage leaves voltage within 1 %. |
| Inverter thermal derate | `solar-inverter-thermal-sop` | `heatsink_temp_c` above 45 degC, all channels reduced proportionally, loss tracks the afternoon ambient peak and clears overnight. |

Also confirm `poa_irradiance_wm2` is valid and that no new physical shading object (a stacked
pallet, a parked vehicle, vegetation) has appeared in the row. Only when all of these are
excluded is a DC fault asserted and a crew authorised.

## 3. The step signature: outage versus soiling

Both a string outage and soiling reduce DC current at near-constant DC voltage. Voltage is set
by the series module count, which neither event changes, so "current down, voltage flat" alone
proves nothing. Three properties separate them.

| Property | String outage | Soiling |
|---|---|---|
| Shape | Step, complete inside one 15-min sample | Monotone ramp over days |
| Magnitude rate | 5.0 % (channel) or 1.9 % (source circuit) instantly | 0.15 - 0.35 %/day, i.e. at most 0.0055 % per 15-min sample |
| Spatial extent | Differential: one channel, one inverter | Common-mode: all 20 channels, all neighbouring inverters |
| Response to rain | None | Substantially reset by rainfall above 4 mm/day |
| Voltage | Unchanged, within 1 % | Unchanged, within 1 % |

**Step test.** A fall of 3 % or more in irradiance-normalised channel current inside one 15-min
interval, not reproduced on peer inverters, is a step. Soiling cannot physically produce it.
Confirm the step persists for at least three consecutive samples before dispatch — a single
sample is a cloud edge or a telemetry gap.

A *voltage* drop with current sustained or slightly raised is a different family: shorted
modules, conducting bypass diodes or a ground fault. Go to sections 6 and 8, not to fuses.

## 4. String current comparison and outlier criteria

Compare the 20 channels of one inverter against each other, never against a nameplate figure.
Validity conditions: `poa_irradiance_wm2` above 400 W/m², POA change under 5 % across the
sample window, sun elevation above 20 degrees, and at least three consecutive 15-min samples.

Compute the ratio `r_i = I_i / median(I_1..I_20)`. The median is used, not the mean, so that a
dead channel does not drag the reference.

| `r_i` | Interpretation | Action |
|---|---|---|
| 0.95 - 1.05 | Normal spread (module tolerance, row position) | None |
| 0.90 - 0.95 | Mild mismatch or localised soiling | Watch; review at next scheduled visit |
| 0.60 - 0.90 | One source circuit open, conducting bypass diode, or partial shading | I-V trace within 14 days, `solar-iv-curve-sop` |
| 0.05 - 0.60 | Partial channel loss, typically one of two or three source circuits | Combiner inspection within 7 days |
| below 0.05 | Full channel outage | Combiner inspection within 72 h |

If **all** channels sit inside 0.95 - 1.05 and the inverter still under-produces, the fault is
not on the DC strings. Return to section 2 and to `solar-inverter-system`.

## 5. Safe DC isolation and combiner fuse checks

A PV array cannot be de-energised in daylight. DC has no natural current zero, so an
interrupted source circuit sustains an arc.

1. Two-person rule. Class 0 (1,000 V) insulated gloves, face shield, insulated tools, arc-rated
   clothing. Fuse pullers only.
2. Command the inverter to STOP at the HMI, then open the AC breaker.
3. Open the inverter DC load-break switch.
4. **Clamp each source circuit and confirm current below 1 A before touching any fuse holder or
   MC4 connector.** Never pull a fuse or unmate a connector under load.
5. Verify with a meter that the string is at open-circuit voltage and unloaded. Expect 770 -
   860 V depending on module temperature.

Fuse checks, holders open and unloaded:

| Observation | Conclusion |
|---|---|
| Fuse open, holder and busbar clean | Replace with 15 A gPV, 1,000 V DC rated. Record the event. |
| Fuse open, second open fuse within 90 days on the same position | Do not simply replace. Look for a ground fault or reverse current — section 6. |
| Fuse intact, zero current at the holder in sunlight | Fault is upstream in the source circuit — section 7. |
| Discoloured holder, melted shell, carbon tracking | Arc damage. Replace holder and both terminations — section 7. |

Fuse rating basis: 9.2 A source circuit x 1.56 = 14.4 A, rounded up to the 15 A gPV standard
size.

## 6. Insulation resistance and ground-fault localisation

Perform with the inverter isolated and its insulation monitor disconnected. Bond array positive
and negative together and measure to earth at 1,000 V DC.

| Riso (312.5 kWp array) | Interpretation | Action |
|---|---|---|
| above 20 MOhm | Healthy | Restore |
| 1 - 20 MOhm | Degraded insulation or moisture ingress | Localise before restoring |
| below 1 MOhm | Inverter blocks start | Do not restore. Locate and repair. |

Localise by bisection: disconnect half the channels, re-measure, keep the half that stays low.
Twenty channels resolve in five measurements. Repeat within the suspect channel at source
circuit level.

**Monsoon caveat.** A Riso that is low in the two hours after rain and recovers above 20 MOhm by
midday is water ingress at a junction box, connector or cable gland — real, but not a module
insulation failure. Record the drying time constant; it is the evidence that distinguishes the
two. A Riso that stays low when the array is dry is a damaged conductor or a failed module
backsheet.

## 7. Connector, cable and arc-fault inspection

Inspect the whole source circuit, not just the terminations:

- **Cross-mated connectors.** Different connector brands mated together are the leading cause of
  high-resistance joints on this site. Verify brand and series match at every pair.
- **Thermal imaging under load**, at above 600 W/m². Any joint more than 20 K above the coolest
  comparable joint on the same combiner at the same current is defective. Any joint above
  90 degC is defective regardless of comparison.
- Cable abrasion at tracker torque tubes, rodent damage at ground level, UV-embrittled ties,
  and unmarked (un-torque-sealed) combiner terminals.

**Arc-fault handling.** DC arcs self-sustain well above 300 V, and this array operates at 640 -
860 V. A series arc shows as erratic, noisy channel current without a clean step, and trips the
AFCI. **Reset an AFCI trip once only.** A second trip on the same channel within 24 h means the
channel is locked out until every connector and fuse holder in it has been thermally imaged and
inspected. Arc faults are dispatched on safety grounds, never on economics.

## 8. I-V curve trace referral

Any channel in the 0.60 - 0.90 band, or any channel whose voltage is low rather than its
current, goes to `solar-iv-curve-sop`. Signature summary for triage only:

| Curve feature | Likely cause |
|---|---|
| Isc reduced, Voc normal, shape intact | Irradiance, soiling or uniform shading |
| Voc down about 5 % per step | One module short-circuited |
| Voc down about 1.7 % per step, with a current shelf | One bypass diode conducting |
| Rounded knee, steep slope at Voc | Series resistance: corroded joint, undersized or damaged conductor |
| Sloped plateau near Isc | Low shunt resistance: cell damage or wet insulation path |

## 9. Restoration and verification

Restore fuses and connectors unloaded, close the DC switch, then start the inverter. Within
30 minutes at above 500 W/m², all four must hold:

1. Repaired channel current within 3 % of the 20-channel median.
2. Array Riso above 20 MOhm.
3. No AFCI or ground-fault event in the following 24 h.
4. Inverter AC power within 2 % of the peer-based clear-sky expectation.

If any check fails, return the channel to lock-out. Record the event in
`incident-log-solar-inverter` and close the alarm under `alarm-response-matrix`.

## 10. Escalation and economics

Lost energy uses the project planning assumption of 4.6 kWh/kWp/day specific yield at Charanka
and the solar tariff of 2.45 INR/kWh (`om-economics-policy`).

| Fault extent | Lost energy | Lost revenue | Response |
|---|---|---|---|
| One source circuit (5.9 kWp) | 27 kWh/day | INR 66/day | Batch to next scheduled visit |
| One channel (15.6 kWp) | 72 kWh/day | INR 176/day | Combiner inspection within 72 h, batched |
| Three or more channels | 216 kWh/day | INR 528/day | Dedicated crew within 48 h |
| Whole inverter (312.5 kWp) | 1,438 kWh/day | INR 3,522/day | Dedicated crew same day |
| Any ground fault or arc fault | Any | Any | Immediate, on safety grounds |

A single string outage does not justify a dedicated mobilisation; the revenue at stake is under
INR 200 per day and a crew trip costs more. The correct behaviour is to detect it reliably,
batch it, and never let it hide inside a soiling trend. That is the whole point of separating
the step from the ramp in section 3.

## Related documents

- `scada-sensor-validation-sop` — run **before** accepting any string outage as real.
- `solar-dc-string-system` — array topology, combiner design and DC tag definitions.
- `solar-inverter-system` — AC side, MPPT behaviour and inverter alarm codes.
- `solar-iv-curve-sop` — curve capture and interpretation.
- `solar-soiling-cleaning-sop` — soiling accumulation rates and washing triggers.
- `solar-inverter-thermal-sop` — derate above 45 degC heatsink, trip at 75 degC.
- `grid-curtailment-policy` — setpoint-driven common-mode deficits.
- `alarm-response-matrix` — alarm ownership and closure.
- `om-economics-policy` — tariffs, crew costs and batching rules.
- `incident-log-solar-inverter` — recorded DC fault cases from this site.
