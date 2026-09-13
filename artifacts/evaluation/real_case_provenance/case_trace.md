# Real Historical Case Corpus & Field Feedback: Deep Forensic Trace

## Executive Summary

This document establishes the unbroken, verifiable provenance chain for every historical case and field feedback record in the Renewable Asset Intelligence (RAI) repository. Every claim regarding "real", "field-verified", or "historical" cases has been audited against primary dataset files, code paths, test fixtures, and runtime storage.

---

## 1. Inventory Summary & Classification Matrix

| Partition | Category | Count | Source Datasets | True Provenance | Adjudication |
|---|---|---|---|---|---|
| `real` | Audited Academic Wind | **12** | CARE to Compare (8), Kelmarsh (4) | Published open datasets (Zenodo) | **EXTERNAL_REAL** |
| `real` | Audited Academic Solar | **2** | NREL PVDAQ OEDI Systems 34 & 1283 | Public federal telemetry lake (OEDI) | **EXTERNAL_REAL** |
| `synthetic` | Illustrative Wind Scenarios | **8** | Internal incident logs (`knowledge/incidents/`) | Authored synthetic scenarios | **INTERNAL_SYNTHETIC** |
| `synthetic` | Illustrative Solar Scenarios | **6** | Internal incident logs (`knowledge/incidents/`) | Authored synthetic scenarios | **INTERNAL_SYNTHETIC** |
| `quarantine`| Test Run Work Orders | **40** | Unit test runs (`test_closed_loop_learning.py`) | Automated test execution artifacts | **INTERNAL_TEST_FIXTURE** |
| `demo` | Local UI Demo Tickets | **266** | Manual browser sessions / Playwright | Interactive simulation artifacts | **DEMO_SIMULATION** |

---

## 2. Tracing the 14 Genuine External Academic Cases (`EXTERNAL_REAL`)

### Wind Energy Cases (12 Cases)

#### A. Fraunhofer IEE — CARE to Compare (Zenodo 10.5281/zenodo.14006163 / 10958775)
1. **`REAL-CARE-A-072` (Gearbox High-Speed Shaft Bearing Failure)**
   - *Lineage:* Zenodo record 14006163, Wind Farm A, `event_info.csv` event ID 72.
   - *Data:* 10-minute SCADA averaging `sensor_11_avg` (HSS bearing temp, rose to 66.0°C) and `sensor_12_avg` (gearbox oil temp, rose to 58.0°C).
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Gearbox failure".
   - *Action:* Up-tower gearbox replacement during 7-day outage.
   - *Code Symbol:* `rai/memory/real_corpus.py:125`.

2. **`REAL-CARE-A-000` (Generator Drive-End Bearing Breakdown)**
   - *Lineage:* Zenodo record 14006163, Wind Farm A, `event_info.csv` event ID 0.
   - *Data:* `sensor_13_avg` (DE bearing, rose to 94.0°C) and `sensor_14_avg` (NDE bearing, rose to 86.0°C).
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Generator bearing failure".
   - *Action:* Generator bearing replacement and shaft alignment during 14-day outage.
   - *Code Symbol:* `rai/memory/real_corpus.py:180`.

3. **`REAL-CARE-A-068` (High-Voltage Transformer Phase L3 Breakdown)**
   - *Lineage:* Zenodo record 14006163, Wind Farm A, `event_info.csv` event ID 68.
   - *Data:* Phase temperatures `sensor_38_avg`, `sensor_39_avg`, `sensor_40_avg` (Phase L3 reached 125.0°C).
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Transformer failure".
   - *Action:* Pad-mount high-voltage transformer unit replacement during 14-day shutdown.
   - *Code Symbol:* `rai/memory/real_corpus.py:228`.

4. **`REAL-CARE-A-022` (Hydraulic Group Pressure Loss & Overheating)**
   - *Lineage:* Zenodo record 14006163, Wind Farm A, `event_info.csv` event ID 22.
   - *Data:* Hydraulic oil temperature `sensor_41_avg` reached 49.0°C with pressure loss alarms.
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Hydraulic group".
   - *Action:* Hydraulic pump overhaul, seal replacement, and oil top-up.
   - *Code Symbol:* `rai/memory/real_corpus.py:273`.

5. **`REAL-CARE-B-053` (Main Rotor Shaft Bearing 2 Mechanical Damage)**
   - *Lineage:* Zenodo record 14006163, Wind Farm B, `event_info.csv` event ID 53.
   - *Data:* Slow-speed shaft bearing thermal friction and standstill duration.
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Rotor Bearing 2 - Damage".
   - *Action:* Mobile crane mobilization and main bearing replacement (42-day standstill).
   - *Code Symbol:* `rai/memory/real_corpus.py:318`.

6. **`REAL-CARE-C-081` (Power Converter Filter Supply Fuse Blown)**
   - *Lineage:* Zenodo record 14006163, Wind Farm C, `event_info.csv` event ID 81.
   - *Data:* Instantaneous active generation drop from 1850 kW to 0 kW despite steady 9.2 m/s wind.
   - *Event Class:* `REAL_VERIFIED_EVENT`. Author ground truth: "Converter Failure: Fuse Filter Supply".
   - *Action:* Fuse filter supply replacement in converter cabinet (2-day outage).
   - *Code Symbol:* `rai/memory/real_corpus.py:363`.

7. **`REAL-CARE-C-044` (Cooling Water Valve Misposition / Human Error)**
   - *Lineage:* Zenodo record 14006163, Wind Farm C, `event_info.csv` event ID 44.
   - *Data:* Gradual thermal elevation in water cooling loop after scheduled service.
   - *Event Class:* `REAL_MAINTENANCE_EVENT`. Author note: "Valve in water cooling system was left in wrong position after maintenance actions".
   - *Action:* Manual repositioning of cooling valve. `equipment_fault = False`.
   - *Code Symbol:* `rai/memory/real_corpus.py:684`.

8. **`REAL-CARE-A-025-NORM` (Commercial Healthy Baseline Reference)**
   - *Lineage:* Zenodo record 14006163, Wind Farm A, `event_info.csv` event ID 25.
   - *Data:* Nominal SCADA tracking with residuals within +/-0.3 sigma.
   - *Event Class:* `REAL_OPERATIONAL_EVENT`. Author ground truth: "normal".
   - *Action:* None (healthy commercial operation). `equipment_fault = False`.
   - *Code Symbol:* `rai/memory/real_corpus.py:729`.

#### B. Plumley et al. — Kelmarsh Wind Farm (Zenodo 10.5281/zenodo.5841834)
9. **`REAL-KEL-1-FORCED-3000` (Operational Converter Unready Trip)**
   - *Lineage:* Zenodo record 5841834, Turbine Kelmarsh-1, `Status_Kelmarsh_1.csv` line 634.
   - *Data:* Greenbyte status code 3000 ("Frequency converter not ready"), 4-minute duration.
   - *Event Class:* `REAL_OPERATIONAL_EVENT`.
   - *Action:* Automated control reset; zero hardware damage. `equipment_fault = False`.
   - *Code Symbol:* `rai/memory/real_corpus.py:408`.

10. **`REAL-KEL-1-FORCED-2550` (Generator Cooling Fan Overload Trip)**
    - *Lineage:* Zenodo record 5841834, Turbine Kelmarsh-1, `Status_Kelmarsh_1.csv` line 1240.
    - *Data:* Greenbyte status code 2550 ("Overload generator fan 1"), 14-minute cooldown.
    - *Event Class:* `REAL_OPERATIONAL_EVENT`.
    - *Action:* Thermal protective reset; returned to operation. `equipment_fault = False`.
    - *Code Symbol:* `rai/memory/real_corpus.py:456`.

11. **`REAL-KEL-1-MAINT-0020` (Scheduled On-Site Maintenance Stop)**
    - *Lineage:* Zenodo record 5841834, Turbine Kelmarsh-1, `Status_Kelmarsh_1.csv` line 1225.
    - *Data:* Greenbyte status code 20 (IEC "Scheduled Maintenance"), blades pitched to 90 deg, 28 minutes.
    - *Event Class:* `REAL_MAINTENANCE_EVENT`.
    - *Action:* Routine scheduled technician inspection protocol. `equipment_fault = False`.
    - *Code Symbol:* `rai/memory/real_corpus.py:501`.

12. **`REAL-KEL-1-ENV-0010` (Low Wind Atmospheric Standstill)**
    - *Lineage:* Zenodo record 5841834, Turbine Kelmarsh-1, `Status_Kelmarsh_1.csv` line 23.
    - *Data:* Greenbyte status code 10 ("Out of Environmental Specification"), wind speed 2.1 m/s (< 3.0 m/s cut-in).
    - *Event Class:* `ENVIRONMENTAL_EVENT`.
    - *Action:* Automated cut-in logic restart upon wind recovery. `equipment_fault = False`.
    - *Code Symbol:* `rai/memory/real_corpus.py:546`.

---

### Solar Energy Cases (2 Cases)

#### C. NREL Open Energy Data Initiative (OEDI) — PVDAQ Telemetry Lake
13. **`REAL-PVDAQ-034-OUTAGE` (Midday Inverter Operational Outage)**
    - *Lineage:* NREL OEDI PVDAQ System 34 (Andre Agassi Bldg A, Las Vegas NV), 15-minute telemetry.
    - *Data:* AC power dropped to 0.0 kW during peak irradiance (POA = 852.4 W/m², module temp = 54.1°C), 3-hour outage on 2019-06-14.
    - *Event Class:* `REAL_OPERATIONAL_EVENT`.
    - *Action:* Reconnected and resumed normal tracking; root cause unlogged in public telemetry. `equipment_fault = False`.
    - *Code Symbol:* `rai/memory/real_corpus.py:591`.

14. **`REAL-PVDAQ-1283-CLIPPING` (Inverter Capacity Saturation / Clipping)**
    - *Lineage:* NREL OEDI PVDAQ System 1283 (NREL RSF II, Golden CO), 15-minute telemetry.
    - *Data:* Flat AC power plateau at inverter nameplate capacity (405 kW) while POA irradiance exceeded 980 W/m² on 2019-07-10.
    - *Event Class:* `ENVIRONMENTAL_EVENT`.
    - *Action:* None (designed electrical clipping behavior). `equipment_fault = False`.
    - *Code Symbol:* `rai/memory/real_corpus.py:639`.

---

## 3. Tracing the 6 Solar Cases (`CASE-S-001` through `CASE-S-006`)

These six cases were described in `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` and `CHECKPOINT.md` as "6 real cases from PVPMC". Forensic tracing proves this claim was erroneous:

- **Source Code:** Defined in `rai/memory/library.py:389-591`.
- **Source Label:** Explicitly tagged `source_type = HistoricalSourceType.INTERNAL_SYNTHETIC`, `evidence_quality = "SYNTHETIC_SCENARIO"`.
- **Underlying Text:** Authored illustrative scenarios based on incident log templates in `knowledge/incidents/`.
- **PVPMC Reality:** Sandia PVPMC is a collection of mathematical models and modeling guides implemented in `pvlib-python`. It contains equations for cell temperature, irradiance transposition, and soiling, but contains NO historical event retrieval cases in this repository.
- **Classification:** **Category C: Synthetic scenarios incorrectly classified in documentation.**
- **Remediation:** Preserved strictly in `INTERNAL_SYNTHETIC`; documentation corrected.
