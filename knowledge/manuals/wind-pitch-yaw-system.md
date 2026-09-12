---
doc_id: wind-pitch-yaw-system
title: Wind Turbine Pitch and Yaw System Manual
asset_type: wind_turbine
component: pitch_system
kind: manual
version: "1.3"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 2 MW pitch-regulated turbine.
> Not manufacturer documentation, not attributable to any OEM. Figures are project-defined
> engineering assumptions unless a section states a measured source.

## 1. Scope

Covers the electric blade pitch system, the yaw drive and brake, and the control behaviour
that both systems impose on the power curve. These systems matter to RAI mainly because they
are the most common **benign** explanation for a power deficit: a turbine that is pitching
or yawing for a control reason is not a faulty turbine.

Related: `wind-gearbox-system` (drivetrain loads), `scada-sensor-validation-sop` (wind vane
and anemometer validation), `INC-2025-003-anemometer-drift-false-alarm` (a yaw and power
deficit that turned out to be a sensor).

## 2. Reference system constants

| Parameter | Value | Unit |
|---|---|---|
| Pitch actuation | Electric, three independent axes | - |
| Pitch range | -1 to +90 (feather) | deg |
| Nominal pitch rate | 7 | deg/s |
| Emergency feather rate | 12 | deg/s |
| Backup energy store | Ultracapacitor bank per axis, 3 full feather cycles | - |
| Pitch bearing | Four-point double-row ball, greased | - |
| Yaw drives | 6 electric geared drives | - |
| Yaw rate | 0.5 | deg/s |
| Yaw brake | 8 hydraulic calipers, 180 bar clamped | bar |
| Yaw residual holding pressure while yawing | 25 - 35 | bar |
| Cable twist limit before untwist routine | +/- 720 | deg |
| Nacelle misalignment control deadband | +/- 8 | deg |
| Yaw misalignment triggering realignment | > 8 deg sustained 30 s | - |

## 3. Control behaviour by wind regime

Understanding these four regimes prevents most false power-deficit alarms.

| Regime | Wind speed | Expected `pitch_angle_deg` | Expected `rotor_rpm` | Expected `power_kw` |
|---|---|---|---|---|
| Below cut-in | < 3.0 m/s | 60 - 90 (parked or idling) | 0 - 4 | ~0 |
| Partial load | 3.0 - 12.5 m/s | -1 to +2 (tracking optimum) | 8.6 - 15.4, tracking tip-speed ratio | Follows power curve |
| Rated | 12.5 - 25.0 m/s | 2 - 28, rising with wind | 15.4, held constant | 2,000 |
| Above cut-out | > 25.0 m/s | 90 (feathered) | 0 - 1 | 0 |

The diagnostic consequences:

- **Pitch above 3 deg while wind is below 12 m/s** is not normal. It means curtailment, a
  derate, a thermal limit, or a pitch calibration error. It is not aerodynamic loss.
- **Pitch at 0 deg with rotor speed tracking correctly but power low** points to the
  electrical path or to an inflated wind reading, not to the pitch system.
- **Rated power reached at a wind speed noticeably below 12.5 m/s** is a strong hint that the
  anemometer reads high. Cross-check per `scada-sensor-validation-sop` section 4.

## 4. Failure modes and observable signatures

| Failure mode | Progression | Primary signature | Discriminator |
|---|---|---|---|
| Pitch bearing wear or corrosion | Months | Rising pitch motor current, slow pitch response, grease extrusion | Requires pitch controller log; not in SCADA |
| Pitch calibration offset on one blade | Step, after service | Power residual -2 to -6 % across the whole partial-load range, 1P tower vibration | `pitch_angle_deg` mean shifted; rotor imbalance at 0.26 Hz |
| Pitch motor or drive failure | Step | Fault code, turbine stop, single-axis feather | `status_code`, `operating_state` = stopped |
| Ultracapacitor bank ageing | Months | Self-test failures, capacity below 80 % | Annual self-test record |
| Yaw drive gear tooth damage | Weeks to months | Yaw motor current spikes, audible knocking, yaw overshoot | Backlash measurement at inspection |
| Yaw brake caliper leak | Weeks | Holding pressure decay, nacelle creep in gusts | Pressure decay test, section 7 |
| Wind vane misalignment | Step, after service | Sustained yaw misalignment, power residual -3 to -8 % | Compare vane to met mast direction |
| Cable twist sensor fault | Instant | Spurious untwist routines | Counter versus physical mark check |

Note the recurring theme: a yaw or pitch calibration error produces a power deficit with
**no thermal and no vibration co-signature**, exactly like a sensor fault. The two are
separated by whether an independent wind reference agrees with the nacelle instruments.

## 5. Yaw misalignment and its energy cost

Power in the wind scales with the cube of wind speed, and the component of flow normal to the
rotor scales with the cosine of the misalignment angle. The standard approximation for
misalignment loss is:

    P(theta) / P(0) = cos(theta) ^ 3

Worked values, for reference in work orders:

| Sustained yaw misalignment | Predicted power loss |
|---|---|
| 5 deg | 1.1 % |
| 8 deg | 2.9 % |
| 10 deg | 4.5 % |
| 15 deg | 10.0 % |
| 20 deg | 17.0 % |

Interpretation rule: a power residual of about -3 % accompanied by a sustained yaw
misalignment near 10 deg is fully explained by the misalignment. Do not escalate it as a
drivetrain finding. A power residual of -9 % with a misalignment of 5 deg is **not**
explained by yaw, and 8 percentage points of the deficit remain unaccounted for.

The exponent 3 assumes the loss acts on the full cube of the normal component. Field data
often fits an exponent between 2 and 3. Values in the table are therefore an upper bound on
the yaw-attributable loss, which is the conservative direction for ruling yaw **in** as an
explanation.

## 6. Monitored SCADA tags and limitations

| Tag | Unit | Role |
|---|---|---|
| `pitch_angle_deg` | deg | Mean of the three axes. Per-blade values are **not** in SCADA |
| `rotor_rpm` | rpm | Speed regulation check |
| `wind_direction_deg` | deg | Nacelle vane; site reference is `site_met.wind_direction_deg` |
| `wind_speed_ms` | m/s | Nacelle anemometer, bias-prone |
| `power_kw` | kW | Deficit magnitude |
| `status_code`, `operating_state` | int, str | Curtailment and stop context |

Honest limitation: because only the **mean** pitch angle is recorded, RAI cannot detect blade
pitch asymmetry from SCADA. Asymmetry detection requires the pitch controller log or a rotor
imbalance measurement, both of which are site-visit activities. Any statement about a single
blade must be marked as not evaluated until that data exists.

## 7. Inspection and test schedule

| Task | Interval | Acceptance criterion |
|---|---|---|
| Pitch bearing lubrication | 6 months | Grease quantity per axis as per lubrication chart; purge old grease |
| Pitch axis zero-position check | 12 months | All three axes within 0.3 deg of the reference mark |
| Pitch emergency feather test | 12 months | Full feather from 0 deg within 8 s on backup energy alone |
| Ultracapacitor capacity self-test | 12 months | Above 80 % of rated capacity, all axes |
| Yaw gear backlash measurement | 12 months | Below 1.5 deg at the ring gear |
| Yaw brake pressure decay test | 12 months | Less than 10 bar decay in 10 min from 180 bar |
| Yaw ring gear tooth inspection | 24 months | No spalling, no tooth-root cracking; photograph and log |
| Wind vane and anemometer alignment | 12 months | Vane north mark within 2 deg of nacelle centreline |
| Cable loop and twist counter check | 12 months | Physical mark agrees with counter within 30 deg |

## 8. Safety prerequisites

1. Rotor locked and lockout-tagout applied before entering the hub. The rotor lock is rated
   for static load only; do not rely on it in wind above 10 m/s at hub height.
2. Pitch backup energy store isolated and discharged before any work on a pitch axis. An
   ultracapacitor bank can feather a blade with the turbine dead. Confirm below 50 V DC.
3. Hub entry requires a second technician outside the hub, harness anchored to a certified
   point, and a filed rescue plan.
4. Yaw brake must be clamped and yaw drives isolated before any work on the yaw deck.
5. Do not defeat the pitch limit switches to obtain travel. If travel is needed, use the
   documented service mode.

## 9. Cost and downtime planning assumptions

From `COMPONENT_ECONOMICS`:

| Item | `pitch_system` | `yaw_system` |
|---|---|---|
| Inspection cost | INR 40,000 | INR 35,000 |
| Planned repair cost | INR 310,000 | INR 260,000 |
| Unplanned failure cost | INR 850,000 | INR 640,000 |
| Planned downtime | 12 h | 10 h |
| Unplanned downtime | 72 h | 60 h |
| Secondary damage multiplier | 1.3 x | 1.25 x |

Both systems have a modest unplanned-to-planned cost ratio, about 2.7 x for pitch and 2.5 x,
compared with 3.6 x for the gearbox. The practical consequence: pitch and yaw findings can
usually wait for the next scheduled visit unless a safety function is affected. A pitch
emergency-feather self-test failure is the exception and is always immediate, because it is a
loss of a protective function rather than a production problem.
