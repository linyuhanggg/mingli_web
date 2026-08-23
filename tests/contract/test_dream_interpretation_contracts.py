from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INPUT_SCHEMA = (
    ROOT / "contracts" / "schemas" / "inputs" / "dream-interpretation-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT / "contracts" / "schemas" / "views" / "dream-interpretation-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "dream-interpretation-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "dream-interpretation-source-rules-v1.yaml"
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _view(dream_text: str, omen_key: str | None) -> dict[str, Any]:
    return {
        "schema_version": "dream-interpretation-view/v1",
        "subject_ref": f"dream:{omen_key or dream_text[:16]}",
        "normalized": {
            "dream_text": dream_text,
            "omen_key": omen_key,
            "script": "hanzi",
        },
        "omen_match": None,
        "source_identity": {
            "source_pack": "selection/yuqia-ji",
            "source_dependency_id": "dream.yuqia-zhanmeng",
            "source_rule_id": "dream-interpretation/yuqia-ji#DI-YQ-03",
            "source_anchor": "fulltext.md#L12",
        },
        "active_source_rule_ids": ["dream-interpretation/yuqia-ji#DI-YQ-03"],
        "source_dependency_ids": ["dream.yuqia-zhanmeng"],
        "source_status": "unmatched",
        "source_gaps": ["current yuqia-ji fulltext has no 占梦 omen table"],
        "limitations": [
            "v1 只做玉匣记占梦查找；当前版本查找表为空，不输出周公网典、模型文案或吉凶。",
        ],
        "hard_verdict": None,
    }


def test_dream_input_schema_accepts_hanzi_and_rejects_latin() -> None:
    schema = _schema(INPUT_SCHEMA)
    Draft202012Validator(schema).validate(
        {
            "schema_version": "dream-interpretation-input/v1",
            "dream_text": "梦见下雨",
            "omen_key": "雨",
        }
    )
    errors = list(
        Draft202012Validator(schema).iter_errors(
            {
                "schema_version": "dream-interpretation-input/v1",
                "dream_text": "I dreamed of rain",
            }
        )
    )
    assert errors


def test_dream_view_schema_forbids_verdict_and_zhou_gong() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view("梦见下雨", "雨")
    Draft202012Validator(schema).validate(payload)
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "hard_verdict": "吉"})
    )
    assert list(
        Draft202012Validator(schema).iter_errors({**payload, "zhou_gong": {"雨": "财"}})
    )


def test_dream_samples_are_transcribed_not_computed() -> None:
    samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    lookup = rules.get("lookup") or {}
    for rule in rules["rules"]:
        lookup.update(rule.get("lookup") or {})
    assert samples["schema_version"] == "mingli-algorithm-source-samples-v1"
    assert rules["provider_status"] == "local_provider_not_in_runtime"
    assert lookup == {}
    for case in samples["cases"].values():
        expected = case["expected"]
        assert expected["hard_verdict"] is None
        assert expected["match_status"] == "unmatched"
        assert expected["omen_match"] is None
        key = expected.get("lookup_key")
        if key:
            assert key not in lookup


def test_dream_interpretation_is_not_wired_into_reading_document() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "dream-interpretation-view/v1" not in dumped
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    catalog_text = catalog.read_text(encoding="utf-8")
    assert "dream-interpretation" not in catalog_text
    assert "jiemeng" not in catalog_text
