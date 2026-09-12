"""Official CARE-to-Compare benchmark scoring (Gück, Roelofs & Faulstich, 2024).

Reference: "CARE to Compare: A real-world dataset for anomaly detection in wind turbine
data", arXiv:2404.10320 / Data 9(12):138, 2024. Dataset: Zenodo record 14006163 (a corrected
later version of the original 10958775 deposit), CC-BY-SA-4.0.

This package implements the paper's own CARE score exactly as published (equations 1-5,
Algorithm 1) rather than RAI's internal "CARE-inspired" operational score
(`rai.eval.metrics.compute_care_score`) - the two are deliberately kept separate so a number
produced here can be compared to the paper's own mini-benchmark figures (all-anomaly=0,
all-normal=0, random=0.5, isolation-forest=0.14, autoencoder=0.66 on the full 95-dataset
collection).
"""

from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    accuracy_score,
    care_score,
    coverage_fbeta,
    criticality_series,
    event_reliability_fbeta,
    weighted_earliness_score,
)

__all__ = [
    "CareDatasetLabel",
    "accuracy_score",
    "care_score",
    "coverage_fbeta",
    "criticality_series",
    "event_reliability_fbeta",
    "weighted_earliness_score",
]
