# Gate 5.6 — Pre-Registered Scientific Audit Protocol

**Role**: Agent — Scientific Auditor (Claude/CLI), per the RAI Three-Agent Master Coordination
Prompt's Gate 5.6 role split (Builder = IDE Agent #1, Adversarial Verifier = IDE Agent #2,
Scientific Auditor = this role).

**Status of Gate 5.6 at time of writing: NOT YET STARTED.** Confirmed by direct repository search
(`artifacts/evaluation/gate56/` does not exist; no `scripts/gate56*`; no `docs/checkpoints/14-*`).
This document is written **before** any Gate 5.6 result exists, deliberately — a pre-registered
audit rubric, not a post-hoc one. The purpose is to fix the evaluation criteria in advance so
that when Gate 5.6 artifacts appear, they are checked against a standard set before the results
were known, not a standard shaped by the results themselves.

**This document contains no model, no fitted parameter, no result, and no claim about Gate 5.6's
eventual outcome.** It is a checklist, nothing else. It will be applied once the Builder (and
ideally the Adversarial Verifier) have produced artifacts under `artifacts/evaluation/gate56/`.

---

## Pre-flight findings (blocking dependencies the Builder must resolve first)

Checked directly, not assumed:

1. **No PVDAQ data exists in this repository yet.** `data/raw/` contains only `care/` (29GB, wind).
   There is no `data/raw/pvdaq/` or equivalent. Gate 5.5's own artifacts
   (`artifacts/evaluation/gate55/`) are inventory/audit documents only — no telemetry was
   downloaded during Gate 5.5, by its own explicit design ("the gate serves exclusively to audit,
   inventory, classify, and certify" — no data pull was in scope).
2. **No NREL/NLR API key is configured anywhere in this repo** (`rai/config.py`, `.env*` all
   checked — none found).
3. **Network reachability from this session's sandbox is inconsistent for the relevant domains**:
   `developer.nrel.gov` and `nsrdb.nrel.gov` and `data.openei.org` timed out; `developer.nlr.gov`
   (the renamed domain, live since 2025-12-01) responded but with a 503; `dkasolarcentre.com.au`
   (DKASC) responded 200; `github.com` (pvlib source) responded 200. This may be an artifact of
   this specific sandbox's egress rules rather than genuine unavailability — the Builder's own
   environment should re-verify independently rather than trust this result.
4. **Implication**: exactly like CARE's 29GB archive, PVDAQ data most likely needs to be manually
   acquired (registered API key + bulk download, or a pre-staged archive placed by the user) before
   Gate 5.6's Builder can do anything beyond code scaffolding. This is a legitimate blocker to flag
   now rather than let the Builder discover partway through — **whether the experimental design
   can even be executed against real data is itself part of "does the experimental design answer
   the research question."**

If Gate 5.6 proceeds without resolving this, the audit will treat any claimed PVDAQ-derived number
that cannot be traced to an actual downloaded file under `data/raw/` as **NOT_REPRODUCIBLE** by
the same standard applied to `care_2d` in the Gate 5.4R reconciliation.

---

## Audit Dimension 1 — Does the experimental design answer the stated research question?

The primary research question is: *can RAI construct a reliable solar expected-performance model
... producing a useful power residual on temporally held-out data and, where feasible, held-out
systems, without synthetic failure labels for fitting.* Checks:

- [ ] All three models (`PVLIB_PHYSICS_REFERENCE`, `SOLAR_EMPIRICAL_BASELINE`, `RAI_SOLAR_CHAMPION`)
      are actually implemented and evaluated — not just the Champion with the other two asserted
      as baselines from memory or literature.
- [ ] The comparison is run on the *same* held-out data for all three models (a fair race, not
      each model evaluated on a different slice).
- [ ] Chronological TRAIN/VALIDATION/TEST split is real and inspectable (`split_manifest.json`
      exists and the boundaries are dates, not row-shuffled indices).
- [ ] System-level holdout is attempted only if the cohort genuinely supports it; if not, the
      report says `INSUFFICIENT_DATA` rather than a weak claim dressed as generalization —
      per the master prompt's own instruction. This is exactly the discipline documented for the
      wind six-way matrix (C→A collapse was reported honestly, not hidden).
- [ ] "Does the hybrid Champion produce better health-oriented residuals" is evaluated on
      residual-quality diagnostics (bias vs. irradiance/temperature/time-of-day, heteroscedasticity,
      autocorrelation), not RMSE alone — the master prompt explicitly warns against reducing this
      to "which model has the lowest RMSE."

## Audit Dimension 2 — Do the claims match the evidence?

- [ ] Every "Final Question" answer carries one of `MEASURED_RESULT / SOURCE_DOCUMENTED /
      STATISTICAL_INFERENCE / INTERPRETATION / HYPOTHESIS / LIMITATION` and the label matches what
      was actually done (e.g., a claim about unseen-system generalization backed only by temporal
      holdout is a mislabeling, not a `MEASURED_RESULT`).
- [ ] None of the forbidden phrases appear ("solar predictive maintenance solved", "physical
      ground truth", "universal generalization", "state of the art", "production ready", "100%
      reliable") unless independently demonstrated — and "independently demonstrated" is checked
      against actual evidence, not asserted.
- [ ] Question 9 ("are the residuals suitable as inputs to Gate 5.7?") is classified `SUPPORTED /
      PARTIALLY_SUPPORTED / NOT_SUPPORTED / UNRESOLVED` with an argument, not a default optimistic
      answer — this mirrors Gate 5.5's own Q9 answer pattern, which should not be rubber-stamped
      forward without Gate 5.6's own evidence.
- [ ] Any `SIMULATED_OUTCOME` stress-test result is never referred to as "validation."

## Audit Dimension 3 — Is the physics/reference comparison fair?

- [ ] pvlib is never treated as ground truth to score the other two models against (the master
      prompt is explicit: "do not call pvlib output physical ground truth"). All three models
      should be compared against *actual measured power*, not against pvlib's output.
- [ ] Model-selection choices inside `ModelChain` (which DC model — SAPM/De Soto/CEC/PVsyst/
      PVWatts; which AC model — Sandia/ADR/PVWatts) are documented with a reason (data
      availability), not silently picked post-hoc because a particular combination scored best
      on TEST — that would be test-set leakage into model selection, one of the exact leakage
      modes the Adversarial Verifier is tasked to attack.
- [ ] `UNSUPPORTED_PHYSICS_CONFIGURATION` is actually used for systems lacking module/inverter
      metadata, rather than inventing plausible-looking parameters to force a physics run — check
      this against the per-system manifest, not the summary prose.
- [ ] The empirical baseline is given a genuinely fair shot (same train data, same evaluation
      protocol) — not implemented as a deliberately weak strawman to make the Champion look
      better by comparison. The master prompt is explicit: "Do not assume #3 wins. That's the
      experiment."

## Audit Dimension 4 — Are the selected PVDAQ systems appropriate?

- [ ] Inclusion/exclusion criteria for the evaluation cohort are recorded (`dataset_selection.csv`/
      `.json`) with an actual reason per excluded system, not a silent shrinkage from "100+
      systems" (Gate 5.5's inventory count) to a small final cohort.
- [ ] The final cohort size is checked against any generalization claim made from it — a claim of
      "unseen-system holdout" from, say, 2–3 systems is a `LIMITATION`, not a `MEASURED_RESULT`
      about generalization, regardless of what the numbers say.
- [ ] Per-system metadata completeness (tilt, azimuth, rated power, module/inverter model) is
      verified against the actual downloaded files, not assumed from Gate 5.5's aggregate "40+
      sites are READY" characterization — Gate 5.5 audited the *ecosystem*, not each individual
      system's file-level completeness.
- [ ] Regime-specific metrics (irradiance bands, temperature bands, time-of-day, clipping,
      curtailment, per-system) are reported separately, not folded into one aggregate score that
      could hide a bad regime.

## Audit Dimension 5 — Is "health evidence" being confused with "anomaly detection"?

This is the dimension most likely to be silently violated, and the one most worth watching:

- [ ] No precision/recall/F1/CARE-style detection score is reported against real PVDAQ data,
      because Gate 5.5 already established `nrel_pvdaq` has `NO_FAILURE_LABELS`. Any detection
      metric can only legitimately appear against `nrel_synthetic_outages`
      (`SIMULATED_OUTCOME`, clearly labeled) or DKASC's maintenance logs (clearly labeled
      `MAINTENANCE_LOGS`, and only as optional, non-tuned external validation per the master
      prompt) — never presented as if it were a benchmark result on the primary PVDAQ cohort.
- [ ] The health-evidence object (`quality_state`, `curtailment_state`, `clipping_state`,
      `residual_z`, `persistence_minutes`) is described and evaluated as *structured evidence for
      later reasoning*, not scored as a detector against ground-truth fault labels that do not
      exist for the primary cohort.
- [ ] If a `SIMULATED_OUTCOME` stress test is used to sanity-check that the residual actually
      moves when a fault is injected, its results are kept clearly separate from (not blended
      into) the real-data residual-quality metrics table, per the master prompt's `FAILURE
      LABELS` section.
- [ ] The final health-evidence schema matches the one specified by the user (asset_id,
      timestamp, actual/expected/residual power, residual_z, persistence_minutes, irradiance,
      temperature, quality/curtailment/clipping state) and is the thing downstream gates consume
      — not raw PVDAQ rows, preserving the architecture boundary the user was explicit about
      ("That becomes the future input to RAI → Needle → Qwen → RAG. Not raw PVDAQ.").

---

## How this connects to the Gate 5.4R precedent

Per the user's own framing: Gate 5.4R (this session's prior reconciliation of the two independent
Gate 5.4 experiments) is the canonical historical record for that gate, while the six-way
transfer matrix remains the canonical *experiment*. The same discipline applies here: this
protocol does not pre-judge Gate 5.6's outcome, does not silently change any Builder/Verifier
result, and if Gate 5.6 turns out to have its own version of a "Farm B active_power" discrepancy
(a real, quantified, disclosed divergence rather than a fabricated or hidden one), the correct
outcome is the same as before — document it, classify its severity, and recommend a follow-up,
not silently patch it or block the whole gate over a single disclosed and bounded issue.

## Addendum — Clean Restart Criteria (post-invalidation)

The originally-audited Gate 5.6 run was found **BLOCKED** and has been preserved as
`GATE_5.6_INVALID_SYNTHETIC_RUN` under `artifacts/evaluation/gate56_invalid_prior_run/`
(see that directory's `invalidation_manifest.json` for the full record: undisclosed synthetic
PVDAQ telemetry generated in-repo, and a physics-reference model that was algebraically
identical to the generating formula it was "validated" against). The following criteria are
added to this pre-registered rubric for the clean restart, and were fact-checked against current
pvlib documentation (pvlib 0.15.2, matching the version this project already pins) before being
written down — again, before any restart artifacts exist:

- [ ] **Synthetic-data tripwire**: no function resembling `generate_pvdaq_telemetry()` (or any
      code path that fabricates a canonical-field time series and labels it as PVDAQ) may exist
      in the restart's code path. `tests/test_gate56_circularity.py` must exist and must fail
      loudly if such a function is reintroduced or called.
- [ ] **Real acquisition, not just real-looking metadata**: every row of `dataset_selection.csv`/
      `candidate_systems.csv` must trace to a `source_url` + `sha256` + `retrieval_date` in
      `acquisition/download_manifest.json` and `acquisition/checksums.csv`. A system with a
      plausible real name and ID (e.g. "SYS_10", "NREL RSF") is **not sufficient evidence** of
      real acquisition — the invalidated run already proved that plausible-looking metadata can
      accompany fully fabricated telemetry.
- [ ] **Circularity check, verified against actual pvlib mechanics**: `ModelChain` infers its DC
      model from which parameter set is present on `PVSystem.arrays[i].module_parameters` —
      `{'A0','A1','C7',...}` → SAPM, `{'a_ref','I_L_ref','I_o_ref','R_sh_ref','R_s','Adjust'}` →
      CEC/De Soto, `{'pdc0','gamma_pdc'}` → PVWatts — and raises `ValueError: Could not infer DC
      model from the module_parameters attributes...` if none match
      ([pvlib ModelChain reference](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.html),
      [GitHub issue #1946](https://github.com/pvlib/pvlib-python/issues/1946)). The restart's
      physics reference must actually construct `pvlib.pvsystem.PVSystem` +
      `pvlib.location.Location` + `pvlib.modelchain.ModelChain` and call `run_model()` or
      `run_model_from_poa()` (the latter requires `poa_global`/`poa_direct`/`poa_diffuse` columns,
      defaulting `temp_air=20°C`/`wind_speed=0` if absent) — not a hand-written formula that
      happens to produce pvlib-like numbers. Confirm this by checking the manifest records real
      `ModelChain` model-name strings (e.g. `sapm`, `cec`, `pvwatts`) rather than a free-text
      description of a manually-coded equation.
- [ ] **`UNSUPPORTED_PHYSICS_CONFIGURATION` must be the documented response to the exact
      `ValueError` above**, for any system whose real metadata doesn't satisfy a parameter set —
      not a caught-and-silently-defaulted exception, and not an invented parameter set to force a
      model to run.
- [ ] **Independence of the "actual power" column from any model in the pipeline**: for real
      acquired data this is automatic (the actual power came from the utility meter/inverter
      log, not from any RAI code), but the auditor should still confirm the `actual_power_kw` /
      `ac_power` field used for scoring is read verbatim from the downloaded raw file (traceable
      to a `local_path` in `download_manifest.json`), never recomputed or "cleaned" through a
      model-shaped transformation before being used as the scoring target.
- [ ] Re-apply Audit Dimensions 1–5 from the original protocol above unchanged — they remain
      correct; only the acquisition/circularity layer needed strengthening.

Sources checked for this addendum:
[pvlib ModelChain user guide](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.html),
[run_model_from_poa reference](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.run_model_from_poa.html),
[pvlib-python GitHub issue #1946 on inference error messaging](https://github.com/pvlib/pvlib-python/issues/1946).

## Stop rule for this document

This protocol is complete and requires no further action until Gate 5.6 artifacts exist under
`artifacts/evaluation/gate56/`. At that point, this role will apply the checklist above against
the actual artifacts, `docs/checkpoints/14-solar-expected-performance.md`, and
`docs/evaluation/SOLAR_EXPECTED_PERFORMANCE.md`, and produce a Gate 5.6 audit verdict using the
same PASS / PASS WITH DOCUMENTED RECONCILIATION / BLOCKED categories used for Gate 5.4R. No model
will be built, no Solar code will be written, and no Needle/Qwen/RAG work will be started by this
role, per the master prompt's explicit scope boundary.
