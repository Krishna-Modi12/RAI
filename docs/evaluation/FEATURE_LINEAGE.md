# Feature Lineage & Temporal Isolation Ledger (Gate 2)

**Status:** Scientifically audited & verified  
**Last Updated:** 2026-09-12  
**Artifact Path:** `artifacts/evaluation/gate2/feature_lineage.csv`

---

## 1. Core Invariant: Strict Temporal Causality

For every prediction or state estimation at time $t$, the feature representation $X_t$ must depend exclusively on physical and environmental observations made at or before $t$:

$$X_t = f\left(D_{\le t}\right)$$

Under no circumstances may any transformation evaluate future observations:

$$X_t \ne f\left(D_{\le t + k}\right) \quad \forall k > 0$$

Every feature generator in `rai/features/build.py`, `rai/models/anomaly.py`, `rai/models/expected.py`, `rai/models/peers.py`, and `rai/environment/` was audited against this invariant.

---

## 2. Feature Pipeline Audit Findings

### 2.1 Rolling Windows & Smoothing
- **Trailing vs. Centered:** All pandas `.rolling()` operations strictly utilize `center=False` (the pandas default). No centered or future-looking windows exist anywhere in the feature extraction code.
- **Window Sizes:** 
  - Wind speed statistics: 60 minutes (`wind_mean_60m`, `wind_std_60m`).
  - Irradiance statistics: 60 minutes (`poa_mean_60m`, `poa_std_60m`).
  - Thermal load tracking: 60, 180, and 360 minutes (`load_mean_60m`, `load_mean_180m`, `load_mean_360m`).
- **Lag Operations:** All `.shift()` calls use positive step integers (`load_lag_30m`, `load_lag_60m`, `load_lag_180m`), shifting backwards in time. No `shift(-n)` operations exist.
- **Exponential Smoothing:** `.ewm(halflife=...)` evaluates only past history with recursive exponential decay; no forward interpolation is performed.

### 2.2 Learned Models & Scalers (Training-Only Isolation)
- **Expected-Behaviour Models (XGBoost):**
  - Trained exclusively on healthy productive prefixes (`ts < cutoff`, where `cutoff` is the onset of any injected fault).
  - No test observations or post-fault periods enter the model training sets.
- **Per-Asset Residual Baselines (`baselines.json`):**
  - Median and MAD estimators are fitted strictly on the healthy training prefix of each individual asset.
  - Test period residuals are normalized using the frozen training baseline $(\text{residual} - \text{median}_{\text{train}}) / \sigma_{\text{train}}$.
- **Isolation Forests (`iforest_*.pkl`):**
  - Fitted per asset on healthy residual vectors during the training window.
  - Scored out-of-sample on trailing 6-hour windows.
- **Risk Model Classifier & Scaler (`risk_model.pkl`):**
  - Grouped by asset ID with leave-one-asset-out cross-validation for out-of-fold probability generation.
  - Final scaler is fitted only on training partitions.

### 2.3 Historical Memory & Case Retrieval
- Case matching in `rai/memory/retrieval.py` now enforces a strict `knowledge_cutoff`:
  - An evaluation at time $t$ can only retrieve historical cases whose closure date satisfies $t_{\text{closed}} \le t$.
  - When evaluating an asset holdout, the target asset's own historical records are excluded (`exclude_asset_id`) to prevent self-retrieval leakage.

---

## 3. Summary Ledger Table

| Group | Variables | Lookback ($L$) | Forward ($k>0$) | Fitted Parameters | Provenance | Leakage Status |
|---|---|---|---|---|---|---|
| **Atmospheric Telemetry** | `wind_speed_ms`, `air_density`, `ambient_temp_c`, `poa_wm2` | Instantaneous | None | None | Raw Sensor | ✅ SAFE |
| **Rolling Wind & Solar** | `wind_mean_60m`, `poa_std_60m`, `turbulence_intensity` | Trailing 60 min | None | None | Trailing Window | ✅ SAFE |
| **Thermal Dynamics** | `load_lag_180m`, `load_mean_360m`, `load_ewm_180m` | Trailing 360 min | None | None | Trailing Window | ✅ SAFE |
| **Expected Behavior** | `wind_power`, `solar_power`, thermal models | Instantaneous features | None | XGBoost trees | Train prefix only | ✅ SAFE |
| **Residual Normalization** | `residual_z` (z-score) | Trailing 6h | None | Median, MAD $\sigma$ | Train prefix only | ✅ SAFE |
| **Manifold Anomaly** | `iforest_score` | Trailing 6h | None | 200 Isolation Trees | Train prefix only | ✅ SAFE |
| **Peer Deviation** | `peer_median_deviation`, `peer_percentile` | Synchronous $t$ | None | Fleet median at $t$ | Cross-sectional at $t$ | ✅ SAFE |
| **Environmental Attribution** | `explains_fraction`, `soiling_loss_pct` | Trailing 24h | None | Kimber kinetics | Prior physics | ✅ SAFE |
| **Historical Retrieval** | `case_similarity` | Trailing signature | None | k-NN weights | Eligible $\le t$ | ✅ SAFE (with cutoff) |
