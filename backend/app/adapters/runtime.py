from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    Describe,
    Described,
    MingliCommand,
    MingliResult,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
)

FAKE_STATE_TOKEN = "fake-opaque-state"
FAKE_MANIFEST_DIGEST = "f" * 64


@runtime_checkable
class MingliRuntime(Protocol):
    async def execute(self, command: MingliCommand) -> MingliResult: ...


def _term(term_id: str, label: str) -> dict[str, object]:
    return {"id": term_id, "label": label, "description": None}


def _capability(
    capability_id: str,
    *,
    label: str,
    object_id: str,
    horizons: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": label,
        "description": "仅用于网站合同测试的 Fake 能力。",
        "objects": [_term(object_id, object_id)],
        "horizons": [_term(item, item) for item in horizons],
        "dimensions": [_term("overview", "概览"), _term("career", "事业")],
        "default_dimension_ids": ["overview"],
        "input_fields": [
            {
                "id": "fixture_input",
                "label": "合同测试输入",
                "type_id": "text",
                "description": None,
                "choices": [],
            }
        ],
        "required_input_groups": [["fixture_input"]],
    }


class FakeMingliRuntimeAdapter:
    """Deterministic contract Fake; it never performs命理 calculation."""

    production_ready = False

    def __init__(self) -> None:
        self._accepted_by_token: dict[str, str] = {}

    async def execute(self, command: MingliCommand) -> MingliResult:
        if isinstance(command, Describe):
            return self._describe()
        if isinstance(command, Prepare):
            return self._prepare(command)
        if isinstance(command, Complete):
            first_copy = self._accepted_by_token.setdefault(
                command.state_token,
                command.public_copy,
            )
            return Accepted(
                state_token=command.state_token,
                public_copy=first_copy,
            )
        raise TypeError(f"unsupported command type: {type(command).__name__}")

    def _describe(self) -> Described:
        return Described(
            protocol_version="mingli-portable-interface-v2",
            manifest_digest=FAKE_MANIFEST_DIGEST,
            capabilities=(
                _capability(
                    "bazi",
                    label="八字 Fake",
                    object_id="natal",
                    horizons=("life", "year", "month", "day"),
                ),
                _capability(
                    "fortune",
                    label="近时 Fake",
                    object_id="near_time_personal",
                    horizons=("day", "week"),
                ),
                _capability(
                    "liuyao",
                    label="六爻 Fake",
                    object_id="concrete_event",
                    horizons=("instant",),
                ),
            ),
        )

    def _prepare(self, command: Prepare) -> Prepared | Stopped:
        capability_id = command.intent.get("capability_id")
        if capability_id not in {"bazi", "fortune", "liuyao"}:
            return Stopped(
                reason="unsupported",
                public_copy="Fake Runtime 不支持该网站能力。",
                state_token=None,
                input_request=None,
            )
        if not command.facts:
            return Stopped(
                reason="need_input",
                public_copy="Fake Runtime 还需要合同测试输入。",
                state_token=FAKE_STATE_TOKEN,
                input_request={
                    "requirements": [
                        {
                            "any_of": [
                                {
                                    "id": "fixture_input",
                                    "label": "合同测试输入",
                                    "type_id": "text",
                                    "description": None,
                                    "choices": [],
                                }
                            ]
                        }
                    ]
                },
            )
        return Prepared(
            state_token=FAKE_STATE_TOKEN,
            brief=self._brief(command, str(capability_id)),
        )

    def _brief(self, command: Prepare, capability_id: str) -> ReadingBrief:
        raw_subjects = command.intent.get("subject_refs")
        subject_refs = raw_subjects if isinstance(raw_subjects, tuple) else ()
        subject_ref = str(subject_refs[0]) if subject_refs else "fixture:subject"
        raw_dimensions = command.intent.get("dimension_ids")
        dimensions = raw_dimensions if isinstance(raw_dimensions, tuple) else ()
        dimension_id = str(dimensions[0]) if dimensions else "overview"
        raw_horizon = command.intent.get("horizon")
        horizon = raw_horizon if isinstance(raw_horizon, Mapping) else {}

        return ReadingBrief.from_dict(
            {
                "question": command.query,
                "vocabulary": [],
                "facts": [
                    {
                        "ref": "fact:fake-1",
                        "subject_ref": subject_ref,
                        "kind_id": "kind.fixture",
                        "value": {"fixture": True},
                        "display_text": "这是 Fake Runtime 合同事实，不是命理结果。",
                    }
                ],
                "evidence": [],
                "findings": [
                    {
                        "ref": "finding:fake-1",
                        "subject_ref": subject_ref,
                        "dimension_ids": [dimension_id],
                        "kind_id": "kind.tendency",
                        "data": {"fixture": True},
                        "fact_refs": ["fact:fake-1"],
                        "evidence_refs": [],
                        "limit_kind_ids": ["limit:fake"],
                        "support_mode": "exact",
                    }
                ],
                "claim_scopes": [
                    {
                        "subject_ref": subject_ref,
                        "dimension_id": dimension_id,
                        "allowed_kind_ids": ["kind.tendency"],
                        "certainty_ceiling_id": "certainty.tendency",
                        "fact_refs": ["fact:fake-1"],
                        "evidence_refs": [],
                    }
                ],
                "limits": [
                    {
                        "kind_id": "limit:fake",
                        "public_text": "这是 Fake Runtime 合同边界。",
                        "scope_refs": [subject_ref],
                        "detail_ids": [],
                    }
                ],
                "prior_answer": None,
                "request_view": {
                    "subject_refs": list(subject_refs) or [subject_ref],
                    "capability_ids": [capability_id],
                    "object_id": str(command.intent["object_id"]),
                    "dimension_ids": list(dimensions),
                    "horizon": {
                        "kind_id": str(horizon["kind_id"]),
                        "start": horizon.get("start"),
                        "end": horizon.get("end"),
                    },
                },
            }
        )
