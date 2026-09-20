// ---------------------------------------------------------------------------
// VajraTwin Local GCS – Shared TypeScript Types  (v2 — 5-channel)
// Mirrors all FastAPI Pydantic models exactly.
// ---------------------------------------------------------------------------

// ── Advisory / fault types ─────────────────────────────────────────────────
export type AdvisoryState =
  | "GO"
  | "GO WITH MONITORING"
  | "GO WITH DERATE"
  | "MAINTENANCE REQUIRED"
  | "PENDING"
  | "ERROR";

export type MissionAdvisory =
  | "GO_FLIGHT"
  | "MAINTENANCE_REQUIRED_POST_FLIGHT"
  | "ABORT_SOON"
  | "ABORT_IMMEDIATE"
  | "CALIBRATING";

export type FaultType = "NONE" | "OIL_LEAK" | "COOLING_FAIL" | "MISFIRE";

// ── POST /twin_analyze request ─────────────────────────────────────────────
export interface TwinIn {
  rpm:              number;
  map_kpa:          number;
  oat_c:            number;
  egt_avg_c:        number;
  cht_avg_c:        number;
  oil_temp_c:       number;
  oil_pressure_psi: number;
  vibration_rms_g:  number;
}

// ── Response sub-objects ───────────────────────────────────────────────────
export interface PhysicsResiduals {
  delta_egt:          number;
  delta_cht:          number;
  delta_oil_temp:     number;
  delta_oil_pressure: number;
  delta_vibration:    number;
  expected_egt:          number;
  expected_cht:          number;
  expected_oil_temp:     number;
  expected_oil_pressure: number;
  expected_vibration:    number;
}

export interface MLDiagnostics {
  anomaly_score:      number;
  fault_class:        string;
  stress_coefficient: number;
  status:             string;  // "CALIBRATING" | "ACTIVE"
}

export interface Prognostics {
  current_health:   number;
  rul_minutes:      number;
  rul_p5:           number;
  rul_p95:          number;
  mission_advisory: MissionAdvisory;
}

// ── Full /twin_analyze response ────────────────────────────────────────────
export interface TwinResponse {
  record_id:      number;
  timestamp:      string;
  telemetry:      TwinIn;
  residuals:      PhysicsResiduals;
  diagnostics:    MLDiagnostics;
  prognostics:    Prognostics;
  active_fault:   FaultType;
  fault_severity: number;
}

// ── Chart buffer point ─────────────────────────────────────────────────────
export interface ChartPoint {
  tick:               number;
  time:               string;
  // Residuals
  delta_egt:          number;
  delta_cht:          number;
  delta_oil_temp:     number;
  delta_oil_pressure: number;
  delta_vibration:    number;
  // Raw
  rpm:                number;
  egt:                number;
  cht:                number;
  oil_temp:           number;
  oil_pressure:       number;
  vibration:          number;
  // ML
  stress_coefficient: number;
  anomaly_score:      number;
  // Health
  current_health:     number;
}

// ── Hook state ─────────────────────────────────────────────────────────────
export interface EngineStreamState {
  latestTelemetry:  TwinIn | null;
  latestResponse:   TwinResponse | null;
  chartData:        ChartPoint[];
  isStreaming:      boolean;
  isLoading:        boolean;
  activeFault:      FaultType;
  connectionStatus: "live" | "idle" | "error";
  errorMessage:     string | null;
  tickCount:        number;
  toggleStreaming:  () => void;
  setFault:         (fault: FaultType, severity: number) => void;
}
