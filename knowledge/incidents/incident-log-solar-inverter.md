---
doc_id: incident-log-solar-inverter
title: Solar Fleet Incident Log — Inverters and DC
asset_type: solar_inverter
component: inverter
kind: incident_log
version: "1.3"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as an
> illustrative incident log for a generic 24 x 250 kW string-inverter solar park. These cases
> are not real service records, are not manufacturer documentation and are not attributable to
> any OEM. All figures are project-defined engineering assumptions unless a section states a
> measured source.

## 1. Scope and how to read this log

Six closed cases from the Charanka Solar Park fleet (`INV-001` .. `INV-024`, 250 kW AC each,
312.5 kWp DC at a DC/AC ratio of 1.25, 20 string inputs per inverter). Each entry records what
the detector saw, **what was ruled out before an equipment cause was accepted**, the root cause
found on site, the intervention, and the money. Two of the six closed with **no equipment
ticket at all** — those are the most instructive entries in the file.

Planning constants used throughout, from `om-economics-policy`: clear-day production
1,250 kWh per inverter (site ≈ 30,000 kWh/day), solar tariff INR 2.45/kWh, fleet performance
ratio (PR) baseline 0.82 when clean. Residual sigma values are the standardised power residual
from the irradiance- and temperature-conditioned expected-behaviour model, not raw power error.

| Incident | Asset | Class | Ticketed as fault | Net cost, INR |
|---|---|---|---|---|
| `INC-2025-011-inv007-string-fuse-open` | INV-007 | DC string outage | Yes | 14,500 |
| `INC-2025-019-inv014-heatsink-fouling-derate` | INV-014 | Thermal derate | Yes | 38,000 |
| `INC-2024-027-inv021-dc-link-capacitor` | INV-021 | Power-stage aging | Yes | 265,000 |
| `INC-2025-006-fleet-soiling-not-ticketed` | All 24 | Environmental | **No** | 96,000 (cleaning) |
| `INC-2025-021-irradiance-sensor-false-fleet-alarm` | All 24 | Instrumentation | **No** | 6,500 |
| `INC-2024-033-inv004-pid-string-group` | INV-004 | Module degradation | Yes | 207,000 |

## 2. INC-2025-011 — INV-007, open string fuse

| Field | Value |
|---|---|
| Detected / confirmed / closed | 2025-02-14 / 2025-02-15 / 2025-02-17 |
| Lead time before quarterly inspection would have found it | 86 days |
| Signature | String input 11 current fell 9.2 A → 0.0 A within one 15-min interval at 11:45, POA irradiance 940 W/m². The other 19 inputs held 8.9 - 9.3 A. |
| Inverter-level effect | DC current deviation −5.1 %, PR 0.812 → 0.771, power residual −3.4 sigma, flat across the day |
| Ruled out first | Peers unaffected (23 inverters at residual ±1.1 sigma); irradiance chain validated per `scada-sensor-validation-sop`; no curtailment setpoint active per `grid-curtailment-policy`; soiling excluded because the deficit sat on one string input, not on all 20 |
| Root cause | 15 A gPV fuse open in combiner position 11; fuse clip retention had relaxed, and the resulting contact resistance cooked the fuse body. Thermal scan showed 118 °C on the adjacent holder. |
| Intervention | Fuse and holder replaced, all 20 holders re-torqued and IR-scanned, per `solar-string-fault-sop` |
| Cost | INR 14,500 (half-day crew, parts) |
| Energy lost | 190 kWh over 3 days ≈ INR 466. Counterfactual at 86 days: ≈ 5,400 kWh, INR 13,200 |

**Lesson.** A 5 % inverter-level deficit is inside the normal fleet PR spread and is invisible at
plant level. Per-string current monitoring is what makes it attributable in one interval.

## 3. INC-2025-019 — INV-014, heatsink fouling and afternoon derate

| Field | Value |
|---|---|
| Detected / confirmed / closed | 2025-04-22 / 2025-04-24 / 2025-04-29 |
| Lead time to a projected 75 °C hard trip | ~11 days at the observed trend |
| Signature | Heatsink temperature 68 °C at 14:10 against 41 °C ambient. Derate begins at 45 °C; at the project-assumed 1.0 kW/K derate slope the AC limit had fallen to 227 kW while DC input supported 250 kW. Power residual −4.6 sigma between 13:00 and 16:00, 0.0 sigma before 11:00. |
| Ruled out first | Ambient was genuinely extreme (site max 43.5 °C), so a naive check blames weather. The discriminator was **peer spread at matched ambient**: the other 23 inverters reached 57 - 60 °C in the same hour, leaving INV-014 8 - 11 K hot. Heatsink temperature residual +11 K against the load-and-ambient model. |
| Root cause | Intake filter matted with Charanka dust, fin pack loaded, and cooling fan 2 running at 61 % of commanded speed on a failing bearing |
| Intervention | Fin cleaning, filter replacement, fan 2 replacement, per `solar-inverter-thermal-sop` |
| Cost | INR 38,000 |
| Energy lost | ≈ 460 kWh over 8 derating days ≈ INR 1,127; avoided a trip-and-restart cycle worth ~900 kWh |

**Lesson.** A residual that only exists in the afternoon and scales with ambient is a cooling
finding, not a conversion fault. The absolute temperature proves nothing in a 43 °C ambient;
the spread against load-matched peers proves everything.

## 4. INC-2024-027 — INV-021, DC-link capacitor bank degradation

| Field | Value |
|---|---|
| Detected / confirmed / closed | 2024-09-03 / 2024-09-09 / 2024-09-26 |
| Lead time | 23 days from first flag to planned replacement |
| Signature | Conversion efficiency (DC-in to AC-out, 40 - 80 % load band) fell 98.1 % → 97.2 %, a 0.9 pp loss against a 98.2 % European-efficiency reference. Power residual −2.8 sigma, **flat across load and across time of day**. Internal cabinet temperature +6 K at matched load. Inverter service-port ripple register rose 4 V → 19 V peak-to-peak; transient DC-bus warnings rose from 14/day to 190/day. |
| Ruled out first | Irradiance chain validated; all 20 string currents symmetric at 9.0 - 9.2 A, so no DC-side loss; heatsink residual +1 K only, so not a cooling problem; no curtailment |
| Root cause | 3 of 12 DC-link electrolytic capacitors with ESR above the 2.5 x new-part service limit; unit at 7.2 years in a cabinet running 51 °C |
| Intervention | Full bank replacement in a planned 6 h low-irradiance window |
| Cost | INR 265,000 planned, against an estimated INR 720,000 unplanned power-stage replacement |
| Energy lost | ≈ 260 kWh efficiency loss over 23 days plus ≈ 700 kWh planned outage ≈ 960 kWh, INR 2,350 |

**Lesson.** The detector that matters for capacitor aging is the **efficiency residual**, not
temperature. A residual that is invariant to load and to time of day is an internal conversion
loss; a residual that moves with ambient is cooling; a residual that moves with one string is DC.

## 5. INC-2025-006 — fleet soiling episode, deliberately not ticketed

| Field | Value |
|---|---|
| Window | 2025-01-08 to 2025-02-02 (26 days) |
| Signature | Fleet-median PR 0.826 → 0.741, slope −0.31 %/day — inside the 0.15 - 0.35 %/day Charanka dry-season soiling band. Inter-inverter PR spread stayed at 0.9 pp, unchanged. Soiling station clean-vs-field ratio 0.921. Last rainfall 2024-12-27 at 1.8 mm, below the ~4 mm/day that substantially resets soiling. |
| Ruled out | Equipment. No inverter deviated from the fleet slope by more than 1.4 sigma; no string-level current asymmetry anywhere; no thermal residual. |
| Decision | RAI classified the event as environmental at confidence 0.93 and **opened zero equipment tickets**. It raised an economics recommendation instead, per `solar-soiling-cleaning-sop` and `om-economics-policy`. |
| Intervention | Full-site wet clean, 2 crews x 3 days |
| Cost | INR 96,000 |
| Energy recovered | PR returned to 0.822. Deficit at cleaning ≈ 8.2 % of 30,000 kWh/day = 2,460 kWh/day = INR 6,027/day; payback ≈ 16 days |

**Lesson.** Uniform, slow, spread-preserving decline across all 24 inverters is soiling. The
fleet-uniformity test is the discriminator, and it must be applied before any per-asset
investigation. Twenty-four wrongly opened tickets would have cost more than the cleaning.

## 6. INC-2025-021 — irradiance sensor error, false fleet-wide alarm

| Field | Value |
|---|---|
| Raised / suppressed / corrected | 2025-06-19 09:15 / 2025-06-19 15:20 / 2025-06-21 |
| Signature | All 24 inverters went to −5.2 to −6.1 sigma power residual **within a single 15-min interval**. Degradation is never simultaneous across 24 independent units, and never a step. |
| Ruled out first | Equipment and soiling. Per `scada-sensor-validation-sop`: POA-1 read 1,031 W/m² at solar noon against 922 W/m² on POA-2 and 918 W/m² from the clear-sky model — an 11.8 % disagreement. Every string current was unchanged at 9.0 - 9.3 A, and AC output was unchanged. Only the *expected* value had moved. |
| Root cause | Datalogger card replaced that morning; the sensitivity constant from the retired pyranometer's certificate was entered for POA-1, inflating irradiance by ~12 % |
| Intervention | Correct constant loaded, POA-1 cross-calibrated against POA-2 and both reference cells, 6.5 h of PR data flagged invalid |
| Cost | INR 6,500 plus 4 engineering hours |
| Energy lost | **0 kWh.** There was never a production loss. |

**Lesson.** A residual appearing on every asset in the fleet inside one interval is an
instrumentation hypothesis until the irradiance chain is validated. Had the alarm been
actioned, 24 inspections at ≈ INR 12,000 each is INR 288,000 of wasted mobilisation — plus the
loss of operator trust that makes the next true alarm ignorable. Compare
`INC-2025-003-anemometer-drift-false-alarm` in `incident-log-wind-gearbox`: same failure shape,
different sensor.

## 7. INC-2024-033 — INV-004, potential-induced degradation on a string group

| Field | Value |
|---|---|
| Trend opened / confirmed / mitigated | 2024-05-02 / 2024-08-14 / 2024-09-05 |
| Lead time | 5 months of trend before IV-curve confirmation |
| Signature | INV-004 PR diverged from fleet median at −0.4 pp/month, −2.1 pp cumulative. Power residual −2.2 sigma, persistent, ambient-independent. Critically the deficit was **not uniform across strings**: inputs 1 - 6 (nearest the negative array pole) carried 8.1 - 8.6 A against 9.0 - 9.2 A on inputs 7 - 20 at matched irradiance, a 7 - 11 % group deficit that worsened on high-humidity mornings. |
| Ruled out first | Soiling (would depress all 20 inputs equally, and the fleet showed no soiling slope in that window), shading (unchanged row geometry, deficit present at solar noon), irradiance sensing, curtailment |
| Root cause | PID on negatively biased modules: humidity plus system voltage driving shunt-resistance collapse. IV curves per `solar-iv-curve-sop` gave fill factor 0.712 against 0.761 on a healthy reference string. |
| Intervention | Night-time anti-PID voltage regeneration unit fitted; recovery over ~6 weeks |
| Cost | INR 185,000 unit and install, INR 22,000 IV-curve survey |
| Energy lost | ≈ 2,250 kWh over 150 days ≈ INR 5,513; ≈ 1.9 pp of PR recovered |

**Lesson.** Soiling is fleet-uniform and inverter-uniform. PID is string-group selective and
humidity-modulated. Both look like a slow PR decline at plant level; the string-current
distribution separates them in one query.

## 8. Cross-case discriminators

| Observation | Most likely class | First action |
|---|---|---|
| One string input at 0 A, peers normal | DC fault | `solar-string-fault-sop` |
| Residual only in the afternoon, tracks ambient | Cooling | `solar-inverter-thermal-sop` |
| Residual flat across load and time of day | Conversion / power stage | Efficiency trend, service port |
| All 24 assets step together in one interval | Instrumentation | `scada-sensor-validation-sop` |
| All 24 assets drift together at 0.15 - 0.35 %/day | Soiling | `solar-soiling-cleaning-sop`, no fault ticket |
| One inverter, one string group, slow, humidity-linked | PID | `solar-iv-curve-sop` |

Two of six cases had no equipment cause. That ratio is the reason `scada-sensor-validation-sop`
and the environmental check run **before** an equipment ticket is authorised, never after.

## Related documents

- `solar-inverter-system` — machine constants, derate curve and alarm limits.
- `solar-dc-string-system` — string electrical constants and combiner arrangement.
- `solar-inverter-thermal-sop` — heatsink and cooling diagnosis.
- `solar-string-fault-sop` — string outage isolation procedure.
- `solar-soiling-cleaning-sop` — soiling rate model and cleaning economics.
- `solar-iv-curve-sop` — IV tracing, fill factor and PID confirmation.
- `scada-sensor-validation-sop` — run this **before** accepting any deficit as real.
- `grid-curtailment-policy` — curtailment setpoints and how they mimic underperformance.
- `om-economics-policy` — tariff, cost registry and planned-versus-unplanned assumptions.
- `alarm-response-matrix` — ownership and response times per alarm class.
- `incident-log-wind-gearbox` — the wind-side companion log.
