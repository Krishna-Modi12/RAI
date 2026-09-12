---
task: README architecture refresh
phase: 5
status: complete
---

## What was built

- Replaced the README with a fresh-machine setup guide and implementation-accurate
  project overview.
- Added an architecture diagram showing the numerical pipeline, EvidencePacket boundary,
  decision-support tools, and human handoff.
- Added a decision-flow diagram showing persistence, attribution, peer, confidence, and
  escalation gates.
- Added a code-walkthrough narrative, configuration reference, evaluation instructions,
  repository map, and explicit non-claims.

## Files

- `README.md` — judge/developer documentation and Mermaid diagrams.
- `docs/checkpoints/04-README-architecture-refresh.md` — task record.

## How it was verified

- README relative-link checker — no missing relative links.
- `Set-Location web; npm run lint` — passed.
- `git diff --check -- README.md` — no content errors after the final edit.

## Measured results

- README contains the current Windows setup path, deterministic demo commands, CI
  commands, architecture flow, and API/frontend status.
- No new numerical claims were introduced; evaluation claims point to generated artifacts.

## Limitations

- The FastAPI route layer and browser-to-API integration remain incomplete.
- Full Ruff output is currently affected by unrelated uncommitted files under `rai/eval/`
  and `tests/test_environment_solar.py`; those files were not changed by this task.

## Next

Implement the frozen FastAPI routes and update the README’s API section with a verified
end-to-end request once the browser integration exists.
