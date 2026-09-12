# Renewable Asset Intelligence Engine — The Complete Build Research Compendium

**Project:** Edge-Native Renewable Asset Intelligence (Predictive Maintenance for Solar & Wind)
**Purpose:** Every dataset, research paper, tool, API, hardware option, competitor fact, and economic number the team needs to build the system from scratch — verified against primary sources, mapped to our architecture pillars, and ordered into a build sequence.
**Companion document:** `Renewable_Asset_Intelligence_Predictive_Maintenance_Ideation_Report.md` (the concept). This document is the *evidence and construction kit* for that concept.
**Research basis:** 130+ targeted web searches, primary-source verification of Needle 2's model card, the CARE to Compare Zenodo record, NREL PVDAQ's OEDI entry, plus curated secondary analysis. Compiled September 2026.

---

## How to Use This Document

- **Sections 2–6** are the raw materials: datasets, wind papers, solar papers, agent/case-based work, and evaluation science. Every entry ends with its **build role** — what part of our system it powers.
- **Section 7** is the Needle 2 deep dive — verified model facts, integration blueprint, honest limits, and backup stacks.
- **Sections 8–10** are the construction stack: software, weather intelligence, and edge hardware.
- **Sections 11–12** are ammunition: competitors and economics/India numbers for the pitch and judge Q&A.
- **Sections 13–17** are the execution layer: our evaluation protocol, demo strategy, the resource→pillar map, the build sequence, and the production-grade horizon.

Pillar codes used throughout (from the ideation report):

| Code | Pillar |
|---|---|
| **P1** | Public historical data → broad training |
| **P2** | Asset digital twin / healthy-state model (expected behavior) |
| **P3** | Live IoT/SCADA telemetry ingestion |
| **P4** | Anomaly + degradation + failure-risk models |
| **P5** | Peer/fleet comparison |
| **P6** | Weather intelligence (environment-vs-equipment discrimination) |
| **P7** | Dust/soiling intelligence + cleaning economics |
| **P8** | Historical failure-trajectory memory (case-based retrieval) |
| **P9** | Local RAG (manuals, SOPs, maintenance records) |
| **P10** | Needle 2 local agent (tool-calling orchestration) |
| **P11** | Economic engine (revenue-at-risk, priority score, counterfactuals) |
| **P12** | Human-in-the-loop + closed-loop learning + fleet dashboards |

---

# 1. Domain Foundations (read before writing any code)

## 1.1 SCADA and the data you will actually touch

SCADA (Supervisory Control and Data Acquisition) is the industrial telemetry layer every renewable plant already runs. In practice you will consume **10-minute-averaged records** — the industry norm for wind SCADA (every major public wind dataset uses 10-minute averages with min/max/std/avg columns per channel) and the coarsest common denominator for solar monitoring. A 2 MW turbine producing ~50 channels at 10-minute resolution yields ~2.6M data points per year; an offshore turbine can expose 500–1,000+ channels (wind farm C in the CARE dataset has 957 features). This matters for the hackathon: you do not need high-frequency data to detect degradation — most published early-warning results work on 10-minute SCADA — but you must handle the *shape* of the data: multi-channel, noisy, with missing periods, curtailment, sensor drift, and status codes mixed with measurements.

For solar, the equivalent layers are **inverter-level and string-level monitoring** (current, voltage, power, DC/AC ratio) plus co-located meteorological stations (irradiance via pyranometers, module/ambient temperature, wind). PVDAQ, DKASC, and the two-plant Kaggle dataset all demonstrate this structure. String-level data is where early detection lives: a single degraded string is diluted to invisibility at plant level but obvious at string level.

**Build implication (P3):** our ingestion layer should normalize everything into the canonical schema from the ideation report (timestamp, asset identity, power, temperatures, environment, state codes). Every dataset in Section 2 gets mapped to that schema. `pymodbus` and `paho-mqtt` (Section 8) let us *simulate* a live SCADA feed by replaying these datasets, which is how the demo will work.

## 1.2 The P-F curve — the economic theory underneath everything

The P-F curve is the foundational model of condition-based maintenance. An asset moves through: **Potential failure (P)** — a detectable but not yet performance-limiting defect exists — then through a degrading interval to **Functional failure (F)** — the asset can no longer perform its intended function. The horizontal distance between P and F is the **P-F interval**: the window in which detection creates value. Detection after P but before F converts a breakdown into a planned intervention; detection after F is a failure the system missed.

Two operational rules follow, and both shape our product:

1. **Inspection intervals must be meaningfully shorter than the P-F interval.** The classical practitioner rule of thumb is to inspect at ½ to ⅓ of the P-F interval (sources in Section 6.9). Our "inspect within 72 hours" recommendation is exactly this logic compressed into an alert-level action.
2. **Detection earliness is a first-class metric, not a bonus.** A detector that fires 6 days before failure is worth a multiple of one that fires 12 hours before — same anomaly, different remaining response space. This is why the CARE score (Section 6.1) formalizes **Earliness** as one of four headline metrics, and why our economic engine converts earliness × probability × output into rupees (P11).

For wind drivetrains, published vibration-CMS practice gives a P-F window of **3–6 months** for bearings; SCADA-based temperature/power residuals typically detect in the **days-to-weeks** range. The CARE dataset's labeled anomaly windows span **4–98 days** before failure — an empirical P-F interval distribution for real farms. Cite this when a judge asks "how early is early?"

## 1.3 Wind failure-mode taxonomy — what actually breaks

A reliable taxonomy is the backbone of the RAG corpus (P9) and the fault dictionary the agent reasons over. The literature converges on the following:

| Subsystem | Typical failure modes | SCADA signatures |
|---|---|---|
| **Gearbox** | Bearing wear (Hertzian fatigue, axial cracking on high-speed shafts), gear tooth damage, lubrication breakdown, oil overheating | Gearbox oil temp residual ↑, bearing temp residuals ↑ vs. power/wind expectation, oil pressure anomalies, vibration (CMS only) |
| **Main bearing** | Raceway spalling, lubrication starvation | Bearing temperature residual ↑ months ahead, rotor rpm irregularity |
| **Generator** | Winding overheating, bearing faults, brush/slip-ring wear (DFIG) | Stator/winding temp residual ↑, generator bearing temp, alarm codes |
| **Pitch system** | Actuator/valve faults, battery degradation, sensor drift | Blade-pitch angle asymmetry between blades, pitch-motor currents, frequent pitch alarms; largest single downtime contributor (~23% of downtime per Windurance analysis) |
| **Power converter** | IGBT/module failures, capacitor aging, control faults | Converter temp ↑, reactive power scatter, trips; 15–20% of downtime (Windpower Monthly) |
| **Yaw** | Misalignment, brake wear, yaw-drive faults | Yaw error vs. wind vane, yaw duty cycles ↑, production drag |
| **Transformer/cell** | Overtemperature, oil issues | Transformer cell high-temp events (the most common event label in CARE wind farm C) |
| **Blades/rotor** | Imbalance, icing, erosion | Power-curve scatter at given wind speed, rotor speed anomaly |

Two structural facts from the failure-statistics literature (Section 12): a minority of failure modes causes the vast majority of downtime — one analysis attributes **95% of downtime to 25% of faults** — and gearbox events dominate *cost* (replacement $250k–300k, lead times up to 18 months) while pitch and converter events dominate *frequency*. Our prioritization engine (P11) must therefore weight probability × consequence, not raw failure count.

## 1.4 Solar failure-mode taxonomy

| Category | Mechanism | SCADA signature | Detection approach |
|---|---|---|---|
| **Soiling** | Dust/bird-dropping accumulation; partial or uniform | Gradual PR decline; recovers after rain/wash; string vs. plant uniformity | Soiling-ratio models (Kimber, stochastic-rate), weather-aware discrimination (P7) |
| **String faults** | Open circuit, blown fuse, connector failure | One string's current drops step-wise vs. peers | Peer-comparison residuals (P5) |
| **Inverter faults** | Clipping anomalies, capacitor/IGBT aging, control derating | AC output plateau shifts, efficiency drop, temp residual | Expected-power residuals (P2), autoencoders |
| **Module degradation** | LID, PID, cracks, delamination, hotspots | Slow PR decline ~0.3–1%/yr, mismatch losses | Year-on-year degradation (RdTools), clear-sky filtering |
| **Shading/new obstruction** | Vegetation growth, structural shadows | Recurring time-of-day PR dips | Peer + time-of-day pattern analysis |
| **Tracker faults** | Stuck axis, backtracking errors | Flat-topped or shifted daily power profile | Power-shape residuals |

The single most important intellectual point from the ideation report — *low output does not automatically mean broken equipment* — maps onto this table: soiling, clouds, temperature, and curtailment explain most production variance, and the weather/environment engine (P6/P7) must adjudicate before any fault is called. The physics tools for that adjudication are `pvlib` (clear-sky models, cell temperature, DC/AC models) and `RdTools` (year-on-year degradation and soiling-ratio estimation), both in Section 8.

## 1.5 The standards that make you sound like an insider

- **IEC 61400-12-1** — wind turbine power-performance measurement: anemometry class, measurement sectors, data filtering, the binned power-curve method, air-density correction. Judge-grade answer to "how do you normalize a power curve?" Use its binning logic in the wind digital twin. (Standard + Power Curve Working Group comparison of correction methods in Section 3.10.)
- **IEC 61724-1:2021** — PV system performance monitoring: sensor accuracy classes (A/B/C), data sampling/filtering, and the definitions of **Performance Ratio (PR)** and availability. Our solar twin's expected-power model and PR calculations should claim conformance to this methodology.
- **IEC 61400-30/31 (emerging)** — condition monitoring for wind (CMS Digitization / CDV-stage standardization of CMS data exchange) — worth naming for the production horizon (Section 17).

**Build implication:** we don't need certification for a hackathon, but structuring the twin's math and the dashboard's KPIs around these standards is free credibility. "PR computed per IEC 61724-1 methodology" is a sentence judges do not expect from a student team.

---

# 2. Public Datasets — The Raw Material

Strategy restated from the ideation report: **train broadly on public data, normalize carefully into the canonical schema, adapt locally to each customer's assets.** The datasets below are the "train broadly" layer. Everything here is legally usable in a hackathon demo; licenses are noted where verified.

## 2.1 Wind SCADA datasets

### 2.1.1 CARE to Compare — THE benchmark (P1, P4, P8, P13-eval)

- **Source:** Fraunhofer IEE (Gück, Roelofs, Faulstich et al.). Zenodo record **15846963** (v6, July 2025): https://zenodo.org/records/15846963 — 5.5 GB zip. Paper: *"CARE to Compare: A real-world dataset for anomaly detection in wind turbine data"*, **MDPI Data 9(12):138, 2024**, DOI `10.3390/data9120138`; arXiv:2404.10320. (~50 citations already.)
- **What's inside (verified from the record):** 95 datasets = **89 turbine-years** of 10-minute SCADA across **36 turbines** in three anonymized farms. Farm A: 5 onshore turbines in Portugal (from EDP's open data platform), 86 features, 22 datasets, fault-timing from a manual logbook. Farms B & C: German offshore farms, 257 and 957 features respectively. **45 of 95 datasets contain a labeled anomaly event leading up to a fault; 50 are normal-behavior series.** Event metadata includes fault descriptions (gearbox bearing damage, transformer-cell high temperature, etc.). Every data point carries a turbine-status label so training data can be filtered to healthy operation.
- **The CARE score:** Coverage, Accuracy, Reliability (false alarms), Earliness — a purpose-built four-axis metric for early anomaly detection (details in Section 6.1). Using the dataset's own metric is a credibility multiplier for the demo.
- **Known data issues (documented by the authors — read before coding):** per-timestamp **Avg values are generally plausible; Min/Max/Std are unreliable** in places (std > possible max, min > avg, all-zero columns — spelled out per sensor in the README). Farm A's pitch-angle min/max/std suffers angle wrapping (0°≡360°). Farm A's status labels are derived from the EDP logbook and should be used for training-filtering, not evaluation. Version 5→6 fixed a unit error (hPa vs bar) on two sensors and relabeled some events.
- **Build role:** this is simultaneously (a) the training corpus for anomaly/degradation models (P4), (b) the **failure-trajectory memory seed** (P8) — 45 real labeled pre-failure trajectories to retrieve against, and (c) the **primary evaluation harness** (Section 6). If the team builds only one dataset pipeline, build this one. Practical note: ~5.5 GB compressed is manageable on a laptop; load per-turbine CSVs lazily with pandas/pyarrow, not `glob` everything into RAM.
- **License:** open (CC-BY-type Zenodo release; confirm exact terms on the record page when submitting).

### 2.1.2 EDP Open Data — wind SCADA + failure logbook (P1, P8)

- **Source:** EDP's open data platform: https://www.edp.com/en/innovation/open-data/data (the underlying raw source of CARE farm A). The most-cited packaging is the Mendeley Data mirror with 2016–2017 SCADA for 5 onshore Portuguese turbines plus the manual **failure logbook** (gearbox/generator/transformer events): https://data.mendeley.com/datasets/zjxjnjp3xs
- **What's inside:** 10-minute SCADA signals for 5 turbines over ~1 year each + dated, component-specific failure entries. One of the very few public pairings of continuous SCADA with human-confirmed component failure dates.
- **Build role:** same as farm A of CARE but raw and un-anonymized — useful for teaching the trajectory-memory pipeline end-to-end without the anonymization layer. Also the citation anchor when judges ask "where do real failure labels come from?"

### 2.1.3 Kelmarsh & Penmanshiel (Cubico Sustainable Investments) — clean multi-turbine SCADA + status/alarm logs (P1, P2, P5)

- **Source:** Zenodo, maintained releases. Penmanshiel (14 × Senvion MM82, 28.7 MW, Scotland): record **5946808** (2016–mid-2021) and updated record **16807304** (2016–end-2024). Kelmarsh (6 turbines): records incl. the IFAC tutorial subset **15799719** (2022 power data with mean/std/min/max). Kaggle mirror of raw Kelmarsh: https://www.kaggle.com/datasets/arthurpierru/kelmarsh-scada-dataset
- **What's inside:** 10-minute SCADA (wind speed/direction, power, pitch, temps, rpm), **status, alarm and event logs**, downtime records, and metadata with turbine specs. Published under open licenses specifically for the research community.
- **Build role:** the **healthy-state modeling farm** (P2) — enough turbines of identical model to do real peer comparison (P5), enough history to train per-turbine baselines, and alarm logs to mine for the alarm-fusion technique (Section 3.7). The 2025-refresh Penmanshiel release extends to end-2024 — great for long-drift demos.

### 2.1.4 Hill of Towie — 10+ years of commercial farm data (P1, P2)

- **Source:** Zenodo record **14870021** (open access, via the WeDoWind/NIAID indexing).
- **What's inside:** over a decade of operational data from a Scottish commercial wind farm — one of the longest open windows available.
- **Build role:** long-horizon drift and degradation trends; demonstrates the "years of telemetry" longevity story in the privacy pitch (Section 5/6 of the ideation report).

### 2.1.5 La Haute Borne (ENGIE Green) — the OpenOA reference farm (P1, P2, P5)

- **Source:** 4 × Senvion MM82 (8.2 MW) in France, published via ENGIE under the Etalab Open License v2.0; canonical access through NREL's **OpenOA** demo data and the IEA Wind Task data ecosystem: https://openoa.readthedocs.io (data linked from there; re-description on Mendeley).
- **What's inside:** 10-minute environmental + power + status data; the de-facto benchmark for power-curve and operational-analysis code.
- **Build role:** pairs directly with NREL OpenOA (Section 8) — if we want to borrow validated operational-analysis code (Monte-Carlo availability, turbine long-term gaps, power-curve filtering), this farm is what that code expects as input.

### 2.1.6 KDD Cup 2022 / SDWPF — 134-turbine farm with NWP (P1, P4, P6)

- **Source:** Baidu KDD Cup 2022 challenge dataset. Paper: *"SDWPF: A Dataset for Spatial Dynamic Wind Power Forecasting"*, **Scientific Data (Nature), 2024** (Zhou et al., ~70 citations): https://www.nature.com/articles/s41597-024-03111-x; arXiv: https://arxiv.org/abs/2405.01929; data on HuggingFace: https://huggingface.co/datasets/aigrids/WindFarm_raw and preprocessing repos on GitHub/figshare.
- **What's inside:** 24 months of 15-minute SCADA (power, wind speed/direction, nacelle temps, pitch, nacelle position) for **134 turbines** (Longyuan Yazangkou farm, China) **plus day-ahead numerical weather prediction (NWP)** columns — the "weather forecast given to the plant" layer.
- **Build role:** the only large open dataset that includes NWP covariates — ideal for prototyping the weather-vs-equipment discrimination logic (P6) where the model sees forecast conditions vs. realized output. Also a fleet-scale (134-asset) peer-comparison sandbox.

### 2.1.7 NREL Gearbox Reliability Collaborative (GRC) — physical gearbox signatures (P1, P2, P9)

- **Source:** NREL GRC dynamometer test campaigns (data via https://data.openei.org and OSTI; companion GRC failure-records database, 2012 reports).
- **What's inside:** controlled dynamometer runs of **healthy and deliberately damaged gearboxes of identical design** — accelerometer channels, torque, temperature; plus the GRC failure-records database documenting which components failed in field gearboxes (industry analysis: bearings ≈ 64% of gearbox failures, gears ≈ 25%).
- **Build role:** grounding truth for the fault dictionary (P9) — "what does a failing planetary bearing actually look like" — and a defensible physics anchor for gearbox-focused demo narratives. (High-frequency vibration is outside 10-minute SCADA, so treat as enrichment, not the main pipeline.)

### 2.1.8 Fraunhofer LBF open vibration dataset (P1, P4)

- **Source:** Mostafavi et al. 2024, open-access (PMC): a 750 W test turbine with accelerometers + tachometer over multiple structural states.
- **Build role:** small, fully open vibration set usable for an edge-side anomaly demo (models tiny enough to run on a Pi). Secondary.

### 2.1.9 WIND Toolkit — synthetic grid-scale wind resource (P1, P6)

- **Source:** NREL Wind Integration National Dataset (Draxl et al. 2015, ~890 citations): https://www.nrel.gov/grid/wind-toolkit.html, API at https://developer.nrel.gov/docs/wind/wind-toolkit/, AWS-hosted via HSDS (https://registry.opendata.aws/nrel-pds-wtk).
- **What's inside:** gridded hourly wind speed/direction/temperature at multiple hub heights (10–200 m) + pressure, 2007–2013, ~2M US locations, from mesoscale NWP.
- **Build role:** not turbine SCADA — use for wind-resource context, site climatology, and demo-location storytelling where a customer site has no met mast.

### 2.1.10 OpenWindSCADA — the meta-repository (meta)

- **Source:** https://github.com/sltzgs/OpenWindSCADA — curated index of open wind-SCADA datasets with descriptions, data-quality notes, and reusable CSV loaders.
- **Build role:** accelerates ingestion for entries 2.1.1–2.1.5; check here before writing a loader from scratch.

## 2.2 Solar PV datasets

### 2.2.1 NREL PVDAQ — the flagship solar corpus (P1, P2, P5, P7)

- **Source:** NREL Photovoltaic Data Acquisition. OEDI entry: https://data.openei.org/submissions/4568 — DOI **10.25984/1846021** (Deline, Perry, Deceglie, Muller, Sekulic, Jordan; NREL 2021, updated 2025). Direct bulk access on AWS: `aws s3 ls --no-sign-request s3://oedi-data-lake/pvdaq/` — CSV lake ≈ **512 GB**, parquet lake ≈ **17 GB** (prefer parquet). Documentation: https://github.com/NREL/pvdaq (data docs). Data map/wiki: https://openei.org/wiki/PVDAQ. License: **CC BY 4.0** (per OEDI site terms).
- **What's inside (verified):** system metadata + performance time series from dozens of experimental and commercial PV sites across climates and years; per-system files with hardware metadata and geo-location; many systems include irradiance, module/ambient temperature, wind speed, and precipitation. Curated subsets exist (e.g., the 2023 DOE Solar Data Prize directories). Used by NREL's own degradation and soiling research — including the **PV Fleet Performance Data Initiative**.
- **Build role:** the primary "train broadly" corpus for the solar twin (P2), soiling behavior across climates (P7), and multi-system peer structures (P5). The parquet lake + site metadata makes site selection by climate/technology trivial — pick arid + humid sites to demo weather-vs-soiling discrimination.

### 2.2.2 NSRDB — the solar resource backbone (P1, P6)

- **Source:** NREL National Solar Radiation Data Base: https://nsrdb.nrel.gov (free access + API; AWS mirror: https://registry.opendata.aws/nrel-pds-nsrdb). Canonical paper: Sengupta et al. 2018, *Solar Energy*, ~1,870 citations.
- **What's inside:** satellite-derived hourly (and 5–30 min in current releases) GHI/DNI/DHI + meteorology, serially complete, 1998→present, contiguous US + growing international coverage (Americas, parts of Asia).
- **Build role:** irradiance ground truth for expected-power models when the plant's own pyranometers are suspect (they often are); also the weather-history layer for degradation analysis. Pairs with pvlib/RdTools.

### 2.2.3 DKASC Alice Springs — multi-technology longitudinal testbed (P1, P2, P5, P7)

- **Source:** Desert Knowledge Australia Solar Centre, Alice Springs (arid central Australia): https://dkasolarcentre.com.au — public download portal with historical CSVs (data notes: https://dkasolarcentre.com.au/download?location=alice-springs).
- **What's inside:** dozens of side-by-side PV systems (different module/inverter technologies) at 5-minute resolution since ~2008+, each with weather-station data. Arid, dusty climate with pronounced dry-season soiling and episodic rain-cleaning — a natural soiling laboratory.
- **Build role:** (a) technology-controlled **peer comparison** — identical weather, different hardware, so anomalies are attributable; (b) soiling-ratio and rain-cleaning event mining for the P7 engine; (c) long degradation drift curves.

### 2.2.4 Two-plant inverter-level dataset (Kaggle) — fastest prototype (P1, P4, P5)

- **Source:** "Solar Power Generation Data" — two Indian plants (one single-inverter layout, one multi-inverter), 15-minute inverter-level AC/DC power + plant weather sensors, ~34 days. Kaggle: https://www.kaggle.com/datasets/anikannal/solar-power-generation-data (also on IEEE DataPort).
- **What's inside:** per-inverter generation + per-plant irradiance/ambient/module temperature. Small enough to prototype in an afternoon.
- **Build role:** day-1 demo data — inverter-level residuals and peer comparison with minimal plumbing. Caveat: known sensor quirks (irradiance sensor drift at plant 1) — treat weather data skeptically, which is itself a good talking point about sensor QC.

### 2.2.5 NREL synthetic PV with injected string outages — labeled anomalies (P1, P4, P13-demo)

- **Source:** Muller et al. (NREL) 2023 synthetic time-series releases on https://data.openei.org / https://www.nrel.gov/publications (methodology documented over ~35 pages).
- **What's inside:** realistic PV production series with **3 injected outage events each** (e.g., −10% mean power over ~21 days) with known ground-truth timing.
- **Build role:** a labeled test set for detector sensitivity/recall — you can quote exact detection-latency numbers because ground truth is exact. Also the methodological template for our own fault-injection (Section 14).

### 2.2.6 PV IV-curve + EL image dataset (P1, P9)

- **Source:** NREL/DOE release on data.openei.org / catalog.data.gov: 613 matched current–voltage flash traces + electroluminescence images of commercial modules with defect annotations.
- **Build role:** grounds the module-level failure taxonomy (cracks, PID) that the RAG corpus references when explaining *why* a SCADA pattern suggests module degradation.

### 2.2.7 Sandia PVPMC + NREL Soiling Map + BMS (P1, P6, P7)

- **PVPMC datasets & models:** https://pvpmc.sandia.gov — curated irradiance/sky-image/weather corpora and the reference performance-model documentation that pvlib implements.
- **NREL PV Soiling Map:** soiling parameters from ~255 stations worldwide (https://www.nrel.gov/solar/soiling-map.html); companion finding: soiling losses ≈ **≥0.5%/yr in rainy climates vs >7%/yr in arid ones** — our soiling priors per climate zone.
- **NREL Baseline Measurement System (BMS):** Golden, Colorado high-quality irradiance/meteorology since 1981 (via https://midcdmz.nrel.gov) — gold-standard sensor reference for QC experiments.

### 2.2.8 String-inverter SCADA with co-located weather (P1, P4)

- **Source:** Mendeley Data releases of half-hourly records from 8 string inverters + 15-minute weather from 3 on-site stations (search "PV SCADA string inverter Mendeley").
- **Build role:** string-level fault simulation with paired weather — the exact structure our solar residual engine consumes.

## 2.3 Weather, dust, and environmental data (P6, P7)

| Source | What it gives | Access | Build role |
|---|---|---|---|
| **NASA POWER** | Hourly/daily solar (GHI, DNI, DHI, PAR), temperature, wind, humidity, pressure — 380+ variables, global, 1981→ (meteorology) / 1984→ (solar) | Free REST API: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ (verified); AWS mirror; R pkg `nasapower` | Zero-cost weather covariates for any demo site; historical alignment with SCADA for healthy-state features |
| **ERA5 / ERA5-Land** | Reanalysis: hourly, 1950→~real-time, 50+ variables incl. wind at 100 m, irradiance components | Free via Copernicus CDS API: https://cds.climate.copernicus.eu; GEE collection `ERA5_LAND_HOURLY` | Climatology backbone; long-term wind resource; consistent weather features across years |
| **CAMS global forecasts** | Twice-daily **5-day aerosol forecasts** incl. **desert dust optical depth**, AOD@550nm, 7 aerosol species | Free via ADS: https://ads.atmosphere.copernicus.eu (datasets → global atmospheric composition forecasts) | **Core of dust intelligence**: forecast DOD → soiling-rate priors → cleaning-before/after-dust-event economics (P7) |
| **MERRA-2** | Reanalysis with **assimilated aerosols** — surface dust mass concentration, hourly, 1980→ | NASA GMAO: https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/ (+ Google Earth Engine collection) | Historical dust exposure reconstruction — correlates multi-year PR drift at arid sites with dust history |
| **AERONET** | Ground sun-photometer AOD — the gold-standard validation reference | Free: https://aeronet.gsfc.nasa.gov | Validate CAMS/MERRA-2 dust signals for the demo region before trusting them |
| **NOAA NESDIS STAR** | Operational satellite AOD retrievals | https://www.star.nesdis.noaa.gov | Independent satellite AOD stream |
| **Open-Meteo** | Free historical + forecast weather + **Air Quality API (PM2.5/PM10)** | https://open-meteo.com/en/docs/historical-weather-api (verified) + /en/docs/air-quality-api | Frictionless prototyping API — one JSON call for weather + dust proxy, non-commercial free |
| **IMD (India)** | Official forecasts, nowcasts, 0.25° daily gridded rainfall 1901→2024 (NetCDF) | https://mausam.imd.gov.in + https://www.imdpune.gov.in; python tooling: IMDLIB https://imdlib.readthedocs.io | India ground truth: monsoon rain-cleaning regimes vs pre-monsoon dust seasons |
| **OpenWeather Air Pollution** | PM2.5/PM10/O₃, hourly, history since Nov 2020 + forecast | https://openweathermap.org/api/air-pollution (history tier: paid) | Secondary dust proxy with clean JSON |
| **AQICN** | Station-level real-time AQI worldwide | https://aqicn.org/api/ | PM ground truth for calibration |
| **Solcast** | Commercial high-res irradiance + PV power forecasts (live cloud tracking) | https://solcast.com (commercial, AWS-hosted) | Benchmark to score our free weather stack against — not the free-tier dependency |

**Integration logic for the dust engine (P7):** CAMS DOD forecast (next 5 days) + MERRA-2 history (climate prior) + local rain (POWER/IMD/Open-Meteo) → soiling-rate estimate → cleaning-window optimization vs. tariff. Validate the dust signal against AERONET where stations exist. This is exactly the "clean before or after the dust storm" reasoning that makes the demo memorable.

## 2.4 India-specific context data (P6, P11-market)

- **NIWE (National Institute of Wind Energy):** wind resource maps at 120 m/150 m agl + station network: https://maps.niwe.res.in / https://niwe.res.in — siting context for demo wind assets.
- **VEDAS (ISRO/SAC) renewable atlas:** WebGIS layers of solar/wind potential: https://vedas.sac.gov.in — credible national maps for slides.
- **MNRE physical progress dashboards:** installed capacity by technology/state: https://mnre.gov.in — the capacity numbers in Section 12 track from here/JMK Research.
- **IMD gridded rainfall (IMD Pune, 0.25°, 1901–2024):** the monsoon regime layer for rain-cleaning logic in India.

---
# 3. Wind Research Papers — Deep Dives

How to read this section: papers are ordered from "read first" (foundations/reviews) to specialized. Each entry gives the citation, the core method, **what to steal for our build**, and the pillar it powers. All linked papers are open-access unless noted.

## 3.1 Zaher, McArthur, Infield & Patel (2009) — the blueprint everyone copies

*"Online wind turbine fault detection through automated SCADA data analysis."* Wind Energy 12(6). ~686 citations. Open access via University of Strathclyde: https://pureportal.strath.ac.uk/en/publications/online-wind-turbine-fault-detection-through-automated-scada-data-anal

**Core method.** Two-stage normal-behavior modeling on 10-minute SCADA: (1) **Auto-Associative Kernel Regression (AAKR)** — a kernel-memory model that reconstructs "expected" sensor values from stored healthy operating history; (2) **Optimal Residual Analysis (ORA)** — an adaptive statistical filter over the residuals (actual − expected) that learns which residuals are abnormal. Demonstrated on yaw and gearbox temperature channels.

**Why it matters to us.** This is the original "reconstruct → residual → adaptive threshold" architecture that most later SCADA papers (including commercial systems) build on. It is also, almost line-for-line, what our digital twin pillar (P2) does: store healthy behavior, reconstruct expected state, watch residuals.

**Steal:** the AAKR formulation is implementable in ~50 lines of Python (kernel regression over a healthy-state matrix — scipy suffices) and is a perfect *first* twin: interpretable, no training hyperparameters to speak of, edge-friendly (memory-based, no gradient descent). Also steal their framing: normalize residuals by operating condition, not absolute thresholds.

## 3.2 Kusiak & Verma (2011) — data-mining pitches and bearings

*"A data-driven approach for monitoring power curve performance"* and especially *"A data-driven approach for monitoring blade pitch faults in wind turbines."* IEEE Transactions on Sustainable Energy 2(1). (Related: Kusiak & Verma 2012, *"Analyzing bearing faults in wind turbines: a data-mining approach,"* Renewable Energy, https://www.sciencedirect.com/science/article/abs/pii/S0960148111003895, ~285 citations.)

**Core method.** Boosted trees / bagged trees / random forests on SCADA channels to predict expected values of power, pitch angle, and generator temps; monitoring the prediction residuals across operating regimes to catch blade-pitch faults and bearing faults before alarms fire.

**Steal:** the residual-monitoring pattern applied per *component* (not just whole-machine), and the demonstration that classic supervised regressors on 10-minute SCADA are enough — no exotic deep learning needed for a credible early-warning story. Good citation for "our ML is defensible."

## 3.3 Tautz-Weinert & Watson (2016) — THE review to read first

*"Using SCADA data for wind turbine condition monitoring — a review."* IET Renewable Power Generation 11(4): 382–394. Open access: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rpg.2016.0248

**Core method.** Systematic review of SCADA-based condition monitoring: normal-behavior models, curve-based methods, clustering, alarm analysis; the paper's lasting contribution is the **data-curation taxonomy** — filtering curtailment, downtime, sensor faults and icing *before* modeling, because dirty training data produces baselines that hide real degradation.

**Steal:** the curation checklist becomes our preprocessing module (P2): (a) remove curtailed/downtime periods via status codes; (b) filter physically impossible values; (c) bin or condition on wind speed; (d) validate against a second sensor where available. Judges ask "how do you avoid false alarms?" — the honest answer starts with this checklist, and the IET 2025 LOF paper (3.8) shows what happens when filtering is overdone.

## 3.4 MDPI Energies (2020) — the faults→signals mapping table

*"Using SCADA Data for Wind Turbine Condition Monitoring: A Systematic Review"* / fault-and-signal reviews, Energies 13(12):3132: https://www.mdpi.com/1996-1073/13/12/3132

**Core method.** Compendium of common wind-turbine faults mapped to the SCADA signals that expose them (temperature residuals, power-curve deviation, pitch/yaw statistics) and the signal-processing methods used for each.

**Steal:** their fault→signal mapping is essentially the first draft of our fault dictionary (P9) — which channels the twin should reconstruct per subsystem. Use it to justify channel selection per asset type in the demo.

## 3.5 Chesterman, Vermosen, Natarajan & Jensen (2023) — NBM bake-off, read second

*"Overview of normal behaviour modelling approaches for wind turbine condition monitoring based on SCADA data."* Wind Energy Science 8: 1069–1097. Open access: https://wes.copernicus.org/articles/8/1069/2023/ (~76 citations and climbing fast).

**Core method.** Rare among reviews: the authors **implement and benchmark** several state-of-the-art NBM techniques (regression baselines, neural nets, Gaussian-process variants) on the same real SCADA data, with matched preprocessing, and compare detection performance and compute cost.

**Steal:** this tells us which model family to baseline first and what performance to expect — we don't have to re-run their bake-off before choosing. Their result pattern (simple regression + good filtering ≈ competitive; GPs add calibrated uncertainty at a compute price) directly shapes the twin implementation plan: start linear/GBM, add GP only where uncertainty matters (alert confidence).

## 3.6 Pandit, Infield & Kolcios (2018, 2020) — Gaussian-process power-curve twins

*"SCADA-based wind turbine anomaly detection using Gaussian process models."* IET Renewable Power Generation (2018, ~147 citations; 2020 follow-up adding wind direction, ~93). https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rpg.2018.6044

**Core method.** Non-parametric **Gaussian-process regression** over the power curve (and later power + wind-direction + density), producing a predicted power *with a variance* at every operating point. Alerts are raised when measured power falls outside the GP's confidence band; adding operational covariates (direction, air density) measurably shrinks uncertainty and false alarms.

**Steal:** two things. (1) The GP's posterior variance is a *calibrated, per-datapoint confidence* — exactly the kind of uncertainty our alerting needs to avoid "hard thresholds everywhere" (P2/P4). (2) The covariate-expansion lesson: conditioning on wind direction and density is cheap and removes whole classes of false positives. For the edge, GP inference over a few thousand inducing points runs comfortably on CPU (numpy/GPyTorch sparse).

## 3.7 UPC fleet work (2020) — fusing alarms with residuals

*"Wind Fleet Generator Fault Detection via SCADA Alarms and Autoencoder"* (Universitat Politècnica de Catalunya, open PDF via UPCommons).

**Core method.** Combines an autoencoder trained on analog SCADA channels with **alarm-log mining** (frequency/pattern of status codes) for generator fault detection at fleet scale; per-turbine residuals are ranked relative to farm norms.

**Steal:** the two-evidence-channel design — numeric residuals *and* discrete alarm patterns — is exactly what Needle 2 should see in its evidence packet (P10): "residual z-score 3.1 on gearbox bearing temp + 4 pitch-fault codes in 14 days." Also adopt fleet-relative ranking (P5): the outlier turbine matters more than the absolute residual.

## 3.8 Threshold engineering — LOF + dynamic thresholds, stationarity windows

- *"Fault Diagnosis and Dynamic Threshold Early Warning of Wind Turbines Based on LOF"* (2025, IET The Journal of Engineering): https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/tje2.70098 — Local Outlier Factor over the wind-speed–power scatter with **operating-point-dependent dynamic thresholds**; the authors candidly note LOF filtering can discard genuinely healthy samples.
- Dao (2024) — *"Anomaly detection of wind turbines based on stationarity"* (sliding-window stationarity monitoring; model-light, ~60 citations): https://www.sciencedirect.com/science/article/abs/pii/S0960148124004302

**Steal:** (1) dynamic thresholds conditioned on operating state — a single global cutoff is a false-alarm factory; (2) the stationarity monitor as a nearly free secondary detector that runs beside the main twin in the demo; (3) the LOF paper's warning becomes an explicit test in our pipeline: *filtering must preserve healthy-data coverage* (also flagged in our evaluation protocol, Section 13).

## 3.9 Deep/unsupervised anomaly detection on SCADA — the modern layer

- *"Deep anomaly detection in horizontal axis wind turbines"* (2022, Energy & AI, open): https://www.sciencedirect.com/science/article/pii/S2666546822000076 — unsupervised deep AD framework on SCADA; useful because it assumes **no labeled failures**, matching our public-data constraints.
- Miraftabzadeh et al. (2025) — deep autoencoder for PV time-series with sparse metadata (listed with solar in 4.x, methodological sibling).
- Pereira & Silva (2018) — variational recurrent autoencoder for energy time series (IEEE, ~228 citations): probabilistic latent scoring; cross-domain landmark.

**Steal:** the unsupervised framing (train only on healthy data, score deviations) is our default posture; supervised classifiers only enter after technician feedback accumulates (P12 closed loop). The VRAE's latent-space scoring is a candidate for the trajectory-memory encoder (P8): embed 72-hour windows into a latent space, retrieve nearest historical pre-failure trajectories.

## 3.10 Power-curve standards & corrections

- **IEC 61400-12-1** (power-performance measurement; 2022 revision): binned power-curve method, measurement sectors, density normalization. Standard available via iTeh/ANSI previews: https://standards.iteh.ai
- Lee et al. (2020) — Power Curve Working Group assessment of **five power-curve correction methods** (~45 citations): https://docs.pcwg.org (PCWG tool + report).

**Steal:** IEC-style binning + density correction is the defensible way to build the wind twin's expected-power curve; PCWG's comparison justifies whichever correction we implement. One paragraph in the appendix: "expected power computed with IEC 61400-12-1 binning; air-density correction per PCWG method X" — instant technical credibility.

## 3.11 RUL & prognosis — SCADA-only failure prediction

- **Encalada-Dávila et al. (2021)** — *"Wind turbine main bearing fault prognosis based solely on SCADA data"* (~110 citations, open via PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC8124482/ — deep learning on component temperatures + rpm + ambient temp predicts main-bearing failures **months ahead** using only standard SCADA. Proves the low-cost-SCADA-only prognosis story we pitch.
- **Vidal et al. (2023)** — main-bearing PdM with a minimal feature set (temps + rotor speed): https://iopscience.iop.org/article/10.1088/1742-6596/2526/1/012006 — the minimal-feature recipe is ideal for edge deployment (fewer channels = smaller model, fewer failure points).
- **Carroll, McDonald & McMillan (2018)** — *"Wind turbine gearbox failure and remaining useful life prediction"* (~153 citations, open via Strathclyde): https://strathprints.strath.ac.uk/63369/ — three ML algorithms predicting gearbox failure/RUL with **asymmetric penalty for missed failures** — the cost-sensitive framing our priority score adopts.
- **Desai et al. (2020)** — gearbox axial-cracking prognosis up to **1 month ahead** from SCADA/CM: https://papers.phmsociety.org/index.php/phme/article/view/3557 — the citable lead-time number for gearbox cracks.
- **ASME (2026) / Cambridge AI-EDAM (2025) RUL reviews** — taxonomies of deep RUL methods for rotating machinery: read when starting serious RUL work; not needed for the hackathon MVP beyond citing that RUL-from-SCADA is an active, mature field.

**Steal:** (1) SCADA-only prognosis is publishable truth — our failure-risk model (P4) doesn't need CMS hardware; (2) cost-asymmetric training/evaluation (missed failure ≫ false alarm) mirrors the economics engine (P11); (3) minimal channel sets keep the edge footprint small.

## 3.12 Transfer learning — cold-start assets

- **Energy & AI (2025)** — *"Fault detection in new wind turbines with limited data by generative deep transfer learning"*, open: https://www.sciencedirect.com/science/article/pii/S2666546825001582 — **official code: https://github.com/EnergyWeatherAI/WT_Generative_Domain_Adaptation** — generative domain adaptation moves SCADA samples from data-rich turbines to cold-start turbines.
- **Zgraggen et al. (2021)** — three transfer-learning frameworks for semi-supervised fault detection between turbines (PHM Society, open): https://papers.phmsociety.org/index.php/phme/article/view/2835

**Steal:** the answer to "your twin needs months of history — what about a new asset?" is *pretraining on public fleets (P1) + domain adaptation to the new asset*. Having a working codebase to point at (the EnergyWeatherAI repo) turns a hand-wave into a method.

## 3.13 Interpretability & LLM-assisted diagnosis

- **Bindingsbø et al. (2023)** — interpretable ML for generator-bearing fault detection with **SHAP** attributions (Frontiers, open): https://www.frontiersin.org/articles/10.3389/fenrg.2023.1116907/full
- **Tan et al. (2025)** — LLMs alongside ML for gearbox bearing-failure prediction from SCADA (MDPI): https://www.mdpi.com/2076-3417/15/14/6262 (check volume on the record page) — direct precedent for an LLM reasoning over SCADA-derived features, i.e., our Needle 2 layer (P10).

**Steal:** SHAP-style attributions become *evidence sentences* the agent can quote ("gearbox-oil-temp residual contributed 41% to the anomaly score"); the 2025 LLM paper is the citation that says "LLM-over-SCADA is legitimate research, not a gimmick."

---

# 4. Solar Research Papers — Deep Dives

## 4.1 Garoudja et al. (2017) — the statistical baseline every solar detector must beat

*"Statistical fault detection in photovoltaic systems."* Solar Energy 150 (~368 citations). Open via KAUST repository: https://repository.kaust.edu.sa/handle/10754/625745

**Core method.** DC-side fault detection from string electrical data: per-string expected current/power from irradiance + temperature regression, with statistical control limits; classifies open-circuit, degradation, and partial shading on real plant data.

**Steal:** this is the "hello world" of string monitoring — simple, robust, and exactly what our peer-comparison residuals generalize (P5). Our pitch line: "classical statistical detectors catch step faults; we add context, history, and economics." Know this paper because a judge who knows solar will know it.

## 4.2 Taghezouit et al. (2024) — model-based PV FDD review

*"Model-based fault detection in photovoltaic systems: a review"* / recent-advances review (~105 citations): https://www.sciencedirect.com/science/article/abs/pii/S2666546824000113 (Energy & AI)

**Core method.** Surveys expected-power/thermal-model residuals, performance-ratio methods, and hybrid model+ML approaches for PV fault detection and diagnosis.

**Steal:** the catalog of expected-power formulations (physics-only, ML-only, hybrid) — our twin (P2) is a hybrid, and this review is the citation map for that choice.

## 4.3 Liu et al. (2025) — cost-effective distributed-PV monitoring (read first for solar FD)

*"A methodological review of cost-effective data-driven fault detection for distributed PV"* (~18 citations, Energy & AI / Applied Energy family): https://www.sciencedirect.com/science/article/pii/S2666546825000199 (verify exact volume on page)

**Core method.** Case-based measurement approaches for monitoring distributed PV fleets under sensor and budget constraints — which signals to require, which to infer, and what detection quality each budget tier buys.

**Steal:** our product targets operators who won't retrofit Class-A pyranometers everywhere; this review is the evidence that infer-and-fallback monitoring design is a real, cited discipline. Shapes the demo's "works even with sparse sensors" claim.

## 4.4 Miraftabzadeh et al. (2025) — autoencoders for sparse-metadata PV

*"Data anomaly detection in PV power time-series by deep autoencoder"* (~21 citations, open, Energy/Applied Sciences family): https://www.mdpi.com/1996-1073/18/4/868 (verify)

**Core method.** Deep autoencoder trained on PV production time series explicitly designed for settings with **insufficient data/metadata** — reconstruction error as the anomaly score.

**Steal:** the honest-deployment recipe: when a site has little metadata, train the AE on power/temperature series alone. Matches exactly how we'll start on a new customer site. Also the architecture we replicate for the inverter-level demo (P4).

## 4.5 Hu et al. (2023) — LSTM + autoencoder for inverters

*"PV inverter anomaly detection combining LSTM and deep autoencoder"* (IOP / Journal of Physics): https://iopscience.iop.org/article/10.1088/1742-6596/2493/1/012008 (verify)

**Core method.** Sequence-aware AE: LSTM encodes temporal dependencies of inverter channels; reconstruction error flags inverters drifting from their own temporal signature.

**Steal:** the sequence-AE variant for inverter channels where daily cycles must be learned, not averaged away. Complements the static regression twin: regression catches "below expectation today," sequence-AE catches "shape of the day has changed."

## 4.6 Pereira & Silva (2018) — variational recurrent AE (cross-domain landmark)

*"Unsupervised anomaly detection in energy time series"* (IEEE, ~228 citations). See 3.9. Listed again here because the solar twin's encoder candidate comes from this line of work — probabilistic latents make retrieval thresholds principled (P8).

## 4.7 Smestad et al. (2020) — the physics of soiling

*"Modelling photovoltaic soiling losses through optical characterization."* Scientific Reports 10 (~160 citations, open): https://www.nature.com/articles/s41598-019-56704-2

**Core method.** A physics framework linking deposited particulate mass/composition → optical transmittance → soiling ratio; global measurement campaign across sites.

**Steal:** the causal chain dust-load → transmittance → SR gives our dust engine (P7) its physics backbone: CAMS dust optical depth (Section 2.3) is a *proxy for particulate load*, and Smestad's framework is the citation that load→loss is physical, not merely correlational.

## 4.8 Redondo et al. (2024) — soiling-model bake-off

*"Review and comparison of methods for soiling modeling"* (MDPI, journal version 2024; earlier UPM open report 2019): https://www.mdpi.com/1996-1073/17/4/798 (verify volume)

**Core method.** Head-to-head comparison of soiling-ratio models (Kimber, site-adaptation, decay+clean models) on real data.

**Steal:** pick our soiling model *from evidence*: Kimber for simplicity/edge, SRM (RdTools stochastic-rate) for data-driven sites, hybrid where dust forecasts exist. The review is the citation for whichever we choose.

## 4.9 Tsanakas et al. (2025) — hybrid data-driven soiling prediction

*"Hybrid data-driven modelling and prediction of soiling losses"* (~7 citations, Wiley Progress in PV): https://onlinelibrary.wiley.com/doi/10.1002/pip.3837 (verify)

**Core method.** Weather-driven ML soiling-loss forecasting at plant level — accumulating-rate models conditioned on weather regime.

**Steal:** the soiling *forecaster* pattern: our P7 engine predicts next-week soiling loss from dust forecast + rain, feeding the cleaning optimizer (P11). This paper is the precedent that prediction (vs. detection) of soiling is current research practice.

## 4.10 Matar (2024) — cleaning-schedule optimization

*"Optimal scheduling of PV panels cleaning and policy"* (MDPI Energies, ~14 citations): https://www.mdpi.com/1996-1073/17/2/375 (verify)

**Core method.** Simulation + optimization of cleaning schedules balancing cleaning cost vs. recovered production, with policy implications.

**Steal:** the cleaning-cost-vs-recovered-energy objective function is the exact math behind our "clean before or after the dust storm" recommendation (P11). Combined with Kimber (4.12) and CAMS forecasts (2.3), this completes the weather-aware cleaning story.

## 4.11 Kimber et al. (2006) + Deceglie SRM — the two canonical soiling estimators

- **Kimber soiling model** — linear accumulation during dry periods, reset by rain events above a cleaning threshold, with an economic layer for wash scheduling. Implemented in **pvlib**: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.soiling.kimber.html; documented at Sandia PVPMC: https://pvpmc.sandia.gov/modeling-steps/2-dc-module-iv/soiling-2/kimber-soiling-model/
- **Deceglie et al. (2018), stochastic rate & condensation cleaning (SRM)** — soiling-rate estimation directly from production data; implemented in **RdTools**: https://rdtools.readthedocs.io (paper: *"An open source Python library for PV degradation analysis"*, ~26 citations: https://www.osti.gov/biblio/1490278)

**Steal:** both are one-call functions in libraries we already use. Kimber = forecastable prior; SRM = measured truth from the plant's own data. Our dust engine runs both and reconciles — a genuinely nice methodological touch for the appendix.

## 4.12 Jordan, Deline, Deceglie et al. (2023) — clear-sky filtering done right

*"Hitchhiker's guide to analyzingimet…"* — more precisely: Jordan et al., *"Trends in clear-sky filter performance"* / clear-sky detection benchmarks (Applied Energy / IEEE PVSC lineage, ~16 citations): https://www.sciencedirect.com/science/article/abs/pii/S0038092X23000630 (verify) — benchmarks Reno-style, RdTools-default, and Ellis clear-sky filters with moving-window GHI congruence.

**Steal:** clear-sky filtering is the *precondition* for honest degradation analysis; the benchmark tells us which filter to ship. Combined with RdTools year-on-year methodology, this is the degradation branch of the twin (slow drift vs. sudden fault discrimination).

## 4.13 Fleet degradation baselines — Lindig, Malvoni, India numbers

- **Lindig et al. (2021)** — *"Performance analysis and degradation of a large fleet of PV systems"* (Statistical Clear-Sky Fitting, ~56 citations, open via TU/e): https://research.tue.nl/en/publications/performance-analysis-and-degradation-of-a-large-fleet-of-photovolt — SCSF doubles as outlier filter + fleet-level performance-ratio baselining (P5).
- **Malvoni et al. (2020)** — measured degradation **0.27–0.5%/yr** across large plants over ~50 months (~162 citations): https://www.sciencedirect.com/science/article/abs/pii/S0378775320304021 (verify) — realistic priors so thresholds drift with age.
- **India:** Navothna et al. (2022, Frontiers, ~52 citations) measured −0.6 to −5%/yr at a large Indian plant: https://www.frontiersin.org/articles/10.3389/fenrg.2022.863656/full (verify); Rajput & Sudhakar long-term India study ~1.9%/yr after 22 years: https://academic.oup.com/ijlct/article/8/3/279/6365970 (verify). **NREL fleet median ≈ 0.5%/yr** (PV Fleet Initiative).

**Steal:** degradation priors feed the twin's expected-PR drift line; the India-specific numbers are pitch ammunition — "Indian field degradation is often worse than the datasheet assumption; we measure it continuously."

## 4.14 Vision-based and I-V-curve confirmation (the evidence layer)

- **Masita et al. (2025)** — *"Deep learning in defect detection of PV modules: a review"* (~90 citations): https://www.sciencedirect.com/science/article/pii/S2949908925000152 (verify) — CNN detection/classification of hotspots, cracks, PID in IR/EL imagery.
- **Jumaboev et al. (2022)** — UAV thermal-image plant fault detection (MDPI, ~94 citations): https://www.mdpi.com/2072-4292/14/18/4526 (verify)
- **Lin et al. (2024)** — deep-learning diagnosis on string **I-V curves** (MDPI): https://www.mdpi.com/1996-1073/17/2/342 (verify)
- **Hopwood et al. (2022)** — physics-based **fully synthetic I-V curve** generation (~23 citations): https://www.osti.gov/biblio/1879207 (verify) — synthetic fault augmentation.
- **Memon et al. (2022)** — robust ML classification of the four most frequent PV fault classes (OC/SC/shading/degradation, ~62 citations, open): https://pmc.ncbi.nlm.nih.gov/articles/PMC9144319/

**Steal:** these are the *confirmation modalities*. SCADA says "string underperforming"; the fault dictionary says the candidate causes; if the site has drone/thermal or I-V tracer assets, they confirm. Even in a hackathon demo where we can't fly drones, mentioning this evidence hierarchy (telemetry → model → confirmatory inspection) mirrors how the agent's recommendation names the *confirming action* the technician should take (P10/P12).

## 4.15 Solar digital twins — architecture references

- **Digital-PV (2024)** — digital-twin platform for autonomous aerial PV inspection (Energy Conversion & Management, open): https://www.sciencedirect.com/science/article/pii/S019689042400904X (verify) — twin that simulates plant configurations for inspection planning.
- *"Photovoltaic Digital Twins: Mathematical Modeling vs. Neural"* (2025, MDPI Applied Sciences): https://www.mdpi.com/2076-3417/15/16/8883 — compares 4 expected-power model classes empirically.

**Steal:** the twin-architecture vocabulary (model layer, state layer, scenario layer) and the empirical comparison for choosing our expected-power formulation with evidence rather than taste.

---

# 5. Case-Based Reasoning, Agents & LLMs in Maintenance

## 5.1 Case-based predictive maintenance — the intellectual home of Pillar P8

Our "historical failure-trajectory memory" is **case-based reasoning (CBR)** applied to telemetry: store past episodes (trajectory + context + diagnosis + outcome), retrieve similar current episodes, adapt the recommendation. Landmarks to cite:

- Aamodt & Plaza (1994) — *"Case-based reasoning: foundational issues"* — the 4R cycle (Retrieve, Reuse, Revise, Retain) that maps 1:1 onto our loop: retrieve similar trajectories (Needle tool), reuse as evidence, revise via technician feedback (P12), retain the resolved case back into memory.
- Modern TS-CBR: similarity search over multivariate windows — implemented in practice with **STUMPY matrix-profile motifs/discords** (Section 8) or latent-space retrieval (VRAE, 3.9). The honest architecture: embed each 72-hour multivariate window → kNN search in the case library → return top-k trajectories with their ground-truth outcomes.

**Steal:** the 4R vocabulary gives the demo's story scientific structure: "the agent doesn't just flag an anomaly; it retrieves the three most similar historical episodes, two of which ended in bearing replacement." That sentence is CBR, and judges respect it.

## 5.2 LLMs/tool-calling agents over industrial telemetry

- **Tan et al. (2025)** — LLMs for gearbox failure prediction (see 3.13) — precedent.
- **Berkeley Function-Calling Leaderboard (BFCL)** — Patil et al., ICML 2025 (~685 citations): https://gorilla.cs.berkeley.edu — the standard eval for tool-calling models (serial/parallel calls, AST matching, multi-turn). Use it to frame *why* a purpose-built 45M tool-caller is credible: Needle 2's own model card positions it against small models on function-calling suites (Section 7).
- Needle 2 paper: **arXiv:2607.18363** — *"Needle 2: A 45M-Parameter Foundation Tool-Calling Model for Tiny Devices"* (Ndubuaku, Mosoyan, Mroz, Cylich, Kumar, Sandhu, Shemet, Lee — Cactus Compute, 2026): https://arxiv.org/abs/2607.18363. Full deep dive in Section 7.

**Steal:** the agent story must be *tool-grounded, not chat-grounded*: the agent's competence is judged on whether it calls the right tools with valid arguments and escalates when confidence is low — BFCL's evaluation philosophy. That is also exactly how we demo it.

## 5.3 RAG for industrial maintenance corpora

Local RAG over manuals/SOPs/incident reports (P9) rests on standard components — embedding models, vector indexes, chunking — all covered with specific tools in Sections 7–8. The literature anchor worth citing: retrieval-augmented generation reduces hallucination by grounding generations in retrieved evidence (Lewis et al. 2020, NeurIPS, https://arxiv.org/abs/2005.11401), and domain-corpora RAG is now standard industrial practice. Our differentiator is *deployment posture*: the corpus and the index live on the plant's own hardware (privacy architecture, ideation report §6), which no cloud RAG vendor can claim.

---
# 6. Evaluation Science — How to Prove the System Works (Without Fooling Ourselves)

This section exists because the fastest way to lose a technical judge is to report inflated anomaly-detection numbers. Everything here is distilled into our protocol in Section 13.

## 6.1 The CARE score (Gück et al., 2024) — our primary metric

*"CARE to Compare: A real-world dataset for anomaly detection in wind turbine data."* MDPI **Data** 9(12):138 (2024): https://www.mdpi.com/2306-5729/9/12/138 — dataset: https://zenodo.org/records/15846963

The paper defines a score for *early* anomaly detection with four components:

- **C — Coverage:** what fraction of the labeled pre-failure prediction window is detected? (A detector that fires for one day out of a 40-day degradation ramp barely helps.)
- **A — Accuracy:** the classification quality of detections *within the event window* (precision/weighted combinations internal to the event).
- **R — Reliability:** the false-alarm side — detections on healthy periods penalize the score, directly encoding the operator's trust cost.
- **E — Earliness:** how far in advance of failure the first true alarm lands — the metric that connects detection to the P-F economics of Section 1.2.

**Why we adopt it wholesale:** it is the metric the dataset's authors defined for exactly this task, it is conservative (penalizes both misses and crying-wolf), and using it makes our results directly comparable to every other team/paper that evaluates on CARE to Compare. Report CARE components individually + the composite; pair with a detection-latency histogram (days-before-failure across the 45 labeled events).

## 6.2 The point-adjust critique — why we will NOT use point-adjust F1

- **Kim, Cho & Kim (2022, AAAI)** — *"Towards a Rigorous Evaluation of Time-Series Anomaly Detection"*: https://aaai.org/papers/2209.05292 — shows that under the widely-used **point-adjust (PA)** protocol, *random noise can score near-perfectly*, because hitting one point in an anomalous segment credits the whole segment.
- **Sørbø & Jensen (2024)** — *"A taxonomy of evaluation metrics for anomaly detection in time series"* (~99 citations, Springer): https://link.springer.com/chapter/10.1007/978-3-031-24894-0_8 (verify chapter) — organizes the metric zoo (event-wise, range-based, time-series aware) and when each misleads.

**Steal:** avoid PA-based F1 entirely; report **range-aware metrics** (range-based precision/recall, or VUS-PR if we adopt the TimeEval stack) and the CARE components. One line in the appendix: "point-adjust is known to overestimate performance (Kim et al., AAAI 2022); we therefore report range-aware and CARE metrics." That sentence inoculates the Q&A.

## 6.3 Protocol rules from the zero-shot / threshold-collapse literature

- **Banerjee et al.** — *"Towards zero-shot multivariate time-series anomaly detection"* (OpenReview): https://openreview.net/forum?id=... (Gorilla-adjacent group; search title) — demonstrates that real-world performance collapses when two common cheats are removed: tuning thresholds on test data and post-hoc threshold learning.
- **Mejri et al. (2024)** — *"Unsupervised anomaly detection in time-series: an extensive evaluation"* (~102 citations): https://www.sciencedirect.com/science/article/pii/S2666546824000149 (verify) — reproducible benchmark of recent unsupervised TSAD; honest baseline expectations (most methods cluster around modest performance on hard real data).

**Steal:** (1) thresholds are fixed on a *validation period that ends before the evaluation window begins*; (2) report a threshold-agnostic curve (PR curve over score) *plus* one fixed operating point chosen by stated policy (e.g., "≤1 false alarm per turbine per month"); (3) expect modest absolute numbers and say so — realism reads as competence.

## 6.4 TimeEval — reuse, don't hand-roll

**TimeEval** (HPI) — distributed benchmarking toolkit for time-series anomaly detection with threshold-agnostic, area-based metrics and dozens of algorithms: https://timeeval.github.io (code on GitHub). If we need to compare our detector against standard baselines (IsolationForest, LOF, MatrixProfile, etc.) in a defensible harness, TimeEval's metric implementations are the shortcut.

## 6.5 NAB — the earliness-weighted philosophy

**Numenta Anomaly Benchmark** (Ahmad, Lavin, Purdy & Agha, 2015): labeled real-time streams; the scoring function gives *higher credit to earlier true detections within a window* and punishes false positives with a decay — the streaming-era ancestor of CARE's Earliness component: https://github.com/numenta/NAB (paper: https://arxiv.org/abs/1510.03375). Citation support for "we weight earliness because operators value time-to-act, not F1."

## 6.6 PA%K — don't let segments hide misses

The **PA%K** segment metric (popularized via the *DL for time-series anomaly detection* repo family, e.g. https://github.com/TheDatumOrg/TSB-AD and related) reports whether only K% of an anomalous segment was detected — protecting against "one lucky point credits the event." If we report event-wise results, include PA%K or a per-segment coverage figure alongside.

## 6.7 Leakage — the silent killer

- **Yang et al. (2024)** — *"Research on information leakage in time series prediction"* (~54 citations, PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC10963xxx (search title) — formalizes leakage channels: overlapping train/test windows, normalization fitted on full series, feature lags that peek forward, event-window bleed.
- **Walk-forward validation practice** — rolling-origin evaluation with strict time order, per-asset grouping, no shuffling: practitioner canon (https://machinelearningmastery.com/...; IBM; stats.stackexchange threads).

**Steal:** our CV protocol (Section 13) is built directly from these: splits are time-ordered, grouped per asset (no turbine appears in both train and test with overlapping dates), scalers fit on train only, and the labeled pre-failure window of one event never straddles a split boundary.

## 6.8 Imbalanced-metrics honesty

- **Richardson et al. (2024)** — *"The ROC curve accurately summarizes…"* (~310 citations, PMC): argues ROC-AUC remains interpretable under imbalance while **PR curves cannot be disentangled from prevalence** — https://pmc.ncbi.nlm.nih.gov/articles/PMC10881522/ (verify).
- **Imani et al. (2026)** — comparison of ROC-AUC / PR-AUC / F2 / **MCC** under extreme imbalance (MDPI): https://www.mdpi.com/1099-4300/28/1/42 (verify).
- **Saito & Rehmsmeier (2015)** — *"The precision-recall plot is more informative than the ROC plot"* (PLOS ONE): https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432 — the classic PR-side citation.

**Steal:** report a small honest battery: **PR-AUC with its prevalence baseline stated** (e.g., "events are 4.7% of days; prevalence-AUPRC = 0.047"), **MCC**, and **recall @ alert budget** (e.g., recall when allowing 2 alerts/turbine/month). This is exactly how an operations team thinks about alerting, which is the point.

## 6.9 P-F interval economics — the bridge from metrics to money

Practitioner canon (with healthy skepticism about the ½–⅓ rule): P-F curve/interval primers from the maintenance-engineering world — e.g., Prometheus Group https://www.prometheusgroup.com/resources/the-p-f-curve-explained, Fluke https://www.fluke.com/en-us/learn/blog/condition-monitoring/what-is-the-p-f-curve, and critiques in reliability journals. The operational translation we adopt: **inspection interval ≤ ⅓ × P-F interval** becomes, per detected case, an "inspect within X hours" recommendation where X is a fraction of the modeled P-F window for that failure mode — which is what makes "72 hours" a derived number rather than a slogan (P11).

## 6.10 Fleet-scale alerting — the open challenge we design for

*"Open challenges in time-series anomaly detection"* (2025, arXiv) argues per-series alerting breaks down at fleet scale (thousands of series → alert storms); the answer is **aggregation + ranking** — exactly our priority-queue design (P11/P12): detectors emit scores; the economic engine ranks; humans see one queue. Cite it as evidence the architecture choice is deliberate, not incidental.

---

# 7. Needle 2 — Deep Dive, Integration Blueprint, and Honest Limits

## 7.1 Verified facts (from the official model card, checked September 2026)

Model card: https://huggingface.co/Cactus-Compute/needle2 · Repo (source + engine + training): https://github.com/cactus-compute/needle · Paper: arXiv:2607.18363 · License: **Apache-2.0** · 296 likes / ~55k downloads/month at time of writing.

**What it is.** Needle 2 is an open **45M-parameter** model for **tool calling, device use, and structured extraction**. The whole model is a **single 14 MB binary**; a full session runs in **~28 MB of RAM**. It is built on Cactus's **Simple Attention Network** (SAN) recipe — Hadamard-MLP replacing the FFN, GQA attention, *engram* hashed n-gram key-value memory, multi-lane hyper-connections — compressed to **CQ2-bit** ("Cactus Quants") and baked into its own engine. It trades wins against other small function-calling models (FunctionGemma 270M, LFM2.5 230M, Apple FM) at 5–70× smaller, running at 2-bit vs. their fp16.

**Measured speeds (from the card):** ~**500 tok/s decode on a Raspberry Pi 5**; 400–1,500 tok/s on VR devices (Quest 3S, Vision Pro); 300–700 tok/s on sub-$200 Android phones; reaches microcontrollers — the card cites ESP32-P4, community reports ~11 MB on ESP32-S3. Every response JSON includes `prefill_tps`, `decode_tps`, `peak_ram_mb` — the model *reports its own telemetry*, a nice touch for our demo UI.

**Portability:** self-contained (no runtime, no downloads, no network after deployment); ARM64, x86-64, ARMv7, RISC-V, WebAssembly; Apple/Windows/Linux/Android/RPi; plus a **WASI Preview 2 component** (`cactus:needle/engine@2.0.0`) and a native C API (`needle_load/init/complete`).

**The behavior contract (this is the important part for us):**

1. **Text in → structured JSON out.** Tool calls are constrained by a **byte-level grammar compiled from our declared schemas** — the model *cannot emit malformed JSON*. There is no separate "JSON mode"; conformance is structural.
2. **Confidence-gated.** Every response carries a calibrated confidence from a learned head; per the card it is the **minimum of (calibrated post-hoc head score, decoding probability of the call tokens)**. The stated contract: pick a threshold, act at/above it, **escalate below it** — the failure mode is escalation, not wrong execution.
3. **Tool retrieval.** Declare a large catalogue; a built-in contrastive head embeds tool schemas once at init and renders **only the top 5 tools per turn** into the context; the grammar is rebuilt over that subset — an unselected tool is *unreachable*, not merely unlikely. `tool_index_path="tools.idx"` persists embeddings across runs.
4. **Bounded memory.** A **256-token sliding window with tools pinned as KV sinks** — total memory stays ~28 MB regardless of conversation length. (This is also the main limitation; see 7.4.)
5. **Off-topic refusal.** A request no declared tool can serve returns the **empty call `[]`** — there is no free-text fallback (except an explicit final `"type":"respond"` step after tool results). The system turn carries *facts, not instructions* (`date:`, `device:`, `battery:` …).
6. **Argument discipline.** Arguments contain only values evidenced in the input; optional fields without evidence are *omitted, not guessed*; `reasoning` is a short derivation of each argument from its source span.
7. **Extraction.** The same exchange powers structured extraction (`needle.extract(text, PydanticModel)`) — declare the record schema as the only tool and schema conformance is guaranteed.
8. **Fine-tuning.** Open and trainable end-to-end; fine-tune on our own tools/domain and export to `.cact` shipped like the base model.
9. **Python UX.** `pip install cactus-needle`; decorate functions with `@needle.tool` (docstring = tool description; Google-style `Args:` block = per-parameter docs; `Literal` = fixed choices; `needle.Field` on `Annotated` compiles ranges/patterns/lengths into the decode grammar); `agent.run()` auto-executes the loop; `agent.complete()` gives the manual loop for tool results; response JSON includes `function_calls[].arguments`, `reasoning`, `confidence`, TPS/RAM telemetry.

## 7.2 Why this is the right agent for the plant edge

The ideation report's principle — *numerical ML predicts; the agent investigates; RAG supplies evidence; economics prioritizes; the technician decides* — maps onto Needle 2's actual mechanics:

- **Deterministic tool discipline:** plant recommendations are safety-adjacent; a 45M model that *structurally cannot* emit malformed calls or invent argument values (grammar-constrained) is a far safer actuator-of-queries than a free-text LLM with a JSON prayer. The empty-call refusal gives us a clean "I cannot act on this" state instead of hallucinated analysis.
- **Confidence gating = human-in-the-loop by construction:** the card's own contract (act above threshold, escalate below) is literally our P12 boundary. We set the threshold per action class: read-only queries (fetch residuals, retrieve cases) can act at low confidence; anything that becomes a work order or writes back requires high confidence or explicit human confirmation.
- **28 MB RAM / 14 MB binary:** the agent coexists with the anomaly models, vector DB, and historian *on the same edge box* — the whole "local AI operating layer" fits on one device. It also means the privacy claim is concrete: there is no second cloud service that could receive the farm's data, because the reasoning engine is a 14 MB file.
- **Tool retrieval:** our tool registry (below) will exceed five tools; the retrieval head keeps the context within budget automatically — we never hand-roll tool selection.
- **Apache-2.0 + fine-tunable:** we can fine-tune on domain tool-calling traces and ship it; no licensing landmine for the startup story.

## 7.3 Integration blueprint — the tool registry (maps to ideation §28–29)

Needle reads tool descriptions to decide what to call and how to fill arguments — "describing them well is the whole game." Our registry, written as Python functions the agent may call (each documented with `Args:` blocks and `Literal` choices):

| # | Tool | Signature sketch | Returns | Pillar |
|---|---|---|---|---|
| 1 | `get_asset_evidence` | `asset_id: str, window: Literal["24h","72h","7d"]` | Residual z-scores per channel, expected vs. actual power, peer percentile, current operating state | P2, P4, P5 |
| 2 | `get_weather_context` | `asset_id: str, horizon: Literal["now","5d"]` | Irradiance/cloud history, temperature, dust forecast (DOD), rain probability, curtailment flag | P6, P7 |
| 3 | `get_soiling_estimate` | `asset_id: str` | Soiling ratio now, accumulation rate, Kimber/SRM reconciliation, days-to-threshold | P7 |
| 4 | `search_similar_cases` | `evidence_summary: str, k: int (1–5)` | Top-k historical failure trajectories with outcomes + component labels | P8 |
| 5 | `search_knowledge` | `query: str, corpus: Literal["manuals","sops","incidents"]` | Local-RAG passages with sources | P9 |
| 6 | `estimate_economic_impact` | `asset_id: str, scenario: Literal["do_nothing","repair_now","defer_7d"]` | Expected energy loss, revenue-at-risk (₹), probability-weighted, assumptions listed | P11 |
| 7 | `create_inspection_ticket` | `asset_id: str, urgency: Literal["routine","priority","urgent"], rationale: str` | Ticket draft **+ requires confirmation**; never dispatches autonomously | P10→P12 |

**Session flow for the demo:** system facts (`date`, `device: edge-gateway`, `location: site-id`) → compact evidence packet assembled by the pipeline (precomputed numbers — see 7.4) → agent orchestrates: `get_asset_evidence` → `get_weather_context` → `search_similar_cases` → `search_knowledge` → `estimate_economic_impact` → `create_inspection_ticket`. Because `complete()` returns the raw call, our harness executes each tool and feeds results back; the final turn is `"type":"respond"` — the agent's evidence-first summary.

**Threshold policy to demo live:** show the same investigation with confidence 0.94 (proceeds, produces recommendation) vs. a deliberately ambiguous case where confidence lands below threshold and the agent *escalates to human review* — the failure mode is escalation, not wrong execution. That 30-second sequence is the most judge-impressive moment in the entire demo, because it shows the safety story is architectural, not aspirational.

## 7.4 Honest limits — and how our design absorbs them

1. **256-token sliding window.** The agent holds one turn's task, not long histories. *Absorption:* our pipeline precomputes the evidence packet; each turn is a compact question. Multi-step loops use `complete()` where each step is small. (Also why "numerical ML predicts, agent investigates" is the right division.)
2. **No arithmetic reliability at 45M/2-bit.** Never ask it to compute revenue-at-risk. *Absorption:* `estimate_economic_impact` does the math in Python; the agent only *calls* it with evidenced parameters and relays the result. The card's own argument discipline (values only from input evidence) supports this.
3. **No free-text fallback.** Off-topic → empty call. *Absorption:* all operator-facing prose is assembled by our app layer from structured evidence + the agent's `reasoning` field; the agent is a controller, not a chatbot. (For a richer conversational layer, see the backup stack in 7.5 — a bigger local LLM can present, while Needle 2 decides.)
4. **Tool-description sensitivity.** The card: "describing them well is the whole game." *Absorption:* tool descriptions get version-controlled, and we fine-tune on our traces (7.1 #8) as the corpus grows.
5. **First-run engine acquisition.** The Python package may download the platform engine on first import (the model itself is baked in / self-contained after deployment). *Absorption:* deployment note only — for the offline claim, say "after deployment, no network required," exactly as the ideation report already words it.
6. **Tiny-model reasoning depth.** For genuinely open-ended diagnostics, 45M parameters are a controller, not an analyst. *Absorption:* that is the architecture — analysts are the ML models + retrieval; the agent orchestrates. If judges push, the honest answer is: "we deliberately chose the smallest tool-caller that meets the contract, because it runs in 28 MB inside the plant; a 4B local LLM is the optional escalation path (7.5), and the confidence gate is what chooses between them."

## 7.5 Backup / escalation stacks (in case judges probe, or Needle 2 hits a wall)

| Layer | Primary choice | Backup / escalation | Notes |
|---|---|---|---|
| Tool-calling agent | **Needle 2** (45M, 14 MB, 28 MB RAM) | **Qwen3 4B** via Ollama (community default for small tool-calling), or Qwen3 1.7B/0.6B as draft model | Ollama native tool-calling API: https://ollama.com / https://docs.ollama.com; models: https://ollama.com/library/qwen3 |
| Runtime | Built-in engine (single binary) | **llama.cpp** with GGUF, **Q4_K_M** quant as default quality/size balance | https://github.com/ggml-org/llama.cpp; Qwen official quantization guidance: https://qwen.readthedocs.io |
| Embeddings | **nomic-embed-text** (137M, 274 MB, CPU-comfortable; most-pulled Ollama embedding model) | **bge-small-en/bge-m3** (multilingual, strong); ⚠️ int8-quantized embeddings shift vectors — re-index if you quantize | https://ollama.com/library/nomic-embed-text; BGE: https://huggingface.co/BAAI |
| Vector store | **sqlite-vec** (vector search inside SQLite — perfect edge/no-cloud fit) | Chroma (easiest), FAISS (raw speed) | https://github.com/asg017/sqlite-vec; comparison: https://risingwave.com/blog/chroma-db-vs-pinecone-vs-faiss-vector-database-showdown/ |
| Structured-output hardening | Byte-level grammar (built into Needle 2) | **Outlines** for bigger local models | https://github.com/dottxt-ai/outlines |
| Eval of the agent layer | Tool-call success rate on scripted investigations + confidence-calibration curve | **BFCL** methodology for function-calling quality | https://gorilla.cs.berkeley.edu |

## 7.6 Needle 2 judge Q&A (pre-armed)

- **"Why a 45M model — isn't that too small?"** → The agent's job is bounded: choose tools, fill evidenced arguments, relay results, escalate on low confidence. That is a tool-calling task with a strict grammar — exactly what Needle 2 is trained for (and what BFCL measures). The heavy lifting (expectation modeling, risk, economics) is done by dedicated models and Python tools. This division is the architecture, not a compromise. [model card + arXiv:2607.18363]
- **"How do you know it won't hallucinate a maintenance order?"** → Grammar-constrained calls (cannot emit invalid arguments), evidence-only argument discipline, confidence gating with escalation, and the ticket tool requires human confirmation. Failure mode is escalation, not wrong execution. [card, Behaviour + Confidence sections]
- **"What if it's offline?"** → Fully offline after deployment: 14 MB binary, no network, no runtime. Weather features come from cached forecasts; freshness degrades gracefully and is labeled. [card, Self-contained]
- **"Why not just call GPT?"** → Section 5 of the ideation report: longitudinal SCADA + failure history + production + configuration is commercially sensitive; the whole USP is *AI on proprietary operational data without a third-party cloud*. Also 28 MB vs. a cloud dependency at a rural plant — reliability is a feature.
- **"How is this different from an MCP agent with a big model?"** → Same idea, radically different deployment envelope (28 MB RAM, µC-capable, WASM-capable) and a stricter contract (grammar + confidence + refusal). We can *escalate* to a 4B local model when confidence is low — the architecture has a growth path.

---
# 8. The Software Stack — Layer by Layer

The stack is deliberately boring: proven, open-source, CPU-friendly, and runnable on a laptop for the hackathon and on an edge gateway in production. Each layer lists the tool, what it does, and its pillar.

## 8.1 Physics & expectation modeling (P2)

| Tool | Use | Link |
|---|---|---|
| **pvlib-python** (Sandia) | Solar position, clear-sky irradiance (Ineichen, Haurwitz, Reno), cell-temperature models (SAPM, Faiman), DC/AC chains, **Kimber soiling** | https://pvlib-python.readthedocs.io · origin: https://pvpmc.sandia.gov · `pvlib.iotools` readers for many public formats |
| **RdTools** (NREL) | Year-on-year degradation, **stochastic-rate & condensation soiling (SRM)**, clear-sky filtering pipeline | https://rdtools.readthedocs.io · paper: https://www.osti.gov/biblio/1490278 |
| **windpowerlib** (oemof) | Turbine power-curve models, density corrections, wind-farm feed-in aggregation — the wind twin's expected-power kernel | https://windpowerlib.readthedocs.io · https://github.com/wind-python/windpowerlib |
| **OpenOA** (NREL) | Production-operational analysis framework (IEA Wind-aligned): power-curve filtering, long-term adjustments, availability MC | https://openoa.readthedocs.io · https://github.com/NREL/OpenOA |

**The twin recipe.** Solar: pvlib clear-sky + site geometry → expected POA irradiance → cell temperature → DC model → AC clip → compare to measured; residuals normalized by irradiance band. Wind: IEC-binned power curve (IEC 61400-12-1) or GBM/GP on (wind speed, direction, density) → expected power and component temperatures; residuals conditioned on operating state. Both twins output per-channel **residual z-scores on a fixed cadence** — the currency the rest of the system trades in.

## 8.2 Anomaly detection & modeling (P4)

| Tool | Use | Link |
|---|---|---|
| **PyOD** | 45+ detectors (IsolationForest, LOF, KNN, OCSVM, autoencoder variants) behind one API; tabular + time-series (PyOD 2) | https://github.com/yzhao062/pyod · docs: https://pyod.readthedocs.io |
| **STUMPY** | Matrix Profile: motifs (recurring signatures → the case library) and **discords** (novel anomalies) with exact anytime algorithms | https://stumpy.readthedocs.io · UCR Matrix Profile page: https://www.cs.ucr.edu/~eamonn/MatrixProfile.html |
| **tsfresh** | Automated extraction of hundreds of time-series features (FRESH) feeding classifiers | https://tsfresh.readthedocs.io · https://github.com/blue-yonder/tsfresh |
| **ruptures** | Offline changepoint detection/segmentation — step changes (string outage, wash event, curtailment onset, retuning) | https://centre-borelli.github.io/ruptures-desc/ · paper: https://arxiv.org/abs/1801.00826 |
| **Merlion** (Salesforce) | Unified forecasting + anomaly detection + changepoint (JMLR 2023) — calibrated thresholds from forecast distributions | https://github.com/salesforce/Merlion |
| **darts** (Unit8) | `darts.ad` scorers/detectors/aggregators — quick ensembles of anomaly scorers | https://unit8co.github.io/darts/ |
| **scikit-learn / XGBoost** | The regression twins (GBM baselines per Chesterman 2023), residual models, peer-ranking models | standard |
| **GPyTorch (sparse GP)** | GP power-curve twin with calibrated variance (Pandit 2018 pattern) | https://gpytorch.ai |

**Recommended model roster for the MVP (in build order):** (1) pvlib/windpowerlib physics expected-value + residual z-scores — always on, interpretable; (2) GBM regression twin per channel — captures what physics misses; (3) PyOD IsolationForest/LOF on residual vectors — multivariate outlier layer; (4) STUMPY discord scan on key channels — novel-event radar; (5) ruptures — segmentation for step changes; (6) GP twin on power only where uncertainty-driven alerting matters. That's six tools, zero deep learning required for a defensible MVP — deep AE (Section 4.4/4.5) is the stretch goal.

## 8.3 Ingestion, storage, serving (P3)

| Layer | Primary | Notes |
|---|---|---|
| Protocol simulation | **pymodbus** (Modbus TCP/RTU client+server) — simulate inverters/PLCs exposing registers; the demo's "SCADA" | https://github.com/pymodbus-dev/pymodbus |
| Telemetry bus | **MQTT** with **paho-mqtt 2.x** — topics `site/asset/channel`, QoS 1; brokers: Mosquitto | https://pypi.org/project/paho-mqtt/ · https://mosquitto.org |
| Historian | **TimescaleDB** (Postgres extension) — SQL joins across telemetry + metadata + RAG bookkeeping in one DB; hypertables for 10-min data | https://www.tigerdata.com/docs (Timescale) |
| App/API | **FastAPI** — evidence endpoints the agent's tools call; WebSocket for dashboard | https://fastapi.tiangolo.com |
| Dashboards | **Grafana** — fleet heatmap, priority queue, asset detail; panel per pillar; alarm-managed alerting | https://grafana.com · renewable case study: SYSO via Grafana |
| Alternative SCADA-ish stack | **ThingsBoard** if a turnkey IoT dashboard is preferred for the demo | https://thingsboard.io |

**Why TimescaleDB over InfluxDB for us:** one Postgres instance carries telemetry, asset metadata, maintenance cases, and the RAG metadata table — fewer moving parts at the edge, and SQL is the lingua franca of the O&M world we're selling to. (Vendor comparison: https://www.tigerdata.com/blog/timescaledb-vs-influxdb-for-time-series-data-timescale-influx-sql-nosql-36489299877; the honest answer is both work — Timescale keeps our edge footprint smaller.)

## 8.4 Local AI layer (P8, P9, P10)

| Component | Primary | Link |
|---|---|---|
| Agent | **Needle 2** (`pip install cactus-needle`) | https://huggingface.co/Cactus-Compute/needle2 · https://github.com/cactus-compute/needle |
| Vector store | **sqlite-vec** (SQLite extension; embedded, zero-ops) | https://github.com/asg017/sqlite-vec |
| Embeddings | **nomic-embed-text** via Ollama (274 MB, CPU) or **bge-small/bge-m3** via sentence-transformers | https://ollama.com/library/nomic-embed-text · https://www.sbert.net |
| Optional bigger local LLM (escalation path / conversational layer) | **Qwen3 4B / 8B** via **Ollama** or **llama.cpp** (Q4_K_M GGUF) | https://ollama.com/library/qwen3 · https://github.com/ggml-org/llama.cpp |
| Structured output for the bigger model | **Outlines** (grammar-constrained decoding) | https://github.com/dottxt-ai/outlines |
| Chunking/pipeline glue | LlamaIndex or LangChain *serving the local index only* (no hosted APIs in the privacy path) | https://docs.llamaindex.ai · https://python.langchain.com |

**RAG corpus design (P9), concretized:** four collections — `manuals` (OEM docs per asset model), `sops` (site procedures), `incidents` (past work orders + outcomes), `cases` (the trajectory library — see P8). Chunk by section with metadata (asset_type, component, doc_version); embed once; store in sqlite-vec with FTS5 alongside for hybrid keyword+vector retrieval (both run in-process). Every retrieval returns **source spans** — the agent quotes document + section, which the UI shows. This is how the "evidence-first output" of ideation §30 is actually built.

## 8.5 Synthetic & labeled data generation (P4, P14-demo)

| Need | Tool/method | Reference |
|---|---|---|
| Labeled PV outages | NREL synthetic PV datasets with injected string outages (methodology paper ~35 pp.) | Section 2.2.5 |
| Synthetic I-V curves | Hopwood physics-based generator | https://www.osti.gov/biblio/1879207 (verify) |
| General HIL fault injection methodology | Abboush & Schmidt (2024), hardware-in-the-loop fault injection for labeled data | https://www.mdpi.com/1424-8220/24/7/2316 (verify) |
| Our own replay+inject harness | Section 14 of this document (CARE/PVDAQ replay through MQTT with scripted fault profiles) | — |

---

# 9. Edge Hardware & Deployment

## 9.1 Device tiers

| Tier | Device | What runs on it | Evidence |
|---|---|---|---|
| **Primary edge box** | **NVIDIA Jetson Orin Nano Super 8 GB** ($249) — 67 INT8 TOPS (up from 40 via software update), 102 GB/s memory bandwidth, 25 W | Everything: historian, twins, detector fleet, sqlite-vec index, Needle 2, optional Qwen3-4B escalation layer | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super/ · NVIDIA's tested-model list: https://forums.developer.nvidia.com/t/ai-models-that-run-on-jetson-orin-nano-super-8gb/365412 · SmolHub tiny-LLM benchmark on Orin Nano Super (llama.cpp vs Ollama, power modes; 25 W ≈ +43% tok/s vs 15 W): https://www.smolhub.com |
| **Ultra-cheap / minimal tier** | **Raspberry Pi 5** (4–8 GB) | Needle 2 (**~500 tok/s decode per the model card**), embedding + sqlite-vec, lightweight detectors; small GGUFs at ~5–25 tok/s | model card (verified); Pi-5 LLM benchmarks: https://www.stratosphereips.org (≈5 tok/s typical for small quantized LLMs); bandwidth heuristic tok/s ≈ 17.1 GB/s ÷ model size (localaimaster) |
| **Microcontroller frontier** | ESP32-P4 / ESP32-S3 | Needle 2 alone (28 MB RAM budget; ~11 MB reported on ESP32-S3) | model card (verified) |

**Honest performance framing (judges ask):** INT8 TOPS ≠ LLM tokens/s — LLM decode is memory-bandwidth-bound (good explanation article: https://ericxliu.me/posts/benchmarking-llms-on-jetson-orin-nano). Quantized-LLM benchmarking across SBCs (25 models × RPi4/5/Orange Pi 5, arXiv Oct 2025) is the academic evidence base for our hardware selection. Design rule: keep models in RAM; SSD-offloaded inference works (~1.7 GB/s QLC; StorageReview DeepSeek-R1-70B-on-Orin test) but is a last resort.

## 9.2 The quantization ledger

- **Anomaly/embedding models → ONNX Runtime**, int8 dynamic quantization (S8S8+QDQ default balancing speed/accuracy): https://onnxruntime.ai/docs/performance/model-optimization/quantization.html · examples: https://github.com/microsoft/onnxruntime-inference-examples
- **⚠️ Embedding quantization caveat:** int8 embedding models produce materially different vectors than fp32 — if you quantize the embedder, **re-index the vector store**; never mix float and quantized indices (HF forum thread, Jul 2025). Plan: keep the embedder fp32 (274 MB is affordable) and quantize only the detector models.
- **LLM escalation layer:** GGUF Q4_K_M default (llama.cpp quantize tool guidance; Qwen's official docs recommend Q4_K_M/Q8_0 presets).

## 9.3 Field-package path (production horizon detail)

- Industrial gateways: fanless, −20…+70 °C operation; selection metric **TOPS-per-watt** in sealed enclosures (SECO guide: https://www.seco.com/.../choosing-edge-ai-hardware-for-wide-temperature-industrial-gateways-why-tops-per-watt-matters).
- Reference deployment pattern: **Siemens Industrial Edge AI Suite** (model asset manager, lifecycle ops) — the enterprise-grade version of what our MVP does with git + systemd: https://www.siemens.com/global/en/products/automation/industrial-edge.html (verify path).
- Academic anchor for the edge-native claim: *"Edge AI for Smart Energy"* review (IntechOpen): https://www.intechopen.com/chapters/1224342 — ML deployed directly at energy-network endpoints.

## 9.4 Demo rig (hackathon reality check)

One laptop runs everything: Dockerized TimescaleDB + Mosquitto + FastAPI + Grafana; pymodbus simulator exposes "plant registers"; a replay service publishes 10-minute steps every ~2 seconds (Section 14); Needle 2 runs as an HTTP server (`./needle --tools tools.json --serve` on localhost:8080, per the model card) or in-process via the Python API. A Raspberry Pi 5 on the table (running Needle 2 + the index) is the optional physical prop that makes "edge" tangible — bring one if possible.

---

# 10. Weather & Dust Intelligence — Pipeline Design (P6, P7)

Section 2.3 listed the sources; this is how they compose. The pipeline has three jobs: **explain the past**, **normalize the present**, **predict the near future**.

## 10.1 Explain the past (training features)

For each asset, build an hourly weather feature history: NASA POWER (or ERA5 where finer history matters) for irradiance/temperature/wind/precipitation; MERRA-2 surface dust mass concentration as the historical dust-exposure regressor. Join to SCADA history → the twin learns expected output *given environment*, which is the entire basis for "environment vs. equipment" discrimination (ideation §20). Validation: when the site has a pyranometer, cross-check POWER/NSRDB irradiance against it and fit the offset — sensor-vs-satellite disagreement is itself a fault signal (soiled/misaligned pyranometer).

## 10.2 Normalize the present (live residual conditioning)

Live loop: current weather (Open-Meteo/POWER near-real-time + on-site sensors where available) conditions the twin's expected output every cadence step. Output flags: `env_explains_deviation` (cloud transient, temperature derate, humidity), `dust_active` (CAMS DOD forecast overlap + AOD nowcast + PM proxy), `rain_cleaning_event` (precipitation above Kimber reset threshold), `curtailment_suspected` (status codes + grid signals). Only when env flags are quiet do residuals become *equipment evidence*. This module is the single biggest driver of false-alarm reduction — the difference between "output down 8%" and "output down 8%, peers normal, weather normal, soiling low → inspect."

## 10.3 Predict the near future (the dust engine)

1. Pull CAMS 5-day dust forecast (DOD/AOD@550) for the site; validate against AERONET historically (and NOAA STAR operationally) → site-specific calibration factor.
2. Convert calibrated DOD → expected soiling accumulation (Kimber accumulation-rate prior scaled by dust regime; Smestad physics as the citation backbone).
3. Simulate cleaning policies for the next 5–10 days: `clean_now` (before dust settles), `clean_after` (one wash instead of two), `wait_for_rain` (precipitation probability above reset threshold), each with expected recovered energy (tariff × Δsoiling × aperture) vs. wash cost (India: ₹ per MW wash — Section 11).
4. Output: a **cleaning-window recommendation with an explicit break-even** — "wash Thursday evening: saves ₹ X vs. washing Monday; rain Saturday is 62% likely — threshold not met."
5. All numerics live in the `estimate_economic_impact`/soiling tools; Needle 2 retrieves and communicates them (P10).

**Demo moment:** the dust-event case study from the ideation report (§42) is exactly this pipeline narrated over a simulated week: dust forecast arrives → soiling rate doubles → agent recommends cleaning *after* the event with the break-even math — then the "false alarm rejection" case (§44) shows the same engine *suppressing* a fault call when a cloud transient explains the dip. One engine, both directions.

---
# 11. Competitive Landscape — What Exists, and the Gap We Occupy

## 11.1 The players

| Company | What they do | Scale/positioning evidence | The gap they leave open (our lane) |
|---|---|---|---|
| **ONYX Insight** (Macquarie Capital) | Wind predictive analytics + condition monitoring (CMS hardware + SCADA analytics); "ecoCMS", engineering services | Acquired by Macquarie (2024); BP Wind platform rollout; enterprise wind fleets | Wind-only; CMS-hardware-centric; cloud/enterprise services model; no tiny on-prem agent; no rupee-ranked autonomous work queue |
| **Clir Renewables** | Cloud SaaS analytics for wind (and solar) underperformance — yaw/pitch categorization, benchmarking | CDL-backed; cloud SaaS positioning | Cloud-locked; analytics consultancy layer; no edge/privacy story, no cleaning economics |
| **SparkCognition (Renewable Suite)** | AI asset-performance management for wind/solar/storage; generative-AI insights | Ørsted deployed across ~5.5 GW; National Grid Renewables; enterprise APM | Heavy enterprise cloud; no 28 MB plant-local agent; no dust/soiling-vs-equipment adjudication as a headline |
| **Raptor Maps** | Drone thermal-inspection analytics + solar digital twin, serial-level reports | DJI ecosystem partner; per-acre pricing model | Inspection-epoch (drone campaigns), not continuous telemetry; no agent, no economic queue |
| **Sitemark** | Drone thermography + AI solar inspection platform | 2,000+ ha inspected for international operators | Same inspection-campaign niche; no live anomaly pipeline |
| **Bazefield (Univers)** | Renewable OT monitoring/analytics platform (wind, solar, hydro, BESS) | ~23 GW managed across 23 countries | Centralized enterprise OT; no edge AI agent; ROI-ranked maintenance queue absent |
| **Uptime Engineering** | Vienna-based SCADA + maintenance-doc analytics ("Uptime HARVEST"), wind fleets | Analyst-in-the-loop service model | Human-analyst dependent; no automation agent; wind-only |
| **CMS hardware vendors** (Bachmann, Emerson/Bently Nevada, Brüel & Kjær Vibro, HBK) | Vibration-based turbine CMS (retrofit/Embedded); monitoring centers | ~14 of 20 commercial CMS are vibration-based (lit.); Bachmann CMScore now has an entry-level tier | Hardware + per-turbine licensing lock-in; hardware-tied, no software-only edge AI; we *complement* CMS rather than replace it |
| **Adjacent cloud APM** (Nispera/Fluence, UL Solutions diagnostics, GPM Horizon/NYSE-listed) | Cloud monitoring + SCADA diagnostics + solar asset mgmt | Enterprise SaaS | Same cloud posture; same gaps |

**Market context (pitch-slide numbers):** renewable asset-management software ≈ **$5.6B (2024) at ~13% CAGR** (Metastat Insight); alternative sizing $4.8B (2025) → $14.2B (2034) (Dataintelo); wind O&M ≈ **$19.4B (2024) → $36.3B** (Strategic Market Research); **India wind O&M $1.05B (2025) → $1.67B (2030), 9.7% CAGR** (MarketsandMarkets).

## 11.2 The composite gap (validated across every row above)

> **Every serious player is cloud SaaS or vibration-hardware. None ships a tiny local tool-calling agent on plant-edge hardware; none fuses weather/dust intelligence with anomaly detection into rupee-denominated, confidence-gated maintenance prioritization; and none is priced or packaged for the mid-size Indian operator.**

Positioning lines per judge probe:
- vs. **CMS vendors**: "We complement vibration CMS — our layer works where CMS isn't installed (most of the fleet), uses SCADA alone, and adds economics; CMS channels become additional evidence."
- vs. **cloud APM**: "They need the farm's data in their cloud. We run the intelligence on the farm. For operators with confidentiality constraints — which is most of them once you show them what a decade of telemetry reveals — that's the deciding line." (Privacy argument from ideation §5–6; the *Turbine 17* thought experiment is the demo-ready version.)
- vs. **drone analytics**: "They confirm what we find. Our loop names the confirming inspection; their report becomes our closed-loop outcome label."

---

# 12. Economics & India — the Numbers That Anchor Every Rupee Claim

Rules of engagement: every number below carries its source; the ones with weaker sourcing are labeled; the demo uses conservative ends of ranges and says so.

## 12.1 Wind — failure and downtime economics

- Unplanned downtime costs up to **$30,000 per turbine per year** (vhive.ai case literature).
- **25% of faults cause ~95% of downtime**; the pitch system alone ≈ **23% of downtime** (Windurance engineering blog) — prioritization must be consequence-weighted, not frequency-weighted.
- Converter failures: **15–20% of downtime** (Windpower Monthly).
- Gearbox replacement: **$250k–300k** with lead times up to **18 months** post-pandemic (Mordor Intelligence; European figures >€250k, Market Data Forecast); a **preventive swap ≈ $40–50k**, and rebuilt gearboxes cost **3–4×** more than planned work (Aafif et al. 2022, ScienceDirect). This asymmetry is the entire business case for early gearbox detection.
- **Crane mobilization ≈ 50% of single-turbine repair crane cost** (Windpower Engineering) — scheduling detection-to-repair windows is real money.
- Vibration CMS warning window: **3–6 months** for bearings (industry practice) — the P-F window our SCADA layer must not be worse than.
- O&M: **$40k–55k per turbine per year** (Transparency Market Research); mature farms benchmark **~97% availability** (Conroy 2011, ScienceDirect) — every availability point ≈ 87 idle-turbine-hours per 100 turbines/year.

## 12.2 Solar — O&M, soiling, degradation, inverter reliability

- India utility-solar O&M: **₹6–10 lakh per MW per year** (Bluebird Solar, market practitioner range; treat as ±30%).
- US benchmark trend: utility O&M **$40/kW-yr (2012) → ~$11/kW-yr (2024)** (LBNL utility-scale solar report: https://emp.lbl.gov) — margins are thin; software that saves 1–2% of AEP is material.
- Soiling: **≥0.5%/yr loss in rainy climates, >7%/yr in arid ones** (NREL soiling map/studies) — the P7 engine's addressable loss in dusty India is measured in single-digit percent of AEP, i.e., enormous in aggregate.
- Degradation: fleet median **~0.5%/yr** (NREL PV Fleet); literature mean/median ~**1.1%/yr** (Straub-Mück 2025); India long-term c-Si ~**1.9%/yr** (Rajput & Sudhakar); modern TOPCon/HJT **0.3–0.4%/yr**. The twin's expected-PR line drifts with these priors (Section 4.13).
- Inverter failure rates: **1–15%/yr** depending on technology/age (Idbouhouch et al. 2024, ScienceDirect); string inverters ~0.89% in first two years (SolarInsure, weak source — label accordingly). Inverter replacement is the most common *material* solar O&M event.

## 12.3 Tariffs and market scale (India)

- Record solar tariffs: **₹2.00/kWh** all-time low (SECI, Nov 2020, IEEFA: https://ieefa.org); **₹2.86/kWh** for the 2 GW solar + 4 GWh storage auction (Oct 2025, pv-magazine: https://www.pv-magazine.com); wind-solar hybrid **₹2.34/kWh** (JMK Research: https://jmkresearch.com).
- Capacity: record **37.9 GW solar + 6.3 GW wind added in CY2025** (JMK Research tracker); renewables crossed **>50% of installed power capacity** in 2025 (PIB/MNRE); wind fleet ≈ **54.5 GW** (Dec 2025, MNRE-sourced trackers); total RE ≈ 220 GW (2024-25, Enerdata). India-first framing: the installed base is now too large for manual inspection to keep up — the labor math *forces* telemetry-driven O&M.
- **Worked demo numbers:** 50 MW solar plant @ 21% CUF → ~92 GWh/yr; ₹2.5/kWh → ₹23 crore/yr revenue. A 1.5% soiling drag costs ₹34.5 lakh/yr; a missed gearbox event on a 2 MW turbine: 21 days downtime ≈ 590 MWh ≈ ₹14.7 lakh lost energy *plus* $250k–300k replacement risk *plus* crane mobilization. Our "expected avoided loss" figures (₹76,900-style) are then conservative, defensible, and auditably computed by `estimate_economic_impact` (P11) — the agent never invents them.

## 12.4 Predictive-maintenance ROI — the meta-evidence

- Maintenance cost **−25–30%**, unplanned downtime **−35–45%** (MaintainX industry survey compilation).
- Downtime **−35–50%**, asset life **+20–40%** (Nucleus Research).
- **ROI 200–500% in year one** for industrial PdM programs (f7i.ai compilation); 545% ROI preventive-maintenance study (MicroMain). Unplanned downtime costs **~35% more** than planned (MaxGrip).
- Honest framing for judges: these are cross-industry PdM meta-figures; our demo's own numbers come only from the simulated assets' actual computed losses — cite the meta-range as *context*, never as *our result*.

## 12.5 The privacy economics (closing the loop with ideation §5)

The ideation report's Turbine-17 example shows what a decade of asset-level telemetry (identity + location + production + faults + maintenance + configuration) reveals: weak points, maintenance windows, output economics, equipment weaknesses, procedures, infrastructure posture. That is why the architecture (public environment in; operational intelligence local) is a *commercial* feature, not just a security preference: it unlocks AI on data the operator would never upload. Section 11's cloud-locked competitors structurally cannot make that claim without re-architecting — which is the moat statement.

---
# 13. Our Evaluation Protocol (Pre-Committed, So We Can't Fool Ourselves)

## 13.1 Primary benchmark: CARE to Compare + CARE score

- Train healthy-state models on the 50 normal-behavior datasets (plus status-filtered healthy data from event datasets); evaluate on the 45 labeled anomaly events with their documented prediction windows.
- Report: **CARE components** (Coverage, Accuracy, Reliability, Earliness) individually + composite; a **detection-latency histogram** (days before failure, all 45 events); and **zero false-alarm-tolerance curves** (CARE Reliability as a function of threshold).
- Never use point-adjust F1 (Kim AAAI 2022 critique, Section 6.2); if an event-wise number is quoted, add PA%K or segment coverage.

## 13.2 Secondary benchmarks (breadth)

- **Solar labeled set:** NREL synthetic injected outages (exact ground truth → exact detection latency); two-plant Kaggle set for inverter-level demos with hand-verified event annotations.
- **Detector cross-comparison:** our ensemble vs. PyOD IsolationForest/LOF baselines and a plain power-curve threshold, all under the identical protocol — showing the *marginal value* of context and ensembles, not just absolute scores.
- Use TimeEval's metric implementations for the cross-comparison to avoid hand-rolled metric bugs (Section 6.4).

## 13.3 Split hygiene (the leakage checklist)

1. Splits are **time-ordered** (train ends before validation, validation before test). 2. **Grouped by asset** — no turbine/inverter appears in train and test with overlapping dates. 3. Scalers/normalizers fit on train only. 4. Labeled pre-failure windows never straddle a split boundary. 5. Thresholds fixed on validation by a stated policy ("≤1 false alarm per turbine per month"), then frozen for test. 6. Report the policy next to the numbers. 7. Random shuffling is banned; if a reviewer asks "why not k-fold CV?" the answer is Section 6.7.

## 13.4 Metric battery (what the results table shows)

| Metric | Why it's there |
|---|---|
| CARE (C/A/R/E) | Primary, dataset-native, earliness-aware |
| PR-AUC **with prevalence baseline stated** | Imbalance-honest (Richardson 2024 caveat) |
| MCC | Single-number balance under imbalance (Imani 2026) |
| Recall @ alert budget (e.g., 2 alerts/turbine/month) | The operator-facing operating point |
| Median days-before-failure + IQR | Earliness in operator units |
| False alarms per turbine-year | Trust cost, drives adoption |
| Compute cost per asset-day | The edge claim, quantified (ms/inference, MB RAM) |

## 13.5 The overclaim guardrails (from ideation §18, enforced by this section)

We never say "we predict the exact date an asset fails." We say: **anomaly → degradation trend → failure probability → risk window → expected loss → recommended intervention**, each with confidence exposed. Every prediction the demo shows carries its confidence value, and Needle 2's escalation threshold is visible in the UI — the same philosophy as the model card's confidence contract, applied at the product level.

---

# 14. Demo Strategy — Replay, Inject, Investigate, Close the Loop

## 14.1 The live pipeline (what judges actually watch)

```text
REPLAY SERVICE (10-min steps ≈ every 2 s of wall clock)
  ├─ CARE/Kelmarsh/PVDAQ history  →  "months ago"
  └─ MQTT broker (paho)  →  ingestion (pymodbus-simulated registers optional)
        → TimescaleDB hypertables
        → twin + detectors (pvlib/GBM/PyOD/STUMPY/ruptures)
        → evidence packet (residuals, peer percentiles, weather flags, soiling)
        → Needle 2 investigation loop (tools: evidence/weather/cases/RAG/economics/ticket)
        → Grafana: fleet heatmap → asset detail → agent's evidence-first output
        → technician action → outcome label written back (closed loop)
```

Wall-clock compression ~300×: a 3-week degradation episode plays in ~10 minutes of demo. The presenter narrates the ideation report's case studies (solar string, dust event, wind gearbox, false-alarm rejection) *as they happen live*.

## 14.2 Fault-injection profiles (scripted, ground-truth-labeled)

| Profile | Shape | Channels | Ground truth for |
|---|---|---|---|
| `gearbox_bearing_wear` | 2–3 week exponential temp-residual ramp | gearbox bearing/oil temps, rpm | earliness, CARE-E, trajectory retrieval |
| `pitch_misbehavior` | blade-angle asymmetry + alarm-code burst | pitch angles, pitch motor current, alarms | alarm-fusion evidence (3.7) |
| `string_outage_solar` | step −100% on one string | string current vs. peers | peer-comparison speed |
| `soiling_accumulation` | 0.15%/day PR decay, no weather anomaly | PR, soiling ratio, dust index | P7 discrimination |
| `cloud_transient` | 40-min dip, irradiance-correlated | power, irradiance | false-alarm rejection |
| `curtailment_window` | flat cap + status code | power, status | not-a-fault classification |

Each profile has an exact start/duration/ground-truth file — detection latency is *measured*, not claimed. Methodological precedent: NREL's injected-outage synthetic datasets (2.2.5) and HIL fault-injection literature (8.5).

## 14.3 The three demo moments that win judges

1. **The discrimination moment** — cloud transient vs. gearbox ramp side by side; weather engine suppresses one, detector fires on the other. ("Low output ≠ broken equipment," proven live.)
2. **The retrieval moment** — gearbox ramp fires; agent retrieves two historical trajectories ending in bearing replacement; the RAG passage cites the OEM manual section; the economic tool prints the break-even. (CBR + RAG + economics in one breath.)
3. **The escalation moment** — ambiguous case lands below Needle 2's confidence threshold → agent escalates to human review with the evidence packet instead of guessing. (Safety architecture, demonstrated in 30 seconds.)

## 14.4 What to bring

Laptop with the full Docker stack; Raspberry Pi 5 running Needle 2 + the vector index as the physical "edge gateway" (model card: ~500 tok/s decode on Pi 5 — measured live if the Wi-Fi cooperates); printed one-pager with the CARE-score results table; the ideation report as the backup appendix for deep questions.

---

# 15. Resource → Pillar Map (the whole kit on one page)

| Pillar | Datasets (§2) | Papers (§3–5) | Tools (§7–9) | Eval (§6, §13) |
|---|---|---|---|---|
| **P1 Public data** | CARE 2.1.1, EDP 2.1.2, Kelmarsh/Penmanshiel 2.1.3, Hill of Towie 2.1.4, La Haute Borne 2.1.5, SDWPF 2.1.6, PVDAQ 2.2.1, NSRDB 2.2.2, DKASC 2.2.3, two-plant 2.2.4 | Tautz-Weinert 3.3 (curation) | OpenWindSCADA loaders 2.1.10, pvlib iotools, OpenOA | — |
| **P2 Digital twin** | same healthy periods | Zaher 3.1, Pandit 3.6, Chesterman 3.5, Xiang/LSTM 3.9-family, IEC 61400-12-1 3.10, Taghezouit 4.2, Digital-PV 4.15 | pvlib, windpowerlib, RdTools, OpenOA, scikit-learn/XGBoost, GPyTorch | — |
| **P3 Telemetry** | (replay of all) | — | pymodbus, paho-mqtt, Mosquitto, TimescaleDB, FastAPI | — |
| **P4 Anomaly/risk** | CARE events, injected outages 2.2.5 | Kusiak 3.2, RAE 3.9, LOF/dynamic 3.8, Encalada-Dávila 3.11, Carroll 3.11, Miraftabzadeh 4.4, Hu 4.5, Garoudja 4.1, transfer learning 3.12 | PyOD, STUMPY, tsfresh, ruptures, Merlion, darts, ONNX Runtime | §13.1–13.4 |
| **P5 Peer comparison** | Kelmarsh/Penmanshiel, DKASC, PVDAQ, two-plant, SDWPF | UPC fleet 3.7, Leite fleet 3.8, Lindig SCSF 4.13 | pandas ranking layer, Grafana heatmap | fleet-rel. ablation |
| **P6 Weather** | POWER/ERA5/CAMS/MERRA-2 2.3, NSRDB, IMD | SDWPF-NWP usage 2.1.6, Shen dust+temp 4-family | NASA POWER API, Open-Meteo, ERA5 CDS | AERONET validation |
| **P7 Soiling/dust** | NREL soiling map 2.2.7, DKASC, PVDAQ arid sites | Smestad 4.7, Redondo 4.8, Tsanakas 4.9, Matar 4.10, Kimber/SRM 4.11 | pvlib.soiling, RdTools SRM, CAMS ADS API, MERRA-2 | dust-event case |
| **P8 Trajectory memory** | CARE 45 events, EDP logbook | CBR 4R 5.1, VRAE latents 3.9, STUMPY motifs | STUMPY, sentence-transformers + sqlite-vec | retrieval hit-rate on injected profiles |
| **P9 RAG** | GRC taxonomy 2.1.7, IV/EL 2.2.6 | Lewis RAG 5.3, fault→signal tables 3.4 | sqlite-vec (+FTS5), nomic-embed, LlamaIndex-local | source-citation check |
| **P10 Needle 2 agent** | — | Needle 2 paper + BFCL 5.2 | cactus-needle, tool registry §7.3, Ollama/llama.cpp backup | scripted investigation success + calibration curve |
| **P11 Economics** | tariff/capacity data 12.3 | Kimber economics 4.11, Matar 4.10, Carroll cost-asymmetry 3.11 | `estimate_economic_impact` tool, P-F interval math 6.9 | break-even audit |
| **P12 HITL + fleet** | — | open-challenges fleet alerting 6.10 | Grafana queues, FastAPI confirm endpoints, feedback tables | HITL latency, feedback-loop growth |

---

# 16. Build Sequence — From Zero to Demo, Mapped to Resources

**Phase 0 (Day 1–2): Data spine.** Download CARE (Zenodo 15846963) + PVDAQ parquet lake + two-plant Kaggle + DKASC subset; canonical schema mapper; TimescaleDB up; replay service publishing to MQTT. *Deliverable:* "live" telemetry on a Grafana fleet heatmap.

**Phase 1 (Day 3–5): Twins.** pvlib solar expected-power (clear-sky + cell temp + AC clip) on PVDAQ/DKASC sites; IEC-binned GBM wind twin on CARE normal datasets + Kelmarsh; residual z-score service. *Deliverable:* expected-vs-actual panels with residuals.

**Phase 2 (Day 6–8): Detection.** PyOD layer on residual vectors; ruptures for step changes; STUMPY discord scan on key channels; dynamic thresholds conditioned on operating state (3.8); peer-percentile ranking (P5). *Deliverable:* anomaly events firing on injected profiles with measured latency.

**Phase 3 (Day 9–10): Weather/dust.** POWER + Open-Meteo joins; CAMS DOD pull + AERONET calibration notebook; Kimber/SRM soiling estimates; `env_explains_deviation` gate. *Deliverable:* the discrimination moment works.

**Phase 4 (Day 11–13): Memory + RAG + agent.** Trajectory library from CARE events + technician-outcome stubs; sqlite-vec + nomic-embed; corpus of 10–20 manuals/SOP excerpts; Needle 2 tool registry (§7.3) wired to FastAPI endpoints; confidence threshold + escalation UI. *Deliverable:* the retrieval and escalation moments work.

**Phase 5 (Day 14): Economics + polish.** `estimate_economic_impact` with auditable assumptions; priority queue; the four ideation case studies scripted into the replay timeline; results table (CARE + metric battery) computed and printed.

**Stretch (Day 15+):** Qwen3-4B escalation layer on Jetson/Pi; GP twin for uncertainty alerts; ONNX int8 quantization of detectors with latency table; closed-loop outcome ingestion.

---

# 17. Production-Grade Horizon (what the startup story adds)

- **Standards compliance:** PR/availability per IEC 61724-1 methodology; power-curve work per IEC 61400-12-1; CMS interop tracking IEC 61400-30/31 as it lands. These convert a hackathon stack into an auditable product.
- **Enterprise integration:** SCADA historians (PI/OSIsoft, Ignition), MarkVision-style fleet managers; SSO/tenant isolation; model registry + signed model artifacts (Siemens Industrial Edge pattern, 9.3).
- **Data governance:** the privacy architecture (ideation §6) becomes contractual — data-flow diagrams, on-prem install, no-telemetry default, export-only-in-aggregate options for fleet benchmarking (opt-in).
- **Insurance & warranty adjacency:** early-detection records create insurability arguments (avoided-loss documentation) and warranty-claim evidence (degradation curves per IEC methodology) — revenue lines no drone vendor can offer.
- **Fleet learning while staying local:** federated-style pattern — models update locally; only *gradient* or *aggregate* signals (never raw telemetry) participate in cross-fleet learning; opt-in per operator.

---

# 18. Master Link Index & Reading Order

## 18.1 If you only read five things before the hackathon

1. **Chesterman et al. 2023 (WES)** — which NBM to build first: https://wes.copernicus.org/articles/8/1069/2023/
2. **CARE paper + dataset** — our benchmark and metric: https://www.mdpi.com/2306-5729/9/12/138 + https://zenodo.org/records/15846963
3. **Needle 2 model card** — the agent's exact contract: https://huggingface.co/Cactus-Compute/needle2
4. **pvlib + RdTools docs** — the solar twin in two libraries: https://pvlib-python.readthedocs.io + https://rdtools.readthedocs.io
5. **Tautz-Weinert & Watson 2016** — data curation checklist: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rpg.2016.0248

## 18.2 Datasets (canonical access)

| Dataset | Access |
|---|---|
| CARE to Compare | https://zenodo.org/records/15846963 (paper: 10.3390/data9120138) |
| EDP open data | https://www.edp.com/en/innovation/open-data/data (mirror: https://data.mendeley.com/datasets/zjxjnjp3xs) |
| Penmanshiel | https://zenodo.org/records/5946808 · https://zenodo.org/records/16807304 |
| Kelmarsh IFAC subset | https://zenodo.org/records/15799719 |
| Hill of Towie | https://zenodo.org/records/14870021 |
| La Haute Borne | via https://openoa.readthedocs.io |
| SDWPF (KDD Cup 2022) | https://www.nature.com/articles/s41597-024-03111-x · https://huggingface.co/datasets/aigrids/WindFarm_raw |
| NREL GRC gearbox | https://data.openei.org (search GRC) |
| WIND Toolkit | https://www.nrel.gov/grid/wind-toolkit.html |
| PVDAQ | https://data.openei.org/submissions/4568 (DOI 10.25984/1846021; `s3://oedi-data-lake/pvdaq`) |
| NSRDB | https://nsrdb.nrel.gov |
| DKASC | https://dkasolarcentre.com.au |
| Two-plant solar | https://www.kaggle.com/datasets/anikannal/solar-power-generation-data |
| NREL soiling map | https://www.nrel.gov/solar/soiling-map.html |
| PVPMC | https://pvpmc.sandia.gov |
| OpenWindSCADA index | https://github.com/sltzgs/OpenWindSCADA |

## 18.3 Weather/dust APIs

| API | Access |
|---|---|
| NASA POWER hourly | https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ |
| ERA5 (CDS) | https://cds.climate.copernicus.eu |
| CAMS forecasts (ADS) | https://ads.atmosphere.copernicus.eu |
| MERRA-2 | https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/ |
| AERONET | https://aeronet.gsfc.nasa.gov |
| Open-Meteo | https://open-meteo.com/en/docs/historical-weather-api · air quality: /en/docs/air-quality-api |
| IMD | https://mausam.imd.gov.in · gridded: https://www.imdpune.gov.in · IMDLIB: https://imdlib.readthedocs.io |
| NOAA STAR AOD | https://www.star.nesdis.noaa.gov |

## 18.4 Tools & models

pvlib · https://pvlib-python.readthedocs.io — RdTools · https://rdtools.readthedocs.io — windpowerlib · https://windpowerlib.readthedocs.io — OpenOA · https://github.com/NREL/OpenOA — PyOD · https://github.com/yzhao062/pyod — STUMPY · https://stumpy.readthedocs.io — tsfresh · https://tsfresh.readthedocs.io — ruptures · https://centre-borelli.github.io/ruptures-desc/ — Merlion · https://github.com/salesforce/Merlion — darts · https://unit8co.github.io/darts — TimescaleDB · https://www.tigerdata.com — Grafana · https://grafana.com — pymodbus · https://github.com/pymodbus-dev/pymodbus — paho-mqtt · https://pypi.org/project/paho-mqtt/ — ONNX Runtime · https://onnxruntime.ai — Ollama · https://ollama.com — llama.cpp · https://github.com/ggml-org/llama.cpp — sqlite-vec · https://github.com/asg017/sqlite-vec — Needle 2 · https://huggingface.co/Cactus-Compute/needle2 — Jetson Orin Nano Super · https://www.nvidia.com/.../jetson-orin/nano-super/

## 18.5 Key papers (one line each)

Zaher 2009 AAKR/ORA · Kusiak & Verma 2011 pitch/bearing mining · Tautz-Weinert 2016 review · Pandit 2018 GP · Chesterman 2023 NBM bake-off · RAE 2022 residual AE · Encalada-Dávila 2021 SCADA-only RUL · Carroll 2018 gearbox RUL · Energy&AI 2025 generative TL (code: https://github.com/EnergyWeatherAI/WT_Generative_Domain_Adaptation) · Bindingsbø 2023 SHAP · Smestad 2020 soiling physics · Kimber 2006 + Deceglie SRM 2018 · Jordan 2023 clear-sky filters · Lindig 2021 SCSF · Malvoni 2020 0.27–0.5%/yr · Garoudja 2017 statistical FD · Miraftabzadeh 2025 sparse AE · Matar 2024 cleaning optimization · Masita 2025 DL defect review · Gück 2024 CARE · Kim 2022 AUD/PA critique · Sørbø 2024 metric taxonomy · Yang 2024 leakage · Saito & Rehmsmeier 2015 PR plots · Lewis 2020 RAG · Patil 2025 BFCL · Ndubuaku 2026 Needle 2 (arXiv:2607.18363)

*(Full deep dives for every paper above are in Sections 3–6.)*

---

*This compendium was compiled from primary-source verification (Needle 2 model card, CARE Zenodo record, PVDAQ OEDI entry) and 130+ targeted searches across datasets, peer-reviewed literature, tooling, weather APIs, competitor materials, and market/economic sources. Weaker-sourced figures are labeled in-line; verify any number before it reaches an investor deck.*
