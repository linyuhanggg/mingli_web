#!/usr/bin/env python3

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest
import yaml
from app.readings.api_schemas import SharedReadingResponse
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"


def _frozen_schemas() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document["components"]["schemas"]


def test_frozen_share_response_points_to_a_narrow_document() -> None:
    schemas = _frozen_schemas()
    shared = schemas["SharedReadingDocumentV1"]

    assert schemas["SharedReadingResponse"]["properties"]["document"]["$ref"] == (
        "#/components/schemas/SharedReadingDocumentV1"
    )
    assert set(shared["required"]) == {
        "schema_version",
        "document_id",
        "reading_version_id",
        "accepted_copy_ref",
        "product_version",
        "presentation_contract_version",
        "answer_summary",
        "themes",
        "claims",
        "evidence",
        "boundaries",
        "versions",
    }
    assert set(shared["properties"]) == set(shared["required"])
    assert shared["properties"]["schema_version"]["const"] == (
        "shared-reading-document/v1"
    )
    assert not {
        "view_model",
        "subject_summaries",
        "actions",
    } & set(shared["properties"])


def test_runtime_share_response_keeps_the_same_top_level_boundary() -> None:
    main = importlib.import_module("app.main")
    schemas = main.create_app().openapi()["components"]["schemas"]
    shared = schemas["SharedReadingDocumentV1"]

    assert set(shared["properties"]) == {
        "schema_version",
        "document_id",
        "reading_version_id",
        "accepted_copy_ref",
        "product_version",
        "presentation_contract_version",
        "answer_summary",
        "themes",
        "claims",
        "evidence",
        "boundaries",
        "versions",
    }
    assert schemas["SharedReadingResponse"]["properties"]["document"]["$ref"] == (
        "#/components/schemas/SharedReadingDocumentV1"
    )


def test_api_response_rejects_owner_document_fields() -> None:
    document = {
        "schema_version": "shared-reading-document/v1",
        "document_id": "reading-version:1",
        "reading_version_id": "version-1",
        "accepted_copy_ref": "accepted-copy:1",
        "product_version": "bazi-v1",
        "presentation_contract_version": "presentation-v1",
        "answer_summary": "先稳住长期积累。",
        "themes": [],
        "claims": [],
        "evidence": [],
        "boundaries": [],
        "versions": {
            "runtime_release": "runtime-v1",
            "view_model_schema": "bazi-chart/v1",
            "reading_document_schema": "reading-document/v1",
        },
    }
    response = SharedReadingResponse.model_validate({"document": document})
    assert "view_model" not in response.document.model_dump()

    with pytest.raises(ValidationError):
        SharedReadingResponse.model_validate(
            {"document": {**document, "view_model": {"schema_version": "bazi-chart/v1"}}}
        )
