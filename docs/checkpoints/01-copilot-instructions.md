---
task: repository Copilot instructions
phase: 1
status: complete
---

## What was built

- Added repository-level Copilot guidance covering verified Python and frontend commands.
- Documented the layered RAI architecture and API/UI contract boundary.
- Captured project-specific numerical honesty, evidence, safety, data, and checkpoint rules.

## Files

- `.github/copilot-instructions.md` — future-session instructions for architecture, commands, and conventions.
- `docs/checkpoints/01-copilot-instructions.md` — task record for this documentation change.

## How it was verified

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed.

## Measured results

91 tests passed; Ruff reported no violations.

## Limitations

The FastAPI application entrypoint is not implemented yet, so no API startup command is documented.

## Next

Implement the frozen FastAPI contract under `services/api/`.

