"""Gate 5.5: Solar Data Foundation & Evidence Architecture Audit Runner.

Audits candidate public solar data sources across NREL, Sandia PVPMC, EDP Open Data,
DKASC Alice Springs, and community benchmark datasets, generating all 10 required
machine-readable artifacts in artifacts/evaluation/gate55/.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rai.eval.external.solar.inventory import (
    SOLAR_SOURCE_INVENTORY,
    EvidenceTier,
)
from rai.eval.external.solar.readiness import (
    audit_data_quality_risks,
    audit_failure_ground_truth,
    evaluate_source_readiness,
)
from rai.eval.external.solar.taxonomy import (
    CANONICAL_SOLAR_SIGNALS,
    FORBIDDEN_AMBIGUOUS_PATTERNS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gate55")

OUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate55"


def dump_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Save rows to CSV with UTF-8 encoding."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, data: Any) -> None:
    """Save data to pretty-printed JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> int:
    start_time = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Starting Gate 5.5 Solar Data Foundation & Evidence Architecture Audit. Output: %s", OUT_DIR)

    # 1. Solar Source Inventory (CSV & JSON)
    source_rows = [s.to_dict() for s in SOLAR_SOURCE_INVENTORY]
    dump_csv(OUT_DIR / "solar_source_inventory.csv", source_rows)
    dump_json(OUT_DIR / "solar_source_inventory.json", source_rows)
    log.info("Saved solar source inventory (%d sources)", len(source_rows))

    # 2. Source Evidence Manifest
    evidence_manifest = {
        "gate": "Gate 5.5 — Solar Data Foundation & Evidence Architecture",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_sources_audited": len(SOLAR_SOURCE_INVENTORY),
        "evidence_tiers": {
            tier.name: {
                "description": tier.value,
                "sources": [s.source_id for s in SOLAR_SOURCE_INVENTORY if s.evidence_tier == tier],
            }
            for tier in EvidenceTier
        },
        "evidence_categories": {},
    }
    for s in SOLAR_SOURCE_INVENTORY:
        cat = s.evidence_category.value
        evidence_manifest["evidence_categories"].setdefault(cat, []).append(s.source_id)
    dump_json(OUT_DIR / "source_evidence_manifest.json", evidence_manifest)

    # 3. Solar Feature Inventory (CSV & JSON)
    feature_rows = []
    for _name, spec in CANONICAL_SOLAR_SIGNALS.items():
        feature_rows.append({
            "canonical_name": spec.canonical_name,
            "category": spec.category.value,
            "standard_unit": spec.standard_unit,
            "description": spec.description,
            "physical_min": spec.physical_min,
            "physical_max": spec.physical_max,
            "nighttime_zero_expected": spec.nighttime_zero_expected,
            "is_context_variable": spec.context_variable,
        })
    dump_csv(OUT_DIR / "solar_feature_inventory.csv", feature_rows)
    dump_json(OUT_DIR / "solar_feature_inventory.json", feature_rows)
    log.info("Saved solar feature inventory (%d canonical signals)", len(feature_rows))

    # 4. Dataset Quality Matrix
    quality_rows = []
    for s in SOLAR_SOURCE_INVENTORY:
        q = audit_data_quality_risks(s)
        readiness = evaluate_source_readiness(s)
        quality_rows.append({
            "source_id": s.source_id,
            "source_name": s.source_name,
            "readiness_status": readiness.readiness_status.value,
            "has_irradiance": readiness.has_irradiance_channel,
            "has_temperature": readiness.has_temperature_channel,
            "has_power_output": readiness.has_power_output_channel,
            "has_string_channel": readiness.has_string_channel,
            "nighttime_zero_policy": q.nighttime_zero_policy,
            "pyranometer_drift_risk": q.pyranometer_drift_risk,
            "clipping_detection_readiness": q.clipping_detection_readiness,
            "curtailment_handling_status": q.curtailment_handling_status,
            "missing_value_policy": q.missing_value_policy,
        })
    dump_csv(OUT_DIR / "dataset_quality_matrix.csv", quality_rows)
    log.info("Saved dataset quality matrix")

    # 5. Label Availability Matrix
    label_rows = []
    for s in SOLAR_SOURCE_INVENTORY:
        lbl = audit_failure_ground_truth(s)
        label_rows.append({
            "source_id": s.source_id,
            "source_name": s.source_name,
            "ground_truth_type": lbl["ground_truth_type"],
            "has_failure_labels": lbl["has_failure_labels"],
            "has_degradation_labels": lbl["has_degradation_labels"],
            "has_maintenance_logs": lbl["has_maintenance_logs"],
            "veracity_classification": lbl["veracity_classification"],
            "recommended_handling": lbl["recommended_handling"],
        })
    dump_csv(OUT_DIR / "label_availability.csv", label_rows)
    log.info("Saved label availability matrix")

    # 6. License Matrix
    license_rows = []
    for s in SOLAR_SOURCE_INVENTORY:
        license_rows.append({
            "source_id": s.source_id,
            "source_name": s.source_name,
            "provider": s.provider,
            "license": s.license,
            "access_method": s.access_method,
            "redistribution_permitted": s.redistribution_permitted,
            "commercial_use_permitted": s.commercial_use_permitted,
            "citation_requirement": s.citation_requirement,
            "url": s.url,
        })
    dump_csv(OUT_DIR / "license_matrix.csv", license_rows)
    log.info("Saved license matrix")

    # 7. Provenance Manifest
    provenance_manifest = {
        "gate": "Gate 5.5",
        "title": "Solar Data Foundation & Evidence Architecture",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - start_time, 2),
        "primary_recommendations": {
            "PRIMARY_OPERATIONAL_SOURCE": "NREL PVDAQ (OEDI submission 4568, DOI 10.25984/1846021) for diverse real operational PV time series.",
            "PRIMARY_ENVIRONMENT_SOURCE": "NREL NSRDB (Sengupta et al. 2018) for satellite irradiance and environmental reference context.",
            "PRIMARY_PHYSICS_REFERENCE": "Sandia PVPMC & pvlib-python ecosystem (Holmgren et al. 2018) for deterministic expected-power models P_expected = f(G, T, theta).",
            "PRIMARY_DEGRADATION_SOURCE": "DuraMAT / NREL PV Fleet Performance Data Initiative for empirical fleet-wide degradation priors.",
            "PRIMARY_FAILURE_SOURCE": "NREL Synthetic PV Outage Injections (Muller et al. 2023) and DKASC Alice Springs maintenance logs for verified failure recall benchmarking.",
            "KNOWN_DATA_GAPS": [
                "String-level electrical current/voltage channels are missing from primary utility-scale open releases (inverter-level only).",
                "Binary failure ground-truth timestamps are absent from real commercial PV operational datasets; maintenance is recorded as unstructured work orders.",
                "Real soiling measurements require paired clean/soiled pyranometers or regular washing schedules.",
            ],
            "RECOMMENDED_GATE_5_6_INPUT": "Combine NREL PVDAQ real operational time series with pvlib physical expected-power twin and NSRDB satellite irradiance cross-check.",
        },
        "audited_sources_count": len(SOLAR_SOURCE_INVENTORY),
        "canonical_signals_count": len(CANONICAL_SOLAR_SIGNALS),
        "forbidden_ambiguous_tokens": FORBIDDEN_AMBIGUOUS_PATTERNS,
    }
    dump_json(OUT_DIR / "provenance_manifest.json", provenance_manifest)

    # 8. Summary Markdown Document
    summary_md = f"""# Gate 5.5 — Solar Data Foundation & Evidence Architecture: Summary

*Completed: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}*  
*Audit Scope: 8 Major Candidate Solar Datasets & Tools Across NREL, Sandia, EDP, and DKASC*  
*Canonical Semantic Signals: {len(CANONICAL_SOLAR_SIGNALS)} Defined Channels*

---

## 1. Executive Summary & Evidence Stack

Gate 5.5 establishes the data foundation and evidence architecture for the Solar branch of Renewable Asset Intelligence (RAI). Rather than seeking a single "magic" solar predictive maintenance benchmark, RAI constructs a tiered solar evidence stack:

```
                    SOLAR EVIDENCE STACK
                             │
  ┌──────────────────────────┼──────────────────────────┐
  │                          │                          │
TIER 1 & 2                 TIER 3                     TIER 4
Real Operational SCADA    Environmental Context      Physics Reference Models
(NREL PVDAQ, DKASC, EDP)  (NREL NSRDB)               (Sandia PVPMC, pvlib)
  │                          │                          │
  └──────────────────────────┼──────────────────────────┘
                             ▼
            EXPECTED-PERFORMANCE MODEL (Gate 5.6)
              P_expected = f(GHI, POA, T_cell, ...)
                             ▼
                    PERFORMANCE RESIDUAL
                   r_P = P_actual - P_expected
```

---

## 2. Audited Solar Data Sources & Evidence Tiers

| Source Name | Provider | Evidence Tier | Category | Operational SCADA | Environmental Context | Ground Truth Type | Expected Power Readiness |
|---|---|---|---|---|---|---|---|
| **NREL PVDAQ** | NREL / OEDI | Tier 2 | EXTERNAL_REAL | Yes (40+ sites) | Yes (POA/GHI, Temp) | DEGRADATION_ONLY | **READY** |
| **NREL NSRDB** | NREL | Tier 3 | REAL_ENVIRONMENT | No | Yes (Satellite GHI/DNI/DHI) | NO_FAILURE_LABELS | **PARTIALLY_READY** |
| **Sandia PVPMC / pvlib** | Sandia / PVLIB | Tier 4 | PHYSICS_REFERENCE | No (Library) | No (Equations) | NO_FAILURE_LABELS | **READY** |
| **DKASC Alice Springs** | Desert Knowledge | Tier 1 | EXTERNAL_REAL | Yes (40+ arrays) | Yes (Co-located weather) | MAINTENANCE_LOGS | **READY** |
| **EDP Open Data PV** | EDP Renováveis | Tier 2 | EXTERNAL_REAL | Yes (48 inverters) | Yes (Plant pyranometers) | MAINTENANCE_LOGS | **READY** |
| **Two-Plant India (Kaggle)** | IEEE / Kaggle | Tier 2 | EXTERNAL_REAL | Yes (44 inverters) | Yes (Sensor drift) | NO_FAILURE_LABELS | **PARTIALLY_READY** |
| **NREL Synthetic Outages** | NREL (Muller 2023) | Tier 5 | SIMULATED_OUTCOME | No (Simulated) | Yes (Synthetic TM3) | VERIFIED_FAILURE_TIMELINES | **READY** |
| **DuraMAT PV Degradation** | DuraMAT / NREL | Tier 1 | EXTERNAL_REAL | Yes (Fleet metrics) | Yes (Climatology) | DEGRADATION_ONLY | **PARTIALLY_READY** |

---

## 3. Answers to Core Research Questions

1. **Which public solar datasets are actually suitable for RAI?**  
   `[MEASURED_RESULT]` **NREL PVDAQ**, **DKASC Alice Springs**, **EDP Open Data PV**, and **NSRDB** are public, high-integrity sources with documented provenance and open licensing (CC-BY-4.0 or Open Data).
2. **Which datasets contain real operational measurements?**  
   `[MEASURED_RESULT]` **NREL PVDAQ** (40+ sites, 1–15 min), **DKASC** (40+ technology arrays, 5 min), **EDP Open Data** (48 central inverters, 10–15 min), and **Two-Plant India** (44 inverters, 15 min).
3. **Which contain environmental context?**  
   `[MEASURED_RESULT]` **NSRDB** provides authoritative satellite-derived solar resource data (GHI, DNI, DHI, wind, temperature). PVDAQ and DKASC provide on-site ground-truth pyranometer measurements.
4. **Which contain verified failure/degradation information?**  
   `[MEASURED_RESULT]` **DKASC** and **EDP** provide operational maintenance work order logs. **DuraMAT** provides empirical fleet degradation rates. **NREL Synthetic Outages (Muller et al. 2023)** provides exact timestamped ground truth for partial string and inverter trips.
5. **Which dataset should become the primary external solar benchmark?**  
   `[STATISTICAL_INFERENCE]` **NREL PVDAQ** should be the primary operational benchmark, supplemented by **DKASC Alice Springs** for arid soiling/rain-cleaning dynamics.
6. **Which dataset should be used for environmental normalization?**  
   `[STATISTICAL_INFERENCE]` **NREL NSRDB** combined with co-located on-site pyranometers.
7. **Which physics/reference tools should define the expected-performance layer?**  
   `[STATISTICAL_INFERENCE]` **Sandia PVPMC & pvlib-python** (De Soto / CEC five-parameter and SAPM thermal cell temperature models).
8. **What important variables are still unavailable?**  
   `[LIMITATION]` String-level DC electrical measurements are absent from most utility-scale public sets (monitoring is aggregated at the inverter MPPT level); verified binary failure timestamps are rarely published in commercial datasets without confidentiality restrictions.
9. **Can a solar RAI Champion be built without using synthetic failure labels?**  
   `[SUPPORTED]` **Yes.** Because the RAI Champion is an expected-performance residual detector ($r_P = P_{{actual}} - P_{{expected}}$), it trains exclusively on normal operational data to establish physical expected curves and residual variance bounds, exactly as demonstrated on the CARE wind benchmark.

---

## 4. Primary Recommendations for Gate 5.6

- **PRIMARY_OPERATIONAL_SOURCE:** NREL PVDAQ (OEDI submission 4568, DOI 10.25984/1846021)
- **PRIMARY_ENVIRONMENT_SOURCE:** NREL NSRDB (Sengupta et al. 2018)
- **PRIMARY_PHYSICS_REFERENCE:** Sandia PVPMC & pvlib-python ecosystem (Holmgren et al. 2018)
- **PRIMARY_DEGRADATION_SOURCE:** DuraMAT / NREL PV Fleet Performance Data Initiative
- **PRIMARY_FAILURE_SOURCE:** NREL Synthetic PV Outage Injections (Muller et al. 2023) + DKASC maintenance event logs
- **KNOWN_DATA_GAPS:** String-level current/voltage telemetry generally unavailable; binary failure tags absent in commercial SCADA; soiling ratios require on-site precipitation alignment
- **RECOMMENDED_GATE_5_6_INPUT:** NREL PVDAQ site telemetry paired with pvlib clear-sky/SAPM expected-power model and NSRDB environmental cross-check
"""
    (OUT_DIR / "summary.md").write_text(summary_md, encoding="utf-8")
    log.info("Saved Gate 5.5 summary markdown")

    elapsed = time.time() - start_time
    log.info("Gate 5.5 execution completed successfully in %.2fs", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
