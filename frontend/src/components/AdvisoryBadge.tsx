// ---------------------------------------------------------------------------
// AdvisoryBadge – colour-coded operational state chip
// ---------------------------------------------------------------------------
import { AlertTriangle, CheckCircle, Info, Wrench, Loader2 } from "lucide-react";
import type { AdvisoryState } from "../types";

interface Props {
  advisory: AdvisoryState;
  animate?: boolean;
}

interface BadgeConfig {
  bg:     string;
  border: string;
  text:   string;
  glow:   string;
  icon:   React.ReactNode;
  label:  string;
}

const BADGE_MAP: Record<AdvisoryState, BadgeConfig> = {
  GO: {
    bg:     "bg-advisory-go/10",
    border: "border-advisory-go/50",
    text:   "text-advisory-go",
    glow:   "shadow-[0_0_16px_rgba(34,197,94,0.25)]",
    icon:   <CheckCircle className="w-5 h-5" />,
    label:  "GO",
  },
  "GO WITH MONITORING": {
    bg:     "bg-advisory-monitor/10",
    border: "border-advisory-monitor/50",
    text:   "text-advisory-monitor",
    glow:   "shadow-[0_0_16px_rgba(234,179,8,0.25)]",
    icon:   <Info className="w-5 h-5" />,
    label:  "GO WITH MONITORING",
  },
  "GO WITH DERATE": {
    bg:     "bg-advisory-derate/10",
    border: "border-advisory-derate/50",
    text:   "text-advisory-derate",
    glow:   "shadow-[0_0_16px_rgba(249,115,22,0.25)]",
    icon:   <AlertTriangle className="w-5 h-5" />,
    label:  "GO WITH DERATE",
  },
  "MAINTENANCE REQUIRED": {
    bg:     "bg-advisory-maint/10",
    border: "border-advisory-maint/60",
    text:   "text-advisory-maint",
    glow:   "shadow-[0_0_20px_rgba(239,68,68,0.35)]",
    icon:   <Wrench className="w-5 h-5" />,
    label:  "MAINTENANCE REQUIRED",
  },
  PENDING: {
    bg:     "bg-gcs-muted/20",
    border: "border-gcs-muted/40",
    text:   "text-gcs-subtext",
    glow:   "",
    icon:   <Loader2 className="w-5 h-5 animate-spin" />,
    label:  "AWAITING DATA",
  },
  ERROR: {
    bg:     "bg-advisory-maint/10",
    border: "border-advisory-maint/40",
    text:   "text-advisory-maint",
    glow:   "",
    icon:   <AlertTriangle className="w-5 h-5" />,
    label:  "COMMS ERROR",
  },
};

export default function AdvisoryBadge({ advisory, animate = false }: Props) {
  const cfg = BADGE_MAP[advisory] ?? BADGE_MAP["MAINTENANCE REQUIRED"];

  return (
    <div
      className={[
        "flex items-center gap-3 px-5 py-3 rounded-xl border",
        "transition-all duration-500",
        cfg.bg, cfg.border, cfg.text, cfg.glow,
        animate && advisory === "MAINTENANCE REQUIRED" ? "animate-pulse" : "",
      ].join(" ")}
    >
      {cfg.icon}
      <span className="font-mono font-bold text-sm tracking-widest uppercase">
        {cfg.label}
      </span>
    </div>
  );
}
