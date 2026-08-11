import importlib
from pathlib import Path
from typing import Any

import yaml

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


def test_verification_request_contract_is_three_result_and_aligned() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["VerificationRequest"]
    runtime = runtime_schemas["VerificationRequest"]

    assert set(frozen["required"]) == set(runtime["required"]) == {"results"}
    for schema in (frozen, runtime):
        results = schema["properties"]["results"]
        assert results["minItems"] == 3
        assert results["maxItems"] == 3
        assert results["items"] == {"$ref": "#/components/schemas/VerificationResultItem"}
        assert _is_nullable(schema["properties"]["note"])
    assert frozen["properties"]["note"]["maxLength"] == 500
    assert runtime["properties"]["note"]["anyOf"][0]["maxLength"] == 500


def test_verification_result_item_contract_is_aligned() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["VerificationResultItem"]
    runtime = runtime_schemas["VerificationResultItem"]

    assert set(frozen["required"]) == set(runtime["required"]) == {"fact_ref", "outcome"}
    assert set(frozen["properties"]["outcome"]["enum"]) == set(
        runtime["properties"]["outcome"]["enum"]
    ) == {"accepted", "partial", "disagreed", "unknown"}
    assert frozen["properties"]["fact_ref"]["type"] == "string"
    assert runtime["properties"]["fact_ref"]["type"] == "string"
    assert frozen["properties"]["fact_ref"]["maxLength"] == 200
    assert runtime["properties"]["fact_ref"]["maxLength"] == 200


def test_verification_summary_contract_is_three_result_and_aligned() -> None:
    frozen_schemas = _frozen_schemas()
    runtime_schemas = _runtime_spec()["components"]["schemas"]

    frozen = frozen_schemas["ReadingVerificationSummary"]
    runtime = runtime_schemas["ReadingVerificationSummary"]

    assert set(frozen["required"]) == set(runtime["required"]) == {
        "verification_id",
        "reading_version_id",
        "results",
        "note",
        "created_at",
    }
    for schema in (frozen, runtime):
        results = schema["properties"]["results"]
        assert results["items"] == {"$ref": "#/components/schemas/VerificationResultItem"}
        assert _is_nullable(schema["properties"]["note"])
