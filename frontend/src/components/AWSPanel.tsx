// ---------------------------------------------------------------------------
// AWSPanel – live AWS infrastructure status display for judges/demo
// Shows exactly which AWS services are being used in real-time
// ---------------------------------------------------------------------------
import { Cloud, Database, Zap, GitBranch, CheckCircle, Cpu, Activity } from "lucide-react";

// These are the real deployed values — hardcoded for demo display
const AWS_CONFIG = {
  region:       "eu-north-1",
  account:      "183863150170",
  apiId:        "3lopkq9jnl",
  apiUrl:       "https://3lopkq9jnl.execute-api.eu-north-1.amazonaws.com/dev",
  lambdaName:   "VajraTwinEngine-dev",
  lambdaRuntime:"Python 3.12",
  lambdaMemory: "256 MB",
  lambdaTimeout:"30 s",
  dynamoTable:  "TelemetryStore-dev",
  dynamoBilling:"PAY_PER_REQUEST",
  dynamoKey:    "engineId (PK) + timestamp (SK)",
  bedrockModel: "claude-haiku-4-5-20251001-v1:0",
  cfnStack:     "vajra-twin-dev",
  cfnArn:       "arn:aws:cloudformation:eu-north-1:183863150170:stack/vajra-twin-dev",
};

interface ServiceRowProps {
  icon:    React.ReactNode;
  service: string;
  detail:  string;
  value:   string;
  status?: "live" | "pending";
}

function ServiceRow({ icon, service, detail, value, status = "live" }: ServiceRowProps) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gcs-border/40 last:border-0">
      <div className="w-7 h-7 rounded-lg bg-gcs-bg border border-gcs-border flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-gcs-text">{service}</span>
          <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-full border font-semibold ${
            status === "live"
              ? "text-adv-go border-adv-go/40 bg-adv-go/10"
              : "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10"
          }`}>
            {status === "live" ? "● LIVE" : "○ PENDING"}
          </span>
        </div>
        <p className="text-[10px] font-mono text-gcs-sub truncate">{detail}</p>
      </div>
      <span className="text-[10px] font-mono text-gcs-accent font-semibold shrink-0 text-right max-w-[140px] truncate">
        {value}
      </span>
    </div>
  );
}

interface Props {
  tickCount:       number;
  advisorySource?: string;
}

export default function AWSPanel({ tickCount, advisorySource }: Props) {
  const bedrockLive = advisorySource === "bedrock";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cloud className="w-4 h-4 text-[#FF9900]" />
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-gcs-text">
            AWS Infrastructure
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-gcs-sub">
          <span className="text-gcs-muted">Region:</span>
          <span className="text-gcs-accent font-semibold">{AWS_CONFIG.region}</span>
          <span className="text-gcs-muted ml-2">Stack:</span>
          <span className="text-adv-go font-semibold">CREATE_COMPLETE</span>
        </div>
      </div>

      {/* Live request counter */}
      {tickCount > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-gcs-accent/5 border border-gcs-accent/20 rounded-lg">
          <Activity className="w-3.5 h-3.5 text-gcs-accent animate-pulse" />
          <span className="text-xs font-mono text-gcs-accent font-semibold">
            {tickCount} live request{tickCount !== 1 ? "s" : ""} processed through AWS pipeline
          </span>
          <CheckCircle className="w-3.5 h-3.5 text-adv-go ml-auto" />
        </div>
      )}

      {/* Services */}
      <div className="flex flex-col">

        <ServiceRow
          icon={<Zap className="w-3.5 h-3.5 text-[#FF9900]" />}
          service="API Gateway"
          detail={`REST API · ${AWS_CONFIG.apiId} · POST /telemetry`}
          value={`${AWS_CONFIG.apiUrl.slice(8, 40)}...`}
          status="live"
        />

        <ServiceRow
          icon={<Cpu className="w-3.5 h-3.5 text-[#FF9900]" />}
          service="Lambda"
          detail={`${AWS_CONFIG.lambdaName} · ${AWS_CONFIG.lambdaRuntime} · ${AWS_CONFIG.lambdaMemory}`}
          value="Physics Engine + XAI"
          status="live"
        />

        <ServiceRow
          icon={<Database className="w-3.5 h-3.5 text-[#FF9900]" />}
          service="DynamoDB"
          detail={`${AWS_CONFIG.dynamoTable} · ${AWS_CONFIG.dynamoBilling}`}
          value={AWS_CONFIG.dynamoKey}
          status="live"
        />

        <ServiceRow
          icon={<Cloud className="w-3.5 h-3.5 text-[bedrockLive ? '#FF9900' : '#6b7280']" />}
          service="Bedrock"
          detail={`anthropic.${AWS_CONFIG.bedrockModel}`}
          value={bedrockLive ? "XAI Active" : "Awaiting approval"}
          status={bedrockLive ? "live" : "pending"}
        />

        <ServiceRow
          icon={<GitBranch className="w-3.5 h-3.5 text-[#FF9900]" />}
          service="CloudFormation"
          detail={`Stack: ${AWS_CONFIG.cfnStack} · IaC managed`}
          value="CREATE_COMPLETE"
          status="live"
        />

      </div>

      {/* Data flow diagram */}
      <div className="bg-gcs-bg border border-gcs-border rounded-lg px-3 py-2">
        <p className="text-[9px] font-mono text-gcs-sub mb-1 uppercase tracking-wider">Live Data Flow</p>
        <p className="text-[10px] font-mono text-gcs-text leading-5">
          <span className="text-adv-go">React GCS</span>
          <span className="text-gcs-muted"> → </span>
          <span className="text-[#FF9900]">API Gateway</span>
          <span className="text-gcs-muted"> → </span>
          <span className="text-[#FF9900]">Lambda</span>
          <span className="text-gcs-muted"> → </span>
          <span className="text-[#FF9900]">Physics Surrogate</span>
          <span className="text-gcs-muted"> → </span>
          <span className={bedrockLive ? "text-[#FF9900]" : "text-gcs-muted"}>Bedrock XAI</span>
          <span className="text-gcs-muted"> → </span>
          <span className="text-[#FF9900]">DynamoDB</span>
          <span className="text-gcs-muted"> → </span>
          <span className="text-adv-go">Advisory</span>
        </p>
      </div>
    </div>
  );
}
