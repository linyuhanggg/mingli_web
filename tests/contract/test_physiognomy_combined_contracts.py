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
    / "physiognomy-combined-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT
    / "contracts"
    / "schemas"
    / "views"
    / "physiognomy-combined-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "physiognomy-combined-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "physiognomy-combined-source-rules-v1.yaml"
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _valid_input() -> dict[str, Any]:
    return {
        "schema_version": "physiognomy-combined-input/v1",
        "mode": "combined",
        "branches": ["face"],
        "observations": [
            {
                "branch": "face",
                "region_id": "forehead",
                "descriptor": "region_visible",
                "visibility": "full",
                "uncertainty": 0.1,
            }
        ],
        "region_label": "首",
        "subject_ref": None,
    }


def _view(*, exact: bool, lookup_key: str, rule_id: str) -> dict[str, Any]:
    return {
        "schema_version": "physiognomy-combined-view/v1",
        "subject_ref": "sid-0123456789abcdef0123456789abcdef",
        "mode": "combined",
        "normalized": {
            "mode": "combined",
            "taxonomy": "branch_comparison_classical_v1",
            "completed_branches": ["face"],
            "missing_branches": ["palm", "posture"],
        },
        "branch_facts": [
            {
                "branch": "face",
                "region_id": "forehead",
                "lookup_key": lookup_key,
                "match_status": "exact" if exact else "unmatched",
                "source_rule_id": rule_id,
                "source_excerpt": "夫手足者谓之四肢，以象四时，加之以首，谓之五体，以象五行",
            }
        ],
        "corroboration": [],
        "disagreements": [],
        "evidence_sufficiency": {
            "completed_count": 1,
            "missing_branches": ["palm", "posture"],
            "status": "single_branch",
        },
        "source_identity": {
            "source_pack": "physiognomy/mayi-shenxiang",
            "source_dependency_id": "physiognomy.combined-branch-comparison",
            "source_rule_id": rule_id,
            "source_anchor": "fulltext.md#L1305",
        },
        "active_source_rule_ids": [rule_id],
        "source_dependency_ids": ["physiognomy.combined-branch-comparison"],
        "source_status": "exact_rule_bound" if exact else "unmatched",
        "source_gaps": [
            "western fused scores are not v1 region_ids",
            "MY-012–MY-014 面相手相十二宫 is modern appendix",
        ],
        "limitations": [
            "v1 只分支出事实与比较行，不输出平均吉凶或补全缺支。",
        ],
        "forced_resolution": False,
        "hard_verdict": None,
    }


def test_combined_input_accepts_subset_and_rejects_western_ids() -> None:
    schema = _schema(INPUT_SCHEMA)
    Draft202012Validator(schema).validate(_valid_input())
    two = _valid_input()
    two["branches"] = ["face", "palm"]
    two["observations"] = [
        *_valid_input()["observations"],
        {
            "branch": "palm",
            "region_id": "left_hand",
            "descriptor": "region_visible",
            "visibility": "partial",
            "uncertainty": 0.2,
        },
    ]
    Draft202012Validator(schema).validate(two)
    western = _valid_input()
    western["observations"] = [
        {
            "branch": "face",
            "region_id": "life_line",
            "descriptor": "region_visible",
            "visibility": "full",
            "uncertainty": 0,
        }
    ]
    assert list(Draft202012Validator(schema).iter_errors(western))
    bmi = _valid_input()
    bmi["branches"] = ["posture"]
    bmi["observations"] = [
        {
            "branch": "posture",
            "region_id": "bmi",
            "descriptor": "region_visible",
            "visibility": "full",
            "uncertainty": 0,
        }
    ]
    assert list(Draft202012Validator(schema).iter_errors(bmi))
    palm_mode = {**_valid_input(), "mode": "palm"}
    assert list(Draft202012Validator(schema).iter_errors(palm_mode))
    face_mode = {**_valid_input(), "mode": "face"}
    assert list(Draft202012Validator(schema).iter_errors(face_mode))
    ghost = _valid_input()
    ghost["observations"][0]["branch"] = "palm"
    assert list(Draft202012Validator(schema).iter_errors(ghost))
    empty = {**_valid_input(), "branches": []}
    assert list(Draft202012Validator(schema).iter_errors(empty))


def test_combined_view_forbids_verdict_and_fusion_fields() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view(
        exact=True,
        lookup_key="首",
        rule_id="physiognomy-combined/mayi-shenxiang#PC-MY-01",
    )
    Draft202012Validator(schema).validate(payload)
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "hard_verdict": "吉"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "fused_score": 0.8})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "forced_resolution": True})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "mode": "palm"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "mode": "face"})
    )


def test_combined_samples_are_transcribed_not_computed() -> None:
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
    assert terminology["首"] == "forehead"
    assert terminology["四肢"] == "left_hand"
    assert terminology["形"] == "form"
    assert "官禄宫" not in terminology
    for case in samples["cases"].values():
        expected = case["expected"]
        assert expected["hard_verdict"] is None
        assert expected["mode"] == "combined"
        assert expected["forced_resolution"] is False
        key = expected.get("lookup_key")
        if expected["match_status"] == "exact":
            assert key in terminology
        else:
            assert expected["region_match"] is None
            assert key not in terminology


def test_physiognomy_combined_is_not_wired_into_reading_document() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "physiognomy-combined-view/v1" not in dumped
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    catalog_text = catalog.read_text(encoding="utf-8")
    assert "physiognomy-combined" not in catalog_text
