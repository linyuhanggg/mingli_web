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


def test_contract_does_not_expose_future_payment_or_model_routes() -> None:
    paths = load_openapi_document()["paths"]

    assert not any("payment" in path for path in paths)
    assert not any("model" in path for path in paths)
