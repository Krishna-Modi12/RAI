---
doc_id: wind-gearbox-system
title: Wind Turbine Gearbox and Drivetrain System Manual
asset_type: wind_turbine
component: gearbox
kind: manual
version: "2.1"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 2 MW geared wind turbine.
> This is not manufacturer documentation and is not attributable to any OEM. All figures are
> project-defined engineering assumptions unless a section states a measured source.

## 1. Scope and reference machine

This manual describes the drivetrain of the generic 2 MW geared turbines modelled at the
Kutch Wind Farm site (asset ids `WT-001` .. `WT-018`). It defines the machine constants that
every other wind document in this corpus depends on, the failure modes the condition
monitoring layer is expected to catch, and the alarm limits used by the RAI detectors.

Related documents:

- `wind-gearbox-inspection-sop` — the inspection procedure and the threshold table that
  triggers field action.
- `wind-vibration-analysis-sop` — spectral interpretation of a vibration exceedance.
- `wind-oil-sampling-sop` — oil sampling and laboratory limits.
- `wind-bearing-replacement-sop` — the intervention, up-tower and down-tower.
- `wind-generator-system` — the load side of the high speed shaft.
- `scada-sensor-validation-sop` — run this **before** accepting any exceedance as real.

## 2. Reference machine constants

| Parameter | Value | Unit |
|---|---|---|
| Rated electrical power | 2,000 | kW |
| Rotor diameter | 92 | m |
| Hub height | 80 | m |
| Cut-in wind speed | 3.0 | m/s |
| Rated wind speed | 12.5 | m/s |
| Cut-out wind speed | 25.0 | m/s |
| Rotor speed range | 8.6 - 15.4 | rpm |
| Gearbox ratio | 1 : 97.5 | - |
| High speed shaft (HSS) speed range | 839 - 1,502 | rpm |
| Generator synchronous speed (4-pole, 50 Hz) | 1,500 | rpm |
| Gearbox configuration | 1 planetary + 2 helical stages | - |
| Lubricant | ISO VG 320 synthetic PAO gear oil | - |
| Oil sump volume | 320 | L |
| Filtration | 10 um inline, 5 um offline kidney loop | - |
| Oil cooler | Forced-air, thermostatic bypass opens at 45 | degC |
| Design life (gearbox) | 20 | years |

Derived frequencies used throughout the corpus, at nominal HSS speed of 1,500 rpm:

| Frequency | Formula | Value at 1,500 rpm HSS |
|---|---|---|
| HSS rotation (1x) | n / 60 | 25.0 Hz |
| Rotor rotation | HSS / 97.5 | 0.256 Hz (15.4 rpm) |
| HSS gear mesh (22-tooth pinion) | 22 x 25.0 | 550 Hz |
| HSS bearing BPFO (16 elements, d/D = 0.20) | (N/2)(1 - d/D) x f_r | 160 Hz |
| HSS bearing BPFI | (N/2)(1 + d/D) x f_r | 240 Hz |

Bearing geometry above is an assumed generic 16-element cylindrical roller arrangement. It
exists so that the worked examples in `wind-vibration-analysis-sop` are reproducible, not
because any specific bearing is specified.

## 3. Drivetrain failure modes and their observable signatures

The signatures below are expressed in the exact telemetry tags RAI monitors, so that a
detector output can be mapped to a physical hypothesis.

| Failure mode | Typical progression | Primary signature | Secondary signature | Typical lead time |
|---|---|---|---|---|
| HSS bearing spalling | 2 - 10 weeks | `drivetrain_vibration_mms` rising, +15 to +40 % over load-matched baseline | `gearbox_oil_temp_c` +5 to +12 degC, Fe and Cr in oil rising | 2 - 6 weeks |
| Intermediate-stage gear tooth pitting | 2 - 6 months | Vibration rise concentrated at mesh orders, modest broadband rise | Oil PQ index rising, no temperature change early | 4 - 12 weeks |
| Planetary stage bearing wear | 3 - 12 months | Low-frequency vibration rise, weak broadband signal | Oil Fe rising, torque ripple | 6 - 20 weeks |
| Oil cooler fouling or fan failure | Days | `gearbox_oil_temp_c` +8 to +20 degC with **no** vibration change | `nacelle_temp_c` elevated, derate at high ambient | Immediate |
| Low oil level or degraded oil | Weeks | Oil temperature rise, viscosity out of band | Vibration rise only late | 1 - 4 weeks |
| Misalignment or coupling wear | Weeks | Vibration at 1x and 2x HSS | Generator bearing temperature rise | 2 - 8 weeks |
| Sensor fault (accelerometer or RTD) | Instant | Step change, frozen value, or physically impossible value | **No** corroborating signal moves | n/a |

The discriminator that matters most in practice is the last row against the first. A single
signal moving alone is a sensor hypothesis until proven otherwise. A **co-signature** of
rising vibration *and* rising oil temperature *and* a negative power residual, with peers
unaffected, is the classic bearing degradation pattern - see
`INC-2024-014-gearbox-bearing-spalling`.

## 4. Monitored SCADA tags

| Tag | Unit | Cadence | Role in diagnosis |
|---|---|---|---|
| `drivetrain_vibration_mms` | mm/s | 10 min | Broadband RMS, 10 - 1,000 Hz, nacelle accelerometer at the HSS bearing housing |
| `gearbox_oil_temp_c` | degC | 10 min | Sump RTD downstream of the cooler bypass |
| `main_bearing_temp_c` | degC | 10 min | Main (rotor) bearing housing RTD |
| `generator_winding_temp_c` | degC | 10 min | Hottest-phase winding RTD, see `wind-generator-system` |
| `nacelle_temp_c` | degC | 10 min | Cooling headroom; confounds all thermal residuals |
| `power_kw` | kW | 10 min | Load reference for every residual |
| `rotor_rpm` | rpm | 10 min | Speed reference; converts frequency orders to Hz |
| `pitch_angle_deg` | deg | 10 min | Distinguishes curtailment and derate from fault |
| `wind_speed_ms` | m/s | 10 min | Nacelle anemometer - bias-prone, validate first |
| `status_code`, `operating_state` | int, str | 10 min | Availability and curtailment context |

Important limitation: the SCADA vibration tag is a **single broadband RMS value**. Order
analysis, envelope demodulation and bearing defect frequency identification require a
portable spectrum capture during a site visit. The corpus therefore never claims a spectral
conclusion from SCADA alone - see `wind-vibration-analysis-sop` section 3.

## 5. Absolute alarm limits (SCADA, independent of residuals)

These are hard limits. They apply regardless of what any model expects.

| Tag | Normal band at 80 - 100 % load | Warning | Alarm | Trip |
|---|---|---|---|---|
| `gearbox_oil_temp_c` | 50 - 68 degC | 75 degC | 80 degC | 85 degC |
| `main_bearing_temp_c` | 40 - 62 degC | 70 degC | 78 degC | 82 degC |
| `generator_winding_temp_c` | 95 - 130 degC | 140 degC | 150 degC | 160 degC |
| `drivetrain_vibration_mms` | 3.2 - 3.8 mm/s | 4.0 mm/s | 5.6 mm/s | 7.1 mm/s |
| `nacelle_temp_c` | 25 - 45 degC | 50 degC | 60 degC | - |

Cold-start inhibit: do not load the gearbox above 25 % rated torque until
`gearbox_oil_temp_c` exceeds 10 degC. In Gujarat this only matters on winter mornings after
a long standstill.

## 6. Load and ambient normalisation

Every gearbox thermal limit above is stated at steady load. Raw comparisons against them
produce false alarms, because oil temperature is driven by three things: transmitted torque,
ambient temperature, and cooler effectiveness. The residual models in RAI therefore predict
`gearbox_oil_temp_c` from `power_kw`, `rotor_rpm`, `ambient_temp_c` and `nacelle_temp_c`, and
the diagnostic quantity is the **residual**, not the raw value.

Rules of thumb for manual sanity checks:

- Oil temperature rises roughly 0.35 degC per 1 degC of ambient rise, at constant load.
- Oil temperature rises roughly 12 - 16 degC from 25 % to 100 % load.
- Vibration broadband RMS rises roughly 0.6 - 0.9 mm/s from 25 % to 100 % load.
- A residual that tracks ambient temperature is a cooling problem, not a bearing problem.
- A residual that persists across the full load range is a mechanical problem.

A thermal exceedance that only appears in the afternoon, disappears overnight and correlates
with `nacelle_temp_c` is a cooling-capacity finding. Check the cooler and fan before opening
any gearbox inspection order.

## 7. Lubrication schedule

| Task | Interval | Note |
|---|---|---|
| Oil sample for laboratory analysis | 6 months, or within 7 days of any vibration Zone B escalation | `wind-oil-sampling-sop` |
| Inline filter element change | 12 months or on differential pressure alarm | 10 um |
| Offline (kidney loop) element change | 12 months | 5 um |
| Oil change | 60 months, or on laboratory recommendation | 320 L, ISO VG 320 PAO |
| Cooler fin cleaning | 12 months, 6 months in dust season | Kutch dust loading is high March - June |
| Magnetic plug and chip detector inspection | 6 months | Photograph debris before cleaning |
| Breather desiccant replacement | 12 months | Monsoon humidity drives water ingress |

## 8. Escalation and decision authority

| Condition | Owner | Required response |
|---|---|---|
| Vibration Zone B (watch) | Site reliability engineer | Trend review within 7 days |
| Vibration Zone B with thermal co-signature | Site reliability engineer | On-site inspection within 72 h, per `wind-gearbox-inspection-sop` section 4.4 |
| Vibration Zone C (alarm) | O&M manager | Inspection within 24 h, consider torque derate |
| Vibration Zone D (trip) | O&M manager | Stop the turbine, do not restart before inspection |
| Oil laboratory alarm limit exceeded | Site reliability engineer | Inspection within 72 h, resample |
| Any exceedance with a suspect sensor | Site reliability engineer | Validate the sensor first, per `scada-sensor-validation-sop` |
| Confirmed spalling with rising trend | Asset manager | Plan intervention inside the trend-derived window |

An equipment fault is never asserted while an environmental or sensor explanation remains
open. This is a project rule, and it exists because the cost of a wrong alarm is a wasted
crew mobilisation plus lost trust in the system - see
`INC-2025-003-anemometer-drift-false-alarm`.

## 9. Cost and downtime planning assumptions

Figures from the project economic registry (`COMPONENT_ECONOMICS`, component `gearbox`),
stated so that field decisions and the economics module use the same numbers.

| Item | Assumption |
|---|---|
| Inspection cost | INR 85,000 |
| Planned repair cost | INR 1,250,000 |
| Unplanned failure cost | INR 4,500,000 |
| Planned downtime | 36 h |
| Unplanned downtime | 288 h |
| Secondary damage multiplier if run to failure | 1.9 x |
| Energy tariff used for lost production | INR 3.20 per kWh |

At a capacity factor of 0.34, one hour of standstill is 680 kWh, or INR 2,176 of lost
revenue. A 288 h unplanned outage is therefore roughly INR 626,000 of lost production on top
of the repair cost. This asymmetry, a factor of about 3.6 between unplanned and planned
repair cost, is the whole economic argument for acting on a 72-hour inspection trigger.
