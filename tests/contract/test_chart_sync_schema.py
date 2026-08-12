import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "contracts" / "schemas" / "bazi-chart-sync-v1.schema.json"


def _validator() -> Draft202012Validator:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_chart_sync_json_schema_accepts_ready_and_need_input_without_token() -> None:
    validator = _validator()
    validator.validate(
        {
            "profile_version_id": "b2f785df-8ac8-4f80-bddd-a76e30438972",
            "status": "ready",
            "chart_handle": None,
            "fact_panel": {
                "facts": [
                    {
                        "ref": "fact:public/calculated/bazi/branch_relations",
                        "value": [],
                    }
                ]
            },
            "input_request": None,
        }
    )
    validator.validate(
        {
            "profile_version_id": "b2f785df-8ac8-4f80-bddd-a76e30438972",
            "status": "need_input",
            "chart_handle": "opaque-server-handle",
            "fact_panel": None,
            "input_request": {"requirements": [{"any_of": []}]},
        }
    )


def test_chart_sync_json_schema_rejects_runtime_state_token() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(
            {
                "profile_version_id": "b2f785df-8ac8-4f80-bddd-a76e30438972",
                "status": "need_input",
                "chart_handle": "opaque-server-handle",
                "fact_panel": None,
                "input_request": {"requirements": []},
                "state_token": "must-never-cross-http",
            }
        )
