# Source-Level Provenance Reconciliation

## 1. Solar Reconciliation: Gate 5.6B vs Retrieval Corpus

### Mandatory Comparison Against Frozen Gate 5.6B State

| Parameter | Gate 5.6B Solar Modeling State | Real Historical Retrieval Corpus |
|---|---|---|
| **Development Cohort** | Systems `[1239, 1283, 34]` | System 34 (`REAL-PVDAQ-034-OUTAGE`), System 1283 (`REAL-PVDAQ-1283-CLIPPING`) |
| **Validation Cohort** | `Validation = []` | None (No independent validation cohort) |
| **Validation Status** | **`INSUFFICIENT_DATA` / `NOT_INDEPENDENTLY_VALIDATED`** | Qualitative trajectory precedent retrieval only; **NOT model validation** |
| **Sandia PVPMC Role** | **Tier 4 Physics Reference** (De Soto, SAPM, Kimber) | **Tier 4 Physics Reference** (Zero retrieval cases) |
| **Cases in `EXTERNAL_REAL`** | N/A (Not an event retrieval system) | Exactly **2** cases (`REAL-PVDAQ-034-OUTAGE`, `REAL-PVDAQ-1283-CLIPPING`) |
| **Status of 6 Solar Cases** | N/A (Internal synthetic scenarios) | Quarantined in **`INTERNAL_SYNTHETIC`** (`CASE-S-001` to `CASE-S-006`) |

### Forensic Adjudication of the Six Solar Cases
The six solar cases (`CASE-S-001` through `CASE-S-006`) fall conclusively under:
**Category C: Synthetic/demo cases incorrectly classified in documentation.**

- **Why they are NOT Category A (genuine external cases unrelated to PVDAQ):**
  They do not possess an external dataset DOI, raw telemetry archive, or utility service record. Their source reference in code is `incident-log-solar-inverter`, an internal documentation template.
- **Why they are NOT Category B (derived from PVDAQ):**
  PVDAQ public data lakes contain continuous multi-channel SCADA measurements, but do not contain string-level combiner box maintenance tickets or capacitor bank ESR service logs.
- **Why they are NOT Category D (mixed/uncertain provenance):**
  Their origin is completely certain: they were authored as illustrative scenarios for the synthetic benchmark library. The code author explicitly documented this in `rai/memory/library.py:10-15`:
  > *"These are illustrative cases authored for this project from the incident logs in knowledge/incidents/, not a customer's maintenance history... A demo that passes off invented history as real history is the one failure mode this project refuses."*

### Preservation of Gate 5.6B Invariant
The 2 real solar cases in the retrieval corpus (`REAL-PVDAQ-034-OUTAGE` and `REAL-PVDAQ-1283-CLIPPING`) are drawn directly from the Gate 5.6B Development cohort (Systems 34 and 1283). They provide historical operational precedent for the retrieval KNN engine, but they do **NOT** constitute out-of-sample validation data. Gate 5.6B's frozen conclusion—`Validation = [] (INSUFFICIENT_DATA)`—remains completely intact and uncompromised.

---

## 2. Wind Reconciliation: Academic Datasets vs Live Field Feedback

### Distinction Between Dataset Evidence and Live Technician Verification

A crucial finding of this audit is that prior documentation occasionally conflated two distinct meanings of "real":

1. **Academic Dataset Ground-Truth (CARE / Kelmarsh):**
   - Publicly available, peer-reviewed open data archives (Zenodo).
   - Event labels were assigned post-hoc by academic researchers or SCADA alarm aggregators.
   - High evidentiary value for evaluating model retrieval and trajectory distance algorithms.
   - **Is it a live field deployment?** NO.

2. **Operational Closed-Loop Technician Field Feedback:**
   - Real-time work orders dispatched to on-site technicians via RAI's Operations Console.
   - Resolutions entered through the physical inspection feedback modal.
   - Requires dual-key verification (`EXTERNAL_FIELD_OBSERVED` + `FIELD_VERIFIED`) to enter `EXTERNAL_REAL`.
   - **Current Status in RAI:** The software lifecycle and API promotion pipeline are 100% verified, but zero commercial plants are currently connected. All records in `artifacts/tickets.jsonl` are test fixtures or demo simulations.

### Breakdown of the 12 Wind Cases
- **CARE to Compare (8 Cases):**
  - 6 Hardware Failures: Gearbox (`REAL-CARE-A-072`), Generator Bearing (`REAL-CARE-A-000`), Transformer (`REAL-CARE-A-068`), Hydraulics (`REAL-CARE-A-022`), Main Rotor Bearing (`REAL-CARE-B-053`), Converter Blown Fuse (`REAL-CARE-C-081`).
  - 1 Maintenance Induced Anomaly: Cooling water valve misposition (`REAL-CARE-C-044`).
  - 1 Normal Baseline: Nominal operation (`REAL-CARE-A-025-NORM`).
- **Kelmarsh Wind Farm (4 Cases):**
  - 2 Operational Trips: Converter unready (`REAL-KEL-1-FORCED-3000`), Fan thermal trip (`REAL-KEL-1-FORCED-2550`).
  - 1 Scheduled Maintenance: Routine service stop (`REAL-KEL-1-MAINT-0020`).
  - 1 Environmental Standstill: Wind speed below cut-in (`REAL-KEL-1-ENV-0010`).
- **Hardware Fault vs Operational Status Enforcement:**
  Under `test_anti_fabrication_boundary()`, operational and environmental events are strictly locked to `equipment_fault = False`.
