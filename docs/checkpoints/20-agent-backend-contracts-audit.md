---
task: agent-backend-contracts-audit
phase: 5
status: complete
---

## What was built

An audit (per CLAUDE.md's task protocol step 2: "inspect existing implementation before
adding a new one") of the backend "intelligence contracts" architecture — schemas, agent
runtime, deterministic fallback reasoner, RAG index/retrieval, tool registry, and economics
engine — against the project's evidence-discipline and numerical-honesty rules. Read in full:
`rai/agent/interfaces.py`, `rai/schemas.py`, `rai/agent/runtime.py`, `rai/agent/fallback.py`,
`rai/agent/investigator.py`, `rai/agent/tools.py`, `rai/rag/index.py`, `rai/rag/retrieve.py`,
`rai/economics/engine.py`.

**Finding: the architecture substantively satisfies the requirements already. No rewrite
performed.** Specific evidence:

- **Evidence-typed contracts exist**, just not under the literal names `OBSERVED`/`RETRIEVED`/
  `INFERRED`/`UNKNOWN`/`ABSTAINED`: `EvidencePacket` (observation), `AgentVerdict` (diagnosis +
  action), `KnowledgeCitation`/`HistoricalCase` (retrieval, tagged `retrieval="fts5"` in
  `rai/rag/retrieve.py:100-113`), `EconomicEvidence`/`EconomicOption` (economics). Abstention is
  expressed as `requires_human_review: bool` + `confidence: float` rather than a named enum —
  functionally equivalent, exercised in two independent code paths
  (`rai/agent/runtime.py:verdict_from_needle`, `rai/agent/fallback.py:diagnose`).
- **Numerical-engine-owns-calculations / LLM-owns-explanation separation is real, not just
  documented**: `rai/agent/investigator.py` runs `fallback.diagnose()` (deterministic) as the
  `baseline` *before* Needle ever runs, and `verdict_from_needle()` only lets a Needle-authored
  field override the baseline when Needle actually supplied it — arithmetic fields (confidence,
  risk numbers) are never computed by the model. `rai/economics/engine.py`'s docstring states
  this explicitly and its tools return pre-computed numbers only.
- **Safety-by-construction confirmed**: `rai/agent/tools.py` registers exactly 6 read-only
  tools plus one write tool (`create_inspection_ticket`) that only proposes
  (`status="proposed_awaiting_human_approval"`) and cannot dispatch — there is no tool that
  writes a setpoint.
- **RAG corpus genuinely prioritizes manuals/SOPs over raw SCADA**: `rai/rag/index.py` indexes
  only markdown files under `knowledge/` (`KNOWLEDGE.glob("**/*.md")`) — numeric SCADA telemetry
  is never markdown and is structurally excluded, not merely deprioritized.
- **Environment/peer/soiling ruled out before equipment fault**: `rai/agent/fallback.py`'s
  `diagnose()` rule chain is `_environmental_ruling → _peer_ruling → _soiling_ruling →
  _equipment_ruling`, first non-`None` wins — the ordering CLAUDE.md mandates is the literal
  control flow, not a comment.

**Concrete, scoped gap found and fixed**: `rai/economics/engine.py::evaluate_cleaning_options()`
(the soiling/cleaning economic advisor, wired into `GET /api/soiling`) violated the "no magic
numbers in model code" / "show all monetary assumptions transparently" rules that the sibling
function `evaluate_options()` in the same file already follows correctly:
- `unit_cleaning_cost_inr = 1850.0` was an inline literal, unsourced from `rai/config.py`, and
  never disclosed to a caller — unlike `evaluate_options()`'s `EconomicOption.assumptions` dict.
- The three recommendation `confidence` values (0.88 / 0.92 / 0.78) were bare literals with no
  documented derivation, unlike `fallback.py`'s `_confidence()` which documents its heuristic.
- `CleaningAdvisorOption` (the schema) had no `assumptions` field at all, unlike its sibling
  `EconomicOption`, which does.
- `services/api/routers/soiling.py` independently re-hardcoded the same `1850.0` figure rather
  than sourcing it from one place.

Fixed by: hoisting the cost and confidence literals to named, commented module constants
(`UNIT_CLEANING_COST_INR`, `POST_CLEAN_BASELINE_SOILING_PCT`, `CLEANING_CONFIDENCE_RAIN_WINDOW`,
`CLEANING_CONFIDENCE_IMMEDIATE`, `CLEANING_CONFIDENCE_DEFER`) matching the file's own existing
convention (`DEFAULT_CAPACITY_FACTOR`, `DEGRADED_OUTPUT_LOSS_FRAC`); adding
`assumptions: dict[str, float]` to `CleaningAdvisorOption` in `rai/schemas.py` and populating it
for all four options; and pointing `services/api/routers/soiling.py` at the same constant
instead of its own copy of the number. This is additive (default `{}`) and does not change any
existing numeric output — verified below.

## Files

- `rai/schemas.py` — added `assumptions: dict[str, float] = Field(default_factory=dict)` to
  `CleaningAdvisorOption` (mirrors `EconomicOption.assumptions`).
- `rai/economics/engine.py` — added 5 named module constants replacing inline literals in
  `evaluate_cleaning_options()`; populated `assumptions=` on all 4 `CleaningAdvisorOption`
  instances.
- `services/api/routers/soiling.py` — imports and uses `UNIT_CLEANING_COST_INR` instead of a
  second hardcoded `1850.0`.
- No other files changed. No new files, no deletions.

## How it was verified

- `.venv/Scripts/python.exe -m pytest tests/ -q` → **421 passed**, 24 warnings (unchanged from
  pre-change baseline; `test_evaluate_cleaning_options_now`/`_rain_wait` in
  `tests/test_economics_memory.py` still pass since the new field is additive with a default).
- `.venv/Scripts/python.exe -m ruff check rai/economics/engine.py rai/schemas.py
  services/api/routers/soiling.py` → **All checks passed!**
- `npx --no-install pyright` (project-wide) → **3 errors, 746 warnings** — identical to the
  pre-existing baseline recorded in checkpoint 19 (both pre-existing errors remain in
  `scripts/evaluate.py`/`scripts/evaluate_gate2.py`, untouched by this change).

## Measured results

Not a modeling task; no metrics produced. The audit itself is the deliverable: 9 files read in
full, cross-referenced against 6 specific requirements from CLAUDE.md and the master research
task's Section 9-13, with line-number evidence recorded above for each. One real gap found and
fixed (magic-number / hidden-assumption violation in the cleaning economics path), confirmed via
`grep` that no other call site of `evaluate_cleaning_options`/`UNIT_CLEANING_COST_INR`-equivalent
numbers exists outside the two now-fixed locations.

## Limitations

- No named `OBSERVED`/`RETRIEVED`/`INFERRED`/`UNKNOWN`/`ABSTAINED` enum was added — the existing
  `retrieval="fts5"` tag + `requires_human_review`/`confidence` fields were judged functionally
  sufficient and adding a parallel taxonomy now would be speculative architecture with no
  consumer, which the master task explicitly deprioritizes under deadline pressure. If a future
  reviewer wants the literal taxonomy for the frontend evidence/provenance surface (Section 14-15
  of the master task), it should be introduced there as a presentation-layer classification over
  these existing fields, not as a backend rewrite.
- `GET /api/soiling` does not currently serialize `CleaningAdvisorOption.options[]` (it hand-picks
  a summary), so the new `assumptions` field is not yet visible in any API response —
  `docs/API_CONTRACT.md` needed no update because it accurately documents what that endpoint
  returns today. Wiring the full per-option breakdown into the API is frontend/API-surface work,
  out of scope for this audit.
- `rai/environment/cleaning_optimizer.py` (a separate module, used by
  `rai/models/environment_solar.py` for physical wash-scheduling, not the API's economic advisor)
  has its own independent `cleaning_cost_per_mw_inr` default — noted but not reconciled with
  `UNIT_CLEANING_COST_INR`, since the two serve different call sites and reconciling them was not
  a concrete requirement of this audit; flagging for a future pass if the two are ever meant to
  agree.

## Next

Continue the master task's remaining priorities: frontend evidence/provenance classification
surface (Section 14-15: REAL_EXTERNAL/INTERNAL_SYNTHETIC/SIMULATED_OUTCOME/MODEL_COMPARISON/
HISTORICAL_AUDIT/SOFTWARE_INVARIANT), further repository cleanup/claim-audit passes (Section
16-17), then documentation coherence (Section 18) — reassessing priority continuously and
switching to product/demo readiness at the ~6:30-7:00 AM deadline rule.
