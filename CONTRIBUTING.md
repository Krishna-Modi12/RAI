# Contributing

## Before changing code

Read `CHECKPOINT.md`, the relevant document in `docs/`, and the existing implementation.
Keep changes within the requested scope and preserve the frozen contracts in
`rai/schemas.py` and `docs/API_CONTRACT.md`.

## Local checks

```powershell
.venv\Scripts\python.exe -m pytest tests\ -q
.venv\Scripts\ruff.exe check .
Set-Location web
npm run lint
npm run build
```

For telemetry, use chronological splits and never train on a window containing the
injected fault. For agent changes, preserve the raw-telemetry boundary and structured
`AgentVerdict` output.

## Documentation and checkpoints

Record completed work in `docs/checkpoints/<nn>-<task-slug>.md` using
`docs/checkpoints/TEMPLATE.md`, then run:

```powershell
.venv\Scripts\python.exe scripts\update_checkpoint.py
```

Do not hand-edit the consolidated checkpoint while another task may update it.

