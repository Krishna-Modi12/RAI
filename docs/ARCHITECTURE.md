# Architecture — Renewable Asset Intelligence (RAI)

How telemetry becomes a defensible maintenance decision, and where the walls are.

Read `docs/PRD.md` for what the system must do, `docs/API_CONTRACT.md` for the frozen
interface, `docs/TECH_STACK.md` for what it is built from. Build status is marked per module;
at the time of writing the schema layer and the configuration/fleet registry are implemented
and everything else is **planned**.

---

## 1. The one-paragraph version

Telemetry is filtered for quality and operating state, compared against a per-asset
expected-behaviour model to produce residuals, fused across several independent detectors
into an anomaly score, then adjudicated against peers and environment to decide whether a
deviation is equipment or weather. What survives becomes a risk assessment and a compact
`EvidencePacket`. Only that packet reaches the local agent, which orchestrates read-only
tools — historical cases, knowledge retrieval, economics — and emits a schema-constrained
`AgentVerdict`. A human approves. The outcome feeds back into the case library.

The load-bearing idea: **numerical models predict, the agent investigates, Python does the
arithmetic, the human decides.**

---

## 2. Layered pipeline

```
   L0  SOURCE                                              module: rai/sim  (rai/ingest)
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Physics simulator: 42 assets, 45 days, 10-min wind / 15-min solar, seed 20260912 │
   │  + injected faults with exact ground truth (InjectedEvent)                        │
   │  In production this slot holds a SCADA/OPC-UA adapter. Nothing downstream changes. │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │  parquet per asset + site_met + events
                                       ▼
   L1  STORE                                                        module: rai/store
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  DuckDB over parquet. Windowed reads, peer-group aggregates, no server process.   │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │  tidy frame, tz-aware UTC
                                       ▼
   L2  QUALITY + STATE FILTER                                     module: rai/features
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Range / stuck-value / freshness checks  ->  SensorHealth                         │
   │  Operating-state classification           ->  OperatingState                      │
   │       normal | curtailed | derated | stopped | maintenance                        │
   │       below_cutin | above_cutout | night | unknown                                │
   │  RULE: below_cutin and night are NOT anomalies. Nothing scores until state is set. │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │  clean frame + state labels
                                       ▼
   L3  EXPECTED-BEHAVIOUR MODELS                                    module: rai/models
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Wind : IEC-style binned power curve + air-density correction, then XGBoost on    │
   │         (wind_speed, direction, density, ambient, state) per monitored signal     │
   │  Solar: pvlib clear-sky / POA + cell-temperature model, then XGBoost residual     │
   │  Output per signal: expected value + baseline sigma. Trained on healthy windows.  │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │  expected[]
                                       ▼
   L4  RESIDUALS                                                  module: rai/features
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  ResidualSignal: actual, expected, residual, residual_pct, z_score,               │
   │                  trend_per_day, trend_7d_per_day, baseline_sigma                  │
   │  z is normalised on the healthy-training residual distribution, so a temperature   │
   │  and a vibration channel become comparable. This is the currency of the system.   │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │  list[ResidualSignal]
                                       ▼
   L5  ANOMALY FUSION                                               module: rai/models
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  residual_z      (threshold settings.residual_z_alert = 3.0)                      │
   │  isolation_forest (multivariate outlier over the residual vector, sklearn)        │
   │  changepoint      (ruptures, step detection -> change_point_at)                   │
   │  -> fused anomaly_score in [0,1], each detector reporting its own score/fired     │
   │  -> persistence gate: settings.min_persistence_hours = 6.0                        │
   │  AnomalyEvidence{anomaly_score, detectors[], signals[], persistence_hours,        │
   │                  first_seen, change_point_at, dominant_signal}                    │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
              ▼                                                 ▼
   L6a PEER ATTRIBUTION                          L6b ENVIRONMENT ATTRIBUTION
   module: rai/models                            module: rai/models
   ┌───────────────────────────────┐             ┌──────────────────────────────────┐
   │ Same peer_group, same window: │             │ site_met + status codes + sensor  │
   │ kutch-row-a (9) kutch-row-b(9)│             │ health -> explains_fraction 0..1  │
   │ charanka-block-1/2 (12 each)  │             │ curtailment_detected              │
   │ -> deviation_percentile       │             │ -> EnvironmentVerdict             │
   │ -> PeerVerdict                │             │    environmental | partial |      │
   │    asset_specific | fleet_wide│             │    not_environmental              │
   │    | normal                   │             │ (+ SoilingEvidence for solar)     │
   └───────────────┬───────────────┘             └────────────────┬─────────────────┘
                   └──────────────────────┬───────────────────────┘
                                          ▼
                    THE GATE: an equipment fault may not be asserted while
                    environment or peers explain the deviation. "Low output"
                    is not a fault until weather, curtailment, peers and
                    sensor health have each been checked and recorded.
                                          │
                                          ▼
   L7  RISK                                                         module: rai/models
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  RiskAssessment{risk_score, risk_band, horizon_days=30, risk_window_days,         │
   │                 calibration, drivers{}}  — calibrated, named method, named drivers │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       ▼
   L8  EVIDENCE PACKET                              module: rai/features + services/api
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  EvidencePacket{asset_id, asset_type, generated_at, health_score, anomaly, risk,  │
   │                 peers, environment, soiling}                                      │
   │  .to_agent_dict() -> flat dict, top 4 signals by |z|, rounded.  <<< HARD BOUNDARY │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       ▼
   L9  LOCAL AGENT                                                   module: rai/agent
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Needle 2 (45M, local) OR the deterministic evidence reasoner — same contract.    │
   │  Tools (read-only):  get_asset_evidence · get_weather_context · get_soiling_      │
   │    estimate · search_similar_cases · search_knowledge · estimate_economic_impact  │
   │  Tool (confirm-required):  create_inspection_ticket                               │
   │            ├─ rai/memory     trajectory kNN over the case library                 │
   │            ├─ rai/rag        SQLite FTS5 over manuals / sops / incidents          │
   │            └─ rai/economics  option set, all arithmetic in Python                 │
   │  Budget: 5 tools/turn, 30 s timeout. Confidence < 0.80 -> requires_human_review.   │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       ▼
   L10 RECOMMENDATION                                                module: rai/agent
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  AgentVerdict{likely_cause, component, severity, confidence, requires_human_      │
   │    review, recommended_action, action_deadline_hours, evidence_summary[],         │
   │    historical_cases[], citations[], economics, model_used, fallback_used,         │
   │    tool_calls[], latency_ms}                                                      │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       ▼
   L11 HUMAN DECISION                                                     module: web
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Operator reads the evidence chain, accepts / defers / rejects, confirms a ticket. │
   │  The system recommends. It never acts on plant equipment.                         │
   └───────────────────────────────────┬─────────────────────────────────────────────┘
                                       ▼
   L12 FEEDBACK                                            module: rai/memory + rai/eval
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │  Outcome + technician finding -> new HistoricalCase -> retrieval improves.        │
   │  Confirmed / probable / maintenance-event / unknown are distinct labels;          │
   │  an unlabelled maintenance visit is never promoted to a failure label.            │
   └─────────────────────────────────────────────────────────────────────────────────┘
```

### What each layer may and may not do

| Layer | May | May not |
|---|---|---|
| L2 quality/state | label, mask, mark suspect | impute a value for display |
| L3 expected | predict what should be happening | be fit on a window containing the fault |
| L5 fusion | combine detector scores | fire on a single sample (persistence gate) |
| L6 attribution | reduce or veto an equipment claim | be skipped when short on time |
| L7 risk | produce a calibrated score | produce a number without a named calibration |
| L9 agent | select tools, explain, decide, escalate | compute anything, see raw telemetry, act on plant |
| L11 human | override anything | be bypassed for a physical action |

---

## 3. Module map

| Module | Responsibility | Key outputs | Status |
|---|---|---|---|
| `rai/schemas.py` | Every data contract. 20 models, `EvidencePacket.to_agent_dict()` is the agent boundary | all types below | **built, frozen** |
| `rai/config.py` | Fleet registry (42 assets, 2 sites, 4 peer groups), physics constants, `COMPONENT_ECONOMICS` (9 profiles), signal lists, thresholds | `FLEET`, `settings`, `economics_for()` | **built, frozen** |
| `rai/sim/` | Physics telemetry generator + fault injection, 12 scenarios, exact ground truth | `data/synthetic/*.parquet`, `events.parquet` | planned |
| `rai/ingest/` | Real-dataset adapters (CARE, Kaggle solar, NASA POWER) mapped into the canonical schema | normalised frames | planned, stretch |
| `rai/store/` | DuckDB-over-parquet access: windowed reads, peer aggregates, freshness | query helpers | planned |
| `rai/features/` | Quality filter, operating-state classification, residual construction, windowing, packet assembly | `ResidualSignal`, `EvidencePacket` | planned |
| `rai/models/` | Expected-behaviour models (wind, solar), anomaly fusion, peer engine, environment attribution, soiling, risk + calibration | `AnomalyEvidence`, `PeerEvidence`, `EnvironmentEvidence`, `SoilingEvidence`, `RiskAssessment` | planned |
| `rai/memory/` | Historical case library + trajectory kNN retrieval | `HistoricalCase` | planned |
| `rai/economics/` | Expected-loss model, option construction, avoidable exposure, priority score | `EconomicOption`, `EconomicEvidence` | planned |
| `rai/rag/` | Corpus ingestion, section chunking, SQLite FTS5 index, cited retrieval | `KnowledgeCitation` | planned |
| `rai/agent/` | Tool registry, Needle 2 runtime, deterministic fallback, confidence gating, verdict validation | `AgentVerdict`, `Investigation` | planned |
| `rai/eval/` | Split policy, leakage guards, detection/lead-time/calibration metrics, evaluation report | `artifacts/evaluation.json` | planned |
| `services/api/` | FastAPI implementing the 18 frozen endpoints, typed errors, SSE stream | JSON per `docs/API_CONTRACT.md` | planned |
| `web/` | Next.js operator interface: fleet command, asset investigation, simulator console, soiling, knowledge | — | planned (directory does not exist yet) |
| `knowledge/` | Illustrative maintenance corpus: `manuals/`, `sops/`, `incidents/` | source documents | directories exist, empty |
| `scripts/` | Build-time entry points: generate data, train, index, evaluate, warm up Needle | `artifacts/` | partial (`update_checkpoint.py` only) |

**Dependency direction is strictly downward.** `rai/agent` imports `rai/memory`,
`rai/rag`, `rai/economics` — never `rai/store` and never a parquet reader. `services/api`
imports everything; nothing imports `services/api`. `rai/schemas` imports nothing from the
project. A cycle here is a design error, not an inconvenience.

---

## 4. The three hard boundaries

These are the walls that make the system defensible. Each states what it forbids, why it
exists, and how it is enforced rather than merely intended.

### Boundary 1 — The LLM never sees raw telemetry. Only `EvidencePacket`.

```
   data/synthetic/WT-017.parquet          6,480 rows x 17 columns, 45 days
            │
            │   <-- rai/store, rai/features, rai/models live here
            ▼
   EvidencePacket  ──▶  .to_agent_dict()  ──▶  ~15 keys, top 4 signals by |z|
            │                                          │
            │                                          ▼
            │                                     ╔═══════════╗
            └── UI reads the full packet ─────────╢   AGENT   ║  sees only this
                                                  ╚═══════════╝
```

**Why.** Three independent reasons, any one of which is sufficient.

1. *Mechanical.* Needle 2 runs a 256-token sliding window. A single asset's 45-day history is
   roughly 110,000 numbers. There is no framing in which raw series fit, and truncating a
   series is worse than summarising it: the model then reasons about an arbitrary window with
   no idea what it missed.
2. *Hallucination surface.* A model handed a wall of numbers will narrate values it only
   half-parsed. A model handed four named z-scores can only talk about those four, and every
   sentence it produces is checkable against a field that exists.
3. *Auditability and privacy.* What the model saw is one small serialisable object. It can be
   stored with the investigation (`Investigation.packet`), replayed, diffed, and shown to an
   auditor. "The model saw the database" is not an auditable statement.

**Enforced by.** `to_agent_dict()` is the only serialiser the agent layer calls; `rai/agent`
has no import path to `rai/store` or to pandas/parquet readers; tools return computed
evidence objects, not frames. A test asserts the import graph.

### Boundary 2 — All arithmetic that matters happens in Python, never in the model.

```
   risk score · residual · z-score · energy loss · rupees · deadline hours
            │
            │  computed in rai/models, rai/economics  (deterministic, seeded, testable)
            ▼
   handed to the agent as values it may relay, compare and explain
            │
            ▼
   the agent contributes: which tool to call · which component · which option
                          · a severity · a confidence · an ordering of evidence
```

**Why.** A 45M-parameter model quantised to roughly 2 bits is a tool-calling controller, not
a calculator; vendor guidance says the same. But the deeper reason is that these numbers are
money and safety-adjacent, and they must be **reproducible**: the same evidence packet must
produce the same ₹ figure today and in the post-incident review. A model-generated number
cannot be regression-tested, cannot be unit-tested, and cannot be defended in a review
meeting. The division also happens to be the honest one — the numerical layer is where the
actual engineering is.

**Enforced by.** `EconomicEvidence` is constructed by `rai/economics` *before* the agent runs
and attached to the verdict; the agent's economic tool returns a precomputed option set and
the agent selects an `option_id`. Numeric fields in `AgentVerdict` are either copied from
Python structures or are the model's own calibrated confidence. Any free-text number in
`evidence_summary` that does not correspond to a packet field counts as an unsupported claim
and is measured as such (`unsupported_claim_rate`, target 0.00).

### Boundary 3 — The agent gets read-only tools plus ticket creation. Never physical control.

```
   ┌────────────────────── AGENT REACHABLE ──────────────────────┐
   │ get_asset_evidence      read   residuals, peer percentile   │
   │ get_weather_context     read   conditions, curtailment flag │
   │ get_soiling_estimate    read   soiling ratio, rate          │
   │ search_similar_cases    read   historical trajectories      │
   │ search_knowledge        read   cited document sections      │
   │ estimate_economic_impact read  precomputed costed options   │
   │ create_inspection_ticket DRAFT ── requires human confirm ───┼──▶ human
   └─────────────────────────────────────────────────────────────┘
                        ▓▓▓▓▓▓▓▓▓ WALL ▓▓▓▓▓▓▓▓▓
   ┌───────────────── NOT REACHABLE, NOT IMPLEMENTED ────────────┐
   │ setpoint writes · curtailment commands · breaker operation  │
   │ tracker/pitch/yaw actuation · SCADA writeback · grid dispatch│
   └─────────────────────────────────────────────────────────────┘
```

**Why.** Physical protection of a generating asset belongs to relays, SCADA/EMS and approved
control infrastructure, and must remain independent of an intelligence layer. Three
consequences follow. *Safety:* a wrong diagnosis costs one unnecessary inspection, not a
tripped turbine. *Security:* if the agent layer were compromised, the blast radius is a draft
ticket — there is no control channel to abuse, because no control client exists anywhere in
the dependency set. *Product:* the failure mode of the whole system is escalation to a human,
which is exactly what `requires_human_review` and the 0.80 confidence gate encode.

**Enforced by.** The tool registry is a closed, version-controlled list of Python functions;
six are pure reads, the seventh returns a draft object with `requires_confirmation`. No
Modbus, OPC-UA, MQTT or vendor-API client is installed (see `docs/TECH_STACK.md`) — you
cannot write to what you cannot address.

---

## 5. Request flows

### 5.1 `GET /api/assets/{asset_id}` — deterministic, no LLM

Note what is absent: the agent. The asset detail view is fully deterministic, so it is fast,
reproducible, and available even when the agent path is not.

```
 client
   │ GET /api/assets/WT-017
   ▼
 services/api/routers/assets.py
   │ 1. validate id against config.FLEET_BY_ID
   │    miss -> 404 {"detail": "unknown asset_id 'WT-999'", "code": "asset_not_found"}
   ▼
 rai/store
   │ 2. DuckDB: last N hours of data/synthetic/WT-017.parquet   (+ freshness)
   │ 3. DuckDB: same window for the 8 peers in kutch-row-b, aggregated
   │ 4. DuckDB: site_met.parquet for kutch-wind over the same window
   ▼
 rai/features
   │ 5. quality checks -> SensorHealth ; state classification -> OperatingState
   ▼
 rai/models  (artifacts/models/*.json loaded once at startup)
   │ 6. expected value + sigma for each of the 7 monitored signals
   │    no artifact -> 503 {"code": "model_not_trained"}
   ▼
 rai/features
   │ 7. ResidualSignal[] : residual, residual_pct, z, trend_per_day, trend_7d
   ▼
 rai/models
   │ 8. fusion  -> AnomalyEvidence (3 detectors, persistence, change point)
   │ 9. peers   -> PeerEvidence     (deviation percentile, verdict)
   │10. env     -> EnvironmentEvidence (explains_fraction, curtailment, verdict)
   │11. soiling -> SoilingEvidence  (solar only; null for wind, never 0.0)
   │12. risk    -> RiskAssessment   (band, window, calibration, drivers)
   ▼
 services/api
   │13. assemble AssetState + asset metadata, serialise per API_CONTRACT
   ▼
 client            target p95 < 800 ms   (measured: not evaluated)
```

`GET /api/assets` and `GET /api/fleet` run steps 2-12 across all 42 assets from a cached
state table refreshed on the simulator tick, not per request.

### 5.2 `POST /api/assets/{asset_id}/investigate` — the agent loop

```
 client
   │ POST /api/assets/WT-017/investigate   {"force_refresh": false}
   ▼
 services/api/routers/investigate.py
   │ create Investigation{investigation_id, started_at}
   │
   ├─[stage: telemetry]──────────  steps 2-7 of the flow above
   ├─[stage: expected_behavior]──  residuals + bands
   ├─[stage: environment]────────  EnvironmentEvidence (+ soiling for solar)
   ├─[stage: peers]──────────────  PeerEvidence
   │
   │   assemble EvidencePacket  ─────────────────────────────────┐
   │                                                             │
   │   rai/economics: costed option set for the implicated       │
   │   component, BEFORE the agent runs (Boundary 2)             │
   │                                                             ▼
   │                                          ╔══════════════════════════════╗
   ├─[stage: history]───────────────────────▶ ║  AGENT                       ║
   │    tool: search_similar_cases            ║  input: packet.to_agent_dict()║
   ├─[stage: knowledge]─────────────────────▶ ║  Needle 2 if weights present ║
   │    tool: search_knowledge                ║  else deterministic reasoner  ║
   ├─[stage: economics]─────────────────────▶ ║  budget 5 tools, 30 s         ║
   │    tool: estimate_economic_impact        ╚══════════════╤═══════════════╝
   │                                                         │
   ├─[stage: decision]───────────────────────────────────────┘
   │    validate against AgentVerdict schema
   │      invalid  -> retry once, then fall back to the deterministic reasoner
   │    confidence < settings.needle_confidence_threshold (0.80)
   │      -> requires_human_review = true, recommended_action downgraded to
   │         "escalate for engineering review", no auto-ticket
   │    agent unavailable and fallback disabled -> 503 {"code": "agent_unavailable"}
   ▼
 client   Investigation{packet, verdict, timeline[8], historical_cases, citations, economics}
          target p95 < 10 s end to end   (measured: not evaluated)
```

Two properties worth stating explicitly. The **timeline is emitted in stage order** so the UI
can animate an investigation rather than showing a spinner — the operator watches the
reasoning happen, which is most of the trust. And the **fallback is not an error path**: it
produces a verdict of the same shape with `fallback_used = true` and `model_used` set
truthfully, so a demo without model weights is a demo with an honest label, not a broken one.

---

## 6. Degradation behaviour

A missing artefact degrades one section, never the page.

| Missing | Endpoint behaviour | UI behaviour |
|---|---|---|
| `data/synthetic/*.parquet` | 503 `model_not_trained` / empty fleet | "no telemetry generated" state with the command to run |
| `artifacts/models/*` | 503 `model_not_trained` on affected endpoints | asset detail shows actuals, expected column blank |
| `artifacts/index/*` (FTS5) | `search_knowledge` -> 503 `index_not_built` | citations panel shows "knowledge index not built" |
| Needle weights | investigate still succeeds via fallback | header badge names the active engine, from `GET /api/health` |
| SSE stream | stream endpoint unavailable | client polls `GET /api/assets/{id}` every 5 s (contract-mandated fallback) |
| A signal absent for an asset | field is `null` | rendered as "not evaluated", never as `0` |

---

## 7. Deployment view

### Today — hackathon demo, one laptop, no network

```
   ┌────────────────────────── Windows laptop (this repo) ──────────────────────────┐
   │                                                                                │
   │   process 1   .venv/Scripts/python.exe -m uvicorn services.api.main:app         │
   │               127.0.0.1:8000     FastAPI + models in-process + agent in-process │
   │                    │                                                            │
   │                    ├── reads  data/synthetic/*.parquet        (DuckDB, no server)│
   │                    ├── reads  artifacts/models/*              (XGBoost boosters) │
   │                    ├── reads  artifacts/index/knowledge.db    (SQLite FTS5)      │
   │                    └── loads  Needle 2 in-process, or the deterministic reasoner │
   │                                                                                │
   │   process 2   npm run dev  ->  127.0.0.1:3000   Next.js operator UI             │
   │                    └── fetch/SSE to 127.0.0.1:8000                              │
   │                                                                                │
   │   build-time  scripts/: generate_data -> train -> build_index -> evaluate       │
   │               (run once; the demo never trains)                                 │
   └────────────────────────────────────────────────────────────────────────────────┘

   Zero containers. Zero database servers. Zero external calls at demo time.
```

The demo-time network dependency is exactly zero, which is not a stylistic choice: it is why
the demo cannot fail on stage the way a cloud-backed one can. It is also why `huggingface.co`
being unreachable in this build environment (verified: connection times out, `pypi.org`
returns 200) costs the demo nothing.

### Production story — an edge box inside the plant

```
                 plant LAN / OT network (no outbound telemetry)
   ┌──────────────────────────────┐          ┌────────────────────────────────────┐
   │ turbine / inverter SCADA     │  Modbus  │  RAI edge box                      │
   │ existing, untouched          │──OPC-UA─▶│  Raspberry Pi 5 (4-8 GB)  or       │
   │ protection & control stay    │  (adapter │  Jetson Orin Nano class            │
   │ entirely with relays/EMS     │  replaces │                                    │
   └──────────────────────────────┘  rai/sim) │  parquet + DuckDB   historian      │
                                              │  XGBoost boosters   expectation    │
   ┌──────────────────────────────┐           │  SQLite FTS5        knowledge      │
   │ site engineer's browser      │◀──HTTP───▶│  Needle 2  14 MB binary, ~28 MB    │
   │ (on the plant LAN)           │           │            RAM, ~500 tok/s decode  │
   └──────────────────────────────┘           │            on a Pi 5 (vendor claim)│
                                              └────────────────────────────────────┘
                                                        │  optional, opt-in
                                                        ▼
                                              site summary only (no raw telemetry)
```

Why this is credible rather than aspirational: the entire inference footprint is XGBoost
boosters (megabytes), a SQLite index (megabytes), and a 14 MB agent binary. There is no
PyTorch, no GPU requirement, no vector database, and no embedding model in the runtime
path — which is precisely why the stack in `docs/TECH_STACK.md` looks conservative. The same
code path runs on the laptop and on the Pi; only L0 changes.

The privacy argument becomes concrete at this point: there is no second service that *could*
receive the farm's data, because the reasoning engine is a file on the box.

### Scaling limits, stated honestly

42 assets fit comfortably in memory and in one process. Beyond roughly a few hundred assets
the per-tick state refresh and the single-queue ranking need revisiting; that is a real
limit, it has not been tested, and the architecture claims nothing above this fleet size.

---

## 8. Data and artefact layout

```
data/synthetic/
  WT-001.parquet ... WT-018.parquet        10-min cadence, 6,480 rows each (expected)
  INV-001.parquet ... INV-024.parquet      15-min cadence, 4,320 rows each (expected)
  site_met.parquet                          both sites, environmental reference
  events.parquet                            InjectedEvent ground truth (never rendered)
artifacts/
  models/     expected-behaviour boosters, detector params, risk calibrator
  index/      SQLite FTS5 knowledge index + case library
  evaluation.json                           the only source of any reported metric
knowledge/
  manuals/ sops/ incidents/                 illustrative documents, labelled as such
```

Expected total at the configured seed and cadence: 116,640 wind rows + 103,680 solar rows =
220,320 rows. This is arithmetic from `rai/config.py`, not a measurement — the simulator has
not been run and `data/synthetic/` is currently empty.

---

## 9. Design decisions worth defending

| Decision | Rationale |
|---|---|
| Residual z-scores as the universal currency | Makes a gearbox temperature and a vibration channel comparable, lets one fusion layer serve both asset types, and gives the agent a unit-free number it can reason about without arithmetic |
| Environment/peer attribution as a gate, not a feature | If it were a feature the model could learn to ignore it. As a gate, an equipment claim is structurally impossible while weather explains the deviation |
| Deterministic asset-detail path, agent only on investigate | The expensive, least predictable component runs on explicit user intent. The dashboard stays fast and reproducible |
| Ground truth from a simulator | Real public data has no reliable failure labels; without `InjectedEvent.onset` there is no honest lead-time number. The cost is domain realism, which is stated rather than hidden |
| Economics computed before the agent runs | Removes any temptation to let the model produce money, and makes the recommendation reproducible from the packet alone |
| Fallback reasoner implementing the same contract | The agent becomes a swappable component rather than a single point of failure, and the API shape is identical either way |
