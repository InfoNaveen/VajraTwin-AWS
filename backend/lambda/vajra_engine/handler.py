"""
VajraTwin – Lambda Handler  (Hackathon Final)
=============================================
Real-Time Digital Twin for MALE UAV Aero-Piston Engines
Calibrated model: Rotax 914 F/UL (turbocharged, 115 hp)

Pipeline
--------
1. Ingest POST /telemetry JSON payload
2. physics_surrogate.calculate_residuals() → full thermodynamic state
3. Amazon Bedrock Claude 3 Haiku → XAI root-cause + advisory
   └─ Deterministic rule-based fallback if Bedrock is unavailable
4. DynamoDB TelemetryStore → persist comprehensive record
5. Return structured JSON (CORS on every response path)

Fault-tolerance guarantee
--------------------------
Bedrock failures (ClientError, timeout, JSON parse error) never crash the
handler.  A local rule-based engine instantly provides a safe advisory so
the live demonstration always produces a result.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Physics surrogate  (co-located in the Lambda package)
# ---------------------------------------------------------------------------
from physics_surrogate import calculate_residuals as physics_calculate_residuals

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
TELEMETRY_TABLE  = os.environ["TELEMETRY_TABLE"]
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0"
)

# ---------------------------------------------------------------------------
# AWS Clients  (module-level → reused across warm invocations)
# ---------------------------------------------------------------------------
_bedrock = boto3.client("bedrock-runtime")
_dynamo  = boto3.resource("dynamodb")
_table   = _dynamo.Table(TELEMETRY_TABLE)

# ---------------------------------------------------------------------------
# CORS headers – must be present on EVERY response, including error paths
# ---------------------------------------------------------------------------
CORS_HEADERS: dict[str, str] = {
    "Content-Type":                 "application/json",
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _response(status_code: int, body: Any) -> dict:
    """Build an API Gateway Lambda Proxy–compatible response."""
    return {
        "statusCode": status_code,
        "headers":    CORS_HEADERS,
        "body":       json.dumps(body),
    }


# ===========================================================================
# SECTION 1 – Deterministic Rule-Based Fallback Advisory
# ===========================================================================
# This runs instantly without any network call.  It is invoked when Bedrock
# is unavailable, returns malformed JSON, or times out.
# Thresholds are derived from Rotax 914 field service limits.
# ===========================================================================

def _rule_based_advisory(physics: dict) -> dict:
    """
    Local deterministic fallback advisory engine.

    Decision tree (evaluated in priority order):
      1. |ΔEGT| > 40 °C  →  GO WITH DERATE
      2. |ΔCHT| > 30 °C  →  GO WITH DERATE
      3. load_factor > 1.2  →  GO WITH MONITORING
      4. |ΔEGT| > 20 °C or |ΔCHT| > 15 °C  →  GO WITH MONITORING
      5. otherwise  →  GO
    """
    delta_egt   = abs(physics.get("delta_egt_c",  0.0))
    delta_cht   = abs(physics.get("delta_cht_c",  0.0))
    load_factor = physics.get("load_factor", 0.0)

    if delta_egt > 40.0 or delta_cht > 30.0:
        return {
            "advisory":   "GO WITH DERATE",
            "root_cause": (
                "Fallback Diagnostic: High thermal residual detected. "
                "Suspected turbocharger wastegate stiction or mixture imbalance. "
                f"ΔEGT={physics.get('delta_egt_c', 0.0):+.1f} °C  "
                f"ΔCHT={physics.get('delta_cht_c', 0.0):+.1f} °C."
            ),
            "source": "rule_engine",
        }

    if load_factor > 1.2:
        return {
            "advisory":   "GO WITH MONITORING",
            "root_cause": (
                "Fallback Diagnostic: Engine load factor exceeds rated threshold "
                f"({load_factor:.3f}).  Possible MAP sensor drift or wastegate "
                "partially stuck closed.  Reduce throttle and monitor."
            ),
            "source": "rule_engine",
        }

    if delta_egt > 20.0 or delta_cht > 15.0:
        return {
            "advisory":   "GO WITH MONITORING",
            "root_cause": (
                "Fallback Diagnostic: Minor thermal deviation detected "
                f"(ΔEGT={physics.get('delta_egt_c', 0.0):+.1f} °C, "
                f"ΔCHT={physics.get('delta_cht_c', 0.0):+.1f} °C). "
                "Engine operating near nominal envelope — continue with monitoring."
            ),
            "source": "rule_engine",
        }

    return {
        "advisory":   "GO",
        "root_cause": (
            "Fallback Diagnostic: Engine operating within nominal thermodynamic "
            "envelope.  All residuals within normal scatter limits."
        ),
        "source": "rule_engine",
    }


# ===========================================================================
# SECTION 2 – Amazon Bedrock XAI
# ===========================================================================

def _build_prompt(telemetry: dict, physics: dict) -> str:
    """
    Construct the Claude 3 Haiku diagnostic prompt.

    Passes raw telemetry, thermal residuals, and four intermediate physics
    signals so the model can reason at the thermodynamic level.
    """
    rpm       = telemetry.get("rpm",       0.0)
    map_kpa   = telemetry.get("map_kpa",   telemetry.get("map_pa", 101.325) / 1000.0)
    oat_c     = telemetry.get("oat_c",    15.0)
    egt_c     = telemetry.get("egt_c",     physics.get("actual_egt_c", 0.0))
    cht_c     = telemetry.get("cht_c",     physics.get("actual_cht_c", 0.0))

    d_egt     = physics["delta_egt_c"]
    d_cht     = physics["delta_cht_c"]
    exp_egt   = physics["expected_egt_c"]
    exp_cht   = physics["expected_cht_c"]
    load      = physics["load_factor"]
    m_dot     = physics["mass_airflow_kg_s"]
    eta_v     = physics["volumetric_efficiency"]
    t_in_c    = physics["inlet_temp_k"] - 273.15

    return f"""You are an aerospace diagnostics AI specialising in turbocharged piston aero-engines.

Engine under analysis : Rotax 914 F/UL (115 hp, turbocharged flat-four)
Ambient conditions    : OAT = {oat_c:.1f} °C

── Operating point ────────────────────────────────────────────────────────
  RPM                     = {rpm:.0f} rev/min
  MAP                     = {map_kpa:.2f} kPa

── Sensor readings vs algebraic physics surrogate ─────────────────────────
  EGT  actual   = {egt_c:.1f} °C   expected = {exp_egt:.1f} °C   Δ = {d_egt:+.1f} °C
  CHT  actual   = {cht_c:.1f} °C   expected = {exp_cht:.1f} °C   Δ = {d_cht:+.1f} °C

── Thermodynamic state (surrogate intermediates) ───────────────────────────
  Engine load factor        = {load:.3f}   (1.0 = rated power, >1.2 = over-boost)
  Mass airflow              = {m_dot:.4f} kg/s
  Volumetric efficiency     = {eta_v:.3f}
  Turbocharged inlet temp   = {t_in_c:.1f} °C

── Diagnostic thresholds (Rotax 914 field guidance) ───────────────────────
  |ΔEGT| < 20 °C and |ΔCHT| < 15 °C  → normal scatter
  ΔEGT > +40 °C                       → lean mixture, wastegate fault, ignition retard
  ΔEGT < −40 °C                       → rich mixture, fuel enrichment fault
  ΔCHT > +30 °C                       → cooling degradation, oil starvation, CHT fault
  ΔCHT < −30 °C                       → excessive cooling, cowl flap fault
  ΔEGT > +40 °C AND ΔCHT > +30 °C     → detonation or turbocharger over-boost
  Load factor > 1.2                   → MAP sensor drift or wastegate stuck closed

Task: Return ONLY a valid JSON object with exactly these two keys:

{{
  "root_cause": "<1–2 sentence technical explanation of what the residuals and thermodynamic state indicate>",
  "advisory":   "<exactly one of: GO | GO WITH MONITORING | GO WITH DERATE | MAINTENANCE REQUIRED>"
}}

Do not include any text outside the JSON object."""


def _invoke_bedrock(prompt: str) -> dict:
    """
    Call Claude 3 Haiku via Bedrock Runtime.

    Returns a dict with keys ``root_cause``, ``advisory``, ``source``.
    Never raises — all exceptions are caught and re-raised as RuntimeError
    so the caller can route to the fallback.
    """
    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens":        300,
        "temperature":       0.0,   # deterministic — safety-critical advisory
        "messages": [{"role": "user", "content": prompt}],
    })

    response = _bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=request_body,
    )

    raw_body     = response["body"].read().decode("utf-8")
    resp_json    = json.loads(raw_body)
    text_content = resp_json["content"][0]["text"].strip()

    # Strip accidental markdown fences
    if text_content.startswith("```"):
        text_content = text_content.split("```")[1]
        if text_content.startswith("json"):
            text_content = text_content[4:]
        text_content = text_content.strip()

    advisory = json.loads(text_content)

    # Validate advisory state — default to safest value if model drifts
    valid_states = {"GO", "GO WITH MONITORING", "GO WITH DERATE", "MAINTENANCE REQUIRED"}
    if advisory.get("advisory") not in valid_states:
        logger.warning(
            "Bedrock returned unexpected advisory '%s' — clamping to MAINTENANCE REQUIRED",
            advisory.get("advisory"),
        )
        advisory["advisory"] = "MAINTENANCE REQUIRED"

    advisory["source"] = "bedrock"
    return advisory


def get_advisory(telemetry: dict, physics: dict) -> dict:
    """
    Attempt Bedrock XAI.  Fall back to local rule engine on ANY failure.

    Catches:
        botocore.ClientError   – IAM, quota, model unavailability
        TimeoutError           – Lambda 30 s wall clock approaching
        json.JSONDecodeError   – malformed model output
        Exception              – any other runtime error
    """
    prompt = _build_prompt(telemetry, physics)
    try:
        logger.info("Invoking Bedrock model: %s", BEDROCK_MODEL_ID)
        result = _invoke_bedrock(prompt)
        logger.info("Bedrock advisory: %s  source=%s", result["advisory"], result["source"])
        return result

    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        logger.warning("Bedrock ClientError [%s] — using rule-based fallback", code)

    except json.JSONDecodeError as exc:
        logger.warning("Bedrock JSON parse error: %s — using rule-based fallback", exc)

    except TimeoutError:
        logger.warning("Bedrock invocation timed out — using rule-based fallback")

    except Exception as exc:  # noqa: BLE001
        logger.warning("Bedrock unexpected error: %s — using rule-based fallback", exc)

    fallback = _rule_based_advisory(physics)
    logger.info("Rule-engine advisory: %s", fallback["advisory"])
    return fallback


# ===========================================================================
# SECTION 3 – DynamoDB Persistence
# ===========================================================================

def _persist_record(
    engine_id: str,
    timestamp: str,
    telemetry: dict,
    physics:   dict,
    advisory:  dict,
) -> None:
    """
    Write a comprehensive telemetry + physics + advisory record to TelemetryStore.

    All numeric values stored as strings to avoid DynamoDB Decimal serialisation
    issues with boto3 resource interface.
    """
    def s(v: Any) -> str:
        return str(round(float(v), 6)) if isinstance(v, (int, float)) else str(v)

    item = {
        # ── Primary key ───────────────────────────────────────────────────
        "engineId":  engine_id,
        "timestamp": timestamp,

        # ── Raw sensor telemetry ──────────────────────────────────────────
        "rpm":     s(telemetry.get("rpm",   0)),
        "map_kpa": s(telemetry.get("map_kpa", telemetry.get("map_pa", 101325) / 1000.0)),
        "oat_c":   s(telemetry.get("oat_c", 15.0)),
        "egt_c":   s(telemetry.get("egt_c", physics.get("actual_egt_c", 0))),
        "cht_c":   s(telemetry.get("cht_c", physics.get("actual_cht_c", 0))),
        "dt_s":    s(telemetry.get("dt_s",  0.05)),

        # ── Physics surrogate baselines ───────────────────────────────────
        "egt_expected":  s(physics["expected_egt_c"]),
        "cht_expected":  s(physics["expected_cht_c"]),
        "steady_egt_c":  s(physics["steady_egt_c"]),
        "steady_cht_c":  s(physics["steady_cht_c"]),

        # ── Residuals ─────────────────────────────────────────────────────
        "delta_egt_c": s(physics["delta_egt_c"]),
        "delta_cht_c": s(physics["delta_cht_c"]),

        # ── Intermediate physics parameters ───────────────────────────────
        "load_factor":           s(physics["load_factor"]),
        "mass_airflow_kg_s":     s(physics["mass_airflow_kg_s"]),
        "volumetric_efficiency": s(physics["volumetric_efficiency"]),
        "inlet_temp_k":          s(physics["inlet_temp_k"]),
        "map_pa":                s(physics["map_pa"]),

        # ── XAI advisory ──────────────────────────────────────────────────
        "advisory":          advisory.get("advisory",   "MAINTENANCE REQUIRED"),
        "root_cause":        advisory.get("root_cause", ""),
        "advisory_source":   advisory.get("source",     "unknown"),

        # ── Metadata ──────────────────────────────────────────────────────
        "record_id":   str(uuid.uuid4()),
        "model_id":    BEDROCK_MODEL_ID,
    }

    logger.info(
        "DynamoDB write: engineId=%s  advisory=%s  source=%s",
        engine_id, item["advisory"], item["advisory_source"],
    )
    _table.put_item(Item=item)


# ===========================================================================
# SECTION 4 – Lambda Handler (entry point)
# ===========================================================================

def lambda_handler(event: dict, context: Any) -> dict:
    """
    API Gateway Lambda Proxy integration.

    Accepted routes
    ───────────────
    OPTIONS /telemetry  →  CORS preflight (200)
    GET     /telemetry  →  health check   (200)
    POST    /telemetry  →  full pipeline  (200 / 400 / 500)

    POST payload schema
    ───────────────────
    Required : engine_id, rpm
    Optional : map_kpa | map_pa, oat_c, egt_c, cht_c, dt_s
               (physics_surrogate accepts all aliases gracefully)
    """
    http_method = event.get("httpMethod", "POST").upper()
    logger.info("Received %s request", http_method)

    # ── CORS preflight ──────────────────────────────────────────────────────
    if http_method == "OPTIONS":
        return _response(200, {"message": "CORS preflight OK"})

    # ── Health-check ────────────────────────────────────────────────────────
    if http_method == "GET":
        return _response(200, {
            "service":        "VajraTwin",
            "model":          "Rotax 914 F/UL",
            "physics_engine": "algebraic surrogate v2 (lumped thermal capacitance)",
            "bedrock_model":  BEDROCK_MODEL_ID,
            "fallback":       "rule_engine",
            "status":         "operational",
        })

    # ── Method guard ────────────────────────────────────────────────────────
    if http_method != "POST":
        return _response(405, {"error": f"Method '{http_method}' not allowed"})

    # ── Outer try — catches every unhandled failure ─────────────────────────
    try:

        # ── Step 1: Parse and validate ──────────────────────────────────────
        if not event.get("body"):
            return _response(400, {"error": "Request body is empty"})

        payload: dict = json.loads(event["body"])

        if "engine_id" not in payload:
            return _response(400, {"error": "Missing required field: engine_id"})
        if "rpm" not in payload:
            return _response(400, {"error": "Missing required field: rpm"})

        engine_id: str = str(payload["engine_id"])
        timestamp: str = datetime.now(timezone.utc).isoformat()

        # Normalise MAP: accept map_kpa or map_pa; default to sea-level
        if "map_kpa" in payload:
            payload["map_kpa"] = float(payload["map_kpa"])
        elif "map_pa" in payload:
            payload["map_kpa"] = float(payload["map_pa"]) / 1000.0
        else:
            payload["map_kpa"] = 101.325   # standard sea-level kPa

        # Soft range guards (logged only, not rejected — sensor faults are data)
        rpm = float(payload.get("rpm", 0))
        if not (3300 <= rpm <= 5800):
            logger.warning("RPM %.0f outside Rotax 914 range [3300, 5800]", rpm)
        if not (60 <= payload["map_kpa"] <= 140):
            logger.warning("MAP %.1f kPa outside expected range [60, 140]", payload["map_kpa"])

        # ── Step 2: Physics surrogate ───────────────────────────────────────
        # The surrogate accepts all key aliases (map_kpa, egt_c, cht_c, etc.)
        physics = physics_calculate_residuals(payload)

        logger.info(
            "Surrogate: EGT_exp=%.1f  CHT_exp=%.1f  "
            "ΔEGT=%+.1f  ΔCHT=%+.1f  load=%.3f  m_dot=%.4f",
            physics["expected_egt_c"], physics["expected_cht_c"],
            physics["delta_egt_c"],    physics["delta_cht_c"],
            physics["load_factor"],    physics["mass_airflow_kg_s"],
        )

        # ── Step 3: XAI advisory (Bedrock with rule-engine fallback) ────────
        advisory = get_advisory(payload, physics)

        # ── Step 4: DynamoDB persistence ────────────────────────────────────
        try:
            _persist_record(engine_id, timestamp, payload, physics, advisory)
        except ClientError as exc:
            # DynamoDB failure must NOT prevent the response from being returned
            logger.error(
                "DynamoDB write failed [%s]: %s — continuing",
                exc.response["Error"]["Code"],
                exc.response["Error"]["Message"],
            )

        # ── Step 5: Build success response ──────────────────────────────────
        body = {
            "engine_id": engine_id,
            "timestamp": timestamp,

            # Raw telemetry echo
            "telemetry": {
                "rpm":     float(payload.get("rpm",   0)),
                "map_kpa": float(payload["map_kpa"]),
                "oat_c":   float(payload.get("oat_c", 15.0)),
                "egt_c":   float(payload.get("egt_c", physics["actual_egt_c"])),
                "cht_c":   float(payload.get("cht_c", physics["actual_cht_c"])),
                "dt_s":    float(payload.get("dt_s",  0.05)),
            },

            # Physics surrogate outputs
            "physics_model": {
                "egt_expected":          round(physics["expected_egt_c"],        2),
                "cht_expected":          round(physics["expected_cht_c"],        2),
                "steady_egt_c":          round(physics["steady_egt_c"],          2),
                "steady_cht_c":          round(physics["steady_cht_c"],          2),
                "load_factor":           round(physics["load_factor"],           4),
                "mass_airflow_kg_s":     round(physics["mass_airflow_kg_s"],     5),
                "volumetric_efficiency": round(physics["volumetric_efficiency"], 4),
                "inlet_temp_c":          round(physics["inlet_temp_k"] - 273.15, 2),
            },

            # Residuals
            "residuals": {
                "delta_egt": round(physics["delta_egt_c"], 2),
                "delta_cht": round(physics["delta_cht_c"], 2),
            },

            # XAI advisory
            "xai_advisory": {
                "root_cause":      advisory["root_cause"],
                "advisory":        advisory["advisory"],
                "advisory_source": advisory["source"],   # "bedrock" | "rule_engine"
            },
        }

        logger.info(
            "Pipeline complete: engine=%s  advisory=%s  source=%s",
            engine_id, advisory["advisory"], advisory["source"],
        )
        return _response(200, body)

    # ── Top-level safety net ─────────────────────────────────────────────────
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s", exc)
        return _response(400, {"error": f"Invalid JSON body: {exc}"})

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled exception in lambda_handler")
        return _response(500, {
            "error":      str(exc),
            "error_type": type(exc).__name__,
        })
