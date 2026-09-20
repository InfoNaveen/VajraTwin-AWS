// ---------------------------------------------------------------------------
// VajraTwin GCS – Shared TypeScript Types
// ---------------------------------------------------------------------------

// ── Advisory States (must match Lambda/Bedrock output exactly) ─────────────
export type AdvisoryState =
  | "GO"
  | "GO WITH MONITORING"
  | "GO WITH DERATE"
  | "MAINTENANCE REQUIRED"
  | "PENDING"       // UI-only: waiting for first API response
  | "ERROR";        // UI-only: API call failed

// ── Raw telemetry sent to the API ─────────────────────────────────────────
export interface TelemetryPayload {
  engine_id:  string;
  rpm:        number;
  map_hpa:    number;
  egt_actual: number;
  cht_actual: number;
}

// ── Physics model baseline returned from Lambda ────────────────────────────
export interface PhysicsModel {
  egt_expected: number;
  cht_expected: number;
}

// ── Residuals returned from Lambda ────────────────────────────────────────
export interface Residuals {
  delta_egt: number;
  delta_cht: number;
}

// ── XAI Advisory returned from Bedrock (via Lambda) ──────────────────────
export interface XAIAdvisory {
  root_cause:      string;
  advisory:        AdvisoryState;
  advisory_source: string;   // "bedrock" | "rule_engine"
}

// ── Full Lambda response body ──────────────────────────────────────────────
export interface TelemetryResponse {
  engine_id:     string;
  timestamp:     string;
  telemetry:     TelemetryPayload;
  physics_model: PhysicsModel;
  residuals:     Residuals;
  xai_advisory:  XAIAdvisory;
}

// ── A single data point stored in the scrolling chart buffer ──────────────
export interface ChartPoint {
  tick:      number;    // monotonic counter used as X axis key
  time:      string;    // HH:MM:SS label
  delta_egt: number;
  delta_cht: number;
  egt:       number;
  cht:       number;
  rpm:       number;
  map_hpa:   number;
}

// ── State shape returned by the useEngineStream hook ─────────────────────
export interface EngineStreamState {
  // Latest telemetry snapshot
  latestTelemetry: TelemetryPayload | null;
  // Latest API response
  latestResponse:  TelemetryResponse | null;
  // Scrolling chart buffer (capped at MAX_CHART_POINTS)
  chartData:       ChartPoint[];
  // Connection / data state
  isStreaming:     boolean;
  isLoading:       boolean;
  isFaultActive:   boolean;
  connectionStatus: "live" | "idle" | "error";
  errorMessage:    string | null;
  tickCount:       number;
  // Controls
  toggleStreaming:  () => void;
  toggleFault:      () => void;
}
