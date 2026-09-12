"""Smoke test suite to verify foundation imports, contracts, and configurations."""

import importlib

import pytest

from rai.config import FLEET, FLEET_BY_ID, SITES, get_asset, peers_of, settings
from rai.schemas import (
    AnomalyEvidence,
    AssetType,
    DetectorScore,
    ResidualSignal,
)


def test_settings_loaded():
    assert settings.sim_seed == 20260912
    assert settings.tariff_wind_inr_per_kwh > 0
    assert settings.tariff_solar_inr_per_kwh > 0
    assert len(SITES) == 2
    assert "kutch-wind" in SITES
    assert "charanka-solar" in SITES

def test_fleet_registry():
    assert len(FLEET) == 42
    assert len(FLEET_BY_ID) == 42
    wt_assets = [a for a in FLEET if a.asset_type == AssetType.WIND_TURBINE]
    solar_assets = [a for a in FLEET if a.asset_type == AssetType.SOLAR_INVERTER]
    assert len(wt_assets) == 18
    assert len(solar_assets) == 24
    assert "WT-017" in FLEET_BY_ID
    assert "INV-023" in FLEET_BY_ID
    assert get_asset("WT-017").name == "Turbine 17"
    assert len(peers_of("WT-017")) > 0

def test_evidence_schemas():
    sig = ResidualSignal(
        name="active_power",
        unit="kW",
        actual=1850.0,
        expected=2000.0,
        residual=-150.0,
        residual_pct=-7.5,
        z_score=-3.2,
    )
    assert sig.residual == -150.0

    score = DetectorScore(
        detector="residual_z",
        score=0.85,
        threshold=0.60,
        fired=True,
    )
    assert score.fired is True

    anomaly = AnomalyEvidence(
        anomaly_score=0.82,
        detectors=[score],
        signals=[sig],
    )
    assert anomaly.anomaly_score == 0.82
    assert len(anomaly.detectors) == 1

@pytest.mark.parametrize(
    "module_name",
    [
        "rai.config",
        "rai.schemas",
        "rai.sim",
        "rai.ingest",
        "rai.features",
        "rai.models",
        "rai.memory",
        "rai.economics",
        "rai.rag",
        "rai.agent",
        "rai.eval",
        "rai.store",
        "services.api",
        "services.api.routers",
    ],
)
def test_module_imports(module_name):
    mod = importlib.import_module(module_name)
    assert mod is not None
