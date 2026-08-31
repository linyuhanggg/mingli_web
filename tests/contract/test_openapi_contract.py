import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"
MINGLI_RESULT_SCHEMA_PATH = ROOT / "contracts" / "schemas" / "mingli-result-v2.schema.json"


def load_openapi_document() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document


def load_mingli_result_schema() -> dict[str, Any]:
    with MINGLI_RESULT_SCHEMA_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = json.load(stream)
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
    "/api/v1/profiles/drafts/{draft_id}": "delete",
    "/api/v1/profiles/drafts/{draft_id}/confirm": "post",
    "/api/v1/profiles": "get",
    "/api/v1/readings/preview": "post",
    "/api/v1/readings/chart-similarity": "post",
    "/api/v1/readings/canwen": "post",
    "/api/v1/readings/hecan": "post",
    "/api/v1/readings/today": "post",
    "/api/v1/readings/week": "post",
    "/api/v1/readings/liuyao": "post",
    "/api/v1/readings/wenshi": "post",
    "/api/v1/readings": "get",
    "/api/v1/readings/{reading_version_id}": "get",
    "/api/v1/readings/{reading_version_id}/fulfillment": "post",
    "/api/v1/readings/{reading_version_id}/input": "post",
    "/api/v1/readings/{reading_version_id}/result": "get",
    "/api/v1/readings/{reading_version_id}/verification": "post",
    "/api/v1/readings/{reading_version_id}/follow-up": "post",
    "/api/v1/readings/{reading_version_id}/recast": "post",
}


def test_phase_two_paths_are_frozen() -> None:
    paths = load_openapi_document()["paths"]

    for path, method in PHASE_TWO_PATHS.items():
        assert path in paths
        assert method in paths[path]


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


def test_profile_display_contract_is_owner_only_minimized_and_rename_only() -> None:
    document = load_openapi_document()
    paths = document["paths"]
    schemas = document["components"]["schemas"]

    summary = schemas["ProfileSummary"]
    assert {"display_name", "birth_date"} <= set(summary["required"])
    assert summary["properties"]["display_name"] == {
        "type": ["string", "null"],
        "minLength": 1,
        "maxLength": 80,
    }
    assert summary["properties"]["birth_date"]["type"] == ["string", "null"]
    assert summary["properties"]["birth_date"]["format"] == "date"

    rename = paths["/api/v1/profiles/{profile_id}"]["patch"]
    assert rename["operationId"] == "updateProfileDisplayName"
    assert {item.get("$ref") for item in rename["parameters"] if "$ref" in item} == {
        "#/components/parameters/CsrfToken"
    }
    assert rename["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ProfileDisplayNameUpdateRequest"
    }
    rename_request = schemas["ProfileDisplayNameUpdateRequest"]
    assert rename_request["additionalProperties"] is False
    assert rename_request["required"] == ["display_name"]
    assert set(rename_request["properties"]) == {"display_name"}
    assert schemas["ProfileDraftRequest"]["properties"]["label"]["pattern"] == (
        rename_request["properties"]["display_name"]["pattern"]
    )
    assert rename["responses"]["409"] == {
        "$ref": "#/components/responses/Conflict"
    }

    list_description = paths["/api/v1/profiles"]["get"]["responses"]["200"][
        "description"
    ].lower()
    detail_description = paths["/api/v1/profiles/{profile_id}/versions"]["get"][
        "responses"
    ]["200"]["description"].lower()
    for description in (list_description, detail_description):
        assert "owner-only" in description
        assert "private/no-store" in description


def test_profile_draft_delete_is_owner_scoped_without_relaxing_profile_delete() -> None:
    paths = load_openapi_document()["paths"]
    delete_draft = paths["/api/v1/profiles/drafts/{draft_id}"]["delete"]

    assert delete_draft["operationId"] == "deleteProfileDraft"
    assert {item.get("$ref") for item in delete_draft["parameters"] if "$ref" in item} == {
        "#/components/parameters/CsrfToken"
    }
    assert delete_draft["parameters"][1] == {
        "name": "draft_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "format": "uuid"},
    }
    assert set(delete_draft["responses"]) == {"204", "401", "403", "404", "429"}
    assert "security" not in delete_draft
    assert paths["/api/v1/profiles/{profile_id}"]["delete"]["security"] == [
        {"deviceSession": []}
    ]


def test_reading_result_contract_exposes_the_runtime_view_model_slot() -> None:
    schema = load_openapi_document()["components"]["schemas"]["ReadingResultResponse"]

    assert "view_model" in schema["required"]
    assert schema["properties"]["view_model"]["oneOf"][0]["type"] == "object"
    assert "document" in schema["required"]
    assert schema["properties"]["document"]["oneOf"][0]["$ref"] == (
        "#/components/schemas/ReadingDocumentV1"
    )


def test_reading_fact_text_and_free_year_set_are_server_projected() -> None:
    schemas = load_openapi_document()["components"]["schemas"]
    display_text = schemas["ReadingFact"]["properties"]["display_text"]
    free_year_set = schemas["TimeLayerEntitlementResponse"]["properties"][
        "free_year_set"
    ]
    target_year = schemas["PreviewStartRequest"]["properties"]["target_year"]

    assert display_text["minLength"] == 1
    assert "never raw JSON" in display_text["description"]
    assert "clients must not assume a fixed count" in free_year_set["description"]
    assert "server selects the free civil year" in target_year["description"]


def test_verified_exact_evidence_fields_are_atomic_and_multi_citation() -> None:
    schemas = load_openapi_document()["components"]["schemas"]
    evidence = schemas["ReadingEvidence"]
    citation = schemas["VerifiedExactCitation"]

    assert evidence["additionalProperties"] is False
    assert set(evidence["required"]) >= {
        "ref",
        "source_title",
        "locator",
        "excerpt",
        "supports_fact_refs",
    }
    assert evidence["properties"]["locator"]["type"] == ["string", "null"]
    assert evidence["properties"]["excerpt"]["type"] == ["string", "null"]
    assert citation["additionalProperties"] is False
    assert citation["properties"]["verification_status"]["const"] == (
        "verified_exact"
    )
    assert evidence["properties"]["verbatim_citations"]["minItems"] == 1
    assert evidence["properties"]["verbatim_citations"]["items"]["$ref"] == (
        "#/components/schemas/VerifiedExactCitation"
    )

    exact_fields = {
        "evidence_ref",
        "rule_id",
        "verification_status",
        "verbatim_excerpt",
        "verbatim_citations",
    }
    dependencies = evidence["dependentRequired"]
    assert set(dependencies) == exact_fields
    for field in exact_fields:
        assert set(dependencies[field]) == exact_fields - {field}


def test_openapi_reading_evidence_matches_authoritative_result_schema() -> None:
    openapi_evidence = load_openapi_document()["components"]["schemas"][
        "ReadingEvidence"
    ]
    authoritative_evidence = load_mingli_result_schema()["$defs"]["publicEvidence"]

    assert openapi_evidence["required"] == authoritative_evidence["required"]
    assert authoritative_evidence["properties"]["locator"]["$ref"] == (
        "#/$defs/nullableText"
    )
    assert authoritative_evidence["properties"]["excerpt"]["$ref"] == (
        "#/$defs/nullableText"
    )
    assert openapi_evidence["properties"]["locator"]["type"] == [
        "string",
        "null",
    ]
    assert openapi_evidence["properties"]["excerpt"]["type"] == [
        "string",
        "null",
    ]


def test_phase_two_mutating_routes_declare_csrf_and_idempotency() -> None:
    paths = load_openapi_document()["paths"]
    csrf_mutating_paths = {
        "/api/v1/profiles/drafts": "post",
        "/api/v1/profiles/drafts/{draft_id}": "delete",
        "/api/v1/profiles/drafts/{draft_id}/confirm": "post",
        "/api/v1/profiles/{profile_id}": "patch",
        "/api/v1/readings/preview": "post",
        "/api/v1/readings/chart-similarity": "post",
        "/api/v1/readings/canwen": "post",
        "/api/v1/readings/hecan": "post",
        "/api/v1/readings/today": "post",
        "/api/v1/readings/week": "post",
        "/api/v1/readings/liuyao": "post",
        "/api/v1/readings/wenshi": "post",
        "/api/v1/readings/{reading_version_id}/fulfillment": "post",
        "/api/v1/readings/{reading_version_id}/input": "post",
        "/api/v1/readings/{reading_version_id}/verification": "post",
        "/api/v1/readings/{reading_version_id}/follow-up": "post",
        "/api/v1/readings/{reading_version_id}/recast": "post",
    }
    for path, method in csrf_mutating_paths.items():
        parameters = paths[path][method].get("parameters", [])
        parameter_names = {item.get("$ref") for item in parameters}
        assert "#/components/parameters/CsrfToken" in parameter_names

    idempotent_paths = {
        "/api/v1/readings/preview": "post",
        "/api/v1/readings/chart-similarity": "post",
        "/api/v1/readings/canwen": "post",
        "/api/v1/readings/hecan": "post",
        "/api/v1/readings/today": "post",
        "/api/v1/readings/week": "post",
        "/api/v1/readings/liuyao": "post",
        "/api/v1/readings/wenshi": "post",
        "/api/v1/readings/{reading_version_id}/follow-up": "post",
        "/api/v1/readings/{reading_version_id}/recast": "post",
    }
    for path, method in idempotent_paths.items():
        parameters = paths[path][method].get("parameters", [])
        parameter_names = {item.get("$ref") for item in parameters}
        assert "#/components/parameters/IdempotencyKey" in parameter_names


def test_base_chart_starts_publish_the_deterministic_fast_path_contract() -> None:
    document = load_openapi_document()
    schemas = document["components"]["schemas"]
    start_properties = schemas["ReadingStartResponse"]["properties"]
    timing = schemas["ChartFastPathTiming"]

    assert {
        "view_model",
        "fast_path_timing",
        "result_available",
        "poll_required",
        "poll_after_seconds",
    }.issubset(start_properties)
    assert timing["properties"]["execution_lane"]["const"] == "direct_runtime"
    assert set(timing["required"]) == {
        "queue_wait_ms",
        "worker_pickup_ms",
        "runtime_one_shot_ms",
        "db_persistence_ms",
        "total_ms",
    }
    summary_properties = schemas["ReadingVersionSummary"]["properties"]
    assert {
        "result_available",
        "poll_required",
        "poll_after_seconds",
    }.issubset(summary_properties)
    assert summary_properties["poll_after_seconds"]["minimum"] == 0

    for path in (
        "/api/v1/readings/preview",
        "/api/v1/readings/ziwei",
        "/api/v1/readings/liuyao",
        "/api/v1/readings/meihua",
        "/api/v1/readings/daliuren",
    ):
        operation = document["paths"][path]["post"]
        assert "synchronously" in operation["summary"]
        assert "queued" not in operation["responses"]["201"]["description"]


def test_fulfillment_contract_requires_payment_and_owner_scoped_idempotency() -> None:
    document = load_openapi_document()
    operation = document["paths"][
        "/api/v1/readings/{reading_version_id}/fulfillment"
    ]["post"]

    assert operation["operationId"] == "bindReadingFulfillment"
    parameters = operation["parameters"]
    assert {
        item.get("$ref")
        for item in parameters
        if "$ref" in item
    } == {"#/components/parameters/CsrfToken"}
    idempotency = next(
        item for item in parameters if item.get("name") == "Idempotency-Key"
    )
    assert idempotency["in"] == "header"
    assert idempotency["required"] is True
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FulfillmentBindingRequest"
    }
    response = document["components"]["schemas"]["FulfillmentBindingResponse"]
    assert response["required"] == [
        "fulfillment_id",
        "reading_version_id",
        "reading_job_id",
        "status",
        "created",
    ]


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


def test_account_history_contract_is_private_and_grouped_by_root() -> None:
    document = load_openapi_document()
    operation = document["paths"]["/api/v1/account/history"]["get"]

    assert operation["operationId"] == "listAccountHistory"
    assert operation["security"] == [{"deviceSession": []}]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema == {"$ref": "#/components/schemas/AccountHistoryResponse"}

    schemas = document["components"]["schemas"]
    root_schema = schemas["AccountHistoryRootResponse"]
    assert root_schema["properties"]["versions"]["items"] == {
        "$ref": "#/components/schemas/AccountHistoryVersionSummary"
    }
    version_schema = schemas["AccountHistoryVersionSummary"]
    assert "prior_answer" not in version_schema["properties"]
    assert "input_request" not in version_schema["properties"]


def test_public_referral_contract_has_guest_capture_and_safe_projection() -> None:
    document = load_openapi_document()
    paths = document["paths"]

    invite = paths["/api/v1/referrals/{code}"]["get"]
    assert invite["operationId"] == "getReferralInvite"
    assert invite["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReferralPublicResponse"
    }

    attribution = paths["/api/v1/referrals/{code}/attribution"]
    assert attribution["post"]["operationId"] == "recordReferralAttribution"
    assert attribution["delete"]["operationId"] == "clearReferralAttribution"
    assert {
        item.get("$ref")
        for item in attribution["post"]["parameters"]
        if "$ref" in item
    } == {"#/components/parameters/CsrfToken"}

    schema = document["components"]["schemas"]["ReferralPublicResponse"]
    assert schema["additionalProperties"] is False
    assert "inviter_user_id" not in schema["properties"]
    assert "visitor_key_hash" not in schema["properties"]


def test_public_bazi_checkout_contract_is_owner_scoped_and_confirmed_only() -> None:
    document = load_openapi_document()
    paths = document["paths"]
    create = paths["/api/v1/commerce/checkout"]["post"]
    status = paths["/api/v1/commerce/checkout/{order_id}"]["get"]

    assert create["operationId"] == "createBaziDeepCheckout"
    assert create["security"] == [{"deviceSession": []}]
    assert {
        item.get("$ref")
        for item in create["parameters"]
        if "$ref" in item
    } == {
        "#/components/parameters/CsrfToken",
        "#/components/parameters/IdempotencyKey",
    }
    assert status["operationId"] == "getBaziDeepCheckout"
    assert status["security"] == [{"deviceSession": []}]

    schemas = document["components"]["schemas"]
    request = schemas["PublicBaziCheckoutRequest"]
    response = schemas["PublicCheckoutResponse"]
    order = schemas["PublicCheckoutOrder"]
    assert request["additionalProperties"] is False
    assert request["required"] == ["reading_version_id"]
    assert set(request["properties"]) == {"reading_version_id"}
    assert response["additionalProperties"] is False
    assert "payment_id" not in response["required"]
    assert "owner_user_id" not in order["properties"]
    assert "purchase_target_ref" not in order["properties"]
