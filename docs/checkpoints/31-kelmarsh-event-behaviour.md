---
task: kelmarsh-event-behaviour
phase: 5
status: partial
---

## What was built

- Acquired and checksum-verified the pinned official Kelmarsh 2019 SCADA release.
- Audited 299 SCADA columns and 59,326 status records across six turbines.
- Implemented a bounded event/behaviour benchmark with a three-signal feature policy,
  causal chronological split, statistical z-score, Isolation Forest, and RAI Champion.
- Explicitly excluded environmental, electrical, technical-standby, communication, and
  unknown records from event evaluation; no event was called a failure.

## Files

- `rai/eval/external/kelmarsh/benchmark.py` — reproducible benchmark runner.
- `tests/test_kelmarsh_event_behaviour.py` — taxonomy and event-window regression tests.
- `docs/evaluation/KELMARSH_EVENT_BEHAVIOUR.md` — methodology, results, and limits.
- `docs/RESEARCH_REGISTRY.md` — experiment `RAI-WIND-002`.
- `docs/CLAIMS.md` — bounded public claim.
- `artifacts/evaluation/kelmarsh_event_behaviour/` — manifest, audit, windows, results.

## How it was verified

- `.venv\\Scripts\\python.exe -m rai.eval.external.kelmarsh.benchmark` — completed with status `PARTIAL`.
- `.venv\\Scripts\\ruff.exe check rai\\eval\\external\\kelmarsh` — all checks passed.
- `.venv\\Scripts\\python.exe -m pytest tests\\test_kelmarsh_event_behaviour.py tests\\test_external_care_adapter.py tests\\test_external_care_metrics.py -q` — expected 21 tests.

## Measured results

92 test-period operational windows: 71 forced outage and 21 scheduled maintenance.
Event coverage was 1.1% for statistical z-score, 47.8% for Isolation Forest, and
81.5% for RAI Champion. Outside-window flag rates were 0.46%, 0.32%, and 1.11%.

## Limitations

Status/event records are not independently adjudicated component-failure ground truth.
The result is temporal association only; it does not establish causation or failure
prediction. It covers one site and one year.

## Next

Do not automatically start another benchmark. Reassess the roadmap; the highest-value
next task is likely historical case/RAG evidence quality or local-agent tool/evidence
evaluation, not another unsupported validation claim.
