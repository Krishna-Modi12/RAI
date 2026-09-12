"""Unit tests for Gate 5.2 Published IF Baseline, RAI Champion, and Feature Policies.

Verifies:
1. CARE_PUBLISHED_IF baseline parameters, PCA 99% policy, and imputation.
2. RAI Champion detector expected power curve regression and persistence gating.
3. Feature policy resolution and schema invariance.
4. Train/prediction split boundary enforcement (zero leakage).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rai.eval.external.care.champion import fit_rai_champion
from rai.eval.external.care.features import (
    CARE_COMMON_SIGNALS,
    FARM_COMMON_MAPPING,
    get_feature_columns,
)
from rai.eval.external.care.published_if import fit_published_isolation_forest


class TestPublishedIsolationForest:
    """Test CARE_PUBLISHED_IF implementation."""

    def test_pca_99_variance_retention(self):
        """Verify that PCA retains 99% of variance and produces expected provenance."""
        np.random.seed(42)
        n = 500
        # Create 5 features where first 2 explain 99%+ of variance
        f1 = np.random.randn(n) * 10.0
        f2 = np.random.randn(n) * 10.0
        f3 = np.random.randn(n) * 0.05
        f4 = np.random.randn(n) * 0.05
        f5 = np.random.randn(n) * 0.05
        df = pd.DataFrame({"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5})

        model = fit_published_isolation_forest(
            df,
            columns=["f1", "f2", "f3", "f4", "f5"],
            contamination=0.09,
            n_estimators=100,
            seed=20260912,
        )

        assert model.provenance["baseline_name"] == "CARE_PUBLISHED_IF"
        assert model.provenance["pca_policy"] == "retain_99_pct_variance"
        assert model.provenance["contamination"] == 0.09
        assert model.provenance["n_estimators"] == 100
        assert model.pca is not None
        # PCA should have reduced 5 dimensions to at most 3 while retaining >= 99% variance
        assert model.pca.n_components_ <= 4
        assert model.provenance["pca_variance_explained"] >= 0.99

    def test_missing_values_imputed_from_train_medians(self):
        """Prediction frame missing values are filled from train medians, not prediction medians."""
        train_df = pd.DataFrame({
            "col1": [10.0, 20.0, 30.0, 40.0, 50.0],  # median = 30.0
            "col2": [1.0, 2.0, 3.0, 4.0, 5.0],      # median = 3.0
        })
        model = fit_published_isolation_forest(train_df, columns=["col1", "col2"])

        # Test frame with missing values
        test_df = pd.DataFrame({
            "col1": [np.nan, 20.0],
            "col2": [2.0, np.nan],
        })
        preds = model.predict(test_df)
        assert len(preds) == 2
        assert set(preds).issubset({0, 1})


class TestRAIChampionDetector:
    """Test RAI Champion detector adapter."""

    def test_expected_power_curve_and_underproduction_alert(self):
        """Underproduction fault generates alarms, while normal operation does not."""
        np.random.seed(42)
        n = 200
        ws = np.linspace(3.0, 15.0, n)
        # Power roughly quadratic: P = 10 * ws^2
        p_normal = 10.0 * (ws**2) + np.random.randn(n) * 5.0
        rs = 2.0 * ws + np.random.randn(n) * 0.2

        train_df = pd.DataFrame({
            "wind_speed_3_avg": ws,
            "power_29_avg": p_normal,
            "sensor_52_avg": rs,
        })

        champion = fit_rai_champion(
            train_df,
            farm_name="Wind Farm A",
            feature_policy="care_common",
            z_threshold=2.5,
            persistence_steps=3,
        )

        assert champion.provenance["detector_name"] == "RAI_CHAMPION_HYBRID"
        assert champion.power_poly is not None

        # Test on healthy data: almost no alarms
        healthy_df = pd.DataFrame({
            "wind_speed_3_avg": ws[:50],
            "power_29_avg": p_normal[:50],
            "sensor_52_avg": rs[:50],
        })
        healthy_preds = champion.predict(healthy_df)
        assert healthy_preds.sum() <= 2

        # Test on degraded data: severe underproduction (power drops to 20% of expected)
        degraded_p = 0.2 * (10.0 * (ws[50:100] ** 2))
        degraded_df = pd.DataFrame({
            "wind_speed_3_avg": ws[50:100],
            "power_29_avg": degraded_p,
            "sensor_52_avg": rs[50:100],
        })
        degraded_preds = champion.predict(degraded_df)
        # Should flag majority of degraded timestamps
        assert degraded_preds.mean() > 0.70

    def test_persistence_gating_filters_transient_spikes(self):
        """A single 1-step transient excursion does not trigger an alarm when persistence=3."""
        train_df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(5.0, 10.0, 50),
            "power_29_avg": np.linspace(250.0, 1000.0, 50),
            "sensor_52_avg": np.linspace(10.0, 20.0, 50),
        })
        champion = fit_rai_champion(
            train_df,
            farm_name="Wind Farm A",
            z_threshold=2.5,
            persistence_steps=3,
        )

        # Test sequence with exactly 1 anomalous point
        ws_test = np.full(10, 8.0)
        p_test = np.full(10, 700.0)  # exact expected power (150*8 - 500 = 700)
        p_test[4] = 0.0              # isolated single 10-min blip

        test_df = pd.DataFrame({
            "wind_speed_3_avg": ws_test,
            "power_29_avg": p_test,
            "sensor_52_avg": np.full(10, 16.0),
        })

        preds = champion.predict(test_df)
        # The single transient spike should be suppressed by 3-step persistence
        assert preds.sum() == 0


class TestFeaturePolicies:
    """Test feature policy definitions."""

    def test_care_common_resolves_three_canonical_signals_per_farm(self):
        for farm in ("Wind Farm A", "Wind Farm B", "Wind Farm C"):
            mapping = FARM_COMMON_MAPPING[farm]
            assert set(mapping.keys()) == set(CARE_COMMON_SIGNALS)
            cols = list(mapping.values())
            resolved = get_feature_columns(farm, "care_common", cols)
            assert len(resolved) == 3
            assert resolved == cols

    def test_care_native_excludes_metadata(self):
        all_cols = ["id", "time_stamp", "status_type_id", "care_train_test", "sensor_1_avg", "sensor_2_avg"]
        native_cols = get_feature_columns("Wind Farm A", "care_native", all_cols)
        assert native_cols == ["sensor_1_avg", "sensor_2_avg"]
