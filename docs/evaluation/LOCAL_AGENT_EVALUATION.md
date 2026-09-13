# Local Agent Evidence / Tool Evaluation

## Scope and claim boundary

This is a deterministic, local evaluation of the evidence and tool boundary. It uses the
checked-in synthetic simulator/case corpus (`INTERNAL_SYNTHETIC`) and Python-computed
economics. It is not a Needle accuracy benchmark, a real-plant validation, or evidence that
historical matches are diagnoses.

Needle is optional. The tests use the injectable runtime seam in `rai/agent/runtime.py` and a
fake runtime for the model-specific path; no weights are downloaded and no test depends on
Needle availability.

## Actual runtime chain

`rai.agent.investigator.investigate()` executes the following fixed chain:

1. Resolve the evidence provider and build one compact `EvidencePacket`.
2. Record telemetry, expected-behaviour, environment, and peer timeline steps.
3. Run the deterministic rule chain once to select the provisional component/query.
4. Retrieve trajectory cases from `rai.memory.retrieval`, preserving source type, evidence
   states, match/difference fields, and limitations.
5. Retrieve cited procedure spans through SQLite FTS5 in `rai.rag.retrieve`.
6. Cost options through `rai.economics.engine`; the agent receives finished Python values.
7. Run the deterministic reasoner again with all evidence attached.
8. If explicitly enabled and available, pass only the compact digest to Needle 2. Missing,
   malformed, contradictory, or low-confidence Needle output falls back to the deterministic
   verdict.
9. Emit the decision step and append an audit record.

The tool registry contains eight read-only tools and one proposal-only ticket tool. There is no
setpoint, dispatch, or physical-control tool. A ticket is written with
`proposed_awaiting_human_approval` status.

## Deterministic suite

Command:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_local_agent_evaluation.py -q
```

The suite covers current state and environmental intent, historical retrieval and comparison,
no-match abstention, conflicting environmental evidence, provenance, actual economics,
failure recovery, malformed ticket arguments, proposal-only safety, investigator ordering, and
injectable Needle success/failure behavior.

## Measured results

Targeted execution: **24 passed**.

| Metric | Result | Definition |
|---|---:|---|
| Tool-selection accuracy | 6/6 (100%) | Deterministic intent-to-registry dispatch cases; not a Needle model score |
| Argument correctness | 6/6 (100%) | Representative tool names and structured argument/return contracts |
| Provenance preservation | 4/4 (100%) | Source type, observed/retrieved/inferred/unknown states, limitations, and applicability fields |
| Unsupported-claim rate | 0/7 (0%) | Evaluated task scenarios produced no flagged unsupported claim |
| Abstention correctness | 4/4 (100%) | Empty retrieval, unknown case detail, unknown asset, and missing economics |
| Recommendation validity | 4/4 (100%) | All deterministic verdicts have bounded actions; economics recommendation is an engine option |
| Task success / evidence coverage | 7/7 (100%) | Evaluator tasks A-G passed and returned the required evidence contract |

These are fixture and contract metrics over a small internal synthetic battery. They should not
be read as production accuracy, calibration, or generalization.

## Limitations

- The historical corpus is internally authored synthetic history; no real maintenance records
  are used by this evaluation.
- The tool-selection metric verifies deterministic dispatch contracts, not an LLM's ability to
  choose tools from unconstrained language.
- The measured Needle path is optional and runtime-focused only: response success 1.00,
  concurrent safety passed, and mean latency was 6451.9 ms in one local run. This is not
  model quality or failure probability.
- The full repository test command currently exercises an existing phase-4 compatibility
  harness as well; its local-agent entry point is forced deterministic so it does not require
  Needle weights.
