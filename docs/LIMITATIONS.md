# Limitations and non-claims

## Data

The primary evaluation spine is synthetic. It is physics-grounded and carries exact
injected-event labels, which makes controlled testing possible, but its generator is
simpler than a live SCADA fleet. Results do not transfer automatically to another OEM,
site, climate, sensor configuration, or failure distribution.

External dataset adapters and research references are documented in
[DATASETS.md](DATASETS.md), but an adapter or citation is not the same as a measured
experiment.

## Models

Expected behaviour is learned from a limited simulated horizon. The risk and economic
layers inherit their assumptions. A fallback confidence value measures agreement among
rules and evidence; it is not a calibrated probability of failure.

## Agent

Needle 2 is optional and may be unavailable when local weights cannot be downloaded. The
deterministic fallback is the honest reproducibility path. Neither path is permitted to
control plant equipment.

## Product integration

The frozen REST contract exists, but the FastAPI routes and browser evidence-ledger
experience are not complete. Current command-line demonstrations should not be described
as a deployed production service.

## Economics

INR outputs depend on configured tariffs, capacity factors, intervention costs, downtime,
and hazard assumptions. They are decision-support estimates and must be reviewed against
site-specific contracts and maintenance records.

