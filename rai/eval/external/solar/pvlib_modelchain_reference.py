"""Gate 5.6C real pvlib.modelchain.ModelChain physics reference.

This module REPLACES `PVLibPhysicsReference` in `models.py` as the physics-reference
model for Gate 5.6C. `PVLibPhysicsReference` is not used here or by anything built on
top of this module: it is a hand-rolled quadratic-efficiency formula that does not call
`pvlib.modelchain.ModelChain` despite its name, and is confirmed to be the second root
cause of `GATE_5.6_INVALID_SYNTHETIC_RUN` (see
`artifacts/evaluation/gate56_invalid_prior_run/invalidation_manifest.json`, item 2:
circular validation). It remains in `models.py` unmodified as historical/audit record
per the project's evidence-preservation policy; it must not be imported by new code.

`PVLibModelChainReference` instead constructs a real `pvlib.pvsystem.PVSystem` +
`pvlib.modelchain.ModelChain` per development system, using ONLY parameters already
verified as real in `artifacts/evaluation/gate56/cohort_adjudication/pvlib_readiness.csv`
and the real per-system metadata JSON under `scratch_gate56a/system_metadata/`:

- Module and inverter electrical parameters: exact name matches against pvlib's bundled
  CEC module/inverter reference databases (`pvlib.pvsystem.retrieve_sam`), verified in
  Gate 5.6B by cross-validating declared STC wattage x quantity against declared system
  nameplate capacity.
- Tilt / azimuth: real fixed-mount metadata (Mount block, PVDAQ system_metadata JSON).
- Inverter quantity and modules-per-inverter: real values from the PVDAQ `Inverters` /
  `Modules` metadata blocks (e.g. system 1239 declares 2 real inverters and 90 real
  modules total -> 45 modules/inverter, an exact real split, not invented).
- modules_per_string=1 with strings_per_inverter=modules_per_inverter: the real metadata
  does not record the exact series/parallel wiring split (modules_per_string / num_strings
  are blank for all three development systems). This is a disclosed simplification, not an
  invented parameter: pvlib scales module voltage by modules_per_string and current by
  strings_per_inverter, so their product (aggregate DC power at a given operating point)
  is invariant to how a fixed total module count is divided between the two -- only the
  real total module count affects the result.
- Irradiance input: real measured POA (plane-of-array) global irradiance is fed directly
  as `effective_irradiance` via `ModelChain.run_model_from_effective_irradiance`, which
  requires only a single POA channel (unlike `run_model_from_poa`, which requires POA
  decomposed into direct+diffuse components that are not available in this real dataset).
  This means transposition, AOI, and spectral-mismatch corrections are not modeled
  (dc_model AOI/spectral set to "no_loss") -- a disclosed simplification made necessary by
  the real sensor configuration (single broadband POA pyranometer per PVDAQ site), not a
  fabricated correction.
- Temperature model: per-system choice already adjudicated in Gate 5.6B and frozen in
  pvlib_readiness.csv -- `faiman` for system 1239 (its real wind_speed channel is
  degenerate/flatlined; faiman defaults wind_speed=1.0 m/s, a disclosed standard
  assumption) and `sapm` with the pvlib-standard `close_mount_glass_glass` racking preset
  for 1283/34 (real array_type="roof" in both cases; real wind_speed is used for these two
  since their wind channels are NOT degenerate).

Systems 1430 and 1433 are NOT modeled here: Gate 5.6B classified both
`physics_ready=False` (1430: no real tracker-axis geometry available;
1433: no CEC module/inverter match exists) -- per the project's PARAMETERIZATION_INSUFFICIENT
rule, no parameters are invented to force a model for either system.

STATUS: MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED (see
`artifacts/evaluation/gate56/gate56c_decision_gate/decision.md`, Path B). No real
component-failure event labels exist for this cohort; any tracking metric (R2, nRMSE)
computed against this model is an internal self-consistency diagnostic only, never a
validated-accuracy or generalization claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.pvsystem import PVSystem, retrieve_sam
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

# Real per-system configuration. Every field traces to a specific real-data source cited
# in this module's docstring and in pvlib_readiness.csv / the PVDAQ system_metadata JSON.
# PARAMETERIZATION_INSUFFICIENT systems (1430, 1433) are intentionally absent.
REAL_MODELCHAIN_CONFIG: dict[int, dict] = {
    1239: {
        "module_name": "Sharp_ND_224UC1",
        "inverter_name": "Yaskawa_Solectria_Solar__PVI_13_kW_480__480V_",
        "tilt_deg": 10.0,
        "azimuth_deg": 155.0,
        "latitude": 46.6704,
        "longitude": -68.0178,
        "altitude_m": 197.0,
        "inverter_quantity": 2,  # real: Inverters.Inverter 0.quantity
        "modules_per_inverter": 45,  # real: 90 total modules / 2 real inverters
        "temperature_model": "faiman",
        "temperature_model_params": {"u0": 25.0, "u1": 6.84},  # pvlib faiman published defaults
        "wind_speed_available": False,  # Gate 5.6B: real channel degenerate (flatlined)
    },
    1283: {
        "module_name": "SunPower_SPR_315E_WHT_D",
        "inverter_name": "SMA_America__SC250U__480V_",
        "tilt_deg": 10.0,
        "azimuth_deg": 165.0,
        "latitude": 39.7409,
        "longitude": -105.1711,
        "altitude_m": 1800.0,
        "inverter_quantity": 2,  # real: Inverters.Inverter 0.quantity
        "modules_per_inverter": 648,  # real: 1296 total modules / 2 real inverters
        "temperature_model": "sapm",
        "temperature_model_params": TEMPERATURE_MODEL_PARAMETERS["sapm"]["close_mount_glass_glass"],
        "wind_speed_available": True,
    },
    34: {
        "module_name": "Sharp_NU_U240F1",
        "inverter_name": "Satcon_Technology__PVS_135__480V_",
        "tilt_deg": 11.2,
        "azimuth_deg": 180.0,
        "latitude": 36.1952,
        "longitude": -115.1582,
        "altitude_m": 620.0,
        "inverter_quantity": 1,  # real: Inverters.Inverter 0.quantity
        "modules_per_inverter": 611,  # real: 611 total modules / 1 real inverter
        "temperature_model": "sapm",
        "temperature_model_params": TEMPERATURE_MODEL_PARAMETERS["sapm"]["close_mount_glass_glass"],
        "wind_speed_available": True,
    },
}


class PVLibModelChainReference:
    """Real pvlib ModelChain physics reference for one development system.

    `predict(df) -> np.ndarray` matches the interface of `PVLibPhysicsReference` in
    `models.py` (kW, aligned to `df`'s row order), so this class is a drop-in replacement
    wherever that interface is consumed (e.g. `RAISolarChampion`'s `physics_model` arg) --
    without importing or reusing any of that class's hand-rolled formula.
    """

    def __init__(self, system_id: int) -> None:
        if system_id not in REAL_MODELCHAIN_CONFIG:
            raise ValueError(
                f"System {system_id} is PARAMETERIZATION_INSUFFICIENT for a real pvlib "
                "ModelChain (see pvlib_readiness.csv) -- no config registered, and none "
                "will be invented."
            )
        cfg = REAL_MODELCHAIN_CONFIG[system_id]
        self.system_id = system_id
        self.inverter_quantity = cfg["inverter_quantity"]
        self.wind_speed_available = cfg["wind_speed_available"]

        cec_mods = retrieve_sam("CECMod")
        cec_invs = retrieve_sam("CECInverter")
        module_params = cec_mods[cfg["module_name"]].to_dict()
        inverter_params = cec_invs[cfg["inverter_name"]].to_dict()

        pv_system = PVSystem(
            surface_tilt=cfg["tilt_deg"],
            surface_azimuth=cfg["azimuth_deg"],
            module_parameters=module_params,
            inverter_parameters=inverter_params,
            temperature_model_parameters=cfg["temperature_model_params"],
            modules_per_string=1,
            strings_per_inverter=cfg["modules_per_inverter"],
        )
        location = Location(cfg["latitude"], cfg["longitude"], tz="UTC", altitude=cfg["altitude_m"])
        self.mc = ModelChain(
            pv_system,
            location,
            dc_model="cec",
            ac_model="sandia",
            aoi_model="no_loss",
            spectral_model="no_loss",
            temperature_model=cfg["temperature_model"],
        )

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict expected AC power in kW for the whole real system (all real inverters).

        Requires real columns: timestamp_utc (tz-aware UTC), poa_wm2, ambient_temp_c, and
        (only when this system's wind channel is real, not degenerate) wind_speed_ms.
        """
        idx = pd.DatetimeIndex(df["timestamp_utc"])
        wind = (
            df["wind_speed_ms"].fillna(1.0).to_numpy()
            if self.wind_speed_available and "wind_speed_ms" in df.columns
            else np.ones(len(df))  # faiman/pvsyst default -- disclosed, see module docstring
        )
        weather = pd.DataFrame(
            {
                "effective_irradiance": df["poa_wm2"].fillna(0.0).to_numpy(),
                "temp_air": df["ambient_temp_c"].fillna(20.0).to_numpy(),
                "wind_speed": wind,
            },
            index=idx,
        )
        self.mc.run_model_from_effective_irradiance(weather)

        ac_w_per_inverter = np.nan_to_num(np.asarray(self.mc.results.ac, dtype=float), nan=0.0)
        ac_w_per_inverter = np.maximum(ac_w_per_inverter, 0.0)  # drop Pnt self-consumption draw
        p_ac_kw = (ac_w_per_inverter * self.inverter_quantity) / 1000.0

        # Zero at night, matching the same convention used by PVLibPhysicsReference /
        # SolarEmpiricalBaseline so downstream residual code sees a consistent contract.
        poa = df["poa_wm2"].fillna(0.0).to_numpy()
        elev = df["solar_elevation_deg"].fillna(-90.0).to_numpy() if "solar_elevation_deg" in df.columns else np.full(len(df), 90.0)
        night_mask = (elev <= 5.0) | (poa < 20.0)
        p_ac_kw[night_mask] = 0.0

        return np.round(p_ac_kw, 2)
