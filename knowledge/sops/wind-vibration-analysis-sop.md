---
doc_id: wind-vibration-analysis-sop
title: Drivetrain Vibration Analysis Procedure
asset_type: wind_turbine
component: gearbox
kind: sop
version: "1.4"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content on vibration analysis for a generic 2 MW
> geared wind turbine drivetrain. This is not manufacturer documentation and is not
> attributable to any OEM. All gear tooth counts, bearing geometries, defect orders and
> thresholds are project-defined engineering assumptions unless a section states a measured
> source.

## 1. Scope and trigger

Applies to `WT-001` .. `WT-018` at Kutch Wind Farm. Invoked when `drivetrain_vibration_mms`
exceeds its 4.0 mm/s RMS warning limit, when the load-normalised vibration residual stays
above baseline for 72 h, or when `wind-gearbox-inspection-sop` escalates for spectral
confirmation.

The SCADA tag is a **single broadband RMS value** (velocity, 10 - 1,000 Hz). It says energy
rose. It cannot say which stage or which bearing. Every conclusion below requires a portable
spectrum capture on site.

## 2. Rule out first (mandatory gate)

No spectral investigation and no equipment-fault hypothesis until all four checks are closed
and recorded in the work order.

1. **Sensor validity** — run `scada-sensor-validation-sop`. Check IEPE bias voltage (expect
   10 - 12 V DC; below 1 V is a shorted cable, above 20 V an open circuit), frozen values and
   step changes with no ramp. One channel moving alone is a sensor hypothesis.
2. **Operating point** — broadband RMS rises 0.6 - 0.9 mm/s from 25 % to 100 % load. Confirm
   the exceedance persists at matched load.
3. **Environment and grid** — confirm no curtailment (`grid-curtailment-policy`) and no icing
   (`weather-icing-operations-sop`). Rotor ice imbalance produces a real 1x rotor rise on a
   mechanically healthy drivetrain and clears when the ice sheds.
4. **Peers and alignment** — compare the fleet peer group for the same wind-direction sector.
   A rise across several turbines in one sector is wake turbulence, not a bearing. A
   persistent 1x rotor rise with a power deficit points to yaw misalignment first
   (`wind-yaw-alignment-sop`).

An intervention authorised without a closed gate is a procedural non-conformance.

## 3. Sensor locations and mounting

| Ch | Location | Axis | Band | Purpose |
|---|---|---|---|---|
| A1 | Main bearing housing | Radial | 0.1 - 1,000 Hz | Rotor 1x, main bearing envelope |
| A2 | Planetary ring gear housing, 12 o'clock | Radial | 0.5 - 3,000 Hz | Planetary mesh and sidebands |
| A3 | Intermediate stage housing | Radial | 2 - 5,000 Hz | Intermediate mesh |
| A4 | HSS bearing housing, gearbox output | Radial | 2 - 10,000 Hz | **SCADA tag source**, HSS mesh, envelope |
| A5 | HSS bearing housing | Axial | 2 - 10,000 Hz | Misalignment, helical thrust |
| A6 / A7 | Generator DE / NDE bearing | Radial | 2 - 10,000 Hz | See `wind-generator-system` |
| T1 | HSS tachometer, 1 pulse/rev | - | - | Order-tracking reference |

Mounting sets usable bandwidth and is the commonest cause of a false spectrum. **Stud mount**
(M8 into a spot-faced pad, 2.0 N·m ±0.3, silicone couplant) is usable to ~10 kHz and is
mandatory for envelope work. Adhesive pad ~4 kHz, velocity spectra only. Magnetic base
~2 kHz, never for bearing analysis. Handheld probe ~1 kHz, screening only.

## 4. Capture settings

Capture at **≥ 70 % rated power**, power stable to ±10 % across the window; take three
consecutive records and discard any pair differing by more than 15 % in band RMS.

| Analysis | Span | Δf | Averages |
|---|---|---|---|
| Velocity, HSS and intermediate | 0 - 1,000 Hz, 3,200 lines | 0.3125 Hz | Hanning, 8, 50 % overlap |
| Velocity, planetary and main bearing | 0 - 100 Hz, 3,200 lines | 0.03125 Hz | Hanning, 8, 50 % overlap |
| Envelope, HSS / generator | 0 - 500 Hz after 2 - 8 kHz band-pass | 0.3125 Hz | Hanning, 8 |
| Envelope, main bearing | 0 - 10 Hz after 0.5 - 5 kHz band-pass | 0.00625 Hz | Hanning, 8, ≥ 8 min record |

The main bearing needs the long record because its FTF is 0.11 Hz; a 60 s capture cannot
resolve it.

## 5. ISO 10816-21 zones for this machine class

Broadband velocity RMS, 10 - 1,000 Hz, at A4, at ≥ 70 % load.

| Zone | Band | Meaning | Action |
|---|---|---|---|
| A | ≤ 2.0 mm/s | Commissioned condition; design baseline | None |
| B | 2.0 - 4.5 mm/s | Acceptable for unrestricted operation | Trend review within 7 days above 4.0 mm/s |
| C | 4.5 - 7.1 mm/s | Unsatisfactory; short-term operation only | On-site inspection within 24 h |
| D | > 7.1 mm/s | Damaging | Stop the turbine; no restart before inspection |

The SCADA limits in `wind-gearbox-system` section 5 (warning 4.0, alarm 5.6, trip
7.1 mm/s) sit **inside** these zones so the alarm fires before the C/D boundary. The healthy
fleet band at 80 - 100 % load is 3.2 - 3.8 mm/s — upper Zone B — which is why 4.0 mm/s is a
watch trigger, not a fault.

## 6. Forcing frequencies

Assumed gear train, chosen so stage ratios multiply to the specified 1 : 97.5 and preserve
the 22-tooth HSS pinion of `wind-gearbox-system`: planetary (sun 24, 3 × planet 36, ring 96)
= 5.000; helical stage 1, gear 78 / pinion 16 = 4.875; helical stage 2, gear 88 / pinion 22
= 4.000. Product = 97.500.

At nominal HSS 1,500 rpm (rotor 15.4 rpm):

| Component | Order (× HSS) | Frequency |
|---|---|---|
| Rotor / planet carrier 1x | 0.01026 | 0.256 Hz |
| Blade pass 3P = planet pass (3 planets) | 0.03077 | 0.769 Hz |
| Planetary gear mesh (96 × carrier) | 0.9846 | 24.62 Hz |
| Sun / LSS shaft 1x | 0.05128 | 1.282 Hz |
| Intermediate gear mesh (16 × 6.25) | 4.000 | 100.0 Hz |
| Intermediate shaft 1x | 0.2500 | 6.25 Hz |
| HSS gear mesh (22 × 25.0) | 22.00 | 550.0 Hz |
| HSS 1x | 1.000 | 25.0 Hz |

Blade pass and planet pass coincide at 0.769 Hz on a 3-blade rotor with 3 planets. A rise
there is a planetary finding only if mesh sidebands accompany it; otherwise it is aerodynamic.

**Sideband rule.** A local gear defect modulates its mesh at the shaft rate of the defective
wheel. At 550 Hz, ±25.0 Hz indicts the 22-tooth pinion, ±6.25 Hz the 88-tooth gear. At
100 Hz, ±6.25 Hz indicts the 16-tooth pinion, ±1.28 Hz the 78-tooth gear. At 24.62 Hz,
±0.256 Hz indicates a distributed ring or planet condition, ±1.28 Hz a sun gear defect.

## 7. Bearing defect orders

Generic geometries, stated so the orders are reproducible. Orders are relative to the shaft
the bearing supports.

| Bearing | N, d/D | FTF | BSF | BPFO | BPFI |
|---|---|---|---|---|---|
| HSS | 16, 0.20 | 0.40× = 10.0 Hz | 2.40× = 60.0 Hz | 6.40× = 160.0 Hz | 9.60× = 240.0 Hz |
| Generator DE | 9, 0.30 | 0.35× = 8.75 Hz | 1.52× = 37.9 Hz | 3.15× = 78.8 Hz | 5.85× = 146.3 Hz |
| Main bearing | 20, 0.14 | 0.43× = 0.110 Hz | 3.50× = 0.898 Hz | 8.60× = 2.205 Hz | 11.40× = 2.923 Hz |

FTF = ½(1 − d/D); BPFO = (N/2)(1 − d/D); BPFI = (N/2)(1 + d/D); BSF = (D/2d)(1 − (d/D)²),
each × shaft rate. BSF usually presents at 2×BSF (HSS: 120 Hz) because a spalled roller
strikes both races per revolution.

## 8. Velocity spectra versus envelope demodulation

Not interchangeable; they answer different questions.

- **Velocity, 10 - 1,000 Hz** resolves low-order, high-energy faults: imbalance (dominant 1x
  radial), misalignment and coupling wear (1x and 2x with strong axial content at A5),
  looseness (1x through 5x harmonics over a raised noise floor), and mesh energy with
  sidebands. This is where `drivetrain_vibration_mms` lives.
- **Envelope** (2 - 8 kHz band-pass, then FFT of the envelope) resolves early bearing
  defects. A spall excites a kHz structural resonance and amplitude-modulates it at the
  defect order. That energy is negligible in velocity RMS: a bearing can be 4 - 8 weeks into
  spalling with broadband RMS still in Zone B. Envelope leads broadband by weeks.

Interpretation: BPFO with shaft-rate sidebands → outer race spall; BPFI with strong 1x
sidebands → inner race spall, load-zone modulated; 2×BSF with FTF sidebands → rolling element
damage; FTF alone over a raised noise floor → cage wear or severe looseness.

## 9. Defect, resonance, or loose sensor

A peak is a defect only if it **tracks order**. Capture at two HSS speeds, nominally 900 and
1,450 rpm:

- A 6.40-order BPFO sits at 96.0 Hz at 900 rpm and 154.7 Hz at 1,450 rpm — it moved with
  speed. **Defect.**
- A bedplate or gearbox-mount resonance holds the same hertz at both speeds while its order
  changes. **Resonance** — a structural finding: check mount bushings and torque, not the
  bearing.
- A mounting fault shows a downward shift of the sensor's mounted resonance, a rising
  broadband noise floor with no discrete peaks, a low-frequency "ski slope" below 5 Hz, and
  amplitude that changes when the sensor is tapped. Re-seat, re-check bias voltage and
  re-capture **before** recording any finding.

Any spectrum whose 1x amplitude differs by more than 20 % between two same-load captures is
untrustworthy. Re-take it.

## 10. Trending and rate of change

Trend the load-normalised 7-day median of `drivetrain_vibration_mms` and the envelope BPFO
peak in g. Rate, not level, sets urgency.

| Rate (load-normalised band RMS) | Interpretation | Action |
|---|---|---|
| < 0.05 mm/s per week | Stable | Routine trending |
| 0.05 - 0.15 mm/s per week | Slow drift | Re-capture in 14 days |
| > 0.15 mm/s per week | Active degradation | Oil sample within 7 days (`wind-oil-sampling-sop`) |
| > 0.40 mm/s per week | Rapid | Inspection within 24 h; plan intervention |

Envelope criterion: a **6 dB** (2×) rise in the BPFO or BPFI peak over 30 days at matched
load is significant whatever the broadband RMS; **12 dB** (4×), or a doubling inside 14 days,
is late-stage. Project the broadband trend linearly to 7.1 mm/s — a crossing inside 60 days
puts the repair in the planning window where `om-economics-policy` applies.

## 11. Corroboration before teardown

A vibration finding alone never authorises a teardown. Require the section 2 gate closed
**plus at least two** of:

1. **Oil evidence** — Fe or Cr trending up, PQ index rising, or debris on the magnetic plug
   or chip detector (`wind-oil-sampling-sop`).
2. **Thermal evidence** — a sustained positive `gearbox_oil_temp_c` residual ≥ 4 degC at
   matched load and ambient, or `main_bearing_temp_c` above its 70 degC warning.
3. **Spectral specificity** — a section 7 defect order with the expected sideband structure,
   confirmed on two captures ≥ 7 days apart.

Rising vibration with no oil debris and no thermal residual is usually misalignment,
looseness or resonance — all cheaper to fix than a bearing, and all made worse by an
unnecessary teardown. Rising vibration *and* rising oil temperature *and* a negative power
residual with peers unaffected is the confirmed degradation pattern; see
`incident-log-wind-gearbox`.

## Related documents

- `wind-gearbox-system` — machine constants, SCADA tags, absolute alarm limits.
- `wind-gearbox-inspection-sop` — the field inspection this procedure escalates into.
- `wind-oil-sampling-sop` — the oil evidence required by section 11.
- `wind-bearing-replacement-sop` — the intervention once a defect is confirmed.
- `wind-generator-system`, `wind-generator-thermal-sop` — channels A6/A7.
- `wind-yaw-alignment-sop` — 1x rotor vibration with a power deficit.
- `scada-sensor-validation-sop` — mandatory first step, section 2.
- `weather-icing-operations-sop` — rotor ice imbalance as a confounder.
- `grid-curtailment-policy` — curtailment as an operating-point confounder.
- `alarm-response-matrix` — ownership and response time per zone.
- `om-economics-policy` — planned versus unplanned cost asymmetry.
- `incident-log-wind-gearbox` — worked cases of the co-signature.
