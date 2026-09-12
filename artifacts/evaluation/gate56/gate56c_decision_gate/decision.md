# Gate 5.6C Decision Gate — Is a defensible real-fault-label solar validation route available?

*Date: 2026-09-13*
*This is a research/decision record, not a model gate. No model was fit, no ModelChain was run.*

## Question

Before building any solar expected-performance model against the real, adjudicated PVDAQ
cohort (Gate 5.6A + 5.6B: Development=[1239, 1283, 34], Validation=[] `INSUFFICIENT_DATA`,
Secondary-only=[1430, 1433]), is there a genuinely defensible source of real component-failure
event labels to validate against — or must modeling proceed without independent validation?

## Evidence consulted

1. **Gate 5.5's own prior audit** (`artifacts/evaluation/gate55/label_availability.csv`,
   already computed, not re-derived): of 8 candidate solar data sources, none has verified
   real-world acute-fault event labels at the SCADA/telemetry level.
   - `nrel_pvdaq` (our real acquired source) — `ground_truth_type=DEGRADATION_ONLY`,
     `has_failure_labels=False`, veracity=`HIGH_STATISTICAL`. Recommended use: "long-term
     health degradation modeling and soiling loss estimation; not for acute component trip
     detection."
   - `duramat_pv_degradation` — same classification, `DEGRADATION_ONLY`, no failure labels.
   - `dkasc_alice_springs` / `edp_open_data_pv` — `MAINTENANCE_LOGS` only, qualitative,
     `MEDIUM_QUALITATIVE` veracity, requires NLP/heuristic work-order-date extraction — weak
     and not integrable within the deadline.
   - `nrel_synthetic_outage_muller2023` — `VERIFIED_FAILURE_TIMELINES`, but explicitly
     `HIGH_SYNTHETIC`: a *synthetic* PV time-series with deliberately injected outages, not
     real operational telemetry.
   - `sandia_pvpmc_pvlib` / `nrel_nsrdb` — `NO_FAILURE_LABELS` (software / irradiance-only).
2. **External web search this gate** (bounded to 2 queries, not an open-ended literature
   review, per the deadline rule):
   - "public PV solar dataset real inverter fault labels ground truth event timestamps
     2024 2025" — surfaced only: (a) image/thermal defect-classification datasets
     (SolarFCD and similar) — a fundamentally different data modality (RGB/thermal
     imagery, not power/irradiance/temperature telemetry) that would require rebuilding
     acquisition and adjudication from zero, not integrable before the deadline; (b) a
     sparse-event inverter-fault-prediction study using a single-plant, 18-inverter,
     89-day SCADA dataset — no public download link surfaced, and even if available,
     acquiring + independently adjudicating a brand-new source with Gate 5.6A/5.6B's level
     of rigor is not achievable before the deadline; (c) academic papers analyzing fault
     mechanisms without an accompanying open, downloadable, event-labeled dataset.
   - "DuraMAT PV Fleet Performance Data Initiative dataset access fault labels public
     download" — confirmed DuraMAT's PV Fleet Data Initiative provides **performance loss
     rate (PLR) and degradation-trend data** from >250kW installations, not acute
     fault-event timestamps. This corroborates, rather than overturns, Gate 5.5's existing
     `DEGRADATION_ONLY` classification.
3. No source consulted provides a real, timestamped, component-level failure/fault event
   label for any of the 5 real PVDAQ systems in our own acquired cohort (1239, 1283, 34,
   1430, 1433) specifically.

## Decision: **PATH B — Solar modeling is feasible but not independently validated**

**Rationale:** A real, adjudicated telemetry cohort exists (Gate 5.6A/5.6B) and can support
a genuine expected-performance engineering pipeline (physics reference + empirical baseline
+ residual generation), which has real product/demo value (the "observed vs. expected"
journey the frontend needs). But no source — old or newly searched — provides real
component-failure event labels for these systems or any readily-integrable equivalent
within the time remaining before submission. Forcing a validation claim here would repeat
the exact `GATE_5.6_INVALID_SYNTHETIC_RUN` failure mode this project has already been
burned by once. Per the master task's own priority function (when options are close,
choose the simpler, more defensible one) and its explicit instruction not to chase
additional datasets without a concrete evaluation need, PATH B is the correct choice.

**What this means concretely for Gate 5.6C implementation:**
- Build `PVLIB_PHYSICS_REFERENCE` using an actual `pvlib.modelchain.ModelChain` (not a
  hand-rolled formula — the exact defect that caused the prior invalidation) against the
  real Development cohort [1239, 1283, 34], using only the CEC module/inverter matches and
  disclosed standard-preset assumptions already verified in `pvlib_readiness.csv` — no
  invented parameters.
- Build an empirical baseline fit strictly on real training-split telemetry.
- Generate residuals, quality-filter them (nighttime, clipping, curtailment — all
  pre-adjudicated in Gate 5.6B), and expose them through a typed evidence contract.
- Every result must be labeled `MODEL_DEVELOPMENT` / `NOT_INDEPENDENTLY_VALIDATED` in every
  artifact and doc that reports it. Tracking metrics (R², nRMSE) may be computed and
  reported as *internal self-consistency* diagnostics (e.g. residual autocorrelation,
  regime stability), never as "validated accuracy" or "generalization."
- A mandatory circularity tripwire test (mirroring `tests/test_gate56a_data_authenticity.py`)
  must assert the physics-reference model's implementation is never algebraically identical
  to anything that generated the input data — trivially true here since the input is real
  telemetry, not generated by any function in this repo, but the test must exist and pass
  before any Gate 5.6C result is reported.
- System-level holdout is not available (Validation=[] from Gate 5.6B) — Gate 5.6C must use
  a temporal holdout within the 3 development systems and say so explicitly; it must not be
  described as cross-system generalization.

## Deferred, not rejected: the synthetic-outage benchmark

`nrel_synthetic_outage_muller2023` (NREL's disclosed, purpose-built synthetic PV time series
with injected outages) is a legitimate resource for a *future* gate: it could validate a
residual/anomaly detector's precision/recall/lead-time against known injected-outage
timestamps, reported explicitly as `SYNTHETIC_INJECTED_OUTAGE_VALIDATION` — categorically
different from citing it as PVDAQ or real-world validation. This was not pursued in this
gate because (a) it requires acquiring and integrating a new external dataset from scratch,
which is exactly the kind of additional-benchmark scope the master task instructs against
chasing under deadline pressure, and (b) Path B's engineering foundation is higher product/
demo value per hour remaining. Recorded here so a future session does not have to
re-research this from zero.

## Go/No-Go

- **Scientific Go:** Yes — this decision is fully traceable to Gate 5.5's existing audit
  artifact plus two bounded, cited external searches; no claim here overstates the evidence.
- **Engineering Go:** Not yet — Gate 5.6C implementation has not started.
- **Reproducibility Go:** Yes — both search queries and their date are recorded above.
- **Product Go:** Yes — Path B still produces the observed/expected/residual pipeline the
  frontend demo journey needs.
- **Demo Go:** Yes, with an honest label — "expected performance vs. observed, with
  disclosed limitations" is an easy story for a judge to follow and does not require an
  unearned validation claim.

## STOP RULE compliance

No `ModelChain` was run. No expected-power model was fit. No residuals were generated. This
record is research/decision documentation only.
