# GATE_5.6_INVALID_SYNTHETIC_RUN

**This directory preserves, for audit history, a Gate 5.6 result that has been formally
invalidated.** It must never be cited as PVDAQ validation, external solar validation,
physics-model accuracy, or RAI Solar Champion performance. See `invalidation_manifest.json`
for the full structured record (`reason_invalid`, `synthetic_data_detected`,
`circular_validation_detected`, `affected_claims`, `affected_metrics`, `replacement_protocol`).

## What happened (scientific history, not something to hide)

```
Gate 5.5 (solar source audit)                                          PASS
   |
Gate 5.6 attempted by Builder agent                                    (produced this snapshot)
   |
Scientific audit discovered undisclosed synthetic "PVDAQ" telemetry    see gate56_audit/
   |
Physics-vs-generator formula comparison found circularity              gate56_scientific_audit_verdict.md
   |
Gate 5.6 marked INVALID (this directory)                                <- you are here
   |
Clean restart per RAI Gate 5.6 Clean Restart master prompt              in progress
```

This is exactly the kind of failure the project's Gate 5.0 claim-integrity system exists to
catch, and catching it before it was cited elsewhere is a correct audit outcome, not a project
setback.

## Why this was invalidated (short version)

1. **Undisclosed synthetic data.** `rai/eval/external/solar/pvdaq.py::generate_pvdaq_telemetry()`
   (snapshotted in `code_snapshot_at_audit_time/pvdaq.py`) fabricated every telemetry value using
   pvlib's own clear-sky/transposition/thermal functions plus a hand-rolled cloud-cover Markov
   process. No real PVDAQ file was ever downloaded (`data/raw/` had no `pvdaq/` directory at
   audit time). The artifacts in this snapshot present the result as real NREL PVDAQ telemetry
   with no synthetic-data disclosure anywhere.
2. **Circular validation.** `PVLibPhysicsReference.predict()` (snapshotted in
   `code_snapshot_at_audit_time/models.py`) uses a formula that is line-for-line identical to the
   one used to generate the synthetic "actual" power it was scored against — so its reported
   R² ≈ 0.999 measures nothing about real-world physics modeling; it measures the model
   recovering its own generating function.

## What is preserved here

- A full snapshot of `artifacts/evaluation/gate56/*.{csv,json,md}` as it existed at audit time,
  before the clean restart could overwrite the same file paths.
- The two offending source files (`pvdaq.py`, `models.py`) as they stood at audit time — the live
  copies under `rai/eval/external/solar/` may since have been rewritten by the restart.

## What is not preserved here (and why that's fine)

The three-model architectural shape (physics reference / empirical baseline / hybrid Champion),
the quality-filter tagging logic, and the Champion's residual/persistence fusion logic are not
shown to be wrong by this audit — see `invalidation_manifest.json`'s `not_affected` field. That
scaffolding may be reused in the clean restart once it is fed real telemetry.

## Full audit trail

- `../gate56_audit/audit_protocol.md` — the pre-registered audit rubric written before any
  Gate 5.6 result existed.
- `../gate56_audit/gate56_scientific_audit_verdict.md` — the full verdict with line-by-line
  formula comparison and the live network reachability test of the OEDI S3 bucket.
- `invalidation_manifest.json` (this directory) — the structured invalidation record.
