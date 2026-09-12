---
doc_id: wind-generator-thermal-sop
title: Generator Thermal Investigation Procedure
asset_type: wind_turbine
component: generator
kind: sop
version: "1.2"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for generator winding overtemperature on a
> generic 2 MW doubly-fed induction generator. Not manufacturer documentation, not
> attributable to any OEM. All figures are project-defined engineering assumptions unless a
> section states a measured source.

## 1. Scope and trigger conditions

Applies to `WT-001` .. `WT-018` at Kutch Wind Farm on any exceedance of
`generator_winding_temp_c`.

| Trigger | Value | Entry point |
|---|---|---|
| Warning | 140 degC on any of six PT100 | Section 4, desk review only |
| Controller thermal derate | 145 degC, torque cut 5 % rated per minute until below 140 degC | Section 4, then 5 within 72 h |
| Alarm | 150 degC | Section 5 within 24 h, derate to 70 % |
| Trip | 160 degC | Stop; section 6 before restart |
| Residual exceedance, no absolute exceedance | residual > +8 degC, z > 3.0 | Section 4 |
| Step change | > +8 degC within one 10-minute interval | Section 4.3 first |

The operative alarm here is the **145 degC derate threshold**, because that is where the
machine begins trading energy for temperature. Class F insulation permits a 155 degC hotspot;
the machine is run to a class B rise so the margin absorbs a dusty Kutch afternoon, not so it
can be consumed routinely.

A derate actively conceals its cause: it converts a thermal fault into a power deficit. If
`power_kw` carries a negative residual while `generator_winding_temp_c` sits flat at
140 - 145 degC, the machine is thermally limited. Do not open an aerodynamic investigation —
see `wind-pitch-yaw-system` for the signatures this is confused with.

## 2. Rule out first — mandatory before any equipment hypothesis

No generator fault is asserted and no crew is dispatched until all four checks are closed. A
hot day and a windy hour both raise winding temperature on a perfectly healthy machine.

1. **Instrumentation.** Run `scada-sensor-validation-sop`. Confirm the six winding PT100s
   agree within 8 degC at equilibrium, that `nacelle_temp_c` and `ambient_temp_c` are alive
   and unfrozen, and that the nacelle anemometer has not drifted. One RTD diverging from its
   five siblings is a sensor hypothesis, not a thermal event.
2. **Ambient.** If `nacelle_temp_c` exceeds its 50 degC warning and the anomaly is fleet-wide,
   the finding is environmental until a residual survives the conditioning in section 3.
3. **Curtailment.** Check `grid-curtailment-policy`. Curtailment changes load history abruptly
   and invalidates any thermal comparison that assumed steady operation.
4. **Peers.** Compare at least four turbines in the same wind sector and wake position over
   the same hour. A shared rise means shared cause — air temperature, air density, a site-wide
   load excursion — not a defect in one generator.

Record all four outcomes in the work order. An exceedance that fails this section is closed as
environmental or instrumentation, with evidence, and generates no ticket.

## 3. Why instantaneous load is the wrong reference

The winding time constant is approximately **18 minutes**, the fastest of the three monitored
thermal masses (gearbox oil ~42 min, main bearing ~55 min). At rated output the winding
settles about **62 K above nacelle air**. Losses are part fixed (iron, windage) and part
load-dependent (copper, scaling with current squared), so the project uses
`rise_K ~= 62 x (0.45 + 0.55 x (P / 2000)^2)`:

| Load | 500 kW | 1,000 kW | 1,500 kW | 2,000 kW |
|---|---|---|---|---|
| Steady rise over nacelle air | 30 K | 36 K | 47 K | 62 K |

A reading therefore responds to the preceding **~54 minutes** (3 tau, 95 % of a step), not to
the load in the same SCADA row. Worked example: stepping 50 % to 100 % raises equilibrium by
26 K, but 10 minutes later only 43 % of that — 11 K — has appeared and the winding is still
climbing. A gust front holding a turbine at rated for twenty minutes produces a temperature
that looks alarming against instantaneous load and is normal against load history.

**Procedure.** Condition on an exponentially-weighted mean of `power_kw` with an 18-minute
constant over the preceding hour, plus `nacelle_temp_c`. If the residual vanishes, the event
is a load-history artefact; close it.

Second discriminator: if `generator_winding_temp_c`, `gearbox_oil_temp_c` and
`main_bearing_temp_c` rise together with the *same* shape, the common cause is nacelle air —
blocked inlet screens, lost ventilation — not the winding (`wind-gearbox-system` section 6).

Third: cooling defects scale with how hard the cooler must work, so their residual correlates
with ambient (r > 0.6) and collapses overnight and at low load. Electrical defects do not.
This test is decisive in `incident-log-wind-gearbox`, case `INC-2024-027-generator-overheating`.

## 4. Desk review before dispatch

4.1 Pull all six PT100 channels individually, not the aggregate maximum, and compute the
phase-to-phase spread. Above 8 degC at equilibrium it is an RTD fault until proven otherwise.
A PT100 reads 100.0 Ohm at 0 degC and 0.385 Ohm/K thereafter — 150.1 Ohm at 130 degC. An open
circuit drives most transmitters to upscale burnout, which presents as a plausible extreme
value; a frozen channel shows no diurnal ripple at all.

4.2 Plot the winding residual against `nacelle_temp_c` over 14 days and record r. That number
routes the diagnosis (`wind-generator-system` section 5).

4.3 For a step change, read the fan status bits in `status_code` in the same interval. A
radiator fan dropping out is a step; degradation is not. Two fans are fitted; losing one gives
+10 to +18 degC.

4.4 Confirm the residual persists across three load bands. Present only at high load means
cooling capacity; present at 40 % as well as 90 % means electrical or mechanical.

## 5. Cooling circuit inspection

Turbine stopped, with the safety prerequisites of `wind-generator-system` section 8 applied.

| Check | Acceptance | Action on failure |
|---|---|---|
| Cooling air filter differential pressure | < 250 Pa | Replace element, re-measure |
| Filter media | No dust cake, no oil wetting | Replace; oil wetting implies a bearing seal leak |
| Radiator fin block | No dust mat, fins undeformed | Clean, compressed air below 6 bar only |
| Both radiator fans | Start within 3 s, current within 10 % of nameplate | Replace relay or motor; log as step-change cause |
| Internal circulation fan | Free rotation, correct direction, no blade damage | Stop until corrected |
| Nacelle inlet screen | No nesting material or dust cake | Clean; monthly in the March - June dust season |
| Airflow path | No insulation, cable bundle or sheet obstructing discharge | Clear |
| Terminal box thermography | No terminal more than 15 degC above neighbours | Retorque the hot terminal |

## 6. Electrical tests at a planned stop

Required when ambient correlation is weak (r < 0.3), at the 150 degC alarm, and always before
restart after a 160 degC trip. Winding below 40 degC before terminal work.

| Test | Method | Pass | Failure meaning |
|---|---|---|---|
| Insulation resistance | 1,000 V, 1 min, corrected to 40 degC (double per 10 K above reference) | > 100 MOhm | 10 - 100 MOhm trend monthly; below 10 MOhm do not energise |
| Polarisation index | IR at 10 min / IR at 1 min | > 2.0 | 1.0 - 2.0 dubious; < 1.0 wet or carbon-contaminated. Not meaningful when the 1-minute value exceeds 5 GOhm |
| Winding resistance balance | Micro-ohmmeter, corrected to 20 degC by (234.5 + 20)/(234.5 + t) | Spread within 2 % | Above 5 % is a connection fault — retorque before condemning a winding |
| RTD resistance and spread | Multimeter at each sensor head | Six within 8 degC, each within 1 Ohm of curve | Replace sensor; never re-rate the machine on a bad channel |

Falling insulation resistance with PI below 2.0, on a machine whose residual does **not**
correlate with ambient, is the only combination that justifies a rewind conversation.

## 7. Bearing insulation, shaft grounding, slip rings and brushes

Converter-fed machines carry common-mode shaft voltage. A failed insulated non-drive-end
bearing or grounding brush lets discharge current erode raceways, and the first symptom is a
localised temperature rise that mimics a winding problem.

- Insulated NDE bearing housing: > 1 MOhm at 500 V, at rest, grounding brush lifted.
- Shaft grounding brush: below 0.1 Ohm shaft-to-frame, face seated, no carbon glaze. Peak
  shaft-to-ground voltage above 3 V pk indicates an ineffective brush (project assumption).
- Grease: greyish or darkened NDE grease with no thermal history explaining it is the
  electrical-discharge signature. Sample before regreasing.
- Vibration: fluting raises broadband RMS with no clean 1x or mesh line. Baseline ~2.0 mm/s,
  4.5 mm/s warning, 7.1 mm/s action. Escalate to `wind-vibration-analysis-sop` rather than
  concluding from the broadband SCADA tag alone.
- Slip rings and brush gear: brush length above the minimum mark, uniform bedding, even
  patina, no grooving above 0.1 mm; replace as a full set. Rotor current imbalance and rising
  converter fault counts alongside a thermal residual point here, not at the stator.

## 8. Derate versus stop, and closure

| Condition | Decision | Authority |
|---|---|---|
| 140 - 145 degC, residual < +8 degC, strong ambient correlation, RTD spread normal | Keep running; clean cooling within 14 days | Site reliability engineer |
| Derating at 145 degC, cooling cause identified | Accept the automatic derate; inspect within 72 h | Site reliability engineer |
| 150 degC alarm, any cause | Manual derate to 70 %; inspect within 24 h | O&M manager |
| Above 155 degC beyond 10 minutes, or any 160 degC trip | Stop; no restart until section 6 passes | O&M manager |
| Weak ambient correlation with falling insulation resistance | Derate to 70 % only until the next planned window, then stop | Asset manager |
| Single RTD divergent, others normal | No derate, no dispatch; sensor work order only | Site reliability engineer |
| Unresolved after sections 4 and 5 | Escalate to human review; the agent does not guess | O&M manager |

At the 3.20 INR/kWh wind tariff a 30 % derate forgoes 600 kWh/h at rated wind (INR 1,920/h),
about 204 kWh/h averaged at a 0.34 capacity factor (INR 653/h); a full stop costs ~680 kWh/h,
INR 2,176/h. Against an unplanned generator failure at INR 2,100,000 and 168 h downtime versus
a planned repair at INR 780,000 and 24 h, several days of derate is cheap. A cooling-side fix
usually closes for a fraction of the INR 55,000 inspection assumption, so state in the work
order when the diagnosis is cooling: the economic case changes by an order of magnitude. See
`om-economics-policy`.

Close the ticket with the four rule-out outcomes, the load-history-conditioned residual and
its ambient correlation, the six-channel RTD spread, fan status and filter differential
pressure, any electrical results, and the decision with its authority. A recommendation
without this package is not actionable and must not be issued.

## Related documents

- `wind-generator-system` — machine constants, failure modes, residual interpretation.
- `scada-sensor-validation-sop` — run before accepting any exceedance as real.
- `grid-curtailment-policy` — context that invalidates load-history comparison.
- `wind-gearbox-system` — shared nacelle thermal environment and load normalisation.
- `wind-vibration-analysis-sop` — spectral follow-up for bearing and fluting signatures.
- `wind-bearing-replacement-sop` — intervention when a generator bearing is confirmed.
- `wind-pitch-yaw-system` — the aerodynamic explanations a derate is mistaken for.
- `weather-icing-operations-sop` — cold-season load and ambient anomalies.
- `alarm-response-matrix` — authority and response times across alarm classes.
- `om-economics-policy` — derate, downtime and intervention cost assumptions.
- `incident-log-wind-gearbox` — `INC-2024-027-generator-overheating`, the ambient correlation
  test worked end to end.
