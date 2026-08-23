from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INPUT_SCHEMA = (
    ROOT
    / "contracts"
    / "schemas"
    / "inputs"
    / "physiognomy-posture-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT
    / "contracts"
    / "schemas"
    / "views"
    / "physiognomy-posture-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "physiognomy-posture-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "physiognomy-posture-source-rules-v1.yaml"
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _valid_input() -> dict[str, Any]:
    return {
        "schema_version": "physiognomy-posture-input/v1",
        "mode": "posture",
        "observations": [
            {
                "region_id": "whole_body",
                "descriptor": "region_visible",
                "visibility": "full",
                "uncertainty": 0.1,
            }
        ],
        "region_label": "五体",
        "subject_ref": None,
    }


def _view(*, match_status: str, lookup_key: str, rule_id: str) -> dict[str, Any]:
    exact = match_status == "exact"
    return {
        "schema_version": "physiognomy-posture-view/v1",
        "subject_ref": "sid-0123456789abcdef0123456789abcdef",
        "mode": "posture",
        "normalized": {
            "mode": "posture",
            "taxonomy": "anatomical_posture_classical_v1",
            "region_ids": ["whole_body"],
            "region_label": lookup_key,
        },
        "region_match": None
        if not exact
        else {
            "region_id": "whole_body",
            "lookup_key": lookup_key,
            "match_status": match_status,
            "source_rule_id": rule_id,
            "source_excerpt": "夫手足者谓之四肢，以象四时，加之以首，谓之五体，以象五行",
        },
        "source_identity": {
            "source_pack": "physiognomy/mayi-shenxiang",
            "source_dependency_id": "physiognomy.posture-body-bone-flesh",
            "source_rule_id": rule_id,
            "source_anchor": "fulltext.md#L1305",
        },
        "active_source_rule_ids": [rule_id],
        "source_dependency_ids": ["physiognomy.posture-body-bone-flesh"],
        "source_status": "exact_rule_bound" if exact else "unmatched",
        "source_gaps": [
            "western BMI/somatotype/medical posture are not v1 region_ids",
            "MY-012–MY-014 脚部运动 is modern appendix",
        ],
        "limitations": [
            "v1 只输出形/骨/肉/五体术语身份，不输出吉凶、西式体型量表或现代附益运动语。",
        ],
        "hard_verdict": None,
    }


def test_posture_input_accepts_classical_regions_and_rejects_western_ids() -> None:
    schema = _schema(INPUT_SCHEMA)
    Draft202012Validator(schema).validate(_valid_input())
    western = _valid_input()
    western["observations"] = [
        {
            "region_id": "bmi",
            "descriptor": "somatotype_ectomorph",
            "visibility": "full",
            "uncertainty": 0,
        }
    ]
    assert list(Draft202012Validator(schema).iter_errors(western))
    spine = _valid_input()
    spine["observations"][0]["region_id"] = "spine_curve"
    assert list(Draft202012Validator(schema).iter_errors(spine))
    palm = {**_valid_input(), "mode": "palm"}
    assert list(Draft202012Validator(schema).iter_errors(palm))
    combined = {**_valid_input(), "mode": "combined"}
    assert list(Draft202012Validator(schema).iter_errors(combined))
    face = _valid_input()
    face["observations"][0]["region_id"] = "forehead"
    assert list(Draft202012Validator(schema).iter_errors(face))


def test_posture_view_forbids_verdict_and_western_fields() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view(
        match_status="exact",
        lookup_key="五体",
        rule_id="physiognomy-posture/mayi-shenxiang#PP-MY-01",
    )
    Draft202012Validator(schema).validate(payload)
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "hard_verdict": "吉"})
    )
    assert list(Draft202012Validator(schema).iter_errors({**payload, "bmi": 22}))
    assert list(Draft202012Validator(schema).iter_errors({**payload, "mode": "combined"}))
    assert list(Draft202012Validator(schema).iter_errors({**payload, "mode": "palm"}))


def test_posture_samples_are_transcribed_not_computed() -> None:
    samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    lookup: dict[str, str] = dict(rules.get("lookup") or {})
    for rule in rules["rules"]:
        lookup.update(rule.get("lookup") or {})
    terminology = rules["terminology_regions"]
    assert samples["schema_version"] == "mingli-algorithm-source-samples-v1"
    assert rules["provider_status"] == "local_provider_not_in_runtime"
    assert lookup == {}
    assert terminology["五体"] == "whole_body"
    assert terminology["骨"] == "bone"
    assert terminology["形"] == "form"
    assert "脚腕" not in terminology
    for case in samples["cases"].values():
        expected = case["expected"]
        assert expected["hard_verdict"] is None
        assert expected["mode"] == "posture"
        key = expected.get("lookup_key")
        if expected["match_status"] == "exact":
            assert key in terminology
        else:
            assert expected["region_match"] is None
            assert key not in terminology


def test_physiognomy_posture_is_not_wired_into_reading_document() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "physiognomy-posture-view/v1" not in dumped
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    catalog_text = catalog.read_text(encoding="utf-8")
    assert "physiognomy-posture" not in catalog_text
