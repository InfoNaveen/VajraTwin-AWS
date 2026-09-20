"""
models.py
=========
VajraTwin Local – Pydantic v2 request / response models.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Advisory state type
# ---------------------------------------------------------------------------
AdvisoryState = Literal[
    "GO",
    "GO WITH MONITORING",
    "GO WITH DERATE",
    "MAINTENANCE REQUIRED",
]


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
class TelemetryIn(BaseModel):
    """
    Incoming telemetry tick from the GCS or simulation loop.
    Accepts both map_kpa and map_pa as MAP input.
    """
    engine_id: str        = Field(...,  description="Unique engine identifier")
    rpm:       float      = Field(...,  ge=0,    le=7000,  description="Engine speed [rev/min]")
    map_kpa:   Optional[float] = Field(None, ge=0, le=250, description="Manifold pressure [kPa]")
    map_pa:    Optional[float] = Field(None, ge=0,         description="Manifold pressure [Pa]  (alias)")
    oat_c:     float      = Field(15.0, ge=-60,  le=60,   description="Outside air temperature [°C]")
    egt_c:     Optional[float] = Field(None,                description="Exhaust gas temperature [°C]")
    cht_c:     Optional[float] = Field(None,                description="Cylinder head temperature [°C]")
    dt_s:      float      = Field(0.05, gt=0,    le=5.0,  description="Time step [s]")

    @model_validator(mode="after")
    def resolve_map(self) -> "TelemetryIn":
        """Ensure map_kpa is always populated from whichever field was provided."""
        if self.map_kpa is None and self.map_pa is not None:
            self.map_kpa = self.map_pa / 1000.0
        if self.map_kpa is None:
            self.map_kpa = 101.325   # standard sea-level default
        return self


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------
class PhysicsModel(BaseModel):
    egt_expected:          float
    cht_expected:          float
    steady_egt_c:          float
    steady_cht_c:          float
    load_factor:           float
    mass_airflow_kg_s:     float
    volumetric_efficiency: float
    inlet_temp_c:          float


class Residuals(BaseModel):
    delta_egt: float
    delta_cht: float


class XAIAdvisory(BaseModel):
    root_cause:      str
    advisory:        AdvisoryState
    advisory_source: Literal["rule_engine"]   # local only — no Bedrock


# ---------------------------------------------------------------------------
# Full response
# ---------------------------------------------------------------------------
class TelemetryOut(BaseModel):
    engine_id:    str
    timestamp:    str
    record_id:    int

    telemetry:    TelemetryIn
    physics_model: PhysicsModel
    residuals:    Residuals
    xai_advisory: XAIAdvisory
