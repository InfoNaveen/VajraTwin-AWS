# VajraTwin — Real-Time Digital Twin for MALE UAV Aero-Piston Engines

> **Hackathon submission** · AWS Serverless · Rotax 914 F/UL calibration · Amazon Bedrock XAI

VajraTwin is a cloud-native digital twin that ingests live engine telemetry from a MALE (Medium-Altitude Long-Endurance) UAV, computes thermodynamic physics residuals in real time, and uses generative AI to provide root-cause analysis and actionable flight advisories — all within a single serverless Lambda invocation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Ground Control Station (GCS)                                           │
│  React + Vite + TypeScript + Tailwind CSS + Recharts                    │
│  AWS Amplify (hosting)                                                  │
└────────────────────────┬────────────────────────────────────────────────┘
                         │  POST /telemetry  (JSON)
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Amazon API Gateway  (REST)                                             │
│  Wide-open CORS · Stage: dev / staging / prod                           │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AWS Lambda  –  VajraTwinEngine  (Python 3.12, 256 MB, 30 s)           │
│                                                                         │
│  1. Telemetry ingestion & validation                                    │
│  2. physics_surrogate.calculate_residuals()                             │
│     ├─ Volumetric efficiency (algebraic, not table lookup)              │
│     ├─ Speed-density mass airflow                                       │
│     ├─ Turbocharger + intercooler inlet temperature                     │
│     └─ First-order lumped thermal capacitance (EGT τ=2.5s, CHT τ=25s) │
│  3. Amazon Bedrock  –  Claude 3 Haiku                                   │
│     └─ Rule-engine fallback (deterministic, zero-latency)              │
│  4. DynamoDB TelemetryStore write                                       │
│  5. JSON response → API Gateway → GCS                                  │
└───────┬──────────────────────────────┬──────────────────────────────────┘
        │                              │
        ▼                              ▼
┌───────────────────┐      ┌───────────────────────────┐
│  Amazon DynamoDB  │      │  Amazon Bedrock            │
│  TelemetryStore   │      │  anthropic.claude-3-haiku  │
│  PAY_PER_REQUEST  │      │  (XAI root-cause + state)  │
│  engineId + ts PK │      └───────────────────────────┘
└───────────────────┘
```

---

## Physics Engine — Rotax 914 F/UL Algebraic Surrogate

The `physics_surrogate.py` module replaces static lookup tables with a fast, edge-deployable thermodynamic model. It runs in **< 25 ms** using only Python's built-in `math` library.

| Sub-model | Method |
|---|---|
| Volumetric efficiency | Parabolic algebraic curve around RPM_PEAK (5500) |
| Inlet temperature | Isentropic compression + compressor η + intercooler effectiveness |
| Mass airflow | Speed-density equation (MAP · V_disp · RPM / 2RT · η_v) |
| EGT baseline | OAT + load-weighted rise − airflow cooling |
| CHT baseline | OAT + load-weighted rise − airflow cooling |
| Thermal dynamics | Exact first-order discrete update: T[n+1] = T[n] + ΔT·(1−e^(−dt/τ)) |

Residuals: **Δ = Actual − Expected** for both EGT and CHT.

---

## Bedrock XAI + Deterministic Fallback

The `get_advisory()` function provides **100% uptime** for the advisory signal:

```
Bedrock available?
    YES → Claude 3 Haiku analyses Δ-vector + thermodynamic state
           → returns root_cause (1–2 sentences) + advisory state
    NO  → Rule engine fires instantly (zero network calls)
           |ΔEGT| > 40 °C or |ΔCHT| > 30 °C  →  GO WITH DERATE
           load_factor > 1.2                   →  GO WITH MONITORING
           minor scatter                        →  GO WITH MONITORING
           all nominal                          →  GO
```

Advisory states (colour-coded in GCS):

| State | Colour | Meaning |
|---|---|---|
| GO | 🟢 Green | All parameters nominal |
| GO WITH MONITORING | 🟡 Yellow | Minor deviation, watch closely |
| GO WITH DERATE | 🟠 Orange | Reduce power, prepare to land |
| MAINTENANCE REQUIRED | 🔴 Red | Land immediately |

---

## API Reference

### `POST /telemetry`

**Request body:**

```json
{
  "engine_id": "rotax-914-001",
  "rpm":        5500,
  "map_kpa":    125.0,
  "oat_c":      15.0,
  "egt_c":      780.0,
  "cht_c":      118.0,
  "dt_s":       0.05
}
```

> `map_pa` (Pascals) is also accepted as an alias for `map_kpa`.
> `oat_c`, `dt_s` are optional (defaults: 15.0 °C, 0.05 s).

**Response body (`200 OK`):**

```json
{
  "engine_id": "rotax-914-001",
  "timestamp": "2026-09-19T10:00:00+00:00",
  "telemetry":     { "rpm": 5500, "map_kpa": 125.0, "oat_c": 15.0, "egt_c": 780.0, "cht_c": 118.0 },
  "physics_model": {
    "egt_expected": 741.06,
    "cht_expected": 118.19,
    "steady_egt_c": 741.06,
    "steady_cht_c": 118.19,
    "load_factor":  1.2337,
    "mass_airflow_kg_s": 0.07354,
    "volumetric_efficiency": 0.9037,
    "inlet_temp_c": 23.91
  },
  "residuals":     { "delta_egt": 38.94, "delta_cht": -0.19 },
  "xai_advisory":  {
    "root_cause":      "Minor elevated EGT residual consistent with slightly lean mixture at high MAP. Wastegate function nominal.",
    "advisory":        "GO WITH MONITORING",
    "advisory_source": "bedrock"
  }
}
```

---

## Repo Layout

```
VAJRAtwin/
├── template.yaml                        # AWS SAM IaC blueprint
├── samconfig.toml                       # SAM CLI deploy defaults (ap-south-1)
├── .gitignore
├── README.md
│
├── backend/
│   └── lambda/
│       └── vajra_engine/
│           ├── handler.py               # Lambda entry-point (fault-tolerant)
│           ├── physics_surrogate.py     # Rotax 914 algebraic surrogate
│           └── requirements.txt         # boto3 pinned
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env.example                     # VITE_API_GATEWAY_URL placeholder
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                      # Full GCS dashboard
│       ├── index.css
│       ├── types/index.ts               # Shared TypeScript types
│       ├── hooks/
│       │   └── useEngineStream.ts       # 3-second simulation + API fetch
│       └── components/
│           ├── TopBar.tsx               # Engine ID / status / controls
│           ├── StatCard.tsx             # Live telemetry readout card
│           ├── ResidualsChart.tsx       # Recharts scrolling Δ line chart
│           ├── DiagnosticsPanel.tsx     # Bedrock root-cause + advisory
│           └── AdvisoryBadge.tsx        # Colour-coded state chip
│
├── docs/
└── scripts/
    └── sample_event.json                # sam local invoke test payload
```

---

## Quick Start

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for `sam local`)
- Node.js 20+ and npm
- AWS credentials configured (`aws configure`)
- Amazon Bedrock model access enabled for `anthropic.claude-3-haiku-20240307-v1:0` in `ap-south-1`

### Backend

```bash
# 1. Build the Lambda package
sam build

# 2. Deploy to AWS (prompts for confirmation)
sam deploy --config-env default

# 3. Local end-to-end test (no AWS account needed)
sam local start-api
# In a second terminal:
curl -X POST http://127.0.0.1:3000/telemetry \
  -H "Content-Type: application/json" \
  -d @scripts/sample_event.json

# 4. Single invocation test
sam local invoke VajraTwinEngineFunction --event scripts/sample_event.json
```

### Frontend

```bash
cd frontend
npm install

# Point at your deployed API Gateway URL
cp .env.example .env.local
# Edit: VITE_API_GATEWAY_URL=https://<api-id>.execute-api.ap-south-1.amazonaws.com/dev

npm run dev          # http://localhost:5173
npm run build        # production build → dist/
```

### Deploy Frontend to Amplify

```bash
# One-time setup
aws amplify create-app --name vajra-twin-gcs
# Then push the frontend/dist/ folder or connect your Git repo in the Amplify console.
```

---

## Environment Variables (Lambda)

| Variable | Default | Description |
|---|---|---|
| `TELEMETRY_TABLE` | *(set by SAM)* | DynamoDB table name |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model ID |
| `LOG_LEVEL` | `INFO` | CloudWatch log verbosity |

---

## IAM Permissions (granted in template.yaml)

| Permission | Resource | Purpose |
|---|---|---|
| `bedrock:InvokeModel` | Claude 3 Haiku ARN | XAI root-cause analysis |
| `dynamodb:PutItem` | TelemetryStore ARN | Telemetry persistence |
| `logs:*` | `*` | CloudWatch logging |

---

## Technology Stack

| Layer | Technology |
|---|---|
| IaC | AWS SAM (CloudFormation transform) |
| API | Amazon API Gateway (REST) |
| Compute | AWS Lambda — Python 3.12 |
| Physics | Custom algebraic surrogate (`physics_surrogate.py`) |
| AI/XAI | Amazon Bedrock — Claude 3 Haiku |
| Database | Amazon DynamoDB (on-demand, PITR enabled) |
| Frontend | React 18 · Vite · TypeScript · Tailwind CSS · Recharts |
| Hosting | AWS Amplify |

---

*VajraTwin — making UAV engine health visible, explainable, and actionable.*
