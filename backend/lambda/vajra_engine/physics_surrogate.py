"""
physics_surrogate.py
====================
VajraTwin – Rotax 914 F/UL algebraic physics surrogate.

Purpose
-------
Replace static lookup tables with a fast, edge-deployable thermodynamic
baseline for a turbocharged 4-cylinder aero-piston engine.

Design constraints
------------------
- Pure Python ``math`` only.  No scipy / no ODE solvers.
- Total cycle budget target: < 25 ms.
- First-order lumped thermal capacitance for EGT and CHT.
- Graceful clamping for impossible telemetry.

Outputs
-------
Physics residuals: Δ = Actual − Expected.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

# =============================================================================
# Engine / environment constants
# =============================================================================

# Rotax 914 F/UL geometry
DISPLACEMENT_M3 = 1211e-6       # 1211 cc → m³
RPM_PEAK        = 5500.0        # rev/min, approximate best-VE region

# Air / environment
R_AIR       = 287.05            # J/(kg·K), specific gas constant for dry air
P_AMB_PA    = 101325.0          # Pa, standard sea-level ambient pressure
GAMMA_AIR   = 1.4               # ratio of specific heats for air

# Turbocharger / intercooler
COMPRESSOR_EFF   = 0.70         # typical small turbo compressor efficiency
INTERCOOLER_EFF  = 0.65         # typical air-to-air intercooler effectiveness

# Thermal ceilings
EGT_MAX_C = 950.0               # °C, Rotax 914 upper EGT limit
CHT_MAX_C = 135.0               # °C, Rotax 914 upper CHT limit

# Lumped thermal time constants
TAU_EGT_S = 2.5                 # s, exhaust gas / probe thermal inertia
TAU_CHT_S = 25.0                # s, cylinder head thermal inertia

# Volumetric efficiency surrogate calibration
ETA_V_MAX         = 0.88
ETA_V_RPM_SENS    = 0.35
ETA_V_BOOST_SENS  = 0.03

# Steady-state EGT calibration
EGT_BASE_RISE    = 250.0        # °C above OAT at zero load
EGT_LOAD_GAIN    = 520.0        # °C per load factor
EGT_AIRFLOW_COOL = 180.0        # °C cooling per normalised airflow

# Steady-state CHT calibration
CHT_BASE_RISE    = 55.0         # °C above OAT at zero load
CHT_LOAD_GAIN    = 48.0         # °C per load factor
CHT_AIRFLOW_COOL = 12.0         # °C cooling per normalised airflow


# =============================================================================
# Small helpers
# =============================================================================

def clamp(value: float, low: float, high: float) -> float:
    """Clamp a scalar to [low, high] without numpy overhead."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _get_float(
    telemetry: Dict[str, Any],
    keys: tuple,
    default: Optional[float],
) -> Optional[float]:
    """Fetch the first matching telemetry key and convert to float."""
    for key in keys:
        if key in telemetry:
            try:
                return float(telemetry[key])
            except (TypeError, ValueError):
                continue
    return default


# =============================================================================
# Algebraic sub-models
# =============================================================================

def estimate_volumetric_efficiency(rpm: float, map_pa: float) -> float:
    """
    Estimate volumetric efficiency eta_v for a turbocharged aero-piston engine.

    This is an algebraic surrogate, not a table lookup.

    Parameters
    ----------
    rpm    : engine speed [rev/min]
    map_pa : manifold absolute pressure [Pa]

    Returns
    -------
    eta_v  : dimensionless volumetric efficiency, typically 0.55–0.95
    """
    if rpm <= 0.0:
        return 0.0

    # Normalised RPM around the best-VE region.
    rpm_norm = rpm / RPM_PEAK

    # Typical broad VE curve: peak near 5500 RPM, mild parabolic falloff.
    rpm_term = ETA_V_MAX - ETA_V_RPM_SENS * (rpm_norm - 1.0) ** 2

    # Boost term: higher MAP slightly improves VE until backpressure dominates.
    map_kpa     = map_pa / 1000.0
    ambient_kpa = P_AMB_PA / 1000.0
    boost_term  = ETA_V_BOOST_SENS * ((map_kpa - ambient_kpa) / 30.0)

    return clamp(rpm_term + boost_term, 0.55, 0.95)


def estimate_inlet_temperature(oat_c: float, map_pa: float) -> float:
    """
    Estimate turbocharged inlet temperature after compressor and intercooler.

    Parameters
    ----------
    oat_c  : outside air temperature [°C]
    map_pa : manifold absolute pressure [Pa]

    Returns
    -------
    T_inlet : inlet air temperature [K]
    """
    T_amb  = max(oat_c + 273.15, 200.0)
    map_pa = max(map_pa, P_AMB_PA)

    # Pressure ratio across compressor.
    pr = map_pa / P_AMB_PA
    if pr <= 1.0:
        return T_amb

    # Ideal isentropic compressor outlet temperature.
    T_ideal = T_amb * (pr ** ((GAMMA_AIR - 1.0) / GAMMA_AIR))

    # Real compressor outlet (with polytropic efficiency).
    T_compressor_out = T_amb + (T_ideal - T_amb) / COMPRESSOR_EFF

    # Intercooler pulls temperature back toward ambient.
    T_inlet = T_compressor_out - INTERCOOLER_EFF * (T_compressor_out - T_amb)

    return T_inlet


def calculate_mass_airflow(
    map_pa: float,
    rpm: float,
    T_inlet_k: float,
    eta_v: float,
) -> float:
    """
    Speed-density mass airflow for a 4-stroke engine.

    Formula
    -------
    m_dot_air = MAP · V_disp · (RPM/60) / (2 · R · T_inlet) · eta_v

    Units
    -----
    MAP       [Pa], V_disp [m³], RPM [rev/min → rev/s],
    R [J/(kg·K)], T_inlet [K], eta_v [-]

    Returns
    -------
    m_dot_air [kg/s]
    """
    if rpm <= 0.0 or map_pa <= 0.0 or T_inlet_k <= 0.0 or eta_v <= 0.0:
        return 0.0

    return (
        map_pa
        * DISPLACEMENT_M3
        * (rpm / 60.0)
        / (2.0 * R_AIR * T_inlet_k)
        * eta_v
    )


def _load_factor(map_pa: float, rpm: float) -> float:
    """
    Dimensionless engine load proxy: MAP ratio × RPM ratio.

    Parameters
    ----------
    map_pa : [Pa]
    rpm    : [rev/min]

    Returns
    -------
    load : dimensionless, clamped to 0.0–1.6
    """
    map_kpa     = map_pa / 1000.0
    ambient_kpa = P_AMB_PA / 1000.0
    return clamp((map_kpa / ambient_kpa) * (rpm / RPM_PEAK), 0.0, 1.6)


def estimate_steady_egt_c(
    oat_c: float,
    map_pa: float,
    rpm: float,
    m_dot_air_kg_s: float,
) -> float:
    """
    Algebraic steady-state Exhaust Gas Temperature baseline.

    Factors: OAT · MAP/RPM load · mass airflow cooling effect.

    Returns
    -------
    steady EGT [°C]
    """
    if rpm <= 0.0 or map_pa <= 0.0 or m_dot_air_kg_s <= 0.0:
        return oat_c

    load         = _load_factor(map_pa, rpm)
    airflow_norm = clamp(m_dot_air_kg_s / 0.08, 0.0, 2.0)

    egt_ss = (
        oat_c
        + EGT_BASE_RISE
        + EGT_LOAD_GAIN    * load
        - EGT_AIRFLOW_COOL * airflow_norm
    )
    return clamp(egt_ss, oat_c, EGT_MAX_C)


def estimate_steady_cht_c(
    oat_c: float,
    map_pa: float,
    rpm: float,
    m_dot_air_kg_s: float,
) -> float:
    """
    Algebraic steady-state Cylinder Head Temperature baseline.

    Factors: OAT · MAP/RPM load · mass airflow cooling effect.

    Returns
    -------
    steady CHT [°C]
    """
    if rpm <= 0.0 or map_pa <= 0.0 or m_dot_air_kg_s <= 0.0:
        return oat_c

    load         = _load_factor(map_pa, rpm)
    airflow_norm = clamp(m_dot_air_kg_s / 0.08, 0.0, 2.0)

    cht_ss = (
        oat_c
        + CHT_BASE_RISE
        + CHT_LOAD_GAIN    * load
        - CHT_AIRFLOW_COOL * airflow_norm
    )
    return clamp(cht_ss, oat_c, CHT_MAX_C)


# =============================================================================
# Thermal capacitance state
# =============================================================================

class ThermalState:
    """
    First-order lumped thermal capacitance for EGT and CHT.

    Uses the exact discrete update:

        T[n+1] = T[n] + (T_ss - T[n]) · (1 - exp(-dt / tau))

    This is algebraic, stable for any positive dt, and avoids ODE solvers.
    """

    __slots__ = ("egt_c", "cht_c", "initialized")

    def __init__(self, egt_c: float = 25.0, cht_c: float = 25.0) -> None:
        self.egt_c       = egt_c
        self.cht_c       = cht_c
        self.initialized = False

    def reset(
        self,
        egt_c: Optional[float] = None,
        cht_c: Optional[float] = None,
    ) -> None:
        """Reset thermal state. Useful for cold-start or test bench setup."""
        if egt_c is not None:
            self.egt_c = egt_c
        if cht_c is not None:
            self.cht_c = cht_c
        self.initialized = False

    def update(self, dt_s: float, egt_ss_c: float, cht_ss_c: float) -> None:
        """Advance thermal state toward steady-state values."""
        dt = clamp(dt_s, 0.0, 5.0)

        if not self.initialized:
            self.egt_c       = egt_ss_c
            self.cht_c       = cht_ss_c
            self.initialized = True
            return

        alpha_egt = 1.0 - math.exp(-dt / TAU_EGT_S)
        alpha_cht = 1.0 - math.exp(-dt / TAU_CHT_S)

        self.egt_c += (egt_ss_c - self.egt_c) * alpha_egt
        self.cht_c += (cht_ss_c - self.cht_c) * alpha_cht


# =============================================================================
# Main surrogate class
# =============================================================================

class PhysicsSurrogate:
    """
    Edge-deployable Rotax 914 F/UL physics surrogate.

    Instantiate once per engine / digital-twin instance so that thermal state
    persists between calls (Lambda warm-invocation friendly).
    """

    def __init__(self) -> None:
        self.thermal = ThermalState()

    def reset(
        self,
        egt_c: Optional[float] = None,
        cht_c: Optional[float] = None,
    ) -> None:
        """Reset the thermal state."""
        self.thermal.reset(egt_c, cht_c)

    def calculate_residuals(
        self, actual_telemetry_dict: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Master residual calculation.

        Expected keys in *actual_telemetry_dict* (flexible aliases accepted):

            rpm      / RPM / engine_rpm      [rev/min]
            map_pa   / MAP_Pa                [Pa]      (preferred)
            map_kpa  / MAP_kPa / map / MAP   [kPa]     (used if map_pa absent)
            oat_c    / OAT_C / oat / OAT     [°C]      (default 15.0)
            egt_c    / EGT_C / egt / EGT     [°C]      (optional)
            cht_c    / CHT_C / cht / CHT     [°C]      (optional)
            dt_s     / dt / delta_t          [s]       (default 0.05)

        Returns
        -------
        dict with residuals, baselines, and intermediate physics diagnostics.
        """

        # ------------------------------------------------------------------
        # 1. Telemetry ingestion and unit normalisation
        # ------------------------------------------------------------------
        rpm   = _get_float(actual_telemetry_dict, ("rpm", "RPM", "engine_rpm"), 0.0)
        oat_c = _get_float(actual_telemetry_dict, ("oat_c", "OAT_C", "oat", "OAT"), 15.0)
        dt_s  = _get_float(actual_telemetry_dict, ("dt_s", "dt", "delta_t"), 0.05)

        if "map_pa" in actual_telemetry_dict or "MAP_Pa" in actual_telemetry_dict:
            map_pa = _get_float(
                actual_telemetry_dict, ("map_pa", "MAP_Pa"), P_AMB_PA
            )
        else:
            map_kpa = _get_float(
                actual_telemetry_dict,
                ("map_kpa", "MAP_kPa", "map_hpa", "MAP_hPa", "map", "MAP"),
                P_AMB_PA / 1000.0,
            )
            # Accept hPa too – hPa and kPa are numerically identical
            map_pa = map_kpa * 1000.0  # type: ignore[operator]

        actual_egt = _get_float(
            actual_telemetry_dict, ("egt_c", "EGT_C", "egt_actual", "egt", "EGT"), None
        )
        actual_cht = _get_float(
            actual_telemetry_dict, ("cht_c", "CHT_C", "cht_actual", "cht", "CHT"), None
        )

        # ------------------------------------------------------------------
        # 2. Physical plausibility clamping
        # ------------------------------------------------------------------
        rpm   = clamp(rpm,   0.0,     7000.0)   # type: ignore[arg-type]
        oat_c = clamp(oat_c, -60.0,   60.0)     # type: ignore[arg-type]
        map_pa = clamp(map_pa if map_pa and map_pa >= 0 else P_AMB_PA, 0.0, 250000.0)  # type: ignore[arg-type]

        # Zero RPM → no combustion, no airflow; clamp MAP to ambient.
        if rpm <= 0.0:
            map_pa    = P_AMB_PA
            eta_v     = 0.0
            T_inlet_k = oat_c + 273.15  # type: ignore[operator]
            m_dot_air = 0.0
        else:
            # --------------------------------------------------------------
            # 3. Speed-density mass airflow
            # --------------------------------------------------------------
            eta_v     = estimate_volumetric_efficiency(rpm, map_pa)
            T_inlet_k = estimate_inlet_temperature(oat_c, map_pa)   # type: ignore[arg-type]
            m_dot_air = calculate_mass_airflow(map_pa, rpm, T_inlet_k, eta_v)

        # ------------------------------------------------------------------
        # 4. Steady-state thermal baselines
        # ------------------------------------------------------------------
        egt_ss = estimate_steady_egt_c(oat_c, map_pa, rpm, m_dot_air)  # type: ignore[arg-type]
        cht_ss = estimate_steady_cht_c(oat_c, map_pa, rpm, m_dot_air)  # type: ignore[arg-type]

        # ------------------------------------------------------------------
        # 5. Lumped thermal capacitance update
        # ------------------------------------------------------------------
        if not self.thermal.initialized:
            # Seed from actual telemetry if available to avoid startup spike.
            self.thermal.egt_c       = actual_egt if actual_egt is not None else egt_ss
            self.thermal.cht_c       = actual_cht if actual_cht is not None else cht_ss
            self.thermal.initialized = True
        else:
            self.thermal.update(dt_s, egt_ss, cht_ss)   # type: ignore[arg-type]

        expected_egt = self.thermal.egt_c
        expected_cht = self.thermal.cht_c

        # If actuals were missing, use expecteds so residual is gracefully zero.
        if actual_egt is None:
            actual_egt = expected_egt
        if actual_cht is None:
            actual_cht = expected_cht

        # ------------------------------------------------------------------
        # 6. Residuals: Δ = Actual − Expected
        # ------------------------------------------------------------------
        delta_egt = actual_egt - expected_egt
        delta_cht = actual_cht - expected_cht

        return {
            # Primary residual outputs
            "delta_egt_c":          delta_egt,
            "delta_cht_c":          delta_cht,
            # Expected baselines (thermal-capacitance corrected)
            "expected_egt_c":       expected_egt,
            "expected_cht_c":       expected_cht,
            # Actuals used
            "actual_egt_c":         actual_egt,
            "actual_cht_c":         actual_cht,
            # Intermediate physics (useful for CloudWatch / diagnostics)
            "mass_airflow_kg_s":    m_dot_air,
            "volumetric_efficiency": eta_v,
            "inlet_temp_k":         T_inlet_k,
            "steady_egt_c":         egt_ss,
            "steady_cht_c":         cht_ss,
            "load_factor":          _load_factor(map_pa, rpm) if rpm > 0.0 else 0.0,
            "rpm":                  rpm,
            "map_pa":               map_pa,
            "oat_c":                oat_c,       # type: ignore[dict-item]
            "dt_s":                 dt_s,        # type: ignore[dict-item]
        }


# =============================================================================
# Module-level singleton convenience API
# =============================================================================

_DEFAULT_SURROGATE: Optional[PhysicsSurrogate] = None


def calculate_residuals(actual_telemetry_dict: Dict[str, Any]) -> Dict[str, float]:
    """
    Master function called by the Lambda handler.

    Uses a module-level singleton so thermal state persists across warm
    invocations.  For multi-engine or unit-test isolation, instantiate
    ``PhysicsSurrogate`` directly.
    """
    global _DEFAULT_SURROGATE
    if _DEFAULT_SURROGATE is None:
        _DEFAULT_SURROGATE = PhysicsSurrogate()
    return _DEFAULT_SURROGATE.calculate_residuals(actual_telemetry_dict)


def reset_surrogate(
    egt_c: Optional[float] = None,
    cht_c: Optional[float] = None,
) -> None:
    """Reset the module-level singleton thermal state."""
    global _DEFAULT_SURROGATE
    if _DEFAULT_SURROGATE is None:
        _DEFAULT_SURROGATE = PhysicsSurrogate()
    _DEFAULT_SURROGATE.reset(egt_c, cht_c)


# =============================================================================
# Quick self-test  (python physics_surrogate.py)
# =============================================================================

if __name__ == "__main__":
    # Example telemetry frame – Rotax 914 at cruise.
    telemetry = {
        "rpm":     5500.0,
        "map_hpa": 125.0,   # handler sends hPa; surrogate accepts it via alias
        "oat_c":   15.0,
        "egt_c":   780.0,
        "cht_c":   118.0,
        "dt_s":    0.05,
    }

    result = calculate_residuals(telemetry)
    print("\nVajraTwin PhysicsSurrogate – self-test output")
    print("=" * 50)
    for key, value in result.items():
        print(f"  {key:>26s}: {value:+.4f}")
