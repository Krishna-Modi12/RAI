---
task: reviewer-ready repository documentation
phase: 1
status: complete
---

## What was built

- Rebuilt the root README around the problem, architecture, reproducible demo, Phase 2 evaluation, and explicit implementation status.
- Added ML, evaluation, demo, API, limitations, and licensing guides plus contribution, security, and community-health files.
- Added deterministic `scripts/demo.py` and measured `scripts/evaluate.py` outputs under `artifacts/evaluation/`.
- Added GitHub pull-request and bug-report templates.

## Files

- `README.md` — reviewer-facing project entry point.
- `docs/ML.md`, `docs/EVALUATION.md`, `docs/DEMO.md`, `docs/LIMITATIONS.md`, `docs/API.md`, `docs/LICENSING.md` — supporting technical and reviewer guides.
- `scripts/demo.py`, `scripts/evaluate.py` — reproducible local demo and evaluation entry points.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/` — repository health and contribution guidance.
- `rai/agent/investigator.py` — allows the deterministic demo to disable the optional Needle probe explicitly.

## How it was verified

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed after the final import cleanup.
- `Set-Location web; npm run lint` — passed.
- `Set-Location web; npm run build` — passed with Next.js 16.3.5.
- `.venv\Scripts\python.exe scripts\evaluate.py` — wrote evaluation artifacts and reported 12/12 scenario agreement.
- `.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear` — completed the 8-stage deterministic investigation.
- Repository Markdown local-link check — 0 broken local links.
- Secret-pattern scan found only documentation/code references, no credential values.

## Measured results

The generated report contains eight expected-behaviour model metric sets and 12/12
scenario-level agreement against simulator equipment/non-equipment flags. These are
synthetic, controlled results and are not real-world validation.

## Limitations

Pyright is configured but is not installed in the checked-in virtual environment, so no
type-check result is claimed. The FastAPI route layer and browser dashboard remain in
progress.

## Next

Implement and test the frozen FastAPI contract, then connect the Next.js evidence-ledger
interface to it.

