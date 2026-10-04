# VajraTwin — Local Development Environment

FastAPI + SQLite backend · React + Vite frontend · No AWS account required.

---

## Folder structure

```
local/
├── README.md
├── backend/
│   ├── main.py               ← FastAPI app (entry-point)
│   ├── database.py           ← SQLite init + insert + fetch
│   ├── models.py             ← Pydantic v2 request / response models
│   ├── rule_engine.py        ← Deterministic advisory (6-level decision tree)
│   ├── physics_surrogate.py  ← Rotax 914 algebraic surrogate (copied from backend/)
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts        ← dev server on :5174, proxies /api → :8000
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── main.tsx
        ├── App.tsx           ← full GCS dashboard
        ├── index.css
        ├── types/index.ts
        ├── hooks/
        │   └── useEngineStream.ts   ← 2 s simulation loop + POST /api/telemetry
        └── components/
            ├── TopBar.tsx
            ├── StatCard.tsx
            ├── ResidualsChart.tsx
            ├── DiagnosticsPanel.tsx
            └── AdvisoryBadge.tsx
```

---

## Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Python | 3.10+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| npm | 9+ | bundled with Node |

---

## 1 — Start the FastAPI backend

Open a terminal and run:

```bash
# Navigate to the backend folder
cd local/backend

# Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

# Install dependencies (FastAPI, Uvicorn, Pydantic)
pip install -r requirements.txt

# Start the server with hot-reload
uvicorn main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     vajratwin  SQLite database initialised at vajratwin.db
```

### Verify the backend is healthy

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"service":"VajraTwin Local","model":"Rotax 914 F/UL","status":"operational"}
```

### Test a single telemetry POST

```bash
curl -X POST http://127.0.0.1:8000/telemetry \
  -H "Content-Type: application/json" \
  -d "{\"engine_id\":\"rotax-914-001\",\"rpm\":5500,\"map_kpa\":125,\"oat_c\":15,\"egt_c\":820,\"cht_c\":118,\"dt_s\":0.05}"
```

### Browse the auto-generated API docs

Open **http://127.0.0.1:8000/docs** in your browser for the interactive Swagger UI.

---

## 2 — Start the React frontend

Open a **second** terminal and run:

```bash
# Navigate to the frontend folder
cd local/frontend

# Install npm dependencies (first time only — takes ~30 s)
npm install

# Start the Vite dev server
npm run dev
```

You should see:

```
  VITE v5.3.1  ready in 300 ms
  ➜  Local:   http://localhost:5174/
```

Open **http://localhost:5174** in your browser.

---

## 3 — Run the live demo

1. Click **START STREAM** in the top bar.
2. The dashboard posts synthetic telemetry to FastAPI every **2 seconds**.
3. Watch the **Residuals Chart** scroll and the **Advisory Badge** update.
4. Click **INJECT FAULT** to spike EGT/CHT and force a `MAINTENANCE REQUIRED` advisory.
5. Click **INJECT FAULT** again to restore normal envelope.
6. Click **STOP STREAM** to pause.

---

## 4 — Inspect the SQLite database

All telemetry and advisory records are persisted to `local/backend/vajratwin.db`.

```bash
# Open the SQLite shell
sqlite3 local/backend/vajratwin.db

# Inside the shell:
.mode column
.headers on
SELECT id, engine_id, timestamp, delta_egt, delta_cht, advisory FROM telemetry_log ORDER BY id DESC LIMIT 10;
.quit
```

Or retrieve records via the REST API:

```bash
curl "http://127.0.0.1:8000/history/rotax-914-001?limit=5"
```

---

## Architecture (local)

```
React GCS (Vite :5174)
        │
        │  POST /api/telemetry  (proxied by Vite → :8000)
        ▼
FastAPI (:8000)
  ├── physics_surrogate.calculate_residuals()
  │     └── Rotax 914 algebraic model (< 25 ms, pure Python)
  ├── rule_engine.get_advisory()
  │     └── 6-level deterministic decision tree
  └── database.insert_record()
        └── SQLite  vajratwin.db
```

---

## Differences from the AWS production deployment

| Feature | Local | AWS |
|---|---|---|
| Compute | FastAPI / Uvicorn | AWS Lambda |
| Advisory AI | Rule engine (deterministic) | Amazon Bedrock (Claude 3 Haiku) |
| Database | SQLite file | Amazon DynamoDB |
| Frontend hosting | Vite dev server | AWS Amplify |
| Physics model | Same `physics_surrogate.py` | Same `physics_surrogate.py` |
| CORS | FastAPI middleware | API Gateway + Lambda headers |

The physics surrogate is **identical** in both environments — a copy is kept in sync at `local/backend/physics_surrogate.py`.
