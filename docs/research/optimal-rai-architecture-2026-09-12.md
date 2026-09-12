# Optimal RAI Architecture Research Notes

**Date:** 2026-09-12  
**Purpose:** translate the proposed RAI architecture into a defensible build plan grounded in current public methods, official docs, and the existing repository.

## Research Findings

1. **Wind evaluation should be event-aware, not accuracy-led.** CARE to Compare provides a real-world wind anomaly benchmark with 36 turbines, 89 turbine-years, 44 anomalous labeled time frames, 51 normal time series, and a CARE score covering coverage, accuracy/normal behavior, reliability/false alarms, and earliness. This supports RAI's choice to track false alarms per asset-year and lead time, not just point metrics.

2. **Time-series validation must preserve time order.** scikit-learn documents that random KFold and ShuffleSplit can produce unreasonable train/test correlation for time series because nearby observations are autocorrelated. RAI should keep temporal holdouts and purge gaps as first-class evaluation gates.

3. **Point-adjusted anomaly F1 is unsafe as a headline metric.** Recent TSAD evaluation work shows point adjustment can overestimate detector quality and can reward weak/no-skill score generators. RAI should keep PR-AUC, MCC, event precision/recall, false alarms, lead time, calibration, and decision regret as the primary scorecard.

4. **Solar environment intelligence should separate atmospheric dust from panel soiling.** Open-Meteo's air-quality API exposes CAMS-based PM10, PM2.5, dust, and AOD forecasts with global coverage. CAMS forecasts global atmospheric composition and aerosols including desert dust. These are excellent dust-exposure priors, but measured PV performance, irradiance, rain, clear-sky normalization, cleaning history, and peer behavior should estimate actual soiling.

5. **PV normalization should use established solar tooling.** pvlib implements the Ineichen/Perez clear-sky model for GHI/DNI/DHI. RdTools includes SRR and CODS soiling/degradation methods. RAI should compare custom soiling logic against these baselines where dependency and data shape permit.

6. **Operational intelligence should optimize decisions, not alerts.** The strongest product loop is: expected behavior -> residual/anomaly -> environmental and peer explanation -> calibrated risk -> historical case evidence -> counterfactual scenarios -> deterministic economics -> human-reviewed recommendation.

## Source Links

- CARE to Compare paper: https://arxiv.org/abs/2404.10320
- CARE dataset record: https://zenodo.org/
- scikit-learn cross-validation guidance: https://scikit-learn.org/stable/modules/cross_validation.html
- scikit-learn TimeSeriesSplit: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- Open-Meteo Air Quality API overview: https://open-meteo.com/
- NASA POWER: https://power.larc.nasa.gov/
- pvlib clear-sky docs: https://pvlib-python.readthedocs.io/
- RdTools soiling example: https://rdtools.readthedocs.io/en/stable/examples/degradation_and_soiling_example.html
- RdTools SRR docs: https://rdtools.readthedocs.io/en/stable/generated/rdtools.soiling.SRRAnalysis.run.html
- RdTools CODS docs: https://rdtools.readthedocs.io/en/latest/generated/rdtools.soiling.soiling_cods.html
- Point-adjustment critique: https://ojs.aaai.org/
- Balanced point-adjustment paper: https://arxiv.org/abs/2409.13053

## Recommended Build Gates

### Gate 1: Honest Baseline

Run the current system without model changes. Persist top-level and `baseline/` artifacts. Required outputs:

- model comparison table
- temporal split report
- asset holdout report
- calibration bins
- latency summary
- explicit gaps for OOD, external CARE, and solar environmental ablations

### Gate 2: Leakage-Safe Model Evaluation

Add tests and artifacts for scaler, threshold, calibration, event, and retrieval leakage. Evaluation should fail loudly if any future data, duplicated case, or held-out asset enters training or memory.

### Gate 3: Environmental Intelligence

Strengthen the solar branch:

- CAMS/Open-Meteo dust, AOD, PM10 exposure windows
- NASA POWER historical context
- pvlib clear-sky normalization where available
- RdTools SRR/CODS baseline comparison where available
- dust-risk, soiling-state, rain-cleaning, and cleaning-regret metrics

### Gate 4: Decision Intelligence

Harden the deterministic scenario and economics layer:

- asset-specific action spaces
- 24h, 72h, 7d, 14d, 30d horizons
- intervention cost, downtime, energy loss, residual risk, expected failure loss
- decision regret against simulator ground truth
- explicit `ACT`, `MONITOR`, `WAIT`, `DO_NOTHING`, `HUMAN_REVIEW`, `INSUFFICIENT_EVIDENCE`

### Gate 5: Evidence And Agent

Only after numerical evidence is stable:

- local RAG with source, section, snippet, relevance
- historical trajectory retrieval with similarity separate from probability
- agent tool policy that forbids invented evidence or arithmetic

### Gate 6: Frontend

Build around actual intelligence:

- fleet command
- asset investigation
- solar soiling
- historical time machine
- counterfactual replay
- knowledge explorer
- evaluation dashboard

### Gate 7: Optional Operations

Route optimization belongs after the decision engine is validated. Treat it as an execution layer, not as the core ML claim.
