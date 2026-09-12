# Gate 5.4R — Reconciliation & Canonicalization: Summary

**Status: PASS WITH DOCUMENTED RECONCILIATION**

Two independently-produced "Gate 5.4" experiments exist in this shared working directory: this
session's CARE Fidelity Audit + RAI Integration (`artifacts/evaluation/external_care/`), and a
concurrent session's six-way Cross-Farm Wind Transfer & Target-Normal Calibration
(`artifacts/evaluation/gate54/`). This audit forensically compared them.

**Result: no direct numeric contradiction.** They use different detectors, different feature
policies, and overlapping-but-not-identical transfer directions — different questions on the same
dataset, not competing answers to the same question. Both are preserved in
`docs/evaluation/EXTERNAL_GENERALIZATION.md` as complementary evidence.

**Two issues found, both disclosed, neither blocking:**
- **D1 (HIGH)**: checkpoint 11's `RAI_CHAMPION`/`care_2d` = 0.000 claim is not reproducible — its
  producing script (`scripts/run_gate53_fast.py`) no longer exists in the repo. Retracted pending
  reproduction; do not cite it further.
- **D2 (HIGH)**: the six-way matrix's hand-curated Farm B `active_power` mapping
  (`power_58_avg`, "Available power") conflicts with RAI's own schema design (which explicitly
  rejects "available" as a power-signal alias) and with this session's independently-derived
  mapping (`power_62_avg`, "Active power"); the two columns correlate at only r=0.79. Real and
  material, but does not explain the matrix's C→A failure (Farm B is not involved in that
  direction) — flagged for a future substitution check, not resolved here.

One repo-hygiene fix recommended (D5: gitignore the 388MB `farm_data_cache.pkl` before the next
commit touching `artifacts/evaluation/gate54/`) and three low-severity process notes (D3, D6, D7)
requiring no action.

**Required outputs, all produced**: `experiment_registry.json`, `discrepancy_log.csv` (8 items,
D1–D8), `artifact_lineage.json`, `canonical_scorecard.csv` + `.json`, `claim_reconciliation.md`,
this `summary.md`.

**Scope discipline maintained**: no new model was built, no live re-run was performed against the
shared `artifacts/evaluation/gate54/` directory (to avoid racing the concurrent session), Solar
(Gate 5.5) and Needle2/Qwen3 agent-architecture work were left untouched, per this role's explicit
mandate. External fact-checking of the user's Needle2/Qwen3/NREL/NASA-battery/wind-transfer-
literature claims was also completed as requested background research; see note below.

**Notable external-research finding worth flagging to the Solar research agent (Role B)**: NREL
was renamed "National Laboratory of the Rockies" (NLR) effective 2025-12-01
(`developer.nrel.gov` retires 2026-05-29 in favor of `developer.nlr.gov`), and none of
PVDAQ/NSRDB/PVWatts/PVPMC-pvlib currently provide curated real-world fault/failure/anomaly labels
suitable for anomaly-detection benchmarking — PVDAQ is real operational data but unlabeled; NSRDB
is irradiance-only; PVWatts is a modeled-output calculator; pvlib/PVPMC ships only small synthetic
fault datasets. This is a gap the Solar gate will need to address (e.g., synthetic fault injection
on real PVDAQ telemetry, mirroring this project's own wind-simulator approach) rather than
expecting to find an off-the-shelf labeled solar-fault benchmark.

**Per role mandate: STOP here.** No further gates started.
