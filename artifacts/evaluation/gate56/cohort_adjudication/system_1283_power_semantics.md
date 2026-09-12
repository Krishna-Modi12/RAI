# System 1283 AC Power Channel Semantics -- Evidence-Based Adjudication

## Question
Gate 5.6A found that system 1283's selected AC power channel (`ac_power_metered_kW`,
metric_id 1040) has 39.5% negative readings (min -900 W). Is this a sensor fault, a wrong
channel, a sign-convention artifact, or legitimate signed power?

## Evidence gathered

### 1. The metrics dictionary reveals the plant-level channel is a DERIVED SUM, not 1040
The real per-system metrics dictionary (`scratch_gate56a/metrics_dicts/metrics_1283.parquet`)
records, for metric_id 1137 (`ac_power`, the catalog's plant-level total):

```
calc_details = "ac_meter_1_power_kW+ac_meter_2_power_kW"
```

This proves the *intended* plant AC output is the SUM of two independent meters
(metric_id 1041 = meter 1, metric_id 1042 = meter 2). Metric 1041 is absent from the real
downloaded 2019 telemetry entirely (confirmed in Gate 5.6A); metric 1042 IS present, is
0.0% negative, and its maximum (251,270 W) closely matches one of the site's two SMA Sunny
Central 250U (250 kW nameplate) central inverters -- strong evidence 1042 is a clean,
unidirectional, generation-only meter for half the plant.

Metric_id 1040 (`ac_power_metered_kW`, the channel Gate 5.6A selected as primary) carries
**no `calc_details` formula** -- it is its own independent sensor, not derived from 1041/1042.
Its maximum (498,700 W) is close to the full two-inverter nameplate (2 x 250 kW = 500 kW),
consistent with 1040 being a **whole-site metering point** (plausibly a utility/revenue
meter) rather than a per-inverter generation meter.

### 2. Negative readings correlate 100% with nighttime, 0% with any daytime interval
Joining metric 1040 against real POA irradiance (metric 1055) at matching real timestamps:

| | Negative (n=199,086) | Non-negative (n=305,298) |
|---|---|---|
| POA > 50 W/m^2 (daytime) | 0 (0%) | all daytime rows |
| POA <= 50 W/m^2 (night) | 199,086 (100%) | remaining night rows |

Every single negative reading occurs during a real, independently-measured nighttime
interval. The negative values cluster tightly: median -600 W, range -100 W to -900 W,
std 130 W -- a small, roughly constant magnitude consistent with nighttime station-service
/ parasitic-load consumption (inverter standby draw, site controls, etc.) being drawn from
the grid and recorded by a bidirectional net meter. This is not consistent with a sensor
fault (which would show larger, more erratic, or daytime-occurring negative excursions), a
wrong-channel selection (which would show a fundamentally different diurnal shape), or a
uniform sign-convention error (which would flip ALL values, not just the small nighttime
subset).

## Classification
**VALID_SIGNED_POWER** -- metric_id 1040 is a legitimate whole-site net AC power meter.
Negative values are small nighttime station-service loads, not a data-quality defect.

## Practical consequence for Gate 5.6C
No channel substitution or value correction is needed. The Gate 5.5 NIGHT quality filter
(`solar_elevation_deg <= 5 deg OR poa_wm2 < 20 W/m^2`) already excludes/flags nighttime
records before any generation-performance metric is computed -- and 100% of the negative
readings on this channel are nighttime records. Applying that pre-existing, already-frozen
policy resolves the ambiguity with zero new logic and zero invented correction. Gate 5.6C
must still apply the NIGHT filter before evaluating this system's residuals (as it would for
every system), and should document that this system's target channel is a net (not
pure-generation) meter for transparency.

## Not fully resolved
Metric 1041 (`ac_meter_1_power_kW`) is absent from the real acquired window, so the
catalog-preferred plant total (`ac_power` = meter_1 + meter_2) cannot be reconstructed or
cross-validated against 1040 in this acquisition window. If a future acquisition window adds
metric 1041, an independent cross-check (1040 vs meter_1+meter_2, restricted to daytime)
would further strengthen this classification.
