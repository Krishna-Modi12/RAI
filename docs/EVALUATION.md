# Evaluation

## What is evaluated today

The repository currently evaluates two different things:

1. **Physics and software invariants** in `tests/test_sim_physics.py`,
   `tests/test_store.py`, and the other test modules.
2. **A reproducible local model/reasoner report** from `scripts/evaluate.py`.

The primary data source is the RAI physics simulator. Its injected events are ground
truth for this controlled experiment. Results from this source must not be described as
real-plant accuracy.

## Reproduce

```powershell
.venv\Scripts\python.exe scripts\generate_data.py
.venv\Scripts\python.exe scripts\evaluate.py --retrain
```

Outputs:

```text
artifacts/evaluation/results.json
artifacts/evaluation/summary.md
```

The JSON contains the computation timestamp, data source, model metrics, split
descriptions, and per-scenario reasoner decisions. It is generated rather than hand
edited.

## Split policy

Expected-behaviour training uses healthy productive windows and chronological
train/validation/test boundaries. It does not use random shuffling. Fault onset is used
as the healthy cutoff so the normal-behaviour model does not train on its target fault.

The current scenario check compares the deterministic reasoner’s equipment/non-equipment
classification with `InjectedEvent.is_equipment_fault`. It is a scenario agreement
measure, not a production precision/recall estimate.

## Metrics

The evaluator reports the metrics produced by the training implementation:

- MAE and RMSE in each model’s native unit;
- R² on the chronological test portion;
- number of train/test rows;
- scenario-level equipment/non-equipment agreement.

Metrics that are not computed are absent or `null`; they must not be filled with plausible
placeholders. The future evaluation surface should add event recall, precision, lead
time, false alarms per asset-month, risk calibration, and agent schema/unsupported-claim
rates only when an executable implementation produces them.

## What a reviewer should conclude

The current results establish that the code can generate physically constrained telemetry,
train on a leakage-aware healthy prefix, and execute a deterministic evidence chain. They
do not establish performance on CARE, Indian solar data, or live SCADA. Those datasets
and transfer experiments remain future validation work unless a dated artifact says
otherwise.

