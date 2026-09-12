---
doc_id: wind-yaw-alignment-sop
title: Yaw and Pitch Alignment Verification
asset_type: wind_turbine
component: yaw_system
kind: sop
version: "1.2"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content on yaw alignment and pitch calibration
> verification for a generic 2 MW pitch-regulated turbine. Not manufacturer documentation,
> not attributable to any OEM. All figures are project-defined engineering assumptions unless
> a section states a measured source.

## 1. Scope and trigger conditions

Verifies that the rotor points into the wind and that the three blades pitch to the angle the
controller believes. Applies to `WT-001` .. `WT-018`. System constants live in
`wind-pitch-yaw-system`; this document tests them rather than restating them. Run when:

- A power residual of -2 % or worse persists across the partial-load band (3.0 - 12.5 m/s)
  with **no** thermal and **no** vibration co-signature.
- Indicated yaw misalignment exceeds the +/- 8 deg control deadband for over 30 s in more than
  10 % of production records in a 7-day window.
- Rated power (2,000 kW) is reached below 12.5 m/s indicated wind, or not reached well above.
- After work on nacelle-top instrumentation, the yaw ring, a pitch axis, or a blade; or on the
  12-month schedule in `wind-pitch-yaw-system` section 7.

## 2. Rule out first (mandatory)

A yaw or pitch calibration error produces a power deficit with no thermal and no vibration
signature. So do a drifting anemometer, curtailment, and icing. The deficit alone does not
separate them. Close all four checks and record each outcome in the work order before
authorising nacelle-top or hub work; `alarm-response-matrix` rejects a ticket that lacks them.

1. **Instrumentation.** Run `scada-sensor-validation-sop` against `wind_speed_ms`,
   `wind_direction_deg`, `rotor_rpm` and `power_kw`. A failed vane or anemometer invalidates
   every yaw number in SCADA, including the misalignment that raised the alarm.
2. **Curtailment.** Confirm per `grid-curtailment-policy` that no setpoint, frequency-response
   event or feeder constraint covers the window. `pitch_angle_deg` above 3 deg below 12 m/s is
   a control action until proven otherwise, not an aerodynamic loss.
3. **Environment.** Check `weather-icing-operations-sop`, and check sector dependence. A
   deficit confined to one wind-direction sector is wake or terrain, not calibration.
4. **Peers.** Compare the nearest three turbines under the same inflow. A fleet-wide deficit in
   the same hours is a site or grid cause; a single-turbine deficit that persists across
   sectors and wind speeds is a machine cause, and this SOP proceeds.

## 3. Yaw misalignment and its energy cost

Available power scales with the cube of the flow component normal to the rotor:

    P(theta) / P(0) = cos(theta) ^ 3

| Static yaw error | Power loss | Annual revenue loss at INR 3.20/kWh |
|---|---|---|
| 5 deg | 1.1 % | INR 211,000 |
| 10 deg | 4.5 % | INR 858,000 |
| 15 deg | 10.0 % | INR 1,906,000 |
| 20 deg | 17.0 % | INR 3,240,000 |

Revenue assumes 5,957 MWh per turbine per year (2,000 kW at capacity factor 0.34, consistent
with `wind-gearbox-system` section 9) and a static error across all operating hours. A
sector-dependent misalignment costs proportionally less.

Interpretation rule: 10 deg accounts for 4.5 percentage points of deficit and no more. If the
residual is -12 %, yaw explains a third of it and the remainder stays open. The exponent 3 is
an upper bound — field fits land between 2 and 3 — so it is conservative when ruling yaw **in**
and non-conservative when ruling it **out**. Where the remainder after yaw is small, re-derive
with exponent 2 before declaring a second fault.

## 4. Measuring true misalignment

The nacelle vane cannot measure yaw error, for a structural reason: it is the controller's own
input. The loop drives the *measured* error to zero, so a vane with a 12 deg installation
offset yields a SCADA yaw error near 0 deg while the rotor sits 12 deg off the true wind. A
clean `yaw_error_deg` trace is evidence of a closed loop, not of alignment.

| Reference | Campaign | Uncertainty | Note |
|---|---|---|---|
| Nacelle-mounted forward-looking lidar | 5 - 10 days | +/- 0.5 deg | Two or more beams, 80 - 120 m focus, undisturbed inflow |
| Spinner anemometer | 14 days | +/- 1.0 deg | Ahead of the rotor wake; needs calibration constants |
| Met mast vs nacelle heading | 30 days | +/- 2.5 deg | Unwaked sectors only |
| Nacelle vane | n/a | not usable | Rotor wake and roof flow distortion; bias 3 - 8 deg |

Campaign acceptance: at least 500 ten-minute records in normal production, 5 - 12 m/s, no
curtailment flag. Take the circular mean of (reference inflow - nacelle heading) per 1 m/s bin.
A bin-independent constant is a static offset; scatter that grows with turbulence intensity is
a control-tuning problem, not a calibration problem.

## 5. Vane calibration and offset table

Correct in software. Do not rotate the vane mount to chase a number — the mount is the
mechanical reference for the next campaign.

| Measured static offset | Classification | Action |
|---|---|---|
| <= 1.0 deg | Within calibration | Log only |
| 1.0 - 2.0 deg | Acceptable | Recheck at 12 months |
| 2.0 - 5.0 deg | Drifted | Software offset at next scheduled visit |
| 5.0 - 10.0 deg | Significant | Offset within 14 days; loss above INR 200,000/yr |
| > 10.0 deg | Vane fault or wrong north mark | Replace or re-index; north mark within 2 deg of centreline |

After applying an offset, observe 72 h and confirm the power residual recovers by the amount
section 3 predicts. If it does not move, the offset was not the cause; reopen the ticket.

## 6. Pitch verification and blade asymmetry

Prerequisites: rotor locked, lockout-tagout applied, pitch backup energy store isolated and
confirmed below 50 V DC, hub entry per `wind-pitch-yaw-system` section 8. Not to be attempted
above 10 m/s at hub height.

Pitch each axis to 0 deg in service mode. Read a calibrated digital inclinometer on the blade
root flange machined face against the blade root 0 deg marking. Record all three blades at the
same rotor position to cancel gravity bias, then repeat 120 deg around.

| Quantity | Limit | Action if exceeded |
|---|---|---|
| Axis deviation from root marking | 0.3 deg | Recalibrate that axis before return to service |
| Blade-to-blade spread (max - min) | 0.5 deg | Recalibrate all three axes; rotor imbalance likely |
| Spread with 1P tower vibration at 0.26 Hz | 1.0 deg | Stop the turbine; structural loading finding |
| Mean offset across all three axes | 0.5 deg | Expect -2 to -6 % partial-load residual; recalibrate |

Honest limitation: SCADA records only the **mean** of the three axes, so asymmetry is not
detectable remotely. Any RAI statement about an individual blade is unevaluated until this
inspection exists, and must be reported as unevaluated rather than estimated.

## 7. Yaw drive and brake checks

| Check | Method | Acceptance |
|---|---|---|
| Yaw rate | Time a commanded 90 deg yaw | 180 s +/- 10 % (162 - 198 s) at 0.5 deg/s |
| Drive current balance | Log 6 drive currents through one yaw | No drive above 125 % of the six-drive mean |
| Ring gear backlash | Dial gauge at the ring gear | Below 1.5 deg |
| Brake pressure | Manifold gauge, clamped and yawing | 180 bar clamped; 25 - 35 bar while yawing |
| Brake decay | Hold 10 min from 180 bar | Below 10 bar decay |
| Cable twist counter | Loop mark vs counter | Within 30 deg; limit +/- 720 deg |

Current imbalance with audible knocking is gear tooth damage, not a calibration problem, and
routes to an inspection order rather than a software offset.

## 8. Excluding an anemometer fault

The anemometer is the most common source of an apparent pitch or yaw fault, because it feeds
the expected-power model. An instrument reading high makes a healthy turbine look deficient
across the whole partial-load band with no thermal or vibration co-signature — precisely the
pattern this SOP investigates.

| Symptom | Anemometer hypothesis | Alignment hypothesis | Discriminator |
|---|---|---|---|
| Negative residual at all wind speeds | Reads high by 3 - 8 % | Static yaw error | Power-curve-inferred wind vs indicated |
| Rated power below 12.5 m/s indicated | Reads high | Not explained by yaw | Rated point moves with the instrument |
| Positive residual, cut-in late above 3.0 m/s | Reads low; friction or icing | Not explained | Rotor turns at an indicated 2.5 m/s |
| Residual in one sector only | Waked by mast or neighbour | Sector-dependent vane bias | Peers in the same sector |
| Step change at a service date | Replaced or re-indexed | Vane or pitch re-index | Service log; check both |

Cross-check indicated wind against the power-curve inversion, the site met mast and the nearest
peers per `scada-sensor-validation-sop` section 4. If the anemometer fails, stop and recompute
the residual on the corrected wind reference before deciding whether an alignment finding still
exists. `INC-2025-003-anemometer-drift-false-alarm` in `incident-log-wind-gearbox` is the case:
a 7 deg apparent yaw error and a -6 % deficit were both artefacts of a drifted instrument.

## 9. Closure and escalation

| Outcome | Owner | Action |
|---|---|---|
| Offset within 2.0 deg, pitch in limits | Site reliability engineer | Close; log the campaign result |
| Offset 2.0 - 10.0 deg | Site reliability engineer | Apply offset, verify recovery over 72 h |
| Blade spread above 0.5 deg | O&M manager | Hub visit, recalibrate, re-verify before restart |
| Yaw drive or brake out of limits | O&M manager | Yaw inspection order, 10 h planned downtime |
| Residual unexplained after correction | Asset manager | Reopen as drivetrain or electrical |

Yaw planned repair is INR 260,000 against INR 640,000 unplanned, a ratio of about 2.5 x, low
enough that yaw findings normally wait for the next scheduled visit. The case for acting sooner
comes from lost production, not the repair: at 10 deg the annual deficit exceeds the planned
repair cost more than threefold. Use `om-economics-policy` for the intervention comparison.

## Related documents

- `wind-pitch-yaw-system` — constants, failure modes, schedule.
- `scada-sensor-validation-sop` — run **before** accepting any yaw or power number.
- `grid-curtailment-policy` — dispatch exclusions.
- `weather-icing-operations-sop` — icing as competing explanation.
- `wind-vibration-analysis-sop` — 1P imbalance, drivetrain path.
- `wind-gearbox-system` — machine constants.
- `wind-generator-system` — electrical-path causes.
- `incident-log-wind-gearbox` — `INC-2025-003-anemometer-drift-false-alarm`.
- `alarm-response-matrix` — routing and evidence fields.
- `om-economics-policy` — expected-loss comparison.
