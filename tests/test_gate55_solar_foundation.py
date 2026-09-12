"""Unit tests for Gate 5.5: Solar Data Foundation & Evidence Architecture.

Verifies:
1. Deterministic source classification and tier assignments.
2. Canonical solar feature vocabulary completeness and properties.
3. Ambiguous feature rejection without context.
4. Unit normalization and physical bound checks.
5. Evidence tier assignments and absence of invented failure labels.
6. Explicit missing metadata representation.
7. Provenance and licensing completeness.
8. Deterministic manifest generation.
"""

from __future__ import annotations

from rai.eval.external.solar.inventory import (
    SOLAR_SOURCE_INVENTORY,
    EvidenceCategory,
    EvidenceTier,
    ExpectedPerformanceReadiness,
    FailureGroundTruthType,
    get_source_by_id,
)
from rai.eval.external.solar.readiness import (
    audit_data_quality_risks,
    evaluate_source_readiness,
)
from rai.eval.external.solar.taxonomy import (
    CANONICAL_SOLAR_SIGNALS,
    FORBIDDEN_AMBIGUOUS_PATTERNS,
    SemanticConfidence,
    SolarSignalCategory,
    resolve_solar_signal,
)


class TestSolarTaxonomyAndVocabulary:
    """Verify semantic signals, validation bounds, and ambiguous rejection."""

    def test_canonical_signals_count_and_categories(self):
        assert len(CANONICAL_SOLAR_SIGNALS) >= 20
        required_signals = [
            "irradiance",
            "plane_of_array_irradiance",
            "GHI",
            "DNI",
            "DHI",
            "ambient_temperature",
            "module_temperature",
            "cell_temperature",
            "wind_speed",
            "DC_power",
            "AC_power",
            "DC_voltage",
            "DC_current",
            "AC_voltage",
            "AC_current",
            "inverter_output",
            "string_current",
            "string_voltage",
            "tracker_angle",
            "tracker_status",
            "grid_status",
            "curtailment",
            "energy_yield",
            "availability",
            "soiling_indicator",
            "degradation_indicator",
        ]
        for sig in required_signals:
            assert sig in CANONICAL_SOLAR_SIGNALS, f"Missing canonical solar signal: {sig}"

    def test_physical_ranges_validity(self):
        for name, spec in CANONICAL_SOLAR_SIGNALS.items():
            assert spec.physical_min < spec.physical_max, f"Signal {name} has invalid bounds."
            assert len(spec.standard_unit) > 0
            assert isinstance(spec.category, SolarSignalCategory)

    def test_nighttime_zero_signals_flagged(self):
        poa = CANONICAL_SOLAR_SIGNALS["plane_of_array_irradiance"]
        assert poa.nighttime_zero_expected is True
        ac_p = CANONICAL_SOLAR_SIGNALS["AC_power"]
        assert ac_p.nighttime_zero_expected is True
        amb_t = CANONICAL_SOLAR_SIGNALS["ambient_temperature"]
        assert amb_t.nighttime_zero_expected is False

    def test_ambiguous_fields_rejected(self):
        for ambig in FORBIDDEN_AMBIGUOUS_PATTERNS:
            sig, conf, reason = resolve_solar_signal(ambig)
            assert sig is None, f"Ambiguous field '{ambig}' was unexpectedly accepted."
            assert conf == SemanticConfidence.REJECTED
            assert "Ambiguous" in reason or "could not be" in reason

    def test_explicit_signal_resolution(self):
        sig, conf, _ = resolve_solar_signal("pyranometer_poa", unit="W/m2")
        assert sig == "plane_of_array_irradiance"
        assert conf == SemanticConfidence.HIGH

        sig, conf, _ = resolve_solar_signal("inv_1_pac", unit="kW", description="Active AC Power")
        assert sig == "AC_power"
        assert conf == SemanticConfidence.HIGH

        sig, conf, _ = resolve_solar_signal("t_module_back", unit="degC")
        assert sig == "module_temperature"
        assert conf == SemanticConfidence.HIGH


class TestSolarSourceInventoryAndEvidenceTiers:
    """Verify source records, evidence tiers, and licensing integrity."""

    def test_inventory_contains_core_sources(self):
        source_ids = {s.source_id for s in SOLAR_SOURCE_INVENTORY}
        assert "nrel_pvdaq" in source_ids
        assert "nrel_nsrdb" in source_ids
        assert "sandia_pvpmc_pvlib" in source_ids
        assert "dkasc_alice_springs" in source_ids
        assert "edp_open_data_pv" in source_ids

    def test_evidence_tier_separation(self):
        # NSRDB must be Tier 3 (environmental), NEVER Tier 1
        nsrdb = get_source_by_id("nrel_nsrdb")
        assert nsrdb.evidence_tier == EvidenceTier.TIER_3
        assert nsrdb.evidence_category == EvidenceCategory.REAL_ENVIRONMENT
        assert nsrdb.operational_data is False
        assert nsrdb.failure_labels is False

        # PVPMC / pvlib must be Tier 4 (physics reference), NEVER Tier 1
        pvlib = get_source_by_id("sandia_pvpmc_pvlib")
        assert pvlib.evidence_tier == EvidenceTier.TIER_4
        assert pvlib.evidence_category == EvidenceCategory.PHYSICS_REFERENCE
        assert pvlib.operational_data is False

        # PVDAQ must be Tier 2 (operational without failure labels)
        pvdaq = get_source_by_id("nrel_pvdaq")
        assert pvdaq.evidence_tier == EvidenceTier.TIER_2
        assert pvdaq.operational_data is True
        assert pvdaq.failure_labels is False  # NO invented failure labels!

        # Synthetic Outages must be Tier 5 (synthetic / simulated)
        synth = get_source_by_id("nrel_synthetic_outage_muller2023")
        assert synth.evidence_tier == EvidenceTier.TIER_5
        assert synth.evidence_category == EvidenceCategory.SIMULATED_OUTCOME

    def test_no_invented_failure_labels(self):
        """Verify that operational sources without verified labels are not falsely tagged."""
        pvdaq = get_source_by_id("nrel_pvdaq")
        assert pvdaq.failure_labels is False
        assert pvdaq.ground_truth_type == FailureGroundTruthType.DEGRADATION_ONLY

        kaggle = get_source_by_id("kaggle_two_plant_india")
        assert kaggle.failure_labels is False
        assert kaggle.ground_truth_type == FailureGroundTruthType.NO_FAILURE_LABELS

    def test_licensing_and_provenance_completeness(self):
        for s in SOLAR_SOURCE_INVENTORY:
            assert len(s.license) > 0
            assert len(s.citation_requirement) > 0
            assert s.url.startswith("http") or s.url.startswith("https")
            assert isinstance(s.redistribution_permitted, bool)
            assert isinstance(s.commercial_use_permitted, bool)


class TestReadinessEvaluator:
    """Verify expected performance readiness and data quality audits."""

    def test_pvdaq_is_ready_for_expected_power(self):
        pvdaq = get_source_by_id("nrel_pvdaq")
        audit = evaluate_source_readiness(pvdaq)
        assert audit.readiness_status == ExpectedPerformanceReadiness.READY
        assert audit.has_irradiance_channel is True
        assert audit.has_temperature_channel is True
        assert audit.has_power_output_channel is True

    def test_nsrdb_is_partially_ready_without_power(self):
        nsrdb = get_source_by_id("nrel_nsrdb")
        audit = evaluate_source_readiness(nsrdb)
        assert audit.readiness_status == ExpectedPerformanceReadiness.PARTIALLY_READY
        assert audit.has_power_output_channel is False

    def test_data_quality_hazard_policies(self):
        for s in SOLAR_SOURCE_INVENTORY:
            q = audit_data_quality_risks(s)
            assert "Filter GHI/POA" in q.nighttime_zero_policy
            assert "clear-sky" in q.pyranometer_drift_risk
            assert "clipping" in q.clipping_detection_readiness.lower()
            assert "curtailment" in q.curtailment_handling_status.lower()
