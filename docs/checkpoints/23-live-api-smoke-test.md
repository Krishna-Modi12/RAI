---
task: live-api-smoke-test
phase: 5
status: complete
---

## What was built

No new code. A live smoke test of the real FastAPI backend (`services/api/main.py`), started
as an actual `uvicorn` server rather than exercised only through the demo CLI path — closing
the one limitation explicitly flagged in checkpoint 22 ("this confirms the demo/CLI integration
path works, not the HTTP API... path").

Started `uvicorn services.api.main:app` on port 8791 and exercised every router's route
surface, including a real HTTP call into the full `investigator.investigate()` pipeline:

- `/api/health`, `/api/soiling`, `/api/evaluation`, `/api/assets` → HTTP 200, real data
  (`"needle_available":true`, `"models_loaded":["wind_expected_power","solar_expected_power",
  "risk"]`, `"assets":42`).
- **Independent confirmation of the checkpoint 20 economics fix, from a second code path**:
  `/api/soiling` returned `"cleaning_cost_inr":44400.0`, which is
  `UNIT_CLEANING_COST_INR (1850) × 24 solar assets`. Checkpoint 22 confirmed this constant is
  live in the `scripts/demo.py` path; this confirms it is *also* correctly wired into
  `services/api/routers/soiling.py`'s live HTTP response — the same fix, verified through two
  independent execution paths (CLI demo, HTTP API), not just unit tests.
- `/api/assets/WT-004` → real per-asset detail: `health_score:55.3`, `risk_band:"elevated"`,
  three fired anomaly detectors, five real signal residuals.
- **`POST /api/assets/WT-004/investigate`** → HTTP 200, full `investigate()` pipeline exercised
  through the real HTTP layer for the first time (previously only confirmed via direct
  `scripts/demo.py` calls, which import `rai.agent` directly rather than going through
  `services/api/`). Response contained:
  - `"model_used":"deterministic_reasoner"`, `"fallback_used":true` — honest: Needle runtime
    was not loaded in this smoke-test process, and the response correctly reports the fallback
    path rather than fabricating a Needle-branded result.
  - `"severity":"critical"`, `"requires_human_review":true` — confirms escalation-to-human-review
    is live behavior over real HTTP, not just a unit-tested code path.
  - Five real historical case matches (`CASE-W-005` ... `CASE-W-001`) with similarity scores,
    three real RAG citations from `wind-generator-thermal-sop`/`wind-generator-system` docs
    (`retrieval:"fts5"`, real match scores).
  - Three economic options (`repair_now`/`defer_3d`/`defer_14d`), each carrying a full
    `assumptions` dict (`tariff_inr_per_kwh`, `capacity_factor`, `hazard_per_day`,
    `planned_downtime_hours`, `unplanned_downtime_hours`, `escalation_cost_inr`,
    `degraded_output_loss_frac`) — confirms the checkpoint-20 assumptions-transparency pattern
    is live end-to-end over HTTP, not just in `rai/economics/engine.py` unit tests.
  - `"tool_calls":[]` — consistent with the fallback (non-Needle) path; no physical control
    tool exists to call regardless (`rai/agent/tools.py`'s registry, audited in checkpoint 20).
- Remaining route surface swept for basic liveness: `GET /api/fleet`, `/api/fleet/priority`,
  `/api/knowledge/search?q=bearing`, `/api/knowledge/docs`, `/api/assets/WT-004/economics`,
  `/api/assets/WT-004/cases`, `/api/assets/WT-004/peers` — all HTTP 200.

## Files

None changed. Verification-only task.

## How it was verified

- Server started: `.venv/Scripts/python.exe -m uvicorn services.api.main:app --port 8791`
  (background process), confirmed listening via successful `curl` responses.
- `curl -s -o /dev/null -w "%{http_code}"` against 13 distinct routes across all 7 routers
  (`health`, `soiling`, `evaluation`, `assets`, `fleet`, `knowledge`, plus the `investigate`
  POST) — all returned `200`.
- Full JSON payloads for `/api/soiling`, `/api/assets/WT-004`, and
  `/api/assets/WT-004/investigate` inspected in full (not just status codes) via
  `.venv/Scripts/python.exe -c "json.load(...)"`, cross-checking specific numbers against
  known constants (`1850 × 24 = 44400`) and against the schemas/architecture audited in
  checkpoint 20.
- Server process identified via `Get-CimInstance Win32_Process -Filter "CommandLine LIKE
  '%uvicorn%8791%'"` (PowerShell) and stopped cleanly with `Stop-Process -Force`; confirmed
  down via a subsequent `curl` to `/api/health` returning connection failure (exit code, no
  HTTP status).

## Measured results

No new metrics — this task's output is confirmation that live HTTP responses match the
architecture already audited (checkpoint 20) and the CLI-path numbers already verified
(checkpoint 22). The one new number surfaced is the `/investigate` HTTP response's
`avoidable_exposure_inr: 2626171.15` for `WT-004`, a real computed value (not previously seen
since checkpoint 22's demo run used `WT-017`), consistent internally with its own
`expected_exposure_inr` fields (`884152.0` vs `defer_14d`'s `3510323.15`).

## Limitations

- This is a smoke test (route liveness + payload sanity), not a full API contract test suite —
  `tests/test_api_contract.py` (referenced in `docs/CLAIMS.md`) is the authoritative,
  repeatable check; this task is a one-time live-server confirmation layered on top of it.
- Needle runtime was not loaded during this test (`fallback_used:true` throughout) — this
  confirms the deterministic fallback path over real HTTP, but does not additionally confirm
  the Needle-overlay path (`verdict_from_needle`) over HTTP; that path was already audited by
  reading `rai/agent/investigator.py` in checkpoint 20 and is gated on local model availability
  independent of the API layer.
- `/api/knowledge/search`, `/api/knowledge/docs`, `/api/fleet`, `/api/fleet/priority`,
  `/api/assets/{id}/economics`, `/api/assets/{id}/cases`, `/api/assets/{id}/peers` were checked
  for HTTP 200 liveness only, not payload correctness — lower priority since none of them sit on
  a previously-identified risk (unlike the soiling/investigate endpoints, which directly tested
  checkpoint 20's fix and checkpoint 21's status corrections).

## Next

Backend intelligence contracts (checkpoint 20), Gate 5.6C status/claim integrity (checkpoint
21), CLI-path integration (checkpoint 22), and now live HTTP-path integration (this checkpoint)
are all verified with real, cross-checked evidence. No further backend verification is
identified as higher-value than either (a) a bounded documentation-coherence pass over
`docs/PRD.md` / `docs/DESIGN.md` / `docs/TECH_STACK.md` / `docs/EVALUATION_FORENSICS.md` for
any remaining contradictions with the corrected Gate 5.6C phase label, or (b) beginning to
prepare for the ~7:00 AM frontend transition (e.g., confirming `web/`'s expected API contract
matches what was just verified live). Reassess and continue per the master task's deadline
rule.
