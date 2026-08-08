import importlib
from collections.abc import Mapping
from typing import Any

import pytest


def prepare_payload() -> dict[str, Any]:
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


def brief_payload() -> dict[str, Any]:
    return {
        "question": "看一下这个八字",
        "vocabulary": [],
        "facts": [],
        "evidence": [],
        "findings": [],
        "claim_scopes": [],
        "limits": [],
        "prior_answer": None,
        "request_view": None,
    }


@pytest.mark.parametrize(
    "payload, expected_type",
    [
        ({"kind": "describe"}, "Describe"),
        (prepare_payload(), "Prepare"),
        (
            {
                "kind": "complete",
                "state_token": "fake-opaque-state",
                "public_copy": "合同测试正文。",
            },
            "Complete",
        ),
    ],
)
def test_command_dtos_validate_and_round_trip_public_json(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")

    command = contracts.command_from_dict(payload)

    assert type(command).__name__ == expected_type
    assert command.to_dict() == payload


@pytest.mark.parametrize(
    "payload, expected_type",
    [
        (
            {
                "kind": "described",
                "protocol_version": "mingli-portable-interface-v2",
                "manifest_digest": "0" * 64,
                "capabilities": [],
            },
            "Described",
        ),
        (
            {
                "kind": "prepared",
                "state_token": "fake-opaque-state",
                "brief": brief_payload(),
            },
            "Prepared",
        ),
        (
            {
                "kind": "accepted",
                "state_token": "fake-opaque-state",
                "public_copy": "合同测试正文。",
            },
            "Accepted",
        ),
        (
            {
                "kind": "stopped",
                "reason": "error",
                "public_copy": "测试运行时停止。",
                "state_token": None,
                "input_request": None,
            },
            "Stopped",
        ),
    ],
)
def test_result_dtos_validate_and_round_trip_public_json(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")

    result = contracts.result_from_dict(payload)

    assert type(result).__name__ == expected_type
    assert result.to_dict() == payload


def test_protocol_boundary_rejects_extra_or_legacy_fields() -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")
    malformed = prepare_payload()
    malformed["legacy_system"] = "bazi"

    with pytest.raises(contracts.ContractValidationError):
        contracts.command_from_dict(malformed)


def test_prepared_brief_is_deeply_immutable() -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")
    payload = {
        "kind": "prepared",
        "state_token": "fake-opaque-state",
        "brief": brief_payload(),
    }
    payload["brief"]["facts"] = [
        {
            "ref": "fact:fake",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fixture",
            "value": {"nested": [1, 2]},
            "display_text": "合同测试事实。",
        }
    ]

    prepared = contracts.result_from_dict(payload)
    fact = prepared.brief["facts"][0]

    assert isinstance(prepared.brief, Mapping)
    assert prepared.to_dict() == payload
    with pytest.raises(TypeError):
        fact["value"]["nested"][0] = 9


def test_narrative_request_has_only_the_closed_model_boundary() -> None:
    runtime = importlib.import_module("app.readings.runtime_contracts")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    brief = runtime.ReadingBrief.from_dict(brief_payload())
    output_contract = narrative.OutputContract.from_dict(
        {
            "schema_version": "mingli-output-contract-v1",
            "contract_id": "preview-v1",
            "language": "zh-CN",
            "min_blocks": 1,
            "max_blocks": 4,
            "max_output_chars": 1200,
            "required_dimension_ids": [],
            "required_limit_kind_ids": [],
            "disclosure_text": "AI 辅助生成，仅供传统文化参考。",
        }
    )
    request = narrative.NarrativeRequest(
        brief=brief,
        narrative_policy_version="policy-v1",
        output_contract=output_contract,
        language="zh-CN",
        max_output_chars=1200,
    )

    payload = request.to_dict()

    assert set(payload) == {
        "brief",
        "narrative_policy_version",
        "output_contract",
        "language",
        "max_output_chars",
    }
    serialized = repr(payload).lower()
    for forbidden in ("state_token", "user_id", "order_id", "entitlement"):
        assert forbidden not in serialized
