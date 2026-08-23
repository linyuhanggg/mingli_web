from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
VIEW_SCHEMA = (
    ROOT
    / "contracts"
    / "schemas"
    / "views"
    / "cross-art-synthesis-view-v1.schema.json"
)
SAMPLES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "fixtures"
    / "cross-art-synthesis-samples-v1.yaml"
)
RULES = (
    ROOT
    / "core"
    / "mingli-master"
    / "references"
    / "matrices"
    / "cross-art-synthesis-source-rules-v1.yaml"
)
LIVE_VIEWS = (
    ROOT / "contracts" / "schemas" / "views" / "hecan-view-v1.schema.json",
    ROOT / "contracts" / "schemas" / "views" / "wenshi-view-v1.schema.json",
    ROOT / "contracts" / "schemas" / "views" / "canwen-view-v1.schema.json",
)


def _schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _view(*, product_id: str, arts: list[str], dimension_id: str) -> dict[str, Any]:
    pack = (
        "divination/huozhu-lin"
        if product_id == "wenshi"
        else "xingming/guotian-jing"
    )
    rule_id = (
        "cross-art-synthesis/huozhu-lin#CAS-HZ-01"
        if product_id == "wenshi"
        else "cross-art-synthesis/guotian-jing#CAS-GX-01"
    )
    return {
        "schema_version": "cross-art-synthesis-view/v1",
        "product_id": product_id,
        "subject_ref": "sid-0123456789abcdef0123456789abcdef",
        "dimension_id": dimension_id,
        "selected_art_ids": arts,
        "present_art_ids": arts,
        "missing_art_ids": [],
        "convergence": [],
        "disagreements": [],
        "evidence_sufficiency": {
            "present_count": len(arts),
            "missing_art_ids": [],
            "status": "all_selected_present",
        },
        "source_identity": {
            "source_pack": pack,
            "source_dependency_id": "cross-art.retain-disagreement",
            "source_rule_id": rule_id,
            "source_anchor": "fulltext.md#L1530",
        },
        "active_source_rule_ids": [rule_id],
        "source_dependency_ids": ["cross-art.retain-disagreement"],
        "source_status": "exact_rule_bound",
        "source_gaps": [
            "dimension_fact_scope is not 互证",
            "理无二致 is compilation slogan",
        ],
        "limitations": [
            "v1 只钉比较行，不输出平均吉凶或补全缺术。",
        ],
        "forced_resolution": False,
        "hard_verdict": None,
    }


def test_synthesis_view_forbids_verdict_and_fusion_fields() -> None:
    schema = _schema(VIEW_SCHEMA)
    payload = _view(
        product_id="hecan",
        arts=["bazi", "ziwei"],
        dimension_id="career",
    )
    Draft202012Validator(schema).validate(payload)
    wenshi = _view(
        product_id="wenshi",
        arts=["liuyao", "qimen", "daliuren"],
        dimension_id="outcome",
    )
    Draft202012Validator(schema).validate(wenshi)
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
        Draft202012Validator(schema).iter_errors({**payload, "winner": "bazi"})
    )
    string_row = {**payload, "convergence": ["两术一致"]}
    assert list(Draft202012Validator(schema).iter_errors(string_row))


def test_synthesis_samples_are_transcribed_not_computed() -> None:
    samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    lookup: dict[str, str] = dict(rules.get("lookup") or {})
    for rule in rules["rules"]:
        lookup.update(rule.get("lookup") or {})
    assert samples["schema_version"] == "mingli-algorithm-source-samples-v1"
    assert rules["provider_status"] == "local_provider_not_in_runtime"
    assert lookup == {}
    excluded = set(rules["excluded_methods"])
    assert "dimension_fact_scope_as_convergence" in excluded
    assert "provider_scope_name_as_disagreement" in excluded
    for case in samples["cases"].values():
        expected = case["expected"]
        assert expected["hard_verdict"] is None
        assert expected["forced_resolution"] is False
        assert expected["convergence"] == []
        if expected["match_status"] == "unmatched":
            assert expected["region_match"] is None
            assert expected.get("lookup_key") not in lookup


def test_live_views_reuse_comparison_rows_and_stay_off_catalog() -> None:
    document = json.loads(
        (ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    dumped = json.dumps(document)
    assert "cross-art-synthesis-view/v1" not in dumped
    comparison_kinds = {
        "source_bound_corroboration",
        "source_disagreement_retained",
        "missing_art",
        "insufficient_arts",
    }
    for path in LIVE_VIEWS:
        live = json.loads(path.read_text(encoding="utf-8"))
        dumped_live = json.dumps(live)
        assert "cross-art-synthesis-view/v1" not in dumped_live
        row = live["$defs"]["comparisonRow"]
        assert row["required"] == [
            "arts",
            "kind",
            "display_text",
            "fact_refs",
            "source_rule_id",
        ]
        assert set(row["properties"]["kind"]["enum"]) == comparison_kinds
        dimension = live["$defs"]["dimension"]["properties"]
        assert dimension["convergence"]["items"] == {"$ref": "#/$defs/comparisonRow"}
        assert dimension["disagreements"]["items"] == {"$ref": "#/$defs/comparisonRow"}
        assert list(
            Draft202012Validator(live).iter_errors(
                {
                    "schema_version": live["properties"]["schema_version"]["const"],
                    "subject_ref": "sid-0123456789abcdef0123456789abcdef",
                    **(
                        {"question": "同一问题"}
                        if "question" in live["properties"]
                        else {}
                    ),
                    "selected_art_ids": (
                        ["liuyao", "qimen", "daliuren"]
                        if path.name.startswith("wenshi")
                        else ["bazi", "ziwei"]
                    ),
                    "dimensions": [
                        {
                            "dimension_id": "career",
                            "signals": [],
                            "convergence": ["两术一致"],
                            "disagreements": [],
                            "missing_art_ids": [],
                        }
                    ],
                }
            )
        )
    catalog = ROOT / "core" / "mingli-master" / "resources" / "runtime" / "catalog-v1.json"
    catalog_text = catalog.read_text(encoding="utf-8")
    assert "cross-art-synthesis" not in catalog_text
