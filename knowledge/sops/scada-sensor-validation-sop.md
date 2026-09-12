---
doc_id: scada-sensor-validation-sop
title: SCADA Sensor Validation Procedure
asset_type: both
component: instrumentation
kind: sop
version: "2.1"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content covering SCADA instrumentation validation
> at a generic wind and solar site. This is not manufacturer documentation and is not
> attributable to any OEM. All figures are project-defined engineering assumptions unless a
> section states a measured source.

## 1. Scope and why this procedure runs first

This procedure validates the SCADA measurement chain for the Kutch Wind Farm (`WT-001` ..
`WT-018`) and the Charanka Solar Park (`INV-001` .. `INV-024`) before any residual,
exceedance or anomaly score is accepted as evidence of an equipment fault.

It runs first because **instrumentation fault is the single most common cause of a false
equipment alarm on this site class**. A detector sees a channel, not a machine. A drifting
nacelle anemometer, a shorted RTD, a soiled pyranometer or a stuck current transformer all
produce exactly the shape a degradation model is trained to flag: a persistent, one-sided,
load-correlated deviation from expected behaviour. Nothing in the residual distinguishes the
two cases. Wind speed is the worst offender — power below rated goes as the cube of wind
speed, so a **10 % anemometer bias produces about a 33 % apparent power deficit** on a
healthy turbine. See `INC-2025-003-anemometer-drift-false-alarm`.

**Rule out first.** No equipment conclusion may be issued until this procedure returns a
disposition for every channel that contributed to it, *and* the environmental and
curtailment checks in section 10 have been cleared.

## 2. The cross-validation principle

Validate every channel against a **physically independent** channel — different sensor,
different signal path, different failure mechanism. Never validate a channel against itself,
its own historical mean, or a derived quantity that already contains it. Three binding
consequences:

- A range check is not a validation. A failed RTD reading 61 °C is inside every limit in
  `wind-gearbox-system` section 5.
- A single channel moving alone is a **sensor hypothesis** until a physically independent
  channel corroborates it.
- Peer comparison is only independent when the peer's sensor is independent. Eighteen
  turbines sharing one met mast do not cross-validate wind speed; they share a common mode.

## 3. Wind channel cross-checks

| Channel | Independent reference | Expected relationship | Validity window |
|---|---|---|---|
| `wind_speed_ms` | `rotor_rpm` | Below rated the rotor tracks optimal tip speed ratio λ ≈ 5.9: `v_implied = 0.816 × rotor_rpm` (m/s) | 8.6 - 15.4 rpm, i.e. 7.0 - 12.5 m/s; unusable at the 8.6 rpm speed floor |
| `wind_speed_ms` | Unwaked neighbour turbines | 10-min means agree within 6 % | Free sectors only |
| `wind_direction_deg` (vane) | `yaw_position_deg` history | The yaw controller nulls the vane, so the 7-day median yaw error sits near 0° | Running, > 5 m/s |
| `power_kw` | Generator current × voltage | P ≈ √3 · V · I · pf; at 690 V terminal voltage (project assumption) rated 2,000 kW is ≈ 1,675 A at unity pf | Above 20 % load |
| `gearbox_oil_temp_c` | `ambient_temp_c` + modelled load rise | Rise ≈ 22 K + 16 K × (`power_kw` / 2,000), i.e. 38 K at rated — consistent with `wind-gearbox-system` section 6 | Steady load ≥ 30 min |
| `main_bearing_temp_c` | Ambient + load | Rise ≈ 26 K at rated | Steady load |
| `generator_winding_temp_c` | The other two phase RTDs | Phase spread > 12 K at steady load is an RTD fault **or** real unbalance — separate with phase currents, see `wind-generator-thermal-sop` | Above 40 % load |
| `drivetrain_vibration_mms` | `power_kw` | RMS must rise 0.6 - 0.9 mm/s from 25 % to 100 % load off a ~2.0 mm/s baseline; a channel that ignores load is loose-mounted or dead | Load sweep available |

## 4. Solar channel cross-checks

| Channel | Independent reference | Expected relationship |
|---|---|---|
| POA irradiance | Clear-sky model | On a clear day the measured/clear-sky ratio is smooth and symmetric about solar noon; a flat-topped or asymmetric ratio is soiling on the *sensor*, not the array |
| POA irradiance | Fleet-median implied irradiance, 24 inverters | Agreement within 10 %; one disagreeing pyranometer is a sensor finding, a fleet-wide offset is atmospheric |
| Inverter AC power | Inverter DC power | `P_ac / P_dc` must lie between 0.95 and 0.988. Above 0.988 exceeds peak inverter efficiency and is **physically impossible** — one meter is wrong |
| String current (20 per inverter) | Median of the other 19 strings | Nominal 9.2 A at STC; ≥ 10 % below median is a string finding for `solar-string-fault-sop` |
| String current reading 0.0 A | Inverter total DC current | If total DC current still accounts for the missing ≈ 9.2 A, the **CT has failed**, not the string. Never dispatch on a dead string before this check |
| Module temperature | NOCT model | `T_mod ≈ T_amb + 25 × G / 800`; at 1,000 W/m² and 35 °C ambient ≈ 66 °C, implying −16.4 % power at −0.004 /K |
| Heatsink temperature | Ambient + inverter loss | Loss at rated ≈ 4.5 kW (250 kW at 98.2 %); derate from 45 °C, trip 75 °C, see `solar-inverter-thermal-sop` |
| Site export meter | Σ inverter AC power | Monthly energy agreement within 2 % |

## 5. Frozen channel and impossible value tests

**Frozen channel.** Flag a channel FROZEN on **6 consecutive bit-identical samples while the
asset is running** — 60 min on wind (10-min cadence), 90 min on solar (15-min cadence, with
irradiance > 50 W/m²). Exempt legitimately constant channels: `pitch_angle_deg` parked at
0.0° below rated, status and operating-state codes, and anything while the asset is stopped.

**Physically impossible step.** Over one 10-min sample a first-order thermal channel can
reach only 1 − e^(−10/τ) of its final change.

| Channel | Time constant | Max plausible 10-min step |
|---|---|---|
| `gearbox_oil_temp_c` | ~42 min | 8 K |
| `main_bearing_temp_c` | ~55 min | 6 K |
| `generator_winding_temp_c` | ~18 min | 25 K |

A larger step is RTD, wiring or transmitter, not thermodynamics. Also reject: negative
irradiance beyond −5 W/m², wind speed above 40 m/s, string voltage above 820 V open-circuit,
and any temperature outside −20 to +200 °C.

## 6. Drift detection and disposition thresholds

Compute the rolling **7-day median** of the disagreement between the channel and its
independent reference, restricted to the validity window in sections 3 and 4. Use the median,
not the mean; a handful of communication dropouts must not set a disposition.

| Systematic disagreement | Disposition |
|---|---|
| < 10 % | OK |
| 10 % to < 16 % | **SUSPECT** |
| ≥ 16 % | **FAILED** |

For thermal channels the percentage is taken against the nominal rise, which makes the
trigger concrete:

| Channel | Nominal rise | SUSPECT at | FAILED at |
|---|---|---|---|
| `gearbox_oil_temp_c` | 38 K | 3.8 K | 6.1 K |
| `generator_winding_temp_c` | 62 K | 6.2 K | 9.9 K |
| `main_bearing_temp_c` | 26 K | 2.6 K | 4.2 K |

Vane bias is stated in degrees, not percent: 7-day median yaw error > 5° is SUSPECT, > 8° is
FAILED. An 8° standing misalignment costs about 2.9 % of energy (cos³ θ) — route to
`wind-yaw-alignment-sop`.

## 7. Timestamp and communication integrity

A clean-looking value at the wrong time corrupts every residual that pairs two channels.

- Controller-to-historian clock skew must be ≤ 2 s; beyond that, suspend all cross-channel
  residuals for that asset.
- Reject duplicate and non-monotonic timestamps. All site timestamps are tz-aware UTC.
- A gap of more than 3 consecutive missing samples (30 min wind, 45 min solar) voids the
  frozen-channel counter; recompute the 7-day drift window on the remaining data.
- Packet loss above 2 % of expected samples in 24 h raises a data-quality flag. Availability
  and energy-loss figures for that day are not citable.

## 8. Calibration record

Every channel carries a record: tag, sensor serial, installation date, last calibration date,
calibration due date, method, deviation found, technician. The record is the audit trail an
alarm is defended with.

| Sensor | Interval |
|---|---|
| Nacelle anemometer | 24 months, or replace on damage |
| Nacelle wind vane | 24 months |
| RTDs (oil, bearing, winding) | 36 months |
| Accelerometers | 36 months |
| Generator CT / VT | 60 months |
| POA pyranometer | 12 months |
| Reference cell | 12 months |

**Hard rule:** a channel whose calibration is overdue by more than 90 days is automatically
SUSPECT regardless of how well it cross-checks.

## 9. Disposition and its effect on an equipment conclusion

| Disposition | Effect on the diagnosis | Action |
|---|---|---|
| OK | Evidence usable at full weight | Proceed |
| SUSPECT | **Downgrades** the conclusion: severity capped at watch, no crew mobilisation on that channel alone, a corroborating independent channel is required before escalation | Schedule verification at next planned visit |
| FAILED | **Blocks** the conclusion entirely. No equipment fault may be asserted from a channel or from any residual that consumes it | Raise a sensor work order; equipment assessment resumes only after replacement plus 72 h of clean cross-check data |

A FAILED sensor is not an equipment alarm and must never be reported as one. It is also not
nothing: it is an availability and data-integrity defect with its own ticket.

## 10. Rule-out sequence before authorising any intervention

Run in order. Stop at the first step that explains the deficit.

1. **Instrumentation** — sections 3 to 8 of this document.
2. **Curtailment and grid** — check `status_code`, `operating_state`, active power setpoint
   and grid frequency against `grid-curtailment-policy`. A dispatch curtailment reproduces a
   power deficit exactly.
3. **Environment** — wind: icing, high turbulence, wake sector, see
   `weather-icing-operations-sop`. Solar: soiling at 0.15 - 0.35 %/day dry-season
   accumulation, reset by rainfall above ~4 mm/day, see `solar-soiling-cleaning-sop`.
4. **Peers** — if all 18 turbines or all 24 inverters move together, it is not one machine.
5. **Only then** open the equipment procedure in `alarm-response-matrix`.

## Related documents

`wind-gearbox-system`, `wind-generator-system`, `wind-pitch-yaw-system`,
`wind-gearbox-inspection-sop`, `wind-vibration-analysis-sop`, `wind-oil-sampling-sop`,
`wind-bearing-replacement-sop`, `wind-generator-thermal-sop`, `wind-yaw-alignment-sop`,
`weather-icing-operations-sop`, `solar-inverter-system`, `solar-dc-string-system`,
`solar-inverter-thermal-sop`, `solar-string-fault-sop`, `solar-soiling-cleaning-sop`,
`solar-iv-curve-sop`, `incident-log-wind-gearbox`, `incident-log-solar-inverter`,
`om-economics-policy`, `grid-curtailment-policy`, `alarm-response-matrix`
