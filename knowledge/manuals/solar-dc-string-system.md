---
doc_id: solar-dc-string-system
title: DC String and Array Manual
asset_type: solar_inverter
component: dc_array
kind: manual
version: "1.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string-inverter PV
> block. This is not manufacturer documentation and is not attributable to any OEM. All
> figures are project-defined engineering assumptions unless a section states a measured
> source.

## 1. Scope and reference array

This manual describes the DC side of the Charanka Solar Park model: modules, source circuits,
combiner positions, DC cabling and earthing, for asset ids `INV-001` .. `INV-024`. It defines
the DC constants every other solar document in this corpus depends on and, most importantly,
the **current-versus-voltage signature** of each string fault class. That distinction is the
backbone of solar diagnosis here: soiling and irradiance move DC *current*; almost nothing
environmental moves DC *voltage*.

Related documents:

- `solar-inverter-system` — the AC side, MPPT behaviour and inverter alarm limits.
- `solar-string-fault-sop` — the field procedure for a string-level deviation.
- `solar-iv-curve-sop` — IV tracing, the only instrument that separates PID from mismatch.
- `solar-soiling-cleaning-sop` — soiling accumulation, cleaning trigger and rain reset.
- `solar-inverter-thermal-sop` — derate and heatsink limits.
- `scada-sensor-validation-sop` — run this **before** accepting any DC deviation as real.

## 2. Array layout and block structure

| Parameter | Value | Unit |
|---|---|---|
| Inverter blocks | 24 (`INV-001` .. `INV-024`) | - |
| AC rating per block | 250 | kW |
| DC/AC ratio | 1.25 | - |
| DC nameplate per block | 312.5 | kWp |
| Site DC / AC capacity | 7,500 / 6,000 | kWp / kW |
| DC input positions per inverter | 20 (`string_id` 1 .. 20) | - |
| Source circuits per inverter | 50 | - |
| Modules per source circuit | 22 in series | - |
| Modules per block / site | 1,100 / 26,400 | - |
| Mounting | Fixed tilt 22 deg, azimuth 180 deg, 2-in-portrait | - |
| Ground coverage ratio | 0.38 | - |
| LV collection | 4 feeders x 6 inverters, 1.6 MVA 400 V / 33 kV each | - |

**Naming convention.** `string_id` 1 .. 20 identifies an **inverter DC input position**, not a
single series source circuit. Ten positions carry three paralleled source circuits, ten carry
two (30 + 20 = 50). This matters for fault magnitude: losing one source circuit is a
**-33 %** current step on a three-circuit position and a **-50 %** step on a two-circuit
position, never a small deviation.

Row pitch at GCR 0.38 gives no row-to-row shading between 09:00 and 15:30 IST on the winter
solstice. Any repeating current deficit *inside* that window is not row shading.

## 3. Module and source-circuit electrical characteristics

Module is a generic 60-cell crystalline unit with three bypass diodes, one per 20-cell
substring. Nameplate 284 Wp is project-defined so that 1,100 modules close on the 312.5 kWp
design figure.

| Quantity | Module | Source circuit (22 series) |
|---|---|---|
| Pmp at STC (1,000 W/m2, 25 degC cell) | 284 W | 6.25 kWp |
| Voc at STC | 37.3 V | 820 V |
| Vmp at STC | 30.9 V | 680 V |
| Isc at STC | 9.75 A | 9.75 A |
| Imp at STC | 9.2 A | 9.2 A |
| Vmp at 45 degC cell (NOCT) | 29.1 V | 640 V |
| Pmp at 45 degC cell, 1,000 W/m2 | 261 W | 5.75 kWp |
| Power temperature coefficient | -0.004 /K | -0.004 /K |
| Voltage temperature coefficient (assumed) | -0.0029 /K | -0.0029 /K |
| Maximum series fuse / reverse current | 15 A | 15 A |

Cell temperature model used throughout the corpus, from NOCT 45 degC:
`T_cell = T_ambient + 25 x G / 800`, G in W/m2. At 40 degC ambient and 1,000 W/m2 this gives
71 degC cell, the design maximum.

**Clipping is normal, not a fault.** At 55 degC cell the array delivers 275 kW DC at full sun;
250 kW AC at 98.2 % efficiency needs 254.6 kW DC. Clipping therefore begins above roughly
925 W/m2 on a hot afternoon and above roughly 970 W/m2 at 65 degC cell. A flat AC power
ceiling with DC power above it is the designed DC/AC ratio working, and must never be scored
as a power deficit.

## 4. String sizing and the temperature-corrected voltage window

System voltage class is 1,000 V DC. Inverter MPPT window 480 - 900 V, maximum DC input 1,000 V.

| Condition | Cell temp | Voc | Vmp |
|---|---|---|---|
| Coldest first light (4 degC ambient, 200 W/m2) | 10 degC | 856 V | 710 V |
| STC reference | 25 degC | 820 V | 680 V |
| NOCT reference | 45 degC | 772 V | 640 V |
| Design maximum (40 degC ambient, full sun) | 71 degC | 711 V | 589 V |

Design margin on the 1,000 V limit is 13 % against the 870 V worst-case Voc used for sizing
(856 V plus low-irradiance allowance). The full operating MPP band is **589 - 710 V**. A DC
voltage reading outside **560 - 730 V** under load is a defect or a measurement fault, not
weather — go to section 9.

## 5. Combiner box, fusing and DC cabling

Three-circuit positions are combined in an array junction box (AJB) at the table and fused;
two-circuit positions are fused at the inverter input. Fusing is required wherever three or
more circuits are paralleled, because the reverse current a faulted circuit can absorb then
exceeds the 15 A module rating.

| Item | Specification | Limit / action |
|---|---|---|
| Source-circuit fuse | 15 A gPV, 1,000 V DC | 1.5 x Isc = 14.6 A |
| Source-circuit cable | 4 mm2 tinned copper, double insulated | <= 60 m one way |
| AJB feeder cable | 16 mm2 copper | <= 100 m one way |
| Source-circuit voltage drop at Imp | 4.75 V over 120 m loop | 0.70 % |
| Feeder voltage drop at 27.6 A | 5.9 V over 200 m loop | 0.87 % |
| Total DC drop budget | 1.57 % design, 2.0 % maximum | > 2.0 % = re-cable |
| Connector (MC4-type) contact resistance | <= 1.0 mOhm healthy | >= 20 mOhm replace pair |

Voltage drop scales with current, so it is worst at exactly the moment production matters. A
drop that grows year on year at constant current is connector or termination degradation, not
cable ageing.

## 6. Earthing, bonding and insulation resistance

The array is functionally ungrounded; the inverter carries an insulation monitoring device
(IMD) that tests before every start and continuously during operation.

| Measurement | Healthy | Warning | Inhibit / trip |
|---|---|---|---|
| Array insulation resistance `riso_kohm` | > 5,000 kOhm dry | 1,000 kOhm | 600 kOhm start inhibit |
| IEC 62109-2 code floor (20,000 / 312.5 kWp) | - | - | 64 kOhm absolute |
| Module frame to earth grid continuity | <= 0.1 Ohm | - | > 0.1 Ohm rebond |
| Earth grid resistance | <= 1.0 Ohm | - | > 1.0 Ohm remediate |

A post-rain or heavy-dew `riso_kohm` dip to 800 - 2,000 kOhm that recovers within two hours of
sunrise is moisture, not a ground fault. A dip that does not recover by midday, or that recurs
at the same string, is a damaged cable jacket or a wet junction box.

## 7. Degradation mechanisms

**Potential induced degradation (PID).** Shunt paths form in cells nearest the most negative
pole under humid nights and high array-to-earth potential. The signature is **fill-factor
collapse before any midday loss**: at 100 - 200 W/m2 the string performance ratio falls 8 % or
more below the block median while the midday deficit is still under 3 %. It progresses over
months, tracks monsoon humidity, and affects whole source circuits with a gradient along the
series order. Confirm with a dark IV trace per `solar-iv-curve-sop`; mitigate with a
night-time positive-bias recovery unit.

**Cell mismatch and hot spots.** Series cells are current-limited by the weakest cell. Above
about 5 % Imp mismatch the weak cell is driven into reverse bias and dissipates. Thermography
grades by delta-T against the module mean: below 5 K normal; 5 - 20 K watch and re-image in 90
days; 20 K or more at a single cell means an IV trace and module replacement; 40 K or more is
immediate isolation.

**Bypass diodes.** Three per module. A diode failed **short** removes one substring permanently:
string Vmp drops about 10.3 V (one third of 30.9 V) with **current unchanged**. A diode failed
**open** is invisible until that substring is shaded, then it creates a hot spot. Two or more
shorted diodes on one source circuit (-20 V, -3 %) risks dropping the string below the MPPT
window on a hot afternoon.

**Connector degradation.** Contact oxidation and thermal cycling raise joint resistance. At
9.2 A a 20 mOhm joint dissipates 1.7 W and reads 10 K or more above adjacent conductor in
thermography. Loss scales with I squared, so it is invisible at low irradiance and worst at noon.

## 8. Monitored DC tags

| Tag | Unit | Cadence | Role in diagnosis |
|---|---|---|---|
| `string_current_a` (x20) | A | 15 min | Per-input current; the block median of 20 is the peer reference |
| `dc_voltage_v` | V | 15 min | Array MPP voltage; the channel soiling cannot move |
| `dc_power_kw`, `ac_power_kw` | kW | 15 min | Conversion loss and clipping detection |
| `poa_irradiance_wm2` | W/m2 | 15 min | Plane-of-array pyranometer; itself soils, validate first |
| `module_temp_c`, `ambient_temp_c` | degC | 15 min | Temperature correction of expected power |
| `inverter_temp_c` | degC | 15 min | Heatsink; derates above 45 degC, trips at 75 degC |
| `riso_kohm` | kOhm | 15 min | Insulation health |
| `status_code`, `operating_state` | int, str | 15 min | Curtailment and availability context |

## 9. String fault taxonomy: current versus voltage

Every row states the effect at the affected DC input position, at matched irradiance and
module temperature.

| Fault | DC current | DC voltage | Time signature | Discriminator |
|---|---|---|---|---|
| Open source circuit (blown fuse, open connector, broken cell) | Step -33 % or -50 % at one position | Unchanged | Instantaneous step, permanent | One position only, V flat |
| Shorted bypass diode | Unchanged | -10.3 V per diode (-1.5 %) | Step, permanent | V step with I flat |
| Partial shading (vegetation, structure, bird soiling) | Reduced, shaped | Slightly reduced, MPPT may hunt | Repeats at the same solar hour, drifts seasonally | Daily periodicity |
| Uniform soiling | All 20 positions down together, -0.15 to -0.35 %/day cumulative | **Unchanged** | Slow ramp, reset by rain > 4 mm/day | V and `inverter_temp_c` unmoved |
| PID | Mildly reduced | Reduced, worst at low irradiance | Months, humidity correlated | Low-irradiance ratio collapse |
| Connector / joint resistance | Unchanged at source | Drops only under high current | Worsens over years, noon-weighted | Loss proportional to I squared |
| Ground fault | Zero after IMD trip | - | Step to zero, may recover when dry | `riso_kohm` < 600 kOhm |
| Irradiance or module-temp sensor drift | Apparently normal | Normal | Deficit appears in the *model*, not the array | **No** physical tag moves |

Escalation on the per-position deviation from the block median of 20, at
`poa_irradiance_wm2` > 600 W/m2, sustained three consecutive intervals: 5 % is a watch, 12 %
opens `solar-string-fault-sop`, a 30 % or larger step dispatches a crew for an open circuit.

## 10. Rule out first

**Do not authorise any DC intervention until all four of these are closed.** This is the
procedural expression of the RAI design decision that environmental and instrumentation
explanations outrank equipment hypotheses.

1. **Sensor validation.** Run `scada-sensor-validation-sop`. A soiled pyranometer dome, a
   detached module-temperature RTD or a frozen current channel each fabricate a deficit on a
   healthy array. The tell is that no other physical tag moves.
2. **Curtailment and grid.** Check `grid-curtailment-policy` and `operating_state`. A
   curtailed inverter shows reduced AC power with **DC voltage riding high** toward Voc — the
   opposite of every fault in section 9.
3. **Soiling and weather.** Check cumulative days since rainfall above 4 mm/day and the
   soiling trend in `solar-soiling-cleaning-sop`. If all 20 positions are down together,
   `dc_voltage_v` is unmoved and `inverter_temp_c` is unmoved or low, the answer is dirt.
4. **Peers.** Compare against the other 23 inverters. A site-wide slope is weather, aerosol
   or soiling. A single block diverging from 23 peers is an equipment hypothesis.

Only when all four are closed does a DC deviation become an equipment finding, and only then
is an IV trace, thermography scan or module replacement authorised. See
`incident-log-solar-inverter` for worked cases in both directions.

## Related documents

`solar-inverter-system`, `solar-inverter-thermal-sop`, `solar-string-fault-sop`,
`solar-iv-curve-sop`, `solar-soiling-cleaning-sop`, `scada-sensor-validation-sop`,
`grid-curtailment-policy`, `alarm-response-matrix`, `om-economics-policy`,
`incident-log-solar-inverter`
