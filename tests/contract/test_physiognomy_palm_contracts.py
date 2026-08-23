from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INPUT_SCHEMA = (
    ROOT / "contracts" / "schemas" / "inputs" / "physiognomy-palm-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT / "contracts" / "schemas" / "views" / "physiognomy-palm-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "physiognomy-palm-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "physiognomy-palm-source-rules-v1.yaml"
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _valid_input() -> dict[str, Any]:
    return {
        "schema_version": "physiognomy-palm-input/v1",
        "mode": "palm",
        "observations": [
            {
                "region_id": "left_palm",
                "descriptor": "region_visible",
                "visibility": "full",
                "uncertainty": 0.1,
            }
        ],
        "region_label": "掌",
        "subject_ref": None,
    }


def _view(*, match_status: str, lookup_key: str, rule_id: str) -> dict[str, Any]:
    exact = match_status == "exact"
    return {
        "schema_version": "physiognomy-palm-view/v1",
        "subject_ref": "sid-0123456789abcdef0123456789abcdef",
        "mode": "palm",
        "normalized": {
            "mode": "palm",
            "taxonomy": "anatomical_palm_classical_v1",
            "region_ids": ["left_palm"],
            "region_label": lookup_key,
        },
        "region_match": None
        if not exact
        else {
            "region_id": "left_palm",
            "lookup_key": lookup_key,
            "match_status": match_status,
            "source_rule_id": rule_id,
            "source_excerpt": "夫手足者谓之四肢，以象四时，加之以首，谓之五体，以象五行",
        },
        "source_identity": {
            "source_pack": "physiognomy/mayi-shenxiang",
            "source_dependency_id": "physiognomy.palm-limbs-handback",
            "source_rule_id": rule_id,
            "source_anchor": "fulltext.md#L1305",
        },
        "active_source_rule_ids": [rule_id],
        "source_dependency_ids": ["physiognomy.palm-limbs-handback"],
        "source_status": "exact_rule_bound" if exact else "unmatched",
        "source_gaps": [
            "western life/head/heart/fate lines are not v1 region_ids",
            "MY-012–MY-014 面相手相十二宫 is modern appendix",
        ],
        "limitations": [
            "v1 只输出手足/掌/五指/手背术语身份，不输出吉凶、西式掌纹或现代附益十二宫。",
        ],
        "hard_verdict": None,
    }


def test_palm_input_accepts_classical_regions_and_rejects_western_lines() -> None:
    schema = _schema(INPUT_SCHEMA)
    Draft202012Validator(schema).validate(_valid_input())
    western = _valid_input()
    western["observations"] = [
        {
            "region_id": "life_line",
            "descriptor": "line_continuous",
            "visibility": "full",
            "uncertainty": 0,
        }
    ]
    assert list(Draft202012Validator(schema).iter_errors(western))
    face = _valid_input()
    face["observations"][0]["region_id"] = "forehead"
    assert list(Draft202012Validator(schema).iter_errors(face))
    posture = {**_valid_input(), "mode": "posture"}
    assert list(Draft202012Validator(schema).iter_errors(posture))
    combined = {**_valid_input(), "mode": "combined"}
    assert list(Draft202012Validator(schema).iter_errors(combined))


def test_palm_view_forbids_verdict_and_western_line_fields() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view(
        match_status="exact",
        lookup_key="掌",
        rule_id="physiognomy-palm/mayi-shenxiang#PP-MY-01",
    )
    Draft202012Validator(schema).validate(payload)
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "hard_verdict": "吉"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "life_line": "continuous"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "mode": "posture"})
    )


def test_palm_samples_are_transcribed_not_computed() -> None:
    samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    lookup: dict[str, str] = dict(rules.get("lookup") or {})
    for rule in rules["rules"]:
        lookup.update(rule.get("lookup") or {})
    terminology = rules["terminology_regions"]
    assert samples["schema_version"] == "mingli-algorithm-source-samples-v1"
    assert rules["provider_status"] == "local_provider_not_in_runtime"
    assert lookup == {}
    assert terminology["掌"] == "left_palm"
    assert terminology["手背纹"] == "hand_back"
    assert terminology["龙纹"] == "fingers"
    for case in samples["cases"].values():
        expected = case["expected"]
        assert expected["hard_verdict"] is None
        assert expected["mode"] == "palm"
        key = expected.get("lookup_key")
        if expected["match_status"] == "exact":
            assert key in terminology
        else:
            assert expected["region_match"] is None
            assert key not in terminology


def test_physiognomy_palm_is_not_wired_into_reading_document() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "physiognomy-palm-view/v1" not in dumped
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    catalog_text = catalog.read_text(encoding="utf-8")
    assert "physiognomy-palm" not in catalog_text
