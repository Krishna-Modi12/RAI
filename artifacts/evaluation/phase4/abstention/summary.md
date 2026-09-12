# Explicit Abstention & Decision Safety Report (Phase 4)

## Executive Summary: Knowing When Not to Act

Autonomous maintenance engines that produce a confident recommendation on invalid telemetry represent catastrophic operational liabilities.
RAI implements a multi-gate evidence checker that explicitly yields **`policy = ABSTAIN`** whenever:
1. Sensor health is not `ok` (stuck, drifting, or missing)
2. Evidence score < 0.60 or persistence < required window
3. Environmental factors explain > 60% of telemetry variance
4. Confidence range width > 0.35 (severe epistemic uncertainty)

### Key Safety Metrics across 30 Stress Scenarios:
- **Dangerous Non-Abstentions (acting on broken/OOD data):** **0 of 30 (0.0%)**
- **Unnecessary Abstentions (withholding action on clear faults):** **0 of 30 (0.0%)**
- **Action Precision when Recommending Maintenance:** **100.0%**
- **Decision Coverage (Actionable scenarios):** `33.3%`

## Scenario Audit Table (Sample)

| ID | Category | Sensor Health | Env Expl | Confidence | Ground Truth | Policy Output | Action | Safe? |
|---|---|---|---|---|---|---|---|---|
| `ABST-01` | `CLEAR_FAULT` | `ok` | 8% | `[0.75, 0.92]` | `DEFECTIVE` | **`ACT`** | `repair_now` | ✅ SAFE |
| `ABST-02` | `CLEAR_FAULT` | `ok` | 12% | `[0.72, 0.89]` | `DEFECTIVE` | **`ACT`** | `repair_now` | ✅ SAFE |
| `ABST-03` | `SENSOR_FAILURE` | `failed` | 5% | `[0.70, 0.90]` | `SENSING_ERROR` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-04` | `SENSOR_FAILURE` | `suspect` | 10% | `[0.70, 0.85]` | `SENSING_ERROR` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-05` | `INSUFFICIENT_EVIDENCE` | `ok` | 20% | `[0.50, 0.65]` | `HEALTHY` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-06` | `ENVIRONMENTAL_DOMINATED` | `ok` | 85% | `[0.72, 0.88]` | `SOILING_OR_WEATHER` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-07` | `MODEL_UNCERTAINTY` | `ok` | 15% | `[0.35, 0.85]` | `AMBIGUOUS` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-08` | `OOD_REGIME` | `ok` | 70% | `[0.40, 0.68]` | `OOD` | **`ABSTAIN`** | `NONE` | ✅ SAFE |
| `ABST-09` | `CLEAR_FAULT` | `ok` | 10% | `[0.72, 0.86]` | `DEFECTIVE` | **`ACT`** | `repair_now` | ✅ SAFE |
| `ABST-10` | `EDGE_CASE` | `ok` | 60% | `[0.40, 0.40]` | `AMBIGUOUS` | **`ABSTAIN`** | `NONE` | ✅ SAFE |

## Conclusion
Explicit abstention operates as the definitive **operational governor** in RAI, ensuring that field crews are dispatched only when evidence meets strict scientific sufficiency standards.
