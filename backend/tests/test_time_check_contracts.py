from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from app.charts.contracts import TimeCheckViewV1
from app.charts.projectors import project_time_check_view_model
from app.readings.api_schemas import TimeCheckStartRequest
from app.readings.output_contracts import (
    UnknownOutputContractError,
    get_output_contract,
    output_contract_for_dimensions,
)
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
VIEW_SCHEMA_PATH = ROOT / "contracts" / "schemas" / "views" / "time-check-view-v1.schema.json"
DOCUMENT_SCHEMA_PATH = ROOT / "contracts" / "schemas" / "reading-document-v1.schema.json"
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"
HOUR_BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")


def _candidate(index: int, branch: str) -> dict[str, object]:
    return {
        "candidate_id": f"candidate-{index + 1:02d}",
        "hour_branch": branch,
        "local_civil_datetime": f"1994-04-30T{index * 2:02d}:00:00+08:00",
        "within_known_time_range": 3 <= index <= 5,
        "bazi_chart_digest": f"digest-{index + 1:02d}",
        "four_pillars": {
            "year": "甲戌",
            "month": "戊辰",
            "day": "丙戌",
            "hour": f"fixture-{branch}",
        },
        "day_master": {"stem": "丙"},
        "calendar_normalization": {
            "timezone": "Asia/Shanghai",
            "time_basis_policy": "civil",
        },
    }


def _brief() -> dict[str, object]:
    values: dict[str, object] = {
        "candidates": [
            _candidate(index, branch) for index, branch in enumerate(HOUR_BRANCHES)
        ],
        "candidate_count": 12,
        "known_time_range": {"start": "06:00", "end": "11:59"},
        "time_basis_policy": "civil",
        "known_event_count": 2,
        "ranking_status": "not_ranked",
        "event_matching_status": "not_calculated",
    }
    return {
        "question": "枚举十二时辰候选事实",
        "facts": [
            {
                "ref": f"fact:/calculated/time-check/{field_id}",
                "subject_ref": "profile-version:time-check-fixture",
                "kind_id": "kind.fact",
                "value": value,
                "display_text": field_id,
            }
            for field_id, value in values.items()
        ],
        "request_view": {
            "subject_refs": ["profile-version:time-check-fixture"],
            "capability_ids": ["time-check"],
            "dimension_ids": ["time_options"],
        },
    }


def _ranked_brief() -> dict[str, object]:
    brief = deepcopy(_brief())
    for fact in brief["facts"]:
        ref = str(fact["ref"])
        if ref.endswith("/ranking_status"):
            fact["value"] = "candidate_evidence_ranked"
        elif ref.endswith("/event_matching_status"):
            fact["value"] = "structured_evidence"
    brief["facts"].extend(
        [
            {
                "ref": "fact:/calculated/time-check/event_input_status",
                "subject_ref": "profile-version:time-check-fixture",
                "kind_id": "kind.fact",
                "value": "structured_valid",
                "display_text": "event_input_status",
            },
            {
                "ref": "fact:/calculated/time-check/candidate_rankings",
                "subject_ref": "profile-version:time-check-fixture",
                "kind_id": "kind.fact",
                "value": [
                    {
                        "candidate_id": f"candidate-{index + 1:02d}",
                        "hour_branch": branch,
                        "eligible": True,
                        "evidence_score": 1,
                        "matched_event_ids": ["event-1"],
                        "elimination_reasons": [],
                        "event_evidence": [
                            {
                                "event_id": "event-1",
                                "matched": True,
                                "evidence_score": 1,
                                "relations": [
                                    {
                                        "natal_position": "day",
                                        "natal_branch": "午",
                                        "event_branch": "未",
                                        "relation_type": "六合",
                                    }
                                ],
                                "event_year_ten_god": "正官",
                                "reasons": ["positive_branch_relation"],
                            }
                        ],
                        "rank": index + 1,
                    }
                    for index, branch in enumerate(HOUR_BRANCHES)
                ],
                "display_text": "candidate_rankings",
            },
            {
                "ref": "fact:/calculated/time-check/event_matches",
                "subject_ref": "profile-version:time-check-fixture",
                "kind_id": "kind.fact",
                "value": [],
                "display_text": "event_matches",
            },
        ]
    )
    return brief


def test_time_check_projects_and_validates_exactly_twelve_candidate_facts() -> None:
    view_model = project_time_check_view_model(_brief())

    assert isinstance(view_model, TimeCheckViewV1)
    assert view_model.candidate_count == 12
    assert tuple(item.hour_branch for item in view_model.candidates) == HOUR_BRANCHES
    assert view_model.ranking_status == "not_ranked"
    assert view_model.event_matching_status == "not_calculated"
    assert view_model.rectification_status is None
    assert view_model.rectification_conclusion is None

    view_schema = json.loads(VIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(view_schema)
    Draft202012Validator(view_schema).validate(view_model.model_dump(mode="json"))

    document_schema = json.loads(DOCUMENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(document_schema)
    assert {"$ref": "#/$defs/timeCheckView"} in document_schema["properties"][
        "view_model"
    ]["oneOf"]


def _rectification_facts(
    *,
    status: str,
    selected_candidate_id: str | None,
    remaining_candidate_ids: list[str],
    basis: str,
    extra: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    conclusion: dict[str, object] = {
        "status": status,
        "selected_candidate_id": selected_candidate_id,
        "remaining_candidate_ids": remaining_candidate_ids,
        "basis": basis,
        "rule_ids": ["bazi/sanming-tonghui#R-02-06"],
    }
    if extra:
        conclusion.update(extra)
    return [
        {
            "ref": "fact:/calculated/time-check/rectification_status",
            "subject_ref": "profile-version:time-check-fixture",
            "kind_id": "kind.fact",
            "value": status,
            "display_text": "rectification_status",
        },
        {
            "ref": "fact:/calculated/time-check/rectification_conclusion",
            "subject_ref": "profile-version:time-check-fixture",
            "kind_id": "kind.fact",
            "value": conclusion,
            "display_text": "rectification_conclusion",
        },
    ]


def test_time_check_projects_typed_event_evidence() -> None:
    view_model = project_time_check_view_model(_ranked_brief())

    assert isinstance(view_model, TimeCheckViewV1)
    evidence = view_model.candidate_rankings[0].event_evidence[0]
    assert evidence.event_id == "event-1"
    assert evidence.relations[0].natal_position == "day"
    assert evidence.relations[0].relation_type == "六合"
    assert evidence.reasons == ("positive_branch_relation",)
    assert view_model.rectification_status is None
    assert view_model.rectification_conclusion is None


def test_time_check_rejects_malformed_typed_event_evidence() -> None:
    malformed = _ranked_brief()
    ranking_fact = next(
        fact
        for fact in malformed["facts"]
        if str(fact["ref"]).endswith("/candidate_rankings")
    )
    first_evidence = ranking_fact["value"][0]["event_evidence"][0]
    del first_evidence["relations"][0]["event_branch"]
    assert project_time_check_view_model(malformed) is None


def test_time_check_rejects_non_object_ranking_rows_instead_of_dropping_them() -> None:
    malformed = _ranked_brief()
    ranking_fact = next(
        fact
        for fact in malformed["facts"]
        if str(fact["ref"]).endswith("/candidate_rankings")
    )
    ranking_fact["value"].append("not-an-evidence-object")
    assert project_time_check_view_model(malformed) is None


def test_time_check_projects_rectification_conclusion_without_outcome() -> None:
    brief = deepcopy(_brief())
    brief["facts"].extend(
        _rectification_facts(
            status="hour_determined",
            selected_candidate_id="candidate-04",
            remaining_candidate_ids=["candidate-04"],
            basis="known_time_range_unique",
        )
    )
    view_model = project_time_check_view_model(brief)

    assert isinstance(view_model, TimeCheckViewV1)
    assert view_model.rectification_status == "hour_determined"
    assert view_model.rectification_conclusion is not None
    assert view_model.rectification_conclusion.selected_candidate_id == "candidate-04"
    assert view_model.rectification_conclusion.basis == "known_time_range_unique"
    dumped = view_model.model_dump(mode="json")
    assert "outcome" not in dumped
    assert "verdict" not in dumped
    assert "outcome" not in dumped["rectification_conclusion"]
    assert "verdict" not in dumped["rectification_conclusion"]
    view_schema = json.loads(VIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(view_schema).validate(dumped)


def test_time_check_rejects_rectification_outcome_or_unpaired_facts() -> None:
    with_outcome = deepcopy(_brief())
    with_outcome["facts"].extend(
        _rectification_facts(
            status="hour_determined",
            selected_candidate_id="candidate-04",
            remaining_candidate_ids=["candidate-04"],
            basis="known_time_range_unique",
            extra={"outcome": "吉"},
        )
    )
    assert project_time_check_view_model(with_outcome) is None

    unpaired = deepcopy(_brief())
    unpaired["facts"].append(
        {
            "ref": "fact:/calculated/time-check/rectification_status",
            "subject_ref": "profile-version:time-check-fixture",
            "kind_id": "kind.fact",
            "value": "hour_determined",
            "display_text": "rectification_status",
        }
    )
    assert project_time_check_view_model(unpaired) is None


def test_time_check_rejects_malformed_candidates_and_missing_required_facts() -> None:
    malformed = deepcopy(_brief())
    candidates = malformed["facts"][0]["value"]
    del candidates[0]["calendar_normalization"]
    assert project_time_check_view_model(malformed) is None

    missing_contract_fact = deepcopy(_brief())
    missing_contract_fact["facts"] = [
        fact
        for fact in missing_contract_fact["facts"]
        if not str(fact["ref"]).endswith("/ranking_status")
    ]
    assert project_time_check_view_model(missing_contract_fact) is None


@pytest.mark.parametrize(
    ("field", "value"),
    (("time_range_start", "24:00"), ("dimension_ids", ["career"])),
)
def test_time_check_request_rejects_illegal_contract_input(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "profile_version_id": uuid4(),
        "time_range_start": "06:00",
        "time_range_end": "11:59",
        "dimension_ids": ["time_options"],
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        TimeCheckStartRequest.model_validate(payload)


def test_time_options_output_and_openapi_contracts_are_frozen() -> None:
    output_contract = output_contract_for_dimensions(("time_options",))
    assert output_contract.required_dimension_ids == ("time_options",)
    with pytest.raises(UnknownOutputContractError, match="unknown output contract"):
        get_output_contract("missing-time-check-contract")

    openapi = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    operation = openapi["paths"]["/api/v1/readings/time-check"]["post"]
    assert operation["operationId"] == "startTimeCheckReading"
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TimeCheckStartRequest"
    }
    request_schema = openapi["components"]["schemas"]["TimeCheckStartRequest"]
    assert request_schema["properties"]["dimension_ids"]["items"]["const"] == (
        "time_options"
    )
