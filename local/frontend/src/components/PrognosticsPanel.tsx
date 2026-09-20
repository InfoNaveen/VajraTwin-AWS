// ---------------------------------------------------------------------------
// PrognosticsPanel – RUL health bar + Monte Carlo confidence band
// ---------------------------------------------------------------------------
import { HeartPulse, Timer, TrendingDown } from "lucide-react";
import AdvisoryBadge from "./AdvisoryBadge";
import type { Prognostics, MissionAdvisory } from "../types";

interface Props {
  prog:      Prognostics | null;
  isLoading: boolean;
}

function HealthBar({ pct }: { pct: number }) {
  const color =
    pct > 70 ? "bg-adv-go"
    : pct > 40 ? "bg-adv-monitor"
    : pct > 20 ? "bg-adv-derate"
    : "bg-adv-maint";

  return (
    <div className="w-full bg-gcs-border rounded-full h-3 overflow-hidden">
      <div
        className={`${color} h-3 rounded-full transition-all duration-700`}
        style={{ width: `${Math.max(pct, 0)}%` }}
      />
    </div>
  );
}

function rulLabel(min: number): string {
  if (min >= 999) return "∞  (nominal)";
  if (min >= 60)  return `${(min / 60).toFixed(1)} h`;
  return `${min.toFixed(0)} min`;
}

export default function PrognosticsPanel({ prog, isLoading }: Props) {
  const advisory = (prog?.mission_advisory ?? "PENDING") as MissionAdvisory | "PENDING";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <HeartPulse className="w-4 h-4 text-adv-go" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Mission Prognostics — RUL
        </span>
        <span className="text-[10px] font-mono text-gcs-muted ml-auto">
          Monte Carlo · 100 paths
        </span>
      </div>

      {/* Mission advisory badge */}
      <AdvisoryBadge advisory={advisory} pulse />

      {/* Health bar */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-gcs-sub">Engine Health</span>
          <span className={`font-bold ${
            (prog?.current_health ?? 100) > 70 ? "text-adv-go"
            : (prog?.current_health ?? 100) > 40 ? "text-adv-monitor"
            : "text-adv-maint"
          }`}>
            {prog ? `${prog.current_health.toFixed(1)}%` : "---"}
          </span>
        </div>
        <HealthBar pct={prog?.current_health ?? 100} />
      </div>

      {/* RUL stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Timer,       label: "Est. RUL",  value: prog ? rulLabel(prog.rul_minutes) : "---", color: "text-gcs-accent" },
          { icon: TrendingDown, label: "P5 (worst)", value: prog ? rulLabel(prog.rul_p5)    : "---", color: "text-adv-derate" },
          { icon: TrendingDown, label: "P95 (best)", value: prog ? rulLabel(prog.rul_p95)   : "---", color: "text-adv-go" },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="bg-gcs-bg border border-gcs-border rounded-lg p-3 flex flex-col gap-1">
            <div className="flex items-center gap-1">
              <Icon className={`w-3 h-3 ${color}`} />
              <span className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider">{label}</span>
            </div>
            <span className={`font-mono text-sm font-bold ${color}`}>{value}</span>
          </div>
        ))}
      </div>

      {isLoading && (
        <p className="text-[10px] font-mono text-gcs-sub text-center animate-pulse">
          Updating RUL estimate…
        </p>
      )}
    </div>
  );
}
