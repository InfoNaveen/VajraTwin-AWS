// ---------------------------------------------------------------------------
// VajraTwin Local GCS – useEngineStream  (v2 — 5-channel)
// ---------------------------------------------------------------------------
// Drives a 2-second simulation loop against POST /api/twin_analyze.
// Fault injection is now server-side: calling setFault() hits PUT /api/fault,
// which writes fault_status.json — the same file the telemetry generator reads.
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ChartPoint,
  EngineStreamState,
  FaultType,
  TwinIn,
  TwinResponse,
} from "../types";

// ── Config ─────────────────────────────────────────────────────────────────
const POLL_MS          = 2000;
const MAX_CHART_POINTS = 60;
const TWIN_URL         = "/api/twin_analyze";
const FAULT_URL        = "/api/fault";

// ── Helpers ────────────────────────────────────────────────────────────────
const rand = (lo: number, hi: number) => Math.random() * (hi - lo) + lo;
const hms  = (d: Date) => d.toTimeString().slice(0, 8);

/** Generate synthetic 8-channel telemetry in the Rotax 914 cruise envelope. */
function generateTelemetry(): TwinIn {
  const rpm     = rand(4500, 5800);
  const map_kpa = rand(90, 130);
  const oat_c   = rand(10, 30);

  // Physics-consistent baselines (same formulas as repo physics_surrogate)
  const egt_base = 400 + 2.0 * map_kpa + 0.05 * rpm;
  const cht_base = oat_c + 0.3 * egt_base;
  const oil_base = cht_base * 0.8;
  const oilp_base = 0.015 * rpm - 0.2 * oil_base + 20;
  const vib_base  = 0.5 + (rpm / 5000) ** 2;

  // Add sensor jitter (small noise only — faults are applied server-side)
  return {
    rpm,
    map_kpa,
    oat_c,
    egt_avg_c:        egt_base  + rand(-3, 3),
    cht_avg_c:        cht_base  + rand(-2, 2),
    oil_temp_c:       oil_base  + rand(-2, 2),
    oil_pressure_psi: oilp_base + rand(-0.5, 0.5),
    vibration_rms_g:  vib_base  + rand(-0.03, 0.03),
  };
}

// ── Hook ───────────────────────────────────────────────────────────────────
export function useEngineStream(): EngineStreamState {
  const [isStreaming,      setIsStreaming]      = useState(false);
  const [isLoading,        setIsLoading]        = useState(false);
  const [activeFault,      setActiveFault]      = useState<FaultType>("NONE");
  const [connectionStatus, setConnectionStatus] = useState<"live"|"idle"|"error">("idle");
  const [errorMessage,     setErrorMessage]     = useState<string | null>(null);
  const [latestTelemetry,  setLatestTelemetry]  = useState<TwinIn | null>(null);
  const [latestResponse,   setLatestResponse]   = useState<TwinResponse | null>(null);
  const [chartData,        setChartData]        = useState<ChartPoint[]>([]);
  const [tickCount,        setTickCount]        = useState(0);

  const tickRef     = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Single tick ─────────────────────────────────────────────────────────
  const runTick = useCallback(async () => {
    const payload = generateTelemetry();
    setLatestTelemetry(payload);
    setIsLoading(true);

    try {
      const res = await fetch(TWIN_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status} – ${text}`);
      }

      const data: TwinResponse = await res.json();
      setLatestResponse(data);
      setActiveFault(data.active_fault);
      setConnectionStatus("live");
      setErrorMessage(null);

      // Append rolling chart point
      tickRef.current += 1;
      setTickCount(tickRef.current);

      const point: ChartPoint = {
        tick:               tickRef.current,
        time:               hms(new Date()),
        delta_egt:          data.residuals.delta_egt,
        delta_cht:          data.residuals.delta_cht,
        delta_oil_temp:     data.residuals.delta_oil_temp,
        delta_oil_pressure: data.residuals.delta_oil_pressure,
        delta_vibration:    data.residuals.delta_vibration,
        rpm:                payload.rpm,
        egt:                payload.egt_avg_c,
        cht:                payload.cht_avg_c,
        oil_temp:           payload.oil_temp_c,
        oil_pressure:       payload.oil_pressure_psi,
        vibration:          payload.vibration_rms_g,
        stress_coefficient: data.diagnostics.stress_coefficient,
        anomaly_score:      data.diagnostics.anomaly_score,
        current_health:     data.prognostics.current_health,
      };

      setChartData((prev) => {
        const next = [...prev, point];
        return next.length > MAX_CHART_POINTS
          ? next.slice(next.length - MAX_CHART_POINTS)
          : next;
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[VajraTwin] tick error:", msg);
      setConnectionStatus("error");
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Interval management ─────────────────────────────────────────────────
  useEffect(() => {
    if (isStreaming) {
      runTick();
      intervalRef.current = setInterval(runTick, POLL_MS);
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

  // ── Fault injection — hits server PUT /fault ─────────────────────────────
  const setFault = useCallback(async (fault: FaultType, severity: number) => {
    try {
      await fetch(FAULT_URL, {
        method:  "PUT",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ active_fault: fault, severity }),
      });
      setActiveFault(fault);
    } catch (err) {
      console.error("[VajraTwin] fault injection error:", err);
    }
  }, []);

  const toggleStreaming = useCallback(() => setIsStreaming((s) => !s), []);

  return {
    latestTelemetry,
    latestResponse,
    chartData,
    isStreaming,
    isLoading,
    activeFault,
    connectionStatus,
    errorMessage,
    tickCount,
    toggleStreaming,
    setFault,
  };
}
