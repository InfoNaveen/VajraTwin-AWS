// ---------------------------------------------------------------------------
// VajraTwin GCS – useEngineStream
// ---------------------------------------------------------------------------
// Custom React hook that drives the live telemetry simulation loop.
//
// Every 3 s it:
//   1. Generates synthetic Rotax 914 telemetry (with optional fault injection)
//   2. POSTs it to API Gateway
//   3. Parses the Lambda response (residuals + Bedrock advisory)
//   4. Appends a chart point to the rolling buffer
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AdvisoryState,
  ChartPoint,
  EngineStreamState,
  TelemetryPayload,
  TelemetryResponse,
} from "../types";

// ── Configuration ──────────────────────────────────────────────────────────
//   Replace this constant with your deployed API Gateway URL, e.g.:
//   "https://abc123.execute-api.ap-south-1.amazonaws.com/dev"
//   For local sam local start-api testing use: "http://127.0.0.1:3000"
export const API_GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://127.0.0.1:3000";

const ENGINE_ID         = "rotax-914-001";
const POLL_INTERVAL_MS  = 3000;
const MAX_CHART_POINTS  = 40;   // keep last 40 ticks (~2 minutes of data)

// ── Helpers ────────────────────────────────────────────────────────────────

/** Uniform random float in [min, max] */
const rand = (min: number, max: number): number =>
  Math.random() * (max - min) + min;

/** Format a Date as HH:MM:SS */
const toTimeLabel = (d: Date): string =>
  d.toTimeString().slice(0, 8);

/** Generate a synthetic telemetry snapshot */
function generateTelemetry(faultActive: boolean): TelemetryPayload {
  if (faultActive) {
    // Fault scenario: EGT and CHT spiked well above normal envelope
    // ΔEGT ≈ +60–90 °C  →  forces Bedrock into MAINTENANCE REQUIRED / DERATE
    return {
      engine_id:  ENGINE_ID,
      rpm:        rand(5200, 5800),
      map_hpa:    rand(118, 130),
      egt_actual: rand(850, 920),   // +60–120 °C above baseline
      cht_actual: rand(220, 250),   // +30–60 °C above baseline
    };
  }

  // Normal operating envelope – Rotax 914 cruise regime
  return {
    engine_id:  ENGINE_ID,
    rpm:        rand(4500, 5800),
    map_hpa:    rand(90, 130),
    egt_actual: rand(750, 820),
    cht_actual: rand(160, 205),
  };
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useEngineStream(): EngineStreamState {
  const [isStreaming,       setIsStreaming]       = useState(false);
  const [isLoading,         setIsLoading]         = useState(false);
  const [isFaultActive,     setIsFaultActive]     = useState(false);
  const [connectionStatus,  setConnectionStatus]  = useState<"live" | "idle" | "error">("idle");
  const [errorMessage,      setErrorMessage]      = useState<string | null>(null);
  const [latestTelemetry,   setLatestTelemetry]   = useState<TelemetryPayload | null>(null);
  const [latestResponse,    setLatestResponse]    = useState<TelemetryResponse | null>(null);
  const [chartData,         setChartData]         = useState<ChartPoint[]>([]);

  // Stable refs so the interval closure never goes stale
  const isFaultRef    = useRef(isFaultActive);
  const tickRef       = useRef(0);
  const intervalRef   = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { isFaultRef.current = isFaultActive; }, [isFaultActive]);

  // ── Core tick ────────────────────────────────────────────────────────────
  const runTick = useCallback(async () => {
    const payload = generateTelemetry(isFaultRef.current);
    setLatestTelemetry(payload);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_GATEWAY_URL}/telemetry`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data: TelemetryResponse = await res.json();
      setLatestResponse(data);
      setConnectionStatus("live");
      setErrorMessage(null);

      // Append to rolling chart buffer
      const now   = new Date();
      tickRef.current += 1;
      const point: ChartPoint = {
        tick:      tickRef.current,
        time:      toTimeLabel(now),
        delta_egt: data.residuals.delta_egt,
        delta_cht: data.residuals.delta_cht,
        egt:       payload.egt_actual,
        cht:       payload.cht_actual,
        rpm:       payload.rpm,
        map_hpa:   payload.map_hpa,
      };

      setChartData((prev) => {
        const next = [...prev, point];
        return next.length > MAX_CHART_POINTS
          ? next.slice(next.length - MAX_CHART_POINTS)
          : next;
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[VajraTwin] API error:", msg);
      setConnectionStatus("error");
      setErrorMessage(msg);

      // Inject an error advisory into the last response so the UI still updates
      setLatestResponse((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          xai_advisory: {
            root_cause: `Connection error: ${msg}`,
            advisory:   "ERROR" as AdvisoryState,
          },
        };
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Start / stop streaming ────────────────────────────────────────────────
  useEffect(() => {
    if (isStreaming) {
      runTick(); // immediate first tick
      intervalRef.current = setInterval(runTick, POLL_INTERVAL_MS);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (!latestResponse) setConnectionStatus("idle");
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isStreaming, runTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Controls ─────────────────────────────────────────────────────────────
  const toggleStreaming = useCallback(() => setIsStreaming((s) => !s), []);
  const toggleFault     = useCallback(() => setIsFaultActive((f) => !f), []);

  return {
    latestTelemetry,
    latestResponse,
    chartData,
    isStreaming,
    isLoading,
    isFaultActive,
    connectionStatus,
    errorMessage,
    toggleStreaming,
    toggleFault,
  };
}
