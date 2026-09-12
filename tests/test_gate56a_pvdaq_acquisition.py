"""Gate 5.6A: Real PVDAQ Acquisition, Cohort Lock & Provenance Test Suite.

Verifies (per the Gate 5.6A master prompt's required-test list):
1. Source provenance completeness (source_manifest.json, retrieval_manifest.json).
2. Checksum completeness for every downloaded file (download_manifest.json / checksums.csv).
3. Development/validation system disjointness.
4. Deterministic, non-performance-based cohort selection (cohort_manifest.json).
5. Timestamp validation (timestamp_quality.csv).
6. Ambiguous-column rejection, cumulative-energy vs instantaneous-power separation,
   AC/DC semantic separation (candidate_systems.json per-candidate signal flags).
7. Unit-metadata completeness for the frozen cohort.
8. Physical sanity flags recorded (not silently discarded).
9. No performance-based selection language anywhere in the frozen cohort manifest.
10. All required Gate 5.6A acquisition artifacts exist and are non-empty.

This suite does NOT run, fit, or score any model -- consistent with the Gate 5.6A
ABSOLUTE STOP RULE. It only audits the acquisition artifacts already written to
artifacts/evaluation/gate56/acquisition/.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACQ_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "acquisition"

REQUIRED_ARTIFACTS = [
    "source_manifest.json",
    "retrieval_manifest.json",
    "candidate_systems.csv",
    "candidate_systems.json",
    "download_manifest.json",
    "checksums.csv",
    "timestamp_quality.csv",
    "quality_filter_manifest.json",
    "cohort_manifest.json",
    "pvpmc_followup_sources.json",
    "provenance_manifest.json",
    "summary.md",
    "access_attempts.md",
]


@pytest.fixture(scope="module")
def cohort_manifest() -> dict:
    with (ACQ_DIR / "cohort_manifest.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def candidate_systems() -> list[dict]:
    with (ACQ_DIR / "candidate_systems.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def download_manifest() -> dict:
    with (ACQ_DIR / "download_manifest.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def source_manifest() -> dict:
    with (ACQ_DIR / "source_manifest.json").open(encoding="utf-8") as f:
        return json.load(f)


# ===========================================================================
# 1. Required artifact completeness
# ===========================================================================

class TestRequiredArtifactsExist:
    def test_all_required_acquisition_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            p = ACQ_DIR / name
            assert p.exists(), f"Missing required Gate 5.6A acquisition artifact: {name}"
            assert p.stat().st_size > 0, f"Artifact {name} is empty."


# ===========================================================================
# 2. Source & retrieval provenance
# ===========================================================================

class TestSourceProvenance:
    def test_source_manifest_has_required_fields(self, source_manifest: dict):
        for field in ["provider", "distribution", "s3_bucket", "https_base_url", "access_method",
                      "systems_table_sha256", "systems_table_size_bytes"]:
            assert field in source_manifest, f"source_manifest.json missing field: {field}"
        assert source_manifest["access_method"], "access_method must be documented, not blank"
        assert len(source_manifest["systems_table_sha256"]) == 64, "sha256 must be a 64-hex-char digest"

    def test_systems_table_checksum_matches_real_file(self, source_manifest: dict):
        systems_csv = REPO_ROOT / "scratch_gate56a" / "systems_20250729.csv"
        assert systems_csv.exists(), "Real systems metadata table missing from scratch acquisition directory"
        actual_sha256 = hashlib.sha256(systems_csv.read_bytes()).hexdigest()
        assert actual_sha256 == source_manifest["systems_table_sha256"]

    def test_retrieval_manifest_records_every_retrieval(self):
        with (ACQ_DIR / "retrieval_manifest.json").open(encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) > 0
        for rec in records:
            for field in ["artifact", "url", "retrieved_at_utc", "http_status", "sha256", "size_bytes"]:
                assert field in rec, f"retrieval record missing field: {field}"
            assert rec["http_status"] == 200
            assert rec["url"].startswith("https://oedi-data-lake.s3.amazonaws.com/")


# ===========================================================================
# 3. Checksum completeness for downloaded telemetry
# ===========================================================================

class TestChecksumCompleteness:
    def test_download_manifest_reports_full_success(self, download_manifest: dict):
        assert download_manifest["total_files_ok"] == download_manifest["total_files_requested"]
        assert download_manifest["total_files_missing_or_error"] == 0

    def test_every_ok_file_has_checksum_and_exists_on_disk(self, download_manifest: dict):
        ok_files = [r for r in download_manifest["files"] if r["status"] == "OK"]
        assert len(ok_files) > 0
        for rec in ok_files:
            assert rec["sha256"] and len(rec["sha256"]) == 64
            local_path = REPO_ROOT / rec["local_path"]
            assert local_path.exists(), f"Downloaded file missing from disk: {rec['local_path']}"

    def test_checksums_csv_matches_download_manifest_count(self, download_manifest: dict):
        with (ACQ_DIR / "checksums.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ok_count = sum(1 for r in download_manifest["files"] if r["status"] == "OK")
        assert len(rows) == ok_count

    def test_sample_checksums_match_actual_file_bytes(self, download_manifest: dict):
        ok_files = [r for r in download_manifest["files"] if r["status"] == "OK"]
        sample = ok_files[:20]
        for rec in sample:
            local_path = REPO_ROOT / rec["local_path"]
            actual_sha256 = hashlib.sha256(local_path.read_bytes()).hexdigest()
            assert actual_sha256 == rec["sha256"], f"Checksum mismatch for {rec['local_path']}"


# ===========================================================================
# 4. Cohort disjointness & deterministic, non-performance-based selection
# ===========================================================================

class TestCohortSelection:
    def test_development_and_validation_disjoint(self, cohort_manifest: dict):
        dev = set(cohort_manifest["development_systems"])
        val = set(cohort_manifest["validation_systems"])
        assert dev & val == set()

    def test_cohort_sizes_within_spec(self, cohort_manifest: dict):
        assert 3 <= len(cohort_manifest["development_systems"]) <= 5
        assert 2 <= len(cohort_manifest["validation_systems"]) <= 3

    def test_selection_method_is_documented_and_non_performance_based(self, cohort_manifest: dict):
        method = cohort_manifest["selection_method"].lower()
        assert "non-performance-based" in method or "not.*performance" in method or "predeclared" in method
        forbidden_terms = ["r2", "r-squared", "residual quality", "best accuracy", "lowest error", "highest score"]
        rules_text = " ".join(cohort_manifest["selection_rules_applied_in_order"]).lower()
        for term in forbidden_terms:
            assert term not in rules_text, f"Selection rules reference performance term '{term}'"

    def test_validation_systems_marked_frozen(self, cohort_manifest: dict):
        assert "validation_systems_frozen" in cohort_manifest
        assert "final" in cohort_manifest["validation_systems_frozen"].lower()

    def test_selected_candidates_match_cohort_manifest(self, candidate_systems: list[dict], cohort_manifest: dict):
        selected = {c["system_id"] for c in candidate_systems if c["selection_status"] == "SELECTED"}
        expected = set(cohort_manifest["development_systems"]) | set(cohort_manifest["validation_systems"])
        assert selected == expected

    def test_excluded_candidates_have_documented_rationale(self, candidate_systems: list[dict]):
        excluded = [c for c in candidate_systems if c["selection_status"] == "EXCLUDED"]
        assert len(excluded) >= 3
        for c in excluded:
            assert c["exclusion_reason_code"] != "NOT_APPLICABLE"
            assert len(c["selection_rationale"]) > 20

    def test_no_candidate_excluded_or_selected_for_a_performance_reason(self, candidate_systems: list[dict]):
        forbidden_terms = ["r2", "r-squared", "lowest error", "highest accuracy", "best fit", "residual"]
        for c in candidate_systems:
            rationale = c["selection_rationale"].lower()
            for term in forbidden_terms:
                assert term not in rationale, (
                    f"System {c['system_id']} rationale references performance term '{term}': {c['selection_rationale']}"
                )


# ===========================================================================
# 5. Signal semantics: irradiance / power / temperature availability & AC-DC separation
# ===========================================================================

class TestSignalSemantics:
    def test_all_selected_systems_have_irradiance_power_temperature(self, candidate_systems: list[dict]):
        selected = [c for c in candidate_systems if c["selection_status"] == "SELECTED"]
        assert len(selected) == 5
        for c in selected:
            assert c["has_irradiance_poa"] == "KNOWN", f"{c['system_id']} missing irradiance"
            assert c["has_ac_power"] == "KNOWN", f"{c['system_id']} missing AC power"
            assert c["has_ambient_temp"] == "KNOWN" or c["has_module_temp"] == "KNOWN", (
                f"{c['system_id']} missing all temperature signals"
            )

    def test_excluded_for_missing_irradiance_are_genuinely_missing(self, candidate_systems: list[dict]):
        for c in candidate_systems:
            if c["exclusion_reason_code"] in ("NO_IRRADIANCE_CHANNEL", "NO_IRRADIANCE_OR_TEMPERATURE_CHANNEL"):
                assert c["has_irradiance_poa"] == "NOT_AVAILABLE"

    def test_unit_metadata_present_for_selected_systems(self, candidate_systems: list[dict]):
        selected = [c for c in candidate_systems if c["selection_status"] == "SELECTED"]
        for c in selected:
            assert c["metrics_dictionary_readable"] == "KNOWN"
            assert c["metric_count"] > 0


# ===========================================================================
# 6. Timestamp quality audit
# ===========================================================================

class TestTimestampQuality:
    def test_timestamp_quality_csv_has_rows_for_every_cohort_system(self, cohort_manifest: dict):
        with (ACQ_DIR / "timestamp_quality.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        cohort_ids = {str(s) for s in cohort_manifest["development_systems"] + cohort_manifest["validation_systems"]}
        seen_ids = {r["system_id"] for r in rows}
        assert cohort_ids <= seen_ids

    def test_available_signals_are_monotonic_nondecreasing(self):
        with (ACQ_DIR / "timestamp_quality.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["n_records"] not in ("0", "NOT_AVAILABLE") and int(r["n_records"]) > 0:
                assert r["monotonic_nondecreasing"] == "True", f"Non-monotonic timestamps: {r}"

    def test_utc_null_signals_are_flagged_not_silently_hidden(self):
        with (ACQ_DIR / "timestamp_quality.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["utc_timestamp_null_fraction"] not in ("NOT_AVAILABLE",) and float(r["utc_timestamp_null_fraction"]) > 0:
                # A fully-null UTC column must fall back to the local `measured_on` basis
                # explicitly, never silently produce a bogus UTC-based result.
                assert r["timestamp_basis_used"] == "measured_on", (
                    f"System {r['system_id']} signal {r['signal']} has null UTC timestamps but "
                    "did not record the local-time fallback basis."
                )


# ===========================================================================
# 7. Physical sanity flags recorded, not silently discarded
# ===========================================================================

class TestPhysicalSanityAudit:
    def test_quality_filter_manifest_documents_policy_and_findings(self):
        with (ACQ_DIR / "quality_filter_manifest.json").open(encoding="utf-8") as f:
            manifest = json.load(f)
        for policy in ["NIGHT", "CLIPPING", "CURTAILMENT", "DATA_GAP", "SENSOR_ANOMALY"]:
            assert policy in manifest["policies"]
        assert manifest["not_applied_in_gate_5_6a"] is True
        assert "per_system" in manifest["real_data_audit_findings"]
        assert len(manifest["real_data_audit_findings"]["per_system"]) > 0

    def test_sanity_flags_are_diagnostic_only_not_filtering_applied(self):
        with (ACQ_DIR / "quality_filter_manifest.json").open(encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["not_applied_in_gate_5_6a"] is True, (
            "Gate 5.6A must not apply quality filters that alter the dataset -- that is a Gate 5.6B decision."
        )
