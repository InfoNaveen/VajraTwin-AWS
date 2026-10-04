// ---------------------------------------------------------------------------
// DiagnosticsPanel – ML anomaly score + fault class from sklearn models
// ---------------------------------------------------------------------------
import { BrainCircuit, ShieldAlert, Activity } from "lucide-react";
import type { MLDiagnostics } from "../types";

interface Props {
  diag:      MLDiagnostics | null;
  isLoading: boolean;
}

const FAULT_COLORS: Record<string, string> = {
  HEALTHY:      "text-adv-go    border-adv-go/40    bg-adv-go/10",
  OIL_LEAK:     "text-adv-derate border-adv-derate/40 bg-adv-derate/10",
  COOLING_FAIL: "text-adv-maint  border-adv-maint/50  bg-adv-maint/10",
  MISFIRE:      "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10",
  UNKNOWN:      "text-gcs-sub   border-gcs-border   bg-gcs-muted/10",
};

function AnomalyMeter({ score }: { score: number }) {
  // score is 0.0 (normal) or 1.0 (anomaly)
  const isAnomaly = score >= 1.0;
  return (
    <div className={[
      "flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-mono font-semibold",
      isAnomaly
        ? "bg-adv-maint/10 border-adv-maint/50 text-adv-maint"
        : "bg-adv-go/10   border-adv-go/40    text-adv-go",
    ].join(" ")}>
      <Activity className="w-3.5 h-3.5" />
      {isAnomaly ? "⚠ ANOMALY DETECTED" : "✓ NOMINAL"}
    </div>
  );
}

export default function DiagnosticsPanel({ diag, isLoading }: Props) {
  const faultClass = diag?.fault_class ?? "UNKNOWN";
  const faultColor = FAULT_COLORS[faultClass] ?? FAULT_COLORS["UNKNOWN"];

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          ML Diagnostics — sklearn Models
        </span>
        {diag?.status === "CALIBRATING" && (
          <span className="ml-auto text-[10px] font-mono text-gcs-muted animate-pulse">
            CALIBRATING…
          </span>
        )}
      </div>

      {/* Anomaly indicator */}
      <AnomalyMeter score={diag?.anomaly_score ?? 0} />

      {/* Fault class badge */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-gcs-sub">Fault Class</span>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold ${faultColor}`}>
          <ShieldAlert className="w-3.5 h-3.5" />
          {faultClass}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Anomaly Score",       value: diag ? diag.anomaly_score.toFixed(1)      : "---", color: diag?.anomaly_score ? "text-adv-maint" : "text-adv-go" },
          { label: "Stress Coefficient",  value: diag ? diag.stress_coefficient.toFixed(4) : "---", color: diag && diag.stress_coefficient > 1.5 ? "text-adv-derate" : "text-gcs-text" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gcs-bg border border-gcs-border rounded-lg p-3">
            <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1">{label}</p>
            <p className={`font-mono text-lg font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Model source tag */}
      <div className="flex items-center justify-between text-[10px] font-mono text-gcs-muted">
        <span>IsolationForest · RandomForest · GradientBoosting</span>
        {isLoading && <span className="animate-pulse">inferring…</span>}
      </div>
    </div>
  );
}
