import importlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"


def load_frozen_paths() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document["paths"]


def test_fastapi_operations_match_the_frozen_contract() -> None:
    main = importlib.import_module("app.main")
    frozen_paths = load_frozen_paths()
    runtime_paths = main.create_app().openapi()["paths"]

    assert set(runtime_paths) == set(frozen_paths)
    for path, frozen_path in frozen_paths.items():
        for method, frozen_operation in frozen_path.items():
            assert runtime_paths[path][method]["operationId"] == frozen_operation["operationId"]


def _runtime_spec() -> dict[str, Any]:
    main = importlib.import_module("app.main")
    return main.create_app().openapi()


def _frozen_schemas() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document["components"]["schemas"]


def _resolve(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return components[ref]
    return schema


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
    assert _is_nullable(runtime["properties"]["note"])
    assert "accepted" not in frozen["properties"]
    assert "accepted" not in runtime["properties"]


def test_reading_summary_nullability_typing_and_status_align() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["ReadingVersionSummary"]
    runtime = _resolve(runtime_schemas["ReadingStartResponse"], runtime_schemas)

    assert _is_nullable(frozen["properties"]["profile_version_id"])
    assert _is_nullable(runtime["properties"]["profile_version_id"])

    frozen_status = frozen["properties"]["status"]
    runtime_status = _resolve(runtime["properties"]["status"], runtime_schemas)
    assert set(frozen_status["enum"]) == set(runtime_status["enum"]) == {
        "input_ready",
        "waiting_input",
        "terminal_stopped",
        "prepared",
        "completing",
        "accepted",
        "delayed",
        "runtime_unknown",
    }

    frozen_horizon = frozen["properties"]["horizon"]
    runtime_horizon = _resolve(runtime["properties"]["horizon"], runtime_schemas)
    assert set(frozen_horizon["properties"]) == set(runtime_horizon["properties"]) == {
        "kind_id",
        "start",
        "end",
    }
    assert frozen_horizon.get("additionalProperties") is False
    assert runtime_horizon.get("additionalProperties") is False
    assert _is_nullable(frozen_horizon["properties"]["start"])
    assert _is_nullable(runtime_horizon["properties"]["start"])
    assert _is_nullable(frozen_horizon["properties"]["end"])
    assert _is_nullable(runtime_horizon["properties"]["end"])
    assert frozen_horizon["properties"]["start"]["format"] == "date"
    runtime_start_branch = next(
        branch
        for branch in runtime_horizon["properties"]["start"]["anyOf"]
        if branch.get("type") != "null"
    )
    assert runtime_start_branch.get("format") == "date"

    assert _is_nullable(frozen["properties"]["prior_answer"])
    assert _is_nullable(runtime["properties"]["prior_answer"])
    assert _is_nullable(frozen["properties"]["input_request"])
    assert _is_nullable(runtime["properties"]["input_request"])


def test_reading_result_and_fact_panel_nullability_align() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen_result = frozen_schemas["ReadingResultResponse"]
    runtime_result = runtime_schemas["ReadingResultResponse"]
    nullable_result_fields = {
        "accepted_copy",
        "fact_panel",
        "verification",
        "input_request",
    }

    assert set(frozen_result["required"]) == set(runtime_result["required"])
    for field_name in nullable_result_fields:
        assert _is_nullable(frozen_result["properties"][field_name])
        assert _is_nullable(runtime_result["properties"][field_name])

    frozen_panel = frozen_schemas["ReadingFactPanel"]
    assert _is_nullable(frozen_panel["properties"]["prior_answer"])
    assert _is_nullable(frozen_panel["properties"]["request_view"])

    frozen_request_view = frozen_schemas["ReadingRequestView"]
    frozen_horizon = frozen_request_view["properties"]["horizon"]
    assert not _is_nullable(frozen_horizon)
    assert _is_nullable(frozen_horizon["properties"]["start"])
    assert _is_nullable(frozen_horizon["properties"]["end"])


def test_frozen_rate_limit_response_declares_retry_after() -> None:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)

    retry_after = document["components"]["responses"]["TooManyRequests"]["headers"][
        "Retry-After"
    ]
    assert retry_after["schema"]["type"] == "string"


def test_liuyao_cast_constraints_align() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["LiuyaoStartRequest"]["properties"]["cast"]
    runtime = runtime_schemas["LiuyaoStartRequest"]["properties"]["cast"]

    frozen_array = next(
        branch for branch in frozen["oneOf"] if branch.get("type") == "array"
    )
    runtime_array = next(
        branch for branch in runtime["anyOf"] if branch.get("type") == "array"
    )
    assert frozen_array["minItems"] == runtime_array["minItems"] == 6
    assert frozen_array["maxItems"] == runtime_array["maxItems"] == 6
    assert frozen_array["items"]["minimum"] == runtime_array["items"]["minimum"] == 6
    assert frozen_array["items"]["maximum"] == runtime_array["items"]["maximum"] == 9

    frozen_coin = next(
        branch for branch in frozen["oneOf"] if branch.get("type") == "string"
    )
    runtime_coin = next(
        branch for branch in runtime["anyOf"] if branch.get("type") == "string"
    )
    assert frozen_coin["const"] == runtime_coin["const"] == "digital_coin"
