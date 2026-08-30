import importlib
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin
from uuid import uuid4

import yaml
from app.readings.api_schemas import (
    CapabilityProjection,
    ReadingResultResponse,
    TimeLayerCapabilityItemResponse,
    TimeLayerEntitlementCapabilityResponse,
    TimeLayerEntitlementLayerResponse,
    TimeLayerEntitlementResponse,
)
from app.readings.runtime_contracts import (
    FREE_BOUNDARY_LAYER_ID,
    PAID_TIME_LAYER_IDS,
    TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION,
    TimeLayerEntitlementV1,
)
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
USER_OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"
ADMIN_OPENAPI_PATH = ROOT / "contracts" / "openapi" / "admin-v1.yaml"


def load_paths(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document["paths"]


def load_frozen_paths() -> dict[str, Any]:
    """Union of public user contract and admin contract."""
    paths = dict(load_paths(USER_OPENAPI_PATH))
    admin_paths = load_paths(ADMIN_OPENAPI_PATH)
    overlap = set(paths) & set(admin_paths)
    assert not overlap, f"admin paths collide with user contract: {sorted(overlap)}"
    paths.update(admin_paths)
    return paths


def test_fastapi_operations_match_the_frozen_contract() -> None:
    main = importlib.import_module("app.main")
    frozen_paths = load_frozen_paths()
    runtime_paths = main.create_app().openapi()["paths"]

    assert set(runtime_paths) == set(frozen_paths)
    for path, frozen_path in frozen_paths.items():
        for method, frozen_operation in frozen_path.items():
            assert runtime_paths[path][method]["operationId"] == frozen_operation["operationId"]


def test_liuyao_deep_contract_freezes_the_candidate_evidence_entrypoint() -> None:
    frozen = load_paths(USER_OPENAPI_PATH)
    operation = frozen["/api/v1/readings/liuyao-deep"]["post"]

    assert operation["operationId"] == "startLiuyaoDeepReading"
    assert (
        operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LiuyaoDeepStartRequest"
    )
    with USER_OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    liuyao = document["components"]["schemas"]["LiuyaoStartRequest"]
    assert "state" in liuyao["properties"]["dimension_ids"]["items"]["enum"]
    assert document["components"]["schemas"]["LiuyaoDeepStartRequest"]["allOf"] == [
        {"$ref": "#/components/schemas/LiuyaoStartRequest"}
    ]


def test_admin_contract_paths_are_namespaced() -> None:
    admin_paths = load_paths(ADMIN_OPENAPI_PATH)
    assert admin_paths
    assert all(path.startswith("/api/v1/admin/") for path in admin_paths)


def _runtime_spec() -> dict[str, Any]:
    main = importlib.import_module("app.main")
    return main.create_app().openapi()


def _frozen_schemas() -> dict[str, Any]:
    with USER_OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document["components"]["schemas"]


def _is_nullable(schema: dict[str, Any]) -> bool:
    if isinstance(schema.get("type"), list):
        return "null" in schema["type"]
    if "anyOf" in schema:
        return any(item.get("type") == "null" for item in schema["anyOf"])
    if "oneOf" in schema:
        return any(item.get("type") == "null" for item in schema["oneOf"])
    return False


def test_neither_contract_declares_a_422_response() -> None:
    frozen_paths = load_frozen_paths()
    runtime_paths = _runtime_spec()["paths"]

    for paths in (frozen_paths, runtime_paths):
        for path in paths.values():
            for operation in path.values():
                assert "422" not in operation.get("responses", {})


def test_verification_request_contract_is_four_value_and_aligned() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["VerificationRequest"]
    runtime = runtime_schemas["VerificationRequest"]

    assert set(frozen["required"]) == set(runtime["required"]) == {"outcome"}
    assert set(frozen["properties"]["outcome"]["enum"]) == set(
        runtime["properties"]["outcome"]["enum"]
    ) == {"accepted", "partial", "disagreed", "unknown"}
    assert _is_nullable(frozen["properties"]["note"])
    assert _is_nullable(runtime["properties"]["note"])
    assert frozen["properties"]["note"]["maxLength"] == 500
    assert runtime["properties"]["note"]["anyOf"][0]["maxLength"] == 500


def test_profile_summary_display_name_constraints_are_aligned() -> None:
    frozen = _frozen_schemas()["ProfileSummary"]
    runtime = _runtime_spec()["components"]["schemas"]["ProfileSummary"]

    assert set(frozen["required"]) == set(runtime["required"])
    frozen_display_name = frozen["properties"]["display_name"]
    runtime_display_name = runtime["properties"]["display_name"]
    assert _is_nullable(frozen_display_name)
    assert _is_nullable(runtime_display_name)
    assert frozen_display_name["minLength"] == 1
    assert frozen_display_name["maxLength"] == 80
    runtime_string = next(
        item
        for item in runtime_display_name["anyOf"]
        if item.get("type") == "string"
    )
    assert runtime_string == {
        "type": "string",
        "minLength": 1,
        "maxLength": 80,
    }


def test_profile_latest_reading_and_atomic_preview_contracts_are_aligned() -> None:
    frozen_paths = load_paths(USER_OPENAPI_PATH)
    runtime = _runtime_spec()
    runtime_paths = runtime["paths"]
    latest_path = "/api/v1/profiles/{profile_id}/readings/latest"
    atomic_path = "/api/v1/profiles/drafts/{draft_id}/readings/preview"

    assert (
        frozen_paths[latest_path]["get"]["operationId"]
        == (runtime_paths[latest_path]["get"]["operationId"])
        == "getLatestProfileReading"
    )
    assert (
        frozen_paths[atomic_path]["post"]["operationId"]
        == (runtime_paths[atomic_path]["post"]["operationId"])
        == "confirmProfileDraftAndStartPreviewReading"
    )
    latest_parameter = next(
        item
        for item in frozen_paths[latest_path]["get"]["parameters"]
        if item["name"] == "product_id"
    )
    assert latest_parameter["required"] is True

    frozen_schemas = _frozen_schemas()
    runtime_schemas = runtime["components"]["schemas"]
    for name, required in {
        "ConfirmProfileDraftAndStartPreviewRequest": {"profile", "reading"},
        "LatestProfileReadingResponse": {
            "profile_id",
            "profile_version_id",
            "reading_root_id",
            "reading_version_id",
            "capability_id",
            "product_id",
            "status",
            "result_available",
            "created_at",
        },
    }.items():
        assert set(frozen_schemas[name]["required"]) == required
        assert set(runtime_schemas[name]["required"]) == required

    combined_dimensions = frozen_schemas["ProfileReadingPreviewOptions"]["properties"][
        "dimension_ids"
    ]
    runtime_combined_dimensions = runtime_schemas["ProfileReadingPreviewOptions"][
        "properties"
    ]["dimension_ids"]
    preview_dimensions = frozen_schemas["PreviewStartRequest"]["properties"][
        "dimension_ids"
    ]
    assert combined_dimensions["uniqueItems"] is True
    assert combined_dimensions["items"]["enum"] == ["overview", "career"]
    assert runtime_combined_dimensions["uniqueItems"] is True
    runtime_combined_array = next(
        item
        for item in runtime_combined_dimensions["anyOf"]
        if item.get("type") == "array"
    )
    assert runtime_combined_array["items"]["enum"] == ["overview", "career"]
    assert runtime_combined_dimensions["uniqueItems"] == combined_dimensions["uniqueItems"]
    assert runtime_combined_array["items"]["enum"] == combined_dimensions["items"][
        "enum"
    ]
    runtime_dimensions_validator = Draft202012Validator(runtime_combined_dimensions)
    assert not list(
        runtime_dimensions_validator.iter_errors(["overview", "career"])
    )
    assert list(runtime_dimensions_validator.iter_errors(["health"]))
    assert list(
        runtime_dimensions_validator.iter_errors(["overview", "overview"])
    )
    assert combined_dimensions["uniqueItems"] == preview_dimensions["uniqueItems"]
    assert combined_dimensions["items"]["enum"] == preview_dimensions["items"]["enum"]
    combined_validator = _openapi_component_validator("ProfileReadingPreviewOptions")
    assert not list(
        combined_validator.iter_errors({"dimension_ids": ["overview", "career"]})
    )
    assert list(combined_validator.iter_errors({"dimension_ids": ["health"]}))
    assert list(
        combined_validator.iter_errors({"dimension_ids": ["overview", "overview"]})
    )


def test_preview_time_target_constraints_are_aligned_and_enforced() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    valid_targets = [
        {},
        {"target_year": 1800},
        {"target_year": 2199},
        {"target_month": "1800-01"},
        {"target_month": "2199-12"},
        {"target_date": "2026-08-15"},
        {"target_year": None, "target_month": None, "target_date": None},
    ]
    invalid_targets = [
        {"target_year": 2026, "target_month": "2026-08"},
        {"target_year": 2026, "target_date": "2026-08-15"},
        {"target_month": "2026-08", "target_date": "2026-08-15"},
        {
            "target_year": 2026,
            "target_month": "2026-08",
            "target_date": "2026-08-15",
        },
        {"target_month": "1799-12"},
        {"target_month": "2200-01"},
    ]

    for name in ("ProfileReadingPreviewOptions", "PreviewStartRequest"):
        frozen = frozen_schemas[name]
        runtime = runtime_schemas[name]
        assert frozen["not"] == runtime["not"]
        assert (
            frozen["properties"]["target_month"]["pattern"]
            == next(
                item
                for item in runtime["properties"]["target_month"]["anyOf"]
                if item.get("type") == "string"
            )["pattern"]
        )

        base = {"profile_version_id": str(uuid4())} if name == "PreviewStartRequest" else {}
        for schema in (frozen, runtime):
            validator = Draft202012Validator(schema)
            for target in valid_targets:
                assert not list(validator.iter_errors({**base, **target})), (name, target)
            for target in invalid_targets:
                assert list(validator.iter_errors({**base, **target})), (name, target)


def test_verification_summary_contract_is_four_value_and_aligned() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["ReadingVerificationSummary"]
    runtime = runtime_schemas["ReadingVerificationSummary"]

    assert set(frozen["required"]) == set(runtime["required"]) == {
        "verification_id",
        "reading_version_id",
        "outcome",
        "note",
        "created_at",
    }
    assert set(frozen["properties"]["outcome"]["enum"]) == set(
        runtime["properties"]["outcome"]["enum"]
    )
    assert _is_nullable(frozen["properties"]["note"])


def test_reading_result_response_keeps_required_runtime_and_document_slots() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["ReadingResultResponse"]
    runtime = runtime_schemas["ReadingResultResponse"]

    assert {"view_model", "document"} <= set(frozen["required"])
    assert {"view_model", "document"} <= set(runtime["required"])
    assert runtime["properties"]["document"]["anyOf"][0]["$ref"] == (
        "#/components/schemas/ReadingDocumentV1"
    )


def _nullable_ref(schema: dict[str, Any]) -> str:
    variants = schema.get("oneOf") or schema.get("anyOf") or []
    refs = [item["$ref"] for item in variants if "$ref" in item]
    has_null = any(item.get("type") == "null" for item in variants)
    assert len(refs) == 1, schema
    assert has_null, schema
    return refs[0]


def _literal_values(annotation: object) -> tuple[object, ...]:
    origin = get_origin(annotation)
    if origin is Literal:
        return get_args(annotation)
    if origin is Union or origin is UnionType:
        values: list[object] = []
        for item in get_args(annotation):
            if item is type(None):
                continue
            values.extend(_literal_values(item))
        return tuple(values)
    return ()


def _openapi_component_validator(name: str) -> Draft202012Validator:
    with USER_OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return Draft202012Validator(
        {
            "$ref": f"#/components/schemas/{name}",
            "components": document["components"],
        }
    )


def _valid_bazi_entitlement_payload() -> dict[str, Any]:
    return {
        "schema_version": TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION,
        "capability_id": "bazi",
        "resolution": "unknown",
        "free_boundary_layer_id": FREE_BOUNDARY_LAYER_ID,
        "paid_layer_ids": list(PAID_TIME_LAYER_IDS),
        "free_year_set": [2026],
        "capability": {
            "time_layers": [
                {
                    "layer_id": "life",
                    "label": "本命",
                    "available": True,
                    "unavailable_reason": None,
                },
                {
                    "layer_id": "year",
                    "label": "流年",
                    "available": True,
                    "unavailable_reason": None,
                },
                {
                    "layer_id": "month",
                    "label": "流月",
                    "available": False,
                    "unavailable_reason": "本次结果尚未返回流月盘面。",
                },
                {
                    "layer_id": "day",
                    "label": "流日",
                    "available": False,
                    "unavailable_reason": "本次结果尚未返回流日盘面。",
                },
                {
                    "layer_id": "hour",
                    "label": "流时",
                    "available": False,
                    "unavailable_reason": "本次结果尚未返回流时盘面。",
                },
            ]
        },
        "layers": [
            {
                "layer_id": "life",
                "tier": "free",
                "access": "readable",
                "upgrade_cta": None,
            },
            {
                "layer_id": "luck_cycles",
                "tier": "free",
                "access": "unavailable",
                "upgrade_cta": None,
            },
            {
                "layer_id": "year",
                "tier": "free",
                "access": "readable",
                "upgrade_cta": None,
            },
            {
                "layer_id": "month",
                "tier": "paid",
                "access": "fail_closed_unknown",
                "upgrade_cta": "professional_info",
            },
            {
                "layer_id": "day",
                "tier": "paid",
                "access": "unavailable",
                "upgrade_cta": None,
            },
            {
                "layer_id": "hour",
                "tier": "paid",
                "access": "unavailable",
                "upgrade_cta": None,
            },
        ],
    }


def _valid_capability_projection_payload() -> dict[str, Any]:
    return CapabilityProjection(
        capability_id="bazi",
        label="八字",
        tier="A",
        source_system=None,
        runtime_active_rule_count=0,
        judgment_rule_count=0,
        source_status="unavailable",
    ).model_dump(mode="json")


def test_reading_result_response_declares_nullable_live_capability_slots() -> None:
    frozen = _frozen_schemas()["ReadingResultResponse"]
    runtime = _runtime_spec()["components"]["schemas"]["ReadingResultResponse"]

    assert set(frozen["properties"]) == set(runtime["properties"])
    assert set(frozen["properties"]) == set(ReadingResultResponse.model_fields)
    assert set(frozen["required"]) == set(runtime["required"])
    assert frozen["additionalProperties"] is False
    assert runtime["additionalProperties"] is False
    assert "capability" not in frozen["required"]
    assert "time_layer_entitlement" not in frozen["required"]
    assert _is_nullable(frozen["properties"]["capability"])
    assert _is_nullable(runtime["properties"]["capability"])
    assert _is_nullable(frozen["properties"]["time_layer_entitlement"])
    assert _is_nullable(runtime["properties"]["time_layer_entitlement"])
    assert _nullable_ref(frozen["properties"]["capability"]) == (
        "#/components/schemas/CapabilityProjection"
    )
    assert _nullable_ref(runtime["properties"]["capability"]) == (
        "#/components/schemas/CapabilityProjection"
    )
    assert _nullable_ref(frozen["properties"]["time_layer_entitlement"]) == (
        "#/components/schemas/TimeLayerEntitlementResponse"
    )
    assert _nullable_ref(runtime["properties"]["time_layer_entitlement"]) == (
        "#/components/schemas/TimeLayerEntitlementResponse"
    )


def test_time_layer_entitlement_openapi_matches_pydantic_and_v1_closed_tables() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    for name, model in (
        ("TimeLayerEntitlementResponse", TimeLayerEntitlementResponse),
        ("TimeLayerEntitlementLayerResponse", TimeLayerEntitlementLayerResponse),
        ("TimeLayerEntitlementCapabilityResponse", TimeLayerEntitlementCapabilityResponse),
        ("TimeLayerCapabilityItemResponse", TimeLayerCapabilityItemResponse),
        ("CapabilityProjection", CapabilityProjection),
    ):
        frozen = frozen_schemas[name]
        runtime = runtime_schemas[name]
        assert set(frozen["properties"]) == set(runtime["properties"]) == set(model.model_fields)
        assert set(frozen["required"]) == set(runtime["required"])
        assert frozen["additionalProperties"] is False
        assert runtime["additionalProperties"] is False

    entitlement = frozen_schemas["TimeLayerEntitlementResponse"]
    layer = frozen_schemas["TimeLayerEntitlementLayerResponse"]
    capability_item = frozen_schemas["TimeLayerCapabilityItemResponse"]
    sample = TimeLayerEntitlementV1.from_dict(_valid_bazi_entitlement_payload())

    assert set(entitlement["properties"]) == set(sample.to_dict())
    assert entitlement["properties"]["schema_version"]["const"] == (
        TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    )
    assert entitlement["properties"]["free_boundary_layer_id"]["const"] == (
        FREE_BOUNDARY_LAYER_ID
    )
    assert tuple(
        item["const"] for item in entitlement["properties"]["paid_layer_ids"]["prefixItems"]
    ) == PAID_TIME_LAYER_IDS
    assert entitlement["properties"]["capability_id"]["enum"] == list(
        _literal_values(TimeLayerEntitlementResponse.model_fields["capability_id"].annotation)
    )
    assert entitlement["properties"]["resolution"]["enum"] == list(
        _literal_values(TimeLayerEntitlementResponse.model_fields["resolution"].annotation)
    )
    assert layer["properties"]["layer_id"]["enum"] == list(
        _literal_values(TimeLayerEntitlementLayerResponse.model_fields["layer_id"].annotation)
    )
    assert layer["properties"]["tier"]["enum"] == list(
        _literal_values(TimeLayerEntitlementLayerResponse.model_fields["tier"].annotation)
    )
    assert layer["properties"]["access"]["enum"] == list(
        _literal_values(TimeLayerEntitlementLayerResponse.model_fields["access"].annotation)
    )
    assert "enum" not in capability_item["properties"]["layer_id"]
    assert capability_item["properties"]["layer_id"]["type"] == "string"
    assert capability_item["properties"]["layer_id"]["minLength"] == 1


def test_live_capability_and_entitlement_wire_validates_against_frozen_openapi() -> None:
    entitlement_payload = TimeLayerEntitlementV1.from_dict(
        _valid_bazi_entitlement_payload()
    ).to_dict()
    entitlement_validator = _openapi_component_validator("TimeLayerEntitlementResponse")
    capability_validator = _openapi_component_validator("CapabilityProjection")
    result_validator = _openapi_component_validator("ReadingResultResponse")

    entitlement_validator.validate(entitlement_payload)
    capability_validator.validate(_valid_capability_projection_payload())

    dumped = ReadingResultResponse(
        reading_version_id=uuid4(),
        status="accepted",
        accepted_copy=None,
        fact_panel=None,
        view_model=None,
        capability=CapabilityProjection.model_validate(
            _valid_capability_projection_payload()
        ),
        verification=None,
        input_request=None,
        document=None,
        time_layer_entitlement=TimeLayerEntitlementResponse.from_contract(
            TimeLayerEntitlementV1.from_dict(entitlement_payload)
        ),
    ).model_dump(mode="json")
    result_validator.validate(dumped)
    assert dumped["capability"]["capability_id"] == "bazi"
    assert dumped["time_layer_entitlement"]["schema_version"] == (
        TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    )

    null_result = dict(dumped)
    null_result["capability"] = None
    null_result["time_layer_entitlement"] = None
    result_validator.validate(null_result)

    extra_entitlement = dict(entitlement_payload)
    extra_entitlement["parallel_slot"] = True
    assert list(entitlement_validator.iter_errors(extra_entitlement))

    parallel_version = dict(entitlement_payload)
    parallel_version["schema_version"] = "time-layer-entitlement/v2"
    assert list(entitlement_validator.iter_errors(parallel_version))

    invented_resolution = dict(entitlement_payload)
    invented_resolution["resolution"] = "maybe"
    assert list(entitlement_validator.iter_errors(invented_resolution))

    extra_capability_layer = dict(entitlement_payload)
    extra_capability_layer["capability"] = {
        "time_layers": [
            {
                **entitlement_payload["capability"]["time_layers"][0],
                "tier": "free",
            }
        ]
    }
    assert list(entitlement_validator.iter_errors(extra_capability_layer))

    extra_result = dict(dumped)
    extra_result["not_in_contract"] = True
    assert list(result_validator.iter_errors(extra_result))
