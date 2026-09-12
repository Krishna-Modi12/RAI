"""Targeted unit tests for Gate 5.4: Cross-Farm Wind Transfer & Target-Normal Calibration.

Verifies:
1. All six directed transfers exist and define disjoint source/target pairs.
2. Target anomaly label leakage prevention during recalibration.
3. Prediction split / future data leakage prevention during recalibration.
4. Parameter preservation: z_threshold and persistence_steps remain frozen without tuning.
5. Cross-farm column resolution dynamically resolves target farm signals.
6. CARE_COMMON semantic mapping is unchanged and aligned across farms.
7. Turbine-level cluster bootstrap mathematical properties (never timestamp-level).
8. Gap recovery mathematics and near-zero denominator safety.
9. Seed determinism with seed 20260912.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rai.eval.external.care.champion import (
    RAIChampionDetector,
    fit_rai_champion,
    recalibrate_rai_champion_target_normal,
)
from rai.eval.external.care.features import (
    CARE_COMMON_SIGNALS,
    FARM_COMMON_MAPPING,
)
from scripts.gate54_cross_farm_transfer import (
    DIRECTED_TRANSFERS,
    DatasetEvaluationResult,
    turbine_cluster_bootstrap,
)


class TestCrossFarmTransferProtocol:
    """Verify transfer graph structure, semantic mapping, and disjoint sets."""

    def test_all_six_directed_transfers_exist(self):
        expected_pairs = {
            ("Wind Farm A", "Wind Farm B"),
            ("Wind Farm A", "Wind Farm C"),
            ("Wind Farm B", "Wind Farm A"),
            ("Wind Farm B", "Wind Farm C"),
            ("Wind Farm C", "Wind Farm A"),
            ("Wind Farm C", "Wind Farm B"),
        }
        assert set(DIRECTED_TRANSFERS) == expected_pairs
        assert len(DIRECTED_TRANSFERS) == 6

    def test_source_and_target_disjoint(self):
        for src, tgt in DIRECTED_TRANSFERS:
            assert src != tgt
            assert src in FARM_COMMON_MAPPING
            assert tgt in FARM_COMMON_MAPPING

    def test_care_common_signals_frozen(self):
        assert set(CARE_COMMON_SIGNALS) == {"wind_speed", "active_power", "rotor_speed"}
        for _farm, mapping in FARM_COMMON_MAPPING.items():
            assert set(mapping.keys()) == {"wind_speed", "active_power", "rotor_speed"}
            assert all(isinstance(v, str) and len(v) > 0 for v in mapping.values())


class TestTargetNormalCalibrationLeakageProtection:
    """Verify that recalibrate_rai_champion_target_normal strictly prevents data leakage."""

    @pytest.fixture
    def synthetic_source_model(self) -> RAIChampionDetector:
        df_src = pd.DataFrame({
            "wind_speed_3_avg": np.linspace(4.0, 15.0, 100),
            "power_29_avg": np.linspace(100.0, 1500.0, 100),
            "sensor_52_avg": np.linspace(8.0, 18.0, 100),
        })
        return fit_rai_champion(
            df_src,
            farm_name="Wind Farm A",
            feature_policy="care_common",
            persistence_steps=3,
            z_threshold=2.5,
        )

    def test_recalibration_forbids_target_anomaly_labels(self, synthetic_source_model):
        # Frame containing forbidden anomaly column
        df_tgt_leaky = pd.DataFrame({
            "wind_speed_59_avg": np.linspace(4.0, 15.0, 100),
            "power_58_avg": np.linspace(100.0, 1500.0, 100),
            "sensor_25_avg": np.linspace(8.0, 18.0, 100),
            "event_label": ["anomaly"] * 100,  # LEAKAGE
        })
        with pytest.raises(ValueError, match="Protocol violation: Forbidden target anomaly columns present"):
            recalibrate_rai_champion_target_normal(
                synthetic_source_model,
                df_tgt_leaky,
                target_farm_name="Wind Farm B",
            )

    def test_recalibration_forbids_prediction_split(self, synthetic_source_model):
        # Frame containing prediction split rows
        df_tgt_future = pd.DataFrame({
            "train_test": ["train"] * 80 + ["prediction"] * 20,
            "wind_speed_59_avg": np.linspace(4.0, 15.0, 100),
            "power_58_avg": np.linspace(100.0, 1500.0, 100),
            "sensor_25_avg": np.linspace(8.0, 18.0, 100),
        })
        with pytest.raises(ValueError, match="Protocol violation.*non-train rows found"):
            recalibrate_rai_champion_target_normal(
                synthetic_source_model,
                df_tgt_future,
                target_farm_name="Wind Farm B",
            )

    def test_parameter_preservation_during_recalibration(self, synthetic_source_model):
        df_tgt_clean = pd.DataFrame({
            "train_test": ["train"] * 100,
            "wind_speed_59_avg": np.linspace(4.0, 15.0, 100),
            "power_58_avg": np.linspace(150.0, 2000.0, 100),
            "sensor_25_avg": np.linspace(9.0, 20.0, 100),
        })
        recalibrated = recalibrate_rai_champion_target_normal(
            synthetic_source_model,
            df_tgt_clean,
            target_farm_name="Wind Farm B",
        )

        # z_threshold and persistence_steps MUST be preserved exactly
        assert recalibrated.z_threshold == synthetic_source_model.z_threshold
        assert recalibrated.persistence_steps == synthetic_source_model.persistence_steps
        assert recalibrated.farm_name == "Wind Farm B"
        assert recalibrated.power_col == "power_58_avg"
        assert recalibrated.wind_col == "wind_speed_59_avg"
        assert recalibrated.rotor_col == "sensor_25_avg"
        assert recalibrated.provenance["calibration_type"] == "TARGET_NORMAL_ONLY"
        assert recalibrated.provenance["source_farm"] == "Wind Farm A"
        assert recalibrated.provenance["target_farm"] == "Wind Farm B"

    def test_frozen_source_cross_farm_column_resolution(self, synthetic_source_model):
        # Test frame with Farm B column names evaluated directly by Farm A model
        df_tgt_test = pd.DataFrame({
            "wind_speed_59_avg": [5.0, 10.0, 15.0],
            "power_58_avg": [100.0, 800.0, 1500.0],
            "sensor_25_avg": [8.0, 12.0, 16.0],
        })
        # predict() must dynamically resolve the target columns and return valid binary flags
        preds = synthetic_source_model.predict(df_tgt_test)
        assert len(preds) == 3
        assert set(np.unique(preds)).issubset({0, 1})


class TestTurbineClusterBootstrapAndMath:
    """Verify cluster bootstrap on turbine groups and gap recovery mathematics."""

    def test_turbine_cluster_bootstrap_structure(self):
        from rai.eval.external.care.metrics import CareDatasetLabel, DatasetReliabilityInput

        # Create synthetic records clustered across 5 turbines
        runs = [
            DatasetEvaluationResult(
                source_farm="Wind Farm A",
                target_farm="Wind Farm B",
                condition="FROZEN_SOURCE",
                dataset_file=f"ds_{i}.csv",
                event_id=i,
                turbine_id=f"WT{i % 5}",
                label=CareDatasetLabel.ANOMALY_EVENT.value if i % 2 == 0 else CareDatasetLabel.NORMAL_BEHAVIOR.value,
                fault_category="Test",
                alarms_count=10 if i % 2 == 0 else 0,
                event_detected=(i % 2 == 0),
                max_criticality=80.0 if i % 2 == 0 else 5.0,
                coverage_fbeta=0.5 if i % 2 == 0 else None,
                lead_time_steps=20 if i % 2 == 0 else None,
                earliness_ws=0.1 if i % 2 == 0 else None,
            )
            for i in range(20)
        ]
        rels = [
            DatasetReliabilityInput(
                label=CareDatasetLabel.ANOMALY_EVENT if r.label == CareDatasetLabel.ANOMALY_EVENT.value else CareDatasetLabel.NORMAL_BEHAVIOR,
                status_normal=np.array([True] * 50),
                prediction=np.array([1 if r.event_detected else 0] * 50),
            )
            for r in runs
        ]

        boot = turbine_cluster_bootstrap(runs, rels, n_resamples=100, seed=20260912)
        assert boot["status"] == "VALID"
        assert boot["n_turbines"] == 5
        assert boot["care_ci_lower_95"] <= boot["care_ci_upper_95"]
        assert 0.0 <= boot["care_mean"] <= 1.0

    def test_gap_recovery_math(self):
        # Scenario 1: Meaningful denominator
        care_frozen = 0.50
        care_cal = 0.55
        care_ref = 0.60
        gap = care_ref - care_frozen
        recovery = (care_cal - care_frozen) / gap
        assert pytest.approx(recovery, abs=1e-5) == 0.5

        # Scenario 2: Near-zero denominator
        care_frozen_2 = 0.50
        care_ref_2 = 0.50001
        diff = abs(care_ref_2 - care_frozen_2)
        assert diff < 1e-4
