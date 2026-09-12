---
doc_id: wind-bearing-replacement-sop
title: Main Bearing and HSS Bearing Replacement
asset_type: wind_turbine
component: gearbox
kind: sop
version: "1.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content on bearing replacement for a generic 2 MW
> geared wind turbine. This is not manufacturer documentation and is not attributable to any
> OEM. All figures are project-defined engineering assumptions unless a section states a
> measured source.

## 1. Scope

Covers the two bearing interventions on the Kutch Wind Farm turbines (`WT-001` .. `WT-018`):
an **up-tower HSS bearing change** at the gearbox output stage, and a **down-tower main
(rotor) bearing exchange**. Machine constants are as defined in `wind-gearbox-system`
section 2 — ratio 1:97.5, HSS 839 - 1,502 rpm, rotor 8.6 - 15.4 rpm, 320 L ISO VG 320
synthetic PAO sump, 10 um inline and 5 um offline filtration. Diagnosis is complete before
this SOP opens.

## 2. Rule out first — gate before any parts order or crane booking

A main bearing exchange commits an assumed INR 2,800,000 crane mobilisation before a bolt is
loosened. The site reliability engineer closes this gate and the O&M manager countersigns it
**before** procurement is raised.

1. **Instrumentation.** Run `scada-sensor-validation-sop` in full. A loose accelerometer mount
   and a drifting bearing RTD both look exactly like incipient spalling. One channel moving
   with no corroborating channel is a sensor hypothesis, not a bearing.
2. **Environment and grid.** Check `operating_state`, `pitch_angle_deg` and the dispatch log
   against `grid-curtailment-policy`; a curtailed machine runs at part load with an unusual
   torque spectrum. December - February, clear `weather-icing-operations-sop` — asymmetric ice
   presents as a 1x-rotor vibration rise and resolves on its own.
3. **Peers.** A residual moving on three or more turbines at once is site-wide, not a bearing.
4. **Two independent evidence classes.** Parts are ordered only when the SCADA trend is
   corroborated by at least two of: portable spectrum (`wind-vibration-analysis-sop`), oil
   laboratory result (`wind-oil-sampling-sop`), borescope or magnetic-plug debris
   (`wind-gearbox-inspection-sop`).

If the gate cannot be closed the case escalates to human review and the turbine stays on
condition monitoring. It does not proceed to intervention on a single trend.

## 3. Up-tower versus down-tower

| Criterion | Up-tower | Down-tower |
|---|---|---|
| Components | HSS and generator bearings, couplings, seals, filters | Main bearing, main shaft, planetary stage |
| Heaviest lift | < 800 kg, nacelle service crane | 8 - 70 t, main crane |
| Rotor removal | No | Yes |
| Crane | None | 600 t crawler, ~95 m hook for an 80 m hub |
| Assumed outage | 36 h | 240 - 336 h elapsed, weather dependent |
| Crew | 4 | 9 - 12 plus crane crew |

The choice is driven by defect **location**, not severity. A confirmed HSS outer-race defect
at BPFO 160 Hz with clean planetary orders is up-tower work even at Zone D vibration. A rising
`main_bearing_temp_c` residual with Fe rising in oil and energy below 10 Hz is down-tower work
even at Zone B, because the main bearing cannot be extracted with the rotor attached.

Convert up-tower to down-tower on discovery of: planetary debris on the magnetic plug, a
cracked housing, main shaft journal scoring, or HSS radial runout above 0.15 mm TIR.

## 4. Crane mobilisation

Lead time is assumed at **21 - 35 days** from purchase order, plus 2 days rig-up and 1 day
de-rig on a prepared hardstand.

- A down-tower exchange is never an emergency response. If the trend gives under 30 days of
  remaining useful life, stop the turbine and wait for the crane rather than accrue secondary
  damage at the 1.9x multiplier.
- Lifts suspend above **8 m/s** at hub height for rotor and blade handling, **10 m/s** for
  nacelle-internal lifts. Kutch afternoon winds March - June exceed both; schedule 05:00 - 11:00.
- Crane cost is per mobilisation, not per turbine. One mobilisation covering three turbines
  amortises INR 2,800,000 to roughly INR 930,000 each. Whether waiting to batch beats acting
  now is decided by `om-economics-policy`, not in the field.

## 5. Parts and consumables

| Item | Up-tower HSS | Down-tower main bearing |
|---|---|---|
| Bearing | HSS drive-end cylindrical roller (16-element generic), non-drive-end deep groove | Main bearing assembly, assumed 7.8 t |
| Seals | Labyrinth kit, housing O-rings | Main shaft seal set, housing gasket |
| Fasteners | Single-use 10.9 cap and coupling bolts | Single-use 10.9 studs, tensioner rated |
| Oil | 320 L ISO VG 320 PAO | 320 L plus 60 L flushing charge |
| Filters | 10 um inline, 5 um offline | Both, plus 5 um filter cart |
| Tooling | Induction heater, calibrated torque wrench, laser alignment set | Hydraulic tensioner with current certificate, hydraulic puller |

Torque values in section 7 assume MoS2-pasted threads at an assumed friction coefficient of
0.12 - 0.14. **Dry or oiled threads invalidate every value.** Bearings are mounted by induction
heating only, never flame; ring temperature must not exceed 110 degC.

## 6. Step sequence

**6.1 Up-tower HSS bearing change — crew 4, ~36 h over three shifts**

1. Lockout: stop, rotor lock, isolate and earth the generator terminals, lock yaw and pitch,
   confirm zero energy. Two-person verification, logged.
2. Hoist parts with the nacelle service crane, single lifts under 800 kg.
3. Drain the 320 L sump into containment; label the drain sample for the laboratory per
   `wind-oil-sampling-sop`. Photograph the magnetic plug and chip detector before cleaning.
4. Disconnect the generator coupling, mark phase orientation, slide the generator back on its
   rails. Do not disturb the generator foot shims.
5. Remove the bearing housing cap, extract with the hydraulic puller, inspect the journal.
   Measure journal diameter at three planes; escalate to down-tower if wear exceeds 0.05 mm.
6. Induction-fit the new bearings, refit housing and seals.
7. Refill with fresh ISO VG 320 PAO, change both filter elements, circulate through the
   offline loop 60 min before first rotation.
8. Re-couple, align per section 7, run in per section 8.

**6.2 Down-tower main bearing exchange — crew 9 - 12, 240 - 336 h**

1. Lockout as above, plus crane exclusion zone and ground crew brief.
2. Remove blades individually or as a rotor star per the lift plan; set down on stands.
3. Separate the main shaft at the shrink disc, or strip the full nacelle if the lift plan
   calls for it.
4. Lift the main shaft and bearing assembly to ground, transfer to the workshop trailer.
5. Inspect the mainframe saddle for fretting; blue-check the seat, minimum 80 % contact.
6. Install the replacement, shim the housing, tension per section 7, re-establish main
   shaft-to-gearbox concentricity.
7. Rebuild in reverse, refill 320 L, replace both elements, run in.

## 7. Torque and alignment

| Joint | Fastener | Method | Value |
|---|---|---|---|
| HSS bearing housing cap | M16 10.9 | 3-pass star, 30 / 70 / 100 % | 280 N.m |
| Generator coupling | M20 10.9 | 3-pass star | 560 N.m |
| Main shaft shrink disc | M24 10.9 | 3 passes, gap uniform to ±0.2 mm | 950 N.m |
| Main bearing housing to mainframe | M36 10.9 | Hydraulic tensioner, 2 passes | 3,400 N.m equivalent |

| Alignment check | Tolerance |
|---|---|
| Gearbox-to-generator parallel offset | <= 0.15 mm, laser measured cold |
| Gearbox-to-generator angular offset | <= 0.05 mm per 100 mm coupling diameter |
| Cold thermal-growth bias | Generator set 0.25 mm low; the winding runs ~62 K over ambient |
| HSS radial runout | <= 0.05 mm TIR |
| Main bearing housing seating | <= 0.10 mm/m, >= 80 % blue contact |

Re-check alignment after the first hour at 100 % load and again at 50 running hours. Re-torque
bolted joints once at 50 hours; a joint that relaxes twice is replaced, not re-torqued again.

## 8. Run-in

Each load step is held for at least three thermal time constants so the recorded value is
steady rather than still rising — oil ~42 min, main bearing ~55 min, winding ~18 min.

| Step | Hold | Recorded at end of hold |
|---|---|---|
| No-load spin, HSS ~850 rpm | 30 min | Noise, leaks, oil pressure |
| 25 % rated | 2 h | Oil temperature, vibration RMS |
| 50 % rated | 4 h | Above plus portable spectrum |
| 75 % rated | 6 h | Above |
| 100 % rated | 12 h | Full acceptance set, section 9 |

Cold-start inhibit applies: no more than 25 % rated torque until `gearbox_oil_temp_c` exceeds
10 degC. Expect elevated Fe in the 50 h oil sample; run-in wear can double steady-state Fe.
That sample is a baseline, not an alarm. The first diagnostic sample is at 500 h.

## 9. Acceptance criteria

Assessed at 80 - 100 % load, steady, with the sensor chain revalidated first.

| Quantity | Acceptance |
|---|---|
| `drivetrain_vibration_mms` | <= 2.8 mm/s RMS and within +0.6 mm/s of the ~2.0 mm/s load-matched baseline; at or above the 4.5 mm/s warning fails outright |
| HSS 1x (25.0 Hz) and 2x (50.0 Hz) | <= 0.8 mm/s each |
| Envelope at BPFO 160 Hz / BPFI 240 Hz | No discrete peak with HSS-1x sidebands |
| `gearbox_oil_temp_c` | Rise over ambient <= 41 K (38 K nominal + 3 K); absolute below the 75 degC warning |
| `main_bearing_temp_c` | Rise over ambient <= 29 K (26 K nominal + 3 K); absolute below the 70 degC warning |
| `generator_winding_temp_c` | Rise over ambient <= 66 K (62 K nominal + 4 K); below the 145 degC alarm, class F limit 155 degC |
| Oil at 500 h | ISO 4406 <= 17/15/12, water < 300 ppm, PQ index trending down |
| Power residual | Within ±1.5 % of peer-referenced expected power, sustained 72 h at >= 60 % load |
| Alarms | No repeat status codes in 72 h |

RAI closes the case only after **7 days** of post-repair telemetry inside band. The closed
case and its pre-repair trajectory are written to `incident-log-wind-gearbox` and become a
retrieval candidate for future similar-case matching.

## 10. Outage window planning

The 36 h planned-downtime figure in `wind-gearbox-system` section 9 covers **up-tower work
only**. A down-tower exchange is booked against its real crane-constrained duration and that
duration — not the registry default — is what the economics module receives. Substituting 36 h
for a crane job understates lost production by an order of magnitude.

Planning inputs to `om-economics-policy`: remaining useful life from the trend, crane lead
time, the 8 - 10 m/s lift wind limits, seasonal wind profile, and whether a batched slot with
another flagged turbine exists. At capacity factor 0.34 and the wind tariff of INR 3.20/kWh,
one standstill hour is 680 kWh or INR 2,176; a 288 h unplanned outage is about INR 626,000 of
lost production before repair cost. Whether the risk accrued by waiting for a batched crane
slot is smaller than the crane saving is computed, not judged on site.

## Related documents

- `wind-gearbox-system` — machine constants, alarm limits, economic assumptions.
- `wind-gearbox-inspection-sop` — the inspection that authorises this intervention.
- `wind-vibration-analysis-sop` — spectral confirmation and post-repair capture.
- `wind-oil-sampling-sop` — drain, 50 h and 500 h samples, laboratory limits.
- `wind-generator-system`, `wind-generator-thermal-sop` — the load side of the HSS.
- `scada-sensor-validation-sop` — mandatory before and after the intervention.
- `weather-icing-operations-sop`, `grid-curtailment-policy` — environmental rule-out.
- `om-economics-policy` — outage window, batching, intervention comparison.
- `alarm-response-matrix` — escalation routing for the triggering alarm.
- `incident-log-wind-gearbox` — closed cases and observed repair outcomes.
