---
doc_id: solar-inverter-system
title: String Inverter System Manual
asset_type: solar_inverter
component: inverter
kind: manual
version: "2.0"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string inverter.
> This is not manufacturer documentation and is not attributable to any OEM. All figures are
> project-defined engineering assumptions unless a section states a measured source.

## 1. Scope and reference machine

This manual describes the string inverters and their DC input architecture at the Charanka
Solar Park site (asset ids `INV-001` .. `INV-024`). It is the reference document for every
other solar document in this corpus: it defines the machine constants, the conversion chain
from plane-of-array irradiance to exported AC power, the alarm limits used by the RAI
detectors, and the failure modes condition monitoring is expected to separate from
environmental lookalikes. It is the solar counterpart of `wind-gearbox-system`.

## 2. Reference inverter constants

| Parameter | Value | Unit |
|---|---|---|
| Rated AC power | 250 | kW |
| Units on site | 24 | - |
| DC/AC ratio | 1.25 | - |
| DC array capacity per inverter | 312.5 | kWp |
| Monitored DC inputs per inverter | 20 | - |
| Independent MPPT channels | 4 (5 monitored inputs each) | - |
| String open-circuit voltage, nominal | 820 | V |
| String MPP voltage, nominal | 640 | V |
| String current at STC | 9.2 | A |
| MPPT tracking window | 520 - 850 | V |
| Maximum system voltage | 1,000 | V |
| European efficiency | 98.2 | % |
| Peak efficiency | 98.8 | % |
| Module power temperature coefficient | -0.004 | /K |
| Module NOCT | 45 | degC |
| Heatsink derate onset | 45 | degC |
| Heatsink hard trip | 75 | degC |
| Energy tariff (solar) | 2.45 | INR/kWh |

## 3. DC input architecture

Each inverter presents 20 fused, individually monitored DC inputs feeding 4 independent MPPT
channels, 5 inputs per channel. Each input is protected by a 15 A gPV string fuse in both
poles and lands behind a Type 2 DC surge protective device per MPPT channel, with a Type 1+2
device at the array combiner. Insulation resistance to earth is measured before each morning
connection; below 1.0 MΩ the inverter refuses to connect and raises `E212`.

A monitored DC input is **not** a single source circuit. One source circuit at the nominal
MPP point delivers 640 V x 9.2 A = 5.89 kW at STC. The 312.5 kWp array therefore comprises 53
source circuits, landed as 13 inputs carrying 3 circuits and 7 inputs carrying 2 circuits:
53 x 5.89 kW = 312.1 kWp, within 0.2 % of nameplate. Expected steady-state current on a
3-circuit input at STC is 27.6 A; on a 2-circuit input, 18.4 A. **This matters for
diagnosis:** the loss of one source circuit shows as a 33 % or 50 % drop on one
`string_current_a` channel, not as a total channel outage, and costs about 1.9 % of array DC
power. Peer comparison is always against inputs of the same circuit count.

## 4. Conversion chain and clipping behaviour

The expected-power model evaluates, in order: POA irradiance → module temperature → DC array
power → MPPT and cabling losses → conversion efficiency → AC power, then applies the 250 kW
AC ceiling and any active thermal derate.

Conversion efficiency as a function of AC loading (project reference curve; the weighted
average reproduces the 98.2 % European efficiency figure):

| AC load | 5 % | 10 % | 20 % | 30 % | 50 % | 75 % | 100 % |
|---|---|---|---|---|---|---|---|
| Efficiency | 93.0 % | 96.0 % | 97.6 % | 98.3 % | 98.8 % | 98.6 % | 98.3 % |

At a DC/AC ratio of 1.25 the array is deliberately oversized, so the inverter clips on clear
mid-day hours. Clipping begins when available DC power exceeds 250 kW / 0.983 = 254.4 kW.
Because module temperature suppresses DC power, the irradiance at which clipping starts
depends on ambient temperature:

| Ambient | 20 degC | 25 degC | 30 degC | 35 degC | 40 degC |
|---|---|---|---|---|---|
| POA at clipping onset | ~900 W/m2 | ~920 W/m2 | ~945 W/m2 | ~971 W/m2 | ~999 W/m2 |

Clipped energy is a **modelled** quantity derived from the expected-power model, never a
measured one, and it is never reported as a fault. A flat 250 kW AC ceiling at high irradiance
is correct behaviour. A ceiling *below* 250 kW at high irradiance is a thermal derate finding —
see section 6.

## 5. Module temperature model

RAI conditions every solar residual on **module temperature, not ambient temperature**. The
module is the generating surface; at 900 W/m2 it runs 28 K above the air around it, and two
days with identical ambient temperature but different irradiance produce module temperatures
20 K apart. Conditioning on ambient alone leaves a systematic residual that looks exactly like
degradation.

The NOCT model used throughout the corpus:

```
T_module = T_ambient + ((NOCT - 20) / 800) * POA = T_ambient + 0.03125 * POA
P_dc = 312.5 kWp * (POA / 1000) * (1 - 0.004 * (T_module - 25)) * (1 - soiling_loss)
```

Worked example, Charanka in May: POA 900 W/m2, ambient 38 degC. Module temperature is
38 + 28.1 = 66.1 degC, a 41.1 K excursion above STC, so the power coefficient costs 16.4 %.
Expected clean DC power is 312.5 x 0.900 x 0.836 = 235.1 kW; at 94 % loading the efficiency is
about 98.4 %, giving 231.3 kW AC. At 5 % soiling the same conditions give 219.7 kW AC. An
operator seeing 220 kW against a 250 kW nameplate is looking at physics, not a fault.

Where a measured `module_temp_c` back-of-module RTD is healthy it overrides the model. The
model is the fallback when the RTD fails validation per `scada-sensor-validation-sop`.

## 6. Cooling design and derate schedule

Forced-convection heatsink with two variable-speed cabinet fans and a washable inlet filter.
Project assumptions: heatsink rises ~12 K above cabinet inlet air at 100 % load with a clean
filter, inlet air rises ~3 K above ambient, thermal time constant ~9 min. An inlet rise above
6 K is a blocked-filter finding in itself.

Derate schedule above 45 degC heatsink, 2.5 % of rating per K, floored at 25 %:

| `heatsink_temp_c` | 45 | 50 | 55 | 60 | 65 | 70 | 75 |
|---|---|---|---|---|---|---|---|
| AC power limit (kW) | 250 | 219 | 188 | 156 | 125 | 94 | 62.5 then trip |

In Charanka summer, clipping and thermal derate coincide: the inverter is simultaneously
irradiance-limited and temperature-limited. Distinguishing them is the point of monitoring
`heatsink_temp_c` alongside `ac_power_kw`. A power ceiling that tracks heatsink temperature is
a cooling finding; a ceiling flat at 250 kW is not.

## 7. Fault and alarm code families

| Family | Domain | Representative codes | Auto-reconnect |
|---|---|---|---|
| `E1xx` | Grid interface | `E101` under/over voltage, `E104` frequency out of band, `E108` anti-islanding | Yes, after 300 s |
| `E2xx` | DC input | `E205` string fuse open, `E208` reverse polarity, `E212` insulation < 1.0 MΩ, `E216` MPPT tracking fault | `E212` yes at next morning test; others no |
| `E3xx` | Thermal | `E301` heatsink derate active, `E305` fan stall, `E309` heatsink 75 degC trip | Yes, on cooldown below 60 degC |
| `E4xx` | Power stage | `E402` IGBT fault, `E407` DC link overvoltage, `E411` DC link capacitor imbalance | No, lockout |
| `E5xx` | Control, metering, comms | `E501` SCADA link loss, `E504` energy meter mismatch | Yes |

Codes with `W` prefixes (`W301`, `W212`) are the pre-alarm warnings at 80 % of the
corresponding trip threshold. Warnings are the condition-monitoring signal; trips are already
a production loss.

## 8. Monitored SCADA tags

| Tag | Unit | Cadence | Role in diagnosis |
|---|---|---|---|
| `poa_irradiance_wm2` | W/m2 | 15 min | Primary driver; two reference cells per site block |
| `module_temp_c` | degC | 15 min | Conditioning variable, back-of-module RTD |
| `ambient_temp_c` | degC | 15 min | NOCT model input and cooling headroom |
| `dc_power_kw`, `dc_voltage_v` | kW, V | 15 min | Per MPPT channel; MPP voltage should sit near 640 V |
| `string_current_a` | A | 15 min | 20 channels per inverter; peer comparison against same-circuit-count siblings |
| `ac_power_kw` | kW | 15 min | Output and residual reference |
| `heatsink_temp_c` | degC | 15 min | Derate state; see section 6 |
| `fan_speed_rpm` | rpm | 15 min | Cooling actuator health |
| `insulation_resistance_mohm` | MΩ | daily | Morning pre-connection test |
| `curtailment_setpoint_pct` | % | 15 min | Rules out grid-instructed limitation, `grid-curtailment-policy` |
| `status_code`, `operating_state` | int, str | 15 min | Availability and alarm context |

## 9. Expected performance ratio

| Quantity | Expected band | Note |
|---|---|---|
| Instantaneous PR, clear sky, clean array | 0.82 - 0.86 | Suppressed by module temperature at mid-day |
| Temperature-corrected PR | 0.88 - 0.92 | The quantity RAI trends; strips out weather |
| Monthly PR, dry season with scheduled cleaning | 0.76 - 0.80 | Soiling-limited |
| Inverter-to-fleet PR spread, healthy | within 2 pp of fleet median | Beyond 3 pp warrants investigation |
| Specific yield planning assumption | 4.6 kWh/kWp/day | 1,437 kWh/day per inverter |

These are design expectations, not measured site results. No PR figure is reported in the UI
unless it was computed from telemetry by the evaluation pipeline.

## 10. Failure modes and their observable signatures

| Failure mode | Progression | Primary signature | Secondary signature | Lead time |
|---|---|---|---|---|
| Thermal derate, blocked air path | Days - weeks | `heatsink_temp_c` +8 K or more over load- and ambient-matched baseline | Fans pinned at maximum, `W301`, afternoon-only deficit | Days |
| Cooling fan failure | Instant | `fan_speed_rpm` zero or erratic on one fan | `E305`, rapid derate at moderate load | Immediate |
| Source circuit outage | Instant | One `string_current_a` channel steps down 33 % or 50 % | Array DC power -1.9 %, PR step, siblings unchanged | Immediate |
| Gradual string degradation or PID | Weeks - months | One channel 3 - 8 % below sibling median, worsening with temperature | No step change, no alarm code | 4 - 12 weeks |
| MPPT tracking fault | Hours - days | Channel `dc_voltage_v` wandering outside 600 - 680 V with normal string currents | `E216`, channel power deficit while siblings track | Hours |
| DC link capacitor ageing | Months - years | Efficiency down 0.3 - 0.8 pp at matched load | Heatsink rise at constant load, `E411` late | 3 - 12 months |
| Power stage / IGBT fault | Instant | AC power to zero, `E402` lockout | DC voltage pinned at open circuit | Immediate |
| Insulation degradation | Weeks - months | Morning `insulation_resistance_mohm` trending toward 1.0 MΩ | Wet-morning-only `E212`, clears as array dries | 2 - 12 weeks |

**Lookalikes the system must not call a fault.** Each of these produces a convincing power
deficit on a healthy inverter:

- **Soiling.** Fleet-wide, slow, 0.15 - 0.35 %/day in the dry season, substantially reset by
  rainfall above ~4 mm/day. Affects all inverters together. See `solar-soiling-cleaning-sop`.
- **Cloud transients.** Fast, correlated with `poa_irradiance_wm2`, zero residual once
  conditioned on POA.
- **Curtailment.** `curtailment_setpoint_pct` below 100; a flat ceiling unrelated to
  irradiance or heatsink temperature. See `grid-curtailment-policy`.
- **Irradiance sensor fault.** A soiled or drifting reference cell shifts the residual of
  **every** inverter in its block simultaneously, with no inverter-level corroboration. This is
  the solar analogue of anemometer drift.
- **Clipping.** Correct behaviour, not a deficit.

## 11. Rule out first, then escalate

No equipment fault is asserted on this fleet while an environmental or instrumentation
explanation remains open. Before any deficit becomes a work order:

1. Validate the irradiance and module temperature channels per `scada-sensor-validation-sop`.
2. Check `curtailment_setpoint_pct` and the grid interface per `grid-curtailment-policy`.
3. Check soiling state and days since last rain or clean per `solar-soiling-cleaning-sop`.
4. Compare against the 23 peer inverters. A deficit shared by the fleet is not an
   inverter fault.
5. Only then isolate to the MPPT channel and string level per `solar-string-fault-sop`.

| Condition | Owner | Required response |
|---|---|---|
| Single channel 3 - 8 % below sibling median | Site technician | I-V trace within 7 days, `solar-iv-curve-sop` |
| Source circuit outage confirmed | Site technician | Fuse and connector check within 72 h |
| `E301` derate active on consecutive days | Site reliability engineer | Filter and fan inspection within 72 h, `solar-inverter-thermal-sop` |
| `E309` or `E402` | O&M manager | Same-day attendance, inverter offline |
| Insulation trending to 1.0 MΩ | Site reliability engineer | Wet-condition IR survey within 7 days |
| Any deficit with a suspect irradiance sensor | Site reliability engineer | Validate the sensor first; no work order |

## 12. Cost and downtime planning assumptions

From the project economic registry (`COMPONENT_ECONOMICS`, component `inverter`):

| Item | Assumption |
|---|---|
| Inspection cost | INR 12,000 |
| Planned repair cost | INR 180,000 |
| Unplanned replacement cost | INR 650,000 |
| Planned downtime | 6 h |
| Unplanned downtime | 72 h |
| Secondary damage multiplier if run to failure | 1.4 x |
| Energy tariff | INR 2.45 per kWh |

At 1,437 kWh/day per inverter, a 72 h unplanned outage costs about 4,310 kWh, or INR 10,560 of
lost production — small beside the INR 650,000 replacement. The economic argument on the solar
side is therefore **not** the outage cost of one inverter; it is the fleet-scale accumulation
of small, persistent deficits. A 2 % undetected deficit across all 24 inverters costs roughly
INR 617,000 per year, more than an unplanned inverter replacement. See `om-economics-policy`.

## Related documents

- `solar-dc-string-system` — the array side of the DC inputs described in section 3.
- `solar-inverter-thermal-sop` — the derate and cooling investigation procedure.
- `solar-string-fault-sop` — isolation of a string or channel deficit.
- `solar-iv-curve-sop` — I-V tracing to confirm a string-level finding.
- `solar-soiling-cleaning-sop` — the dominant environmental lookalike.
- `incident-log-solar-inverter` — worked historical cases for the failure modes in section 10.
- `scada-sensor-validation-sop` — run this **before** accepting any deficit as real.
- `grid-curtailment-policy` — curtailment context for every power residual.
- `alarm-response-matrix` — the code-to-action mapping for section 7.
- `om-economics-policy` — expected-loss method behind section 12.
- `wind-gearbox-system` — the wind-side reference document in the same style.
