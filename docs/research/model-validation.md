# Research Compendium: Model Validation, Leakage Prevention & Predictive Maintenance Evaluation

**Author:** Renewable Asset Intelligence (RAI) Engineering & Science Team  
**Scope:** Rigorous evaluation methodologies for early fault detection in wind & solar SCADA time series.  
**Normative Status:** Guides evaluation harness design (`rai/eval/`), split mechanics (`splits.py`), leakage detection (`leakage.py`), and metrics (`metrics.py`).

---

## 1. The Core Failure Mode of Standard ML in Industrial Predictive Maintenance

In consumer or tabular ML, accuracy, ROC-AUC, and point-adjusted F1 ($F_1^{\text{PA}}$) are ubiquitous. In industrial SCADA early fault detection, optimizing for these metrics produces catastrophically misleading models:

1. **Extreme Class Imbalance**: Normal operation accounts for $>99\%$ of 10-minute intervals. A degenerate classifier predicting "always normal" achieves $>99\%$ accuracy while preventing zero failures.
2. **Point-Adjustment Traps ($F_1^{\text{PA}}$)**: Standard benchmark libraries often grant full true-positive credit to an entire multi-day anomaly interval if even a single point crosses the threshold. Kim et al. (AAAI 2022) and subsequent literature demonstrated that random noise spikes achieve $F_1^{\text{PA}} > 0.90$ under point adjustment. RAI strictly rejects pure point-adjusted metrics in favor of range-aware, event-level, and operational scoring.
3. **Temporal Autocorrelation & Data Leakage**: SCADA features (such as bearing temperature or active power) are continuous processes with long auto-regressive memories. Random train/test splits leak identical operating states between adjacent 10-minute records ($t$ and $t+1$), yielding near-zero validation error that completely collapses when deployed on future time horizons.
4. **Turbine Memorization**: An unconstrained machine learning model can easily memorize the baseline calibration of a specific physical turbine (e.g., Turbine 17's specific anemometer bias) rather than learning the generalized degradation physics.

---

## 2. The CARE Benchmark Formulation

For wind turbine anomaly detection, RAI adopts the **CARE to Compare** benchmark formulation (Gück, Roelofs, Faulstich et al., Fraunhofer IEE, *MDPI Data* 9(12):138, 2024; Zenodo 15846963).

CARE formulates early fault detection along four independent, operational axes:

$$\text{CARE} = \frac{C + A + R + E}{4}$$

### 2.1 Coverage ($C$)
Measures the proportion of ground-truth component failures that were detected within their pre-failure anomaly window:
$$C = \frac{\sum_{i=1}^{N_{\text{events}}} \mathbf{1}(\text{detected}_i)}{N_{\text{events}}}$$
A failure that occurs without prior alert receives $C_i = 0$.

### 2.2 Accuracy ($A$)
Measures the reliability of predictions during confirmed healthy operating periods. To prevent status changes (curtailment, scheduled maintenance, icing shutdowns) from contaminating the healthy baseline, intervals with non-zero maintenance/curtailment status codes are filtered before computing true negative specificity.

### 2.3 Reliability ($R$) — False Alarm Resistance
Measures the operational alert burden placed on plant operators:
$$R = \exp\left(-\frac{\text{False Alarms per Asset-Year}}{\lambda_{\text{budget}}}\right)$$
where $\lambda_{\text{budget}}$ is the maximum tolerable false alarm budget (set to 12 false alarms/turbine-year, or 1/month).

#### Storm Suppression Rule (72-Consecutive-Point Filter)
To prevent single SCADA glitches from triggering operator dispatch, an alert event is confirmed only when the fused anomaly score remains above threshold for $\ge 72$ consecutive 10-minute points (12 continuous hours), or where a verified changepoint step-change persists $\ge 6$ hours.

### 2.4 Earliness ($E$)
Measures how much lead time the model gives maintenance teams before catastrophic failure:
$$E = \frac{1}{N_{\text{detected}}} \sum_{i \in \text{detected}} \min\left(1.0, \frac{\Delta t_{\text{lead}, i}}{\Delta t_{\text{P-F}, \text{target}}}\right)$$
where $\Delta t_{\text{lead}, i}$ is the time difference between the first confirmed detection and actual component failure, and $\Delta t_{\text{P-F}, \text{target}}$ is the target operational planning window (14 to 30 days). An alarm 1 hour before failure is operationally useless; an alarm 14 days before failure enables scheduled crane and crew dispatch.

---

## 3. Strict Leakage Prevention Architecture

RAI implements four mandatory leakage barriers:

```
[Level 1: Temporal Holdout]  Train: Days 0..T1  ──[Purge Gap]──►  Test: Days T2..Tend
[Level 2: Asset Holdout]     Train: Assets A..K ──────────────►  Test: Assets L..Z (Unseen)
[Level 3: Site Holdout]      Train: Site 1      ──────────────►  Test: Site 2 (Cross-Site)
[Level 4: OOD Challenge]     Train: Standard    ──────────────►  Test: Altered Physics & Noise
```

1. **Purged & Embargoed Cross-Validation**: Following de Prado (2018), temporal splits introduce an embargo gap ($g \ge 24\text{ hours}$) between training and test sets to eliminate autoregressive information carryover.
2. **Strict Preprocessing Enclosure**:
   - Scalers (`StandardScaler`, `RobustScaler`), PCA transforms, and power curve baselines must be fit strictly on training fold observations.
   - Normalization statistics must never inspect validation or test records.
3. **Threshold & Calibration Isolation**:
   - Anomaly score thresholds ($\tau_z, \tau_{\text{IF}}$) and probability calibration mappings (Platt sigmoid, isotonic regression) must be tuned strictly on the validation set, never on the test partition.
   - Once a test split is evaluated, no hyperparameter or threshold adjustment is permitted.

---

## 4. Probabilistic Risk Calibration

A predictive maintenance system must provide calibrated failure probabilities, not arbitrary decision scores. If an asset is assigned an $80\%$ probability of failure within 30 days, approximately 8 out of 10 such historical cases must result in failure.

### 4.1 Brier Score
The Mean Squared Error of probability forecasts:
$$\text{BS} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
Decomposed into Reliability, Resolution, and Uncertainty:
$$\text{BS} = \text{Reliability} - \text{Resolution} + \text{Uncertainty}$$

### 4.2 Expected Calibration Error (ECE)
Grouping predicted probabilities into $M$ bins $B_m \subset (0, 1]$:
$$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
where $\text{conf}(B_m)$ is the mean predicted probability in bin $m$, and $\text{acc}(B_m)$ is the empirical event frequency.

### 4.3 Reliability Diagram
Plots $\text{conf}(B_m)$ vs. $\text{acc}(B_m)$ alongside the $45^\circ$ diagonal. Deviations below the diagonal indicate over-confidence; deviations above indicate under-confidence.

---

## 5. Champion–Challenger Evaluation Matrix

For every diagnostic task, RAI systematically benchmarks six model tiers:

| Tier | Name | Formulation | Operational Role |
|---|---|---|---|
| **Baseline 1** | Simple Physics / Rules | IEC 61400-12 power curve envelope + static thermal limits | Sanity check; guarantees explainable safety boundaries |
| **Baseline 2** | Expected-Behavior Regression | LightGBM / Ridge / Polynomial fit ($P = f(v_{\text{wind}}, \rho_{\text{air}})$) | Quantifies raw residual deviation $\Delta P$ |
| **Baseline 3** | Residual Thresholding | Mahalanobis distance & z-score on load-normalized residuals | Direct statistical signal tracking |
| **Baseline 4** | Residual + Isolation Forest | Unsupervised multidimensional anomaly detection on residuals | Detects complex correlated multi-channel shifts |
| **Baseline 5** | Residual + Change-point Detection | Pruned Exact Linear Time (PELT / Ruptures) on residual drift | Distinguishes abrupt steps from continuous trends |
| **Challenger** | Hybrid Ensemble | Layered Bayesian fusion + Environmental & Peer Gating | Champion model combining physical bounds and ML |

---

## 6. References

1. **Gück, R., Roelofs, S., Faulstich, S., et al.** (2024). *CARE to Compare: A real-world dataset for anomaly detection in wind turbine data*. MDPI Data 9(12):138. DOI: `10.3390/data9120138`.
2. **Kim, S., Choi, K., Choi, H. S., et al.** (2022). *Towards a Rigorous Evaluation of Time-Series Anomaly Detection*. AAAI Conference on Artificial Intelligence.
3. **de Prado, M. L.** (2018). *Advances in Financial Machine Learning* (Purged K-Fold Cross-Validation and Combinatorial Purged CV). Wiley.
4. **Ahmad, S., Lavin, A., Purdy, S., & Agha, Z.** (2015). *Evaluating Real-time Anomaly Detection: The Numenta Anomaly Benchmark*. arXiv:1510.03375.
5. **Niculescu-Mizil, A., & Caruana, R.** (2005). *Predicting good probabilities with supervised learning*. ICML.
