"""
smoke_test.py
=============
Full Lambda pipeline smoke test — no AWS credentials needed.
Mocks boto3.client (Bedrock) and boto3.resource (DynamoDB).
Run from repo root:  python scripts/smoke_test.py
"""

import json
import os
import sys
import unittest.mock as mock

# Add Lambda package to path
LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "lambda", "vajra_engine")
sys.path.insert(0, LAMBDA_DIR)

os.environ["TELEMETRY_TABLE"]  = "TelemetryStore-dev"
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-3-haiku-20240307-v1:0"

# ── Bedrock mock response ──────────────────────────────────────────────────
BEDROCK_PAYLOAD = json.dumps({
    "content": [{"type": "text", "text": json.dumps({
        "root_cause": "Elevated EGT residual consistent with lean mixture at high MAP.",
        "advisory":   "GO WITH MONITORING"
    })}]
})

mock_bedrock_resp = {"body": mock.MagicMock(read=lambda: BEDROCK_PAYLOAD.encode())}
mock_table        = mock.MagicMock()

GOOD_EVENT = {
    "httpMethod": "POST",
    "body": json.dumps({
        "engine_id":  "rotax-914-001",
        "rpm":         5500.0,
        "map_hpa":     120.0,
        "oat_c":       15.0,
        "egt_actual":  820.0,
        "cht_actual":  195.0,
        "dt_s":        0.05,
    }),
}

passes = 0
failures = 0

def check(label, condition, detail=""):
    global passes, failures
    if condition:
        print(f"  PASS  {label}")
        passes += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        failures += 1


# ── Import handler with mocked AWS ────────────────────────────────────────
with mock.patch("boto3.client") as mock_client_cls, \
     mock.patch("boto3.resource") as mock_res_cls:

    mock_client_cls.return_value.invoke_model.return_value = mock_bedrock_resp
    mock_res_cls.return_value.Table.return_value = mock_table

    import importlib
    import handler
    importlib.reload(handler)

    print("\n── Test 1: OPTIONS preflight ────────────────────────────────────")
    r = handler.lambda_handler({"httpMethod": "OPTIONS"}, None)
    check("Status 200",            r["statusCode"] == 200)
    check("CORS header present",   r["headers"]["Access-Control-Allow-Origin"] == "*")

    print("\n── Test 2: GET health check ─────────────────────────────────────")
    r = handler.lambda_handler({"httpMethod": "GET"}, None)
    check("Status 200",            r["statusCode"] == 200)
    b = json.loads(r["body"])
    check("Service field present", "service" in b)

    print("\n── Test 3: POST nominal telemetry ───────────────────────────────")
    r = handler.lambda_handler(GOOD_EVENT, None)
    b = json.loads(r["body"])
    check("Status 200",                  r["statusCode"] == 200)
    check("CORS on success",             r["headers"]["Access-Control-Allow-Origin"] == "*")
    check("residuals block present",     "residuals"     in b)
    check("physics_model block present", "physics_model" in b)
    check("xai_advisory block present",  "xai_advisory"  in b)
    check("Advisory value correct",      b["xai_advisory"]["advisory"] == "GO WITH MONITORING")
    check("DynamoDB put_item called",    mock_table.put_item.called)

    delta_egt = b["residuals"]["delta_egt"]
    delta_cht = b["residuals"]["delta_cht"]
    load      = b["physics_model"]["load_factor"]
    m_dot     = b["physics_model"]["mass_airflow_kg_s"]
    egt_exp   = b["physics_model"]["egt_expected"]
    print(f"         delta_egt        = {delta_egt}")
    print(f"         delta_cht        = {delta_cht}")
    print(f"         egt_expected     = {egt_exp}")
    print(f"         load_factor      = {load}")
    print(f"         mass_airflow_kg_s= {m_dot}")
    print(f"         advisory         = {b['xai_advisory']['advisory']}")
    print(f"         root_cause       = {b['xai_advisory']['root_cause'][:70]}...")
    print(f"         advisory_source  = {b['xai_advisory'].get('advisory_source','bedrock')}")

    print("\n── Test 4: Bedrock fallback on ClientError ───────────────────────")
    from botocore.exceptions import ClientError
    mock_client_cls.return_value.invoke_model.side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeModel",
    )
    importlib.reload(handler)
    r = handler.lambda_handler(GOOD_EVENT, None)
    b = json.loads(r["body"])
    check("Status 200 on Bedrock failure",   r["statusCode"] == 200)
    check("CORS on fallback response",       r["headers"]["Access-Control-Allow-Origin"] == "*")
    check("Fallback source = rule_engine",   b["xai_advisory"].get("advisory_source") == "rule_engine")
    check("Fallback advisory is valid",      b["xai_advisory"]["advisory"] in {
        "GO", "GO WITH MONITORING", "GO WITH DERATE", "MAINTENANCE REQUIRED"
    })
    print(f"         advisory         = {b['xai_advisory']['advisory']}")
    print(f"         advisory_source  = {b['xai_advisory']['advisory_source']}")

    print("\n── Test 5: 400 on missing fields ────────────────────────────────")
    mock_client_cls.return_value.invoke_model.side_effect = None
    importlib.reload(handler)
    r = handler.lambda_handler({"httpMethod": "POST", "body": '{"engine_id":"x"}'}, None)
    check("Status 400",            r["statusCode"] == 400)
    check("CORS on 400",           r["headers"]["Access-Control-Allow-Origin"] == "*")

    print("\n── Test 6: 400 on empty body ────────────────────────────────────")
    r = handler.lambda_handler({"httpMethod": "POST", "body": ""}, None)
    check("Status 400",            r["statusCode"] == 400)
    check("CORS on empty body",    r["headers"]["Access-Control-Allow-Origin"] == "*")

    print("\n── Test 7: 405 on unsupported method ────────────────────────────")
    r = handler.lambda_handler({"httpMethod": "DELETE"}, None)
    check("Status 405",            r["statusCode"] == 405)
    check("CORS on 405",           r["headers"]["Access-Control-Allow-Origin"] == "*")

# ── Summary ────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  Results: {passes} passed, {failures} failed")
print(f"{'='*50}\n")
sys.exit(0 if failures == 0 else 1)
