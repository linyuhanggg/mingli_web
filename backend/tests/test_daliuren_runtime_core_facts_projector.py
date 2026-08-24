from __future__ import annotations

import copy
import json
from pathlib import Path

from app.charts.contracts import DaliurenChartV1
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


def test_daliuren_projector_preserves_explicit_dimension_nulls() -> None:
    payload = copy.deepcopy(_load_fixture())
    timing = payload["dimension_facts"]["timing"]
    timing["candidate_branch"] = None
    timing["candidate_date"] = None
    timing["relative_speed"] = None

    work = copy.deepcopy(payload["dimension_facts"]["relationship"])
    work["requested_dimension"] = "work"
    work["canonical_dimension"] = "work"
    del work["stage_flow"]
    work["stage_status"] = []
    work["target_contract_status"] = None
    work["target_general_modifier"] = None
    work["target_presence"] = None
    work["target_relative"] = None
    work["target_strength"] = None
    payload["dimension_facts"]["work"] = work

    view_model = project_daliuren_view_model(_runtime_core_brief(payload))

    assert isinstance(view_model, DaliurenChartV1)
    serialized = view_model.model_dump(mode="json")
    timing_serialized = serialized["core_facts"]["dimension_facts"]["timing"]
    assert timing_serialized["candidate_branch"] is None
    assert timing_serialized["candidate_date"] is None
    assert timing_serialized["relative_speed"] is None
    assert "stage_flow" not in timing_serialized

    work_serialized = serialized["core_facts"]["dimension_facts"]["work"]
    assert work_serialized["target_contract_status"] is None
    assert work_serialized["target_general_modifier"] is None
    assert work_serialized["target_presence"] is None
    assert work_serialized["target_relative"] is None
    assert work_serialized["target_strength"] is None

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(serialized)


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
