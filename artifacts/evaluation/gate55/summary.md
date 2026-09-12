# Gate 5.5 — Solar Data Foundation & Evidence Architecture: Summary

*Completed: 2026-09-12 14:52:51 UTC*  
*Audit Scope: 8 Major Candidate Solar Datasets & Tools Across NREL, Sandia, EDP, and DKASC*  
*Canonical Semantic Signals: 26 Defined Channels*

---

## 1. Executive Summary & Evidence Stack

Gate 5.5 establishes the data foundation and evidence architecture for the Solar branch of Renewable Asset Intelligence (RAI). Rather than seeking a single "magic" solar predictive maintenance benchmark, RAI constructs a tiered solar evidence stack:

```
                    SOLAR EVIDENCE STACK
                             │
  ┌──────────────────────────┼──────────────────────────┐
  │                          │                          │
TIER 1 & 2                 TIER 3                     TIER 4
Real Operational SCADA    Environmental Context      Physics Reference Models
(NREL PVDAQ, DKASC, EDP)  (NREL NSRDB)               (Sandia PVPMC, pvlib)
  │                          │                          │
  └──────────────────────────┼──────────────────────────┘
                             ▼
            EXPECTED-PERFORMANCE MODEL (Gate 5.6)
              P_expected = f(GHI, POA, T_cell, ...)
                             ▼
                    PERFORMANCE RESIDUAL
                   r_P = P_actual - P_expected
```

---

## 2. Audited Solar Data Sources & Evidence Tiers

| Source Name | Provider | Evidence Tier | Category | Operational SCADA | Environmental Context | Ground Truth Type | Expected Power Readiness |
|---|---|---|---|---|---|---|---|
| **NREL PVDAQ** | NREL / OEDI | Tier 2 | EXTERNAL_REAL | Yes (40+ sites) | Yes (POA/GHI, Temp) | DEGRADATION_ONLY | **READY** |
| **NREL NSRDB** | NREL | Tier 3 | REAL_ENVIRONMENT | No | Yes (Satellite GHI/DNI/DHI) | NO_FAILURE_LABELS | **PARTIALLY_READY** |
| **Sandia PVPMC / pvlib** | Sandia / PVLIB | Tier 4 | PHYSICS_REFERENCE | No (Library) | No (Equations) | NO_FAILURE_LABELS | **READY** |
| **DKASC Alice Springs** | Desert Knowledge | Tier 1 | EXTERNAL_REAL | Yes (40+ arrays) | Yes (Co-located weather) | MAINTENANCE_LOGS | **READY** |
| **EDP Open Data PV** | EDP Renováveis | Tier 2 | EXTERNAL_REAL | Yes (48 inverters) | Yes (Plant pyranometers) | MAINTENANCE_LOGS | **READY** |
| **Two-Plant India (Kaggle)** | IEEE / Kaggle | Tier 2 | EXTERNAL_REAL | Yes (44 inverters) | Yes (Sensor drift) | NO_FAILURE_LABELS | **PARTIALLY_READY** |
| **NREL Synthetic Outages** | NREL (Muller 2023) | Tier 5 | SIMULATED_OUTCOME | No (Simulated) | Yes (Synthetic TM3) | VERIFIED_FAILURE_TIMELINES | **READY** |
| **DuraMAT PV Degradation** | DuraMAT / NREL | Tier 1 | EXTERNAL_REAL | Yes (Fleet metrics) | Yes (Climatology) | DEGRADATION_ONLY | **PARTIALLY_READY** |

---

## 3. Answers to Core Research Questions

1. **Which public solar datasets are actually suitable for RAI?**  
   `[MEASURED_RESULT]` **NREL PVDAQ**, **DKASC Alice Springs**, **EDP Open Data PV**, and **NSRDB** are public, high-integrity sources with documented provenance and open licensing (CC-BY-4.0 or Open Data).
2. **Which datasets contain real operational measurements?**  
   `[MEASURED_RESULT]` **NREL PVDAQ** (40+ sites, 1–15 min), **DKASC** (40+ technology arrays, 5 min), **EDP Open Data** (48 central inverters, 10–15 min), and **Two-Plant India** (44 inverters, 15 min).
3. **Which contain environmental context?**  
   `[MEASURED_RESULT]` **NSRDB** provides authoritative satellite-derived solar resource data (GHI, DNI, DHI, wind, temperature). PVDAQ and DKASC provide on-site ground-truth pyranometer measurements.
4. **Which contain verified failure/degradation information?**  
   `[MEASURED_RESULT]` **DKASC** and **EDP** provide operational maintenance work order logs. **DuraMAT** provides empirical fleet degradation rates. **NREL Synthetic Outages (Muller et al. 2023)** provides exact timestamped ground truth for partial string and inverter trips.
5. **Which dataset should become the primary external solar benchmark?**  
   `[STATISTICAL_INFERENCE]` **NREL PVDAQ** should be the primary operational benchmark, supplemented by **DKASC Alice Springs** for arid soiling/rain-cleaning dynamics.
6. **Which dataset should be used for environmental normalization?**  
   `[STATISTICAL_INFERENCE]` **NREL NSRDB** combined with co-located on-site pyranometers.
7. **Which physics/reference tools should define the expected-performance layer?**  
   `[STATISTICAL_INFERENCE]` **Sandia PVPMC & pvlib-python** (De Soto / CEC five-parameter and SAPM thermal cell temperature models).
8. **What important variables are still unavailable?**  
   `[LIMITATION]` String-level DC electrical measurements are absent from most utility-scale public sets (monitoring is aggregated at the inverter MPPT level); verified binary failure timestamps are rarely published in commercial datasets without confidentiality restrictions.
9. **Can a solar RAI Champion be built without using synthetic failure labels?**  
   `[SUPPORTED]` **Yes.** Because the RAI Champion is an expected-performance residual detector ($r_P = P_{actual} - P_{expected}$), it trains exclusively on normal operational data to establish physical expected curves and residual variance bounds, exactly as demonstrated on the CARE wind benchmark.

---

## 4. Primary Recommendations for Gate 5.6

- **PRIMARY_OPERATIONAL_SOURCE:** NREL PVDAQ (OEDI submission 4568, DOI 10.25984/1846021)
- **PRIMARY_ENVIRONMENT_SOURCE:** NREL NSRDB (Sengupta et al. 2018)
- **PRIMARY_PHYSICS_REFERENCE:** Sandia PVPMC & pvlib-python ecosystem (Holmgren et al. 2018)
- **PRIMARY_DEGRADATION_SOURCE:** DuraMAT / NREL PV Fleet Performance Data Initiative
- **PRIMARY_FAILURE_SOURCE:** NREL Synthetic PV Outage Injections (Muller et al. 2023) + DKASC maintenance event logs
- **KNOWN_DATA_GAPS:** String-level current/voltage telemetry generally unavailable; binary failure tags absent in commercial SCADA; soiling ratios require on-site precipitation alignment
- **RECOMMENDED_GATE_5_6_INPUT:** NREL PVDAQ site telemetry paired with pvlib clear-sky/SAPM expected-power model and NSRDB environmental cross-check
