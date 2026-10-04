import type { LucideIcon } from "lucide-react";

interface Props {
  label:      string;
  value:      number | null;
  unit:       string;
  icon:       LucideIcon;
  color:      string;
  precision?: number;
  isAlert?:   boolean;
  subLabel?:  string;
  subValue?:  number | null;
}

export default function StatCard({
  label, value, unit, icon: Icon, color,
  precision = 1, isAlert = false, subLabel, subValue,
}: Props) {
  return (
    <div className={[
      "bg-gcs-surface border rounded-xl p-4 flex flex-col gap-2 transition-all duration-300",
      isAlert
        ? "border-adv-maint/60 shadow-[0_0_12px_rgba(239,68,68,0.2)]"
        : "border-gcs-border hover:border-gcs-muted",
    ].join(" ")}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">{label}</span>
        <Icon className={`w-4 h-4 ${color} opacity-70`} />
      </div>
      <div className="flex items-end gap-2">
        <span className={`font-mono tabular-nums text-3xl font-bold leading-none ${color}`}>
          {value !== null ? value.toFixed(precision) : "---"}
        </span>
        <span className="text-gcs-sub text-sm mb-0.5 font-mono">{unit}</span>
      </div>
      {subLabel && (
        <div className="flex items-center gap-1.5 pt-1 border-t border-gcs-border/50">
          <span className="text-gcs-sub text-xs font-mono">{subLabel}</span>
          <span className="text-gcs-sub text-xs font-mono font-semibold">
            {subValue != null ? subValue.toFixed(precision) : "---"} {unit}
          </span>
        </div>
      )}
    </div>
  );
}
