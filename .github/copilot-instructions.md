# Copilot instructions for Renewable Asset Intelligence

## Project shape

RAI is a local-first predictive-maintenance system for wind and solar assets. The
pipeline is intentionally layered:

1. `rai/sim/` and `rai/ingest/` provide physics-simulated or normalized telemetry.
2. `rai/store/` reads parquet through DuckDB; `rai/features/` applies quality/state
   filters, creates residuals, windows, and compact evidence packets.
3. `rai/models/` predicts expected behavior and combines anomaly, peer, environmental,
   soiling, and risk evidence.
4. `rai/memory/`, `rai/rag/`, and `rai/economics/` provide historical cases,
   cited maintenance knowledge, and Python-computed intervention costs.
5. `rai/agent/` investigates only with an `EvidencePacket`, using Needle 2 when
   available and a deterministic reasoner otherwise; it returns an `AgentVerdict`.
6. `services/api/` is the backend boundary and `web/` is the Next.js operator UI.

The dependency direction is downward: schemas are dependency-free; `rai/agent` may
use memory/RAG/economics but not raw telemetry readers; `services/api` may import
the domain layers, but domain code must not import the API. The API/UI integration
contract is `docs/API_CONTRACT.md`; update both sides together if it changes.

## Commands

Run Python commands from the repository root with the checked-in virtual
environment:

```powershell
.venv\Scripts\python.exe -m pytest tests\ -q
.venv\Scripts\python.exe -m pytest tests\test_agent_reasoning.py -q
.venv\Scripts\python.exe -m pytest tests\test_agent_reasoning.py -k gearbox -q
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe scripts\generate_data.py
.venv\Scripts\python.exe scripts\train.py
.venv\Scripts\python.exe scripts\update_checkpoint.py
```

Frontend commands run from `web\`:

```powershell
npm run dev
npm run build
npm run lint
```

For frontend changes, this repository uses Next.js 16.3.5. Read the applicable
guidance under `web\node_modules\next\dist\docs\` before relying on older Next.js
APIs; `web\AGENTS.md` is generated and must be preserved.

## Non-negotiable domain rules

- Do not fabricate metrics, dataset statistics, risk values, or UI numbers. Uncomputed
  values are `null` and the UI must render them as “not evaluated”, not zero.
- Python computes residuals, risk, energy loss, and money. The LLM explains and decides;
  it does not perform consequential arithmetic.
- Raw telemetry and long time series never enter the LLM context. Only the compact,
  structured `EvidencePacket.to_agent_dict()` crosses that boundary.
- Never assert an equipment fault until environmental causes, curtailment, peer behavior,
  and sensor health have been checked. Curtailment, night, and below-cut-in are not
  anomalies.
- Agent confidence below `settings.needle_confidence_threshold` escalates to human
  review. The agent is read-only except for confirm-required inspection ticket creation;
  it never controls plant equipment.
- Use time-ordered telemetry splits, fit scalers on training data only, and keep
  thresholds/configuration in `rai/config.py` rather than model magic numbers.
- Preserve UTC, timezone-aware timestamps and the project units: INR, kWh, kW, °C;
  wind cadence is 10 minutes and solar cadence is 15 minutes.
- Asset IDs follow `WT-###`, `INV-###`, and `STR-###`.
- Do not add dependencies without recording them in the project’s technology
  documentation. Avoid generic dashboard UI; follow `docs/DESIGN.md`.

## Change workflow

Before editing, read `CHECKPOINT.md`, the relevant document in `docs\`, and the
existing implementation. Keep changes scoped and reuse the Pydantic contracts in
`rai\schemas.py`.

After a task, run the smallest relevant test or a real execution of the changed
path. Record the work in `docs\checkpoints\<nn>-<task-slug>.md` using
`docs\checkpoints\TEMPLATE.md`, then regenerate `CHECKPOINT.md` with
`scripts\update_checkpoint.py`; do not hand-edit the consolidated checkpoint.
