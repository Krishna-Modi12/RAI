"""Typed registry of every external dataset this project references.

Two things this module guarantees:

1. Nothing here is a remembered statistic. Every row/byte count reported for a dataset
   comes from reading the filesystem at call time. A dataset that is not on disk reports
   ``absent, instructions provided`` and carries the exact acquisition steps.
2. Licence and attribution text travels with the dataset spec, so any component that
   cites a dataset can cite it correctly without hard-coding a licence string.

The registry is deliberately wider than what the build uses: datasets marked
``research_only`` are named so a reviewer can see what was considered and why it was not
used, rather than us silently implying our synthetic fleet is the only option.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rai.config import RAW


class DatasetRole(str, Enum):
    """What a dataset is for in *this* project."""

    TRAIN = "train"
    VALIDATE = "validate"
    CONTEXT = "context"
    RESEARCH_ONLY = "research_only"


class DatasetStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent, instructions provided"
    FETCHED = "fetched"


class AcquisitionMode(str, Enum):
    """How the bytes can be obtained from this sandbox."""

    AUTO_HTTP = "auto_http"  # fetchable here, no credentials
    MANUAL_DOWNLOAD = "manual_download"  # user must download and drop in place
    CREDENTIALED = "credentialed"  # needs an account / API token


class DatasetSpec(BaseModel):
    """Immutable description of one external dataset."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    name: str
    url: str
    licence: str
    attribution: str
    cadence: str
    role: DatasetRole
    purpose: str
    acquisition: AcquisitionMode
    local_dir: Path
    expected_files: tuple[str, ...] = ()
    approx_size: str = "unknown"
    instructions: str = ""
    caveats: str = ""


class DatasetAvailability(BaseModel):
    """Result of looking at the filesystem right now."""

    dataset_id: str
    name: str
    status: DatasetStatus
    local_dir: Path
    n_files: int = 0
    bytes_on_disk: int = 0
    found_files: tuple[str, ...] = ()
    missing_files: tuple[str, ...] = ()
    detail: str = ""


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

_CARE = DatasetSpec(
    dataset_id="care",
    name="CARE to Compare (Zenodo 10958775)",
    url="https://zenodo.org/records/10958775",
    licence="CC-BY-SA-4.0",
    attribution=(
        "Gück, C., Roelofs, C. M. A., & Faulstich, S. (2024). CARE to Compare: A real-world "
        "benchmark dataset for early fault detection in wind turbine data. Zenodo. "
        "https://doi.org/10.5281/zenodo.10958775. Licensed CC-BY-SA-4.0."
    ),
    cadence="10 min",
    role=DatasetRole.VALIDATE,
    purpose=(
        "Real wind-turbine SCADA with labelled anomaly windows and normal-behaviour "
        "training periods. Used to validate that the expected-behaviour + residual "
        "pipeline transfers off the simulator."
    ),
    acquisition=AcquisitionMode.MANUAL_DOWNLOAD,
    local_dir=RAW / "care",
    expected_files=("datasets.csv", "event_info.csv"),
    approx_size="~5.5 GB zipped",
    instructions=(
        "1. Open https://zenodo.org/records/10958775 and download the archive "
        "(CC-BY-SA-4.0, no account needed).\n"
        "2. Extract it, then copy the per-farm folders (Wind Farm A/B/C) into "
        "data/raw/care/ so you end up with e.g. "
        "data/raw/care/Wind Farm A/datasets/<id>.csv and "
        "data/raw/care/Wind Farm A/event_info.csv.\n"
        "3. Re-run scripts/fetch_datasets.py; the loader auto-discovers whatever is there.\n"
        "Nothing is downloaded automatically: the archive is far larger than this "
        "environment should pull, and its share-alike licence deserves a deliberate "
        "human decision."
    ),
    caveats=(
        "Up to ~957 columns per farm with avg/min/max/std variants; sensor names are "
        "anonymised per farm; the authors document sensor drop-outs and mislabelled "
        "status periods. rai.ingest.care applies an explicit mapping table plus a "
        "quality filter rather than trusting column order."
    ),
)

_KAGGLE_SOLAR = DatasetSpec(
    dataset_id="kaggle_solar_two_plant",
    name="Solar Power Generation Data (two Indian plants)",
    url="https://www.kaggle.com/datasets/anikannal/solar-power-generation-data",
    licence="CC0-1.0 (public domain dedication, per the Kaggle dataset page)",
    attribution=(
        "Ani Kannal, 'Solar Power Generation Data', Kaggle. "
        "https://www.kaggle.com/datasets/anikannal/solar-power-generation-data"
    ),
    cadence="15 min",
    role=DatasetRole.VALIDATE,
    purpose=(
        "34 days of inverter-level generation plus plant-level irradiance and module "
        "temperature from two utility-scale Indian PV plants. Real Indian-climate "
        "counterpart to the Charanka synthetic fleet; used to sanity-check the solar "
        "expected-power model and inverter peer comparison."
    ),
    acquisition=AcquisitionMode.CREDENTIALED,
    local_dir=RAW / "kaggle_solar",
    expected_files=(
        "Plant_1_Generation_Data.csv",
        "Plant_1_Weather_Sensor_Data.csv",
        "Plant_2_Generation_Data.csv",
        "Plant_2_Weather_Sensor_Data.csv",
    ),
    approx_size="~12 MB",
    instructions=(
        "Kaggle requires an authenticated session, so this is a manual step:\n"
        "1. Put a Kaggle API token at ~/.kaggle/kaggle.json, then run\n"
        "   kaggle datasets download -d anikannal/solar-power-generation-data "
        "-p data/raw/kaggle_solar --unzip\n"
        "   (or download the zip from the dataset page in a browser and extract it there).\n"
        "2. The four CSVs must sit directly in data/raw/kaggle_solar/."
    ),
    caveats=(
        "Known quirks handled by the loader: Plant_1 generation timestamps are "
        "DD-MM-YYYY while the weather files are ISO; DC_POWER in Plant_1 is roughly 10x "
        "AC_POWER (string-sum scaling) and is NOT silently rescaled; IRRADIATION has no "
        "documented unit and is treated as kW/m2 behind an explicit flag."
    ),
)

_NASA_POWER = DatasetSpec(
    dataset_id="nasa_power",
    name="NASA POWER hourly point data (MERRA-2 / SYN1deg reanalysis)",
    url="https://power.larc.nasa.gov/docs/services/api/temporal/hourly/",
    licence="Public domain / freely available (NASA POWER data policy, no key required)",
    attribution=(
        "These data were obtained from the NASA Langley Research Center POWER Project "
        "funded through the NASA Earth Science Directorate Applied Science Program."
    ),
    cadence="1 h",
    role=DatasetRole.CONTEXT,
    purpose=(
        "Independent weather context for the Gujarat sites: irradiance, temperature, "
        "wind, humidity, pressure and precipitation at the real Kutch and Charanka "
        "coordinates. Lets the environment-attribution layer cite a third-party source "
        "instead of the simulator's own met file, and supplies real rain history for "
        "the soiling model."
    ),
    acquisition=AcquisitionMode.AUTO_HTTP,
    local_dir=RAW / "nasa_power",
    approx_size="~0.5 MB per site-year",
    instructions=(
        "Fetched automatically by scripts/fetch_datasets.py (no credentials). Responses "
        "are cached as parquet under data/raw/nasa_power/ keyed by lat/lon/date-range/"
        "parameter set, so repeat calls are fully offline."
    ),
    caveats=(
        "Reanalysis on a ~0.5 deg x 0.625 deg grid, not a met mast: treat it as regional "
        "context, not as a hub-height measurement. Aerosol optical depth is not available "
        "on the hourly endpoint, so site_met.dust_aod is left null rather than guessed."
    ),
)

_KELMARSH = DatasetSpec(
    dataset_id="kelmarsh",
    name="Kelmarsh Wind Farm SCADA (2016-2021)",
    url="https://zenodo.org/records/8252025",
    licence="CC-BY-4.0",
    attribution=(
        "Plumley, C. (2022). Kelmarsh wind farm data. Zenodo. "
        "https://doi.org/10.5281/zenodo.8252025. Licensed CC-BY-4.0."
    ),
    cadence="10 min",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "Six Senvion MM92 turbines with descriptive (non-anonymised) column names and a "
        "separate status/curtailment log. Referenced as the source of truth for how "
        "commercial SCADA names its channels, which is what the CARE mapping table "
        "aliases against. Not loaded in this build."
    ),
    acquisition=AcquisitionMode.MANUAL_DOWNLOAD,
    local_dir=RAW / "kelmarsh",
    approx_size="~1 GB",
    instructions=(
        "Download the per-turbine 10-minute CSVs from the Zenodo record into "
        "data/raw/kelmarsh/. No loader is implemented in this build."
    ),
    caveats="No loader implemented. Listed for provenance of the wind column aliases.",
)

_PENMANSHIEL = DatasetSpec(
    dataset_id="penmanshiel",
    name="Penmanshiel Wind Farm SCADA (2016-2021)",
    url="https://zenodo.org/records/8253010",
    licence="CC-BY-4.0",
    attribution=(
        "Plumley, C. (2022). Penmanshiel wind farm data. Zenodo. "
        "https://doi.org/10.5281/zenodo.8253010. Licensed CC-BY-4.0."
    ),
    cadence="10 min",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "Fourteen Senvion MM82 turbines, same schema family as Kelmarsh. Candidate for "
        "a larger peer-group study after the hackathon. Not loaded in this build."
    ),
    acquisition=AcquisitionMode.MANUAL_DOWNLOAD,
    local_dir=RAW / "penmanshiel",
    approx_size="~2 GB",
    instructions=(
        "Download the per-turbine 10-minute CSVs from the Zenodo record into "
        "data/raw/penmanshiel/. No loader is implemented in this build."
    ),
    caveats="No loader implemented.",
)

_EDP = DatasetSpec(
    dataset_id="edp_open_data",
    name="EDP Open Data wind turbine SCADA + failure logs (2016-2017)",
    url="https://www.edp.com/en/innovation/open-data",
    licence="EDP Open Data terms (attribution, non-commercial research use)",
    attribution="EDP Open Data, Wind Turbine SCADA signals and failure logs, 2016-2017.",
    cadence="10 min",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "Five turbines with component-level failure logs (gearbox, generator, "
        "transformer, hydraulic, bearing). The failure taxonomy informed our fault "
        "scenarios and the component keys in COMPONENT_ECONOMICS. Not loaded in this "
        "build."
    ),
    acquisition=AcquisitionMode.MANUAL_DOWNLOAD,
    local_dir=RAW / "edp",
    approx_size="~50 MB",
    instructions=(
        "Register on the EDP Open Data portal and download the wind-turbine SCADA and "
        "failure-log CSVs into data/raw/edp/. No loader is implemented in this build."
    ),
    caveats="Licence is not a standard CC licence; check terms before redistributing.",
)

_PVDAQ = DatasetSpec(
    dataset_id="nrel_pvdaq",
    name="NREL PVDAQ (PV Data Acquisition)",
    url="https://developer.nrel.gov/docs/solar/pvdaq-v3/",
    licence="Public domain (US Government work), API key required",
    attribution="NREL PVDAQ, National Renewable Energy Laboratory.",
    cadence="1 min - 15 min, system dependent",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "Long-horizon PV system data with inverter-level channels and documented "
        "soiling/degradation studies. The reference for realistic soiling-rate ranges. "
        "Not loaded in this build (needs an api.data.gov key)."
    ),
    acquisition=AcquisitionMode.CREDENTIALED,
    local_dir=RAW / "pvdaq",
    approx_size="varies by system-year",
    instructions=(
        "Request a free api.data.gov key, then pull per-system CSVs into "
        "data/raw/pvdaq/. No loader is implemented in this build."
    ),
    caveats="Requires an API key; not attempted from this sandbox.",
)

_DKASC = DatasetSpec(
    dataset_id="dkasc",
    name="DKA Solar Centre (Desert Knowledge Australia, Alice Springs)",
    url="https://dkasolarcentre.com.au/download",
    licence="CC-BY-4.0 (site download terms)",
    attribution="DKA Solar Centre, Desert Knowledge Australia Solar Centre, Alice Springs.",
    cadence="5 min",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "Desert-climate PV arrays of many module technologies with long records. The "
        "closest public analogue to Charanka's dust regime; referenced for soiling "
        "seasonality. Not loaded in this build."
    ),
    acquisition=AcquisitionMode.MANUAL_DOWNLOAD,
    local_dir=RAW / "dkasc",
    approx_size="~100 MB per system-decade",
    instructions=(
        "Use the site's download form to export per-system CSVs into data/raw/dkasc/. "
        "No loader is implemented in this build."
    ),
    caveats="No loader implemented.",
)

_SDWPF = DatasetSpec(
    dataset_id="sdwpf",
    name="SDWPF - Spatial Dynamic Wind Power Forecasting (KDD Cup 2022)",
    url="https://aistudio.baidu.com/competition/detail/152/0/introduction",
    licence="Competition terms, research use (Baidu / Longyuan Power)",
    attribution=(
        "Zhou, J. et al. (2022). SDWPF: A Dataset for Spatial Dynamic Wind Power "
        "Forecasting over a Large Turbine Array. KDD Cup 2022."
    ),
    cadence="10 min",
    role=DatasetRole.RESEARCH_ONLY,
    purpose=(
        "134 turbines with relative spatial coordinates - the reference for how wake "
        "interaction shows up in a real array, which is what our two-row peer-group "
        "design imitates. Not loaded in this build."
    ),
    acquisition=AcquisitionMode.CREDENTIALED,
    local_dir=RAW / "sdwpf",
    approx_size="~200 MB",
    instructions=(
        "Register for the AI Studio competition to obtain wtbdata_245days.csv and the "
        "turbine location file, and place them in data/raw/sdwpf/. No loader is "
        "implemented in this build."
    ),
    caveats="Competition registration required; not attempted from this sandbox.",
)


DATASETS: dict[str, DatasetSpec] = {
    spec.dataset_id: spec
    for spec in (
        _CARE,
        _KAGGLE_SOLAR,
        _NASA_POWER,
        _KELMARSH,
        _PENMANSHIEL,
        _EDP,
        _PVDAQ,
        _DKASC,
        _SDWPF,
    )
}

# Datasets a loader in rai.ingest can actually read.
IMPLEMENTED_LOADERS: tuple[str, ...] = ("care", "kaggle_solar_two_plant", "nasa_power")

# Extensions that count as dataset payload when measuring a local directory.
_DATA_SUFFIXES = {".csv", ".parquet", ".zip", ".gz", ".json", ".nc", ".xlsx", ".txt"}


def get_dataset(dataset_id: str) -> DatasetSpec:
    if dataset_id not in DATASETS:
        raise KeyError(f"unknown dataset_id {dataset_id!r}")
    return DATASETS[dataset_id]


def _scan_dir(root: Path) -> tuple[list[Path], int]:
    """Return (data files found recursively, total bytes)."""
    if not root.exists():
        return [], 0
    files = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in _DATA_SUFFIXES and not p.name.startswith(".")
    ]
    total = 0
    for p in files:
        try:
            total += p.stat().st_size
        except OSError:  # pragma: no cover - race with a concurrent writer
            continue
    return files, total


def availability(spec: DatasetSpec, *, root: Path | None = None) -> DatasetAvailability:
    """Look at the filesystem and report what is really there.

    `root` overrides the spec's local_dir so tests can point at a tmp_path.
    """
    local_dir = root if root is not None else spec.local_dir
    files, total = _scan_dir(local_dir)
    names = {p.name for p in files}
    missing = tuple(f for f in spec.expected_files if f not in names)

    if not files:
        return DatasetAvailability(
            dataset_id=spec.dataset_id,
            name=spec.name,
            status=DatasetStatus.ABSENT,
            local_dir=local_dir,
            missing_files=tuple(spec.expected_files),
            detail=f"nothing at {local_dir}; see spec.instructions",
        )

    # A dataset we pulled over HTTP ourselves is "fetched"; bytes a human placed
    # there are "present". The distinction matters for provenance claims.
    status = (
        DatasetStatus.FETCHED
        if spec.acquisition is AcquisitionMode.AUTO_HTTP
        else DatasetStatus.PRESENT
    )
    if missing and spec.expected_files:
        detail = (
            f"{len(files)} data file(s) found but {len(missing)} expected name(s) missing: "
            + ", ".join(missing)
        )
    else:
        detail = f"{len(files)} data file(s), {total / 1e6:.2f} MB"

    return DatasetAvailability(
        dataset_id=spec.dataset_id,
        name=spec.name,
        status=status,
        local_dir=local_dir,
        n_files=len(files),
        bytes_on_disk=total,
        found_files=tuple(sorted(names)[:12]),
        missing_files=missing,
        detail=detail,
    )


def registry_status() -> list[DatasetAvailability]:
    """Live availability for every registered dataset, registry order preserved."""
    return [availability(spec) for spec in DATASETS.values()]


def attribution_block(dataset_ids: list[str] | None = None) -> str:
    """Attribution text for the datasets actually used, for docs and UI footers."""
    ids = dataset_ids if dataset_ids is not None else list(IMPLEMENTED_LOADERS)
    return "\n\n".join(f"{get_dataset(d).name}\n  {get_dataset(d).attribution}" for d in ids)
