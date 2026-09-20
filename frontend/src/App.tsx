// ---------------------------------------------------------------------------
// VajraTwin GCS – App.tsx
// Ground Control Station Dashboard
// ---------------------------------------------------------------------------
import {
  Gauge,
  Thermometer,
  Wind,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

import TopBar          from "./components/TopBar";
import StatCard        from "./components/StatCard";
import ResidualsChart  from "./components/ResidualsChart";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import AWSPanel        from "./components/AWSPanel";
import { useEngineStream } from "./hooks/useEngineStream";

// ── Helpers ────────────────────────────────────────────────────────────────

/** Return a Tailwind colour class based on residual magnitude */
function residualColor(delta: number, warnThreshold: number): string {
  const abs = Math.abs(delta);
  if (abs >= warnThreshold * 2) return "text-advisory-maint";
  if (abs >= warnThreshold)     return "text-advisory-derate";
  return "text-advisory-go";
}

/** Small inline trend arrow based on sign */
function TrendIcon({ value }: { value: number }) {
  if (value >  2) return <TrendingUp   className="w-3 h-3 text-advisory-maint inline" />;
  if (value < -2) return <TrendingDown className="w-3 h-3 text-advisory-go    inline" />;
  return              <Minus           className="w-3 h-3 text-gcs-subtext    inline" />;
}

// ── Dashboard ──────────────────────────────────────────────────────────────

export default function App() {
  const stream = useEngineStream();

  const telem    = stream.latestTelemetry;
  const response = stream.latestResponse;
  const physics  = response?.physics_model;
  const residuals = response?.residuals;

  // Alert flags
  const egtAlert = residuals ? Math.abs(residuals.delta_egt) >= 40 : false;
  const chtAlert = residuals ? Math.abs(residuals.delta_cht) >= 30 : false;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gcs-bg">

      {/* ── Top navigation bar ──────────────────────────────────────────── */}
      <TopBar
        engineId={telem?.engine_id ?? "rotax-914-001"}
        isStreaming={stream.isStreaming}
        isLoading={stream.isLoading}
        isFaultActive={stream.isFaultActive}
        connectionStatus={stream.connectionStatus}
        onToggleStream={stream.toggleStreaming}
        onToggleFault={stream.toggleFault}
      />

      {/* ── Main scrollable content ─────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

        {/* Error banner */}
        {stream.errorMessage && (
          <div className="flex items-center gap-3 px-4 py-3 bg-advisory-maint/10 border border-advisory-maint/30 rounded-xl text-advisory-maint text-xs font-mono animate-fade-in">
            <Activity className="w-4 h-4 shrink-0" />
            <span className="font-semibold">LINK ERROR:</span>
            <span className="truncate">{stream.errorMessage}</span>
          </div>
        )}

        {/* ── Row 1: Engine header strip ──────────────────────────────── */}
        <section className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gcs-text tracking-wide">
              Rotax 914 F/UL &nbsp;
              <span className="text-gcs-subtext font-normal text-base">
                — 115 hp Turbocharged Flat-Four
              </span>
            </h1>
            <p className="text-xs font-mono text-gcs-subtext mt-0.5">
              MALE UAV Aero-Piston Engine · Digital Twin · Physics Residual Monitor
            </p>
          </div>
          {/* Mission clock */}
          <div className="hidden md:flex flex-col items-end">
            <span className="gcs-label">Mission Time</span>
            <span className="font-mono text-sm text-gcs-text">
              {new Date().toLocaleTimeString()}
            </span>
          </div>
        </section>

        {/* ── Row 2: Live telemetry stat cards ────────────────────────── */}
        <section>
          <p className="gcs-label mb-3">Live Sensor Telemetry</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Engine Speed"
              value={telem?.rpm ?? null}
              unit="RPM"
              icon={Gauge}
              color="text-telemetry-rpm"
              precision={0}
            />
            <StatCard
              label="Manifold Pressure"
              value={telem?.map_hpa ?? null}
              unit="hPa"
              icon={Wind}
              color="text-telemetry-map"
              precision={1}
            />
            <StatCard
              label="Exhaust Gas Temp"
              value={telem?.egt_actual ?? null}
              unit="°C"
              icon={Thermometer}
              color="text-telemetry-egt"
              precision={1}
              isAlert={egtAlert}
              subLabel="Expected:"
              subValue={physics?.egt_expected ?? null}
            />
            <StatCard
              label="Cylinder Head Temp"
              value={telem?.cht_actual ?? null}
              unit="°C"
              icon={Thermometer}
              color="text-telemetry-cht"
              precision={1}
              isAlert={chtAlert}
              subLabel="Expected:"
              subValue={physics?.cht_expected ?? null}
            />
          </div>
        </section>

        {/* ── Row 3: Residual KPI strip + chart side-by-side ──────────── */}
        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">

          {/* Residual KPI cards – 1 column */}
          <div className="flex flex-col gap-4">
            <p className="gcs-label">Δ Residuals</p>

            {/* ΔEGT card */}
            <div className="gcs-card flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="gcs-label text-[10px]">Exhaust Gas Temp Δ</span>
                <TrendIcon value={residuals?.delta_egt ?? 0} />
              </div>
              <div className="flex items-end gap-1.5">
                <span
                  className={`gcs-value text-4xl font-bold leading-none ${
                    residuals ? residualColor(residuals.delta_egt, 40) : "text-gcs-subtext"
                  }`}
                >
                  {residuals
                    ? `${residuals.delta_egt > 0 ? "+" : ""}${residuals.delta_egt.toFixed(1)}`
                    : "---"}
                </span>
                <span className="text-gcs-subtext font-mono text-sm mb-0.5">°C</span>
              </div>
              <div className="text-[10px] font-mono text-gcs-subtext">
                Warn threshold: ±40 °C
              </div>
            </div>

            {/* ΔCHT card */}
            <div className="gcs-card flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="gcs-label text-[10px]">Cylinder Head Temp Δ</span>
                <TrendIcon value={residuals?.delta_cht ?? 0} />
              </div>
              <div className="flex items-end gap-1.5">
                <span
                  className={`gcs-value text-4xl font-bold leading-none ${
                    residuals ? residualColor(residuals.delta_cht, 30) : "text-gcs-subtext"
                  }`}
                >
                  {residuals
                    ? `${residuals.delta_cht > 0 ? "+" : ""}${residuals.delta_cht.toFixed(1)}`
                    : "---"}
                </span>
                <span className="text-gcs-subtext font-mono text-sm mb-0.5">°C</span>
              </div>
              <div className="text-[10px] font-mono text-gcs-subtext">
                Warn threshold: ±30 °C
              </div>
            </div>

            {/* Fault injection indicator */}
            {stream.isFaultActive && (
              <div className="gcs-card border-advisory-maint/50 bg-advisory-maint/5 animate-pulse">
                <p className="text-advisory-maint text-xs font-mono font-bold tracking-widest text-center">
                  ⚡ FAULT INJECTION ACTIVE
                </p>
                <p className="text-advisory-maint/70 text-[10px] font-mono text-center mt-1">
                  EGT/CHT spiked beyond normal envelope
                </p>
              </div>
            )}
          </div>

          {/* Scrolling residuals chart – 2 columns */}
          <div className="xl:col-span-2">
            <ResidualsChart data={stream.chartData} />
          </div>
        </section>

        {/* ── Row 4: AI diagnostics panel ─────────────────────────────── */}
        <section>
          <DiagnosticsPanel
            response={response ?? null}
            isLoading={stream.isLoading}
          />
        </section>

        {/* ── Row 5: AWS Infrastructure panel ─────────────────────────── */}
        <section>
          <AWSPanel
            tickCount={stream.tickCount ?? 0}
            advisorySource={response?.xai_advisory?.advisory_source}
          />
        </section>

        {/* ── Row 6: Last raw payload inspector (collapsible) ─────────── */}
        {response && (
          <section>
            <details className="gcs-card group">
              <summary className="gcs-label cursor-pointer list-none flex items-center gap-2 select-none">
                <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                Raw Lambda Response Payload
              </summary>
              <pre className="mt-3 text-[11px] font-mono text-gcs-subtext overflow-x-auto leading-relaxed">
                {JSON.stringify(response, null, 2)}
              </pre>
            </details>
          </section>
        )}

        {/* Bottom padding so last card isn't flush with viewport edge */}
        <div className="h-4" />
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="px-6 py-2 border-t border-gcs-border bg-gcs-surface flex items-center justify-between">
        <span className="text-[10px] font-mono text-gcs-muted">
          VAJRATWIN · MALE UAV DIGITAL TWIN · ROTAX 914 F/UL CALIBRATION
        </span>
        <span className="text-[10px] font-mono text-gcs-muted">
          AWS Bedrock · Claude 3 Haiku · DynamoDB TelemetryStore
        </span>
      </footer>
    </div>
  );
}
