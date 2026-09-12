# Product Requirements — Renewable Asset Intelligence (RAI)

> We turn renewable-farm telemetry into an evidence-backed maintenance decision before a
> small anomaly becomes an expensive failure.

**Status of this document.** Requirements are written against the frozen contracts
(`rai/schemas.py`, `rai/config.py`, `docs/API_CONTRACT.md`). Every requirement carries a
build status. The repository now includes the simulator, stores, numerical model layers,
economics, historical memory, deterministic agent fallback, tests, and command-line
evaluation/demo paths. The REST endpoint layer and browser integration remain in progress.

**Scope of the build.** 24-hour hackathon. One machine, no cloud, no GPU, no internet at
demo time. The deliverable is a runnable system over a simulated-but-physically-grounded
fleet of 42 assets, not a research paper.

---

## 1. Problem

Unplanned failure of renewable equipment costs money in six places at once: lost
generation, emergency crew mobilisation, expedited parts, extended downtime, avoidable
secondary damage, and shortened asset life. For a wind gearbox, the frozen economics in
`rai/config.py` put a planned repair at ₹12.5 lakh and 36 hours of downtime against ₹45
lakh and 288 hours for the same failure taken unplanned — an 8x downtime multiplier and a
1.9x secondary-damage multiplier. The entire product exists inside that gap.

Degradation is gradual, and that is the difficulty:

```
healthy -> small deviation -> persistent deviation -> degradation -> warning signs -> failure
                      |                                     |
              where value is created              where alarms usually fire
```

A threshold alarm answers "is this sensor past a limit?". The question that creates value is
**"has this asset's behaviour changed in a way that is statistically, physically, and
operationally meaningful?"**

And renewables make that question genuinely hard, because output is dominated by weather.
Solar output moves with irradiance, cloud, cell temperature, soiling, shading, clipping and
curtailment. Wind output moves with speed, direction, air density, turbulence, pitch, yaw
and operating state. The consequence is the single sentence this product is built around:

> **Low output does not automatically mean broken equipment.**

Any system that skips environmental adjudication produces alerts that the site stops
reading within two weeks.

---

## 2. Why existing monitoring fails

Four distinct failure mechanisms, not one.

**Threshold alarms fire on weather and curtailment, not on faults.** A fixed limit on
`power_kw` or `gearbox_oil_temp_c` has no model of what the value *should* be at the current
operating point. Low wind, a hot afternoon, a grid curtailment window and an actual bearing
fault all cross the same line. The literature's fix — expected-behaviour (normal-behaviour)
modelling with residuals conditioned on operating point — is 15 years old and still not
standard in field monitoring. Conditioning on wind direction and air density alone removes
whole classes of false positives (Pandit et al., 2018, GP power-curve twins).

**SCADA alarms are reactive by construction.** SCADA is an excellent visibility and control
layer; its alarm codes are trip and protection events, which by definition fire at or after
the functional failure. Published vibration-CMS practice gives a P-F interval of roughly
3-6 months for wind drivetrain bearings, and SCADA temperature/power residuals typically
detect in the days-to-weeks range. The CARE dataset's labelled pre-failure windows span
4-98 days (Gück et al., 2024). An alarm code arriving at hour zero throws all of that away.

**Analysts drown in false positives.** Per-series alerting does not survive fleet scale: a
few thousand series produce alert storms, so the operator's real constraint is not recall but
**alerts per asset per month**. RAI therefore fixes an explicit alert budget
(`settings.false_alarm_budget_per_asset_month = 1.0`) and ranks a single queue instead of
emitting one alarm per series. Detection without ranking is not a product.

**Vendor monitoring is siloed and per-OEM.** Turbine and inverter portals each answer "what
is happening on my box", none answers "which of my 42 assets should a crew visit tomorrow,
and what does it cost me if they do not". There is no cross-asset peer comparison, no
historical-case memory, and no rupee figure attached to waiting.

The gap RAI occupies, in five questions SCADA does not answer:

| Question | SCADA | RAI |
|---|---|---|
| What is happening? | yes | yes |
| Is it abnormal *for this asset at this operating point*? | no | yes |
| Why — environment, sensor, or equipment? | no | yes |
| What has this pattern turned into before? | no | yes |
| What does it cost to act now versus in 14 days? | no | yes |

---

## 3. Target users

| User | Horizon | Decision they own | What they need from RAI |
|---|---|---|---|
| **Site O&M engineer** (Kutch Wind Farm / Charanka Solar Park) | today, this shift | Which assets a crew climbs or visits, in what order, with which spares | One ranked queue, and for the top item: what is wrong, how confident, what to carry, by when |
| **Asset performance manager** | this week / month | Where generation is being lost against budget; whether a loss is recoverable (clean, retune) or structural (repair, replace) | Expected-vs-actual yield per asset, loss attributed to soiling / environment / equipment, recoverable rupees |
| **Regional operations head** | quarter | Crew allocation and maintenance budget across sites; which risks are accepted deliberately | Fleet risk exposure in rupees, deferral consequences, an auditable record of why each call was made |

All three are inside the operator's network. None of them can send production telemetry to a
third-party cloud — which is a requirement, not a preference (see NFR-1).

### Jobs to be done

1. "When output drops, tell me within one shift whether I need to send a person — and prove it."
2. "Rank my fleet by what it costs me to wait, not by which sensor looks worst."
3. "Tell me if this has happened before on this fleet, and what it turned into."
4. "Tell me whether to wash Block 2 now or wait for rain, with the break-even."
5. "Give me a defensible reason for the maintenance I did not do."
6. "Do all of the above without my telemetry leaving the site."

---

## 4. Value proposition

RAI is an intelligence layer that sits *above* SCADA and produces one artefact: an
**evidence-backed maintenance decision**. Concretely, for each asset it produces a
`RiskAssessment`, an `EvidencePacket`, and an `AgentVerdict` carrying a component, a
severity, a deadline in hours, the residuals and peer/environment checks that justify it,
the historical cases it resembles, the document sections it cites, and a costed comparison of
acting now versus waiting.

Four things make it different from "another anomaly-detection dashboard":

1. **Environmental adjudication is mandatory, not optional.** An equipment fault cannot be
   asserted until weather, curtailment, peers and sensor health have been checked and
   recorded (`EnvironmentEvidence.explains_fraction`, `PeerEvidence.verdict`).
2. **Numbers come from Python, language comes from the agent.** The local model never
   computes a risk score, a residual, or a rupee. It orchestrates tools and explains.
3. **Every claim is traceable.** `AgentVerdict.evidence_summary` +
   `historical_cases` + `citations` + `economics.assumptions` — no free-floating assertions.
4. **It runs on a 14 MB local agent.** No cloud LLM in the data path, ever.

---

## 5. Functional requirements

Status legend: **built** = code exists and is executed; **planned** = specified, not yet
implemented. IDs are stable; other agents' checkpoint records reference them.

### 5.1 Fleet triage (FR-TRI)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-TRI-1 | Fleet summary: health, expected-yield %, assets at risk, assets offline, generation vs expected generation, availability, revenue at risk per day | `GET /api/fleet` | planned |
| FR-TRI-2 | Ranked action queue over all 42 assets, ordered by `revenue_at_risk_inr` x `risk_score` descending, one row per asset with component, risk band, risk window, recommended action, deadline hours, dominant signal | `GET /api/fleet/priority` | planned |
| FR-TRI-3 | Per-asset list view with health, risk, anomaly score, operating state, actual vs expected power, capacity factor, data freshness | `GET /api/assets` | planned |
| FR-TRI-4 | Priority must combine probability and consequence, never raw residual magnitude. An anemometer with a 4-sigma residual must rank below a gearbox with 3 sigma, because `COMPONENT_ECONOMICS` puts unplanned costs at ₹1.2 lakh versus ₹45 lakh | `rai/economics` | planned |
| FR-TRI-5 | Queue must respect the alert budget: at the frozen operating point, no more than ~1 false alarm per asset-month (`settings.false_alarm_budget_per_asset_month`) | `rai/eval` | planned |

### 5.2 Asset investigation (FR-INV)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-INV-1 | Per-asset state: asset metadata, current state, risk with named drivers, anomaly with per-detector scores, per-signal residuals (actual, expected, residual, residual_pct, z, trend/day, baseline sigma), peers, environment, soiling | `GET /api/assets/{id}` | planned |
| FR-INV-2 | Expected-behaviour models for both asset types producing an expected value **and** an uncertainty band per monitored signal (7 wind signals, 7 solar signals per `rai/config.py`) | `rai/models` | planned |
| FR-INV-3 | Time series of actual vs expected with band and residual z, plus event markers (`changepoint`, `alert`, `maintenance`, `curtailment`, `weather`, `repair`) | `GET /api/assets/{id}/timeseries` | planned |
| FR-INV-4 | Anomaly fusion over at least three independent detectors (residual-z, isolation forest, change point), each reporting its own score, threshold and fired flag | `AnomalyEvidence.detectors` | planned |
| FR-INV-5 | Persistence gating: a deviation is not an event until it survives `settings.min_persistence_hours` (6.0 h) — single-sample spikes never reach the queue | `rai/models` | planned |
| FR-INV-6 | Investigation run producing an 8-stage timeline (`telemetry`, `expected_behavior`, `environment`, `peers`, `history`, `knowledge`, `economics`, `decision`) and a schema-valid `AgentVerdict` | `POST /api/assets/{id}/investigate` | planned |
| FR-INV-7 | Risk assessment with band, 30-day horizon, a risk window in days, a named calibration method, and driver weights that sum to a stated basis | `RiskAssessment` | planned |

### 5.3 Environmental discrimination (FR-ENV)

This is the capability the product is judged on.

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-ENV-1 | For every deviation, compute the fraction explainable by environment (`explains_fraction`, 0-1) and emit a verdict of `environmental` / `partial` / `not_environmental` | `EnvironmentEvidence` | planned |
| FR-ENV-2 | Classify operating state before scoring: `normal`, `curtailed`, `derated`, `stopped`, `maintenance`, `below_cutin`, `above_cutout`, `night`, `unknown`. Below cut-in and night are not anomalies | `OperatingState` | planned |
| FR-ENV-3 | Curtailment detection independent of status codes (some operators curtail without setting one), using fleet simultaneity plus pitch/rpm signature for wind | `EnvironmentEvidence.curtailment_detected` | planned |
| FR-ENV-4 | Sensor-health adjudication: `ok` / `suspect` / `failed`, so a drifting anemometer or a frozen sensor is reported as a sensor fault, not a drivetrain fault | `SensorHealth` | planned |
| FR-ENV-5 | Peer comparison within the asset's own `peer_group` (`kutch-row-a`, `kutch-row-b`, `charanka-block-1`, `charanka-block-2`) with the subject's deviation percentile, returning `asset_specific` / `fleet_wide` / `normal`. WT-017 has 8 peers, INV-023 has 11 | `GET /api/assets/{id}/peers` | planned |
| FR-ENV-6 | The four environment-class simulator scenarios (`sensor_freeze`, `curtailment_window`, `cloud_transient`, `icing_event`) must be classified as **not** equipment faults; this is a measured acceptance criterion, not a demo talking point | `rai/eval` | planned |

### 5.4 Historical memory (FR-MEM)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-MEM-1 | Case library of past episodes with component, fault mode, observed signature, outcome, lead time in days, and repair cost, each labelled with its source | `HistoricalCase` | planned |
| FR-MEM-2 | Trajectory retrieval: given the current multi-signal residual trajectory, return the k most similar historical episodes with a similarity in 0-1 | `GET /api/assets/{id}/cases` | planned |
| FR-MEM-3 | Retrieved cases must carry their outcome, so the operator sees what the pattern turned into, not just that it matched | `HistoricalCase.outcome` | planned |
| FR-MEM-4 | Knowledge retrieval over the local maintenance corpus (`knowledge/manuals`, `knowledge/sops`, `knowledge/incidents`) returning document id, title, **section**, snippet and score | `GET /api/knowledge/search` | planned |
| FR-MEM-5 | Corpus documents must be clearly labelled as illustrative documents authored for this project; no OEM manual is reproduced | `GET /api/knowledge/docs` | planned |

### 5.5 Soiling intelligence (FR-SOIL, solar only)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-SOIL-1 | Per-inverter soiling ratio, loss %, accumulation rate in %/day, days since cleaning, days since rain, and the estimation method used | `SoilingEvidence` | planned |
| FR-SOIL-2 | Site-level soiling view with per-zone loss and performance ratio, dust risk, and the worst asset per zone | `GET /api/soiling` | planned |
| FR-SOIL-3 | Cleaning recommendation with an explicit break-even in days, comparing recovered energy at ₹2.45/kWh against a ₹42,000 per-block cleaning campaign, and against rain probability in the next 48 h | `GET /api/soiling` | planned |
| FR-SOIL-4 | Soiling loss must be separated from module degradation and from inverter derate; a soiling verdict must not be returned when peers in the same block show the same drop simultaneously with a cloud signature | `rai/models` | planned |

### 5.6 Economic decision (FR-ECON)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-ECON-1 | Costed option set per investigation, minimum: act now, defer 7 days, do nothing. Each option carries intervention cost, energy loss, failure-escalation cost, expected exposure, and failure probability | `EconomicOption` | planned |
| FR-ECON-2 | Every option carries its `assumptions` dict (downtime hours, capacity factor, tariff) and the UI must display them; a recommendation without visible assumptions is not shippable | `EconomicEvidence` | planned |
| FR-ECON-3 | Avoidable exposure = (expected exposure of the do-nothing branch) - (expected exposure of the recommended branch), computed in Python | `GET /api/assets/{id}/economics` | planned |
| FR-ECON-4 | Tariffs and component economics read from `rai/config.py` only (₹3.20/kWh wind, ₹2.45/kWh solar, 10% annual discount, 9 component profiles). No literal money in model code | `rai/config.py` | built |
| FR-ECON-5 | Deadline hours must be derived from the modelled P-F window for the fault mode (inspection interval a fraction of the P-F interval), not chosen for narrative effect | `AgentVerdict.action_deadline_hours` | planned |

### 5.7 Local agent (FR-AGENT)

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-AGENT-1 | Agent receives **only** an `EvidencePacket`, via `to_agent_dict()`, which caps the payload at the top 4 signals by absolute z-score. Raw telemetry never enters the context | `rai/agent` | planned |
| FR-AGENT-2 | Seven read-only tools plus one confirm-required ticket tool: `get_asset_evidence`, `get_weather_context`, `get_soiling_estimate`, `search_similar_cases`, `search_knowledge`, `estimate_economic_impact`, `create_inspection_ticket` | `rai/agent` | planned |
| FR-AGENT-3 | Output must validate as `AgentVerdict`. Free-form prose in place of the schema is a failure, not a degraded success | `rai/agent` | planned |
| FR-AGENT-4 | Confidence below `settings.needle_confidence_threshold` (0.80) sets `requires_human_review = true` and suppresses the auto-action. The failure mode is escalation, never wrong execution | `rai/agent` | planned |
| FR-AGENT-5 | Deterministic evidence reasoner implementing the identical `AgentVerdict` contract, used when Needle weights are unavailable, with `fallback_used = true` and `model_used` set truthfully | `rai/agent` | planned |
| FR-AGENT-6 | `GET /api/health` reports which reasoning path is live (`needle_available`, `needle_detail`) — the demo never silently pretends | `services/api` | planned |
| FR-AGENT-7 | Tool call budget of `settings.agent_max_tools_per_turn` (5) per turn and a hard timeout of `settings.agent_timeout_s` (30 s) | `rai/agent` | planned |

### 5.8 Simulator (FR-SIM)

The simulator is not a demo prop; it is the only source of ground truth in this build, and
therefore the only reason any evaluation number can be trusted.

| ID | Requirement | Contract | Status |
|---|---|---|---|
| FR-SIM-1 | Physics-grounded telemetry for 42 assets over `settings.sim_days` (45) at 10-min (wind) and 15-min (solar) cadence from `settings.sim_seed` (20260912) — an expected 116,640 wind + 103,680 solar = 220,320 rows | `rai/sim` | planned |
| FR-SIM-2 | Canonical column schema exactly as specified in the build brief, one parquet per asset, plus `events.parquet` and `site_met.parquet` | `data/synthetic/` | planned |
| FR-SIM-3 | Twelve injectable scenarios, eight equipment and four environment/sensor class, each emitting an `InjectedEvent` with `onset`, `detectable_from`, `is_equipment_fault` and `severity_final` | `GET /api/simulator/scenarios` | planned |
| FR-SIM-4 | Live injection with a time-acceleration multiplier, and reset, so a judge can watch detection happen | `POST /api/simulator/inject`, `/reset` | planned |
| FR-SIM-5 | `detectable_from` enables honest lead-time measurement: lead time = detection timestamp - `onset`, never - `detectable_from`, and the distinction must be stated wherever lead time is reported | `rai/eval` | planned |
| FR-SIM-6 | Ground truth is never rendered as a model output. `InjectedEvent` fields must not leak into `AssetState`, `EvidencePacket`, or the UI | `rai/eval` | planned |

---

## 6. Non-functional requirements

| ID | Requirement | How it is enforced |
|---|---|---|
| NFR-1 **Local-first** | The full pipeline runs on one laptop with no internet. No managed database, no container runtime, no external service in the request path | DuckDB + parquet on local disk; SQLite FTS5 index; agent is a local binary. See `docs/TECH_STACK.md` |
| NFR-2 **No cloud LLM** | No request to any hosted model provider, at any point, in code or demo. Telemetry is commercially sensitive; this is a product requirement, not a cost optimisation | Only `cactus-needle` (local) plus a pure-Python deterministic reasoner |
| NFR-3 **Honest metrics** | A metric that has not been computed is `null` and renders as "not evaluated". Every number in the UI traces to a computed artefact | `GET /api/evaluation` returns nulls; `CLAUDE.md` numerical-honesty rules; frozen contract forbids placeholder numbers |
| NFR-4 **No LLM arithmetic** | Risk, residuals, energy and money are computed in Python and handed to the agent | Boundary 2 in `docs/ARCHITECTURE.md`; `EconomicOption` produced before the agent is called |
| NFR-5 **Latency targets** | Targets, not measurements: fleet view p95 < 500 ms; asset detail p95 < 800 ms; investigation p95 < 10 s end to end; agent hard timeout 30 s (`settings.agent_timeout_s`). **Measured: not evaluated** | measured in the evaluation harness; `AgentVerdict.latency_ms` per run |
| NFR-6 **Time-ordered evaluation** | Time-ordered, per-asset-grouped splits. Never `shuffle=True`. Scalers fit on train only. Thresholds frozen on a validation window that ends before the test window begins | `rai/eval` leakage guards; split policy reported in `GET /api/evaluation` |
| NFR-7 **Determinism** | One seed (`settings.sim_seed`) reproduces the dataset, the injected events, and therefore every metric | seed in config; no wall-clock randomness in the simulator |
| NFR-8 **Graceful degradation** | A missing model, index, or agent returns a typed error (`model_not_trained`, `index_not_built`, `agent_unavailable`) and the UI degrades a section, never the page. Stale weather is labelled with its age | error codes in `docs/API_CONTRACT.md`; SSE stream has a documented polling fallback |
| NFR-9 **Auditability** | Every recommendation is reconstructible: evidence packet, tool calls, citations, assumptions, and which reasoning path produced it | `Investigation` persists `packet`, `verdict`, `timeline`; `fallback_used` recorded |
| NFR-10 **Units and time** | UTC tz-aware timestamps everywhere, INR for money, kWh for energy, kW for power, degrees Celsius. A naive timestamp at a +05:30 site shifts residuals by half a day and is treated as a bug | enforced in schemas and the store layer |
| NFR-11 **Footprint** | Must run within a laptop's RAM alongside the API and UI, and be portable to a Raspberry Pi 5 class box. No dependency above ~200 MB installed | torch and sentence-transformers rejected; see `docs/TECH_STACK.md` |

---

## 7. Success metrics

Two tiers. Tier 1 is what the demo is judged on; tier 2 is what makes tier 1 trustworthy.
**No value below has been measured yet** — targets are design commitments, and
`GET /api/evaluation` must return `null` for anything not computed.

### Tier 1 — demo metrics

| Metric | Target | Measured |
|---|---|---|
| Median detection lead time on injected equipment faults (relative to `onset`) | >= 3 days | not evaluated |
| Equipment-vs-environment classification accuracy over the 12 scenarios | >= 0.90 | not evaluated |
| False alarms per asset-month at the frozen operating point | <= 1.0 | not evaluated |
| Event recall at that operating point | >= 0.80 | not evaluated |
| Investigation latency, p95, end to end | < 10 s | not evaluated |
| Agent output schema-valid rate | 1.00 | not evaluated |
| Unsupported-claim rate in `evidence_summary` (claims not backed by a packet field) | 0.00 | not evaluated |

### Tier 2 — model quality

| Metric | Target | Measured |
|---|---|---|
| Wind expected-power MAE on the held-out test window | < 3% of rated (< 60 kW on 2 MW) | not evaluated |
| Solar expected-power MAE on the held-out test window | < 3% of rated (< 7.5 kW on 250 kW) | not evaluated |
| Risk model Brier score | < 0.12 | not evaluated |
| Risk calibration | monotone, method named (`RiskAssessment.calibration`) | not evaluated |
| Escalation rate (confidence below 0.80) | 0.10-0.25 (neither rubber-stamping nor useless) | not evaluated |

### Metric policy (non-negotiable)

- **Point-adjust F1 is not reported.** Under the point-adjust protocol, random noise can
  score near-perfectly, because hitting one sample inside an anomalous segment credits the
  whole segment (Kim, Cho & Kim, AAAI 2022). RAI reports event-wise recall with per-event
  coverage, and lead-time distribution.
- **Earliness is a headline metric, not a bonus.** A detector firing 6 days before failure is
  worth a multiple of one firing 12 hours before. This mirrors the CARE score's Earliness
  component (Gück et al., 2024).
- **The operating point is stated with every number.** One fixed threshold chosen by the
  stated policy ("<= 1 false alarm per asset-month"), plus a threshold-agnostic curve.
- **Prevalence is stated with every precision figure.** Events are a small fraction of
  asset-days; a precision number without its base rate is decoration.
- **Accuracy is never reported alone.** With a healthy-to-fault ratio in the thousands,
  "99% accurate" is a statement about the base rate, not about the model.

### Definition of done for the build

1. `scripts/` produces the dataset, trains models, builds the index, and runs the evaluation
   end to end from a clean checkout with one seed.
2. Every endpoint in `docs/API_CONTRACT.md` returns contract-shaped data or a typed error.
3. `GET /api/evaluation` returns real computed numbers, and the UI shows the nulls where
   they exist.
4. The WT-017 gearbox story and the INV-023 soiling story both run live, including one case
   where the system *declines* to call a fault.
5. `pytest tests/ -q` green.

---

## 8. Out of scope

Explicitly not built, and not implied anywhere in the UI:

- **Physical control of anything.** No setpoints, no curtailment commands, no breaker or
  tracker actuation, no writes back to SCADA. The agent's most powerful action is drafting a
  ticket that a human confirms. Protection stays with relays, SCADA/EMS and approved control
  infrastructure.
- **Real SCADA protocol integration.** No Modbus, OPC-UA, IEC 61850 or OEM API clients. The
  simulator is the telemetry source; a protocol adapter is a production-horizon item.
- **Module-level (individual panel) diagnosis.** Reporting stops at the inverter and string
  level because that is the observability we have. Claiming panel-level faults without
  panel-level telemetry is exactly the overreach this product argues against.
- **Remaining useful life in hours.** RAI emits a risk band and a risk window in days
  (`RiskAssessment.risk_window_days`), not "fails in 412 hours".
- **Vibration spectral analysis.** 10-minute averaged `drivetrain_vibration_mms` supports
  trend and residual analysis, not order or envelope analysis. No CMS hardware is assumed.
- **Multi-tenancy, authentication, RBAC, audit users.** Single-operator local deployment.
- **Cloud deployment, containers, orchestration.** Deliberately: see `docs/TECH_STACK.md`.
- **Work-order system integration** (SAP PM, Maximo, Upkeep). Ticket drafts are produced,
  not dispatched.
- **Live weather API ingestion at demo time.** Weather comes from the simulated site met file.
  A forecast adapter is planned-but-not-built, and any stale value is labelled with its age.
- **Energy market bidding, curtailment optimisation, storage dispatch.** Adjacent product.
- **Drone/thermal imagery, IV-curve tracing, oil sample chemistry.** Confirmation modalities
  belong to the technician's visit, which RAI schedules; it does not replace them.
- **Battery storage, offshore wind, tracker-axis control, hybrid plant modelling.**
- **Knowledge graph, blockchain provenance, foundation-model pretraining.** Time sinks with
  no demo value at this scale.
- **Training on real customer data.** The corpus is illustrative documents authored for this
  project, labelled as such at every retrieval.

---

## 9. What would make this fail in the field

An honest list. Each item is a mechanism that has broken real deployments, the design
response, and whether that response is built.

1. **Baseline contamination.** The expected-behaviour model is fit on a window that already
   contains degradation, so the fault becomes "normal" and residuals stay near zero. This is
   the most common silent failure in condition monitoring. *Response:* healthy-period
   selection plus change-point screening before fitting, and refusal to fit when no clean
   window exists. *Status: planned.*

2. **Sensor drift that biases the model's own input.** For wind, expected power is a function
   of the turbine's nacelle anemometer. If the anemometer drifts, the expectation drifts with
   it and the residual vanishes — the fault hides inside the model. *Response:* cross-check
   nacelle wind against the site met reference and peers, and adjudicate `SensorHealth`
   before trusting a residual; `anemometer_drift` is an explicit simulator scenario.
   *Status: planned (schema field exists, logic does not).*

3. **Curtailment without a status code.** A grid operator curtails, SCADA reports normal
   operation, and every asset on the feeder looks broken at once. *Response:* fleet
   simultaneity test plus pitch/rpm signature, surfaced as `PeerVerdict.FLEET_WIDE` and
   `curtailment_detected`, independent of `status_code`. *Status: planned.*

4. **The economic assumptions are the weakest number in the system.** Deadline hours and
   "act now" recommendations are driven by `COMPONENT_ECONOMICS` and the tariff, which are
   order-of-magnitude estimates for Indian utility-scale sites. A wrong downtime figure or a
   PPA tariff that differs from ₹3.20/kWh can flip the recommendation. *Response:* every
   `EconomicOption` carries its `assumptions` dict, the UI shows them, and they live in one
   config file so a site can correct them in a minute. It is a decision-support number, and
   it is labelled as one. *Status: config built, surfacing planned.*

5. **Missing channels.** Many farms have no vibration channel and no string-level current.
   A system that silently substitutes a default value produces confident nonsense.
   *Response:* absent signals are `null`, never imputed for display; confidence is reduced
   and the reason stated ("gearbox diagnosis confidence reduced: vibration telemetry
   unavailable"). *Status: schema supports it (`ResidualSignal` fields are optional);
   confidence logic planned.*

6. **Domain shift.** Models fit on this fleet's two asset classes do not transfer to a
   different OEM, rotor diameter, or climate. RAI must not claim otherwise. *Response:* the
   honest framing is fleet pretraining plus per-asset baseline adaptation; the cold-start
   path (asset-class prior, then personal baseline) is design, not code. *Status: planned.*

7. **Trust collapse after one bad truck roll.** A site that drives two hours for a cloud
   transient stops reading the queue permanently, and no later accuracy recovers it. This is
   why the alert budget is a hard constraint and why environmental adjudication is mandatory
   rather than advisory. *Response:* FR-ENV-6 is an acceptance test; the demo deliberately
   includes a declined fault call. *Status: planned.*

8. **Label poverty.** Real maintenance records say "maintenance performed" without a cause,
   so supervised training and evaluation quietly learn the wrong thing. *Response:* the case
   library distinguishes confirmed fault / probable fault / maintenance event / unknown
   cause, and an unlabelled maintenance event is never promoted to a failure label. In this
   build ground truth comes from the simulator, which is the only reason lead time is
   measurable at all. *Status: planned.*

9. **Alert storms at real fleet scale.** 42 assets is not 1,250. A ranking policy that works
   on 42 rows can still collapse into a 200-row queue on a real portfolio. *Response:*
   aggregate-then-rank architecture with a per-asset-month budget rather than per-series
   alerting; the scaling claim stays untested at this size and is stated as untested.
   *Status: planned, and explicitly unproven above 42 assets.*

10. **Stale environmental context during a network outage.** Detection continues locally, but
    dust and rain forecasts age. Acting on a two-day-old rain probability can waste a
    cleaning campaign. *Response:* freshness is carried and displayed
    (`AssetState.data_freshness_s`, weather age labelling) and confidence is reduced rather
    than the value being used silently. *Status: schema field built, labelling planned.*

11. **The agent path is unavailable.** Needle 2 fetches weights from `huggingface.co`, which
    is unreachable from this build environment (verified: connection times out, while
    `pypi.org` returns 200). A demo whose reasoning depends on a network fetch is a demo that
    fails on stage. *Response:* the deterministic evidence reasoner implements the same
    `AgentVerdict` contract and is the default path; `GET /api/health` states which engine is
    live. *Status: planned, and the primary reason it is planned this way.*

12. **Tool-description sensitivity.** Needle 2's behaviour is strongly dependent on how tools
    are described; an edit to a docstring can change which tool is selected. *Response:* tool
    descriptions are version-controlled source, not prompts assembled at runtime, and tool
    selection is asserted in tests. *Status: planned.*

---

## 10. Where the build actually stands

| Layer | State |
|---|---|
| `rai/schemas.py` — 20 data contracts | built, frozen |
| `rai/config.py` — 42-asset fleet, 2 sites, 9 component economic profiles, 14 monitored signals, thresholds | built, frozen; verified by execution |
| `docs/API_CONTRACT.md` — 18 endpoints, 6 error codes | frozen |
| `rai/sim`, `rai/store`, `rai/features`, `rai/models`, `rai/memory`, `rai/economics`, `rai/rag`, `rai/agent`, `rai/eval` | package directories exist, empty |
| `services/api` | package directory exists, empty |
| `web/` | does not exist yet |
| `data/synthetic/` | empty — no telemetry has been generated |
| `knowledge/{manuals,sops,incidents}` | directories exist, empty |
| `artifacts/{models,index}` | empty |
| Measured metrics | none |

Related documents: `docs/ARCHITECTURE.md` (how it is put together),
`docs/TECH_STACK.md` (what it is built from and what was rejected),
`docs/API_CONTRACT.md` (the frozen interface).
