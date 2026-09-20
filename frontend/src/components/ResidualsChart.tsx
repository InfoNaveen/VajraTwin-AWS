// ---------------------------------------------------------------------------
// ResidualsChart – live scrolling Recharts line chart for ΔEGT and ΔCHT
// ---------------------------------------------------------------------------
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ChartPoint } from "../types";

interface Props {
  data: ChartPoint[];
}

// Normal-scatter thresholds (from Rotax 914 diagnostic guide)
const EGT_WARN_THRESHOLD  =  40;
const EGT_NORM_THRESHOLD  = -40;
const CHT_WARN_THRESHOLD  =  30;
const CHT_NORM_THRESHOLD  = -30;

// Custom tooltip
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ color: string; name: string; value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gcs-bg border border-gcs-border rounded-lg px-3 py-2 text-xs font-mono shadow-xl">
      <p className="text-gcs-subtext mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-bold">{p.value > 0 ? "+" : ""}{p.value.toFixed(1)} °C</span>
        </p>
      ))}
    </div>
  );
}

export default function ResidualsChart({ data }: Props) {
  const isEmpty = data.length === 0;

  return (
    <div className="gcs-card flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="gcs-label">Physics Residuals</span>
          <p className="text-gcs-subtext text-xs mt-0.5 font-mono">
            Δ = Actual − Expected &nbsp;·&nbsp; Normal scatter: |ΔEGT| &lt; 20 °C, |ΔCHT| &lt; 15 °C
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 bg-[#fb923c]" />
            <span className="text-gcs-subtext">ΔEGT</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 bg-[#38bdf8]" />
            <span className="text-gcs-subtext">ΔCHT</span>
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-52">
        {isEmpty ? (
          <div className="h-full flex items-center justify-center text-gcs-subtext text-sm font-mono">
            Awaiting telemetry stream…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1f2937"
                vertical={false}
              />

              {/* Zero line */}
              <ReferenceLine y={0} stroke="#374151" strokeWidth={1} />

              {/* EGT warning bands */}
              <ReferenceLine
                y={EGT_WARN_THRESHOLD}
                stroke="#fb923c"
                strokeDasharray="4 4"
                strokeWidth={1}
                strokeOpacity={0.5}
              />
              <ReferenceLine
                y={EGT_NORM_THRESHOLD}
                stroke="#fb923c"
                strokeDasharray="4 4"
                strokeWidth={1}
                strokeOpacity={0.5}
              />

              {/* CHT warning bands */}
              <ReferenceLine
                y={CHT_WARN_THRESHOLD}
                stroke="#38bdf8"
                strokeDasharray="4 4"
                strokeWidth={1}
                strokeOpacity={0.5}
              />
              <ReferenceLine
                y={CHT_NORM_THRESHOLD}
                stroke="#38bdf8"
                strokeDasharray="4 4"
                strokeWidth={1}
                strokeOpacity={0.5}
              />

              <XAxis
                dataKey="time"
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={{ stroke: "#1f2937" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v}`}
                domain={["auto", "auto"]}
              />
              <Tooltip content={<CustomTooltip />} />

              <Line
                type="monotone"
                dataKey="delta_egt"
                name="ΔEGT"
                stroke="#fb923c"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#fb923c" }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="delta_cht"
                name="ΔCHT"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#38bdf8" }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
