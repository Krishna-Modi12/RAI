---
doc_id: incident-log-wind-gearbox
title: Wind Fleet Incident Log — Drivetrain
asset_type: wind_turbine
component: drivetrain
kind: incident_log
version: "1.3"
source_note: Illustrative sample document authored for this project
---

> **Sample document.** Authored for the Renewable Asset Intelligence (RAI) project as an
> illustrative drivetrain incident record for a generic 2 MW geared wind fleet. These are not
> real events, this is not manufacturer documentation, and nothing here is attributable to any
> OEM. All dates, signatures, costs and outcomes are project-defined engineering assumptions
> unless a section states a measured source.

## 1. Scope and how to read this log

Six closed drivetrain episodes across `WT-001` .. `WT-018` at Kutch Wind Farm, in date order.
Each entry records the signature as the detectors actually saw it, the lead time between first
detection and intervention, the physical finding, the cost, and the lesson. This file is the
seed corpus for the case-memory retrieval layer: a live residual trajectory is matched against
the signatures below, so the numbers are stated in the same units and tags as
`wind-gearbox-system` section 4.

Two of the six are failures of the monitoring process, not of a machine. They are logged at the
same level of detail as the equipment failures because they are the cases the system exists to
prevent. Cost basis throughout: INR 3.20 per kWh, 680 kWh per standstill hour at capacity
factor 0.34 (`om-economics-policy`).

## 2. Case index

| Incident | Asset | Detected | Closed | Class | Lead time | Total cost (INR) |
|---|---|---|---|---|---|---|
| `INC-2024-014-gearbox-bearing-spalling` | WT-007 | 2024-03-09 | 2024-05-14 | True positive, equipment | 66 d | 1,417,688 |
| `INC-2024-022-oil-cooler-fouling` | WT-012 | 2024-05-28 | 2024-05-31 | True positive, cooling | 3 d | 55,056 |
| `INC-2024-027-generator-overheating` | WT-004 | 2024-07-02 | 2024-07-11 | True positive, cooling + sensor | 9 d | 188,936 |
| `INC-2024-039-gear-pitting-misattributed` | WT-015 | 2024-10-17 | 2025-02-24 | **Missed call** — real defect dismissed as environmental | 83 d discarded | 4,443,992 |
| `INC-2025-003-anemometer-drift-false-alarm` | WT-009 | 2025-02-06 | 2025-02-21 | **False alarm** — instrumentation drift | 8 d to null finding | 82,352 |
| `INC-2025-011-main-bearing-wear` | WT-002 | 2025-04-22 | 2025-06-03 | True positive, sub-threshold | 42 d | 196,232 |

## 3. INC-2024-014 — HSS bearing spalling, WT-007

| Field | Value |
|---|---|
| First detection | 2024-03-09, `drivetrain_vibration_mms` residual +2.8 sigma |
| Intervention | 2024-05-14, up-tower HSS bearing replacement |
| Lead time | 66 days |

**Signature.** Vibration rose from a load-matched baseline of 2.1 mm/s RMS to 3.4 mm/s over
five weeks with no ambient correlation, crossing the 4.5 mm/s warning threshold on 2024-04-21
at 4.6 mm/s. `gearbox_oil_temp_c` residual reached +6.1 K against the load and ambient
normalised model. Oil Fe climbed 38 → 96 ppm across two samples six weeks apart, Cr 4 → 11 ppm.
Power residual settled at -1.9 %. Peers WT-006 and WT-008 were clean in the same wind bins.

**Rule out first.** Anemometer validated against the met mast per `scada-sensor-validation-sop`
(bias -0.05 m/s, within tolerance); no curtailment instruction in the window per
`grid-curtailment-policy`; the thermal residual persisted overnight, which excludes an ambient
or cooler-capacity cause. Three independent tags moved together — this is the co-signature
described in `wind-gearbox-system` section 3, not a single-signal artefact.

**Found.** Portable spectrum capture (`wind-vibration-analysis-sop`) showed a 160 Hz BPFO peak
with 25 Hz sidebands. Teardown confirmed a 14 mm spall on the HSS non-drive-end outer race.

**Cost.** Repair INR 1,250,000, inspection INR 85,000, 38 h planned downtime = 25,840 kWh =
INR 82,688. Total INR 1,417,688 against an unplanned-failure exposure of roughly INR 5,126,000.

**Lesson.** The textbook case. Vibration, oil temperature and oil chemistry moving together
with clean peers is sufficient to authorise intervention, and the 66-day lead time was enough
to schedule the crew instead of mobilising one.

## 4. INC-2024-022 — Oil cooler fouling, WT-012

| Field | Value |
|---|---|
| First detection | 2024-05-28, `gearbox_oil_temp_c` residual +8.4 K (+3.6 sigma) |
| Intervention | 2024-05-31, fin wash and fan contactor replacement |
| Lead time | 3 days |

**Signature.** At 39 degC ambient and 78 % load the model expected 69.8 degC oil; observed
78.2 degC, within 1.8 K of the 80 degC trip. `drivetrain_vibration_mms` was flat at 2.2 mm/s
throughout. Oil Fe 31 ppm, unchanged. The residual appeared only in the afternoon and cleared
overnight, tracking `nacelle_temp_c` with a lag consistent with the 42 min gearbox thermal time
constant. Peers WT-011 and WT-013 showed residuals of +0.3 K and -0.4 K at the same ambient.

**Found.** Cooler fin matrix roughly 60 % blocked with Kutch dry-season dust; the number 2
cooler fan contactor had dropped out and not re-latched, so the unit had been running on one
fan for an estimated 11 days.

**Cost.** Labour and parts INR 42,000, 6 h downtime = 4,080 kWh = INR 13,056. Total INR 55,056.

**Lesson.** A thermal residual with **no** vibration co-signature and a diurnal shape is a
cooling finding. No gearbox inspection order was opened, and none was needed. March-June fin
cleaning was moved to a 4-month interval fleet-wide after this case.

## 5. INC-2024-027 — Generator winding overheating, WT-004

| Field | Value |
|---|---|
| First detection | 2024-07-02, `generator_winding_temp_c` 148.3 degC, above the 145 degC alarm |
| Intervention | 2024-07-11, radiator fan motor and filter mats replaced, PT100 re-terminated |
| Lead time | 9 days |

**Signature.** Winding residual +11 K (+4.2 sigma) against the load-normalised model, with the
excursion following load steps inside 20 min — consistent with the ~18 min winding thermal time
constant, and therefore a machine-side or cooling-path effect rather than nacelle heat soak.
Vibration 2.3 mm/s, unchanged; gearbox oil residual +1.1 K, not significant. Peak recorded
148.3 degC against the class F 155 degC insulation limit.

**Found.** External radiator fan 1 motor bearing seized; filter mats loaded with monsoon
vegetation debris. Separately, one of the six PT100 elements read 4.1 K high against the other
two sensors on the same phase — a partial instrumentation contribution to the alarm magnitude,
caught during the visit and corrected.

**Cost.** Parts and labour INR 165,000, 11 h downtime = 7,480 kWh = INR 23,936. Total
INR 188,936. See `wind-generator-thermal-sop` and `wind-generator-system`.

**Lesson.** Winding thermal findings are a cooling-path problem until the cooling path is
cleared. Also: a sensor can be wrong *and* the machine can be hot. Validating the sensor does
not close the case, it only corrects the magnitude.

## 6. INC-2024-039 — Gear pitting misattributed to environment, WT-015

| Field | Value |
|---|---|
| First detection | 2024-10-17, power residual -3.1 %, vibration 2.0 → 2.6 mm/s |
| Incorrectly closed | 2024-10-21, attributed to post-monsoon turbulence and wake from WT-014 |
| Re-flagged | 2025-01-08, vibration 4.9 mm/s, oil Fe 142 ppm |
| Intervention | 2025-02-18 to 2025-02-24, down-tower gearbox exchange |
| Lead time discarded | 83 days |

**What went wrong.** The October signature was genuinely weak: vibration at 2.6 mm/s was far
below the 4.5 mm/s warning, so no SCADA alarm existed, and the oil temperature residual was
+1.4 K. The reviewer closed it on an environmental hypothesis that was never tested. WT-014 was
under a curtailment instruction for most of that week and was producing at reduced load, so the
wake explanation offered was not physically available; a peer-normalised check across the same
wind-direction bin would have shown WT-015 alone carrying the deficit. No such check was run.

**Progression.** By 2025-01-08 vibration reached 4.9 mm/s, oil Fe 142 ppm (against a 100 ppm
laboratory alarm), PQ index 12 → 61, power residual -4.6 % at -5.7 sigma.

**Found.** Intermediate-stage helical pinion with micropitting over roughly 40 % of the active
flank and early spalling on two teeth. Planetary stage and main bearing were serviceable; by
January the damage had progressed past the point where an up-tower repair was viable.

**Cost.** Gearbox exchange INR 4,050,000 including INR 900,000 crane mobilisation, plus
INR 85,000 inspection, plus 142 h downtime = 96,560 kWh = INR 308,992. Total INR 4,443,992.
Counterfactual at first detection: an up-tower repair at approximately INR 1,250,000 and 36 h.
The delay cost roughly INR 2.9 million and 106 additional hours of lost production.

**Lesson.** "Environmental" is a hypothesis that must be *tested*, not a default disposal
reason. The rule-out discipline runs in both directions: it forbids asserting a fault before
weather, curtailment and sensors are cleared, and it equally forbids dismissing a deficit as
environmental without naming the environmental driver and showing it on the peers. This case
is why the agent must record which specific environmental hypothesis it rejected and on what
evidence, per `alarm-response-matrix`.

## 7. INC-2025-003 — Anemometer drift false alarm, WT-009

| Field | Value |
|---|---|
| First detection | 2025-02-06, power residual -6.8 % at -4.4 sigma, sustained 9 days |
| Crew dispatched | 2025-02-14, 2 technicians, 9 h on site, **no finding** |
| Root cause identified | 2025-02-21, nacelle anemometer bias |

**Signature.** A large, persistent negative power residual with **nothing else moving**.
Vibration 2.1 mm/s, gearbox oil residual +0.2 K, main bearing residual -0.1 K, oil Fe 24 ppm,
peers WT-008 and WT-010 clean. Because a power deficit reads as lost drivetrain efficiency, the
duty engineer treated it as incipient gearbox degradation and overrode the sensor-validation
step as "advisory".

**Root cause.** The nacelle anemometer had been replaced after lightning damage in January and
commissioned with the wrong transfer function. Met-mast comparison on 2025-02-21 measured a
mean bias of +0.22 m/s over the 7-11 m/s band. Below rated wind speed, power scales roughly
with the cube of wind speed, so a +0.22 m/s bias at 8 m/s inflates *expected* power by about
8 % — which accounts for the entire -6.8 % residual. The turbine was healthy the whole time.
After the transfer function was corrected the residual returned to -0.4 % inside 24 h.

**Cost.** Crew mobilisation INR 78,000, 2 h shutdown for inspection = 1,360 kWh = INR 4,352.
Total INR 82,352 for a null finding.

**Lesson.** A single-signal residual with no co-signature is a **sensor hypothesis** until
proven otherwise. This incident is why `scada-sensor-validation-sop` is a blocking gate rather
than an advisory one, and why no equipment fault may be asserted on a power residual alone. The
inconvenient part is that the signature was strong: -4.4 sigma sustained over nine days looked
more convincing than INC-2024-014 did at first detection. Magnitude is not evidence.
Corroboration is.

## 8. INC-2025-011 — Main bearing wear below alarm threshold, WT-002

| Field | Value |
|---|---|
| First detection | 2025-04-22, `main_bearing_temp_c` residual +5.8 K (+3.4 sigma) |
| Intervention | 2025-06-03, relubrication and interval change, replacement deferred |
| Lead time | 42 days |

**Signature.** Slow drift over six weeks. Absolute peak 68.9 degC at 38 degC ambient — 1.1 K
below the 70 degC warning, so **no SCADA alarm ever fired**. The residual persisted overnight,
which the ~55 min main bearing thermal time constant makes inconsistent with an ambient cause.
Vibration rose 2.0 → 2.9 mm/s with a portable capture showing energy concentrated at 1x and 2x
rotor order (0.21 and 0.42 Hz at 12.6 rpm), not at HSS orders. Grease sample returned Fe 310
ppm with spherical wear particles.

**Rule out first.** Anemometer validated (bias +0.03 m/s), no curtailment in the window, peers
WT-001 and WT-003 residuals within ±1 K.

**Intervention.** The economics comparison favoured relubrication with a halved regrease
interval and a re-inspection at 90 days over immediate replacement, given the low residual slope
and a main bearing exchange cost dominated by crane hire. Regrease INR 96,000, inspection
INR 85,000, 7 h downtime = 4,760 kWh = INR 15,232. Total INR 196,232.

**Lesson.** The finding sat 1.1 K under the absolute warning limit and would never have been
raised by threshold monitoring. Residual detection against a load and ambient normalised
expectation is what made it visible. Equally: a confirmed degradation finding does not
automatically mean replacement — the recommended action is the one the expected-loss comparison
selects, not the most conservative one available.

## 9. What the fleet record shows

Across the six cases, INR 6,384,256 of drivetrain cost was recorded. INC-2024-039 alone accounts
for 69.6 % of it, and it is the one case where the detector fired early and the human closed it
on an untested environmental hypothesis. The four episodes actioned on first detection ran to a
median lead time of 25 days and a median total cost of INR 192,584.

The false alarm, INC-2025-003, cost INR 82,352 — about 1.3 % of the total. The correct reading
of that ratio is not that false alarms are cheap; it is that the cost of a false alarm is
bounded and one-off, while the cost of a missed call compounds with the damage. That asymmetry
is why the corpus sets a low bar for *investigating* and a high bar for *asserting*: run the
sensor and environmental checks on everything, but never open a repair order on a single signal.

## Related documents

- `wind-gearbox-system` — machine constants, failure-mode signature table, alarm limits.
- `wind-generator-system` — load side of the HSS, referenced by INC-2024-027.
- `wind-gearbox-inspection-sop` — the inspection triggered in INC-2024-014 and INC-2024-039.
- `wind-vibration-analysis-sop` — spectral confirmation used in INC-2024-014 and INC-2025-011.
- `wind-oil-sampling-sop` — Fe, Cr and PQ index limits cited throughout.
- `wind-bearing-replacement-sop` — the up-tower and down-tower interventions.
- `wind-generator-thermal-sop` — cooling-path procedure for INC-2024-027.
- `scada-sensor-validation-sop` — the blocking gate created by INC-2025-003.
- `grid-curtailment-policy` — the check not run in INC-2024-039.
- `om-economics-policy` — cost, downtime and tariff basis for every figure above.
- `alarm-response-matrix` — disposition rules, including the recorded-rejection requirement.
- `incident-log-solar-inverter` — the equivalent record for `INV-001` .. `INV-024`.
