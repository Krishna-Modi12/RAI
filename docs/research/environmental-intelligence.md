# Research Compendium: Solar Environmental Risk Intelligence, Desert Soiling & Cleaning Optimization

**Author:** Renewable Asset Intelligence (RAI) Engineering & Science Team  
**Scope:** Atmospheric physics, desert dust forecasting (CAMS / Open-Meteo), clear-sky solar modeling (`pvlib`), soiling kinetics, and event-driven cleaning economics.  
**Normative Status:** Guides `rai/models/environment_solar.py`, `rai/models/weather_provider.py`, and `rai/economics/engine.py`.

---

## 1. The Environmental Reality of Utility Solar in Arid & Semi-Arid Regions

In utility-scale solar installations across western India (e.g., Charanka Solar Park, Patan district, Gujarat, and Bhadla Solar Park, Rajasthan), soiling is not a uniform background nuisance—it is an episodic, highly volatile operational risk:

1. **IEA PVPS Task 13 Findings**: The International Energy Agency Photovoltaic Power Systems Programme (IEA PVPS) identifies soiling as one of the largest worldwide causes of preventable PV underperformance, causing $>4\text{–}7\%$ annualized energy loss globally and exceeding $20\text{–}30\%$ loss during dust storm episodes.
2. **Desert Dust Storms (*Andhi*)**: Pre-monsoon and summer convective dust storms deposit significant particulate matter in hours. A single event can reduce plane-of-array (POA) optical transmittance by $8\text{–}15\%$ overnight.
3. **The Light Rain Trap (Cementation)**: A common operational failure is assuming all precipitation cleans panels. Studies (e.g., Kimber et al., 2006; Micheli & Muller, 2017) show that light rainfall ($<2\text{–}3\text{ mm}$) during or immediately following elevated airborne dust conditions forms muddy streaks and cement-like deposits that bake onto the glass under subsequent solar irradiance, worsening transmittance loss rather than restoring it. Conversely, intense rainfall ($>5\text{ mm}$) provides effective natural washing.

---

## 2. Atmospheric & Dust Data Architecture (CAMS & Open-Meteo)

RAI integrates atmospheric composition forecasts using the Copernicus Atmosphere Monitoring Service (CAMS) provided through the Open-Meteo Air Quality and Weather APIs:

### 2.1 Monitored Atmospheric Variables
* **Dust Particulate Matter ($\mu\text{g/m}^3$)**: Near-surface desert dust aerosol concentration.
* **Aerosol Optical Depth (AOD @ 550 nm)**: Column-integrated extinction coefficient measuring atmospheric turbidity. AOD $>0.5$ indicates heavy haze; AOD $>1.0$ indicates an active dust/sandstorm.
* **Particulate Matter ($\text{PM}_{10}, \text{PM}_{2.5}$)**: Coarse and fine suspended particulates indicating local dust loading.
* **Precipitation (mm) & Probability ($\%$)**: Forecasted rainfall accumulation and probability over 24h, 48h, and 72h horizons.
* **Wind Velocity ($v_{\text{wind}}$) & Direction ($\theta_{\text{wind}}$)**: Determines dust transport and saltation potential ($v_{\text{wind}} > 8\text{ m/s}$ in dry soils triggers dust entrainment).

### 2.2 Provider Abstraction & Offline Resiliency
* **Live Ingestion**: `OpenMeteoProvider` queries hourly CAMS and meteorological variables up to 5 days ahead.
* **Cached / Offline Fallback**: Deterministic offline fixtures calibrated to Charanka historical meteorology guarantee uninterrupted edge execution even during plant communication dropouts.

---

## 3. Physics-Informed Solar Baseline (`pvlib`)

To prevent atmospheric attenuation from being misdiagnosed as inverter or DC-string failure, RAI implements a clear-sky reference layer using `pvlib-python`:

```
Direct Normal Irradiance (DNI)
Diffuse Horizontal Irradiance (DHI)  ──►  Clear-Sky Model  ──►  Clear-Sky POA Irradiance
Global Horizontal Irradiance (GHI)        (Ineichen/Perez)      (G_poa,expected)
                                                                       │
Measured Ambient Temp (T_amb)       ──►  Faiman/King Cell  ──►         ▼
Measured Wind Speed (v_wind)              Temp Model            Expected DC Power (P_dc,expected)
                                                                       │
Measured POA Irradiance (G_poa,actual) ───────────────────────►        ▼
                                                                Transmittance & Soiling Ratio
```

### 3.1 Clear-Sky Irradiance Normalization
Using the Ineichen/Perez clear-sky model with Linke turbidity, clear-sky global horizontal irradiance $G_{\text{ghi,cs}}$ is computed for site latitude and solar zenith angle $\theta_z$:
$$G_{\text{ghi,cs}} = a_1 I_0 \cos\theta_z \exp\left( -a_2 m (f_{\text{h1}} + f_{\text{h2}} (T_L - 1)) \right)$$
Transposing to plane-of-array gives the un-attenuated reference $G_{\text{poa,cs}}$. Comparing measured $G_{\text{poa}}$ against $G_{\text{poa,cs}}$ cleanly isolates cloud and haze transients before evaluating inverter performance.

### 3.2 Kimber & RdTools Soiling Kinetics
Following Kimber et al. (IEEE PVSC, 2006) and NREL RdTools:
* **Soiling Ratio ($SR_t \in [0, 1]$)**: Ratio of observed performance ratio ($\text{PR}_t$) to clean-panel reference ($\text{PR}_{\text{clean}}$) during clear-sky midday periods ($G_{\text{poa}} > 400\text{ W/m}^2$).
* **Soiling Accumulation Rate ($\beta_{\text{soil}}$)**: Daily slope of performance degradation between rain/cleaning events:
  $$SR_t = SR_{t_0} - \beta_{\text{soil}} \cdot (t - t_0) + \epsilon_t$$
  Typical dry-season rate: $\beta_{\text{soil}} \approx 0.20\text{–}0.35\%/\text{day}$; post-sandstorm rate: sudden jump of $5\text{–}12\%$.
* **Rain Wash Reset Condition**:
  $$SR_t \leftarrow 1.0 \quad \text{if } P_{\text{rain, 24h}} \ge 5.0\text{ mm} \text{ and } \text{Dust}_{24h} < 50\,\mu\text{g/m}^3$$
* **Muddy Cementation Risk**:
  $$\text{Flag Cementation Risk} \quad \text{if } 0.5\text{ mm} \le P_{\text{rain, 24h}} < 3.0\text{ mm} \text{ and } \text{Dust}_{24h} \ge 120\,\mu\text{g/m}^3$$

---

## 4. Additive Loss Decomposition Architecture

When a solar inverter underperforms its nominal rated capacity, plant operators require an exact, additive breakdown of losses rather than an ambiguous alert.

For nominal expected clean power $P_{\text{rated,stc}}$ and actual power $P_{\text{actual}}$:
$$\Delta P = P_{\text{expected,clean}} - P_{\text{actual}}$$

RAI strictly enforces exact additivity:
$$\Delta P = \Delta P_{\text{irradiance}} + \Delta P_{\text{soiling}} + \Delta P_{\text{thermal}} + \Delta P_{\text{curtailment}} + \Delta P_{\text{equipment}} + \Delta P_{\text{unexplained}}$$

| Component | Physical Mechanism | Computation Basis |
|---|---|---|
| **$\Delta P_{\text{irradiance}}$** | Cloud coverage, atmospheric haze, solar geometry | $(G_{\text{poa,cs}} - G_{\text{poa,actual}}) \times \eta_{\text{stc}} \times A_{\text{pv}}$ |
| **$\Delta P_{\text{thermal}}$** | Cell efficiency temperature derating | $P_{\text{dc}} \times \gamma_{\text{temp}} \times (T_{\text{cell}} - 25^\circ\text{C})$ |
| **$\Delta P_{\text{soiling}}$** | Optical dust accumulation on module front glass | $(1.0 - SR) \times P_{\text{expected,clean}}$ |
| **$\Delta P_{\text{curtailment}}$** | Grid export setpoint curtailment / frequency limit | $P_{\text{expected}} - P_{\text{setpoint}}$ when `curtailment_flag = True` |
| **$\Delta P_{\text{equipment}}$** | Inverter IGBT degradation, blown DC string fuses | Deficit confirmed asset-specific relative to healthy peers |
| **$\Delta P_{\text{unexplained}}$** | Residual variance unassigned to physical drivers | $\Delta P - \sum \Delta P_i$; if $>5\%$, triggers `human_review` |

---

## 5. Event-Driven Smart Cleaning Optimization

Static bi-weekly or monthly panel washing schedules either waste money by cleaning immediately before rain or lose money by allowing severe post-dust soiling to linger.

RAI formulates cleaning dispatch as a **finite-horizon dynamic cost minimization problem**. For candidate delay horizons $d \in \{0, 1, 3, 7\}$ days:

$$\text{Net Exposure}(d) = C_{\text{clean}} + \sum_{t=1}^H \left( \Delta E_{\text{lost}}(t, d) \times \text{Tariff} \right) - E_{\text{rain-benefit}}(d)$$

Where:
* $C_{\text{clean}}$ = Direct cleaning expenditure (contractor labor + demineralized water + robotic cleaning fuel) $\approx \text{INR } 42,000$ per 24-inverter block.
* $\Delta E_{\text{lost}}(t, d)$ = Energy deficit on day $t$ assuming uncleaned state until day $d$.
* $E_{\text{rain-benefit}}(d)$ = Expected natural washing savings if rainfall $P_{\text{rain}} \ge 5\text{ mm}$ occurs before day $d$:
  $$E_{\text{rain-benefit}}(d) = P(\text{Rain} \ge 5\text{ mm within } d) \times C_{\text{clean}}$$

### Decision Matrix
* If $P(\text{Rain} \ge 5\text{ mm in } 48\text{h}) > 0.40$ and current soiling loss $< 8\%$, **Wait for natural wash; reassess 24h post-rain**.
* If Dust Storm occurs $\to$ soiling jumps $>10\%$, and $P(\text{Rain}) < 0.15$, **Dispatch emergency washing immediately (break-even $<3.2$ days)**.
* If light rain ($<2\text{ mm}$) occurs on high dust $\to$ cementation warning triggered $\to$ **Dispatch mechanical brush wash with high water volume**.

---

## 6. References

1. **IEA PVPS Task 13** (2025). *Technical and Economic Assessment of PV Soiling and Mitigation Strategies*. Report IEA-PVPS T13-22:2025.
2. **Kimber, A., Mitchell, L., Nogradi, S., & Wenger, H.** (2006). *The effect of soiling on large grid-connected photovoltaic systems in California and the Southwest Region*. IEEE 4th World Conference on Photovoltaic Energy Conversion.
3. **Micheli, L., & Muller, M.** (2017). *An investigation of the effect of rainfall on photovoltaic soiling*. IEEE Journal of Photovoltaics, 7(5):1371–1376.
4. **Holmgren, W. F., Hansen, C. W., & Mikofski, M. A.** (2018). *pvlib python: a python package for modeling solar energy systems*. Journal of Open Source Software, 3(29), 884.
5. **Copernicus Atmosphere Monitoring Service (CAMS)**. *Global Atmospheric Composition Forecasts & Desert Dust Models*. European Centre for Medium-Range Weather Forecasts (ECMWF).
