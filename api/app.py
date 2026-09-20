from fastapi import FastAPI, Request
from core.physics_surrogate import calculate_residuals
from core.ai_diagnostics import DiagnosticEngine
from core.mission_prognostics import PrognosticEngine

app = FastAPI()

# Global stateful engines
diagnostic_engine = DiagnosticEngine()
prognostic_engine = PrognosticEngine()

@app.post("/twin_analyze")
async def analyze_twin(request: Request):
    payload = await request.json()
    
    # 1. Physics Layer: Expected vs Actual Residuals
    residuals = calculate_residuals(payload)
    
    # 2. Diagnostics Layer: Root-cause anomaly detection
    diag_out = diagnostic_engine.process_frame(residuals)
    
    status = diag_out["status"]
    
    # 3. Handle Warm-up Buffer Gracefully
    if status == "CALIBRATING":
        return {
            "status": status,
            "fault_class": diag_out["fault_class"],
            "anomaly_score": diag_out["anomaly_score"],
            "stress_coefficient": diag_out["stress_coefficient"],
            "estimated_rul_minutes": 999.0,
            "mission_advisory": "CALIBRATING"
        }
        
    # 4. Prognostics Layer: Remaining Useful Life Monte Carlo
    stress_coeff = diag_out["stress_coefficient"]
    prog_out = prognostic_engine.calculate_rul(stress_coeff, delta_t_seconds=1.0)
    
    # 5. Merged Integration Response
    return {
        "status": status,
        "fault_class": diag_out["fault_class"],
        "anomaly_score": diag_out["anomaly_score"],
        "stress_coefficient": stress_coeff,
        "estimated_rul_minutes": prog_out["estimated_rul_minutes"],
        "mission_advisory": prog_out["mission_advisory"]
    }
