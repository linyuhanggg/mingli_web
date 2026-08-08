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
