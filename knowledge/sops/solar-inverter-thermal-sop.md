---
doc_id: solar-inverter-thermal-sop
title: Inverter Thermal Derate Investigation
asset_type: solar_inverter
component: inverter
kind: sop
version: "1.4"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string inverter.
> This is not manufacturer documentation and is not attributable to any OEM. All figures are
> project-defined engineering assumptions unless a section states a measured source.

## 1. Scope and trigger conditions

This procedure investigates a Charanka Solar Park string inverter (`INV-001` .. `INV-024`)
that is running hot, asserting a thermal derate, or delivering a persistent negative power
residual with an elevated heatsink temperature. It covers derate confirmation, the thermal
chain, cooling-path inspection, DC bus capacitor ageing, power module fatigue and infrared
survey of the current-carrying joints.

Open this SOP when any of the following holds:

- `derate_flag` set for more than 3 consecutive 15-min intervals on a single inverter.
- `heatsink_temp_c` above 60 degC, or above 45 degC when peer inverters are below 45 degC.
- `internal_temp_c` above 55 degC at any load.
- Normalised heatsink rise (section 5) above 20 K per unit load for a full day.
- A power residual worse than -6 % that survives the gate in section 2.

## 2. Rule out first (mandatory gate)

A high-irradiance, high-ambient Charanka afternoon derates a perfectly healthy inverter. That
is designed behaviour, not a fault. Do not raise a work order, and do not let the agent assert
an equipment fault, until every item below is closed.

| Check | Procedure | Disqualifying result |
|---|---|---|
| Sensor validity | `scada-sensor-validation-sop` — heatsink RTD, `internal_temp_c`, POA pyranometer, ambient probe shielding | Any single tag moving with no corroborating tag |
| Ambient probe siting | Probe in direct sun or mounted on the cabinet reads 6 - 12 K high | Reads high vs. the met-mast ambient |
| Grid curtailment | `grid-curtailment-policy` — plant controller set-point log | All 24 inverters flat-topped together |
| Soiling | `solar-soiling-cleaning-sop` — soiling is fleet-wide and does **not** raise heatsink temperature | Deficit present on all inverters, heatsink normal |
| String-side loss | `solar-string-fault-sop`, `solar-iv-curve-sop` — a lost string reduces power and *lowers* heatsink temperature | Power down **and** heatsink down |
| Environment conditioning | Residual computed in a matched bin: POA +/- 50 W/m2, `ambient_temp_c` +/- 2 K | Residual disappears inside the matched bin |

The last row is the decisive one. RAI predicts `ac_power_kw` from POA irradiance, ambient
temperature, wind speed and time of day. Only the residual is diagnostic. A deficit that
vanishes once POA and ambient are conditioned on is weather, and the case is closed there.

## 3. Reference constants and the derate schedule

| Parameter | Value | Unit |
|---|---|---|
| Rated AC power | 250 | kW |
| DC array per inverter (DC/AC 1.25) | 312.5 | kWp |
| Strings per inverter | 20 | - |
| String Voc / MPP / Isc-equivalent current at STC | 820 / 640 / 9.2 | V, V, A |
| European efficiency / peak efficiency | 98.2 / 98.8 | % |
| Module power temperature coefficient | -0.004 | per K |
| NOCT | 45 | degC |
| Derate onset (heatsink) | 45 | degC |
| Hard trip (heatsink) | 75 | degC |
| Heatsink thermal time constant | ~8 | min |
| Enclosure air thermal time constant | ~25 | min |
| Site tariff (solar) | 2.45 | INR/kWh |

Derate schedule, linear at **-2.0 % of rated per K above 45 degC**, floored at 50 %:

| `heatsink_temp_c` | Output ceiling | Note |
|---|---|---|
| <= 45 | 250 kW (100 %) | No derate |
| 50 | 225 kW (90 %) | Routine on summer afternoons |
| 55 | 200 kW (80 %) | Routine April - June |
| 60 | 175 kW (70 %) | Inspect cooling path within 7 days |
| 65 | 150 kW (60 %) | Inspect within 72 h |
| 70 - 74 | 125 kW (50 %), floor | Inspect within 24 h |
| 75 | Trip | Do not reset before section 6 inspection |

**Equilibrium behaviour is the single best discriminator.** A healthy inverter that derates
sheds its own loss, so the heatsink stabilises within roughly two time constants (~15 min) at
1 - 5 K above the 45 degC knee and holds there. A faulted cooling path does not stabilise: the
ceiling falls, the heatsink keeps climbing, and the pair walk each other down toward the trip.

## 4. Confirming a real derate rather than an irradiance limit

Because DC/AC ratio is 1.25, a flat top at 250.0 kW is **clipping**, which is normal and
correct. A derate is a flat top *below* 250 kW while DC power is still available.

| Observation | Clipping | Thermal derate | Irradiance-limited |
|---|---|---|---|
| `ac_power_kw` | Flat at 249 - 250 kW | Flat below 248 kW | Tracks POA smoothly |
| `dc_voltage_v` | 640 - 700 V | **680 - 760 V**, walked above MPP | 620 - 660 V, at MPP |
| `heatsink_temp_c` | Any | >= 45 degC | Any |
| `derate_flag` | Clear | Set | Clear |
| Peers at same POA | Also flat | Not flat, or flat higher | Also tracking |

The DC voltage row is the mechanism: to shed power the inverter walks the operating point up
the I-V curve away from maximum power point, so bus voltage rises while current falls. If
`dc_voltage_v` is sitting at MPP, the inverter is not limiting anything.

Expected DC power for the cross-check, using cell temperature
`T_cell = T_amb + (NOCT - 20)/800 x POA`:

> POA 950 W/m2, ambient 42 degC gives `T_cell` = 42 + 29.7 = 71.7 degC; temperature factor
> `1 - 0.004 x (71.7 - 25)` = 0.813. With 3 % soiling and 3 % wiring/mismatch loss,
> `P_dc` = 312.5 x 0.95 x 0.813 x 0.97 x 0.97 = 227 kW, i.e. **~223 kW AC available and no
> clipping at all**. A healthy unit at 54 degC heatsink is capped at 205 kW, so ~18 kW is lost
> to a legitimate thermal derate — about 36 kWh and INR 88 per inverter over a two-hour
> window, roughly INR 2,100 per day fleet-wide. That loss is real, and it is still not a fault.

## 5. The thermal chain and its diagnostic triad

The cabinet is dual-chamber: the heatsink is swept by outside air, the electronics compartment
is sealed and cooled separately. Project-assumed healthy offsets at steady output:

| Quantity | 20 % load | 50 % load | 100 % load |
|---|---|---|---|
| `heatsink_temp_c` - `ambient_temp_c` | +3 K | +7 K | **+12 K** |
| `internal_temp_c` - `ambient_temp_c` | +2 K | +4 K | +6 K |
| `heatsink_temp_c` - `internal_temp_c` | +1 K | +3 K | +6 K |

Normalise to the load-independent index
`theta = (heatsink_temp_c - ambient_temp_c) / (ac_power_kw / 250)`, in K per unit load.
Baseline 12 K/pu; **watch 16 K/pu; action 20 K/pu; suspect module or thermal-interface
degradation above 26 K/pu** (section 9).

| Pattern | Interpretation | Go to |
|---|---|---|
| Heatsink and internal both high, ambient high, peers alike | Environmental — no fault | Section 2 |
| Heatsink high, internal normal | Heatsink-side: fan, fin fouling, thermal interface, module | Sections 6, 7, 9 |
| Internal high, heatsink normal | Compartment filter blocked, magnetics or DC bus capacitor losses | Sections 6, 8 |
| Both high overnight at zero load | Sensor fault or auxiliary heater stuck | `scada-sensor-validation-sop` |

## 6. Cooling fans, filters and airflow measurement

Isolate AC and DC, wait 5 min for DC bus discharge, verify below 50 V DC at the bus test
points before opening the electronics compartment.

| Item | Method | Accept | Act |
|---|---|---|---|
| Heatsink fans (2, EC type) | Command full speed, read `fan_speed_rpm` | Both within 5 % of nominal | Any fan below 90 % or stalled — replace |
| Intake face velocity | Vane anemometer, 9-point traverse of the intake grille | >= 3.4 m/s mean (nominal 4.0 m/s) | Below 3.0 m/s — service filter; below 2.2 m/s — fan or blockage fault |
| Filter differential pressure | Manometer across the compartment filter | <= 40 Pa | 60 Pa service; 90 Pa alarm, replace before restart |
| Fan bearing noise / current | Listen, clamp meter | Steady current, no growl | Replace at next visit |

Filter elements: replace every 6 months, and every 3 months March - June. Kutch and Charanka
dust loading is high in that window; this matches the dust-season interval used for the wind
cooler fins in `wind-gearbox-system` section 7.

## 7. Heatsink fouling, enclosure ingress and dust

Inspect the fin stack with a torch along the channel axis. Charanka dust binds with morning
dew into a mat that is not removable by air alone.

- A ~1 mm bound dust mat across the fin stack adds **4 - 6 K** at rated output, i.e. it moves
  `theta` from 12 to 16 - 18 K/pu and pulls the derate knee forward by that much ambient.
- Clean when `theta` exceeds 16 K/pu, or on visual fin blockage above 20 % of channel area.
- Method: compressed air at <= 4 bar blown **against** the airflow direction, then a soft
  brush, then a low-pressure rinse only if the enclosure rating permits it. Never pressure-wash
  a fin stack with the cabinet energised.
- Enclosure ingress: check door gasket compression, cable-gland seals, and the breather. Dust
  film on PCBs or inside the compartment is an ingress finding, not a cleaning finding — it
  means a seal has failed and will recur.
- Record `theta` before and after cleaning. If cleaning does not move `theta` by at least
  3 K/pu, the finding was not fouling; continue to sections 8 - 10.

## 8. DC bus capacitor ageing

Electrolytic DC bus capacitors age by electrolyte loss; equivalent series resistance rises,
self-heating rises, and the compartment runs hot with a normal heatsink. Assumed design life
90,000 h at 45 degC internal air, halving per 10 K above that.

| Indicator | Baseline at rated | Watch | Action |
|---|---|---|---|
| DC bus ripple, peak-to-peak | <= 8 V | 14 V | 20 V — plan replacement |
| `internal_temp_c` - `ambient_temp_c` at rated | +6 K | +11 K | +15 K |
| Internal rise at night / near-zero load | +1 to +2 K | +4 K | +6 K |
| Physical | Flat cans, dry vents | Discolouration | Bulging or vented — replace before restart |

The night-load row is the clean signature: ageing capacitors dissipate on the bus pre-charge
and standby rails, so the compartment stays warm when the inverter is doing no work. Nothing
environmental produces that.

## 9. Power module thermal-cycling fatigue

Bond-wire lift-off and solder-layer fatigue raise junction-to-heatsink thermal resistance.
Charanka sees roughly one large daily cycle plus 15 - 40 cloud-transient cycles per day.

| Indicator | Baseline | Watch | Action |
|---|---|---|---|
| `module_temp_c` - `heatsink_temp_c` at rated | 22 K | 28 K | 34 K — replace module |
| `theta` after cooling path cleared | 12 K/pu | 18 K/pu | 26 K/pu |
| Phase current imbalance | <= 1.5 % | 3 % | 5 % |
| Measured efficiency at 50 - 80 % load | >= 98.0 % | 97.3 % | 96.5 % |
| Desaturation or overtemperature trips | 0 / month | 1 / month | 2 or more / month |

A rising module-to-heatsink delta with a **clean, verified** cooling path is the fatigue
signature; it does not respond to cleaning and it does not correlate with ambient.

## 10. Infrared thermography of busbars and terminations

Survey with the inverter at **>= 40 % rated current (>= 100 kW)**; readings below that are not
interpretable. Correct to rated with `dT_rated = dT_measured x (I_rated / I_measured)^2`.
Survey points: DC input terminal blocks, all 20 string fuse holders, DC bus busbar joints, AC
output lugs, AC contactor terminals, and the transformer-side cable terminations.

| dT vs. similar component at similar load | dT vs. ambient | Classification | Required action |
|---|---|---|---|
| 1 - 3 K | 1 - 10 K | Possible deficiency | Repair at next scheduled outage |
| 4 - 15 K | 11 - 20 K | Probable deficiency | Repair within 30 days |
| > 15 K | 21 - 40 K | Deficiency | Repair within 7 days |
| - | > 40 K | Major discrepancy | De-energise and repair immediately |

A single hot string fuse holder relative to its 19 peers is the most common finding and is a
termination defect, not a thermal-system defect. Re-torque to the values recorded on the DC
compartment label (project registry: 2.5 N.m string fuse holders, 20 N.m AC output lugs),
re-survey under the same load, and confirm the delta has closed. Record emissivity and the
reflected-ambient setting used; a bare copper busbar read at default emissivity will
under-report by a large and unusable margin.

## 11. Fault assertion criteria and escalation

An inverter thermal fault may be asserted only when **all** of the following hold:

1. Section 2 gate fully closed, with the sensor validation recorded.
2. Power residual worse than -6 % of expected, in matched POA and ambient bins, on 3 or more
   consecutive production days.
3. Peer-relative deficit greater than 4 % against at least 3 inverters sharing the POA sensor.
4. A corroborating thermal residual: `theta` at or above 16 K/pu, or an offset from section 5,
   8 or 9 beyond its watch value.

Two independent signals are required. One signal alone remains a sensor hypothesis, exactly as
in `wind-gearbox-system` section 3. Below that bar the agent escalates to human review rather
than naming a fault.

| Condition | Owner | Response |
|---|---|---|
| Derate with heatsink stable at 46 - 50 degC | Site engineer | Log as environmental, no action |
| `theta` 16 - 20 K/pu | Site engineer | Cooling-path inspection within 7 days |
| `theta` > 20 K/pu, or heatsink > 65 degC | O&M manager | Inspection within 72 h |
| Heatsink trip at 75 degC | O&M manager | No reset before sections 6 and 7 are complete |
| Capacitor or module action threshold met | Asset manager | Plan replacement, cost case per `om-economics-policy` |

Downtime and repair costs are not stated here; use the registry values in
`om-economics-policy` so that field decisions and the RAI economics module cite the same
numbers.

## Related documents

- `solar-inverter-system` — the machine this SOP applies to, and its tag list.
- `solar-dc-string-system` — DC array architecture behind the bus.
- `solar-string-fault-sop` — a lost string lowers power *and* heatsink temperature.
- `solar-iv-curve-sop` — I-V verification when the DC side is suspect.
- `solar-soiling-cleaning-sop` — the fleet-wide deficit that is never a thermal fault.
- `scada-sensor-validation-sop` — run **before** accepting any thermal exceedance as real.
- `grid-curtailment-policy` — the other source of a flat-topped power curve.
- `om-economics-policy` — intervention costs and the expected-loss comparison.
- `alarm-response-matrix` — owner, timer and escalation path for each alarm code.
- `incident-log-solar-inverter` — worked cases, including derate misdiagnosis.
- `wind-gearbox-system` — the cooling-vs-fault reasoning pattern in its wind form.
