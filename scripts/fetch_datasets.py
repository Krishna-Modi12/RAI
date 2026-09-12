"""CLI utility to inspect, discover, and fetch external renewable benchmarks and context.

Checks status according to rai.ingest.registry and can generate lightweight validation
fixtures for offline testing.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from rai.config import RAW
from rai.ingest.care import discover
from rai.ingest.registry import DATASETS, availability

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(asctime)s] %(message)s")
log = logging.getLogger("fetch_datasets")


def print_status():
    """Print the availability and disk status of all registered external datasets."""
    print("\n" + "=" * 80)
    print("RENEWABLE ASSET INTELLIGENCE — EXTERNAL DATASET REGISTRY STATUS")
    print("=" * 80)

    for ds in DATASETS.values():
        avail = availability(ds)
        print(f"\n[Dataset] {avail.name} ({ds.dataset_id})")
        print(f"  Role:        {ds.role.value}")
        print(f"  Status:      {avail.status.value}")
        print(f"  Local dir:   {avail.local_dir}")
        print(f"  Files found: {avail.n_files} ({avail.bytes_on_disk / (1024 * 1024):.2f} MB on disk)")
        if avail.found_files:
            print(f"  Sample:      {', '.join(avail.found_files[:3])}")
        if avail.status.value != "present" and ds.instructions:
            print("  Acquisition instructions:")
            for line in ds.instructions.strip().splitlines()[:3]:
                print(f"    {line}")

    # Inspect CARE specific discovery
    care_inv = discover()
    print("\n" + "-" * 80)
    print("CARE SCADA Ingestion Discovery:")
    print(care_inv.explain())
    print("=" * 80 + "\n")


def generate_external_fixture():
    """Create a lightweight external SCADA validation fixture to test zero-shot transfer."""
    fixture_dir = RAW / "care" / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    out_file = fixture_dir / "external_turbine_sample.csv"

    if out_file.exists():
        log.info("External turbine fixture already exists at %s", out_file)
        return out_file

    log.info("Generating external turbine fixture representing Senvion MM92 (2050 kW)...")
    import numpy as np

    n_samples = 1440  # 10 days of 10-minute SCADA
    t0 = pd.Timestamp("2024-01-01T00:00:00Z")
    timestamps = pd.date_range(t0, periods=n_samples, freq="10min")

    rng = np.random.default_rng(20260912)
    wind_speed = np.clip(rng.weibull(2.1, n_samples) * 8.5, 0.5, 24.0)

    # Power curve for 2050 kW turbine (cut-in 3.0 m/s, rated 12.0 m/s)
    cp = 0.44
    air_density = 1.225
    rotor_area = np.pi * (46.0**2)
    theoretical_power = 0.5 * air_density * rotor_area * (wind_speed**3) / 1000.0
    power_kw = np.where(
        wind_speed < 3.0,
        0.0,
        np.where(
            wind_speed >= 12.0,
            2050.0 + rng.normal(0, 15.0, n_samples),
            np.clip(theoretical_power * cp + rng.normal(0, 20.0, n_samples), 0.0, 2050.0),
        ),
    )

    ambient_temp = 12.0 + 6.0 * np.sin(np.linspace(0, 20 * np.pi, n_samples)) + rng.normal(0, 1.0, n_samples)
    gearbox_temp = 45.0 + 0.015 * power_kw + 0.5 * ambient_temp + rng.normal(0, 1.5, n_samples)
    rotor_rpm = np.where(wind_speed < 3.0, 0.0, np.clip(wind_speed * 1.3 + rng.normal(0, 0.2, n_samples), 0.0, 16.0))

    # Inject progressive bearing degradation in final 3 days (last 432 samples)
    degradation_onset = n_samples - 432
    wear = np.linspace(0, 25.0, 432)
    gearbox_temp[degradation_onset:] += wear

    df = pd.DataFrame({
        "time_stamp": timestamps.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "turbine_id": "EXT-SENVION-01",
        "wind_speed_avg": np.round(wind_speed, 2),
        "power_avg": np.round(power_kw, 1),
        "rotor_speed_avg": np.round(rotor_rpm, 2),
        "gearbox_bearing_temperature_avg": np.round(gearbox_temp, 2),
        "ambient_temperature_avg": np.round(ambient_temp, 2),
        "status_code": [0] * n_samples,
    })

    df.to_csv(out_file, index=False)
    log.info("Wrote external SCADA fixture with %d intervals to %s", len(df), out_file)
    return out_file


def main():
    parser = argparse.ArgumentParser(description="External dataset status and fetching utility.")
    parser.add_argument("--status", action="store_true", default=True, help="Print dataset availability status")
    parser.add_argument("--fixture", action="store_true", help="Generate lightweight external validation fixture")
    args = parser.parse_args()

    if args.fixture:
        generate_external_fixture()
    print_status()


if __name__ == "__main__":
    main()
