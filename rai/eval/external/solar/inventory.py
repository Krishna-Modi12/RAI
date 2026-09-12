"""Public Solar Dataset & Tool Inventory for Renewable Asset Intelligence (RAI).

Audits candidate public solar data sources across NREL, Sandia PVPMC, EDP Open Data,
DKASC, and community benchmark datasets, assigning strict Evidence Tiers and
provenance records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class EvidenceTier(str, Enum):
    """Data evidence tiers as defined by the RAI evidence architecture."""

    TIER_1 = "Tier 1 — Real operational PV telemetry + verified failure/degradation evidence"
    TIER_2 = "Tier 2 — Real operational PV telemetry without verified failure labels"
    TIER_3 = "Tier 3 — Real environmental/resource/weather data"
    TIER_4 = "Tier 4 — Physics/reference/modeling tools"
    TIER_5 = "Tier 5 — Synthetic or simulated operational/failure data"


class EvidenceCategory(str, Enum):
    """Repository-wide evidence taxonomy category."""

    EXTERNAL_REAL = "EXTERNAL_REAL"
    REAL_ENVIRONMENT = "REAL_ENVIRONMENT"
    PHYSICS_REFERENCE = "PHYSICS_REFERENCE"
    INTERNAL_SYNTHETIC = "INTERNAL_SYNTHETIC"
    SIMULATED_OUTCOME = "SIMULATED_OUTCOME"
    MODEL_COMPARISON = "MODEL_COMPARISON"


class FailureGroundTruthType(str, Enum):
    """Classification of failure / degradation ground truth available in source."""

    NO_FAILURE_LABELS = "NO_FAILURE_LABELS"
    DEGRADATION_ONLY = "DEGRADATION_ONLY"
    COMPONENT_FAILURE = "COMPONENT_FAILURE"
    MAINTENANCE_LOGS = "MAINTENANCE_LOGS"
    VERIFIED_FAILURE_TIMELINES = "VERIFIED_FAILURE_TIMELINES"
    UNKNOWN = "UNKNOWN"


class ExpectedPerformanceReadiness(str, Enum):
    """Readiness to support expected-power modeling P_expected = f(environment, system)."""

    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class SolarSourceRecord:
    """Comprehensive specification of a candidate public solar data source."""

    source_id: str
    source_name: str
    provider: str
    url: str
    access_method: str
    license: str
    redistribution_permitted: bool
    commercial_use_permitted: bool
    citation_requirement: str
    technology: str
    operational_data: bool
    environmental_data: bool
    weather_data: bool
    irradiance_data: bool
    power_data: bool
    voltage_data: bool
    current_data: bool
    temperature_data: bool
    inverter_data: bool
    string_data: bool
    tracker_data: bool
    maintenance_logs: bool
    failure_labels: bool
    degradation_labels: bool
    timestamps: str
    sampling_resolution: str
    geographic_scope: str
    duration: str
    number_of_sites: str
    number_of_assets: str
    known_data_quality_issues: list[str]
    ground_truth_type: FailureGroundTruthType
    expected_performance_readiness: ExpectedPerformanceReadiness
    readiness_rationale: str
    recommended_RAI_use: str
    evidence_tier: EvidenceTier
    evidence_category: EvidenceCategory

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ground_truth_type"] = self.ground_truth_type.value
        d["expected_performance_readiness"] = self.expected_performance_readiness.value
        d["evidence_tier"] = self.evidence_tier.value
        d["evidence_category"] = self.evidence_category.value
        return d


# Authoritative inventory of evaluated solar datasets and tools
SOLAR_SOURCE_INVENTORY: list[SolarSourceRecord] = [
    SolarSourceRecord(
        source_id="nrel_pvdaq",
        source_name="NREL PVDAQ (PV Data Acquisition)",
        provider="National Renewable Energy Laboratory (NREL)",
        url="https://data.openei.org/submissions/4568",
        access_method="AWS S3 bucket (s3://oedi-data-lake/pvdaq/) and OpenEI REST API",
        license="CC-BY-4.0",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Deline, Perry, Deceglie, Muller, Sekulic, Jordan; NREL 2021, DOI: 10.25984/1846021",
        technology="Distributed commercial, rooftop, and experimental PV arrays (c-Si, CdTe, CIGS)",
        operational_data=True,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=True,
        current_data=True,
        temperature_data=True,
        inverter_data=True,
        string_data=False,
        tracker_data=True,
        maintenance_logs=False,
        failure_labels=False,
        degradation_labels=True,  # Used by NREL PV Fleet Performance Data Initiative
        timestamps="UTC ISO 8601",
        sampling_resolution="1-min to 15-min interval SCADA",
        geographic_scope="Continental United States (diverse climate zones: arid, humid, sub-arctic)",
        duration="Multi-year longitudinal operational records (2010 to 2024)",
        number_of_sites="40+ public systems",
        number_of_assets="65+ monitored inverters and arrays",
        known_data_quality_issues=[
            "Variable instrumentation across sites (some sites lack plane-of-array pyranometers)",
            "Intermittent sensor dropout and unflagged pyranometer drift",
            "Inverter clipping during peak solar noon not explicitly flagged in raw telemetry",
            "Zero operational fault logs or equipment failure timestamps provided",
        ],
        ground_truth_type=FailureGroundTruthType.DEGRADATION_ONLY,
        expected_performance_readiness=ExpectedPerformanceReadiness.READY,
        readiness_rationale="Provides synchronized POA/GHI irradiance, module/ambient temperature, and AC/DC power to fit P_expected = f(G, T).",
        recommended_RAI_use="Primary real operational PV performance baseline and degradation calibration across diverse climates.",
        evidence_tier=EvidenceTier.TIER_2,
        evidence_category=EvidenceCategory.EXTERNAL_REAL,
    ),
    SolarSourceRecord(
        source_id="nrel_nsrdb",
        source_name="NREL NSRDB (National Solar Radiation Database)",
        provider="National Renewable Energy Laboratory (NREL)",
        url="https://nsrdb.nrel.gov",
        access_method="NREL Developer REST API and AWS Public Data (s3://nrel-pds-nsrdb)",
        license="CC-BY-4.0",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Sengupta et al. (2018), Solar Energy, DOI: 10.1016/j.solener.2018.06.039",
        technology="Physical Solar Model (PSM v3 / GOES satellite retrievals)",
        operational_data=False,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=False,
        voltage_data=False,
        current_data=False,
        temperature_data=True,
        inverter_data=False,
        string_data=False,
        tracker_data=False,
        maintenance_logs=False,
        failure_labels=False,
        degradation_labels=False,
        timestamps="UTC ISO 8601",
        sampling_resolution="30-min and 60-min gridded time series",
        geographic_scope="Americas (US, Canada, Latin America, parts of Asia)",
        duration="1998 to present (continuous satellite reanalysis)",
        number_of_sites="Contiguous 4km gridded mesh",
        number_of_assets="NOT_APPLICABLE",
        known_data_quality_issues=[
            "Satellite resolution cannot capture local cloud transients or sub-hourly shading",
            "Not an equipment maintenance or fault dataset; contains zero equipment SCADA",
            "Satellite-to-ground pyranometer bias under high aerosol/haze conditions",
        ],
        ground_truth_type=FailureGroundTruthType.NO_FAILURE_LABELS,
        expected_performance_readiness=ExpectedPerformanceReadiness.PARTIALLY_READY,
        readiness_rationale="Provides complete environmental context (GHI, DNI, DHI, ambient temp, wind), but lacks asset operational telemetry.",
        recommended_RAI_use="Primary environmental resource ground truth for environmental normalization and pyranometer QC cross-checking.",
        evidence_tier=EvidenceTier.TIER_3,
        evidence_category=EvidenceCategory.REAL_ENVIRONMENT,
    ),
    SolarSourceRecord(
        source_id="sandia_pvpmc_pvlib",
        source_name="PVPMC & pvlib Ecosystem (Sandia / PVLIB)",
        provider="Sandia National Laboratories & PVLIB Open Source Community",
        url="https://pvpmc.sandia.gov / https://github.com/pvlib/pvlib-python",
        access_method="Python open-source library (pip/conda) and Sandia web portal",
        license="BSD-3-Clause",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Holmgren et al. (2018), JOSS, DOI: 10.21105/joss.00884; Sandia PVPMC Modeling Guides",
        technology="Empirical and physical photovoltaic simulation models (De Soto, CEC, SAPM, Perez POA)",
        operational_data=False,
        environmental_data=False,
        weather_data=False,
        irradiance_data=False,
        power_data=False,
        voltage_data=False,
        current_data=False,
        temperature_data=False,
        inverter_data=False,
        string_data=False,
        tracker_data=False,
        maintenance_logs=False,
        failure_labels=False,
        degradation_labels=False,
        timestamps="NOT_APPLICABLE",
        sampling_resolution="Arbitrary continuous simulation",
        geographic_scope="Global (ephemeris and physical equations)",
        duration="NOT_APPLICABLE",
        number_of_sites="NOT_APPLICABLE",
        number_of_assets="NOT_APPLICABLE",
        known_data_quality_issues=[
            "Model parameters depend on accurate OEM datasheet coefficients (CEC / Sandia module libraries)",
            "Physics modeling library, not an empirical operational dataset",
        ],
        ground_truth_type=FailureGroundTruthType.NO_FAILURE_LABELS,
        expected_performance_readiness=ExpectedPerformanceReadiness.READY,
        readiness_rationale="Implements deterministic clear-sky, POA decomposition, thermal cell temperature, and inverter efficiency functions.",
        recommended_RAI_use="Core physics and reference modeling engine to compute P_expected(G, T, theta) for residual computation.",
        evidence_tier=EvidenceTier.TIER_4,
        evidence_category=EvidenceCategory.PHYSICS_REFERENCE,
    ),
    SolarSourceRecord(
        source_id="dkasc_alice_springs",
        source_name="DKASC Alice Springs (Desert Knowledge Australia)",
        provider="Desert Knowledge Australia Solar Centre",
        url="https://dkasolarcentre.com.au/download?location=alice-springs",
        access_method="Public web portal CSV download",
        license="Open Access with Attribution",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Desert Knowledge Australia Solar Centre, Alice Springs, Northern Territory",
        technology="40+ side-by-side technologies (Mono-Si, Poly-Si, Thin-Film, CPV, 1-axis/2-axis tracker, fixed tilt)",
        operational_data=True,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=True,
        current_data=True,
        temperature_data=True,
        inverter_data=True,
        string_data=False,
        tracker_data=True,
        maintenance_logs=True,
        failure_labels=False,
        degradation_labels=True,
        timestamps="Local Time (ACST) / UTC convertible",
        sampling_resolution="5-min continuous time series",
        geographic_scope="Alice Springs, Arid Central Australia",
        duration="2008 to present (>16 years continuous operation)",
        number_of_sites="1 centralized research facility",
        number_of_assets="40+ distinct technology array installations",
        known_data_quality_issues=[
            "Timezone requires conversion from Australian Central Standard Time (UTC+9:30)",
            "Occasional station maintenance gaps and sensor calibration intervals",
            "Inverter failures appear in telemetry but are documented in qualitative site logs rather than binary time tags",
        ],
        ground_truth_type=FailureGroundTruthType.MAINTENANCE_LOGS,
        expected_performance_readiness=ExpectedPerformanceReadiness.READY,
        readiness_rationale="Co-located high-accuracy pyranometers, module temperatures, and electrical outputs in an identical micro-climate.",
        recommended_RAI_use="Technology peer-comparison, arid soiling accumulation/rain-cleaning validation, and multi-year degradation benchmarking.",
        evidence_tier=EvidenceTier.TIER_1,
        evidence_category=EvidenceCategory.EXTERNAL_REAL,
    ),
    SolarSourceRecord(
        source_id="edp_open_data_pv",
        source_name="EDP Open Data Solar PV Fleet",
        provider="EDP Renováveis (EDP Open Data)",
        url="https://opendata.edp.com",
        access_method="EDP Open Data Portal download (CSV/API)",
        license="Open Data License (EDP Open Data)",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="EDP Open Data, EDP Renováveis Platform",
        technology="Utility-scale central inverter PV plants with single-axis tracking and fixed tilt",
        operational_data=True,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=True,
        current_data=True,
        temperature_data=True,
        inverter_data=True,
        string_data=False,
        tracker_data=True,
        maintenance_logs=True,
        failure_labels=False,
        degradation_labels=False,
        timestamps="UTC ISO 8601",
        sampling_resolution="10-min and 15-min operational SCADA",
        geographic_scope="Iberian Peninsula & Latin America (Portugal, Spain, Brazil)",
        duration="Multi-year operational seasons (2019 to 2023)",
        number_of_sites="3 commercial utility-scale solar parks",
        number_of_assets="48 central inverters",
        known_data_quality_issues=[
            "Occasional communication dropout between inverters and central plant SCADA",
            "Partial inverter derating during summer grid curtailment commands",
            "Work orders are logged in unstructured textual maintenance summaries",
        ],
        ground_truth_type=FailureGroundTruthType.MAINTENANCE_LOGS,
        expected_performance_readiness=ExpectedPerformanceReadiness.READY,
        readiness_rationale="Utility-scale commercial telemetry matching modern commercial SCADA architectures.",
        recommended_RAI_use="Real-world utility-scale operational validation for inverter underperformance and tracker tracking errors.",
        evidence_tier=EvidenceTier.TIER_2,
        evidence_category=EvidenceCategory.EXTERNAL_REAL,
    ),
    SolarSourceRecord(
        source_id="kaggle_two_plant_india",
        source_name="Solar Power Generation Dataset (Two Indian Plants)",
        provider="Anik Annal / Kaggle & IEEE DataPort",
        url="https://www.kaggle.com/datasets/anikannal/solar-power-generation-data",
        access_method="Kaggle API & direct CSV download",
        license="CC-BY-SA-4.0",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Annal, A. (2020), Solar Power Generation Data, Kaggle Dataset",
        technology="Utility-scale PV plants in India (Plant 1: 22 inverters; Plant 2: 22 inverters)",
        operational_data=True,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=False,
        current_data=False,
        temperature_data=True,
        inverter_data=True,
        string_data=False,
        tracker_data=False,
        maintenance_logs=False,
        failure_labels=False,
        degradation_labels=False,
        timestamps="Local format 'YYYY-MM-DD HH:MM:SS'",
        sampling_resolution="15-min synchronized intervals",
        geographic_scope="India (monsoon and pre-monsoon dry season)",
        duration="34 consecutive days (May 15 to June 17, 2020)",
        number_of_sites="2 commercial solar plants",
        number_of_assets="44 string/central inverters",
        known_data_quality_issues=[
            "Plant 1 irradiance sensor suffers pronounced measurement drift and unphysical scaling",
            "Short duration (34 days) cannot support long-term degradation or seasonal analysis",
            "Lacks string-level electrical monitoring (inverter level only)",
            "Contains zero failure logs or verified fault tags",
        ],
        ground_truth_type=FailureGroundTruthType.NO_FAILURE_LABELS,
        expected_performance_readiness=ExpectedPerformanceReadiness.PARTIALLY_READY,
        readiness_rationale="Contains 15-min DC/AC power and weather, but suffers sensor calibration drift at Plant 1 and lacks string channels.",
        recommended_RAI_use="Rapid multi-inverter peer comparison prototyping and sensor-drift QC challenge.",
        evidence_tier=EvidenceTier.TIER_2,
        evidence_category=EvidenceCategory.EXTERNAL_REAL,
    ),
    SolarSourceRecord(
        source_id="nrel_synthetic_outage_muller2023",
        source_name="NREL Synthetic PV Time-Series with Injected Outages",
        provider="National Renewable Energy Laboratory (NREL)",
        url="https://data.openei.org / Muller et al. 2023",
        access_method="OpenEI download / NREL publication data repository",
        license="US Government Public Domain / CC0",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Muller et al. (2023), NREL Technical Report, Synthetic PV Fault Injections",
        technology="Physics-simulated commercial PV arrays with scripted partial string and inverter outages",
        operational_data=False,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=True,
        current_data=True,
        temperature_data=True,
        inverter_data=True,
        string_data=True,
        tracker_data=False,
        maintenance_logs=False,
        failure_labels=True,
        degradation_labels=False,
        timestamps="UTC ISO 8601",
        sampling_resolution="15-min synthetic intervals",
        geographic_scope="Simulated US meteorological profiles",
        duration="1 full synthetic meteorological year",
        number_of_sites="1 simulated commercial plant",
        number_of_assets="12 simulated string inverters",
        known_data_quality_issues=[
            "Simulated data generated by PVWatts/SAM rather than physical field transducers",
            "Noise profiles are synthetic Gaussian rather than true field transducer noise",
        ],
        ground_truth_type=FailureGroundTruthType.VERIFIED_FAILURE_TIMELINES,
        expected_performance_readiness=ExpectedPerformanceReadiness.READY,
        readiness_rationale="Exact verified failure onset, duration, and magnitude ground truth for algorithm recall benchmarking.",
        recommended_RAI_use="Controlled benchmark evaluation of detector lead time and recall under known outage percentages.",
        evidence_tier=EvidenceTier.TIER_5,
        evidence_category=EvidenceCategory.SIMULATED_OUTCOME,
    ),
    SolarSourceRecord(
        source_id="duramat_pv_degradation",
        source_name="DuraMAT / NREL PV Fleet Performance Data Initiative",
        provider="DuraMAT Consortium & NREL",
        url="https://www.duramat.org",
        access_method="DuraMAT Data Hub access / curated research reports",
        license="Open Access / Public Domain",
        redistribution_permitted=True,
        commercial_use_permitted=True,
        citation_requirement="Jordan et al. (2020), Photovoltaic Fleet Performance Initiative, Progress in Photovoltaics",
        technology="Fleet-scale PV module field degradation metrics across hundreds of commercial sites",
        operational_data=True,
        environmental_data=True,
        weather_data=True,
        irradiance_data=True,
        power_data=True,
        voltage_data=False,
        current_data=False,
        temperature_data=True,
        inverter_data=True,
        string_data=False,
        tracker_data=False,
        maintenance_logs=False,
        failure_labels=False,
        degradation_labels=True,
        timestamps="Daily / Monthly aggregated time series",
        sampling_resolution="Aggregated performance indices (Performance Ratio, degradation slope)",
        geographic_scope="Global / North America",
        duration="10+ years multi-site degradation monitoring",
        number_of_sites="300+ commercial and utility sites",
        number_of_assets=">1,000 systems",
        known_data_quality_issues=[
            "Data primarily released as aggregated performance metrics and degradation distributions rather than high-frequency SCADA",
            "Site names anonymized to protect asset owner confidentiality",
        ],
        ground_truth_type=FailureGroundTruthType.DEGRADATION_ONLY,
        expected_performance_readiness=ExpectedPerformanceReadiness.PARTIALLY_READY,
        readiness_rationale="Provides gold-standard empirical degradation priors, but high-frequency SCADA requires extraction.",
        recommended_RAI_use="Grounding empirical priors on annual degradation rates (-0.5% to -1.0%/yr) in the economic decision engine.",
        evidence_tier=EvidenceTier.TIER_1,
        evidence_category=EvidenceCategory.EXTERNAL_REAL,
    ),
]


def get_source_by_id(source_id: str) -> SolarSourceRecord:
    """Retrieve a solar source record by its unique identifier."""
    for s in SOLAR_SOURCE_INVENTORY:
        if s.source_id == source_id:
            return s
    raise KeyError(f"Solar source '{source_id}' not found in inventory.")
