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
| The system is validated on live or public plant telemetry | Future | No dated external-data evaluation artifact is present | Do not claim this yet |
| The REST API and browser operator interface are complete | Specified/in progress | `docs/API_CONTRACT.md`, `web/` scaffold, empty API package | Track implementation before presenting an end-to-end dashboard |

Synthetic scenario agreement is not real-world predictive accuracy. The evidence and
limitations must travel with any presentation of a result.

