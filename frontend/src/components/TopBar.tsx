// ---------------------------------------------------------------------------
// TopBar – GCS navigation bar with engine ID, status, and control buttons
// ---------------------------------------------------------------------------
import { Activity, Power, Zap, ZapOff, Cpu } from "lucide-react";
import { API_GATEWAY_URL } from "../hooks/useEngineStream";

interface Props {
  engineId:        string;
  isStreaming:     boolean;
  isLoading:       boolean;
  isFaultActive:   boolean;
  connectionStatus: "live" | "idle" | "error";
  onToggleStream:  () => void;
  onToggleFault:   () => void;
}

const STATUS_CONFIG = {
  live:  { dot: "status-dot live",  label: "LIVE",         text: "text-advisory-go" },
  idle:  { dot: "status-dot idle",  label: "STANDBY",      text: "text-gcs-subtext" },
  error: { dot: "status-dot error", label: "LINK FAILURE", text: "text-advisory-maint" },
};

export default function TopBar({
  engineId,
  isStreaming,
  isLoading,
  isFaultActive,
  connectionStatus,
  onToggleStream,
  onToggleFault,
}: Props) {
  const status = STATUS_CONFIG[connectionStatus];

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gcs-surface border-b border-gcs-border">
      {/* Left – branding + engine ID */}
      <div className="flex items-center gap-4">
        {/* Logo mark */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gcs-accent/10 border border-gcs-accent/30 rounded-lg flex items-center justify-center">
            <Activity className="w-4 h-4 text-gcs-accent" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide text-gcs-text leading-none">
              VAJRATWIN
            </div>
            <div className="text-[10px] text-gcs-subtext font-mono leading-none mt-0.5">
              DIGITAL TWIN · GCS v1.0
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-gcs-border" />

        {/* Engine identifier */}
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-gcs-subtext" />
          <span className="font-mono text-xs text-gcs-subtext uppercase tracking-wider">
            Engine
          </span>
          <span className="font-mono text-xs text-gcs-accent font-semibold">
            {engineId}
          </span>
        </div>

        {/* API endpoint indicator */}
        <div className="hidden lg:flex items-center gap-1.5">
          <span className="font-mono text-[10px] text-gcs-muted">
            {API_GATEWAY_URL}/telemetry
          </span>
        </div>
      </div>

      {/* Right – status + controls */}
      <div className="flex items-center gap-3">
        {/* Connection status */}
        <div className={`flex items-center gap-2 ${status.text}`}>
          <span className={status.dot} />
          <span className="font-mono text-xs font-semibold tracking-wider">
            {status.label}
          </span>
          {isLoading && (
            <span className="font-mono text-[10px] text-gcs-subtext animate-pulse">
              PROCESSING…
            </span>
          )}
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-gcs-border" />

        {/* Fault Inject button */}
        <button
          onClick={onToggleFault}
          disabled={!isStreaming}
          className={[
            "flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold",
            "transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed",
            isFaultActive
              ? "bg-advisory-maint/15 border-advisory-maint/60 text-advisory-maint hover:bg-advisory-maint/25 animate-pulse"
              : "bg-gcs-muted/20 border-gcs-muted/40 text-gcs-subtext hover:border-advisory-maint/40 hover:text-advisory-maint",
          ].join(" ")}
          title={isStreaming ? "Toggle fault injection" : "Start stream first"}
        >
          {isFaultActive ? (
            <ZapOff className="w-3.5 h-3.5" />
          ) : (
            <Zap className="w-3.5 h-3.5" />
          )}
          {isFaultActive ? "FAULT ACTIVE" : "INJECT FAULT"}
        </button>

        {/* Stream toggle button */}
        <button
          onClick={onToggleStream}
          className={[
            "flex items-center gap-2 px-4 py-1.5 rounded-lg border text-xs font-mono font-semibold",
            "transition-all duration-200",
            isStreaming
              ? "bg-advisory-go/10 border-advisory-go/50 text-advisory-go hover:bg-advisory-go/20"
              : "bg-gcs-accent/10 border-gcs-accent/40 text-gcs-accent hover:bg-gcs-accent/20",
          ].join(" ")}
        >
          <Power className="w-3.5 h-3.5" />
          {isStreaming ? "STOP STREAM" : "START STREAM"}
        </button>
      </div>
    </header>
  );
}
