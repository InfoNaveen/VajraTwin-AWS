// ---------------------------------------------------------------------------
// StatCard – single telemetry parameter readout card
// ---------------------------------------------------------------------------
import type { LucideIcon } from "lucide-react";

interface Props {
  label:      string;
  value:      number | null;
  unit:       string;
  icon:       LucideIcon;
  color:      string;   // Tailwind text colour class, e.g. "text-telemetry-rpm"
  precision?: number;
  // Optional: alert state turns the card border red
  isAlert?:   boolean;
  // Optional: show a mini sub-value (e.g. expected baseline)
  subLabel?:  string;
  subValue?:  number | null;
}

export default function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  color,
  precision = 1,
  isAlert = false,
  subLabel,
  subValue,
}: Props) {
  const displayValue = value !== null ? value.toFixed(precision) : "---";
  const displaySub   = subValue !== null && subValue !== undefined
    ? subValue.toFixed(precision)
    : null;

  return (
    <div
      className={[
        "gcs-card flex flex-col gap-2 transition-all duration-300",
        isAlert
          ? "border-advisory-maint/60 shadow-[0_0_12px_rgba(239,68,68,0.2)]"
          : "hover:border-gcs-muted",
      ].join(" ")}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="gcs-label">{label}</span>
        <Icon className={`w-4 h-4 ${color} opacity-70`} />
      </div>

      {/* Main value */}
      <div className="flex items-end gap-2">
        <span className={`gcs-value text-3xl font-bold leading-none ${color}`}>
          {displayValue}
        </span>
        <span className="text-gcs-subtext text-sm mb-0.5 font-mono">{unit}</span>
      </div>

      {/* Optional baseline sub-value */}
      {subLabel && (
        <div className="flex items-center gap-1.5 pt-1 border-t border-gcs-border/50">
          <span className="text-gcs-subtext text-xs font-mono">{subLabel}</span>
          <span className="text-gcs-subtext text-xs font-mono font-semibold">
            {displaySub ?? "---"} {unit}
          </span>
        </div>
      )}
    </div>
  );
}
