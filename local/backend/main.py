"""
main.py
=======
VajraTwin Local – FastAPI application.

Endpoints
---------
GET  /health                  → service health check
POST /telemetry               → 2-channel EGT/CHT pipeline (original, kept intact)
POST /twin_analyze            → full 5-channel pipeline from VajraTwin-AWS repo
GET  /history/{engine_id}     → recent telemetry_log records
GET  /twin_history            → recent twin_log records
PUT  /fault                   → hot-swap fault_status.json for live fault injection

Pipeline for POST /twin_analyze
--------------------------------
  Payload (8 fields)
    ↓
  core/physics_surrogate.calculate_residuals()    → 5 residuals + 5 expected values
    ↓
  core/ai_diagnostics.DiagnosticEngine            → anomaly_score, fault_class, stress_coefficient
    ↓
  core/mission_prognostics.PrognosticEngine       → current_health, RUL, mission_advisory
    ↓
  database.insert_twin_record()                   → SQLite twin_log
    ↓
  JSON response

Run
---
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ensure local backend directory is on sys.path for sibling imports
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from database import (
    init_db, insert_record, fetch_recent,
    insert_twin_record, fetch_twin_recent,
)
from models import TelemetryIn, TelemetryOut, PhysicsModel, Residuals, XAIAdvisory
from rule_engine import get_advisory
from physics_surrogate import calculate_residuals as egt_cht_residuals   # Rotax 914 algebraic surrogate

# VajraTwin-AWS repo modules
from ai_diagnostics import DiagnosticEngine
from mission_prognostics import PrognosticEngine

# Physics surrogate from repo (5-channel)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "repo_physics",
    os.path.join(_BACKEND_DIR, "..", "vajra_aws", "core", "physics_surrogate.py"),
)
_repo_physics = _ilu.module_from_spec(_spec)   # type: ignore[arg-type]
_spec.loader.exec_module(_repo_physics)        # type: ignore[union-attr]
repo_calculate_residuals = _repo_physics.calculate_residuals

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vajratwin")

# ---------------------------------------------------------------------------
# Module-level singletons (warm Lambda-style: survive across requests)
# ---------------------------------------------------------------------------
_diag_engine = DiagnosticEngine()
_prog_engine  = PrognosticEngine()

# Path to the hot-swappable fault file
FAULT_FILE = os.path.join(_BACKEND_DIR, "fault_status.json")


def _load_fault_status() -> dict:
    try:
        with open(FAULT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"active_fault": "NONE", "severity": 0.0}


def _save_fault_status(data: dict) -> None:
    with open(FAULT_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    logger.info("SQLite initialised — twin_log and telemetry_log tables ready")
    logger.info("DiagnosticEngine and PrognosticEngine singletons live")
    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VajraTwin Local API",
    description="5-channel Digital Twin — Physics · ML Diagnostics · RUL Prognostics",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Pydantic models for /twin_analyze
# ===========================================================================

class TwinIn(BaseModel):
    """
    Full 8-channel telemetry tick (matches VajraTwin-AWS repo schema exactly).
    All sensor fields are optional so the endpoint degrades gracefully when
    oil / vibration sensors are not yet wired.
    """
    rpm:              float = Field(...,  ge=0,   le=7000,  description="Engine speed [rev/min]")
    map_kpa:          float = Field(...,  ge=0,   le=250,   description="Manifold pressure [kPa]")
    oat_c:            float = Field(15.0, ge=-60, le=60,    description="Outside air temp [°C]")
    egt_avg_c:        float = Field(...,                    description="Exhaust gas temp [°C]")
    cht_avg_c:        float = Field(...,                    description="Cylinder head temp [°C]")
    oil_temp_c:       float = Field(80.0,                   description="Oil temperature [°C]")
    oil_pressure_psi: float = Field(55.0,                   description="Oil pressure [psi]")
    vibration_rms_g:  float = Field(0.5,                    description="Vibration RMS [g]")


class FaultIn(BaseModel):
    active_fault: str   = Field("NONE", description="NONE | OIL_LEAK | COOLING_FAIL | MISFIRE")
    severity:     float = Field(0.0,    ge=0.0, le=1.0, description="0.0 = off, 1.0 = full")


class PhysicsResiduals(BaseModel):
    delta_egt:          float
    delta_cht:          float
    delta_oil_temp:     float
    delta_oil_pressure: float
    delta_vibration:    float
    expected_egt:          float
    expected_cht:          float
    expected_oil_temp:     float
    expected_oil_pressure: float
    expected_vibration:    float


class MLDiagnostics(BaseModel):
    anomaly_score:      float
    fault_class:        str
    stress_coefficient: float
    status:             str


class Prognostics(BaseModel):
    current_health:   float
    rul_minutes:      float
    rul_p5:           float
    rul_p95:          float
    mission_advisory: str


class TwinOut(BaseModel):
    record_id:   int
    timestamp:   str
    telemetry:   TwinIn
    residuals:   PhysicsResiduals
    diagnostics: MLDiagnostics
    prognostics: Prognostics
    active_fault:   str
    fault_severity: float


# ===========================================================================
# Routes
# ===========================================================================

@app.get("/", tags=["health"])
@app.get("/health", tags=["health"])
def health_check() -> dict:
    fault = _load_fault_status()
    return {
        "service":         "VajraTwin Local",
        "version":         "2.0.0",
        "model":           "Rotax 914 F/UL",
        "physics_engine":  "VajraTwin-AWS repo (5-channel)",
        "ml_models":       "IsolationForest · RandomForest · GradientBoosting",
        "prognostics":     "Monte Carlo RUL",
        "active_fault":    fault.get("active_fault", "NONE"),
        "fault_severity":  fault.get("severity", 0.0),
        "status":          "operational",
    }


# ---------------------------------------------------------------------------
# POST /twin_analyze  — full 5-channel pipeline
# ---------------------------------------------------------------------------
@app.post("/twin_analyze", response_model=TwinOut, tags=["twin"])
def twin_analyze(body: TwinIn) -> TwinOut:
    """
    Full VajraTwin-AWS pipeline:
      1. repo physics_surrogate → 5 residuals
      2. DiagnosticEngine       → anomaly score, fault class, stress coefficient
      3. PrognosticEngine       → health, RUL, mission advisory
      4. Persist to twin_log
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    fault_status = _load_fault_status()

    # ── Step 1: Physics residuals (repo 5-channel surrogate) ───────────────
    payload = body.model_dump()
    residuals_raw = repo_calculate_residuals(payload)

    # Compute expected baselines for UI display
    rpm, map_kpa, oat_c = body.rpm, body.map_kpa, body.oat_c
    expected_egt          = 400 + (2.0 * map_kpa) + (0.05 * rpm)
    expected_cht          = oat_c + (0.3 * expected_egt)
    expected_oil_temp     = expected_cht * 0.8
    expected_oil_pressure = (0.015 * rpm) - (0.2 * expected_oil_temp) + 20
    expected_vibration    = 0.5 + (rpm / 5000.0) ** 2

    logger.info(
        "twin_analyze: RPM=%.0f MAP=%.1f  "
        "ΔEGT=%+.1f ΔCHT=%+.1f ΔOIL_T=%+.1f ΔOIL_P=%+.2f ΔVib=%+.3f",
        rpm, map_kpa,
        residuals_raw["delta_egt"], residuals_raw["delta_cht"],
        residuals_raw["delta_oil_temp"], residuals_raw["delta_oil_pressure"],
        residuals_raw["delta_vibration"],
    )

    # ── Step 2: ML diagnostics ─────────────────────────────────────────────
    diag = _diag_engine.process_frame(residuals_raw)

    logger.info(
        "diagnostics: fault_class=%s  anomaly=%.1f  stress=%.4f  status=%s",
        diag["fault_class"], diag["anomaly_score"],
        diag["stress_coefficient"], diag["status"],
    )

    # ── Step 3: Prognostics / RUL ──────────────────────────────────────────
    prog = _prog_engine.calculate_rul(diag["stress_coefficient"], delta_t_seconds=1.0)

    logger.info(
        "prognostics: health=%.2f%%  RUL=%.1f min  advisory=%s",
        prog["current_health"], prog["estimated_rul_minutes"],
        prog["mission_advisory"],
    )

    # ── Step 4: Persist ────────────────────────────────────────────────────
    row: dict[str, Any] = {
        "timestamp":           timestamp,
        "rpm":                 body.rpm,
        "map_kpa":             body.map_kpa,
        "oat_c":               body.oat_c,
        "egt_avg_c":           body.egt_avg_c,
        "cht_avg_c":           body.cht_avg_c,
        "oil_temp_c":          body.oil_temp_c,
        "oil_pressure_psi":    body.oil_pressure_psi,
        "vibration_rms_g":     body.vibration_rms_g,
        # residuals
        "delta_egt":           residuals_raw["delta_egt"],
        "delta_cht":           residuals_raw["delta_cht"],
        "delta_oil_temp":      residuals_raw["delta_oil_temp"],
        "delta_oil_pressure":  residuals_raw["delta_oil_pressure"],
        "delta_vibration":     residuals_raw["delta_vibration"],
        # expected baselines
        "expected_egt":           expected_egt,
        "expected_cht":           expected_cht,
        "expected_oil_temp":      expected_oil_temp,
        "expected_oil_pressure":  expected_oil_pressure,
        "expected_vibration":     expected_vibration,
        # ML diagnostics
        "anomaly_score":       diag["anomaly_score"],
        "fault_class":         diag["fault_class"],
        "stress_coefficient":  diag["stress_coefficient"],
        "diag_status":         diag["status"],
        # prognostics
        "current_health":      prog["current_health"],
        "rul_minutes":         prog["estimated_rul_minutes"],
        "rul_p5":              prog["confidence_interval"][0],
        "rul_p95":             prog["confidence_interval"][1],
        "mission_advisory":    prog["mission_advisory"],
        # fault injection state
        "active_fault":        fault_status.get("active_fault", "NONE"),
        "fault_severity":      fault_status.get("severity", 0.0),
    }
    record_id = insert_twin_record(row)

    # ── Step 5: Response ────────────────────────────────────────────────────
    return TwinOut(
        record_id=record_id,
        timestamp=timestamp,
        telemetry=body,
        residuals=PhysicsResiduals(
            delta_egt=           round(residuals_raw["delta_egt"],           2),
            delta_cht=           round(residuals_raw["delta_cht"],           2),
            delta_oil_temp=      round(residuals_raw["delta_oil_temp"],      2),
            delta_oil_pressure=  round(residuals_raw["delta_oil_pressure"],  3),
            delta_vibration=     round(residuals_raw["delta_vibration"],     4),
            expected_egt=           round(expected_egt,           2),
            expected_cht=           round(expected_cht,           2),
            expected_oil_temp=      round(expected_oil_temp,      2),
            expected_oil_pressure=  round(expected_oil_pressure,  3),
            expected_vibration=     round(expected_vibration,     4),
        ),
        diagnostics=MLDiagnostics(
            anomaly_score=      round(diag["anomaly_score"],      3),
            fault_class=        diag["fault_class"],
            stress_coefficient= round(diag["stress_coefficient"], 4),
            status=             diag["status"],
        ),
        prognostics=Prognostics(
            current_health= round(prog["current_health"],           2),
            rul_minutes=    round(prog["estimated_rul_minutes"],     1),
            rul_p5=         round(prog["confidence_interval"][0],    1),
            rul_p95=        round(prog["confidence_interval"][1],    1),
            mission_advisory= prog["mission_advisory"],
        ),
        active_fault=   fault_status.get("active_fault", "NONE"),
        fault_severity= fault_status.get("severity", 0.0),
    )


# ---------------------------------------------------------------------------
# PUT /fault  — hot-swap fault injection without restarting the server
# ---------------------------------------------------------------------------
@app.put("/fault", tags=["twin"])
def set_fault(body: FaultIn) -> dict:
    """
    Write fault_status.json so the telemetry generator and twin_analyze
    endpoint both pick it up on the next tick.

    Valid active_fault values: NONE | OIL_LEAK | COOLING_FAIL | MISFIRE
    """
    valid = {"NONE", "OIL_LEAK", "COOLING_FAIL", "MISFIRE"}
    if body.active_fault not in valid:
        raise HTTPException(status_code=400, detail=f"active_fault must be one of {valid}")
    _save_fault_status({"active_fault": body.active_fault, "severity": body.severity})
    logger.info("Fault updated: %s  severity=%.2f", body.active_fault, body.severity)
    return {"active_fault": body.active_fault, "severity": body.severity, "status": "applied"}


# ---------------------------------------------------------------------------
# GET /twin_history — recent twin_log records
# ---------------------------------------------------------------------------
@app.get("/twin_history", tags=["twin"])
def get_twin_history(limit: int = 100) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be 1–1000")
    return fetch_twin_recent(limit)


# ---------------------------------------------------------------------------
# Original /telemetry endpoint — preserved intact
# ---------------------------------------------------------------------------
@app.post("/telemetry", response_model=TelemetryOut, tags=["telemetry"])
def post_telemetry(body: TelemetryIn) -> TelemetryOut:
    """Original 2-channel EGT/CHT pipeline (Rotax 914 algebraic surrogate)."""
    timestamp = datetime.now(timezone.utc).isoformat()

    surrogate_input: dict[str, Any] = {
        "rpm":     body.rpm,
        "map_kpa": body.map_kpa,
        "oat_c":   body.oat_c,
        "dt_s":    body.dt_s,
    }
    if body.egt_c is not None:
        surrogate_input["egt_c"] = body.egt_c
    if body.cht_c is not None:
        surrogate_input["cht_c"] = body.cht_c

    physics = egt_cht_residuals(surrogate_input)
    delta_egt = round(physics["delta_egt_c"], 2)
    delta_cht = round(physics["delta_cht_c"], 2)

    advisory = get_advisory(physics)

    record = {
        "engine_id":    body.engine_id,
        "timestamp":    timestamp,
        "rpm":          body.rpm,
        "map_kpa":      body.map_kpa,
        "oat_c":        body.oat_c,
        "egt_c":        body.egt_c,
        "cht_c":        body.cht_c,
        "dt_s":         body.dt_s,
        "egt_expected": physics["expected_egt_c"],
        "cht_expected": physics["expected_cht_c"],
        "delta_egt":    delta_egt,
        "delta_cht":    delta_cht,
        "load_factor":  physics["load_factor"],
        "mass_airflow": physics["mass_airflow_kg_s"],
        "vol_efficiency": physics["volumetric_efficiency"],
        "inlet_temp_c": physics["inlet_temp_k"] - 273.15,
        "advisory":     advisory["advisory"],
        "root_cause":   advisory["root_cause"],
        "advisory_source": advisory["advisory_source"],
    }
    row_id = insert_record(record)

    return TelemetryOut(
        engine_id=body.engine_id,
        timestamp=timestamp,
        record_id=row_id,
        telemetry=body,
        physics_model=PhysicsModel(
            egt_expected=          round(physics["expected_egt_c"],        2),
            cht_expected=          round(physics["expected_cht_c"],        2),
            steady_egt_c=          round(physics["steady_egt_c"],          2),
            steady_cht_c=          round(physics["steady_cht_c"],          2),
            load_factor=           round(physics["load_factor"],           4),
            mass_airflow_kg_s=     round(physics["mass_airflow_kg_s"],     5),
            volumetric_efficiency= round(physics["volumetric_efficiency"], 4),
            inlet_temp_c=          round(physics["inlet_temp_k"] - 273.15, 2),
        ),
        residuals=Residuals(delta_egt=delta_egt, delta_cht=delta_cht),
        xai_advisory=XAIAdvisory(
            root_cause=      advisory["root_cause"],
            advisory=        advisory["advisory"],        # type: ignore[arg-type]
            advisory_source= advisory["advisory_source"], # type: ignore[arg-type]
        ),
    )


@app.get("/history/{engine_id}", tags=["telemetry"])
def get_history(engine_id: str, limit: int = 100) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be 1–1000")
    return fetch_recent(engine_id, limit)
