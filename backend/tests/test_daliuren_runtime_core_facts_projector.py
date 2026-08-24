from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.charts.contracts import (
    DaliurenChartV1,
    DaliurenCoreFacts,
    DaliurenSourcePattern,
)
from app.charts.projectors import project_daliuren_view_model
from jsonschema import Draft202012Validator

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "liuren-runtime-core-facts-v1.json"
)
SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "schemas"
    / "views"
    / "daliuren-chart-v1.schema.json"
)
CORE_SCRIPTS_PATH = (
    Path(__file__).resolve().parents[2]
    / "core"
    / "mingli-master"
    / "scripts"
)


def _runtime_core_brief(runtime_core_facts: dict[str, object]) -> dict[str, object]:
    return {
        "question": "fixture question",
        "facts": [
            {
                "ref": "fact:calculated/liuren/runtime_core_facts",
                "subject_ref": "fixture:probe",
                "kind_id": "kind.fact",
                "value": runtime_core_facts,
                "display_text": "runtime_core_facts",
            }
        ],
        "request_view": {
            "subject_refs": ["fixture:probe"],
            "capability_ids": ["liuren"],
        },
    }


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_runtime_rejects(
    runtime_core_facts: dict[str, object],
    expected_error: str,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys\n"
                "from reading_engine.liuren_contract import (\n"
                "    LiurenRuntimeContractError, validate_runtime_core_facts,\n"
                ")\n"
                "try:\n"
                "    validate_runtime_core_facts(json.load(sys.stdin))\n"
                "except LiurenRuntimeContractError as exc:\n"
                "    print(exc)\n"
                "else:\n"
                "    raise AssertionError('Runtime accepted invalid core facts')\n"
            ),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "PYTHONPATH": str(CORE_SCRIPTS_PATH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
        },
        input=json.dumps(runtime_core_facts),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert expected_error in result.stdout


def _assert_runtime_accepts(runtime_core_facts: dict[str, object]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys\n"
                "from reading_engine.liuren_contract import "
                "validate_runtime_core_facts\n"
                "validate_runtime_core_facts(json.load(sys.stdin))\n"
            ),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "PYTHONPATH": str(CORE_SCRIPTS_PATH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
        },
        input=json.dumps(runtime_core_facts),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _state_dimension(
    payload: dict[str, object],
    correspondence: dict[str, object],
) -> dict[str, object]:
    return {
        "requested_dimension": "state",
        "canonical_dimension": "state",
        "status": "calculated_facts_not_verdict",
        "source_rule_ids": [],
        "rule_evidence": copy.deepcopy(
            payload["dimension_facts"]["relationship"]["rule_evidence"]
        ),
        "stage_status": [
            {
                "branch": "酉",
                "heavenly_general": "天空",
                "is_xunkong": False,
                "season_strength": "休",
                "six_relative": "兄弟",
                "stage": "initial",
            }
        ],
        "general_landing_correspondences": [correspondence],
    }


def _payload_with_state_work_money_dimensions() -> dict[str, object]:
    payload = copy.deepcopy(_load_fixture())
    relationship = payload["dimension_facts"]["relationship"]
    rule_evidence = relationship["rule_evidence"]
    stage_status = {
        "branch": "辰",
        "heavenly_general": "青龙",
        "is_xunkong": False,
        "season_strength": "旺",
        "six_relative": "妻财",
        "stage": "initial",
    }
    general_landing = {
        "stage": "initial",
        "heavenly_general": "青龙",
        "landing_branch": "辰",
        "source_pack": "san-shi/liuren-miben",
        "source_rule": "LM-R01",
        "role": "source_bound_correspondence",
        "status": "source_correspondence_matched",
        "source_text": "fixture source text",
        "source_anchor": "fulltext.md#fixture",
    }
    general_modifier = {**general_landing, "six_relative": "妻财"}

    payload["dimension_facts"].update(
        {
            "state": {
                "requested_dimension": "state",
                "canonical_dimension": "state",
                "status": "calculated_facts_not_verdict",
                "source_rule_ids": [],
                "rule_evidence": copy.deepcopy(rule_evidence),
                "stage_status": [copy.deepcopy(stage_status)],
                "general_landing_correspondences": [
                    copy.deepcopy(general_landing)
                ],
            },
            "work": {
                "requested_dimension": "work",
                "canonical_dimension": "work",
                "status": "calculated_facts_not_verdict",
                "source_rule_ids": [],
                "rule_evidence": copy.deepcopy(rule_evidence),
                "six_relative_stages": copy.deepcopy(
                    relationship["six_relative_stages"]
                ),
                "stage_status": [copy.deepcopy(stage_status)],
                "subject_object_relation": copy.deepcopy(
                    relationship["subject_object_relation"]
                ),
                "target_relative": "妻财",
                "target_contract_status": "bound",
                "target_presence": True,
                "target_strength": [
                    {
                        "stage": "initial",
                        "branch": "辰",
                        "six_relative": "妻财",
                        "season_strength": "旺",
                        "is_xunkong": False,
                    }
                ],
                "target_general_modifier": [copy.deepcopy(general_modifier)],
            },
            "money": {
                "requested_dimension": "money",
                "canonical_dimension": "money",
                "status": "calculated_facts_not_verdict",
                "source_rule_ids": [],
                "rule_evidence": copy.deepcopy(rule_evidence),
                "wealth_presence": True,
                "wealth_stage_strength": [
                    {
                        "stage": "initial",
                        "branch": "辰",
                        "six_relative": "妻财",
                        "season_strength": "旺",
                    }
                ],
                "wealth_void_status": [
                    {
                        "stage": "initial",
                        "branch": "辰",
                        "six_relative": "妻财",
                        "is_xunkong": False,
                    }
                ],
                "wealth_general_modifier": [copy.deepcopy(general_modifier)],
            },
        }
    )
    return payload


_MING17_SOURCE_PATTERNS = {
    "四课不备": (
        "DLR-07",
        "liuren.structural.incomplete-four-lessons",
        "fulltext.md#L58",
    ),
    "八专日": (
        "DLR-08",
        "liuren.structural.bazhuan-day",
        "fulltext.md#L7556",
    ),
    "伏吟": ("DLR-09", "liuren.structural.fuyin", "fulltext.md#L7696"),
    "反吟": ("DLR-10", "liuren.structural.fanyin", "fulltext.md#L7874"),
}


def _source_pattern(title: str) -> dict[str, object]:
    rule_id, local_rule_id, source_anchor = _MING17_SOURCE_PATTERNS[title]
    return {
        "rule_id": rule_id,
        "local_rule_id": local_rule_id,
        "title": title,
        "source_pack": "san-shi/daliuren-daquan",
        "source_anchor": source_anchor,
        "status": "predicate_matched_not_verdict",
        "fact_paths": ["fact:/chart_facts/output/structural_patterns/0"],
        "predicate_audit": [f"/chart_facts/output/structural_patterns/0:eq:{title}"],
        "source_dependency_id": "liuren.source-conditioned-structural-patterns-v1",
    }


def test_daliuren_projector_maps_ming11_runtime_core_facts_fixture() -> None:
    view_model = project_daliuren_view_model(_runtime_core_brief(_load_fixture()))

    assert isinstance(view_model, DaliurenChartV1)
    assert [item.lesson_id for item in view_model.lessons] == ["1", "2", "3", "4"]
    assert [item.upper for item in view_model.lessons] == ["辰", "辰", "酉", "酉"]
    assert [item.general for item in view_model.transmissions] == ["勾陈", "天后", "青龙"]

    core_facts = view_model.core_facts
    assert core_facts is not None
    assert core_facts.day_hour is not None
    assert core_facts.day_hour.day == "乙酉"
    assert core_facts.month_general is not None
    assert core_facts.month_general.name == "小吉"
    assert core_facts.noble_person is not None
    assert core_facts.noble_person.direction == "reverse"
    assert core_facts.lesson_method is not None
    assert core_facts.lesson_method.primary == "伏吟"
    assert core_facts.lesson_method.use_method == "伏吟有克/重审"
    assert core_facts.earth_plate is not None
    assert len(core_facts.earth_plate) == 12
    assert core_facts.heaven_plate is not None
    assert len(core_facts.heaven_plate) == 12
    assert core_facts.heavenly_generals is not None
    assert len(core_facts.heavenly_generals) == 12
    assert core_facts.structural_patterns == ("伏吟", "四课不备")
    assert [
        item.model_dump(mode="json")
        for item in core_facts.source_conditioned_patterns
    ] == [_source_pattern("伏吟")]
    assert core_facts.plate_offset == 0
    assert core_facts.xunkong is not None
    assert core_facts.xunkong.xun == "甲申"

    assert core_facts.dimension_facts is not None
    assert tuple(core_facts.dimension_facts) == ("relationship", "timing")
    relationship = core_facts.dimension_facts["relationship"]
    assert relationship.rule_evidence.hard_verdict is None
    assert relationship.rule_evidence.requires_school_adjudication is True
    assert relationship.subject_object_relation is not None
    assert relationship.subject_object_relation.relation == "object_overcomes_subject"

    timing = core_facts.dimension_facts["timing"]
    assert timing.relative_speed == "relatively_faster"
    assert timing.candidate_date is not None
    assert timing.candidate_date.solar_date == "2026-07-20"
    assert timing.rule_evidence.matched[0].rule_id == "LM-R21"

    assert core_facts.timing_candidates is not None
    assert core_facts.timing_candidates[0].source_rule == "LM-R21"
    assert core_facts.timing_candidates[0].candidate_not_guarantee is True

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


@pytest.mark.parametrize("title", _MING17_SOURCE_PATTERNS)
def test_daliuren_projector_projects_each_ming17_source_pattern(title: str) -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["structural_patterns"] = [title]
    payload["source_conditioned_patterns"] = [_source_pattern(title)]
    if title == "四课不备":
        payload["four_lessons"] = [
            {"lesson": 1, "upper": "子", "lower": "庚"},
            {"lesson": 2, "upper": "丑", "lower": "辰"},
            {"lesson": 3, "upper": "寅", "lower": "申"},
            {"lesson": 4, "upper": "子", "lower": "辰"},
        ]
        payload["source_conditioned_patterns"][0]["fact_paths"] = [
            "fact:/chart_facts/output/structural_patterns/0",
            "fact:/chart_facts/output/four_lessons/0/upper",
            "fact:/chart_facts/output/four_lessons/1/upper",
            "fact:/chart_facts/output/four_lessons/2/upper",
            "fact:/chart_facts/output/four_lessons/3/upper",
        ]
        payload["source_conditioned_patterns"][0]["predicate_audit"].append(
            "/chart_facts/output/four_lessons/*/upper:distinct_count_eq:3"
        )

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert [item.title for item in view_model.core_facts.source_conditioned_patterns] == [
        title
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.pop("source_conditioned_patterns"),
        lambda payload: payload.__setitem__("source_conditioned_patterns", "wrong-type"),
        lambda payload: payload["source_conditioned_patterns"][0].__setitem__(
            "untrusted", "raw-json"
        ),
        lambda payload: payload["source_conditioned_patterns"][0].__setitem__(
            "source_anchor", "fulltext.md#L0"
        ),
    ],
    ids=("missing", "wrong-type", "unknown-key", "forged-anchor"),
)
def test_daliuren_projector_fail_closes_only_invalid_source_pattern_block(
    mutate: object,
) -> None:
    payload = copy.deepcopy(_load_fixture())
    assert callable(mutate)
    mutate(payload)

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.structural_patterns == ("伏吟", "四课不备")
    assert view_model.core_facts.source_conditioned_patterns == ()


def test_daliuren_projector_fail_closes_incomplete_four_lessons_source() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["structural_patterns"] = ["四课不备"]
    payload["source_conditioned_patterns"] = [_source_pattern("四课不备")]

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.source_conditioned_patterns == ()


def test_daliuren_projector_fail_closes_unbound_source_provenance() -> None:
    unrelated_audit = copy.deepcopy(_load_fixture())
    unrelated_audit["source_conditioned_patterns"][0]["predicate_audit"] = [
        "/unrelated:eq:伏吟"
    ]

    mismatched_structural_index = copy.deepcopy(_load_fixture())
    mismatched_structural_index["structural_patterns"] = ["八专日", "伏吟"]
    mismatched_structural_index["source_conditioned_patterns"] = [
        _source_pattern("伏吟")
    ]
    mismatched_structural_index["source_conditioned_patterns"][0]["fact_paths"] = [
        "fact:/chart_facts/output/structural_patterns/1"
    ]

    private_input_path = copy.deepcopy(_load_fixture())
    private_input_path["source_conditioned_patterns"][0]["fact_paths"].append(
        "fact:/chart_facts/input/question"
    )

    incomplete_four_lessons_paths = copy.deepcopy(_load_fixture())
    incomplete_four_lessons_paths["structural_patterns"] = ["四课不备"]
    incomplete_four_lessons_paths["four_lessons"] = [
        {"lesson": 1, "upper": "子", "lower": "庚"},
        {"lesson": 2, "upper": "丑", "lower": "辰"},
        {"lesson": 3, "upper": "寅", "lower": "申"},
        {"lesson": 4, "upper": "子", "lower": "辰"},
    ]
    incomplete_four_lessons_paths["source_conditioned_patterns"] = [
        _source_pattern("四课不备")
    ]
    incomplete_four_lessons_paths["source_conditioned_patterns"][0][
        "predicate_audit"
    ].append("/chart_facts/output/four_lessons/*/upper:distinct_count_eq:3")

    for payload in (
        unrelated_audit,
        mismatched_structural_index,
        private_input_path,
        incomplete_four_lessons_paths,
    ):
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1)
        assert view_model.core_facts is not None
        assert view_model.core_facts.source_conditioned_patterns == ()


def test_daliuren_contract_rejects_mismatched_or_duplicate_source_identity() -> None:
    mismatched_identity = _source_pattern("伏吟")
    mismatched_identity["local_rule_id"] = "liuren.structural.fanyin"

    with pytest.raises(ValueError, match="identity fields must match"):
        DaliurenSourcePattern.model_validate(mismatched_identity)

    view_model = project_daliuren_view_model(_runtime_core_brief(_load_fixture()))
    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    duplicate_identity = view_model.core_facts.model_dump(mode="json")
    duplicate_identity["source_conditioned_patterns"].append(
        copy.deepcopy(duplicate_identity["source_conditioned_patterns"][0])
    )

    with pytest.raises(ValueError, match="identities must be unique"):
        DaliurenCoreFacts.model_validate(duplicate_identity)


def test_daliuren_projector_fail_closed_without_runtime_core_facts() -> None:
    legacy_brief = {
        "question": "fixture question",
        "facts": [
            {
                "ref": "fact:calculated/liuren/four_lessons",
                "subject_ref": "fixture:probe",
                "kind_id": "kind.fact",
                "value": [{"lesson": 1, "upper": "辰", "lower": "庚"}],
                "display_text": "four_lessons",
            }
        ],
        "request_view": {
            "subject_refs": ["fixture:probe"],
            "capability_ids": ["liuren"],
        },
    }

    assert project_daliuren_view_model(legacy_brief) is None


def test_daliuren_projector_fail_closed_on_wrong_schema_version() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["schema_version"] = "mingli-liuren-runtime-core-facts-v0"

    assert project_daliuren_view_model(_runtime_core_brief(payload)) is None


def test_daliuren_projector_rejects_unknown_or_malformed_runtime_envelope_fields() -> None:
    unknown_envelope_field = copy.deepcopy(_load_fixture())
    unknown_envelope_field["internal_trace"] = {"runtime": "private"}

    malformed_optional_field = copy.deepcopy(_load_fixture())
    malformed_optional_field["timing_candidates"] = {"not": "an array"}

    for payload in (unknown_envelope_field, malformed_optional_field):
        assert project_daliuren_view_model(_runtime_core_brief(payload)) is None


def test_daliuren_projector_preserves_empty_runtime_arrays() -> None:
    omitted_payload = copy.deepcopy(_load_fixture())
    omitted_payload.pop("timing_candidates")
    omitted_view = project_daliuren_view_model(_runtime_core_brief(omitted_payload))

    empty_payload = copy.deepcopy(_load_fixture())
    empty_payload["timing_candidates"] = []
    empty_view = project_daliuren_view_model(_runtime_core_brief(empty_payload))

    empty_patterns_payload = copy.deepcopy(_load_fixture())
    empty_patterns_payload["structural_patterns"] = []
    empty_patterns_view = project_daliuren_view_model(
        _runtime_core_brief(empty_patterns_payload)
    )

    assert isinstance(omitted_view, DaliurenChartV1)
    assert omitted_view.core_facts is not None
    assert omitted_view.core_facts.timing_candidates is None
    assert isinstance(empty_view, DaliurenChartV1)
    assert empty_view.core_facts is not None
    assert empty_view.core_facts.timing_candidates == ()
    assert isinstance(empty_patterns_view, DaliurenChartV1)
    assert empty_patterns_view.core_facts is not None
    assert empty_patterns_view.core_facts.structural_patterns == ()


def test_daliuren_projector_rejects_empty_structural_pattern_entries() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["structural_patterns"] = [""]

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["structural_patterns"] = [""]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_preserves_missing_source_correspondence_shape() -> None:
    correspondence = {
        "stage": "initial",
        "heavenly_general": "天空",
        "landing_branch": "酉",
        "source_pack": "san-shi/liuren-miben",
        "source_rule": "LM-R01",
        "role": "imagery_correspondence_not_observed_activity",
        "status": "no_exact_source_correspondence",
    }
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["state"] = _state_dimension(
        payload,
        correspondence,
    )

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.dimension_facts is not None
    state = view_model.core_facts.dimension_facts["state"]
    assert state.general_landing_correspondences is not None
    assert state.general_landing_correspondences[0].source_anchor is None
    serialized = view_model.model_dump(mode="json")
    serialized_correspondence = serialized["core_facts"]["dimension_facts"][
        "state"
    ]["general_landing_correspondences"][0]
    assert "source_anchor" not in serialized_correspondence
    assert "source_text" not in serialized_correspondence

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(serialized)


def test_daliuren_projector_enforces_status_specific_source_fields() -> None:
    common_fields = {
        "stage": "initial",
        "heavenly_general": "天空",
        "landing_branch": "酉",
        "source_pack": "san-shi/liuren-miben",
        "source_rule": "LM-R01",
        "role": "imagery_correspondence_not_observed_activity",
    }
    invalid_correspondences = (
        {
            **common_fields,
            "source_anchor": "fulltext.md#forged",
            "source_text": "forged",
            "status": "no_exact_source_correspondence",
        },
        {
            **common_fields,
            "status": "source_correspondence_matched",
        },
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    for correspondence in invalid_correspondences:
        payload = copy.deepcopy(_load_fixture())
        payload["dimension_facts"]["state"] = _state_dimension(
            payload,
            correspondence,
        )

        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1)
        assert view_model.core_facts is None

        schema_payload = project_daliuren_view_model(
            _runtime_core_brief(_load_fixture())
        ).model_dump(mode="json")
        schema_payload["core_facts"]["dimension_facts"]["state"] = (
            _state_dimension(payload, correspondence)
        )
        assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_requires_nullable_runtime_keys() -> None:
    field_paths = (
        ("lesson_method", "direct_direction"),
        ("dimension_facts", "relationship", "rule_evidence", "hard_verdict"),
    )
    valid_schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    for field_path in field_paths:
        payload = copy.deepcopy(_load_fixture())
        runtime_parent = payload
        for field in field_path[:-1]:
            runtime_parent = runtime_parent[field]
        del runtime_parent[field_path[-1]]

        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), field_path
        assert view_model.core_facts is None, field_path

        schema_payload = copy.deepcopy(valid_schema_payload)
        schema_parent = schema_payload["core_facts"]
        for field in field_path[:-1]:
            schema_parent = schema_parent[field]
        del schema_parent[field_path[-1]]
        assert list(
            Draft202012Validator(schema).iter_errors(schema_payload)
        ), field_path


def test_daliuren_projector_preserves_runtime_nullable_dimension_fields() -> None:
    payload = _payload_with_state_work_money_dimensions()
    timing = payload["dimension_facts"]["timing"]
    timing["candidate_branch"] = None
    timing["candidate_date"] = None
    timing["relative_speed"] = None

    work = payload["dimension_facts"]["work"]
    work["target_relative"] = None
    work["target_contract_status"] = "missing_target_relative"
    work["target_presence"] = False
    work["target_strength"] = []
    work["target_general_modifier"] = []

    _assert_runtime_accepts(payload)

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    serialized = view_model.model_dump(mode="json")
    timing_serialized = serialized["core_facts"]["dimension_facts"]["timing"]
    assert timing_serialized["candidate_branch"] is None
    assert timing_serialized["candidate_date"] is None
    assert timing_serialized["relative_speed"] is None
    assert "stage_flow" not in timing_serialized

    work_serialized = serialized["core_facts"]["dimension_facts"]["work"]
    assert work_serialized["target_relative"] is None
    assert work_serialized["target_contract_status"] == "missing_target_relative"
    assert work_serialized["target_presence"] is False
    assert work_serialized["target_strength"] == []
    assert work_serialized["target_general_modifier"] == []

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(serialized)


def test_daliuren_projector_accepts_state_work_money_control_samples() -> None:
    payload = _payload_with_state_work_money_dimensions()

    _assert_runtime_accepts(payload)
    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.dimension_facts is not None
    assert {"state", "work", "money"}.issubset(
        view_model.core_facts.dimension_facts
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


def test_daliuren_projector_accepts_nullable_stage_season_strength() -> None:
    payload = _payload_with_state_work_money_dimensions()
    payload["dimension_facts"]["state"]["stage_status"][0][
        "season_strength"
    ] = None

    _assert_runtime_accepts(payload)
    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    serialized = view_model.model_dump(mode="json")
    assert (
        serialized["core_facts"]["dimension_facts"]["state"]["stage_status"][
            0
        ]["season_strength"]
        is None
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(serialized)


def test_daliuren_projector_rejects_null_non_nullable_work_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    valid_view = project_daliuren_view_model(
        _runtime_core_brief(_payload_with_state_work_money_dimensions())
    )
    assert isinstance(valid_view, DaliurenChartV1)
    assert valid_view.core_facts is not None
    valid_schema_payload = valid_view.model_dump(mode="json")

    for field in (
        "target_contract_status",
        "target_presence",
        "target_strength",
        "target_general_modifier",
    ):
        payload = _payload_with_state_work_money_dimensions()
        payload["dimension_facts"]["work"][field] = None

        _assert_runtime_rejects(
            payload,
            f"dimension_facts.work.{field}",
        )
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), field
        assert view_model.core_facts is None, field

        schema_payload = copy.deepcopy(valid_schema_payload)
        schema_payload["core_facts"]["dimension_facts"]["work"][field] = None
        assert list(
            Draft202012Validator(schema).iter_errors(schema_payload)
        ), field


def test_daliuren_projector_rejects_untyped_work_money_rows() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    valid_view = project_daliuren_view_model(
        _runtime_core_brief(_payload_with_state_work_money_dimensions())
    )
    assert isinstance(valid_view, DaliurenChartV1)
    assert valid_view.core_facts is not None
    valid_schema_payload = valid_view.model_dump(mode="json")
    row_fields = (
        ("work", "target_strength"),
        ("work", "target_general_modifier"),
        ("money", "wealth_stage_strength"),
        ("money", "wealth_void_status"),
        ("money", "wealth_general_modifier"),
    )

    for dimension, field in row_fields:
        payload = _payload_with_state_work_money_dimensions()
        payload["dimension_facts"][dimension][field] = [
            {"internal_trace": "must-not-publish"}
        ]

        _assert_runtime_rejects(
            payload,
            f"dimension_facts.{dimension}.{field}[0]",
        )
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), (dimension, field)
        assert view_model.core_facts is None, (dimension, field)

        schema_payload = copy.deepcopy(valid_schema_payload)
        schema_payload["core_facts"]["dimension_facts"][dimension][field] = [
            {"internal_trace": "must-not-publish"}
        ]
        assert list(
            Draft202012Validator(schema).iter_errors(schema_payload)
        ), (dimension, field)


def test_daliuren_projector_rejects_non_boolean_dimension_facts() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    valid_view = project_daliuren_view_model(
        _runtime_core_brief(_payload_with_state_work_money_dimensions())
    )
    assert isinstance(valid_view, DaliurenChartV1)
    assert valid_view.core_facts is not None
    valid_schema_payload = valid_view.model_dump(mode="json")
    mutations = (
        ("state", "stage_status", "is_xunkong"),
        ("work", None, "target_presence"),
        ("money", None, "wealth_presence"),
    )

    for dimension, row_field, field in mutations:
        payload = _payload_with_state_work_money_dimensions()
        dimension_payload = payload["dimension_facts"][dimension]
        if row_field is None:
            dimension_payload[field] = 1
        else:
            dimension_payload[row_field][0][field] = 1

        _assert_runtime_rejects(payload, f"dimension_facts.{dimension}")
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), (dimension, field)
        assert view_model.core_facts is None, (dimension, field)

        schema_payload = copy.deepcopy(valid_schema_payload)
        schema_dimension = schema_payload["core_facts"]["dimension_facts"][
            dimension
        ]
        if row_field is None:
            schema_dimension[field] = 1
        else:
            schema_dimension[row_field][0][field] = 1
        assert list(
            Draft202012Validator(schema).iter_errors(schema_payload)
        ), (dimension, field)


def test_daliuren_projector_allows_empty_source_rule_ids_for_location() -> None:
    payload = copy.deepcopy(_load_fixture())
    location = payload["dimension_facts"].pop("relationship")
    location["canonical_dimension"] = "location"
    location["requested_dimension"] = "location"
    location["source_rule_ids"] = []
    del location["six_relative_stages"]
    del location["subject_object_relation"]
    del location["stage_flow"]
    location["stage_branch_directions"] = []
    payload["dimension_facts"]["location"] = location

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.dimension_facts is not None
    assert view_model.core_facts.dimension_facts["location"].source_rule_ids == ()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


def test_daliuren_projector_rejects_empty_source_rule_ids() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["source_rule_ids"] = [""]

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["dimension_facts"]["relationship"][
        "source_rule_ids"
    ] = [""]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_allows_empty_rule_evidence_fact_paths() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["rule_evidence"]["matched"][0][
        "fact_paths"
    ] = []

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.dimension_facts is not None
    matched = view_model.core_facts.dimension_facts[
        "relationship"
    ].rule_evidence.matched
    assert matched[0].fact_paths == ()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


def test_daliuren_projector_rejects_empty_rule_evidence_fact_path_entries() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["rule_evidence"]["matched"][0][
        "fact_paths"
    ] = [""]

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["dimension_facts"]["relationship"][
        "rule_evidence"
    ]["matched"][0]["fact_paths"] = [""]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_rejects_boolean_days_after_cast() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["timing_candidates"][0]["days_after_cast"] = True

    _assert_runtime_rejects(payload, "days_after_cast must be an integer")
    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["timing_candidates"][0]["days_after_cast"] = True
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_rejects_empty_xunkong_branch_entries() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["xunkong"]["branches"] = ["", ""]

    _assert_runtime_rejects(payload, "xunkong.branches[0] must be a non-empty string")
    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["xunkong"]["branches"] = ["", ""]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_rejects_empty_stop_condition_entries() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["rule_evidence"]["matched"][0][
        "stop_conditions"
    ] = [""]

    _assert_runtime_rejects(
        payload,
        "rule_evidence.matched[0].stop_conditions[0] must be a non-empty string",
    )
    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["dimension_facts"]["relationship"][
        "rule_evidence"
    ]["matched"][0]["stop_conditions"] = [""]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_fails_closed_when_adjudication_is_not_true() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["rule_evidence"][
        "requires_school_adjudication"
    ] = False

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["dimension_facts"]["relationship"]["rule_evidence"][
        "requires_school_adjudication"
    ] = False
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_fails_closed_on_unknown_runtime_fields() -> None:
    mutations: list[dict[str, object]] = []

    unknown_dimension_field = copy.deepcopy(_load_fixture())
    unknown_dimension_field["dimension_facts"]["relationship"]["internal_trace"] = {}
    mutations.append(unknown_dimension_field)

    unknown_evidence_field = copy.deepcopy(_load_fixture())
    unknown_evidence_field["dimension_facts"]["relationship"]["rule_evidence"]["matched"][
        0
    ]["internal_trace"] = {}
    mutations.append(unknown_evidence_field)

    unknown_requested_dimension = copy.deepcopy(_load_fixture())
    unknown_requested_dimension["dimension_facts"]["internal"] = copy.deepcopy(
        unknown_requested_dimension["dimension_facts"]["relationship"]
    )
    mutations.append(unknown_requested_dimension)

    missing_source_anchor = copy.deepcopy(_load_fixture())
    del missing_source_anchor["dimension_facts"]["relationship"]["rule_evidence"][
        "matched"
    ][0]["source_refs"][0]["source_anchor"]
    mutations.append(missing_source_anchor)

    for payload in mutations:
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1)
        assert view_model.core_facts is None


def test_daliuren_projector_fails_closed_when_any_required_runtime_field_is_missing() -> None:
    required_fields = (
        "day_hour",
        "earth_plate",
        "heaven_plate",
        "heavenly_generals",
        "month_general",
        "noble_person",
        "lesson_method",
        "four_lessons",
        "three_transmissions",
        "plate_offset",
        "xunkong",
        "structural_patterns",
        "dimension_facts",
    )

    for field in required_fields:
        payload = copy.deepcopy(_load_fixture())
        payload.pop(field)

        assert project_daliuren_view_model(_runtime_core_brief(payload)) is None, field


def test_daliuren_projector_fails_closed_when_required_core_fields_are_malformed() -> None:
    malformed_core_fields: dict[str, object] = {
        "day_hour": "bad",
        "earth_plate": "bad",
        "heaven_plate": [],
        "heavenly_generals": [],
        "month_general": "bad",
        "noble_person": "bad",
        "lesson_method": "bad",
        "plate_offset": True,
        "xunkong": "bad",
        "structural_patterns": {"bad": "shape"},
        "dimension_facts": "bad",
    }
    for field, malformed_value in malformed_core_fields.items():
        payload = copy.deepcopy(_load_fixture())
        payload[field] = malformed_value

        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), field
        assert view_model.core_facts is None, field

    for field in ("four_lessons", "three_transmissions"):
        payload = copy.deepcopy(_load_fixture())
        payload[field] = []

        assert project_daliuren_view_model(_runtime_core_brief(payload)) is None, field


def test_daliuren_projector_rejects_incomplete_canonical_dimension_fields() -> None:
    for field in ("candidate_branch", "candidate_date", "relative_speed"):
        payload = copy.deepcopy(_load_fixture())
        del payload["dimension_facts"]["timing"][field]

        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1), field
        assert view_model.core_facts is None, field

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    valid_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    for field in ("candidate_branch", "candidate_date", "relative_speed"):
        schema_payload = copy.deepcopy(valid_payload)
        del schema_payload["core_facts"]["dimension_facts"]["timing"][field]

        assert list(Draft202012Validator(schema).iter_errors(schema_payload)), field


def test_daliuren_projector_rejects_cross_dimension_fields() -> None:
    payload = copy.deepcopy(_load_fixture())
    payload["dimension_facts"]["relationship"]["candidate_date"] = copy.deepcopy(
        payload["dimension_facts"]["timing"]["candidate_date"]
    )

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None

    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["dimension_facts"]["relationship"][
        "candidate_date"
    ] = copy.deepcopy(
        schema_payload["core_facts"]["dimension_facts"]["timing"]["candidate_date"]
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_fail_closed_on_unknown_lesson_method_key() -> None:
    payload = copy.deepcopy(_load_fixture())
    lesson_method = dict(payload["lesson_method"])
    lesson_method["selection_trace"] = {"forged": True}
    payload["lesson_method"] = lesson_method

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    assert view_model.core_facts is None


def test_daliuren_projector_rejects_dimension_key_and_status_mismatches() -> None:
    key_mismatch = copy.deepcopy(_load_fixture())
    key_mismatch["dimension_facts"]["relationship"]["requested_dimension"] = "timing"
    key_mismatch["dimension_facts"]["relationship"]["canonical_dimension"] = "timing"

    invalid_status = copy.deepcopy(_load_fixture())
    invalid_status["dimension_facts"]["relationship"]["status"] = "verdict"

    for payload in (key_mismatch, invalid_status):
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1)
        assert view_model.core_facts is None

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    valid_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_key_mismatch = copy.deepcopy(valid_payload)
    schema_key_mismatch["core_facts"]["dimension_facts"]["relationship"][
        "requested_dimension"
    ] = "timing"
    assert list(Draft202012Validator(schema).iter_errors(schema_key_mismatch))

    schema_status_mismatch = copy.deepcopy(valid_payload)
    schema_status_mismatch["core_facts"]["dimension_facts"]["relationship"][
        "status"
    ] = "verdict"
    assert list(Draft202012Validator(schema).iter_errors(schema_status_mismatch))


def test_daliuren_projector_rejects_invalid_plate_topology() -> None:
    shuffled_earth = copy.deepcopy(_load_fixture())
    shuffled_earth["earth_plate"][0], shuffled_earth["earth_plate"][1] = (
        shuffled_earth["earth_plate"][1],
        shuffled_earth["earth_plate"][0],
    )

    duplicated_heaven = copy.deepcopy(_load_fixture())
    duplicated_heaven["heaven_plate"][1]["heaven"] = "子"

    misaligned_general = copy.deepcopy(_load_fixture())
    misaligned_general["heavenly_generals"][0]["heaven"] = "亥"

    for payload in (shuffled_earth, duplicated_heaven, misaligned_general):
        view_model = project_daliuren_view_model(_runtime_core_brief(payload))

        assert isinstance(view_model, DaliurenChartV1)
        assert view_model.core_facts is None

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_payload = project_daliuren_view_model(
        _runtime_core_brief(_load_fixture())
    ).model_dump(mode="json")
    schema_payload["core_facts"]["earth_plate"][0] = "丑"
    assert list(Draft202012Validator(schema).iter_errors(schema_payload))


def test_daliuren_projector_rejects_legacy_transmission_rows() -> None:
    missing_six_relative = copy.deepcopy(_load_fixture())
    del missing_six_relative["three_transmissions"][0]["six_relative"]

    legacy_general_alias = copy.deepcopy(_load_fixture())
    legacy_general_alias["three_transmissions"][0]["general"] = (
        legacy_general_alias["three_transmissions"][0].pop("heavenly_general")
    )

    unknown_field = copy.deepcopy(_load_fixture())
    unknown_field["three_transmissions"][0]["internal_trace"] = {}

    out_of_order = copy.deepcopy(_load_fixture())
    out_of_order["three_transmissions"][0], out_of_order["three_transmissions"][1] = (
        out_of_order["three_transmissions"][1],
        out_of_order["three_transmissions"][0],
    )

    for payload in (
        missing_six_relative,
        legacy_general_alias,
        unknown_field,
        out_of_order,
    ):
        assert project_daliuren_view_model(_runtime_core_brief(payload)) is None
