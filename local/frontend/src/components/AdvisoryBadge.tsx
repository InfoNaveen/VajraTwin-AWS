import { AlertTriangle, CheckCircle, Info, Loader2, Ban } from "lucide-react";
import type { MissionAdvisory } from "../types";

interface Props { advisory: MissionAdvisory | "PENDING"; pulse?: boolean; }

const CFG: Record<string, {
  bg: string; border: string; text: string; glow: string;
  icon: React.ReactNode; label: string;
}> = {
  GO_FLIGHT: {
    bg: "bg-adv-go/10", border: "border-adv-go/50", text: "text-adv-go",
    glow: "shadow-[0_0_16px_rgba(34,197,94,0.25)]",
    icon: <CheckCircle className="w-5 h-5" />, label: "GO FLIGHT",
  },
  MAINTENANCE_REQUIRED_POST_FLIGHT: {
    bg: "bg-adv-monitor/10", border: "border-adv-monitor/50", text: "text-adv-monitor",
    glow: "shadow-[0_0_16px_rgba(234,179,8,0.25)]",
    icon: <Info className="w-5 h-5" />, label: "MAINT. POST-FLIGHT",
  },
  ABORT_SOON: {
    bg: "bg-adv-derate/10", border: "border-adv-derate/50", text: "text-adv-derate",
    glow: "shadow-[0_0_16px_rgba(249,115,22,0.25)]",
    icon: <AlertTriangle className="w-5 h-5" />, label: "ABORT SOON",
  },
  ABORT_IMMEDIATE: {
    bg: "bg-adv-maint/10", border: "border-adv-maint/60", text: "text-adv-maint",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.4)]",
    icon: <Ban className="w-5 h-5" />, label: "ABORT IMMEDIATE",
  },
  CALIBRATING: {
    bg: "bg-gcs-muted/20", border: "border-gcs-muted/40", text: "text-gcs-sub",
    glow: "",
    icon: <Loader2 className="w-5 h-5 animate-spin" />, label: "CALIBRATING (5 ticks)",
  },
  PENDING: {
    bg: "bg-gcs-muted/10", border: "border-gcs-muted/30", text: "text-gcs-sub",
    glow: "",
    icon: <Loader2 className="w-5 h-5 animate-spin" />, label: "AWAITING DATA",
  },
};

export default function AdvisoryBadge({ advisory, pulse = false }: Props) {
  const c = CFG[advisory] ?? CFG["ABORT_IMMEDIATE"];
  return (
    <div className={[
      "flex items-center gap-3 px-5 py-3 rounded-xl border transition-all duration-500",
      c.bg, c.border, c.text, c.glow,
      pulse && advisory === "ABORT_IMMEDIATE" ? "animate-pulse" : "",
    ].join(" ")}>
      {c.icon}
      <span className="font-mono font-bold text-sm tracking-widest uppercase">{c.label}</span>
    </div>
  );
}
