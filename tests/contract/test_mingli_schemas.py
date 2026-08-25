import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "contracts" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    assert path.is_file(), f"missing frozen contract: {path}"

    from jsonschema import Draft202012Validator

    with path.open(encoding="utf-8") as stream:
        schema: dict[str, Any] = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture
def validate_schema() -> Callable[[str, object], None]:
    def validate(name: str, payload: object) -> None:
        schema = load_schema(name)
        from jsonschema import Draft202012Validator, FormatChecker

        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(payload)

    return validate


@pytest.fixture
def reject_schema() -> Callable[[str, object], None]:
    def reject(name: str, payload: object) -> None:
        schema = load_schema(name)
        from jsonschema import Draft202012Validator, FormatChecker

        errors = tuple(
            Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            ).iter_errors(payload)
        )
        assert errors, f"payload unexpectedly matched {name}"

    return reject


def prepare_command() -> dict[str, Any]:
    return {
        "kind": "prepare",
        "query": "看一下这个八字",
        "intent": {
            "subject_refs": ["profile-version:test"],
            "object_id": "natal",
            "dimension_ids": ["overview"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        "facts": {
            "profile-version:test": {
                "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00"
            }
        },
        "state_token": None,
        "transition": None,
    }


def reading_brief() -> dict[str, Any]:
    return {
        "question": "事业上最该先抓住哪条主线？",
        "vocabulary": [
            {"id": "career", "label": "事业", "description": None}
        ],
        "facts": [
            {
                "ref": "fact:day-master",
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": {"day_master": "甲"},
                "display_text": "日主为甲木。",
            }
        ],
        "evidence": [
            {
                "ref": "evidence:book-1",
                "source_title": "公开古籍",
                "locator": "卷一",
                "excerpt": "示例节录",
                "supports_fact_refs": ["fact:day-master"],
            }
        ],
        "findings": [
            {
                "ref": "finding:career-1",
                "subject_ref": "profile-version:test",
                "dimension_ids": ["career"],
                "kind_id": "kind.tendency",
                "data": {"summary": "适合持续积累"},
                "fact_refs": ["fact:day-master"],
                "evidence_refs": ["evidence:book-1"],
                "limit_kind_ids": ["limit:traditional-culture"],
                "support_mode": "exact",
            }
        ],
        "claim_scopes": [
            {
                "subject_ref": "profile-version:test",
                "dimension_id": "career",
                "allowed_kind_ids": ["kind.tendency"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:day-master"],
                "evidence_refs": ["evidence:book-1"],
            }
        ],
        "limits": [
            {
                "kind_id": "limit:traditional-culture",
                "public_text": "内容仅供传统文化研究与个人参考。",
                "scope_refs": ["profile-version:test"],
                "detail_ids": [],
            }
        ],
        "prior_answer": None,
        "request_view": {
            "subject_refs": ["profile-version:test"],
            "capability_ids": ["bazi"],
            "object_id": "natal",
            "dimension_ids": ["career"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
        },
    }


def candidate() -> dict[str, Any]:
    return {
        "schema_version": "mingli-narrative-candidate-v1",
        "blocks": [
            {
                "block_id": "b1",
                "block_type": "claim",
                "text": "事业主线更适合先抓住可持续积累。",
                "subject_ref": "profile-version:test",
                "dimension_id": "career",
                "claim_kind_id": "kind.tendency",
                "certainty_id": "certainty.tendency",
                "fact_refs": ["fact:day-master"],
                "finding_refs": ["finding:career-1"],
                "evidence_refs": ["evidence:book-1"],
                "limit_kind_ids": ["limit:traditional-culture"],
            }
        ],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "describe"},
        prepare_command(),
        {
            "kind": "complete",
            "state_token": "fake-opaque-state",
            "public_copy": "这是一份已经通过网站 Guard 的正文。",
        },
    ],
    ids=("describe", "prepare", "complete"),
)
def test_command_union_contains_exactly_three_public_kinds(
    validate_schema: Callable[[str, object], None],
    payload: dict[str, Any],
) -> None:
    validate_schema("mingli-command-v2.schema.json", payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "kind": "described",
            "protocol_version": "mingli-portable-interface-v2",
            "manifest_digest": "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342",
            "capabilities": [
                {
                    "id": "bazi",
                    "label": "八字",
                    "description": "本命事实能力",
                    "objects": [
                        {"id": "natal", "label": "本命", "description": None}
                    ],
                    "horizons": [
                        {"id": "life", "label": "长期", "description": None}
                    ],
                    "dimensions": [
                        {"id": "career", "label": "事业", "description": None}
                    ],
                    "default_dimension_ids": ["career"],
                    "input_fields": [
                        {
                            "id": "birth_datetime_or_four_pillars",
                            "label": "出生时间或四柱",
                            "type_id": "text",
                            "description": None,
                            "choices": [],
                        }
                    ],
                    "required_input_groups": [["birth_datetime_or_four_pillars"]],
                    "time_semantics": {
                        "role_id": "birth",
                        "supported_policy_ids": ["civil"],
                        "default_policy_id": "civil",
                        "coordinate_required_policy_ids": [],
                        "unsupported_behavior_id": "stop",
                    },
                }
            ],
        },
        {
            "kind": "prepared",
            "state_token": "fake-opaque-state",
            "brief": reading_brief(),
        },
        {
            "kind": "accepted",
            "state_token": "fake-opaque-state",
            "public_copy": "事业主线更适合先抓住可持续积累。",
        },
        {
            "kind": "stopped",
            "reason": "need_input",
            "public_copy": "还需要确认出生时间。",
            "state_token": "fake-opaque-state",
            "input_request": {
                "requirements": [
                    {
                        "any_of": [
                            {
                                "id": "birth_datetime_or_four_pillars",
                                "label": "出生时间或四柱",
                                "type_id": "text",
                                "description": None,
                                "choices": [],
                            }
                        ]
                    }
                ]
            },
        },
    ],
    ids=("described", "prepared", "accepted", "stopped"),
)
def test_result_union_contains_exactly_four_public_kinds(
    validate_schema: Callable[[str, object], None],
    payload: dict[str, Any],
) -> None:
    validate_schema("mingli-result-v2.schema.json", payload)


def test_prepare_facts_are_grouped_by_subject(
    validate_schema: Callable[[str, object], None],
    reject_schema: Callable[[str, object], None],
) -> None:
    validate_schema("mingli-command-v2.schema.json", prepare_command())
    malformed = prepare_command()
    malformed["facts"] = {
        "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00"
    }
    reject_schema("mingli-command-v2.schema.json", malformed)


def test_candidate_blocks_require_the_full_trace_contract(
    validate_schema: Callable[[str, object], None],
    reject_schema: Callable[[str, object], None],
) -> None:
    payload = candidate()
    validate_schema("mingli-narrative-candidate-v1.schema.json", payload)

    required_trace_fields = (
        "block_id",
        "text",
        "subject_ref",
        "dimension_id",
        "claim_kind_id",
        "certainty_id",
        "fact_refs",
        "finding_refs",
        "evidence_refs",
        "limit_kind_ids",
    )
    for field in required_trace_fields:
        malformed = copy.deepcopy(payload)
        malformed["blocks"][0].pop(field)
        reject_schema("mingli-narrative-candidate-v1.schema.json", malformed)


def test_candidate_rejects_business_acceptance_and_extra_fields(
    reject_schema: Callable[[str, object], None],
) -> None:
    payload = candidate()
    payload["accepted"] = False
    reject_schema("mingli-narrative-candidate-v1.schema.json", payload)


def test_output_contract_is_versioned_and_closed(
    validate_schema: Callable[[str, object], None],
    reject_schema: Callable[[str, object], None],
) -> None:
    payload = {
        "schema_version": "mingli-output-contract-v1",
        "contract_id": "preview-v1",
        "language": "zh-CN",
        "min_blocks": 1,
        "max_blocks": 4,
        "max_output_chars": 1200,
        "required_dimension_ids": ["overview"],
        "required_limit_kind_ids": ["limit:traditional-culture"],
        "disclosure_text": "本内容由 AI 辅助生成，仅供传统文化参考。",
    }
    validate_schema("mingli-output-contract-v1.schema.json", payload)

    payload["agent_tools"] = ["web_search"]
    reject_schema("mingli-output-contract-v1.schema.json", payload)


def property_names(schema: object) -> set[str]:
    if isinstance(schema, dict):
        names = set(schema.get("properties", {}))
        return names | set().union(*(property_names(value) for value in schema.values()))
    if isinstance(schema, list):
        return set().union(*(property_names(value) for value in schema))
    return set()


def test_state_token_exists_only_in_runtime_protocol_schemas() -> None:
    command_fields = property_names(load_schema("mingli-command-v2.schema.json"))
    result_fields = property_names(load_schema("mingli-result-v2.schema.json"))
    candidate_fields = property_names(
        load_schema("mingli-narrative-candidate-v1.schema.json")
    )
    output_fields = property_names(load_schema("mingli-output-contract-v1.schema.json"))

    assert "state_token" in command_fields
    assert "state_token" in result_fields
    assert "state_token" not in candidate_fields
    assert "state_token" not in output_fields


def test_daliuren_chart_schema_rejects_transmission_method_alias(
    reject_schema: Callable[[str, object], None],
) -> None:
    payload = {
        "schema_version": "daliuren-chart/v1",
        "subject_ref": "fixture:probe",
        "question": "fixture question",
        "lessons": [
            {"lesson_id": "1", "upper": "辰", "lower": "庚"},
            {"lesson_id": "2", "upper": "子", "lower": "辰"},
            {"lesson_id": "3", "upper": "辰", "lower": "申"},
            {"lesson_id": "4", "upper": "子", "lower": "辰"},
        ],
        "transmissions": [
            {"stage": "initial", "branch": "子", "general": "青龙"},
            {"stage": "middle", "branch": "申", "general": "腾蛇"},
            {"stage": "final", "branch": "辰", "general": "玄武"},
        ],
        "core_facts": {
            "transmission_method": {"primary": "伏吟"},
        },
    }
    reject_schema("views/daliuren-chart-v1.schema.json", payload)


def test_daliuren_chart_schema_accepts_only_typed_source_pattern_fields(
    validate_schema: Callable[[str, object], None],
    reject_schema: Callable[[str, object], None],
) -> None:
    payload = {
        "schema_version": "daliuren-chart/v1",
        "subject_ref": "fixture:probe",
        "question": "fixture question",
        "lessons": [
            {"lesson_id": "1", "upper": "辰", "lower": "庚"},
            {"lesson_id": "2", "upper": "子", "lower": "辰"},
            {"lesson_id": "3", "upper": "辰", "lower": "申"},
            {"lesson_id": "4", "upper": "子", "lower": "辰"},
        ],
        "transmissions": [
            {"stage": "initial", "branch": "子", "general": "青龙"},
            {"stage": "middle", "branch": "申", "general": "腾蛇"},
            {"stage": "final", "branch": "辰", "general": "玄武"},
        ],
        "core_facts": {
            "structural_patterns": ["伏吟"],
            "source_conditioned_patterns": [
                {
                    "rule_id": "DLR-09",
                    "local_rule_id": "liuren.structural.fuyin",
                    "title": "伏吟",
                    "source_pack": "san-shi/daliuren-daquan",
                    "source_anchor": "fulltext.md#L7696",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": [
                        "fact:/chart_facts/output/structural_patterns/0"
                    ],
                    "predicate_audit": [
                        "/chart_facts/output/structural_patterns/0:eq:伏吟"
                    ],
                    "source_dependency_id": (
                        "liuren.source-conditioned-structural-patterns-v1"
                    ),
                }
            ],
        },
    }

    validate_schema("views/daliuren-chart-v1.schema.json", payload)

    for rule_id, local_rule_id, title, source_anchor in (
        (
            "DLR-08",
            "liuren.structural.bazhuan-day",
            "八专日",
            "fulltext.md#L7556",
        ),
        (
            "DLR-10",
            "liuren.structural.fanyin",
            "反吟",
            "fulltext.md#L7874",
        ),
    ):
        rule_payload = copy.deepcopy(payload)
        rule_payload["core_facts"]["structural_patterns"] = [title]
        rule_pattern = rule_payload["core_facts"]["source_conditioned_patterns"][0]
        rule_pattern.update(
            {
                "rule_id": rule_id,
                "local_rule_id": local_rule_id,
                "title": title,
                "source_anchor": source_anchor,
                "predicate_audit": [
                    f"/chart_facts/output/structural_patterns/0:eq:{title}"
                ],
            }
        )
        validate_schema("views/daliuren-chart-v1.schema.json", rule_payload)

    second_index_payload = copy.deepcopy(payload)
    second_index_payload["core_facts"]["structural_patterns"] = ["未映射课体", "伏吟"]
    second_index_pattern = second_index_payload["core_facts"][
        "source_conditioned_patterns"
    ][0]
    second_index_pattern["fact_paths"] = [
        "fact:/chart_facts/output/structural_patterns/1"
    ]
    second_index_pattern["predicate_audit"] = [
        "/chart_facts/output/structural_patterns/1:eq:伏吟"
    ]
    validate_schema("views/daliuren-chart-v1.schema.json", second_index_payload)

    mismatched_structural_title = copy.deepcopy(payload)
    mismatched_structural_title["core_facts"]["structural_patterns"][0] = "反吟"
    reject_schema(
        "views/daliuren-chart-v1.schema.json", mismatched_structural_title
    )

    out_of_bounds_structural_index = copy.deepcopy(payload)
    out_of_bounds_pattern = out_of_bounds_structural_index["core_facts"][
        "source_conditioned_patterns"
    ][0]
    out_of_bounds_pattern["fact_paths"] = [
        "fact:/chart_facts/output/structural_patterns/3"
    ]
    out_of_bounds_pattern["predicate_audit"] = [
        "/chart_facts/output/structural_patterns/3:eq:伏吟"
    ]
    reject_schema(
        "views/daliuren-chart-v1.schema.json", out_of_bounds_structural_index
    )

    private_fact_path = copy.deepcopy(payload)
    private_fact_path["core_facts"]["source_conditioned_patterns"][0][
        "fact_paths"
    ] = ["fact:/chart_facts/input/question"]
    reject_schema("views/daliuren-chart-v1.schema.json", private_fact_path)

    unrelated_predicate_audit = copy.deepcopy(payload)
    unrelated_predicate_audit["core_facts"]["source_conditioned_patterns"][0][
        "predicate_audit"
    ] = ["/unrelated:eq:伏吟"]
    reject_schema("views/daliuren-chart-v1.schema.json", unrelated_predicate_audit)

    forged_provenance = copy.deepcopy(payload)
    forged_pattern = forged_provenance["core_facts"][
        "source_conditioned_patterns"
    ][0]
    forged_pattern["fact_paths"] = ["fact:/chart_facts/input/question"]
    forged_pattern["predicate_audit"] = ["/unrelated:eq:伏吟"]
    reject_schema("views/daliuren-chart-v1.schema.json", forged_provenance)

    mismatched_path_audit_index = copy.deepcopy(payload)
    mismatched_path_audit_index["core_facts"]["source_conditioned_patterns"][0][
        "fact_paths"
    ] = ["fact:/chart_facts/output/structural_patterns/1"]
    reject_schema("views/daliuren-chart-v1.schema.json", mismatched_path_audit_index)

    incomplete_four_lessons = copy.deepcopy(payload)
    incomplete_four_lessons["lessons"][2]["upper"] = "寅"
    incomplete_four_lessons["core_facts"]["structural_patterns"] = ["四课不备"]
    incomplete_pattern = incomplete_four_lessons["core_facts"][
        "source_conditioned_patterns"
    ][0]
    incomplete_pattern.update(
        {
            "rule_id": "DLR-S01",
            "local_rule_id": "liuren.structural.incomplete-four-lessons",
            "title": "四课不备",
            "source_anchor": "fulltext.md#L58",
            "fact_paths": [
                "fact:/chart_facts/output/structural_patterns/0",
                "fact:/chart_facts/output/four_lessons/0/upper",
                "fact:/chart_facts/output/four_lessons/1/upper",
                "fact:/chart_facts/output/four_lessons/2/upper",
                "fact:/chart_facts/output/four_lessons/3/upper",
            ],
            "predicate_audit": [
                "/chart_facts/output/structural_patterns/0:eq:四课不备",
                "/chart_facts/output/four_lessons/*/upper:distinct_count_eq:3",
            ],
        }
    )
    validate_schema("views/daliuren-chart-v1.schema.json", incomplete_four_lessons)

    forged_incomplete_four_lessons_audit = copy.deepcopy(incomplete_four_lessons)
    for lesson, upper in zip(
        forged_incomplete_four_lessons_audit["lessons"],
        ("子", "丑", "寅", "卯"),
        strict=True,
    ):
        lesson["upper"] = upper
    reject_schema(
        "views/daliuren-chart-v1.schema.json",
        forged_incomplete_four_lessons_audit,
    )

    missing_four_lesson_provenance = copy.deepcopy(incomplete_four_lessons)
    missing_pattern = missing_four_lesson_provenance["core_facts"][
        "source_conditioned_patterns"
    ][0]
    missing_pattern["fact_paths"] = [
        "fact:/chart_facts/output/structural_patterns/0"
    ]
    missing_pattern["predicate_audit"] = [
        "/chart_facts/output/structural_patterns/0:eq:四课不备"
    ]
    reject_schema(
        "views/daliuren-chart-v1.schema.json", missing_four_lesson_provenance
    )

    mismatched_identity = copy.deepcopy(payload)
    mismatched_identity["core_facts"]["source_conditioned_patterns"][0][
        "local_rule_id"
    ] = "liuren.structural.fanyin"
    reject_schema("views/daliuren-chart-v1.schema.json", mismatched_identity)

    duplicate_identity = copy.deepcopy(payload)
    repeated_pattern = copy.deepcopy(
        duplicate_identity["core_facts"]["source_conditioned_patterns"][0]
    )
    repeated_pattern["predicate_audit"].append("/audit:second-valid-string")
    duplicate_identity["core_facts"]["source_conditioned_patterns"].append(
        repeated_pattern
    )
    reject_schema("views/daliuren-chart-v1.schema.json", duplicate_identity)

    unknown_field = copy.deepcopy(payload)
    unknown_field["core_facts"]["source_conditioned_patterns"][0][
        "verdict"
    ] = "forged"
    reject_schema("views/daliuren-chart-v1.schema.json", unknown_field)

    out_of_range_index = copy.deepcopy(payload)
    out_of_range_index["core_facts"]["source_conditioned_patterns"][0][
        "fact_paths"
    ] = ["fact:/chart_facts/output/structural_patterns/4"]
    out_of_range_index["core_facts"]["source_conditioned_patterns"][0][
        "predicate_audit"
    ] = ["/chart_facts/output/structural_patterns/4:eq:伏吟"]
    reject_schema("views/daliuren-chart-v1.schema.json", out_of_range_index)

    duplicate_structural_title = copy.deepcopy(payload)
    duplicate_structural_title["core_facts"]["structural_patterns"] = [
        "伏吟",
        "伏吟",
    ]
    reject_schema("views/daliuren-chart-v1.schema.json", duplicate_structural_title)

    forged_old_dlr07 = copy.deepcopy(incomplete_four_lessons)
    forged_old_dlr07["core_facts"]["source_conditioned_patterns"][0][
        "rule_id"
    ] = "DLR-07"
    reject_schema("views/daliuren-chart-v1.schema.json", forged_old_dlr07)
