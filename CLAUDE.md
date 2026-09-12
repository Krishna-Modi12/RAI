# Renewable Asset Intelligence (RAI)

Local-first predictive-maintenance intelligence for wind and solar assets. The system
turns raw telemetry into an **evidence-backed maintenance decision**: it detects abnormal
behaviour, separates equipment degradation from environmental causes, retrieves similar
historical failures, quantifies the economic consequence, and recommends an action.

## The one-sentence product

> We turn renewable-farm telemetry into an evidence-backed maintenance decision before a
> small anomaly becomes an expensive failure.

## Repository map

| Path | Owner | Contents |
|---|---|---|
| `rai/sim/` | data | Physics-grounded telemetry simulator + fault injection (ground truth) |
| `rai/ingest/` | data | Real-dataset adapters (CARE, Kaggle solar, NASA POWER) |
| `rai/features/` | ml | Feature engineering, residual construction, windowing |
| `rai/models/` | ml | Expected-behaviour models, anomaly detectors, risk model |
| `rai/memory/` | ml | Historical failure-case retrieval (trajectory kNN) |
| `rai/economics/` | ml | Expected-loss and intervention comparison |
| `rai/rag/` | rag | Document ingestion, SQLite FTS5 + optional dense retrieval |
| `rai/agent/` | agent | Needle 2 runtime, tool registry, output schemas, fallback |
| `rai/eval/` | ml | Metrics, split policy, leakage checks |
| `services/api/` | backend | FastAPI application |
| `web/` | frontend | Next.js operator interface |
| `knowledge/` | rag | Curated maintenance corpus (clearly-labelled sample documents) |
| `docs/` | shared | PRD, architecture, datasets, ML plan, design, evaluation |

## Non-negotiable rules

**Numerical honesty**
- Never fabricate a metric. If a model has not been evaluated, the value is `null`, not a
  plausible-looking number. Every number shown in the UI traces to a computed artifact.
- Never fabricate dataset statistics. Cite the loader output, not a remembered figure.
- The LLM never computes arithmetic that matters. Risk scores, residuals, energy loss and
  money are computed in Python and *handed to* the agent. The agent only explains and decides.

**Evidence discipline**
- No alert without evidence. Every recommendation carries the residuals, peer comparison,
  environmental check, historical matches and knowledge citations that produced it.
- An environmental explanation must be ruled out before an equipment fault is asserted.
  Low output is not a fault until weather, curtailment, peers and sensor health are checked.
- Agent confidence below threshold escalates to human review. It never guesses.

**Safety**
- The agent has read-only tools plus ticket creation. It never issues physical control commands.
- Raw telemetry is never streamed into the LLM context. Only structured evidence packets.

**Engineering**
- Time-ordered splits only. Never `shuffle=True` on telemetry. Scalers fit on train only.
- Do not add a dependency without recording it in `docs/TECH_STACK.md`.
- Do not build generic dashboard UI. See `docs/DESIGN.md` for the prohibited-pattern list.
- Delete dead code rather than leaving compatibility shims.

## Task protocol (every task, without exception)

1. Read `CHECKPOINT.md` and the relevant doc in `docs/` before editing.
2. Inspect the existing implementation before adding a new one.
3. Implement **only** the requested scope. No adjacent refactors.
4. Run the relevant tests (`pytest tests/ -q`) or a real execution of the code path.
5. **Write your task record** to `docs/checkpoints/<nn>-<task-slug>.md` using the template in
   `docs/checkpoints/TEMPLATE.md`: what changed, files touched, how it was verified, measured
   results, limitations, next task. Then run `python scripts/update_checkpoint.py` to
   regenerate `CHECKPOINT.md`. Never hand-edit `CHECKPOINT.md` while other tasks are running —
   per-task files exist precisely so parallel work cannot clobber shared state.
6. Report: changed / files / tests / metrics / limitations / next task.
7. Never claim completion without an execution or test result behind it.

## Conventions

- Python package is `rai`. Run everything through `.venv\Scripts\python.exe`.
- Config lives in `rai/config.py` (pydantic-settings). No magic numbers in model code.
- Asset ids: `WT-###` wind turbines, `INV-###` solar inverters, `STR-###` strings.
- Timestamps are UTC, tz-aware, 10-minute cadence for wind, 15-minute for solar.
- Money is INR. Energy is kWh. Temperature is °C. Power is kW.
