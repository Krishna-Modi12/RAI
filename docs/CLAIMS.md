# Claims matrix

This matrix keeps the public story tied to executable evidence. A claim marked
**demonstrated** is reproducible locally; **specified** means the contract or design exists
but the full implementation is not complete; **future** is a research direction.

| Claim | Status | Evidence | How to verify |
|---|---|---|---|
| The simulator emits wind and solar telemetry with injected ground truth | Demonstrated | `rai/sim/`, `InjectedEvent`, physics tests | `python scripts/generate_data.py`; `pytest tests/test_sim_physics.py -q` |
| Healthy behaviour is trained without random temporal shuffling | Demonstrated | `rai/models/expected.py`, `chronological_split` | `python scripts/evaluate.py --retrain` |
| An equipment conclusion is gated by environment, peers, and sensor health | Demonstrated | `rai/models/environment.py`, `rai/models/peers.py`, fallback tests | `pytest tests/test_agent_reasoning.py -q` |
| The local reasoner returns a schema-valid evidence-backed verdict | Demonstrated | `rai/agent/fallback.py`, `rai/schemas.py` | `python scripts/demo.py --scenario gearbox_bearing_wear` |
| Economic options are computed in Python, not by the agent | Demonstrated | `rai/economics/engine.py` and economics tests | `pytest tests/test_economics_memory.py -q` |
| Needle 2 can be used as an optional local explanation layer | Implemented with fallback | `rai/agent/runtime.py`; availability depends on local weights | `python scripts/warmup_needle.py` on a network that can reach the model host |
| Scenario-level equipment/non-equipment agreement is 12/12 | Measured synthetic result | `artifacts/evaluation/results.json` | `python scripts/evaluate.py` |
| Real, public plant telemetry was acquired and adjudicated (not modeled or validated) | Demonstrated | `artifacts/evaluation/gate56/acquisition/`, `.../cohort_adjudication/` (NREL PVDAQ, checksummed) — Gate 5.6A/5.6B, **COMPLETE and FROZEN** | `docs/checkpoints/15-gate56a-pvdaq-real-acquisition.md`, `docs/checkpoints/16-gate56b-cohort-adjudication.md` |
| A solar expected-performance model, fit against that real telemetry, is independently validated | **Not yet true — do not claim this.** Preliminary/`partial`, not `Future` (the model exists and ran; validation does not) | `rai/eval/external/solar/pvlib_modelchain_reference.py`, `artifacts/evaluation/gate56/gate56c_model_development/` — labeled `MODEL_DEVELOPMENT`/`NOT_INDEPENDENTLY_VALIDATED` throughout; Gate 5.6C is **not complete** | `docs/checkpoints/19-gate56c-model-development.md` (status: `partial`), `docs/checkpoints/21-gate56c-status-correction.md` |
| The system is validated on live plant telemetry (real-time production deployment) | Future | No live-deployment or real-time-feed evaluation artifact is present | Do not claim this yet |
| The REST API and browser operator interface are complete | Demonstrated | `services/api/` (FastAPI, routers wired), `web/` (Next.js, `npm run build` succeeds: 8 routes, 0 errors) | `npm run build` in `web/`; `pytest tests/test_api_contract.py -q` |

Synthetic scenario agreement is not real-world predictive accuracy. The evidence and
limitations must travel with any presentation of a result.

