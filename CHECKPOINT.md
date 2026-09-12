# CHECKPOINT

> Consolidated build state. Individual task records live in `docs/checkpoints/` and are
> merged here by `scripts/update_checkpoint.py` (parallel agents each write their own file,
> so there are no write races on this document).

**Last updated:** 2026-09-12 (foundation phase)
**Overall:** ▓▓░░░░░░░░ 15%

---

## Environment (verified, not assumed)

| Check | Result |
|---|---|
| Python | 3.11.9 ✅ |
| Node / npm | 26.7.0 / 11.19.0 ✅ |
| git | 2.51.1 ✅ |
| Core Python stack | numpy, pandas, scipy, sklearn, xgboost, duckdb, pyarrow ✅ |
| API stack | fastapi, uvicorn, pydantic, httpx ✅ |
| Domain libs | pvlib ✅, ruptures ✅ |
| Needle 2 (`cactus-needle`) | installed ✅ — **runtime blocked in this sandbox** ⚠️ |
| Next.js available | 16.3.5 ✅ |

### ⚠️ Known environment constraint

`huggingface.co` is unreachable from the build sandbox (`pypi.org` and `github.com` are
fine). Needle 2 fetches its native library and weights from the Hub on first construction,
so `needle.Needle(...)` raises `LocalEntryNotFoundError` here.

Consequences, by design:
- The agent layer is built against Needle's **verified real API** (`@needle.tool`,
  `needle.Needle(tools=, system=, weights=, tool_index_path=)`, `agent.run(query,
  max_steps=, max_new_tokens=, strict=)`, `needle.extract(text, schema)`).
- A **deterministic evidence reasoner** implements the identical `AgentVerdict` contract and
  is fully testable here, so the demo never depends on a network fetch.
- `scripts/warmup_needle.py` pre-fetches the model on an unrestricted network (your machine).
  `GET /api/health` reports which path is live.

---

## Frozen contracts

| Artifact | Status |
|---|---|
| `rai/schemas.py` — all data contracts | ✅ authored |
| `rai/config.py` — fleet registry, physics, economics | ✅ authored |
| `docs/API_CONTRACT.md` — REST contract | ✅ frozen |
| `CLAUDE.md` — project rules + task protocol | ✅ authored |

Fleet: 18 × 2.0 MW turbines (Kutch Wind Farm) + 24 × 250 kW inverters (Charanka Solar Park),
both Gujarat. Demo heroes: `WT-017`, `INV-023`.

---

## Task board

### Phase 1 — Foundation
- [x] Repo scaffold, git init, `.gitignore`
- [x] Python environment + dependency verification
- [x] Data contracts (`rai/schemas.py`)
- [x] Fleet + economics config (`rai/config.py`)
- [x] Frozen API contract (`docs/API_CONTRACT.md`)
- [ ] Physics telemetry simulator + fault injection
- [ ] Parquet/DuckDB store layer
- [ ] Real-dataset adapters (CARE, Kaggle solar, NASA POWER)
- [ ] Knowledge corpus + FTS5 retrieval
- [ ] Project documentation set
- [ ] Frontend design system + scaffold

### Phase 2 — Intelligence
- [ ] Feature engineering + residual construction
- [ ] Wind expected-behaviour model (physics + GBM)
- [ ] Solar expected-behaviour model (pvlib + GBM)
- [ ] Anomaly fusion (residual-z + Isolation Forest + changepoint)
- [ ] Peer comparison engine
- [ ] Environmental attribution engine
- [ ] Risk model + calibration
- [ ] Historical case memory (trajectory kNN)
- [ ] Soiling estimation
- [ ] Economic decision engine
- [ ] Evaluation harness + leakage guards

### Phase 3 — Agent + API
- [ ] Needle tool registry (7 tools)
- [ ] Needle runtime + deterministic fallback + confidence gating
- [ ] FastAPI service implementing the frozen contract

### Phase 4 — Interface
- [ ] Fleet command view
- [ ] Asset investigation view
- [ ] Simulator console
- [ ] Soiling intelligence view
- [ ] Knowledge view

### Phase 5 — Verify
- [ ] Test suite green
- [ ] Measured evaluation report
- [ ] End-to-end demo rehearsal
- [ ] Audit report

---

## Verified metrics

None yet. Every metric in this file must come from an executed evaluation run
(`scripts/evaluate.py` → `artifacts/evaluation.json`). Placeholder numbers are prohibited.

## Current blocker

None.

## Demo readiness

0% — no runnable path yet.

<!-- CONSOLIDATED:BEGIN -->

## Consolidated task log

_Generated 2026-09-12 08:22 UTC from 3 task record(s) in `docs/checkpoints/`._

**3/3 task records complete.**

| | Task | Phase | Status |
|---|---|---|---|
| ✅ | repository Copilot instructions | 1 | complete |
| ✅ | reviewer-ready repository documentation | 1 | complete |
| ✅ | Phase 2 repository upgrade | 5 | complete |

### ✅ repository Copilot instructions

**What was built**

- Added repository-level Copilot guidance covering verified Python and frontend commands.
- Documented the layered RAI architecture and API/UI contract boundary.
- Captured project-specific numerical honesty, evidence, safety, data, and checkpoint rules.

**How it was verified**

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed.

**Measured results**

91 tests passed; Ruff reported no violations.

**Limitations**

The FastAPI application entrypoint is not implemented yet, so no API startup command is documented.

### ✅ reviewer-ready repository documentation

**What was built**

- Rebuilt the root README around the problem, architecture, reproducible demo, Phase 2 evaluation, and explicit implementation status.
- Added ML, evaluation, demo, API, limitations, and licensing guides plus contribution, security, and community-health files.
- Added deterministic `scripts/demo.py` and measured `scripts/evaluate.py` outputs under `artifacts/evaluation/`.
- Added GitHub pull-request and bug-report templates.

**How it was verified**

- `.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.
- `.venv\Scripts\ruff.exe check .` — all checks passed after the final import cleanup.
- `Set-Location web; npm run lint` — passed.
- `Set-Location web; npm run build` — passed with Next.js 16.3.5.
- `.venv\Scripts\python.exe scripts\evaluate.py` — wrote evaluation artifacts and reported 12/12 scenario agreement.
- `.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear` — completed the 8-stage deterministic investigation.
- Repository Markdown local-link check — 0 broken local links.
- Secret-pattern scan found only documentation/code references, no credential values.

**Measured results**

The generated report contains eight expected-behaviour model metric sets and 12/12
scenario-level agreement against simulator equipment/non-equipment flags. These are
synthetic, controlled results and are not real-world validation.

**Limitations**

Pyright is configured but is not installed in the checked-in virtual environment, so no
type-check result is claimed. The FastAPI route layer and browser dashboard remain in
progress.

### ✅ Phase 2 repository upgrade

**What was built**

- Added a claims-to-evidence matrix and curated references for datasets, research, and
  software.
- Added maintainable Mermaid source diagrams for architecture, decision flow, demo flow,
  and data flow.
- Added GitHub Actions quality checks for Python tests/Ruff and frontend lint/build.
- Corrected stale documentation and stopped tracking local Claude settings.

**How it was verified**

`.venv\Scripts\python.exe -m pytest tests\ -q` — 91 passed.

`.venv\Scripts\ruff.exe check .` — passed.

`Set-Location web; npm run lint` — passed.

`Set-Location web; npm run build` — passed.

`.venv\Scripts\python.exe scripts\evaluate.py` — scenario agreement 12/12.

`.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear` — completed
the deterministic investigation path.

**Measured results**

- Python tests: 91 passed.
- Synthetic scenario agreement: 12/12.
- Frontend production build: successful.

**Limitations**

- The API route layer and browser-to-API integration remain incomplete.
- CI has not run on GitHub in this session; the workflow is validated against the same
  local commands.
- Evaluation results remain synthetic and are not real-world accuracy claims.

