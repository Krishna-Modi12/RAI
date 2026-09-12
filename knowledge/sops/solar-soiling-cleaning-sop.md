---
doc_id: solar-soiling-cleaning-sop
title: Soiling Assessment and Module Cleaning
asset_type: solar_inverter
component: pv_modules
kind: sop
version: "1.3"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content for a generic 250 kW string-inverter PV
> plant. This is not manufacturer documentation and is not attributable to any OEM. All
> figures are project-defined engineering assumptions unless a section states a measured
> source.

## 1. Scope and applicability

This procedure covers soiling quantification, the cleaning decision, cleaning execution and
post-clean verification for the Charanka Solar Park array (`INV-001` .. `INV-024`, 250 kW AC
per inverter, 312.5 kWp DC per inverter at a DC/AC ratio of 1.25, 7,500 kWp DC site total).

Soiling is a **recoverable performance loss**, not an equipment fault. The entire purpose of
this SOP is to separate a soiling deficit — which is fixed by a broom and water — from a DC
string fault, an inverter derate or an instrumentation error, which are not. Section 11
states the classification rule that follows from this and is binding on the RAI agent.

## 2. Rule out first

Do not open a soiling assessment, and do not quote a soiling number, until all four checks
below are closed. A power deficit has at least four non-soiling explanations that look
identical in daily energy.

| Check | Why it fakes soiling | Procedure |
|---|---|---|
| Irradiance instrumentation | A soiled POA reference cell reads low and **hides** real soiling; a drifting pyranometer reading high **invents** soiling. The reference cell soils at the same rate as the array. | `scada-sensor-validation-sop` |
| Grid curtailment | A curtailed inverter produces a clean-looking ramp deficit across the whole fleet at once. | `grid-curtailment-policy` |
| Inverter thermal derate | Heatsink above 45 degC derates output; above 75 degC it trips. Afternoon-only deficits are thermal until disproved. | `solar-inverter-thermal-sop` |
| Availability | Partial-day outages and MPPT restarts depress daily energy without any optical loss. | `solar-inverter-system` |

**Clipping caveat.** At a DC/AC ratio of 1.25 the array can present 312.5 kW DC into a
250 kW AC inverter, so clear-sky midday operation absorbs the first ~20 % of DC loss with no
change in AC power at all. Soiling is therefore **invisible** in midday energy and must be
assessed in shoulder hours where plane-of-array irradiance is 400 - 700 W/m2 and the inverter
is demonstrably off its AC limit.

## 3. Quantifying soiling

Three independent measures are used. A cleaning decision requires at least two to agree.

**3.1 Soiling ratio (primary).** The site soiling station is a matched pair of reference
modules on the array tilt: one cleaned every morning, one left to soil naturally. Both report
short-circuit current and back-of-module temperature.

```
soiling_ratio = (Isc_soiled / G) / (Isc_clean / G)     soiling_loss = 1 - soiling_ratio
```

Both devices see the same irradiance, so G cancels. Accept a reading only when POA irradiance
exceeds 600 W/m2 and the two back-of-module temperatures are within 5 K. Report the 3-day
median, never a single sample.

**3.2 Temperature-corrected performance ratio (secondary).** Per inverter,

```
PR = E_ac / (POA_kWh_per_m2 x P_dc_stc / 1.0 kW/m2)
PR_corr = PR / (1 + (-0.004 /K) x (T_mod - 25 degC))
```

using the module power temperature coefficient of -0.004 /K and NOCT 45 degC for back-of-module
estimation where a module RTD is unavailable. The reference is the `PR_corr` measured in the
48 h after the last verified clean. Soiling appears as a slow, monotone, fleet-synchronous
decline in `PR_corr`.

**3.3 String-current uniformity (discriminator).** Compare each of the 20 strings on an
inverter against the sibling median, normalised to irradiance against the 9.2 A STC reference
(`solar-dc-string-system`). Uniform soiling moves all 20 strings together.

| Observation | Threshold | Action |
|---|---|---|
| Soiling loss, 3-day median | >= 3.0 % | Add block to the next scheduled cleaning cycle |
| Soiling loss, 3-day median | >= 5.0 % | Clean within 7 days |
| Soiling loss, 3-day median | >= 8.0 % | Clean within 72 h |
| `PR_corr` spread across the 24 inverters | <= 1.5 pp | Consistent with uniform soiling |
| `PR_corr` spread across the 24 inverters | > 3.0 pp | Not uniform soiling — go to section 5 |
| One inverter below fleet median `PR_corr` | > 4.0 pp | Localised deposition or DC fault |
| One string below sibling median current | < 90 % | I-V trace required, `solar-iv-curve-sop` |

## 4. Charanka accumulation rates and dust events

Regional rates, expressed as percentage points of soiling loss gained per day. These are
project planning assumptions calibrated to the 0.15 - 0.35 %/day dry-season band.

| Season | Months | Accumulation | Character |
|---|---|---|---|
| Post-monsoon | Oct - Nov | 0.15 - 0.20 %/day | Low airborne load, heavy dew — cementation risk |
| Winter | Dec - Feb | 0.18 - 0.25 %/day | Agricultural residue burning, stable haze layer |
| Pre-monsoon dust season | Mar - May | 0.28 - 0.35 %/day | Rann and Thar dust transport, frequent storms |
| Monsoon | Jun - Sep | 0.10 - 0.20 %/day between events | Repeatedly reset by rainfall, section 6 |

**Dust events are a step, not a ramp.** A single frontal dust storm can add 3 - 8 percentage
points of soiling loss in under 24 h. The signature is unmistakable and must be recognised
before anyone calls it a fault: the step is **simultaneous across all 24 inverters**, lands
within one reporting interval, and is accompanied by a wind and visibility excursion in the
site weather record. No equipment failure mode is fleet-synchronous to the sample.

## 5. Uniform soiling versus localised deposition

| Pattern | Signature | Route to |
|---|---|---|
| Uniform dust | All 24 inverters within 1.5 pp; all 20 strings per inverter within 5 % | Cleaning work order, this SOP |
| Bird droppings | One or two strings 10 - 40 % low; hot spots on thermography; abrupt onset | `solar-string-fault-sop`, then targeted wet clean |
| Cement or construction dust | Adjacent blocks only, downwind of works; deposit does not brush off dry | Wet clean, section 8 |
| Agricultural burning residue | Fleet-wide but oily and cemented; dry brushing smears it | Wet clean only |
| Row-end or edge soiling | Perimeter rows only, vehicle track dust | Cleaning, restrict site traffic |

Localised deposition that survives one full cleaning pass stops being a soiling finding and
becomes a DC finding. Bypass-diode activation from a persistently shaded cell produces a
thermal signature that cleaning will not change.

## 6. Rainfall reset and the natural-cleaning decision

Rainfall above **4 mm/day** in a single event substantially resets accumulated soiling,
recovering 60 - 90 % of the loss within 24 h of the rain stopping. Below that it does not,
and in one band it makes things worse.

| Daily rainfall | Effect | Decision |
|---|---|---|
| < 0.5 mm | None | Proceed with the schedule |
| 0.5 - 4.0 mm | **Adverse.** Wets and cements the dust film, leaves drying streaks. Soiling loss can rise 1 - 3 pp. | Do **not** cancel a scheduled clean. Re-measure within 48 h; switch dry passes to wet |
| > 4.0 mm | Substantial reset | Defer cleaning, re-measure soiling ratio 24 h after rain stops |
| > 15 mm | Effectively a full clean | Re-baseline `PR_corr` and treat as a verified clean if section 10 acceptance is met |

**Deferral rule.** Defer a scheduled clean when current soiling loss is below 5.0 % *and* the
5-day forecast carries at least a 60 % probability of a > 4 mm/day event. Above 5.0 % loss,
clean regardless of forecast — the expected revenue lost while waiting on uncertain rain
exceeds the cleaning cost.

## 7. Economic cleaning interval

Soiling accumulates approximately linearly between cleans, so mean loss over an interval of
T days at rate r (fraction/day) is `r x T / 2`, and the optimum interval is:

```
T* = sqrt( 2 x C_clean / ( r x R_day ) )
```

Planning assumptions: specific yield 1,650 kWh/kWp DC per year (project assumption, not a
measured site figure), giving 1,413 kWh/day per inverter block and a gross revenue of
**INR 3,461/day per block** at the solar tariff of **2.45 INR/kWh**. Cleaning cost is taken as
INR 4.00/kWp DC for a dry pass (**INR 1,250 per block**, INR 30,000 for the full plant) and
INR 9.00/kWp DC for a wet pass (**INR 2,813 per block**, INR 67,500 plant-wide).

| Accumulation rate | Optimum dry interval | Optimum wet interval | Mean loss carried (dry) |
|---|---|---|---|
| 0.15 %/day | 22 days | 33 days | 1.65 % |
| 0.25 %/day | 17 days | 25 days | 2.13 % |
| 0.35 %/day | 14 days | 22 days | 2.45 % |

At the optimum the revenue lost to soiling over the interval exactly equals the cleaning cost
— a useful field check. At 0.25 %/day the total cost of soiling is INR 147/day per block,
about 4.3 % of gross revenue. Over a ~240-day dry season this is roughly 14 dry passes per
block, INR 420,000 plant-wide. Economic method and cost registry are in `om-economics-policy`.

## 8. Cleaning methods, water and safe practice

**Dry cleaning is the default** at this site because water is scarce. Use a rotating soft
nylon or microfibre brush, tractor- or rail-mounted, on loose dust with soiling loss <= 6 %.
Throughput approximately one inverter block per 40 min. Zero water.

**Wet cleaning** is mandatory for cemented deposits (post-dew, post-dirty-rain, burning
residue), bird droppings and cement dust. Demineralised or soft water only: TDS < 100 ppm,
hardness < 75 ppm as CaCO3, pH 6.5 - 8.0. **No detergents, no solvents.** Consumption
assumption 0.6 L/m2 of module area; at an assumed 200 W/m2 module power density a block is
~1,563 m2, so **~940 L per inverter block** and **~22.5 m3 for a full-plant wet pass**.

Timing and safety:

- Clean before 09:00 or after 17:00 local. Never apply water to a module whose back-of-module
  temperature exceeds 50 degC — thermal shock cracks glass.
- Suspend tractor-mounted operations above 12 m/s wind.
- Treat the DC side as live whenever irradiance is non-zero. String open-circuit voltage is
  nominally ~820 V. Isolation and lockout per `solar-string-fault-sop` section 2.

## 9. Warranty and abrasion cautions

- Never stand, kneel or place tools on a module. Point loading causes cell microcracks and
  voids the module warranty.
- No abrasive pads, scrapers, metal implements or bristles harder than soft nylon. The
  anti-reflective coating is the first casualty and its loss is permanent.
- Maximum jet pressure 35 bar at a standoff of at least 300 mm, never directed at the frame
  seal, junction box or connectors.
- Do not dry-brush a cemented deposit "harder". Escalate to wet. Repeated dry passes on
  cemented dust are the main abrasion mechanism at this site.
- Replace brush heads every 40 passes and log passes per block; cumulative abrasion is a
  warranty consideration and needs a record.

## 10. Verification

Measure 2 - 6 h after the pass, once modules are dry, at POA irradiance above 600 W/m2.

| Acceptance criterion | Limit |
|---|---|
| Post-clean soiling loss (soiling station) | <= 1.0 % |
| `PR_corr` recovery vs last verified clean reference | within 1.0 pp |
| String-current spread across the 20 strings | <= 5 % |

Log date, method, blocks cleaned, water volume, pre/post soiling ratio, pre/post `PR_corr`,
brush-pass count and operator.

**The important failure case:** if `PR_corr` does not recover to within **2.0 pp** of the
clean reference after a verified clean, soiling was not the explanation. From that moment the
residual deficit is an equipment finding — open `solar-iv-curve-sop` and `solar-string-fault-sop`.
A verified clean is the step that converts a suspicion into a fault.

## 11. Classification rule — soiling is not an equipment fault

Binding on the RAI agent and on ticket routing:

1. A confirmed uniform soiling finding generates a **cleaning work order** categorised as
   performance recovery. It must **never** generate an equipment inspection ticket, an
   inverter or string health downgrade, or a change to remaining useful life.
2. Soiling loss is excluded from equipment residuals. The expected-behaviour model is
   evaluated against a soiling-corrected baseline so that a dirty array does not accumulate
   phantom degradation.
3. An equipment fault may only be asserted on a soiled array after a verified clean
   (section 10) or after the deficit is shown to be non-uniform (section 5).
4. Escalation: cleaning schedule is owned by the site O&M supervisor; deferral against a
   rainfall forecast is owned by the plant manager; any deficit surviving a verified clean is
   owned by the site reliability engineer.

## Related documents

- `solar-inverter-system` — plant topology, inverter ratings and clipping behaviour.
- `solar-dc-string-system` — string electrical constants and array layout.
- `solar-iv-curve-sop` — I-V tracing to separate optical loss from cell and diode faults.
- `solar-string-fault-sop` — the DC fault path when cleaning does not restore output.
- `solar-inverter-thermal-sop` — the 45 degC derate and 75 degC trip path.
- `scada-sensor-validation-sop` — run this **before** accepting any PR deficit as real.
- `grid-curtailment-policy` — curtailment as a competing explanation for lost energy.
- `om-economics-policy` — tariff, cost registry and the expected-loss method used in section 7.
- `alarm-response-matrix` — ticket categories, ownership and escalation timers.
- `incident-log-solar-inverter` — worked cases, including deficits wrongly attributed to soiling.
