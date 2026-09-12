"""Gate 5.2 CARE Scorer Mathematical Audit Test Suite.

Rigorously verifies the official CARE evaluation equations from Gück, Roelofs & Faulstich (2024):
- Coverage (Eq. 1): Pointwise F_beta on normal-status points of anomaly datasets
- Accuracy (Eq. 2): tn / (fp + tn) on normal-status points of normal-behavior datasets
- Reliability (Algorithm 1 + Eq. 1): Event-level F_beta over criticality exceedance threshold
- Earliness (Eq. 3, Fig. 1): Weighted sum decaying linearly from 1.0 at midpoint to 0.0 at end
- CARE Aggregation (Eq. 4-5): Trivial baseline floors and weighted score aggregation
"""

from __future__ import annotations

import numpy as np
import pytest

from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    accuracy_score,
    care_score,
    coverage_fbeta,
    criticality_series,
    event_reliability_fbeta,
    weighted_earliness_score,
)


class TestCareCoverageFBeta:
    """Audit Eq. 1 Coverage."""

    def test_perfect_coverage(self):
        """When all ground truth anomalies on normal-status points are predicted, Coverage=1.0."""
        gt = np.array([1, 1, 1, 0, 0])
        pred = np.array([1, 1, 1, 0, 0])
        status_norm = np.array([True, True, True, True, True])
        assert coverage_fbeta(gt, pred, status_norm, beta=0.5) == pytest.approx(1.0)

    def test_zero_positives_predicted_when_anomalies_exist(self):
        """When ground truth has anomalies but none are predicted, Coverage=0.0."""
        gt = np.array([1, 1, 0, 0])
        pred = np.array([0, 0, 0, 0])
        status_norm = np.array([True, True, True, True])
        # tp=0, fp=0, fn=2 -> denom = 0 + 0.25*2 + 0 = 0.5 -> 0.0
        assert coverage_fbeta(gt, pred, status_norm, beta=0.5) == pytest.approx(0.0)

    def test_abnormal_status_points_strictly_ignored(self):
        """Points where status is abnormal (status_normal=False) are ignored per Table 3.3 / Eq. 1."""
        gt = np.array([1, 1, 0, 1])
        pred = np.array([1, 0, 0, 0])  # index 3 would be a false negative if counted
        status_norm = np.array([True, True, True, False])  # index 3 ignored
        # Masked: gt=[1, 1, 0], pred=[1, 0, 0] -> tp=1, fp=0, fn=1
        # beta=0.5 -> b2=0.25 -> (1.25 * 1) / (1.25 * 1 + 0.25 * 1 + 0) = 1.25 / 1.5 = 5/6
        expected = (1.25 * 1) / (1.25 * 1 + 0.25 * 1 + 0)
        assert coverage_fbeta(gt, pred, status_norm, beta=0.5) == pytest.approx(expected)

    def test_no_positives_present_or_predicted(self):
        """When both ground truth and predictions are empty or all-zero, returns 1.0 by convention."""
        gt = np.array([0, 0, 0])
        pred = np.array([0, 0, 0])
        status_norm = np.array([True, True, True])
        assert coverage_fbeta(gt, pred, status_norm, beta=0.5) == pytest.approx(1.0)


class TestCareAccuracyScore:
    """Audit Eq. 2 Accuracy."""

    def test_perfect_accuracy(self):
        """Zero false alarms on normal dataset yields Accuracy=1.0."""
        pred = np.array([0, 0, 0, 0])
        status_norm = np.array([True, True, True, True])
        assert accuracy_score(pred, status_norm) == pytest.approx(1.0)

    def test_all_false_alarms(self):
        """Predicting anomaly on every normal-status point yields Accuracy=0.0."""
        pred = np.array([1, 1, 1])
        status_norm = np.array([True, True, True])
        assert accuracy_score(pred, status_norm) == pytest.approx(0.0)

    def test_accuracy_masks_abnormal_status(self):
        """False alarm during abnormal status does not penalize normal accuracy."""
        pred = np.array([0, 1, 0])  # index 1 has an alarm
        status_norm = np.array([True, False, True])  # index 1 ignored
        assert accuracy_score(pred, status_norm) == pytest.approx(1.0)


class TestCareCriticalityAlgorithm1:
    """Audit Algorithm 1 Criticality Series."""

    def test_criticality_increments_only_during_abnormal_status(self):
        """Criticality increments on hit during abnormal status, decrements on miss, freezes on normal."""
        status_norm = np.array([False, False, True, False, False])
        pred = np.array([1, 1, 1, 0, 1])
        # step 0: abnormal + pred=1 -> 1
        # step 1: abnormal + pred=1 -> 2
        # step 2: normal -> frozen at 2
        # step 3: abnormal + pred=0 -> max(2-1, 0) = 1
        # step 4: abnormal + pred=1 -> 2
        crit = criticality_series(status_norm, pred)
        assert list(crit) == [1, 2, 2, 1, 2]

    def test_criticality_bounded_below_by_zero(self):
        status_norm = np.array([False, False, False])
        pred = np.array([0, 0, 0])
        crit = criticality_series(status_norm, pred)
        assert (crit == 0).all()


class TestCareEventReliability:
    """Audit Event-Level Reliability EF_beta."""

    def test_reliability_single_event_detected(self):
        """Anomaly dataset exceeds criticality threshold, normal dataset stays below -> Reliability=1.0."""
        ds_anom = DatasetReliabilityInput(
            label=CareDatasetLabel.ANOMALY_EVENT,
            status_normal=np.array([False] * 10),
            prediction=np.array([1] * 10),  # crit reaches 10
        )
        ds_norm = DatasetReliabilityInput(
            label=CareDatasetLabel.NORMAL_BEHAVIOR,
            status_normal=np.array([False] * 10),
            prediction=np.array([0] * 10),  # crit stays 0
        )
        score = event_reliability_fbeta([ds_anom, ds_norm], criticality_threshold=5.0, beta=0.5)
        assert score == pytest.approx(1.0)

    def test_reliability_false_alarm_on_normal_penalizes(self):
        """Normal dataset clearing criticality threshold counts as false positive."""
        ds_norm_fa = DatasetReliabilityInput(
            label=CareDatasetLabel.NORMAL_BEHAVIOR,
            status_normal=np.array([False] * 10),
            prediction=np.array([1] * 10),  # crit reaches 10 >= 5 -> false alarm
        )
        score = event_reliability_fbeta([ds_norm_fa], criticality_threshold=5.0, beta=0.5)
        # g=[0], p=[1] -> tp=0, fp=1, fn=0 -> 0.0
        assert score == pytest.approx(0.0)


class TestCareWeightedEarliness:
    """Audit Eq. 3 Weighted Earliness (WS)."""

    def test_earliness_full_duration_detection(self):
        """Predicting anomaly across the entire event window yields WS=1.0."""
        pred = np.ones(20)
        assert weighted_earliness_score(pred) == pytest.approx(1.0)

    def test_earliness_first_half_vs_second_half(self):
        """Detections in first half get weight 1.0; second half decays linearly."""
        m = 11  # indices 0 to 10
        # rel positions: 0.0, 0.1, 0.2, 0.3, 0.4, 0.5 (weight=1.0), 0.6 (0.8), 0.7 (0.6), 0.8 (0.4), 0.9 (0.2), 1.0 (0.0)
        pred_early = np.zeros(m)
        pred_early[0:2] = 1.0  # weight 1.0 each

        pred_late = np.zeros(m)
        pred_late[9:11] = 1.0  # weights 0.2 and 0.0

        assert weighted_earliness_score(pred_early) > weighted_earliness_score(pred_late)

    def test_earliness_at_exact_event_end_scores_zero(self):
        """A single alarm at the exact final index (rel=1.0) has weight=0.0."""
        pred = np.zeros(10)
        pred[-1] = 1.0
        assert weighted_earliness_score(pred) == pytest.approx(0.0)

    def test_earliness_empty_window(self):
        assert weighted_earliness_score(np.array([])) == pytest.approx(0.0)


class TestCareScoreAggregation:
    """Audit Eq. 4-5 CARE Aggregation Rules."""

    def test_care_rule_1_zero_anomalies_predicted_scores_zero(self):
        """Paper Rule 1: If zero anomalies predicted anywhere across evaluation, CARE=0."""
        assert care_score(
            mean_coverage_fbeta=0.9,
            mean_earliness_ws=0.9,
            event_reliability=0.9,
            mean_accuracy=0.99,
            any_anomaly_predicted=False,
        ) == pytest.approx(0.0)

    def test_care_rule_2_accuracy_below_random_floor(self):
        """Paper Rule 2: If mean accuracy < 0.5 (worse than random guessing on normal data), CARE = accuracy."""
        assert care_score(
            mean_coverage_fbeta=0.9,
            mean_earliness_ws=0.9,
            event_reliability=0.9,
            mean_accuracy=0.42,
            any_anomaly_predicted=True,
        ) == pytest.approx(0.42)

    def test_care_rule_3_weighted_average(self):
        """Paper Rule 3: Normal weighted average: (Coverage + Earliness + Reliability + 2*Accuracy) / 5."""
        cov = 0.6
        ear = 0.4
        rel = 0.8
        acc = 0.7
        expected = (1.0 * cov + 1.0 * ear + 1.0 * rel + 2.0 * acc) / 5.0
        assert care_score(
            mean_coverage_fbeta=cov,
            mean_earliness_ws=ear,
            event_reliability=rel,
            mean_accuracy=acc,
            any_anomaly_predicted=True,
        ) == pytest.approx(expected)
