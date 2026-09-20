// ---------------------------------------------------------------------------
// DiagnosticsPanel – Bedrock XAI root-cause display + advisory badge
// ---------------------------------------------------------------------------
import { BrainCircuit, Clock, Loader2 } from "lucide-react";
import AdvisoryBadge from "./AdvisoryBadge";
import type { TelemetryResponse } from "../types";

interface Props {
  response:  TelemetryResponse | null;
  isLoading: boolean;
}

export default function DiagnosticsPanel({ response, isLoading }: Props) {
  const advisory   = response?.xai_advisory;
  const timestamp  = response?.timestamp
    ? new Date(response.timestamp).toLocaleTimeString()
    : null;

  return (
    <div className="gcs-card flex flex-col gap-4">
      {/* Panel header */}
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-gcs-accent" />
        <span className="gcs-label">Amazon Bedrock XAI — Root Cause Analysis</span>
        {isLoading && (
          <Loader2 className="w-3.5 h-3.5 text-gcs-accent animate-spin ml-auto" />
        )}
      </div>

      {/* Advisory state badge */}
      <AdvisoryBadge
        advisory={advisory?.advisory ?? "PENDING"}
        animate={true}
      />

      {/* Root-cause narrative */}
      <div className="bg-gcs-bg rounded-lg border border-gcs-border p-4 min-h-[80px]">
        {advisory?.root_cause ? (
          <p className="text-sm leading-relaxed text-gcs-text font-sans animate-fade-in">
            {advisory.root_cause}
          </p>
        ) : (
          <p className="text-sm text-gcs-subtext font-mono italic">
            {isLoading
              ? "Invoking Claude 3 Haiku…"
              : "Start the stream to receive AI diagnostics."}
          </p>
        )}
      </div>

      {/* Last updated timestamp */}
      {timestamp && (
        <div className="flex items-center gap-1.5 text-xs text-gcs-subtext font-mono">
          <Clock className="w-3 h-3" />
          <span>Last analysis: {timestamp}</span>
        </div>
      )}
    </div>
  );
}
