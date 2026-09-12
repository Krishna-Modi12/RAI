"""Unit tests for the official CARE score (Gück, Roelofs & Faulstich, 2024), equations 1-5.

Each test checks one formula against a hand-computed expectation, and a final pair of tests
reproduce the paper's own qualitative claim that the "all anomaly" and "all normal" trivial
strategies both score CARE = 0 (section 4.2.3) - useful as an end-to-end sanity check that
the pieces compose the way the paper says they do, independent of any real CARE data.
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


def test_coverage_fbeta_matches_hand_computation():
    # 4 normal-status points: ground truth [1,1,0,0], prediction [1,0,0,1] -> tp=1, fn=1, fp=1
    g = np.array([1, 1, 0, 0])
    p = np.array([1, 0, 0, 1])
    status_normal = np.array([True, True, True, True])
    beta = 0.5
    b2 = beta * beta
    expected = (1 + b2) * 1 / ((1 + b2) * 1 + b2 * 1 + 1)
    assert coverage_fbeta(g, p, status_normal) == pytest.approx(expected)


def test_coverage_fbeta_ignores_abnormal_status_points():
    # The abnormal-status point (index 2) has a wrong prediction but must be excluded.
    g = np.array([1, 0, 1])
    p = np.array([1, 0, 0])
    status_normal = np.array([True, True, False])
    # Only indices 0,1 count: tp=1, fp=0, fn=0 -> Fbeta = 1.0
    assert coverage_fbeta(g, p, status_normal) == pytest.approx(1.0)


def test_accuracy_score_matches_hand_computation():
    # 5 normal-status points, predictions: [0,0,1,0,1] -> fp=2, tn=3
    p = np.array([0, 0, 1, 0, 1])
    status_normal = np.array([True, True, True, True, True])
    assert accuracy_score(p, status_normal) == pytest.approx(3 / 5)


def test_accuracy_score_perfect_and_zero():
    status_normal = np.array([True, True, True])
    assert accuracy_score(np.array([0, 0, 0]), status_normal) == pytest.approx(1.0)
    assert accuracy_score(np.array([1, 1, 1]), status_normal) == pytest.approx(0.0)


def test_criticality_series_algorithm_1_hand_trace():
    # abnormal, abnormal, abnormal, normal, abnormal, abnormal
    status_normal = np.array([False, False, False, True, False, False])
    # predictions during abnormal points: hit, hit, miss, (frozen), hit, miss
    prediction = np.array([1, 1, 0, 0, 1, 0])
    crit = criticality_series(status_normal, prediction)
    # i0: abnormal+hit -> 1 ; i1: abnormal+hit -> 2 ; i2: abnormal+miss -> max(2-1,0)=1
    # i3: normal -> frozen at 1 ; i4: abnormal+hit -> 2 ; i5: abnormal+miss -> 1
    assert list(crit) == [1, 2, 1, 1, 2, 1]


def test_criticality_never_goes_negative():
    status_normal = np.array([False, False, False])
    prediction = np.array([0, 0, 0])
    crit = criticality_series(status_normal, prediction)
    assert list(crit) == [0, 0, 0]


def test_event_reliability_fbeta_threshold_behaviour():
    # One anomaly-event dataset that clears a low threshold, one normal dataset that doesn't
    # falsely clear it, scored together.
    event_ds = DatasetReliabilityInput(
        label=CareDatasetLabel.ANOMALY_EVENT,
        status_normal=np.array([False, False, False]),
        prediction=np.array([1, 1, 1]),  # criticality reaches 3
    )
    normal_ds = DatasetReliabilityInput(
        label=CareDatasetLabel.NORMAL_BEHAVIOR,
        status_normal=np.array([False, False, False]),
        prediction=np.array([0, 0, 0]),  # criticality stays 0
    )
    score = event_reliability_fbeta([event_ds, normal_ds], criticality_threshold=3.0)
    # g=[1,0], p=[1,0] -> tp=1, fp=0, fn=0 -> perfect Fbeta = 1.0
    assert score == pytest.approx(1.0)


def test_event_reliability_fbeta_false_alarm_penalised():
    # A normal dataset whose criticality accidentally clears the threshold is a false alarm.
    false_alarm_ds = DatasetReliabilityInput(
        label=CareDatasetLabel.NORMAL_BEHAVIOR,
        status_normal=np.array([False, False]),
        prediction=np.array([1, 1]),  # criticality reaches 2, clears threshold=2
    )
    score = event_reliability_fbeta([false_alarm_ds], criticality_threshold=2.0)
    # g=[0], p=[1] -> tp=0, fp=1, fn=0 -> Fbeta = 0.0
    assert score == pytest.approx(0.0)


def test_weighted_earliness_full_detection_scores_one():
    assert weighted_earliness_score(np.array([1, 1, 1, 1, 1])) == pytest.approx(1.0)


def test_weighted_earliness_zero_detection_scores_zero():
    assert weighted_earliness_score(np.array([0, 0, 0, 0, 0])) == pytest.approx(0.0)


def test_weighted_earliness_favours_early_detection():
    n = 10
    early = np.zeros(n)
    early[:3] = 1  # detections only in the first half (weight 1.0 there)
    late = np.zeros(n)
    late[-3:-1] = 1  # same count, but in the decaying second half
    assert weighted_earliness_score(early) > weighted_earliness_score(late)


def test_weighted_earliness_detection_at_the_very_end_scores_zero():
    n = 10
    at_fault_onset = np.zeros(n)
    at_fault_onset[-1] = 1  # relative position exactly 1.0 -> weight exactly 0
    assert weighted_earliness_score(at_fault_onset) == pytest.approx(0.0)


def test_care_score_all_normal_strategy_scores_zero():
    # "all normal": never predicts an anomaly anywhere.
    assert care_score(
        mean_coverage_fbeta=0.0, mean_earliness_ws=0.0, event_reliability=0.0,
        mean_accuracy=1.0, any_anomaly_predicted=False,
    ) == pytest.approx(0.0)


def test_care_score_all_anomaly_strategy_scores_zero():
    # "all anomaly": predicts anomaly everywhere, so accuracy on normal-behavior datasets is 0.
    assert care_score(
        mean_coverage_fbeta=1.0, mean_earliness_ws=1.0, event_reliability=1.0,
        mean_accuracy=0.0, any_anomaly_predicted=True,
    ) == pytest.approx(0.0)


def test_care_score_weighted_average_when_above_accuracy_floor():
    score = care_score(
        mean_coverage_fbeta=0.8, mean_earliness_ws=0.6, event_reliability=0.7,
        mean_accuracy=0.9, any_anomaly_predicted=True,
    )
    expected = (1.0 * 0.8 + 1.0 * 0.6 + 1.0 * 0.7 + 2.0 * 0.9) / 5.0
    assert score == pytest.approx(expected)
