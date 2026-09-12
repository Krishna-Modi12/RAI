---
doc_id: wind-generator-system
title: Wind Turbine Generator and Cooling System Manual
asset_type: wind_turbine
component: generator
kind: manual
version: "1.4"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 2 MW doubly-fed induction
> generator. Not manufacturer documentation, not attributable to any OEM. Figures are
> project-defined engineering assumptions unless a section states a measured source.

## 1. Scope

Covers the generator, its cooling circuit, slip rings and brush gear, and the converter
interface, for the generic 2 MW turbines `WT-001` .. `WT-018` at Kutch Wind Farm. The
mechanical input side is described in `wind-gearbox-system`. Thermal faults in this system
are the most commonly **misdiagnosed** wind finding, because a blocked filter and a failing
winding produce the same first symptom.

## 2. Reference machine constants

| Parameter | Value | Unit |
|---|---|---|
| Type | Doubly-fed induction generator (DFIG), 4-pole | - |
| Rated power | 2,000 | kW |
| Rated voltage | 690 | V AC |
| Synchronous speed at 50 Hz | 1,500 | rpm |
| Operating speed range | 1,050 - 1,750 | rpm |
| Slip range | -30 % to +17 % | - |
| Insulation class | F (155 degC limit), utilised to class B rise | - |
| Cooling | Air-to-air, two-stage: internal circulation fan + two external radiator fans | - |
| Winding temperature sensors | 6 x PT100, two per phase | - |
| Bearing arrangement | Drive-end and non-drive-end, regreasable | - |
| Rated torque at 1,500 rpm | 12.7 | kNm |

Insulation class F allows a 155 degC hotspot, but the machine is operated to a class B rise
so that the design margin absorbs a dusty afternoon. The consequence for diagnosis: winding
temperatures in the 130 - 140 degC range are not immediately dangerous, but they are far
outside the normal operating band and mean the cooling chain has lost headroom.

## 3. Failure modes and observable signatures

| Failure mode | Progression | Primary signature | Discriminator |
|---|---|---|---|
| Cooling air filter blockage | Days to weeks | `generator_winding_temp_c` residual +8 to +15 degC, strongly ambient-correlated | `nacelle_temp_c` also elevated; residual collapses at low load and at night |
| Radiator fan failure (one of two) | Step | Winding residual +10 to +18 degC, step change at a single timestamp | Step is instantaneous; fan status bit in `status_code` |
| Winding insulation degradation | Months | Slow winding residual rise, +0.2 to +0.5 degC per week | Insulation resistance falls; polarisation index below 2.0 |
| Generator bearing wear | Weeks | Vibration rise at 1x, `drivetrain_vibration_mms` modest rise | Grease analysis; temperature rise localised to one bearing |
| Slip ring or brush wear | Weeks to months | Rotor current imbalance, converter faults, carbon dust | Visual: brush length below limit, glazing on the ring |
| Rotor bar or winding asymmetry | Months | Current signature sidebands around 50 Hz at 2 x slip x f | Requires current signature analysis, not SCADA |
| Winding RTD fault | Instant | One sensor diverges from the other five | Phase-to-phase spread; see `scada-sensor-validation-sop` |

## 4. Monitored SCADA tags and thermal limits

| Tag | Unit | Normal band at 80 - 100 % load | Warning | Alarm | Trip |
|---|---|---|---|---|---|
| `generator_winding_temp_c` | degC | 95 - 130 | 140 | 150 | 160 |
| `nacelle_temp_c` | degC | 25 - 45 | 50 | 60 | - |
| `main_bearing_temp_c` | degC | 40 - 62 | 70 | 78 | 82 |
| `drivetrain_vibration_mms` | mm/s | 3.2 - 3.8 | 4.0 | 5.6 | 7.1 |
| `power_kw` | kW | load reference | - | - | - |

Derate behaviour: above a winding temperature of 145 degC the controller reduces torque
demand in steps of 5 % rated power per minute until the temperature falls below 140 degC. A
derate therefore **masks** a thermal fault by converting it into a power deficit. If
`power_kw` shows a negative residual while `generator_winding_temp_c` sits flat at 140 - 145
degC, the turbine is thermally limited and the correct hypothesis is cooling, not
aerodynamic underperformance.

## 5. Winding temperature residual interpretation

The residual model predicts `generator_winding_temp_c` from `power_kw`, `rotor_rpm`,
`ambient_temp_c` and `nacelle_temp_c`. Interpretation table:

| Winding residual | Residual z | Ambient correlation | Most likely cause | Response |
|---|---|---|---|---|
| < +3 degC | < 2.0 | any | Normal scatter | None |
| +3 to +8 degC | 2.0 - 3.0 | Strong (r > 0.6) | Cooling capacity loss: filter, fin fouling | Clean filters and radiator at next visit, 14 days |
| +3 to +8 degC | 2.0 - 3.0 | Weak (r < 0.3) | Early winding or bearing issue | Trend weekly, insulation test at next planned stop |
| +8 to +15 degC | 3.0 - 4.5 | Strong | Blocked filter or one failed fan | On-site inspection within 72 h |
| +8 to +15 degC | 3.0 - 4.5 | Weak | Winding degradation suspected | Inspection within 72 h, insulation test mandatory |
| > +15 degC, or absolute > 150 degC | > 4.5 | any | Loss of cooling | Inspect within 24 h; derate to 70 % until resolved |
| Step change > +8 degC within one interval | any | any | Fan or sensor failure | Check fan status bits and RTD spread before dispatch |

The ambient-correlation test in column three is the single most useful discriminator in this
system. A cooling-side defect scales with how hard the cooler has to work; an electrical
defect does not. `INC-2024-027-generator-overheating` is a worked example of exactly this
test being decisive.

## 6. Cooling system maintenance

| Task | Interval | Acceptance criterion |
|---|---|---|
| Cooling air filter inspection | 3 months; monthly in dust season | Differential pressure below 250 Pa |
| Cooling air filter replacement | 12 months or on differential pressure alarm | - |
| Radiator fin cleaning | 6 months | No visible dust mat; compressed air below 6 bar only |
| Fan current and rotation check | 6 months | Both fans start within 3 s of demand; current within 10 % of nameplate |
| Nacelle air inlet screen check | 6 months | Free of nesting material and dust cake |
| Thermographic survey of terminal box | 12 months | No terminal more than 15 degC above its neighbours |

Kutch dust loading between March and June is the dominant driver of filter blockage. A
6-month filter interval is not sufficient in that window; monthly inspection is the standard
for this site.

## 7. Electrical tests at planned stops

| Test | Instrument | Pass criterion | Note |
|---|---|---|---|
| Winding insulation resistance | 1,000 V insulation tester | > 100 MOhm at 40 degC, corrected | Below 10 MOhm: do not energise |
| Polarisation index (10 min / 1 min) | Insulation tester | > 2.0 | 1.0 - 2.0 is dubious, below 1.0 is wet or contaminated |
| Winding resistance balance | Micro-ohmmeter | Phase spread within 2 % | Asymmetry above 5 % implies a connection fault |
| RTD continuity and spread | Multimeter | All six PT100 within 8 degC at thermal equilibrium | Larger spread implies a sensor fault |
| Brush length and bedding | Calliper, visual | Above minimum mark, uniform bedding | Replace as a full set |
| Slip ring surface | Visual, surface roughness | No grooving above 0.1 mm, even patina | Carbon dust implies humidity or wrong grade |

## 8. Safety prerequisites for generator work

1. Turbine stopped, rotor locked, lockout-tagout applied on the main breaker and the
   converter, keys held by the technician performing the work.
2. Confirmed dead with a proved instrument at the generator terminals. The converter DC link
   holds charge; wait the full 10 minute discharge time and verify below 50 V DC.
3. Winding temperature below 40 degC before touching terminals.
4. Wind speed at hub height below 12 m/s for nacelle entry, below 10 m/s for any work
   requiring the rotor lock to be loaded.
5. Two-person rule, rescue plan filed, radio contact confirmed with the control room.
6. Hot-work permit required for any brazing on cooling circuits.

## 9. Cost and downtime planning assumptions

From `COMPONENT_ECONOMICS`, component `generator`:

| Item | Assumption |
|---|---|
| Inspection cost | INR 55,000 |
| Planned repair cost | INR 780,000 |
| Unplanned failure cost | INR 2,100,000 |
| Planned downtime | 24 h |
| Unplanned downtime | 168 h |
| Secondary damage multiplier | 1.5 x |

A cooling-side fix - filters, fins, a fan relay - typically costs a small fraction of the
planned-repair assumption and needs less than one shift. The planned-repair figure covers a
bearing exchange or a rewind. When the diagnosis is cooling, say so explicitly in the work
order, because the economic case changes by an order of magnitude. See
`INC-2024-027-generator-overheating`, where the actual intervention cost was INR 62,000
against a planned-repair assumption of INR 780,000.
