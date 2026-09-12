# Machine-learning and decision layers

This document explains what the current code actually computes. It is not a claim that
every planned subsystem is production-ready.

## Expected healthy behaviour

`rai/models/expected.py` pools healthy, productive windows by asset type, stops training
at the earliest injected fault onset, and uses chronological train/validation/test
boundaries. The current model family is XGBoost regression, with physics references kept
as interpretable baselines.

Outputs are expected values and residual baselines for monitored wind and solar signals.
The rest of the system reasons about residuals rather than raw output.

## Features and residuals

`rai/features/build.py` applies physical cleaning and operating-state classification,
then creates lagged/load/weather features. A residual contains actual value, expected
value, absolute and percentage difference, z-score, trend, and baseline spread.

The z-score is normalized against a healthy residual distribution, making temperature,
power, and vibration comparable for anomaly fusion.

## Anomaly fusion

`rai/models/anomaly.py` combines:

- residual-z thresholding;
- per-asset Isolation Forest models over residual features;
- change-point detection;
- persistence gating.

A single sample is not enough to create a maintenance conclusion. Detector scores and
thresholds remain visible in `AnomalyEvidence`.

## Environmental and peer attribution

`rai/models/environment.py` checks operating state, curtailment, weather explanation, and
sensor health. `rai/models/peers.py` compares the asset with its configured peer group.
An equipment conclusion is gated by both layers: shared fleet movement, curtailment,
weather, and failed/suspect sensors must not be reported as a drivetrain fault.

## Risk and economics

`rai/models/risk.py` produces a risk score and band with calibration metadata when a
fitted model is available. `rai/economics/engine.py` then computes intervention options
in Python. The agent receives finished options; it does not multiply probabilities or
costs itself.

## Historical memory and local reasoning

`rai/memory/retrieval.py` represents a packet as a trajectory signature and returns
similar project case-library entries. Similarity is evidence, not confidence.

`rai/agent/fallback.py` is a deterministic, auditable reasoner. `rai/agent/runtime.py`
optionally layers Needle 2 over the same contracts. The fallback is intentionally the
reproducible judge path when model weights or network access are unavailable.

## Implementation boundary

Implemented: the numerical layers above and their tests. Partial: local knowledge
retrieval and agent runtime integration. Planned/in progress: complete FastAPI endpoints,
frontend evidence ledger, external-dataset validation, and a full evaluation harness for
lead time, false alarms, and calibration.

