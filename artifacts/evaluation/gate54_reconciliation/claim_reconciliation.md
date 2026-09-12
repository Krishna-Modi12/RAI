# Gate 5.4R — Reconciliation & Canonicalization: Claim Reconciliation

**Audit role**: Agent 1 — Scientific Auditor (Claude/CLI), scoped strictly to reconciling the
two independently-produced "Gate 5.4" experiments found in this shared working directory.
No new model was built, no Solar work was started, no agent/LLM architecture work was started,
per this role's explicit scope boundary.

**Inputs audited**: this session's own `docs/checkpoints/13-care-fidelity-rai-integration-gate54.md`
+ `artifacts/evaluation/external_care/`, versus the concurrent session's
`docs/checkpoints/12-cross-farm-transfer.md` + `artifacts/evaluation/gate54/`. Full findings are
in `experiment_registry.json`, `discrepancy_log.csv` (D1–D8), `artifact_lineage.json`, and
`canonical_scorecard.csv`/`.json`. This document answers the specific forensic questions posed
in the master coordination prompt.

## Q1 — Are the two Gate 5.4 experiments running the same code, same dataset, same feature
mappings, and same Champion implementation?

- **Same dataset**: Yes. Both read the identical on-disk `data/raw/care/` archive
  (CARE-to-Compare, Gück/Roelofs/Faulstich 2024, arXiv:2404.10320, Zenodo 14006163) — same
  turbine/dataset/raw-column counts per farm in both experiments' manifests
  (`experiment_registry.json`, `dataset` block). Neither re-downloaded or re-anonymized data.
- **Same Champion implementation**: Yes, with one addition, not a fork. Both use
  `rai/eval/external/care/champion.py`. The other session's experiment calls a new function,
  `recalibrate_rai_champion_target_normal` (added to the same file, not a separate copy), to
  implement `TARGET_NORMAL_CALIBRATED` recalibration. This session's own work does not call
  `champion.py` at all (it evaluates `isolation_forest`/`zscore_threshold` directly), so there is
  no version skew to reconcile there — only one experiment touches `champion.py`.
- **Same code otherwise**: No — and this is expected, not a defect. This session wrote three new
  modules (`feature_inventory.py`, `feature_policy.py`, `cross_farm_semantic.py`) to answer a
  *different* question (feature-resolution fidelity) than `scripts/gate54_cross_farm_transfer.py`
  (transfer robustness). Different code for different questions on the same dataset is expected
  and does not itself indicate a conflict.
- **Same feature mappings**: **Mostly, with one material exception.** Both approaches converge
  exactly on `rotor_speed` for all three farms (D4 — positive convergent evidence) and on
  `active_power`/`wind_speed` for Farms A and C. They diverge on Wind Farm B's `active_power`:
  the hand-curated `FARM_COMMON_MAPPING` picks `power_58_avg` ("Available power"), while this
  session's independently-built alias-scoring resolver picks `power_62_avg` ("Active power") —
  see **D2** below. This is the single most consequential finding of this reconciliation.

## Q2 — Why does checkpoint 11 report `RAI_CHAMPION`/`care_2d` = 0.000, and is that a bug in the
current code or a stale/irreproducible claim?

**It is not currently reproducible, and the evidence points to the latter (stale/irreproducible),
not a live defect in the current `champion.py`.** Checkpoint 11
(`docs/checkpoints/11-care-feature-rai-integration.md`) names its producing script as
`scripts/run_gate53_fast.py`. That file does not exist anywhere in the current repository (a
recursive filename search found nothing but a stale compiled `.pyc` for a since-deleted test
module). The current `scripts/gate53_cross_turbine_and_input_audit.py` contains no `care_2d` code
path at all — it cannot be re-run to reproduce the number. Direct inspection of the current
`champion.py::fit_rai_champion` shows that under a `care_2d` (2-signal: wind_speed, power only)
mapping, `has_power_model` should still resolve `True`, so a structural "0.000 on every farm"
result is not obviously explained by anything currently in the code — the most defensible
explanation is a bug or misconfiguration specific to the deleted script, not a defect that
persists today. **Verdict: retract the number as unreproducible (D1), do not carry it forward as
a claim, and do not silently "fix" it retroactively** — reproducing or formally retracting it is
future work outside this gate's mandate.

## Q3 — Which artifact directory is authoritative for which claim?

See `artifact_lineage.json` in full. Summary:
- `artifacts/evaluation/external_care/` — authoritative for CARE_NARROW vs CARE_SEMANTIC feature
  policy comparison, the feature inventory, and the A→B/A→C semantic cross-farm re-check.
- `artifacts/evaluation/gate54/` — authoritative for the six-way directed transfer matrix and its
  three conditions, **with the D5 (ungitignored cache) and D2 (Farm-B mapping) caveats attached**.
- `artifacts/evaluation/gate52/` + `gate53/` — authoritative for RAI_CHAMPION care_common/
  care_native scores (0.601/0.560/0.575) and the published-IF fidelity reproduction; explicitly
  **not** authoritative for any `care_2d` number (D1).
- `artifacts/evaluation/gate2/external_care/`, `gate51/`, `gate5_1/` — treated as one converged
  result (D7); no conflict to resolve.

## Q4 — Are the headline numbers byte-for-byte reproducible from the current repository state?

- **This session's own Gate 5.4 numbers**: Yes, confirmed live. Re-running the CARE_NARROW policy
  during this session's own work reproduced the pre-existing Farm A/B/C numbers exactly
  (0.5345/0.5062, 0.5324/0.4013, 0.5328/0.4388) — an actual determinism check, not an assumption.
- **The other session's six-way matrix**: **Structurally sound but not live-re-executed by this
  audit.** `scripts/gate54_cross_farm_transfer.py` uses a fixed seed (`20260912`, explicitly
  labeled `REPRODUCIBILITY_CHOICE` in its own manifest), deterministic polynomial fitting, and a
  seeded `RandomState` for its turbine-clustered bootstrap — nothing in the code is
  non-deterministic by inspection. This audit **deliberately did not re-run it live**, to avoid
  writing into the same `artifacts/evaluation/gate54/` output directory (and racing on the 388MB
  `farm_data_cache.pkl`, D5) that the concurrent session may still be actively using. This is a
  documented scope decision, not a finding of irreproducibility — see Q8.
- **care_2d (checkpoint 11)**: **Not reproducible** — see Q2/D1.

## Q5 — Is the Farm-B `active_power` discrepancy (D2) a real problem, and does it change any
scientific conclusion?

**Yes, it is real and material — but it does not overturn the six-way matrix's headline
conclusion, it qualifies it.** RAI's own pre-existing schema
(`rai/ingest/care.py::WIND_SIGNAL_SPECS["power_kw"].reject_tokens`) already encodes "available"
as a *rejected* token for `power_kw`, i.e., RAI's own design treats "available power" (a
theoretical/curtailment-ceiling quantity) as a different physical signal from delivered active
power. The hand-curated `FARM_COMMON_MAPPING` used by the six-way matrix nonetheless assigns
Farm B's `active_power` to `power_58_avg` ("Available power"), while this session's generic,
farm-policy-blind resolver — applying RAI's own existing alias/reject-token rules mechanically —
lands on `power_62_avg` ("Active power"). Empirically on Farm B's data the two columns correlate
at only r=0.79, with 33.6% of rows differing by more than 0.05 on their shared ~[0,1] scale: a
genuine, non-cosmetic divergence, not a data-quality tiebreak (both columns are fully populated).
Because the two problem directions in the six-way matrix are exactly `B→A` and `C→A` (not `B→C`
or `C→B`), and `power_58_avg` only touches Farm-B-involving transfers, **this discrepancy could
partially confound the B-related asymmetry numbers, but it cannot explain the C→A failure at all**
(C→A does not touch Farm B). The physical distribution-shift explanation for C→A (onshore vs.
offshore wind regime, rotor-speed medians 11.40 vs 7.98 rpm) stands independently of D2. The
recommended follow-up (re-run Farm-B `care_common` legs with `power_62_avg` substituted) is
flagged in `discrepancy_log.csv` D2 as future work, not performed here (would require writing into
the shared `gate54/` directory — same scope decision as Q4).

## Q6 — Are the two Gate 5.4 sections in `docs/evaluation/EXTERNAL_GENERALIZATION.md`
contradictory, and should one be deleted or merged?

**No contradiction found — preserve both, exactly as the user's own message proposed.** Per D8:
the two experiments use different detectors (`isolation_forest`/`zscore_threshold` vs.
`RAIChampionDetector`), different feature policies (auto-derived CARE_SEMANTIC, 6–13 signals, vs.
hand-curated CARE_COMMON, fixed 3 signals), and overlapping-but-not-identical transfer directions
(this session: A→B, A→C only; the other session: all 6 directed pairs). No single
`(source, target, detector, feature_policy)` tuple is reported by both sessions with conflicting
numbers. They answer different questions — *feature/schema fidelity* vs. *transfer/deployment
robustness* — and should both remain in the final report, clearly attributed to their own
methodology, per D8's recommendation.

## Q7 — What about the recurring pattern of duplicate/near-duplicate gates (5.1, 5.2, 5.3, 5.5)?

Documented in `experiment_registry.json` for completeness but **explicitly out of this gate's
scope** (the task brief scopes this audit to Gate 5.4 only). Gate 5.1's duplication (D7) is
confirmed harmless (both scripts converge on identical numbers). Gates 5.2 and 5.3 each have two
differently-named checkpoint docs claiming the same gate number; Gate 5.3's duplication was
partially investigated only insofar as it produced the care_2d claim (D1). These are flagged as
candidates for a future Gate 5.2R/5.3R reconciliation pass, not resolved here. Checkpoint-number
collisions at 10, 11, and 13 (D6) are cosmetic (filenames differ, no data was overwritten) but
degrade `CHECKPOINT.md` readability.

## Q8 — Why wasn't the six-way matrix live-re-executed to settle Q4/Q5 definitively?

A deliberate, documented risk-avoidance decision, not an oversight. `scripts/gate54_cross_farm_transfer.py`
writes to a hardcoded `artifacts/evaluation/gate54/` output directory and reuses/creates a 388MB
`farm_data_cache.pkl` there. The task brief that scoped this audit explicitly instructs that
concurrent work must be preserved, not overwritten or raced against; the other session's Gate 5.4
work is plausibly still active in the same shared working directory. Re-running the script live
risked corrupting or racing that in-progress state for a verification this audit could otherwise
complete via static code inspection (seed, determinism, manifest cross-checks). This is recorded
verbatim in `experiment_registry.json`'s reproducibility field for that experiment.

## Which claims belong in the final report?

Both Gate 5.4 sections belong, unmodified in their core claims, with the following disclosures
added:
1. The six-way matrix's Farm-B-involving rows (`A↔B`, `B↔C`, and by extension any claim that
   leans on Farm B's `active_power`) should carry a footnote citing D2 — the mapping choice is
   defensible but contested, and a substitution check is recommended future work.
2. Any `care_2d`/`RAI_CHAMPION` = 0.000 claim from checkpoint 11 must **not** be repeated as a
   validated result — it is retracted-pending-reproduction per D1.
3. The 388MB `farm_data_cache.pkl` (D5) should be gitignored before the next commit touching that
   directory, to prevent an accidental large-binary commit — this is a hygiene fix, not a
   correctness issue, and does not affect any reported number.
4. All other numbers in `canonical_scorecard.csv`/`.json` are COMPUTED and may be cited directly
   with their listed source artifact.

## Final Gate 5.4R Status

**PASS WITH DOCUMENTED RECONCILIATION.**

Both Gate 5.4 experiments are independently sound, methodologically complementary, and make no
directly contradictory numeric claim (D8). Two concrete issues require disclosure rather than
blocking: D1 (an unreproducible legacy number that must not be cited further) and D2 (a real,
quantified semantic-mapping choice on Farm B that qualifies but does not invalidate the six-way
matrix's conclusions). One repo-hygiene item (D5) should be fixed before the next commit. No
finding in this audit requires retracting, merging, or deleting either Gate 5.4 section.
