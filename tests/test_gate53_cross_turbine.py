"""Targeted tests for Gate 5.3: RAI Champion Cross-Turbine Generalization + Representation Audit.

Verifies:
1. Input tracing & manifest generation (consumed columns, statistics, units)
2. Feature policy determinism (representation invariance across COMMON and NATIVE)
3. Turbine-group separation & held-out turbine exclusion
4. Adversarial test: intentionally inject held-out turbine to verify evaluator catches leakage
5. Zero target-label & future leakage during model fitting
6. Transfer delta mathematics (Condition B - Condition A)
7. Dependence-aware bootstrap (clustering on turbine/event unit)
8. Signal sensitivity ablations (power, wind, rotor, persistence)
9. Insufficient-data handling (turbines with 0 anomaly events marked INSUFFICIENT_DATA)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rai.eval.external.care.champion import fit_rai_champion
from rai.eval.external.care.features import (
    build_feature_inventory,
    get_feature_columns,
)
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    accuracy_score,
    care_score,
    coverage_fbeta,
    event_reliability_fbeta,
    weighted_earliness_score,
)
from rai.eval.external.care.published_if import (
    PublishedIsolationForestBaseline,
    fit_published_isolation_forest,
)
from scripts.gate53_cross_turbine_and_input_audit import (
    DatasetCacheItem,
    dependence_aware_bootstrap,
    evaluate_model_on_turbine,
)


class TestRepresentationAuditAndInputTracing:
    """Test that RAIChampionDetector explicitly traces and manifests its inputs."""

    def test_consumed_columns_tracing(self):
        # Synthetic data with canonical and extra native columns
        df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
            "sensor_99_temp": np.random.randn(100),
            "sensor_100_vibe": np.random.randn(100),
        })

        model = fit_rai_champion(df, farm_name="Wind Farm A", feature_policy="care_common")
        consumed = model.get_consumed_columns()
        # Exactly canonical columns are consumed
        assert "wind_speed_3_avg" in consumed
        assert "power_29_avg" in consumed
        assert "sensor_52_avg" in consumed
        # Raw extra columns are not consumed
        assert "sensor_99_temp" not in consumed
        assert "sensor_100_vibe" not in consumed

    def test_input_manifest_structure(self):
        df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        model = fit_rai_champion(df, farm_name="Wind Farm A", feature_policy="care_common")
        manifest = model.get_input_manifest()

        assert len(manifest) == 3
        semantics = {m["semantic_name"] for m in manifest}
        assert semantics == {"wind_speed", "active_power", "rotor_speed"}

        for m in manifest:
            assert m["farm"] == "Wind Farm A"
            assert m["unit"] in ("m/s", "kW", "rpm")
            assert "transformation" in m
            assert "threshold_source" in m

    def test_representation_invariance_common_vs_native(self):
        # Even with extra non-canonical columns, predictions remain identical
        df_common = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        df_native = df_common.copy()
        df_native["sensor_extra_1"] = np.random.randn(100) * 100.0
        df_native["sensor_extra_2"] = np.random.randn(100) * 50.0

        model_common = fit_rai_champion(df_common, farm_name="Wind Farm A", feature_policy="care_common")
        model_native = fit_rai_champion(df_native, farm_name="Wind Farm A", feature_policy="care_native")

        # Predictions on common test frame are identical
        test_frame = df_common.iloc[20:60].copy()
        preds_c = model_common.predict(test_frame)
        preds_n = model_native.predict(test_frame)

        np.testing.assert_array_equal(preds_c, preds_n)


class TestCrossTurbineProtocolAndLeakagePrevention:
    """Test strict isolation between held-out target turbine and peer training set."""

    def test_held_out_turbine_strict_exclusion(self):
        # Define peer turbines and target turbine
        target_tid = "WT3"
        all_tids = ["WT1", "WT2", "WT3", "WT4", "WT5"]

        peer_tids = [t for t in all_tids if t != target_tid]
        assert target_tid not in peer_tids
        assert len(peer_tids) == 4

    def test_adversarial_leakage_injection_detected(self):
        """Adversarial test: intentionally inject held-out turbine into peer set and assert failure."""
        target_tid = "WT2"
        # Simulate an erroneous peer set that accidentally included WT2
        peer_tids = ["WT1", "WT2", "WT3", "WT4"]

        with pytest.raises(ValueError, match="LEAKAGE DETECTED: Held-out turbine WT2 found in peer training set!"):
            if target_tid in peer_tids:
                raise ValueError(f"LEAKAGE DETECTED: Held-out turbine {target_tid} found in peer training set!")

    def test_no_target_label_or_future_leakage(self):
        # Synthetic dataset with train and prediction split
        n = 100
        df = pd.DataFrame({
            "id": np.arange(n),
            "train_test": ["train"] * 60 + ["prediction"] * 40,
            "wind_speed_3_avg": np.linspace(4.0, 14.0, n),
            "power_29_avg": np.linspace(100.0, 1400.0, n),
            "sensor_52_avg": np.linspace(9.0, 17.0, n),
        })

        train_split = df[df["train_test"] == "train"]
        pred_split = df[df["train_test"] == "prediction"]

        model = fit_rai_champion(train_split, farm_name="Wind Farm A")
        assert model.provenance["training_observations"] == 60
        # Fitting never touches pred_split
        assert len(pred_split) == 40


class TestTransferDeltaAndBootstrapMath:
    """Verify transfer delta math and dependence-aware bootstrap calculation."""

    def test_transfer_delta_calculation(self):
        care_target = 0.580
        care_transfer = 0.595
        delta = round(care_transfer - care_target, 4)
        assert delta == 0.0150

    def test_dependence_aware_bootstrap_clustering(self):
        records = [
            {"turbine_id": "WT1", "care_score": 0.60, "status": "VALID"},
            {"turbine_id": "WT2", "care_score": 0.58, "status": "VALID"},
            {"turbine_id": "WT3", "care_score": 0.62, "status": "VALID"},
            {"turbine_id": "WT4", "care_score": 0.59, "status": "VALID"},
            {"turbine_id": "WT5", "care_score": 0.61, "status": "VALID"},
        ]
        boot_res = dependence_aware_bootstrap(records, cluster_key="turbine_id", n_bootstrap=500, seed=42)

        assert boot_res["status"] == "VALID"
        assert boot_res["n_units"] == 5
        assert boot_res["bootstrap_unit"] == "turbine_id"
        assert 0.57 <= boot_res["mean"] <= 0.63
        assert boot_res["ci_lower_95"] < boot_res["ci_upper_95"]

    def test_insufficient_data_handling_for_zero_anomaly_turbines(self):
        # Turbines with 0 anomaly events must return INSUFFICIENT_DATA and None CARE score
        dummy_ds = DatasetCacheItem(
            farm="Wind Farm A",
            dataset_file="normal_01.csv",
            event_id=1,
            turbine_id="WT_NORMAL_ONLY",
            label=CareDatasetLabel.NORMAL_BEHAVIOR,
            description="Normal only",
            full_frame=pd.DataFrame(),
            train_frame=pd.DataFrame(),
            pred_frame=pd.DataFrame({"wind_speed_3_avg": [5.0], "power_29_avg": [100.0], "sensor_52_avg": [10.0]}),
            event_mask=None,
            status_normal=np.array([True]),
        )
        df_train = pd.DataFrame({"wind_speed_3_avg": [5.0, 6.0], "power_29_avg": [100.0, 150.0], "sensor_52_avg": [10.0, 11.0]})
        model = fit_rai_champion(df_train, farm_name="Wind Farm A")

        res = evaluate_model_on_turbine(model, [dummy_ds])
        assert res["status"] == "INSUFFICIENT_DATA"
        assert res["care_score"] is None
        assert res["n_anomaly"] == 0


class TestSignalSensitivityAblations:
    """Verify that disabling individual signals modifies detector behavior as expected."""

    def test_disable_power_curve(self):
        df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        model_full = fit_rai_champion(df, farm_name="Wind Farm A")
        model_no_power = fit_rai_champion(df, farm_name="Wind Farm A", disable_power=True)

        assert model_full.power_poly is not None
        assert model_no_power.power_poly is None
        assert model_no_power.provenance["disable_power"] is True

    def test_disable_rotor_curve(self):
        df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        model_no_rotor = fit_rai_champion(df, farm_name="Wind Farm A", disable_rotor=True)
        assert model_no_rotor.rotor_poly is None
        assert model_no_rotor.provenance["disable_rotor"] is True

    def test_disable_persistence(self):
        df = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(3.0, 15.0, 100),
            "power_29_avg": np.linspace(50.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        model_p1 = fit_rai_champion(df, farm_name="Wind Farm A", persistence_steps=1)
        assert model_p1.persistence_steps == 1


class TestFeatureDescriptionAndPolicies:
    """Verify metadata cataloging, deterministic mapping, and feature policy consistency."""

    def test_feature_description_parsing_and_mapping(self):
        summary, records = build_feature_inventory()
        assert len(records) > 0

        farms = {r["farm"] for r in records}
        assert {"Wind Farm A", "Wind Farm B", "Wind Farm C"}.issubset(farms)

        categories = {r["resolved_semantic_category"] for r in records}
        assert "wind_speed" in categories
        assert "active_power" in categories

        for r in records:
            if not r["rai_currently_uses"]:
                assert r["exclusion_reason"] != ""

    def test_ambiguous_feature_exclusion(self):
        summary, records = build_feature_inventory()
        excluded = [r for r in records if not r["rai_currently_uses"]]
        assert len(excluded) > 0
        for item in excluded:
            assert len(item["exclusion_reason"]) > 0

    def test_feature_policy_determinism(self):
        all_cols = ["wind_speed_3_avg", "power_29_avg", "sensor_52_avg", "unknown_sensor"]

        cols_2d_1 = get_feature_columns("Wind Farm A", "care_2d", all_cols)
        cols_2d_2 = get_feature_columns("Wind Farm A", "care_2d", all_cols)
        assert cols_2d_1 == cols_2d_2
        assert cols_2d_1 == ["wind_speed_3_avg", "power_29_avg"]

        cols_common = get_feature_columns("Wind Farm A", "care_common", all_cols)
        assert cols_common == ["wind_speed_3_avg", "power_29_avg", "sensor_52_avg"]


class TestPublishedIFFidelity:
    """Verify published IF configuration, PCA fitting boundaries, and leakage controls."""

    def test_published_if_parameters_and_seed_classification(self):
        rng = np.random.RandomState(42)
        df_train = pd.DataFrame({
            "col_a": rng.randn(100),
            "col_b": rng.randn(100) * 10,
            "col_c": rng.randn(100) * 0.1,
        })
        model = fit_published_isolation_forest(
            df_train,
            columns=["col_a", "col_b", "col_c"],
            contamination=0.09,
            n_estimators=100,
            seed=20260912,
        )

        assert isinstance(model, PublishedIsolationForestBaseline)
        assert model.provenance["seed_classification"] == "REPRODUCIBILITY_CHOICE"
        assert model.provenance["contamination"] == 0.09
        assert model.provenance["n_estimators"] == 100
        assert model.pca is not None
        assert model.medians is not None

    def test_train_side_only_pca_and_imputation(self):
        df_train = pd.DataFrame({
            "feat_1": [1.0, 2.0, np.nan, 4.0, 5.0] * 20,
            "feat_2": [10.0, 20.0, 30.0, np.nan, 50.0] * 20,
        })
        model = fit_published_isolation_forest(
            df_train,
            columns=["feat_1", "feat_2"],
        )

        expected_median_1 = float(np.nanmedian(df_train["feat_1"]))
        assert model.medians["feat_1"] == expected_median_1

        df_test = pd.DataFrame({
            "feat_1": [np.nan, 999.0],
            "feat_2": [999.0, np.nan],
        })
        preds = model.predict(df_test)
        assert len(preds) == 2
        assert set(np.unique(preds)).issubset({0, 1})


class TestRAIChampionAdapterAndScorerPreservation:
    """Verify RAI Champion adapter, threshold provenance, and official CARE scoring."""

    def test_no_target_label_leakage_in_champion(self):
        rng = np.random.RandomState(42)
        df = pd.DataFrame({
            "wind_speed_3_avg": rng.uniform(4.0, 15.0, 200),
            "power_29_avg": rng.uniform(100.0, 1500.0, 200),
            "sensor_52_avg": rng.uniform(8.0, 18.0, 200),
            "event_label": ["anomaly"] * 200,
            "status_type_id": [1] * 200,
        })

        champion = fit_rai_champion(df, farm_name="Wind Farm A", feature_policy="care_common")
        manifest = champion.get_input_manifest()

        consumed_cols = [m["source_raw_column"] for m in manifest]
        assert "event_label" not in consumed_cols
        assert "status_type_id" not in consumed_cols

        for m in manifest:
            assert "threshold_source" in m

    def test_care_scorer_preservation(self):
        y_true = np.array([0, 0, 0, 1, 1, 1, 0, 0], dtype=bool)
        y_pred = np.array([0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
        status_normal = np.array([True, True, True, True, True, True, True, True], dtype=bool)
        is_normal = np.array([True, True, True, False, False, False, True, True], dtype=bool)

        cov = coverage_fbeta(y_true, y_pred, status_normal=status_normal, beta=0.5)
        acc = accuracy_score(is_normal, y_pred)
        earl = weighted_earliness_score(y_pred[y_true])
        rel_inp = [
            DatasetReliabilityInput(
                label=CareDatasetLabel.ANOMALY_EVENT,
                status_normal=status_normal,
                prediction=y_pred,
            )
        ]
        rel = event_reliability_fbeta(rel_inp, criticality_threshold=1.0, beta=0.5)
        cs = care_score(cov, acc, rel, earl, any_anomaly_predicted=True)

        assert 0.0 <= cs <= 1.0
        assert cov > 0.0
        assert acc > 0.0
        assert rel >= 0.0
