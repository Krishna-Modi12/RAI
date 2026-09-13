---
task: Historical case intelligence and provenance-safe retrieval
phase: 3
status: partial
---

## What was built

- Extended `HistoricalCase` with structured context, provenance type, evidence states, and match/difference explanations.
- Reused the existing weighted trajectory retrieval and separated it from document FTS5 retrieval.
- Added bounded case-detail and comparison tools for the local agent.
- Added a focused Asset Deep-Dive presentation for provenance and applicability.
- Added deterministic regression coverage and documented the bounded claim.

## Files

- `rai/schemas.py` — structured historical case and provenance contracts.
- `rai/memory/retrieval.py` — explained retrieval and bounded case details.
- `rai/agent/tools.py` — `get_case_details` and `compare_case`.
- `tests/test_historical_intelligence.py` — provenance and abstention regressions.
- `web/src/components/EvidenceAccordion.tsx` — contextual historical evidence display.
- `docs/evaluation/HISTORICAL_CASE_RETRIEVAL.md` — protocol and limitations.

## How it was verified

`.venv\Scripts\python.exe -m pytest tests\test_historical_intelligence.py tests\test_economics_memory.py tests\test_agent_reasoning.py -q` — 30 passed.

## Measured results

Authored thermal relevance precision@3: 1.00 (3/3). The regression set also verified
provenance, explanation fields, and unknown-case abstention.

## Limitations

The corpus is internally authored synthetic history. No independent real maintenance-case
validation or diagnosis claim is supported.

## Next

Run the full relevant backend and frontend verification, then reassess whether economic
decision intelligence or technician feedback is the next highest-value phase.
