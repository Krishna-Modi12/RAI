# Real Case Corpus Provenance Reconciliation

**Audit type:** Provenance/claim reconciliation (not a new evaluation run).
**Trigger:** `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` asserted the `EXTERNAL_REAL` retrieval
partition contains "16 cases (10 wind, 6 solar from PVPMC)". That figure was never correct and
contradicted this repository's own `docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md`, which has
always said 14. This document traces every real case to its construction site, resolves the
contradiction, and states exactly what the corpus does and does not prove.
**Final Verdict:** **PASS WITH DOCUMENTED LIMITATIONS** (see §10).

---

## 1. Full Provenance Table (all 14 cases)

The sole construction site for the `EXTERNAL_REAL` academic corpus is `rai/memory/real_corpus.py`
(`REAL_RECORDS`, one commit, `3108be0`, never modified since). `rai/memory/library.py::get_real_cases()`
adds zero further records today, because zero field-feedback tickets have been promoted to
`EXTERNAL_REAL` (dual-key gate requires `EXTERNAL_FIELD_OBSERVED` + `FIELD_VERIFIED`; current ledger
is `INTERNAL_TEST_FIXTURE`/`DEMO_SIMULATION` only). **The live "real" partition size is therefore
exactly 14, not 16.**

| # | Case ID | Dataset / Source | Asset | Component | `event_class` (repo taxonomy) | What was observed |
|---|---|---|---|---|---|---|
| 1 | `REAL-CARE-A-072` | CARE to Compare Farm A, Zenodo 14006163, event 72 | CARE-WT-A01 (wind) | Gearbox | `REAL_VERIFIED_EVENT` | HSS bearing temp 51.3→66.0°C, author-labelled "Gearbox failure", 7-day repair outage |
| 2 | `REAL-CARE-A-000` | CARE Farm A, Zenodo 14006163, event 0 | CARE-WT-A02 (wind) | Generator | `REAL_VERIFIED_EVENT` | Bearing temp 46.5→94.0°C, author-labelled "Generator bearing failure", 14-day outage |
| 3 | `REAL-CARE-A-068` | CARE Farm A, Zenodo 14006163, event 68 | CARE-WT-A03 (wind) | Transformer | `REAL_VERIFIED_EVENT` | Phase L3 temp reached 125°C, author-labelled "Transformer failure", 14-day outage |
| 4 | `REAL-CARE-A-022` | CARE Farm A, Zenodo 14006163, event 22 | CARE-WT-A04 (wind) | Hydraulic group | `REAL_VERIFIED_EVENT` | Oil temp rise + pressure-loss alarms, "Hydraulic group" label, 7-day repair |
| 5 | `REAL-CARE-B-053` | CARE Farm B, Zenodo 14006163, event 53 | CARE-WT-B01 (wind) | Rotor bearing | `REAL_VERIFIED_EVENT` | "Rotor Bearing 2 - Damage" label, 42-day standstill, crane mobilization |
| 6 | `REAL-CARE-C-081` | CARE Farm C, Zenodo 14006163, event 81 | CARE-WT-C01 (wind) | Power converter | `REAL_VERIFIED_EVENT` | Step drop 1850→0 kW at steady 9.2 m/s wind, "Converter Failure: Fuse Filter Supply" |
| 7 | `REAL-CARE-C-044` | CARE Farm C, Zenodo 14006163, event 44 | CARE-WT-C02 (wind) | Cooling system | `REAL_MAINTENANCE_EVENT` | Post-service human error — cooling valve left mispositioned; resolved by manual correction |
| 8 | `REAL-CARE-A-025-NORM` | CARE Farm A, Zenodo 14006163, event 25 | CARE-WT-A05 (wind) | General turbine | `REAL_OPERATIONAL_EVENT`¹ | Author-labelled healthy baseline reference period; no maintenance, no anomaly |
| 9 | `REAL-KEL-1-FORCED-3000` | Kelmarsh Wind Farm, Zenodo 5841834, status line 634 | Kelmarsh-1 (wind) | Power converter | `REAL_OPERATIONAL_EVENT` | Greenbyte code 3000, 4-min stop, auto-reset, zero thermal anomaly |
| 10 | `REAL-KEL-1-FORCED-2550` | Kelmarsh, Zenodo 5841834, status line 1240 | Kelmarsh-1 (wind) | Cooling system | `REAL_OPERATIONAL_EVENT` | Greenbyte code 2550, 14-min fan-overload protection trip, auto-reset |
| 11 | `REAL-KEL-1-MAINT-0020` | Kelmarsh, Zenodo 5841834, status line 1225 | Kelmarsh-1 (wind) | General turbine | `REAL_MAINTENANCE_EVENT` | Greenbyte code 20, "Scheduled Maintenance", 28-min on-site service stop |
| 12 | `REAL-KEL-1-ENV-0010` | Kelmarsh, Zenodo 5841834, status line 23 | Kelmarsh-1 (wind) | Environment | `ENVIRONMENTAL_EVENT` | Wind 2.1 m/s < cut-in 3.0 m/s, automated standby, peer turbines also idling |
| 13 | `REAL-PVDAQ-034-OUTAGE` | NREL PVDAQ OEDI System 34 (Las Vegas NV) | PVDAQ-34 (solar) | Inverter | `REAL_OPERATIONAL_EVENT` | 3-hour midday generation drop to 0 kW at 852 W/m² POA; reconnected automatically |
| 14 | `REAL-PVDAQ-1283-CLIPPING` | NREL PVDAQ OEDI System 1283 (Golden CO) | PVDAQ-1283 (solar) | Inverter | `ENVIRONMENTAL_EVENT` | Power plateau at nameplate under >980 W/m² POA — designed clipping, explicitly not a fault |

¹ **Known taxonomy inconsistency, documented not silently fixed:** case 8's `event_class` is coded as
`REAL_OPERATIONAL_EVENT` even though `real_corpus.py`'s own module docstring defines that class as
"shutdown, curtailment, or control trip" — a *healthy baseline* period fits none of those. This is a
labelling quirk in the source module, not a partition-integrity defect (the case is still correctly
`EXTERNAL_REAL`, still correctly not `REAL_VERIFIED_EVENT`, and its adjudication text is accurate: "A
real physical failure... " is never claimed for it). Per the task's `DO NOT MODIFY` scope boundary,
`real_corpus.py`'s taxonomy is left as-is rather than reclassified without a corresponding code change
and full regression re-run; flagged here for a future task.

---

## 2. Classification (this task's taxonomy)

| Repo `event_class` | Count | Mapped classification | Rationale |
|---|---|---|---|
| `REAL_VERIFIED_EVENT` | 6 | `EXTERNAL_REAL_VERIFIED_EVENT` | Independently authored failure label + physical repair/replacement action in the source dataset's own event log |
| `REAL_OPERATIONAL_EVENT` | 4 | `EXTERNAL_REAL_OPERATIONAL_EVENT` | Protection trip / control stop / labelled-healthy period with **no** proven hardware damage |
| `REAL_MAINTENANCE_EVENT` | 2 | `EXTERNAL_REAL_MAINTENANCE_EVENT` | Planned or human-error maintenance intervention, not equipment wear |
| `ENVIRONMENTAL_EVENT` | 2 | `EXTERNAL_REAL_OPERATIONAL_EVENT` (environmental subtype) | Weather/resource-driven, zero equipment involvement; this task's rubric has no dedicated environmental bucket, so these are grouped under operational-non-fault but kept individually labelled in §1 to avoid conflating them with control-system trips |
| `UNKNOWN` | 0 | — | No case in the corpus has an ambiguous root cause |
| `EXCLUDED` | 0 | — | No case was dropped for corrupt data |
| `INTERNAL_SYNTHETIC` / `SIMULATED_OUTCOME` / `MODEL_COMPARISON` | 0 | — | Not applicable — this table covers only the `partition="real"` corpus; the 14-case `SYNTHETIC_CASES` benchmark fixture library and the physics simulator (`rai/sim/`) are separately and correctly partitioned as `INTERNAL_SYNTHETIC` (see §9) |

**No case in the corpus was upgraded from an operational/maintenance/environmental event to a
component failure.** All 6 `REAL_VERIFIED_EVENT` cases are wind turbines from CARE; zero solar cases
are confirmed failures.

---

## 3. The Six... No, Two Solar Cases

The task brief that triggered this reconciliation assumed 6 solar real cases existed. **They do not.**
There are exactly **2**, both from NREL PVDAQ OEDI, both non-fault events:

- `REAL-PVDAQ-034-OUTAGE` (System 34): a real inverter outage, but the maintenance action is recorded
  as `UNKNOWN (inverter breaker trip / grid interface trip reset)` — no work order exists confirming
  what actually happened; it is `REAL_OPERATIONAL_EVENT`, not a controlled/emulated fault, not
  independently labelled beyond the SCADA power/irradiance record itself.
- `REAL-PVDAQ-1283-CLIPPING` (System 1283): explicitly **designed** inverter saturation behavior under
  peak irradiance, not an anomaly of any kind (`ENVIRONMENTAL_EVENT`).

**What each can legitimately be used for:**

| Use | `REAL-PVDAQ-034-OUTAGE` | `REAL-PVDAQ-1283-CLIPPING` |
|---|---|---|
| Historical context | ✅ Yes | ✅ Yes |
| Retrieval validation | ⚠️ Only as a self-consistency check (see §7) — not an independent benchmark | ⚠️ Same |
| Fault classification | ❌ No — not proven to be a fault at all | ❌ No — proven **not** to be a fault |
| Failure validation | ❌ No confirmed failure exists to validate against | ❌ No |
| Diagnosis validation | ❌ No | ❌ No |

There is no PVPMC-sourced case anywhere in the corpus. Sandia PVPMC / pvlib is used elsewhere in this
repository (`rai/eval/external/solar/inventory.py`, Gate 5.5/5.6) strictly as a **physics-reference
modeling library** (`operational_data=False`, `environmental_data=False`) — it has never contributed a
real case record.

---

## 4. PVDAQ / Gate 5.6B Boundary

**Gate 5.6B is not altered by this document.** Its cohort adjudication
(`docs/checkpoints/16-gate56b-cohort-adjudication.md`) remains: Development cohort = `[1239, 1283, 34]`,
Validation cohort = `[]` (`INSUFFICIENT_DATA`), Gate 5.6C = `NOT VALIDATED`. That verdict is unchanged.

**New fact, now documented for the first time:** PVDAQ Systems 34 and 1283 are the *same physical
installations* in both efforts — confirmed independently by both documents describing System 1283 as
having net-meter/bidirectional-meter semantics (`real_corpus.py:657` and
`artifacts/evaluation/gate56/cohort_adjudication/summary.md` Q3). These are **two independent,
non-overlapping uses** of the same raw telemetry:

1. Here: 2 of the 3 Development-cohort systems each contribute **one retrieval-memory case record**
   (both non-fault events).
2. Gate 5.6B: the same 2 systems (plus System 1239, which has no case-corpus counterpart) are
   **model-fitting data** for solar expected-performance development.

**Neither validates the other.** The existence of this real-case corpus does not imply Gate 5.6C
achieved a validated result — it explicitly did not (empty validation cohort). This cross-reference is
now recorded in `docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md` §1 to prevent future confusion.

---

## 5. Wind Case Reconciliation

12 wind cases, from two sources, zero upgraded beyond their source evidence:

- **CARE to Compare (8 cases):** 6 `REAL_VERIFIED_EVENT` confirmed component failures (gearbox,
  generator bearing, transformer, hydraulic group, rotor bearing, converter fuse — cases 1-6 in §1),
  1 `REAL_MAINTENANCE_EVENT` (human-error valve misposition, case 7), 1 `REAL_OPERATIONAL_EVENT`
  (healthy baseline, case 8, see taxonomy note above).
- **Kelmarsh Wind Farm (4 cases):** 2 `REAL_OPERATIONAL_EVENT` protection trips with explicit
  "must remain OPERATIONAL_EVENT!" annotations in the source module (cases 9-10), 1
  `REAL_MAINTENANCE_EVENT` scheduled service stop (case 11), 1 `ENVIRONMENTAL_EVENT` low-wind
  standstill (case 12).

No Kelmarsh operational trip is described anywhere in the corpus, tests, docs, or frontend as a
component failure — the module's own inline comments enforce this ("Does NOT prove component failure
or hardware degradation. Must remain OPERATIONAL_EVENT!").

---

## 6. Claim Audit — What Was Fixed

A full-repository search (README.md, `docs/CLAIMS.md`, `docs/RESEARCH_REGISTRY.md`, every
`docs/evaluation/*.md`, `CHECKPOINT.md`, and `web/src/**`) found the wrong "16 cases / 10 wind + 6
solar / PVPMC" claim in exactly two files, corrected in this task:

| File | Lines corrected | Was | Now |
|---|---|---|---|
| `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` | 19, 90-103, 134-135, 319, 350, 360 | "16 cases (10 wind, 6 solar from PVPMC)"; fabricated `REAL_WIND_CASES`/`REAL_SOLAR_CASES` pseudo-code | "14 cases (12 wind CARE/Kelmarsh, 2 solar NREL PVDAQ)"; code block now matches the actual `library.py::get_real_cases()` |
| `CHECKPOINT.md` | 5 (hand-maintained header) | "16 real adjudicated cases across CARE, Kelmarsh, and PVPMC" — contradicted line 16 of the same file | "14 real adjudicated cases across CARE, Kelmarsh, and NREL PVDAQ" — now consistent with line 16 |

Everything else checked (`README.md:184`, `docs/CLAIMS.md:22`, `docs/RESEARCH_REGISTRY.md:82-88`,
`docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md`, `web/src/app/work-orders/page.tsx:727,730`)
already correctly said 14 / NREL PVDAQ and needed no change. The "16/PVPMC" error did not leak into
any frontend string.

No wording anywhere claims `REAL_CASE_CORPUS` implies `REAL_FAILURE_VALIDATION` — the strongest
existing claim (`docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md` §8 "Supported Claim") was already
explicit about NOT constituting failure/causal/probability validation; it has now additionally been
qualified to disclose that its relevance labels are curated, not independently sourced (§7 below).

---

## 7. Retrieval Evaluation Audit & Level Rubric

`rai/eval/retrieval_eval.py::evaluate_retrieval_benchmark()` genuinely computes Precision@1,
Precision@3, Recall@3, and MRR (real arithmetic over real function calls — `artifacts/retrieval_benchmark_results.json`
exists on disk with a fresh mtime, so the reported numbers are real computed outputs, not invented
text). However:

- The "relevant case" answer key (`BENCHMARK_QUERIES[i].relevant_case_ids`) is a **developer-authored
  constant list**, written by the same codebase that implements the retrieval/distance algorithm being
  scored — there is no external label file and no reference to the source datasets' own independent
  fault tickets.
- Each benchmark query's *input* is a live `build_evidence_packet()` call against a **simulated** fleet
  asset (`rai/sim/`), not a real telemetry stream leading up to one of the 14 real cases.
- `retrieval_eval.py` is invoked by **zero** files under `tests/` and by no `scripts/` entrypoint — it
  only runs manually via `python -m rai.eval.retrieval_eval`, and its numbers are not part of the
  535-test `pytest` count anywhere in this repository.

**Level determination:**

| Level | Description | Supported? |
|---|---|---|
| 1 | Real cases can be stored and retrieved | ✅ Yes — `cases_for(partition="real")` mechanically works, verified by genuine passing tests |
| 2 | Retrieval evaluated against real cases with defensible relevance labels | ❌ No — labels are self-authored by the retrieval algorithm's own author, not independently sourced |
| 3 | Real fault-history retrieval validated | ❌ No — same circularity, plus the harness is outside the automated test suite |
| 4 | Diagnosis validated against real ground truth | ❌ No — nothing in this repository compares an agent diagnosis to a real, independently confirmed field outcome |

`docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md` has been updated with an explicit methodology
caveat and its "Supported Claim" now discloses the curated (not independent) nature of the relevance
labels, so the P@1/P@3/R@3/MRR figures are not misread as Level-2-or-higher validation.

The 13/18/19 targeted test counts cited elsewhere (`test_real_case_retrieval.py`,
`test_real_historical_retrieval.py`) are genuine passing `pytest` assertions, but they test corpus
bookkeeping (partition purity, provenance fields, single hardcoded top-1 case IDs, temporal-cutoff
leakage prevention) — not ranking accuracy — and are correctly scoped to Level 1.

---

## 8. Partition Integrity

Traced `cases_for()` → `get_real_cases()` / `SYNTHETIC_CASES` / `get_all_cases()` in
`rai/memory/library.py`. **No cross-contamination path exists structurally**: `partition="real"` and
`partition="synthetic"` draw from disjoint code paths (the 14 audited records + `source_type`-filtered
field cases, vs. a hardcoded `SYNTHETIC_CASES` literal that never references real data). The one
dynamic decision point — `get_field_feedback_cases()`'s dual-key promotion check
(`library.py:668-671,724`) — is the actual attack surface (a bug there could mislabel a case), and it
is already covered by dedicated regression tests (`test_closed_loop_synthetic_feedback_stays_synthetic`,
`test_closed_loop_genuine_external_feedback_promoted_to_real`,
`test_unverified_operator_claim_stays_synthetic` in `tests/test_closed_loop_learning.py`).

`tests/test_real_historical_retrieval.py::test_real_synthetic_partition_separation`'s prior exact-equality
assertion (`len(all) == len(real) + len(synth)`) had already been relaxed to `>=` plus membership checks
in a staged, uncommitted edit from a different (concurrent) task. That relaxation was independently
verified as **necessary**, not cosmetic: `artifacts/tickets.jsonl` persists indefinitely across all
local test runs (306 accumulated entries at time of audit) and `get_all_cases()` legitimately includes
every field-feedback case regardless of promotion status. The relaxation does **not** weaken
cross-contamination detection — that is caught by untouched, per-element predicates earlier in the same
test (`assert all(c.source_type == ... for c in real_wind)` etc.), which fail unconditionally on any
leaked case regardless of list length. It did give up a duplicate/extraneous-entry check, which this
task restored (§9).

Also noted, not fixed (dead code, not a contamination vector): `rai/schemas.py`'s `HistoricalSourceType`
defines three near-synonymous "real" values (`REAL_EXTERNAL`, `EXTERNAL_REAL`, `HISTORICAL_REAL`); only
`EXTERNAL_REAL` is used anywhere. Worth pruning in a future cleanup task per the project's dead-code
policy — out of scope here.

---

## 9. Changes Made In This Task

1. `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` — corrected 16→14 case count and PVPMC→NREL PVDAQ
   solar-source attribution at all 6 confirmed locations; corrected fabricated pseudo-code to match the
   real `library.py::get_real_cases()` implementation.
2. `CHECKPOINT.md` — corrected the hand-maintained header line that contradicted its own body text.
3. `docs/evaluation/REAL_HISTORICAL_CASE_RETRIEVAL.md` — added an evaluation-methodology caveat
   (curated relevance labels, simulated query inputs, not part of the automated test suite), qualified
   the "Supported Claim" wording, and added the Gate 5.6B/PVDAQ-system cross-reference note.
4. `web/src/components/EvidenceAccordion.tsx` — the "REAL HISTORICAL CASE" badge no longer implies
   uniform confirmed-failure certainty: `event_class` now renders with a plain-language gloss and
   distinct (alarm-red only for `REAL_VERIFIED_EVENT`) styling instead of one flat neutral tone for
   every class, and the `fault_mode` line is no longer rendered in alarm color for non-fault real
   cases (operational/maintenance/environmental).
5. `tests/test_real_historical_retrieval.py` — tightened the corpus-size assertion to an exact `== 14`
   (was a loose `>= 12`), and added a uniqueness check plus explicit characterization of any "extra"
   elements in the `all` partition, restoring detection strength the prior `>=` relaxation had given up
   without reintroducing its false-failure risk against the persistent ticket ledger.

No changes were made to: Gate 5.6B/5.6C results or verdicts, CARE/Kelmarsh benchmark definitions, the
closed-loop architecture, the economic engine, or the dispatch optimizer, per the task's explicit
`DO NOT MODIFY` scope.

---

## 10. Final Output

```
REAL CASE COUNT:          14
WIND CASE COUNT:          12   (8 CARE + 4 Kelmarsh)
SOLAR CASE COUNT:          2   (both NREL PVDAQ OEDI — Systems 34 and 1283)
VERIFIED EVENT COUNT:      6   (EXTERNAL_REAL_VERIFIED_EVENT — all wind, all CARE)
OPERATIONAL EVENT COUNT:   4   (2 Kelmarsh trips + 1 PVDAQ outage + 1 CARE healthy-baseline, see §1 footnote)
MAINTENANCE EVENT COUNT:   2   (1 CARE human-error + 1 Kelmarsh scheduled)
ENVIRONMENTAL EVENT COUNT: 2   (1 Kelmarsh low-wind + 1 PVDAQ clipping; repo taxonomy keeps this
                                distinct from OPERATIONAL, see §2)
UNKNOWN COUNT:             0
EXCLUDED COUNT:            0
```
Classification basis for every count above: the `event_class` field set at construction time in
`rai/memory/real_corpus.py`, cross-checked against each record's own `adjudication.what_source_proves`
/ `what_source_does_not_prove` text (§1). No count required inference beyond what the source module
already states.

### What real case retrieval is currently proven to do
- Store, partition, and retrieve 14 genuinely externally-sourced historical records with complete
  provenance (dataset, license, event class, adjudication) and zero cross-contamination with the
  synthetic benchmark library.
- Correctly retrieve the intended top-1 case for hand-picked queries built from simulated telemetry
  (Level 1, self-consistency).
- Correctly abstain (return no match) when no candidate clears the similarity floor.
- Correctly refuse to let unpromoted or unverified field feedback enter the `EXTERNAL_REAL` partition.

### What it is NOT proven to do
- It does **not** constitute an independently validated information-retrieval benchmark (Level 2+) —
  the relevance labels are self-authored by the same team that built the algorithm.
- It does **not** validate real fault-history retrieval or agent diagnosis against real ground truth
  (Levels 3-4).
- It does **not** demonstrate that any solar case is a confirmed equipment failure — none of the 2 real
  solar cases are.
- It does **not** validate, or get validated by, Gate 5.6C's solar expected-performance model, despite
  reusing 2 of the same 3 PVDAQ Development-cohort systems — that gate's own verdict (`NOT VALIDATED`,
  empty validation cohort) is unchanged and unrelated.

**Final Verdict: PASS WITH DOCUMENTED LIMITATIONS.** The underlying corpus data and partition
mechanics were sound throughout (no contamination ever occurred); the defects found were entirely in
documentation framing (wrong count/source, un-caveated benchmark claims) and frontend presentation
(uniform badge styling), all corrected above without touching the corpus data, the retrieval algorithm,
or any locked gate result.
