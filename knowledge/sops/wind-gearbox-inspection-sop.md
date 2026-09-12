---
doc_id: wind-gearbox-inspection-sop
title: Wind Turbine Gearbox Inspection Procedure
asset_type: wind_turbine
component: gearbox
kind: sop
version: "1.4"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as
> illustrative operations and maintenance content describing borescope and visual inspection
> of a generic 2 MW geared wind turbine gearbox. This is not manufacturer documentation and is
> not attributable to any OEM. All figures are project-defined engineering assumptions unless
> a section states a measured source.

## 1. Scope

Visual and borescope inspection of the 1 planetary + 2 helical stage gearbox fitted to
`WT-001` .. `WT-018` at the Kutch Wind Farm, including HSS bearing race inspection, oil
sight-glass reading and magnetic plug debris assessment. Machine constants are defined in
`wind-gearbox-system` and are not restated except where a threshold depends on them.
Disassembly is out of scope: once this procedure returns **Replace**, work transfers to
`wind-bearing-replacement-sop`.

## 2. Rule out first — mandatory gate

No inspection tier may be authorised on a detector output alone. A power deficit, a thermal
residual and a vibration rise are all reproducible on a healthy drivetrain. Complete this gate
and record each result; an inspection order without it is rejected at review.

1. **Instrumentation.** Run `scada-sensor-validation-sop` on every tag in the trigger. A
   single signal moving with no corroborating movement in `gearbox_oil_temp_c`,
   `drivetrain_vibration_mms`, `power_kw` or `main_bearing_temp_c` is a sensor hypothesis, not
   a gearbox hypothesis. Confirm accelerometer mount torque and sump RTD loop resistance.
2. **Environment.** Oil temperature rises ~0.35 degC per 1 degC of ambient against a nominal
   ~38 K rise over ambient with a ~42 min thermal time constant, so an exceedance that appears
   in the afternoon and clears overnight is cooling capacity. Inspect cooler fins and fan
   first — Kutch dust loading March - June explains most summer drift.
3. **Curtailment.** Check `status_code`, `operating_state` and `pitch_angle_deg` against
   `grid-curtailment-policy`. A curtailed machine shows a negative power residual, no fault.
4. **Peers.** Compare at least four turbines in the same wind sector. A fleet-wide shift is a
   site or met condition; icing excursions are handled by `weather-icing-operations-sop`.
5. **Lubrication state.** Confirm the last oil result and filter change per
   `wind-oil-sampling-sop`. A degraded or low charge explains both temperature and vibration.

Only when all five return "not explanatory" is the trigger table applied.

## 3. Inspection trigger table

Zones are the ISO 10816 scale used by this corpus: A/B boundary 2.0 mm/s RMS (healthy
load-matched baseline), B/C 4.5 mm/s, C/D 7.1 mm/s. The SCADA absolute alarms in
`wind-gearbox-system` section 5 (4.0 warning, 5.6 alarm, 7.1 trip) are the operating limits;
the zone scale is the condition-assessment scale. Both are evaluated.

| Trigger | Tier | Response time |
|---|---|---|
| RAI residual anomaly, vibration < 4.0 mm/s, no thermal co-signature | Tier 0 — desk review of trend and peers | 7 days |
| Vibration 4.0 - 4.5 mm/s sustained 72 h, load-matched | Tier 1 — visual, sight glass, magnetic plug | 14 days |
| Vibration Zone B (4.5 - 7.1 mm/s), no thermal co-signature | Tier 1 plus oil sample | 7 days |
| Vibration Zone B **with** `gearbox_oil_temp_c` residual > +5 degC | Tier 2 — full borescope | 72 h |
| `gearbox_oil_temp_c` > 75 degC warning, load and ambient normalised | Tier 1, cooler check first | 72 h |
| `gearbox_oil_temp_c` > 80 degC alarm | Tier 2 | 24 h |
| `main_bearing_temp_c` > 70 degC warning, normalised | Tier 1 plus main bearing grease check | 72 h |
| Vibration Zone C/D (> 7.1 mm/s) or SCADA trip | Tier 2, turbine held stopped | Immediate |
| Oil laboratory Fe, Cr or PQ index above alarm limit | Tier 2 | 72 h |
| Ferrous flakes > 3 mm on the magnetic plug | Tier 3 — borescope plus filter cut-open | 24 h, stopped |
| RAI match to `incident-log-wind-gearbox` above confidence threshold | Tier 2 | 72 h |

A Tier 2 inspection costs INR 85,000 plus ~8 h downtime at an assumed INR 2,176 per hour of
lost production (3.20 INR/kWh) — about INR 102,000 all-in, against the INR 4,500,000
unplanned failure assumption in `om-economics-policy`. Do not argue a tier down on cost.

## 4. Safety isolation and lockout/tagout

1. Stop from SCADA; wait for rotor speed below 0.5 rpm.
2. Apply the rotor lock pin and confirm engagement visually, not by indicator lamp.
3. Activate the nacelle maintenance switch — yaw and pitch to local control only.
4. Lock open the generator breaker **and** the auxiliary supply feeding the oil pump, cooler
   fan and heaters. The offline filtration loop runs on auxiliaries and will motor the pump.
5. One personal lock and tag per person at every isolation point.
6. Verify dead: zero volts at the generator terminals, and the oil pump does not start when
   commanded.
7. Confirm `gearbox_oil_temp_c` below 45 degC before opening a port. Hot ISO VG 320 burns and
   floods any port opened above sump level.
8. Fall arrest, hoist inspection and a second person on the platform. Single-person up-tower
   gearbox entry is prohibited.
9. Barring for tooth indexing only with the barring device fitted, the lock withdrawn under
   direct supervision, and no hands inside any port.

## 5. Borescope access and sequence

Equipment: 6 mm articulating videoscope, 2.0 m working length, 4-way articulation, integral
LED, 90 degree side-view mirror adapter, measurement reticle or stereo tip for pit sizing.
Record video at every port, not stills alone.

| Port | Location | Stage viewed | Indexing |
|---|---|---|---|
| P1 | Front cover, rotor side, 10 o'clock | Planetary ring gear, 3 planets, planet bearing outer races | Bar the rotor one revolution in 12 steps |
| P2 | Top cover, mid-housing | Intermediate helical stage, both flanks, pinion | Index on the intermediate shaft, not the rotor |
| P3 | HSS housing, drive end, by the accelerometer boss | HSS pinion and wheel mesh, HSS bearing inner and outer race | Rotate the HSS by hand at the coupling, 20 steps |
| P4 | Sump inspection hatch | Sump floor, suction strainer, sludge bed | Static |

Inspect loaded flanks first — on the ring gear, the downwind side of each tooth. Clean the
mirror adapter between ports; oil film on the tip is the commonest cause of a falsely benign
report.

## 6. Surface distress and decision

Extent is the percentage of active flank area on the worst single tooth, sized against the
reticle. Between rows, take the more severe row.

| Distress | Borescope appearance | Accept | Monitor | Replace |
|---|---|---|---|---|
| **Micropitting** | Matte grey frosted patches in the dedendum, no profile loss | < 10 %, dedendum only; re-inspect 12 months | 10 - 25 %; oil sample 7 days, re-borescope 3 months | > 25 %, or profile loss at the pitch line |
| **Macropitting** | Discrete sharp-edged craters 0.5 - 3 mm | Isolated pits < 1 mm, under 3 per cm2; re-inspect 6 months | Any pit 1 - 2 mm, or pit field under 10 % of flank; re-borescope 30 days | Pit > 2 mm, pit field > 10 %, or any pitting on the planetary ring |
| **Spalling** | Contiguous material loss, irregular edge, bright fresh substrate | Never | Never | Any contiguous spall > 5 mm2 — stop the turbine |
| **Scuffing** | Radial score lines, torn or welded directional marks | Never without an oil result | < 5 % of flank **and** oil viscosity and additives in band; re-borescope 30 days | > 5 % of flank, any out-of-band oil result, or a concurrent oil temperature residual |
| **White etching cracks** | Axial or near-axial race cracking, often a raised lip alongside | Never | Never | Any visible axial crack on an HSS or planet bearing race — immediate stop, Tier 3 |

Micropitting is expected on a running-in gearbox and is not a fault by itself. Macropitting
and above are trends, not snapshots: a Monitor decision requires the follow-up inspection to
be scheduled in the work order before return to service, or it defaults to Replace.

## 7. HSS bearing race inspection

Through P3 with the mirror adapter, rotating the HSS by hand. Inspect the full circumference
of both races and at least 8 rolling elements.

- **Outer race load zone** (lower quadrant, rotor-side bearing) — spalling initiates here. Any
  spall or axial crack ends the inspection: stop, Tier 3.
- **Inner race** — rotates with the shaft, so damage repeats at roller pitch spacing. Index in
  20 steps to cover the circumference.
- **Fluting / electrical erosion** — evenly spaced axial washboard marks, frosted grey. This
  is shaft current, not overload. Check the earthing brush and replace below 10 mm remaining
  length. Monitor if confined and the earthing path is restored; Replace if the pattern covers
  more than a quarter of the circumference. See `wind-generator-system` for the generator-side
  path and `wind-generator-thermal-sop` for the thermal escalation route.
- **False brinelling** — dull elliptical depressions at roller spacing after a long standstill.
  Monitor; it does not progress once running.
- **True brinelling** — bright shock-load indentations. Replace.

Correlate every finding with the spectral capture in `wind-vibration-analysis-sop`. A BPFO
peak at 160 Hz with sidebands over a clean outer race means the capture or the tachometer
reference is wrong. Resolve the contradiction before writing a conclusion.

## 8. Oil sight glass and magnetic plug

Perform after at least 30 minutes of standstill so the sump has settled.

**Sight glass.** Level must sit between MIN and MAX against the 320 L nominal charge. Below
MIN, top up with ISO VG 320 synthetic PAO **and** raise a leak investigation. Colour, backlit
against a white card: clear amber is normal; hazy or milky is water ingress — oil sample
within 48 h and replace the breather desiccant; dark brown with varnish on the glass is
thermal degradation — oil sample within 48 h and review the cooler; visible suspended
particulate is Tier 3, cut open the 10 um inline element.

**Magnetic plug and chip detector.** Withdraw, photograph the debris against a 10 mm scale
**before** cleaning, then clean and refit to torque.

| Debris | Interpretation | Decision |
|---|---|---|
| Fine grey fuzz, particles under 1 mm | Normal running wear | Accept, record estimated mass |
| Discrete curved dull flakes 1 - 3 mm | Early surface fatigue | Monitor; oil sample 48 h, re-check plug 30 days |
| Flakes > 3 mm, bright faceted chunks, or total mass > 0.5 g | Active spalling | Stop the turbine, Tier 3, no restart before borescope |

Debris is corroborating evidence, never a standalone conclusion. A single large flake with a
clean borescope and a flat vibration trend is most often an assembly remnant from an earlier
intervention — record it as such rather than inventing a failure.

## 9. Inspection record fields

One record per inspection. These are the retrieval keys used by the RAI evidence layer; "not
observed" is a valid value, blank is not.

`asset_id` · `inspection_datetime_utc` · `tier` · `trigger_source` · `rule_out_gate_result`
(all five checks, pass/fail with note) · `scada_validation_ref` · `isolation_confirmed_by` ·
`ports_inspected` · `stage_findings` (per stage: distress type, extent %, max pit dimension
mm) · `hss_bearing_inner_race` · `hss_bearing_outer_race` · `rolling_elements_inspected` ·
`oil_level` · `oil_colour` · `magnetic_plug_debris_class` · `debris_photo_ref` · `decision`
(Accept / Monitor / Replace) · `follow_up_due_date` · `media_refs` · `inspector_id` ·
`reviewed_by`.

A Monitor decision with an empty `follow_up_due_date` is invalid and escalates to Replace.

## 10. Escalation timing

| Outcome | Owner | Action and deadline |
|---|---|---|
| Accept | Site reliability engineer | Close the order, restore the 6-month schedule |
| Monitor — micropitting 10 - 25 % | Site reliability engineer | Re-borescope 3 months, oil sample 7 days |
| Monitor — macropitting or light scuffing | Site reliability engineer | Re-borescope 30 days, oil sample 30 days, weekly vibration trend review |
| Replace, no secondary damage risk | Asset manager | Plan inside the trend-derived window, 36 h planned downtime assumption |
| Replace — spalling or axial cracking | O&M manager | Turbine held stopped, intervention plan within 72 h |
| Debris > 3 mm or > 0.5 g | O&M manager | Turbine held stopped, Tier 3 within 24 h |
| Inconclusive (fouled port, blocked access) | Site reliability engineer | Re-inspect within 7 days; never recorded as Accept |

Where borescope evidence and vibration or oil evidence disagree, the inspection is
inconclusive. Do not resolve it by preferring the more alarming reading, and do not close the
order on the less alarming one — escalate to human review with both records attached.

## Related documents

`wind-gearbox-system` · `wind-vibration-analysis-sop` · `wind-oil-sampling-sop` ·
`wind-bearing-replacement-sop` · `wind-generator-system` · `wind-generator-thermal-sop` ·
`scada-sensor-validation-sop` · `weather-icing-operations-sop` · `grid-curtailment-policy` ·
`alarm-response-matrix` · `om-economics-policy` · `incident-log-wind-gearbox`
