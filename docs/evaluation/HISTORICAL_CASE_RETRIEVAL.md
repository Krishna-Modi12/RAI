# Historical Case Intelligence — Retrieval Evaluation

## Claim level

`MODEL_COMPARISON` / `SOFTWARE_INVARIANT` only. This phase demonstrates a bounded,
deterministic retrieval capability over the repository's existing authored case library.
It is not failure validation, diagnosis, or evidence that a historical outcome will recur.

## Corpus and provenance

The corpus is the existing `rai/memory/library.py` episode library. Cases represent
meaningful investigation trajectories, including non-equipment explanations. Every result
is labelled `source_type=INTERNAL_SYNTHETIC`; unavailable fields remain `UNKNOWN` or null.
Raw SCADA is not indexed as a case. The document RAG layer remains SQLite FTS5 for reviewed
manuals, SOPs, and incident documents.

## Retrieval protocol

1. Build a compact signature from the computed `EvidencePacket` only.
2. Filter the existing library by asset type and exclude the current asset when requested.
3. Rank with the weighted trajectory distance already used by RAI.
4. Apply contradiction penalty when environmental evidence conflicts with a case.
5. Reject matches below the minimum similarity threshold rather than padding results.
6. Return `why_matched`, `what_is_similar`, `what_is_different`, `why_may_not_apply`,
   source type, and evidence states.

Similarity is a ranking aid, not a probability.

## Deterministic evaluation

The regression set covers a wind thermal query, provenance preservation, explanation fields,
and unknown-case abstention. On the authored thermal relevance set
`{CASE-W-001, CASE-W-002, CASE-W-003, CASE-W-006}`, precision@3 was **1.00 (3/3)**.
It verifies that a missing case returns
`INSUFFICIENT_EVIDENCE`, that no raw telemetry is exposed, and that synthetic provenance is
preserved. Exact precision@k is not claimed because the repository has no reviewed
real-world relevance judgements; the reported score is only for this explicitly authored
deterministic regression set and must not be generalized to real maintenance history.

## Limitations

The available cases are internally authored and not customer maintenance records. There is
no independent adjudicated real-case corpus in the repository. Historical outcomes may
inform investigation context and economic questions, but never guarantee a future outcome.
