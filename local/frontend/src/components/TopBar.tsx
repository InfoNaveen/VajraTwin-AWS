import { Activity, Power, Cpu, Database, Zap } from "lucide-react";
import type { FaultType } from "../types";

interface Props {
  isStreaming:      boolean;
  isLoading:        boolean;
  activeFault:      FaultType;
  connectionStatus: "live" | "idle" | "error";
  tickCount:        number;
  onToggleStream:   () => void;
  onSetFault:       (fault: FaultType, severity: number) => void;
}

const FAULT_OPTS: { label: string; value: FaultType; severity: number; color: string }[] = [
  { label: "No Fault",     value: "NONE",         severity: 0.0, color: "text-adv-go" },
  { label: "Oil Leak",     value: "OIL_LEAK",     severity: 0.8, color: "text-adv-derate" },
  { label: "Cooling Fail", value: "COOLING_FAIL", severity: 0.8, color: "text-adv-maint" },
  { label: "Misfire",      value: "MISFIRE",      severity: 0.8, color: "text-adv-monitor" },
];

const STATUS = {
  live:  { cls: "bg-adv-go animate-pulse-slow",  label: "LIVE",    text: "text-adv-go" },
  idle:  { cls: "bg-gcs-muted",                  label: "STANDBY", text: "text-gcs-sub" },
  error: { cls: "bg-adv-maint",                  label: "ERROR",   text: "text-adv-maint" },
};

export default function TopBar({
  isStreaming, isLoading, activeFault, connectionStatus,
  tickCount, onToggleStream, onSetFault,
}: Props) {
  const s = STATUS[connectionStatus];
  const hasFault = activeFault !== "NONE";

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gcs-surface border-b border-gcs-border flex-wrap gap-y-2">
      {/* Left — branding */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gcs-accent/10 border border-gcs-accent/30 rounded-lg flex items-center justify-center">
            <Activity className="w-4 h-4 text-gcs-accent" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide text-gcs-text leading-none">VAJRATWIN</div>
            <div className="text-[10px] text-gcs-sub font-mono leading-none mt-0.5">
              LOCAL GCS · 5-CH · ML DIAGNOSTICS · RUL
            </div>
          </div>
        </div>

        <div className="h-6 w-px bg-gcs-border" />

        <div className="hidden lg:flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-gcs-sub" />
            <span className="font-mono text-xs text-gcs-accent font-semibold">Rotax 914 F/UL</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-gcs-muted" />
            <span className="font-mono text-[10px] text-gcs-muted">:8000 · SQLite</span>
          </div>
        </div>
      </div>

      {/* Right — controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Status */}
        <div className={`flex items-center gap-2 ${s.text}`}>
          <span className={`inline-block w-2 h-2 rounded-full ${s.cls}`} />
          <span className="font-mono text-xs font-semibold tracking-wider">{s.label}</span>
          {tickCount > 0 && <span className="font-mono text-[10px] text-gcs-muted">#{tickCount}</span>}
          {isLoading && <span className="font-mono text-[10px] text-gcs-sub animate-pulse ml-1">COMPUTING…</span>}
        </div>

        <div className="h-6 w-px bg-gcs-border" />

        {/* Fault injection selector */}
        <div className={[
          "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono",
          hasFault
            ? "bg-adv-maint/10 border-adv-maint/50 text-adv-maint"
            : "bg-gcs-muted/10 border-gcs-muted/30 text-gcs-sub",
        ].join(" ")}>
          <Zap className="w-3.5 h-3.5 shrink-0" />
          <select
            disabled={!isStreaming}
            value={activeFault}
            onChange={(e) => {
              const opt = FAULT_OPTS.find((o) => o.value === e.target.value);
              if (opt) onSetFault(opt.value, opt.severity);
            }}
            className="bg-transparent outline-none cursor-pointer font-mono text-xs disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {FAULT_OPTS.map((o) => (
              <option key={o.value} value={o.value} className="bg-gcs-surface text-gcs-text">
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Stream toggle */}
        <button
          onClick={onToggleStream}
          className={[
            "flex items-center gap-2 px-4 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all duration-200",
            isStreaming
              ? "bg-adv-go/10 border-adv-go/50 text-adv-go hover:bg-adv-go/20"
              : "bg-gcs-accent/10 border-gcs-accent/40 text-gcs-accent hover:bg-gcs-accent/20",
          ].join(" ")}>
          <Power className="w-3.5 h-3.5" />
          {isStreaming ? "STOP STREAM" : "START STREAM"}
        </button>
      </div>
    </header>
  );
}
