// ---------------------------------------------------------------------------
// VajraTwin Local GCS – App.tsx  (v2 — 5-channel + ML + RUL)
// ---------------------------------------------------------------------------
import {
  Gauge, Thermometer, Wind, Droplets,
  Gauge as PressureIcon, Vibrate, TrendingUp, TrendingDown, Minus,
} from "lucide-react";

import TopBar           from "./components/TopBar";
import StatCard         from "./components/StatCard";
import ResidualsChart   from "./components/ResidualsChart";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import PrognosticsPanel from "./components/PrognosticsPanel";
import { useEngineStream } from "./hooks/useEngineStream";

// ── Helpers ────────────────────────────────────────────────────────────────
function deltaColor(v: number, warn: number) {
  const a = Math.abs(v);
  if (a >= warn * 2) return "text-adv-maint";
  if (a >= warn)     return "text-adv-derate";
  return "text-adv-go";
}

function ResidualKPI({
  label, value, unit, warn, precision = 2,
}: {
  label: string; value: number | null; unit: string; warn: number; precision?: number;
}) {
  const v = value ?? 0;
  const color = value !== null ? deltaColor(v, warn) : "text-gcs-sub";
  const Icon  = v >  0.001 ? TrendingUp
              : v < -0.001 ? TrendingDown
              : Minus;

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-3 flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          {label}
        </span>
        <Icon className={`w-3 h-3 ${color}`} />
      </div>
      <div className="flex items-end gap-1">
        <span className={`font-mono tabular-nums text-2xl font-bold leading-none ${color}`}>
          {value !== null ? `${v > 0 ? "+" : ""}${v.toFixed(precision)}` : "---"}
        </span>
        <span className="text-gcs-sub font-mono text-xs mb-0.5">{unit}</span>
      </div>
      <p className="text-[9px] font-mono text-gcs-muted">warn ±{warn}{unit}</p>
    </div>
  );
}

// ── Fault status banner ────────────────────────────────────────────────────
const FAULT_BANNERS: Record<string, { label: string; color: string; bg: string }> = {
  OIL_LEAK:     { label: "🛢  OIL LEAK FAULT ACTIVE",     color: "text-adv-derate", bg: "bg-adv-derate/10 border-adv-derate/40" },
  COOLING_FAIL: { label: "❄  COOLING FAILURE ACTIVE",     color: "text-adv-maint",  bg: "bg-adv-maint/10  border-adv-maint/50"  },
  MISFIRE:      { label: "⚡ MISFIRE FAULT ACTIVE",        color: "text-adv-monitor",bg: "bg-adv-monitor/10 border-adv-monitor/40" },
};

// ── Dashboard ──────────────────────────────────────────────────────────────
export default function App() {
  const stream   = useEngineStream();
  const t        = stream.latestTelemetry;
  const response = stream.latestResponse;
  const res      = response?.residuals;
  const diag     = response?.diagnostics ?? null;
  const prog     = response?.prognostics ?? null;
  const fault    = response?.active_fault ?? "NONE";

  const faultBanner = FAULT_BANNERS[fault];

  const egtAlert  = res ? Math.abs(res.delta_egt)          >= 40  : false;
  const chtAlert  = res ? Math.abs(res.delta_cht)          >= 30  : false;
  const oilTAlert = res ? Math.abs(res.delta_oil_temp)     >= 10  : false;
  const oilPAlert = res ? Math.abs(res.delta_oil_pressure) >= 3   : false;
  const vibAlert  = res ? Math.abs(res.delta_vibration)    >= 0.3 : false;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gcs-bg">

      {/* ── Top bar ───────────────────────────────────────────────────── */}
      <TopBar
        isStreaming={stream.isStreaming}
        isLoading={stream.isLoading}
        activeFault={stream.activeFault}
        connectionStatus={stream.connectionStatus}
        tickCount={stream.tickCount}
        onToggleStream={stream.toggleStreaming}
        onSetFault={stream.setFault}
      />

      {/* ── Scrollable body ───────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

        {/* Connection error banner */}
        {stream.errorMessage && (
          <div className="flex items-center gap-3 px-4 py-3 bg-adv-maint/10 border border-adv-maint/30 rounded-xl text-adv-maint text-xs font-mono animate-fade-in">
            <span className="font-semibold shrink-0">BACKEND ERROR:</span>
            <span className="truncate">{stream.errorMessage}</span>
            <span className="ml-auto text-adv-maint/60 shrink-0 hidden md:block">
              Is FastAPI running on :8000?
            </span>
          </div>
        )}

        {/* Active fault banner */}
        {faultBanner && (
          <div className={`flex items-center justify-between px-4 py-2.5 border rounded-xl text-xs font-mono font-bold animate-pulse ${faultBanner.color} ${faultBanner.bg}`}>
            <span>{faultBanner.label}</span>
            <span className="opacity-60 font-normal">
              severity {((response?.fault_severity ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* ── Section header ────────────────────────────────────────── */}
        <section className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-bold text-gcs-text tracking-wide">
              Rotax 914 F/UL
              <span className="text-gcs-sub font-normal text-base"> — 115 hp · 5-Channel Digital Twin</span>
            </h1>
            <p className="text-xs font-mono text-gcs-sub mt-0.5">
              VajraTwin-AWS Physics · IsolationForest · RandomForest · GradientBoosting · Monte Carlo RUL
            </p>
          </div>
          <div className="hidden md:flex flex-col items-end shrink-0">
            <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">DB Record</span>
            <span className="font-mono text-sm text-gcs-text">{response?.record_id ?? "—"}</span>
          </div>
        </section>

        {/* ── Row 1: 8-channel sensor cards ─────────────────────────── */}
        <section>
          <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub mb-3">
            Live Sensor Telemetry — 8 Channels
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Engine Speed"   value={t?.rpm            ?? null} unit="RPM" icon={Gauge}        color="text-tel-rpm" precision={0} />
            <StatCard label="MAP"            value={t?.map_kpa        ?? null} unit="kPa" icon={Wind}         color="text-tel-map" precision={1} />
            <StatCard label="EGT"            value={t?.egt_avg_c      ?? null} unit="°C"  icon={Thermometer}  color="text-tel-egt" precision={1}
              isAlert={egtAlert}
              subLabel="Exp:" subValue={res?.expected_egt ?? null} />
            <StatCard label="CHT"            value={t?.cht_avg_c      ?? null} unit="°C"  icon={Thermometer}  color="text-tel-cht" precision={1}
              isAlert={chtAlert}
              subLabel="Exp:" subValue={res?.expected_cht ?? null} />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
            <StatCard label="Oil Temp"       value={t?.oil_temp_c     ?? null} unit="°C"  icon={Thermometer}  color="text-[#a78bfa]" precision={1}
              isAlert={oilTAlert}
              subLabel="Exp:" subValue={res?.expected_oil_temp ?? null} />
            <StatCard label="Oil Pressure"   value={t?.oil_pressure_psi ?? null} unit="psi" icon={PressureIcon} color="text-[#34d399]" precision={1}
              isAlert={oilPAlert}
              subLabel="Exp:" subValue={res?.expected_oil_pressure ?? null} />
            <StatCard label="Vibration RMS"  value={t?.vibration_rms_g ?? null} unit="g"  icon={Vibrate}      color="text-[#f472b6]" precision={3}
              isAlert={vibAlert}
              subLabel="Exp:" subValue={res?.expected_vibration ?? null} />
            <StatCard label="OAT"            value={t?.oat_c          ?? null} unit="°C"  icon={Droplets}     color="text-[#93c5fd]" precision={1} />
          </div>
        </section>

        {/* ── Row 2: 5-channel residual KPIs ────────────────────────── */}
        <section>
          <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub mb-3">
            Physics Residuals — Δ = Actual − Expected
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <ResidualKPI label="ΔEGT"       value={res?.delta_egt          ?? null} unit="°C"  warn={40}  precision={1} />
            <ResidualKPI label="ΔCHT"       value={res?.delta_cht          ?? null} unit="°C"  warn={30}  precision={1} />
            <ResidualKPI label="ΔOil Temp"  value={res?.delta_oil_temp     ?? null} unit="°C"  warn={10}  precision={1} />
            <ResidualKPI label="ΔOil Press" value={res?.delta_oil_pressure ?? null} unit="psi" warn={3}   precision={2} />
            <ResidualKPI label="ΔVibration" value={res?.delta_vibration    ?? null} unit="g"   warn={0.3} precision={3} />
          </div>
        </section>

        {/* ── Row 3: Twin scrolling charts ──────────────────────────── */}
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ResidualsChart data={stream.chartData} mode="thermal"    />
          <ResidualsChart data={stream.chartData} mode="mechanical" />
        </section>

        {/* ── Row 4: Diagnostics + Prognostics ──────────────────────── */}
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <DiagnosticsPanel diag={diag}   isLoading={stream.isLoading} />
          <PrognosticsPanel prog={prog}   isLoading={stream.isLoading} />
        </section>

        {/* ── Row 5: Raw response inspector ─────────────────────────── */}
        {response && (
          <section>
            <details className="bg-gcs-surface border border-gcs-border rounded-xl p-4 group">
              <summary className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub cursor-pointer select-none flex items-center gap-2">
                <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                Raw /twin_analyze Response — record #{response.record_id}
              </summary>
              <pre className="mt-3 text-[11px] font-mono text-gcs-sub overflow-x-auto leading-relaxed">
                {JSON.stringify(response, null, 2)}
              </pre>
            </details>
          </section>
        )}

        <div className="h-4" />
      </main>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="px-6 py-2 border-t border-gcs-border bg-gcs-surface flex items-center justify-between">
        <span className="text-[10px] font-mono text-gcs-muted">
          VAJRATWIN LOCAL · 5-CH PHYSICS · SKLEARN DIAGNOSTICS · MONTE CARLO RUL
        </span>
        <span className="text-[10px] font-mono text-gcs-muted">
          FastAPI · SQLite · VajraTwin-AWS Core
        </span>
      </footer>
    </div>
  );
}
