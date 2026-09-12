# Gate 5.5 — Solar Data Foundation & Evidence Architecture

*Date: 2026-09-12*  
*Protocol Status: GATE 5.5 COMPLETE (AUDITED & FROZEN)*  
*Test Suite: 290/290 passed (`pytest -q`)*  
*Static Analysis: Ruff clean (0 errors), Pyright clean (0 errors in `rai/eval/external/solar`)*

---

## 1. Executive Summary

Gate 5.5 marks the formal initiation of the Solar track within the Renewable Asset Intelligence (RAI) platform, building directly upon the evidentiary and physical principles established in Gates 5.0–5.4 for wind:

$$\begin{matrix}
\textbf{Wind Architecture} & \text{Wind SCADA} & \longrightarrow & P_{\text{expected}} = f(v) & \longrightarrow & r_P = P_{\text{actual}} - P_{\text{expected}} & \longrightarrow & \text{Anomaly Trajectory} \\
\textbf{Solar Architecture} & \text{PV Telemetry} & \longrightarrow & P_{\text{expected}} = f(G, T, \text{geom}) & \longrightarrow & r_P = P_{\text{actual}} - P_{\text{expected}} & \longrightarrow & \text{Health Evidence}
\end{matrix}$$

### Strict Gate Boundaries
In accordance with the Gate 5.5 specification:
- **NO deep neural network was trained.**
- **NO final anomaly detector was fitted.**
- **NO LLM was fine-tuned.**
- **NO final agentic RAG system was built.**
- **The gate serves exclusively to audit, inventory, classify, and certify the public solar data, modeling, and failure-evidence foundation.**

All public sources, features, and modeling tools have been audited under the RAI Evidentiary Taxonomy:
`INTERNAL_SYNTHETIC`, `EXTERNAL_REAL`, `SIMULATED_OUTCOME`, `MODEL_COMPARISON`, `HISTORICAL_AUDIT`, `SOFTWARE_INVARIANT`, `REAL_ENVIRONMENT`, and `PHYSICS_REFERENCE`.

---

## 2. Authoritative Solar Source Inventory & Evidence Tiers

We audited eight candidate public solar data and tool ecosystems across five distinct **Data Evidence Tiers**:
- **Tier 1:** Real operational PV telemetry + verified maintenance/failure/degradation evidence.
- **Tier 2:** Real operational PV telemetry without verified failure labels.
- **Tier 3:** Real environmental / resource / weather context (zero SCADA, zero failure labels).
- **Tier 4:** Physics / reference / modeling tools (not empirical ground truth).
- **Tier 5:** Synthetic or simulated operational / failure data.

| Source ID | Source Name | Provider | Evidence Tier | Primary Category | Tech Scope | Sites / Assets | Duration / Scope | Recommended RAI Role |
|---|---|---|---|---|---|---|---|---|
| `nrel_pvdaq` | NREL PV Data Acquisition (PVDAQ) | NREL / US DOE | **Tier 2** | `EXTERNAL_REAL` | Crystalline Si, Thin Film, CPV | 40+ US sites, 100+ systems | Multi-year (1-min / 15-min) | Primary operational telemetry & expected-power validation |
| `nrel_nsrdb` | National Solar Radiation Database (NSRDB) | NREL | **Tier 3** | `REAL_ENVIRONMENT` | Satellite / NWP resource grid | 4 km grid across Americas | 1998–present (30-min / 60-min) | External environmental context & satellite irradiance crosscheck |
| `sandia_pvlib` | Sandia PVPMC / pvlib-python | Sandia Nat Labs / PVPMC / NumFOCUS | **Tier 4** | `PHYSICS_REFERENCE` | Physical & empirical PV models | Universal mathematical library | Software / Reference Algorithms | Foundational expected-performance modeling engine ($P_{\text{expected}}$) |
| `dkasc_alice_springs` | Desert Knowledge Australia Solar Centre (DKASC) | DKASC / Ekistica | **Tier 1** | `EXTERNAL_REAL` | 40+ side-by-side PV technologies | Single multi-array facility (Alice Springs) | 2008–present (5-min resolution) | Real operational benchmark with documented soiling & technology comparisons |
| `edp_open_data_pv` | EDP Open Data Solar Portfolio | EDP Renewables | **Tier 2** | `EXTERNAL_REAL` | Utility-scale central inverter PV | Utility-scale commercial plants | Multi-month/year operational SCADA | Industrial utility-scale inverter telemetry benchmark |
| `kaggle_two_plant_india` | Two-Plant Solar Power Generation (India) | Anil Kumar / Kaggle Open Data | **Tier 2** | `EXTERNAL_REAL` | Commercial grid-tied PV (2 plants) | 2 plants, 22 inverters each | 34 days (15-min resolution) | Multi-inverter yield comparison & inverter-level residual testing |
| `nrel_synthetic_outages` | NREL PV Outage Synthetic Benchmark (Muller 2023) | NREL | **Tier 5** | `SIMULATED_OUTCOME` | Simulated string/inverter outages | Controlled synthetic configurations | Synthetic event sequences | Exact ground-truth benchmark for detection recall evaluation |
| `duramat_fleet` | DuraMAT PV Fleet Degradation Dataset | NREL / DuraMAT Consortium | **Tier 1** | `EXTERNAL_REAL` | Multi-fleet degradation tracking | 100+ fleets, multiple climates | Long-term multi-year degradation | Longitudinal degradation and aging evidence validation |

> [!IMPORTANT]
> **Evidentiary Boundary Enforcement:**
> - `nrel_nsrdb` contains satellite-derived solar irradiance and weather context. It contains **zero** PV performance telemetry and **zero** equipment failure labels.
> - `sandia_pvlib` contains mathematical models and reference empirical equations. It is classified strictly as `PHYSICS_REFERENCE`, **never** as physical ground truth.
> - `nrel_synthetic_outages` contains precisely labeled fault timestamps, but is classified as `SIMULATED_OUTCOME`, **never** as real-world field maintenance data.

---

## 3. Canonical Solar Signal Taxonomy

To avoid ambiguous sensor mapping and silent failures, Gate 5.5 establishes a canonical 26-signal semantic vocabulary across 8 functional categories, complete with physical validation bounds, standard SI units, and nighttime zero expectations:

| Canonical Name | Category | Standard Unit | Physical Range | Context Variable | Nighttime Zero | Semantic Meaning |
|---|---|---|---|---|---|---|
| `irradiance` | Environmental | $\text{W/m}^2$ | $[0.0, 1500.0]$ | Yes | Yes | Generic global/surface solar irradiance |
| `plane_of_array_irradiance` | Environmental | $\text{W/m}^2$ | $[0.0, 1500.0]$ | Yes | Yes | Total irradiance on the tilted collector plane (POA) |
| `GHI` | Environmental | $\text{W/m}^2$ | $[0.0, 1400.0]$ | Yes | Yes | Global Horizontal Irradiance |
| `DNI` | Environmental | $\text{W/m}^2$ | $[0.0, 1200.0]$ | Yes | Yes | Direct Normal Irradiance |
| `DHI` | Environmental | $\text{W/m}^2$ | $[0.0, 800.0]$ | Yes | Yes | Diffuse Horizontal Irradiance |
| `wind_speed` | Environmental | $\text{m/s}$ | $[0.0, 60.0]$ | Yes | No | Ambient wind speed for module convective cooling |
| `ambient_temperature` | Thermal | $^\circ\text{C}$ | $[-40.0, 60.0]$ | Yes | No | Dry bulb ambient air temperature |
| `module_temperature` | Thermal | $^\circ\text{C}$ | $[-30.0, 95.0]$ | Yes | No | Back-of-module surface temperature sensor |
| `cell_temperature` | Thermal | $^\circ\text{C}$ | $[-30.0, 105.0]$ | Yes | No | Effective PV junction operating temperature |
| `DC_power` | Electrical DC | $\text{kW}$ | $[0.0, 5000.0]$ | No | Yes | Measured total direct current power output |
| `DC_voltage` | Electrical DC | $\text{V}$ | $[0.0, 1500.0]$ | No | Yes | Direct current bus or string voltage |
| `DC_current` | Electrical DC | $\text{A}$ | $[0.0, 5000.0]$ | No | Yes | Direct current bus or array current |
| `AC_power` | Electrical AC | $\text{kW}$ | $[0.0, 5000.0]$ | No | Yes | Active alternating current power output |
| `AC_voltage` | Electrical AC | $\text{V}$ | $[0.0, 800.0]$ | No | No | Alternating current grid or inverter terminal voltage |
| `AC_current` | Electrical AC | $\text{A}$ | $[0.0, 5000.0]$ | No | Yes | Alternating current inverter output current |
| `inverter_output` | Inverter | $\text{kW}$ | $[0.0, 5000.0]$ | No | Yes | Total conditioned power output from inverter unit |
| `string_current` | Inverter | $\text{A}$ | $[0.0, 500.0]$ | No | Yes | Individual PV string direct current |
| `string_voltage` | Inverter | $\text{V}$ | $[0.0, 1500.0]$ | No | Yes | Individual PV string direct current voltage |
| `tracker_angle` | Tracker | $\text{deg}$ | $[-90.0, 90.0]$ | Yes | No | Tilt or azimuth tracking angle of the mounting system |
| `tracker_status` | Tracker | $\text{dimensionless}$ | $[0.0, 10.0]$ | Yes | No | Tracking controller status code or operational state |
| `grid_status` | Operational Context | $\text{dimensionless}$ | $[0.0, 10.0]$ | Yes | No | Interconnection grid status or curtailment flag |
| `curtailment` | Operational Context | $\text{kW}$ | $[0.0, 5000.0]$ | Yes | No | Grid-mandated power curtailment reduction |
| `energy_yield` | Operational Context | $\text{kWh}$ | $[0.0, 100000.0]$ | No | No | Cumulative or interval energy production yield |
| `availability` | Operational Context | $\text{ratio}$ | $[0.0, 1.0]$ | Yes | No | Operational availability factor |
| `soiling_indicator` | Health Evidence | $\text{ratio}$ | $[0.0, 1.2]$ | No | No | Transmission ratio or soiling index |
| `degradation_indicator` | Health Evidence | $\text{ratio}$ | $[0.0, 1.5]$ | No | No | Performance ratio or capacity degradation index |

### Strict Ambiguous Field Rejection
Any raw data column matching forbidden ambiguous patterns (e.g., `temp`, `power`, `voltage`, `status`, `sensor1`, `value`) is rejected by policy unless accompanied by explicit unit or description metadata that resolves it deterministically to a canonical signal.

---

## 4. Expected-Performance Readiness Audit ($P_{\text{expected}} = f(E, S)$)

The core requirement of the RAI solar architecture is the ability to compute an expected-performance residual:
$$r_P = P_{\text{actual}} - P_{\text{expected}}(G, T, \theta, S)$$

To support this physics-informed formulation, a dataset must provide both:
1. **Context variables:** Plane-of-array irradiance ($G_{\text{POA}}$ or $G_{\text{HI}}$) and module/ambient temperature ($T_{\text{mod}}$ or $T_{\text{amb}}$).
2. **Measurement variables:** Actual DC or AC power output ($P_{\text{DC}}$ or $P_{\text{AC}}$).

| Source ID | Status | Has Irradiance? | Has Temperature? | Has Power? | Has Geometry? | Audit Finding & Readiness Assessment |
|---|---|---|---|---|---|---|
| `nrel_pvdaq` | **`READY`** | Yes (POA & GHI) | Yes (Module & Ambient) | Yes (DC & AC) | Yes (Tilt, Azimuth, Rating) | Complete context and output channels across 40+ sites. Fully ready for Gate 5.6 $P_{\text{expected}}$ fitting. |
| `dkasc_alice_springs` | **`READY`** | Yes (POA & GHI) | Yes (Module & Ambient) | Yes (DC & AC) | Yes (Fixed, 1-axis, 2-axis) | Multi-technology arrays with co-located pyranometers and weather stations. Fully ready for Gate 5.6. |
| `edp_open_data_pv` | **`READY`** | Yes (Pyranometer) | Yes (Ambient & Module) | Yes (Inverter AC/DC) | Yes (Plant Specs) | Commercial utility-scale PV SCADA with weather stations. Fully ready for central-inverter modeling. |
| `kaggle_two_plant_india` | **`READY`** | Yes (Irradiation) | Yes (Ambient & Module) | Yes (DC & AC) | Partially (2 Plants) | Inverter-level AC/DC with on-site weather stations. Ready for multi-inverter residual comparison. |
| `duramat_fleet` | **`READY`** | Yes (Satellite + Sensor) | Yes (Temperature) | Yes (Power / Yield) | Yes (Fleet Metadata) | Curated multi-fleet longitudinal time series for degradation modeling. Ready. |
| `nrel_synthetic_outages` | **`PARTIALLY_READY`** | Yes (Synthetic GHI) | Yes (Synthetic Temp) | Yes (Synthetic Power) | Yes (Modeled System) | Simulated conditions with exact outage injections. Ready for recall testing; NOT real field data. |
| `nrel_nsrdb` | **`PARTIALLY_READY`** | Yes (GHI, DNI, DHI) | Yes (Ambient & Wind) | **NO** (0 kW output) | Geographic Grid Only | Contains complete atmospheric resource data, but zero PV power. Useful strictly for environmental normalization. |
| `sandia_pvlib` | **`PARTIALLY_READY`** | Reference Equations | Reference Thermal | Reference Electrical | Reference Geometry | Modeling algorithms and physics solvers. Serves as the mathematical modeling engine, not an empirical dataset. |

---

## 5. Data Quality Hazards & Audited Remediation Policies

Solar telemetry contains characteristic physical and telemetry hazards that require explicit, audited handling policies:

1. **Nighttime Behavior & Sun Elevation ($G \le 0$):**
   - *Hazard:* Irradiance sensors drop below zero due to thermal offsets; inverters enter sleep mode with zero power. Including nighttime data inflates sample counts and distorts residual distributions.
   - *Policy:* Filter out all records where solar elevation $\theta_{\text{elev}} \le 5^\circ$ or $G_{\text{POA}} < 20\,\text{W/m}^2$. Never treat nighttime zero power as an equipment outage.

2. **Inverter Power Clipping:**
   - *Hazard:* High irradiance induces DC power exceeding inverter nameplate rating, clamping AC power at rated capacity. This produces artificial negative residuals ($P_{\text{actual}} < P_{\text{expected}}$) that could be misdiagnosed as component degradation.
   - *Policy:* Tag operating points where $P_{\text{AC}} \ge 0.98 \times P_{\text{rated}}$ and $G_{\text{POA}} > 800\,\text{W/m}^2$ as `INVERTER_CLIPPING` and exclude them from linear residual tracking.

3. **Pyranometer Soiling & Calibration Drift:**
   - *Hazard:* Uncleaned pyranometers under-measure irradiance, causing $P_{\text{expected}}$ to be underestimated and masking real module degradation (or creating apparent "over-performance").
   - *Policy:* Perform clear-sky envelope crosschecks using `pvlib.clearsky` (e.g. Ineichen-Perez model) and compare ground sensors against satellite NSRDB estimates to identify sensor calibration drift.

4. **Sensor Dropouts & Missingness Gaps:**
   - *Hazard:* Communication loss or logger freezes produce frozen sensor values or nulls.
   - *Policy:* Never silently forward-fill sensor dropouts across gaps $> 30$ minutes. Flag missing intervals explicitly as `DATA_GAP`.

5. **Grid Curtailment & Power Export Restrictions:**
   - *Hazard:* Grid operator issues setpoint reductions, driving AC output below capability despite clear skies.
   - *Policy:* Cross-reference inverter power with grid interconnection status or utility curtailment command signals.

---

## 6. Failure Ground-Truth & Degradation Evidence Audit

A critical finding of Gate 5.5 is that **public solar data lacks a unified, labeled benchmark comparable to CARE for wind**:

| Source ID | Failure Ground Truth Classification | Label Details & Maintenance Provenance |
|---|---|---|
| `dkasc_alice_springs` | `MAINTENANCE_LOGS` | Semi-structured public maintenance logs, inverter replacement records, and soiling cleaning schedules. Real field operational ground truth. |
| `duramat_fleet` | `DEGRADATION_ONLY` | Fleet-level annual degradation rates (%/year) with quality scores. No granular timestamped fault sequences. |
| `edp_open_data_pv` | `MAINTENANCE_LOGS` | Commercial CMMS work orders and technician qualitative logs. High noise; requires manual alignment. |
| `nrel_synthetic_outages` | `VERIFIED_FAILURE_TIMELINES` | Synthetic benchmark with exact timestamped string, inverter, and tracker outage injection windows. Classified as `SIMULATED_OUTCOME`. |
| `nrel_pvdaq` | `NO_FAILURE_LABELS` | High-quality 1-min/15-min operational SCADA, but lacks systematic labeled failure records. |
| `kaggle_two_plant_india` | `NO_FAILURE_LABELS` | 34 days of inverter-level telemetry. Contains zero maintenance logs or labeled outages. |
| `nrel_nsrdb` | `NO_FAILURE_LABELS` | Satellite irradiance and meteorological model. Zero equipment or failure data. |
| `sandia_pvlib` | `NO_FAILURE_LABELS` | Software modeling library. Zero empirical failure ground truth. |

---

## 7. Licensing & Redistribution Audit

| Source ID | License / Terms | Redistribution Permitted? | Commercial Use? | API Key Required? | Dataset Citation Requirement |
|---|---|---|---|---|---|
| `nrel_pvdaq` | US Government Public Domain / CC0 | Yes | Yes | Yes (Free NREL Developer Key) | NREL PVDAQ citation required |
| `nrel_nsrdb` | US Government Open Data | Yes | Yes | Yes (Free NREL Developer Key) | Sengupta et al. (2018) NSRDB citation |
| `sandia_pvlib` | BSD 3-Clause | Yes | Yes | No | Holmgren et al., pvlib-python citation |
| `dkasc_alice_springs` | Creative Commons Attribution 4.0 (CC BY 4.0) | Yes | Yes | No (Direct Web / CSV Download) | DKASC / Ekistica attribution required |
| `edp_open_data_pv` | EDP Open Data License / Attribution | Yes | Yes | Yes (Registration Required) | EDP Open Data citation |
| `kaggle_two_plant_india` | CC BY-NC-SA 4.0 | Non-commercial only | No (Non-commercial) | Yes (Kaggle API token) | Anil Kumar Kaggle attribution |
| `nrel_synthetic_outages` | Creative Commons Attribution 4.0 (CC BY 4.0) | Yes | Yes | No | Muller et al. (2023) citation |
| `duramat_fleet` | US DOE / DuraMAT Open Access | Yes | Yes | No | DuraMAT PV Fleet Consortium citation |

---

## 8. Primary Research Questions & Evidentiary Answers

### Question 1: Which public solar datasets are actually suitable for RAI?
**Answer: SUPPORTED.**  
`nrel_pvdaq` and `dkasc_alice_springs` are fully suitable for real operational telemetry. `nrel_nsrdb` is suitable for environmental resource context. `sandia_pvlib` is suitable for the physics-reference layer. `duramat_fleet` is suitable for longitudinal degradation benchmarking.

### Question 2: Which datasets contain real operational measurements?
**Answer: SUPPORTED.**  
`nrel_pvdaq` (40+ sites, 100+ systems), `dkasc_alice_springs` (40+ side-by-side technologies), `edp_open_data_pv` (commercial central-inverter plants), and `kaggle_two_plant_india` (multi-inverter plants) contain genuine physical field measurements.

### Question 3: Which contain environmental context?
**Answer: SUPPORTED.**  
`nrel_nsrdb` provides continental-scale satellite irradiance ($G_{\text{HI}}, D_{\text{NI}}, D_{\text{HI}}$) and meteorological fields. `nrel_pvdaq` and `dkasc_alice_springs` provide co-located on-site pyranometers, anemometers, and ambient/module RTD sensors.

### Question 4: Which contain verified failure/degradation information?
**Answer: PARTIALLY_SUPPORTED.**  
Public solar data does **not** possess a universal labeled benchmark like CARE. `dkasc_alice_springs` and `edp_open_data_pv` provide real-world qualitative maintenance logs. `duramat_fleet` provides verified multi-year degradation rates. `nrel_synthetic_outages` provides exact failure timestamps, but is synthetic.

### Question 5: Which dataset/source should become the primary external solar benchmark?
**Answer: SUPPORTED.**  
`nrel_pvdaq` should serve as the primary operational telemetry benchmark, complemented by `dkasc_alice_springs` for multi-technology and soiling/cleaning validation.

### Question 6: Which dataset should be used for environmental normalization?
**Answer: SUPPORTED.**  
`nrel_nsrdb` (for satellite regional irradiance baseline and clear-sky modeling) combined with co-located on-site pyranometers from `nrel_pvdaq`.

### Question 7: Which physics/reference tools should define the expected-performance layer?
**Answer: SUPPORTED.**  
`sandia_pvlib` (pvlib-python) provides the authoritative industry-standard equations for solar position calculation, transposition (Perez/Hay-Davies models), module temperature estimation (Sandia/Faiman models), and DC/AC power conversion (De Soto five-parameter / Sandia Inverter models).

### Question 8: What important variables are still unavailable?
**Answer: SUPPORTED.**  
Individual string-level current/voltage telemetry is rarely available in older public utility datasets; high-resolution soiling transmission sensors are sparse outside dedicated research stations; and unified, machine-readable failure/fault logs are almost non-existent in public repositories.

### Question 9: Can a solar RAI Champion be built without using synthetic failure labels?
**Answer: SUPPORTED.**  
Yes. By adopting the same physics-informed residual architecture proven in wind ($r_P = P_{\text{actual}} - P_{\text{expected}}$), the solar Champion learns the baseline normal operating envelope from healthy operational SCADA ($G, T_{\text{mod}} \to P$), flagging persistent underproduction without requiring supervised failure labels for detector training.

---

## 9. Primary Recommendations for Gate 5.6

PRIMARY_OPERATIONAL_SOURCE: NREL_PVDAQ
PRIMARY_ENVIRONMENT_SOURCE: NREL_NSRDB
PRIMARY_PHYSICS_REFERENCE: SANDIA_PVPMC_PVLIB
PRIMARY_DEGRADATION_SOURCE: DURAMAT_PV_FLEET
PRIMARY_FAILURE_SOURCE: DKASC_ALICE_SPRINGS_MAINTENANCE_LOGS
KNOWN_DATA_GAPS: STRING_LEVEL_CURRENT_TELEMETRY, DIRECT_SOILING_SENSORS, STANDARDIZED_MACHINE_READABLE_FAULT_TIMELINES
RECOMMENDED_GATE_5_6_INPUT: NREL_PVDAQ_SITE_TELEMETRY_WITH_PVLIB_EXPECTED_POWER_BASELINE
