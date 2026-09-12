---
doc_id: weather-icing-operations-sop
title: Icing and Adverse Weather Operations
asset_type: both
component: environment
kind: sop
version: "1.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations content for cold-weather, high-wind, dust and extreme-heat operation
> of a generic 2 MW turbine fleet and a generic 250 kW string inverter solar park. Not
> manufacturer documentation, not attributable to any OEM. Figures are project-defined
> engineering assumptions unless a section states a measured source.

## 1. Scope and honest applicability

Covers `WT-001` .. `WT-018` (Kutch) and `INV-001` .. `INV-024` (Charanka) under blade icing,
high wind, high turbulence, dust storm and extreme heat. Each of these produces a large,
convincing power deficit on a completely healthy machine. This SOP defines how to recognise
that and forbids an equipment-fault conclusion until it is ruled out.

Applicability caveat: hub-height (80 m) temperature at Kutch falls below +2 degC on only a few
December and January nights in a typical year, and no icing event exists in the project's
simulated or ingested telemetry. The icing path in RAI is therefore **unvalidated against site
data** — any icing flag is a hypothesis needing met or visual confirmation, never an evaluated
detector output. Sections 8 - 10 are the parts exercised routinely at these sites.

## 2. Icing formation conditions and meteorological signature

Icing is possible when all three hold at hub height, sustained 30 min:

| Condition | Threshold | Tag |
|---|---|---|
| Air temperature | -10.0 to +2.0 degC | `ambient_temp_c` (hub height, not ground) |
| Relative humidity | >= 95 % | `humidity_pct` |
| Liquid water present | Cloud base below 80 m, fog, or freezing drizzle | `cloud_base_m`, `precip_mm` |

Rime (low temperature, low water content) builds a light opaque leading-edge accretion. Glaze
(near 0 degC, freezing rain) builds a heavier, denser one and is the ice-throw case. Both start
at the tip, where relative velocity is highest: at 15.4 rpm on a 92 m rotor the tip runs 74 m/s.

Declare an **icing window** open when the three conditions are met; close it only when
`ambient_temp_c` has exceeded +2.0 degC continuously for 6 h and any ice indicator has cleared.
The window, not the instantaneous temperature, is the attribution unit used in section 11.

## 3. Why icing looks exactly like a pitch fault or blade erosion

Ice thickens and roughens the aerofoil. Lift falls, drag rises, the rotor cannot hold its design
tip-speed ratio, and the controller leaves pitch near optimum because the blade simply
underperforms. Observable result:

- Power residual -8 % to -35 %, concentrated in partial load (3.0 - 12.5 m/s).
- Effective cut-in rises from 3.0 m/s to roughly 4.5 - 5.5 m/s; the machine idles in
  productive wind.
- `pitch_angle_deg` stays in its normal -1 to +2 deg partial-load band.
- No thermal co-signature; the machine is lightly loaded.

Per `wind-pitch-yaw-system` section 4, a single-blade pitch calibration offset gives -2 % to
-6 % across partial load with a 1P imbalance and no thermal co-signature. Leading-edge erosion
gives the same shape again. The three are **not separable from the power curve alone**. They
separate on time behaviour:

| Hypothesis | Onset | Temperature gated | Reverses |
|---|---|---|---|
| Blade icing | Hours | Yes, only below +2 degC | Yes, fully, on thaw |
| Pitch calibration offset | Step, usually after a service visit | No | Only on recalibration |
| Leading-edge erosion | Monotonic over 6 - 24 months | No | No |

## 4. Rule out first (mandatory)

No icing conclusion and no equipment conclusion is recorded until these are complete.

1. **Instrumentation.** Run `scada-sensor-validation-sop`. An unheated anemometer or vane ices
   before the blades do; a frozen or under-reading anemometer fabricates both the deficit and
   the wind speed it is measured against. Cross-check `site_met.wind_speed_ms`; look for
   flatline and frozen-value signatures.
2. **Curtailment.** Check `status_code`, `operating_state` and the curtailment flag against
   `grid-curtailment-policy`. A dispatch-down is indistinguishable in `power_kw`.
3. **Environment.** Confirm the icing window from site met data, not nacelle instruments alone.
4. **Fleet coherence.** Compare all 18 turbines. Icing, dust and heat hit the whole site within
   one or two intervals. A deficit on one turbine while 17 peers are normal under identical met
   conditions is **not** an environmental explanation.

## 5. Ice detection methods and their confidence

| Method | Signature | At Kutch | Confidence |
|---|---|---|---|
| Power curve deviation, normal vibration and pitch | -8 % to -35 % partial-load residual inside an icing window | Yes, SCADA | Low alone; suggestive with section 2 met |
| Rotor imbalance | 1P tower response, 0.143 Hz at 8.6 rpm to 0.256 Hz at 15.4 rpm | No tower accelerometer fitted | High if measured; not obtainable from SCADA |
| Drivetrain broadband vibration | Small rise from the 2.0 mm/s baseline; ice alone rarely reaches the 4.5 mm/s warning | Yes | Low; the HSS-housing sensor is insensitive to 1P |
| Heated vs unheated anemometer differential | Unheated reads low or freezes; heated tracks met mast | Heated nacelle unit assumed | Medium |
| Dedicated ice detector (resonant, ultrasonic) | Direct accretion signal | Not fitted | High where fitted |
| Nacelle or blade camera, ground visual at standstill | Direct observation | Manual, daylight | Definitive |
| Failure to start | Rotor stationary above 3.0 m/s with no fault code | Yes | Medium |

Honest limitation: with the assumed instrumentation RAI can produce an icing *hypothesis* from
met conditions plus a power residual, and cannot produce an ice *measurement*. Any evidence
packet citing this document must carry that distinction.

## 6. Shutdown, exclusion zones and restart

**Stop and feather to 90 deg** when an icing window is open and any one of:
`drivetrain_vibration_mms` above the 4.5 mm/s warning; a measured 1P imbalance; ice visually
confirmed on any blade; or a partial-load power residual beyond -25 % with instrumentation
validated per section 4.

**Ice-throw exclusion zone:** radius 258 m from the tower base, being
1.5 x (hub height 80 m + rotor diameter 92 m). Extend to 390 m downwind in glaze conditions.
Barrier and sign the access road at the boundary, notify the control room, log the closure. No
entry while a blade carries ice unless the turbine is stopped **and** the rotor locked.

**Restart — all four required:** `ambient_temp_c` above +2.0 degC for 3 h continuous; no
precipitation in the preceding 1 h; visual confirmation of clean blades where daylight allows;
and power within 3 % of the expected curve for 60 min above 5 m/s after reconnection. Automatic
restart from an icing stop is disabled; restart is a manual, logged decision by the site
reliability engineer.

## 7. Blade heating

Not fitted at Kutch; documented for fleet portability because the economics generalise. Assume
electrothermal leading-edge mats, 30 kW per blade, 90 kW total, 4.5 % of the 2,000 kW rating.
Anti-ice runs pre-emptively while producing; de-ice runs at standstill to shed an accretion,
typically 2 - 6 h. Economic gate at the wind tariff of INR 3.20 per kWh and the 680 kWh per
standstill hour assumption from `wind-gearbox-system` section 9: a 4 h de-ice cycle consumes
360 kWh, INR 1,152, against 4 h of standstill at 2,720 kWh, INR 8,704. Heating is authorised
whenever it is expected to shorten the outage at all. The comparison is computed by the
economics module, not estimated in the field — see `om-economics-policy`.

## 8. High wind and turbulence

| Condition | Threshold | Action |
|---|---|---|
| Cut-out, 10-min mean | 25.0 m/s | Feather to 90 deg, generator offline |
| Gust cut-out, 3 s | 30.0 m/s | Immediate feather at the 12 deg/s emergency rate |
| Storm derate band | 22.0 - 25.0 m/s | Progressive load-reducing torque derate |
| Reconnect hysteresis | 10-min mean below 22.0 m/s for 10 min | Automatic restart permitted |
| High turbulence | Turbulence intensity above 0.25 at or above rated | Derate; log as a fatigue-load event |

Repeated cut-out cycling near 25.0 m/s costs availability and is correct behaviour. Report it as
availability, never as performance degradation, and check `status_code` before trending
anything measured in a storm week.

## 9. Dust storms

Kutch and Charanka carry heavy dust loading March to June.

**Wind.** Cooler fins foul, raising `gearbox_oil_temp_c` with **no** vibration change — the
cooler-fouling row in `wind-gearbox-system` section 3. Use the 6-month dust-season fin cleaning
interval. Dust biases anemometer and vane readings; revalidate per `scada-sensor-validation-sop`
after every event. Cumulative leading-edge erosion is the long-term cost and never reverses.

**Solar.** Baseline soiling accrues at 0.15 - 0.35 %/day in the dry season; one storm can step
performance down 1.5 - 3.0 % inside a single interval, and rainfall above about 4 mm/day
substantially resets it. The discriminator is simultaneity: a step across all 24 inverters is
soiling; a step on one inverter or one string is not. Escalate cleaning per
`solar-soiling-cleaning-sop`, and never raise a string fault without `solar-string-fault-sop`
and `solar-iv-curve-sop`.

## 10. Extreme heat

**Wind.** Gearbox oil runs about 38 K above ambient at full load (42 min time constant), main
bearing about 26 K (55 min), generator winding about 62 K (18 min). At 45 degC ambient expect
roughly 83 degC oil, 71 degC main bearing, 107 degC winding. Oil is then past its 75 degC
warning and at the 80 degC alarm and the main bearing past its 70 degC warning **with no fault
present**, while the winding stays far below its 145 degC alarm. Apply a torque derate to hold
oil below 80 degC and record it as ambient-limited. Full alarm ladders: `wind-gearbox-system`
section 5. Suppress thermal fault hypotheses while `ambient_temp_c` moves faster than 3 K/h, and
require two time constants (84 min for oil) of stable conditions before accepting an exceedance
— see `wind-generator-thermal-sop`.

**Solar.** Module power follows the -0.004 /K coefficient: at NOCT 45 degC the module is 20 K
above STC, an 8.0 % loss; a 65 degC cell in a heat event is 40 K above STC, a 16.0 % loss. That
is physics, not degradation. Inverters derate above 45 degC heatsink temperature and hard trip
at 75 degC, so a fleet-wide mid-afternoon clipped-shaped deficit is thermal derate. Per-unit
deviation is the fault signal — `solar-inverter-thermal-sop`.

## 11. Attribution rule (binding)

A power deficit whose samples fall inside an open icing window, a storm cut-out period, a
dust-storm step or a heat derate is attributed to that environmental cause. The equipment-fault
hypothesis may be raised **only** if the conditioned residual — conditioned on validated wind
speed, air density, pitch angle, curtailment flag and peer behaviour — persists at least 48 h
after the window closes, at a magnitude within one standard error of the in-window residual. If
it does not persist, close the anomaly as `environmental_explained`, record the met evidence and
raise no ticket. Confidence below the agent threshold escalates to human review rather than
guessing between icing, pitch and erosion.

## Related documents

`scada-sensor-validation-sop`, `grid-curtailment-policy`, `wind-pitch-yaw-system`,
`wind-gearbox-system`, `wind-vibration-analysis-sop`, `wind-generator-thermal-sop`,
`wind-yaw-alignment-sop`, `solar-soiling-cleaning-sop`, `solar-inverter-thermal-sop`,
`solar-string-fault-sop`, `solar-iv-curve-sop`, `solar-dc-string-system`,
`alarm-response-matrix`, `om-economics-policy`, `incident-log-wind-gearbox`.
