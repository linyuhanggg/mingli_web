from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INPUT_SCHEMA = (
    ROOT / "contracts" / "schemas" / "inputs" / "name-analysis-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT / "contracts" / "schemas" / "views" / "name-analysis-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "name-analysis-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "name-analysis-source-rules-v1.yaml"
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _view(family: str, given: str | None, *, tone: str | None, status: str) -> dict[str, Any]:
    match_status = "exact" if tone else "unmatched"
    source_status = "exact_rule_bound" if tone else "unmatched"
    graphemes = [family] + ([given] if given else [])
    return {
        "schema_version": "name-analysis-view/v1",
        "subject_ref": f"name:{''.join(graphemes)}",
        "normalized": {
            "family_name": family,
            "given_name": given,
            "graphemes": graphemes,
            "script": "hanzi",
        },
        "surname_wuyin": {
            "grapheme": family,
            "lookup_key": family,
            "tone": tone,
            "element": {
                "角": "wood",
                "徵": "fire",
                "宫": "earth",
                "商": "metal",
                "羽": "water",
            }.get(tone) if tone else None,
            "match_status": match_status,
            "source_rule_id": status,
        },
        "given_name_wuyin": None,
        "seasonal_markers": None if tone is None else {
            "status": "identity_only",
            "wang_branches": ["寅", "卯"],
            "de_branches": ["戌", "亥"],
            "hard_verdict": None,
            "source_rule_id": "name-analysis/wuxing-jingji#NA-WX-01b",
            "boundary": "identity markers only",
        },
        "source_identity": {
            "source_pack": "luming-nayin/wuxing-jingji",
            "source_dependency_id": "name-analysis.wuyin-xingshi",
            "source_rule_id": status,
            "source_anchor": "fulltext.md#L2953",
        },
        "active_source_rule_ids": [status],
        "source_dependency_ids": ["name-analysis.wuyin-xingshi"],
        "source_status": source_status,
        "source_gaps": ["given-name 五音 table is not in v1"],
        "limitations": [
            "v1 只输出姓氏五音身份，不输出康熙笔画、五格或吉凶。",
        ],
        "hard_verdict": None,
    }


def test_name_analysis_input_schema_accepts_hanzi_and_rejects_latin() -> None:
    schema = _schema(INPUT_SCHEMA)
    Draft202012Validator(schema).validate(
        {
            "schema_version": "name-analysis-input/v1",
            "name": "赵青",
            "usage_scene": "unspecified",
        }
    )
    errors = list(
        Draft202012Validator(schema).iter_errors(
            {
                "schema_version": "name-analysis-input/v1",
                "name": "Alex",
                "usage_scene": "unspecified",
            }
        )
    )
    assert errors


def test_name_analysis_view_schema_forbids_verdict_and_wuge() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view("赵", "青", tone="角", status="name-analysis/wuxing-jingji#NA-WX-02")
    Draft202012Validator(schema).validate(payload)
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "hard_verdict": "吉"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "wuge": {"天格": 1}})
    )


def test_name_analysis_samples_are_transcribed_not_computed() -> None:
    samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for rule in rules["rules"]:
        lookup.update(rule.get("lookup") or {})
    assert samples["schema_version"] == "mingli-algorithm-source-samples-v1"
    assert rules["provider_status"] == "contract_only_no_provider"
    assert lookup["赵"] == "角"
    assert lookup["钱"] == "徵"
    assert lookup["孙"] == "宫"
    assert lookup["王"] == "商"
    assert lookup["吴"] == "羽"
    unmatched = samples["cases"]["name-analysis-unmatched-surname"]["expected"]
    assert unmatched["lookup_key"] not in lookup
    assert unmatched["hard_verdict"] is None


def test_name_analysis_is_not_wired_into_reading_document() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "name-analysis-view/v1" not in dumped
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    assert "name-analysis" not in catalog.read_text(encoding="utf-8")
