---
task: kelmarsh-benchmark-research
phase: 5
status: partial
---

## What was built

- Recorded the first bounded research decision for the independent wind benchmark route.
- Added a source-backed claim boundary: Kelmarsh is real operational SCADA plus event data, not yet confirmed component-failure ground truth.
- Added the next executable experiment: version-pinned acquisition, event-code taxonomy, and adjudication before detector fitting.

## Files

- `docs/RESEARCH_REGISTRY.md` — research question, sources, findings, decision, and status.
- `docs/CLAIMS.md` — prevents unsupported Kelmarsh validation claims.
- `docs/checkpoints/30-kelmarsh-benchmark-research.md` — this record.

## How it was verified

Reviewed the official Zenodo dataset record and the OpenWindSCADA inventory README on 2026-09-13. No model or benchmark was run.

## Measured results

Not evaluated. No detector was fit and no validation metric was produced.

## Limitations

The public sources establish dataset contents and the absence of a public label column in the inventory, but they do not independently adjudicate every event code. The next task must perform that event-semantic audit before using Kelmarsh for validation.

## Next

Acquire a version-pinned Kelmarsh release and produce an event taxonomy separating fault, maintenance, environmental, sensor, and unknown events.
