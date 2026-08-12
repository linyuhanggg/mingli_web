from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"


def load_openapi_document() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document


def test_phase_one_paths_are_frozen() -> None:
    paths = load_openapi_document()["paths"]

    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths
    assert "/api/v1/guest-sessions" in paths
    assert "/api/v1/auth/otp/request" in paths
    assert "/api/v1/auth/otp/verify" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/account" in paths


def test_cookie_session_security_scheme_is_explicit() -> None:
    security_schemes = load_openapi_document()["components"]["securitySchemes"]

    assert security_schemes["deviceSession"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "mingli_session",
    }


def test_unauthorized_contract_documents_stale_device_cookie_recovery() -> None:
    unauthorized = load_openapi_document()["components"]["responses"]["Unauthorized"]

    assert "Device or Guest owner session" in unauthorized["description"]
    assert "expires stale device and CSRF cookies" in unauthorized["description"]
    assert "Set-Cookie" in unauthorized["headers"]


def test_contract_does_not_expose_future_payment_or_model_routes() -> None:
    paths = load_openapi_document()["paths"]

    assert not any("payment" in path for path in paths)
    assert not any("model" in path for path in paths)


PHASE_TWO_PATHS = {
    "/api/v1/profiles/drafts": "post",
    "/api/v1/profiles/drafts/{draft_id}/confirm": "post",
    "/api/v1/profiles": "get",
    "/api/v1/readings/preview": "post",
    "/api/v1/readings/today": "post",
    "/api/v1/readings/week": "post",
    "/api/v1/readings/liuyao": "post",
    "/api/v1/readings": "get",
    "/api/v1/readings/{reading_version_id}": "get",
    "/api/v1/readings/{reading_version_id}/input": "post",
    "/api/v1/readings/{reading_version_id}/result": "get",
    "/api/v1/readings/{reading_version_id}/verification": "post",
    "/api/v1/readings/{reading_version_id}/follow-up": "post",
}

CHART_PATHS = {
    "/api/v1/charts/bazi/sync": "syncBaziChart",
    "/api/v1/charts/bazi/sync/{chart_handle}/input": "supplyBaziChartInput",
}


def test_phase_two_paths_are_frozen() -> None:
    paths = load_openapi_document()["paths"]

    for path, method in PHASE_TWO_PATHS.items():
        assert path in paths
        assert method in paths[path]


def test_sync_chart_paths_and_public_response_are_frozen() -> None:
    document = load_openapi_document()
    paths = document["paths"]
    for path, operation_id in CHART_PATHS.items():
        operation = paths[path]["post"]
        assert operation["operationId"] == operation_id
        assert operation["tags"] == ["Charts"]
        parameter_refs = {item.get("$ref") for item in operation["parameters"]}
        assert "#/components/parameters/CsrfToken" in parameter_refs
        assert "#/components/parameters/RequiredIdempotencyKey" in parameter_refs
        response_schema = operation["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/BaziChartSyncResponse"}
        assert "422" not in operation["responses"]

    schemas = document["components"]["schemas"]
    assert schemas["BaziChartSyncResponse"]["oneOf"] == [
        {"$ref": "#/components/schemas/BaziChartReadyResponse"},
        {"$ref": "#/components/schemas/BaziChartNeedInputResponse"},
    ]
    assert schemas["ReadingFact"]["properties"]["value"] == {}


def test_phase_two_contracts_never_expose_runtime_or_birth_secrets() -> None:
    schemas = load_openapi_document()["components"]["schemas"]
    serialized = yaml.safe_dump(schemas).lower()

    for banned in (
        "state_token",
        "candidate",
        "prompt",
        "ciphertext",
        "nonce",
        "fingerprint",
    ):
        assert banned not in serialized, f"schema exposes forbidden runtime token {banned!r}"

    response_schema_names = {
        "ProfileDraftResponse",
        "ProfileSummary",
        "ProfileListResponse",
        "ReadingVersionSummary",
        "ReadingStartResponse",
        "ReadingListResponse",
        "ReadingResultResponse",
        "ReadingFactPanel",
        "ReadingFact",
        "ReadingEvidence",
        "ReadingFinding",
        "ReadingClaimScope",
        "ReadingLimit",
        "ReadingRequestView",
        "ReadingVerificationSummary",
        "VerificationResponse",
    }
    response_schemas = {
        name: schemas[name] for name in response_schema_names if name in schemas
    }
    response_text = yaml.safe_dump(response_schemas).lower()
    for banned in (
        "birth_datetime",
        "four_pillars",
        "timezone",
        "location",
        "gender",
        "longitude",
        "latitude",
        "coordinate_source",
    ):
        assert banned not in response_text, f"response exposes decrypted birth data {banned!r}"


def test_phase_two_mutating_routes_declare_csrf_and_idempotency() -> None:
    paths = load_openapi_document()["paths"]
    csrf_mutating_paths = {
        "/api/v1/profiles/drafts": "post",
        "/api/v1/profiles/drafts/{draft_id}/confirm": "post",
        "/api/v1/readings/preview": "post",
        "/api/v1/readings/today": "post",
        "/api/v1/readings/week": "post",
        "/api/v1/readings/liuyao": "post",
        "/api/v1/readings/{reading_version_id}/input": "post",
        "/api/v1/readings/{reading_version_id}/verification": "post",
        "/api/v1/readings/{reading_version_id}/follow-up": "post",
    }
    for path, method in csrf_mutating_paths.items():
        parameters = paths[path][method].get("parameters", [])
        parameter_names = {item.get("$ref") for item in parameters}
        assert "#/components/parameters/CsrfToken" in parameter_names

    idempotent_paths = {
        "/api/v1/readings/preview": "post",
        "/api/v1/readings/today": "post",
        "/api/v1/readings/week": "post",
        "/api/v1/readings/liuyao": "post",
        "/api/v1/readings/{reading_version_id}/follow-up": "post",
    }
    for path, method in idempotent_paths.items():
        parameters = paths[path][method].get("parameters", [])
        parameter_names = {item.get("$ref") for item in parameters}
        assert "#/components/parameters/IdempotencyKey" in parameter_names


def test_readings_list_contract_is_frozen_with_summary_items() -> None:
    document = load_openapi_document()
    operation = document["paths"]["/api/v1/readings"]["get"]

    assert operation["operationId"] == "listReadings"
    assert operation["tags"] == ["Readings"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema == {"$ref": "#/components/schemas/ReadingListResponse"}

    list_schema = document["components"]["schemas"]["ReadingListResponse"]
    assert list_schema["type"] == "object"
    assert list_schema["additionalProperties"] is False
    assert list_schema["required"] == ["readings"]
    assert list_schema["properties"]["readings"]["items"] == {
        "$ref": "#/components/schemas/ReadingVersionSummary"
    }
