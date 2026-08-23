from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.adapters.model import FakeModelGateway
from app.adapters.runtime import FAKE_STATE_TOKEN, FakeMingliRuntimeAdapter
from app.readings.alerts import NoopAlertSink
from app.readings.errors import NarrativeGenerationError
from app.readings.models import ReadingJobRecord
from app.readings.narrative_contracts import NarrativeRequest
from app.readings.narrative_guard import NarrativeGuard
from app.readings.output_contracts import output_contract_for_product, resolve_output_contract
from app.readings.public_copy import PublicCopyAssembler
from app.readings.orchestrator import OrchestratorInvariantError, ReadingOrchestrator
from app.readings.relationship_deep_extract import (
    RelationshipDeepDocumentResult,
    extract_relationship_deep_candidate,
    relationship_deep_complete_intent,
    relationship_deep_fake_runtime_accept,
    relationship_deep_persist_job_accepted,
    relationship_deep_persist_job_candidate,
    relationship_deep_persist_job_output_contract,
    relationship_deep_persist_job_prepared,
    relationship_deep_persist_job_relationship_type,
    relationship_deep_persist_job_runtime_release,
    relationship_deep_persist_job_version,
    relationship_deep_generate_orchestrator,
    relationship_deep_persist_orchestrator,
    relationship_deep_prepare_orchestrator,
    relationship_deep_persist_reading_document,
    relationship_deep_reading_document,
    relationship_deep_http_export,
    relationship_deep_http_follow_up,
    relationship_deep_http_result,
    relationship_deep_http_share,
)
from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
)
from app.readings.export import render_reading_export
from app.readings.repository import SqlReadingRepository
from app.readings.share_contracts import SharedReadingDocumentV1
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher
from httpx import AsyncClient
from orchestrator_fakes import FixedClock
from sqlalchemy import select

from test_profiles_api import create_confirmed_profile, create_guest
from test_reading_repository import create_reading_graph
from test_readings_api import seed_runtime_release

SIGNAL_A = "甲方年支与乙方年支构成六冲（跨盘结构事实）。"
SIGNAL_B = "甲方年干与乙方月干构成天干五合（跨盘结构事实）。"
SIGNAL_C = "甲方日支与乙方日支构成六合（跨盘结构事实）。"
WRAPPER_TEXT = "跨盘结构事实"

_CONTRACTS = (
    "bazi-relationship-deep-output-v1",
    "ziwei-relationship-deep-output-v1",
    "qizheng-relationship-deep-output-v1",
)
_CONTRACT_CAPABILITY = {
    "bazi-relationship-deep-output-v1": "bazi",
    "ziwei-relationship-deep-output-v1": "ziwei",
    "qizheng-relationship-deep-output-v1": "xingming",
}
_CONTRACT_VIEW_SCHEMA = {
    "bazi-relationship-deep-output-v1": "bazi-relationship/v1",
    "ziwei-relationship-deep-output-v1": "ziwei-relationship/v1",
    "qizheng-relationship-deep-output-v1": "qizheng-relationship/v1",
}
_CONTRACT_API_PRODUCT = {
    "bazi-relationship-deep-output-v1": "bazi-relationship-deep",
    "ziwei-relationship-deep-output-v1": "ziwei-relationship-deep",
    "qizheng-relationship-deep-output-v1": "qizheng-relationship-deep",
}


def _signal(signal_id: str, display_text: str) -> dict[str, object]:
    return {
        "dimension_id": "relationship",
        "subject_refs": ["profile-version:a", "profile-version:b"],
        "signal_id": signal_id,
        "display_text": display_text,
        "fact_refs": [
            "fact:profile-version:a/calculated/bazi/four_pillars",
            "fact:profile-version:b/calculated/bazi/four_pillars",
        ],
    }


def _brief(
    *,
    signals: object | None = ...,
    omit_signals_fact: bool = False,
    capability_id: str = "bazi",
) -> ReadingBrief:
    source_facts = [
        {
            "ref": f"fact:profile-version:{suffix}/calculated/bazi/four_pillars",
            "subject_ref": f"profile-version:{suffix}",
            "kind_id": "kind.bazi.four_pillars",
            "value": {"year": suffix},
            "display_text": "四柱",
        }
        for suffix in ("a", "b")
    ]
    signal_value: object
    if signals is ...:
        signal_value = [
            _signal("bazi.cross_branch.liu_chong.year.year", SIGNAL_A),
            _signal("bazi.cross_stem.wu_he.year.month", SIGNAL_B),
            _signal("bazi.cross_branch.liu_he.day.day", SIGNAL_C),
        ]
    else:
        signal_value = signals
    facts: list[dict[str, object]] = list(source_facts)
    fact_refs = [item["ref"] for item in source_facts]
    if not omit_signals_fact:
        facts.append(
            {
                "ref": "fact:relationship/calculated/bazi/relationship_signals",
                "subject_ref": "relationship",
                "kind_id": "kind.bazi.relationship_signals",
                "value": signal_value,
                "display_text": WRAPPER_TEXT,
            }
        )
        fact_refs.append("fact:relationship/calculated/bazi/relationship_signals")
    return ReadingBrief.from_dict(
        {
            "question": "双方关系的结构事实是什么？",
            "vocabulary": [],
            "facts": facts,
            "evidence": [],
            "findings": [],
            "claim_scopes": [
                {
                    "subject_ref": "relationship",
                    "dimension_id": "relationship",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": fact_refs,
                    "evidence_refs": [],
                }
            ],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": ["profile-version:a", "profile-version:b"],
                "capability_ids": [capability_id],
                "object_id": "relationship",
                "dimension_ids": ["relationship"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def _candidate(texts: tuple[str, str, str]) -> dict[str, Any]:
    return {
        "schema_version": "mingli-narrative-candidate-v1",
        "blocks": [
            {
                "block_id": f"b{index}",
                "block_type": "claim",
                "text": text,
                "subject_ref": "relationship",
                "dimension_id": "relationship",
                "claim_kind_id": "kind.tendency",
                "certainty_id": "certainty.tendency",
                "fact_refs": ["fact:relationship/calculated/bazi/relationship_signals"],
                "finding_refs": [],
                "evidence_refs": [],
                "limit_kind_ids": [],
            }
            for index, text in enumerate(texts, start=1)
        ],
    }


@pytest.mark.parametrize("contract_id", _CONTRACTS)
def test_relationship_deep_accepts_verbatim_signal_display_text(contract_id: str) -> None:
    result = NarrativeGuard().validate(
        _candidate((SIGNAL_A, SIGNAL_B, SIGNAL_C)),
        _brief(),
        output_contract=contract_id,
    )

    assert result.passed is True
    assert result.errors == ()


@pytest.mark.parametrize("contract_id", _CONTRACTS)
def test_relationship_deep_rejects_paraphrase_and_wrapper_fact_text(
    contract_id: str,
) -> None:
    guard = NarrativeGuard()
    brief = _brief()

    paraphrased = guard.validate(
        _candidate((f"{SIGNAL_A} 因此双方关系紧张。", SIGNAL_B, SIGNAL_C)),
        brief,
        output_contract=contract_id,
    )
    wrapper = guard.validate(
        _candidate((WRAPPER_TEXT, SIGNAL_B, SIGNAL_C)),
        brief,
        output_contract=contract_id,
    )

    assert paraphrased.passed is False
    assert paraphrased.errors == ("relationship_deep_text_not_grounded",)
    assert wrapper.passed is False
    assert wrapper.errors == ("relationship_deep_text_not_grounded",)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
def test_relationship_deep_rejects_duplicate_signal_text(contract_id: str) -> None:
    result = NarrativeGuard().validate(
        _candidate((SIGNAL_A, SIGNAL_A, SIGNAL_B)),
        _brief(),
        output_contract=contract_id,
    )

    assert result.passed is False
    assert result.errors == ("relationship_deep_duplicate_source",)


@pytest.mark.parametrize(
    "signals, omit_signals_fact",
    [
        ([], False),
        (None, True),
        ("not-a-list", False),
        ([{"signal_id": "broken"}], False),
    ],
)
def test_relationship_deep_fail_closed_when_signals_missing(
    signals: object,
    omit_signals_fact: bool,
) -> None:
    brief = (
        _brief(omit_signals_fact=True)
        if omit_signals_fact
        else _brief(signals=signals)
    )
    candidate = _candidate((SIGNAL_A, SIGNAL_B, SIGNAL_C))
    if omit_signals_fact:
        for block in candidate["blocks"]:
            block["fact_refs"] = ["fact:profile-version:a/calculated/bazi/four_pillars"]

    result = NarrativeGuard().validate(
        candidate,
        brief,
        output_contract="bazi-relationship-deep-output-v1",
    )

    assert result.passed is False
    assert "relationship_signals_missing" in result.errors


def test_free_relationship_preview_does_not_use_extractive_gate() -> None:
    result = NarrativeGuard().validate(
        _candidate((f"{SIGNAL_A} 因此双方关系紧张。", SIGNAL_B, SIGNAL_C)),
        _brief(),
        output_contract=output_contract_for_product(
            "bazi-relationship", ("relationship",)
        ),
    )

    assert result.passed is True
    assert result.errors == ()


@pytest.mark.parametrize("contract_id", _CONTRACTS)
def test_extract_fills_blocks_with_verbatim_signal_display_text(
    contract_id: str,
) -> None:
    brief = _brief()
    extracted = extract_relationship_deep_candidate(brief, contract_id)

    assert extracted.errors == ()
    assert extracted.candidate is not None
    texts = tuple(block.text for block in extracted.candidate.blocks)
    assert texts == (SIGNAL_A, SIGNAL_B, SIGNAL_C)
    assert WRAPPER_TEXT not in texts
    assert all(
        block.fact_refs == ("fact:relationship/calculated/bazi/relationship_signals",)
        for block in extracted.candidate.blocks
    )

    result = NarrativeGuard().validate(
        extracted.candidate,
        brief,
        output_contract=contract_id,
    )
    assert result.passed is True
    assert result.errors == ()


def test_extract_caps_at_eight_unique_signal_texts() -> None:
    extra = tuple(f"跨盘结构信号{index}。" for index in range(1, 10))
    signals = [_signal(f"bazi.extra.{index}", text) for index, text in enumerate(extra, start=1)]
    extracted = extract_relationship_deep_candidate(
        _brief(signals=signals),
        "bazi-relationship-deep-output-v1",
    )

    assert extracted.errors == ()
    assert extracted.candidate is not None
    assert tuple(block.text for block in extracted.candidate.blocks) == extra[:8]


def test_extract_skips_duplicate_and_empty_signal_text() -> None:
    signals = [
        _signal("one", SIGNAL_A),
        _signal("dup", SIGNAL_A),
        _signal("blank", "   "),
        _signal("two", SIGNAL_B),
        _signal("three", SIGNAL_C),
        {"signal_id": "no-text"},
    ]
    extracted = extract_relationship_deep_candidate(
        _brief(signals=signals),
        "bazi-relationship-deep-output-v1",
    )

    assert extracted.errors == ()
    assert extracted.candidate is not None
    assert tuple(block.text for block in extracted.candidate.blocks) == (
        SIGNAL_A,
        SIGNAL_B,
        SIGNAL_C,
    )


@pytest.mark.parametrize(
    "signals, omit_signals_fact",
    [
        ([], False),
        (None, True),
        ("not-a-list", False),
        ([{"signal_id": "broken"}], False),
        (
            [
                _signal("one", SIGNAL_A),
                _signal("two", SIGNAL_B),
            ],
            False,
        ),
    ],
)
def test_extract_fail_closed_when_fewer_than_three_unique_signals(
    signals: object,
    omit_signals_fact: bool,
) -> None:
    brief = (
        _brief(omit_signals_fact=True)
        if omit_signals_fact
        else _brief(signals=signals)
    )
    extracted = extract_relationship_deep_candidate(
        brief,
        "bazi-relationship-deep-output-v1",
    )

    assert extracted.candidate is None
    assert extracted.errors == ("relationship_signals_missing",)


def test_extract_does_not_apply_to_free_relationship_preview() -> None:
    extracted = extract_relationship_deep_candidate(
        _brief(),
        output_contract_for_product("bazi-relationship", ("relationship",)),
    )

    assert extracted.candidate is None
    assert extracted.errors == ("relationship_deep_extract_not_applicable",)


def _generate_request(brief: ReadingBrief, output_contract: object) -> NarrativeRequest:
    contract = resolve_output_contract(output_contract)
    return NarrativeRequest(
        brief=brief,
        narrative_policy_version="policy-v1",
        output_contract=contract,
        language=contract.language,
        max_output_chars=contract.max_output_chars,
    )


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_generate_returns_extract_candidate_for_relationship_deep(
    contract_id: str,
) -> None:
    brief = _brief()
    generation = await FakeModelGateway().generate(_generate_request(brief, contract_id))

    texts = tuple(block.text for block in generation.candidate.blocks)
    assert texts == (SIGNAL_A, SIGNAL_B, SIGNAL_C)
    assert WRAPPER_TEXT not in texts
    assert generation.candidate.blocks[0].text != "这是合同测试候选稿，不是正式命理解读。"
    result = NarrativeGuard().validate(
        generation.candidate,
        brief,
        output_contract=contract_id,
    )
    assert result.passed is True
    assert result.errors == ()


async def test_generate_fail_closed_when_relationship_signals_missing() -> None:
    with pytest.raises(NarrativeGenerationError, match="relationship_signals_missing"):
        await FakeModelGateway().generate(
            _generate_request(_brief(signals=[]), "bazi-relationship-deep-output-v1")
        )


async def test_generate_does_not_extract_free_relationship_preview() -> None:
    generation = await FakeModelGateway().generate(
        _generate_request(
            _brief(),
            output_contract_for_product("bazi-relationship", ("relationship",)),
        )
    )

    texts = tuple(block.text for block in generation.candidate.blocks)
    assert texts == ("这是合同测试候选稿，不是正式命理解读。",)
    assert SIGNAL_A not in texts


def _expected_public_copy(texts: tuple[str, ...], contract_id: str) -> str:
    contract = resolve_output_contract(contract_id)
    return "\n\n".join((*texts, contract.disclosure_text))


def _pad_unique_texts(count: int, joined_budget: int, marks: str) -> tuple[str, ...]:
    separators = 2 * (count - 1)
    remainder = joined_budget - separators
    body = remainder // count
    extra = remainder % count
    texts = []
    for index in range(count):
        length = body + (extra if index == 0 else 0)
        mark = marks[index]
        texts.append(mark + ("甲" * (length - 1)))
    return tuple(texts)


def _oversized_min_block_signals(contract_id: str) -> list[dict[str, object]]:
    contract = resolve_output_contract(contract_id)
    disclosure_overhead = 2 + len(contract.disclosure_text)
    texts = _pad_unique_texts(contract.min_blocks, contract.max_output_chars, "乙丙丁")
    joined = "\n\n".join(texts)
    assert len(joined) <= contract.max_output_chars
    assert len(joined) + disclosure_overhead > contract.max_output_chars
    return [_signal(f"bazi.oversize.{index}", text) for index, text in enumerate(texts, start=1)]


def _trimmable_public_copy_signals(contract_id: str) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    contract = resolve_output_contract(contract_id)
    overhead = 2 + len(contract.disclosure_text)
    texts = _pad_unique_texts(4, min(contract.max_output_chars, contract.max_output_chars - overhead + 12), "1234")
    kept_texts = texts[:3]
    kept_copy = "\n\n".join((*kept_texts, contract.disclosure_text))
    full_joined = "\n\n".join(texts)
    full_copy = "\n\n".join((*texts, contract.disclosure_text))
    assert len(full_joined) <= contract.max_output_chars
    assert len(kept_copy) <= contract.max_output_chars
    assert len(full_copy) > contract.max_output_chars
    signals = [_signal(f"bazi.trim.{index}", text) for index, text in enumerate(texts, start=1)]
    return signals, kept_texts


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_generate_candidate_assembles_verbatim_public_copy(
    contract_id: str,
) -> None:
    brief = _brief()
    generation = await FakeModelGateway().generate(_generate_request(brief, contract_id))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract_id,
    )

    assert public_copy == _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    assert WRAPPER_TEXT not in public_copy.split("\n\n")
    assert "匹配度" not in public_copy.split("\n\n")[0]


async def test_generate_does_not_assemble_extract_copy_for_free_relationship_preview() -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )

    assert SIGNAL_A not in public_copy
    assert generation.candidate.blocks[0].text in public_copy


async def test_generate_fail_closed_when_assembled_public_copy_exceeds_contract() -> None:
    brief = _brief(signals=_oversized_min_block_signals("bazi-relationship-deep-output-v1"))
    with pytest.raises(NarrativeGenerationError, match="relationship_signals_missing"):
        await FakeModelGateway().generate(
            _generate_request(brief, "bazi-relationship-deep-output-v1")
        )


async def test_generate_trims_candidate_until_public_copy_fits() -> None:
    signals, kept_texts = _trimmable_public_copy_signals("bazi-relationship-deep-output-v1")
    brief = _brief(signals=signals)
    generation = await FakeModelGateway().generate(
        _generate_request(brief, "bazi-relationship-deep-output-v1")
    )
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        "bazi-relationship-deep-output-v1",
    )

    assert tuple(block.text for block in generation.candidate.blocks) == kept_texts
    assert public_copy == _expected_public_copy(
        kept_texts, "bazi-relationship-deep-output-v1"
    )


_PREPARED_TOKEN = "opaque-prepared-token"


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_assembled_public_copy_becomes_complete_intent(contract_id: str) -> None:
    brief = _brief()
    generation = await FakeModelGateway().generate(_generate_request(brief, contract_id))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract_id,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract_id,
    )

    assert intent.errors == ()
    assert intent.command is not None
    assert intent.command.kind == "complete"
    assert intent.command.state_token == _PREPARED_TOKEN
    assert intent.command.public_copy == public_copy
    assert intent.command.public_copy.encode() == public_copy.encode()
    assert intent.command.to_dict() == {
        "kind": "complete",
        "state_token": _PREPARED_TOKEN,
        "public_copy": public_copy,
    }
    assert WRAPPER_TEXT not in intent.command.public_copy.split("\n\n")
    assert "匹配度" not in intent.command.public_copy.split("\n\n")[0]


async def test_complete_intent_does_not_apply_to_free_relationship_preview() -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )

    assert intent.command is None
    assert intent.errors == ("relationship_deep_extract_not_applicable",)


async def test_complete_intent_fail_closed_when_public_copy_blank() -> None:
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy="   ",
        output_contract="bazi-relationship-deep-output-v1",
    )

    assert intent.command is None
    assert intent.errors == ("relationship_signals_missing",)


async def test_complete_intent_fail_closed_when_state_token_blank() -> None:
    brief = _brief()
    generation = await FakeModelGateway().generate(
        _generate_request(brief, "bazi-relationship-deep-output-v1")
    )
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        "bazi-relationship-deep-output-v1",
    )
    intent = relationship_deep_complete_intent(
        state_token="   ",
        public_copy=public_copy,
        output_contract="bazi-relationship-deep-output-v1",
    )

    assert intent.command is None
    assert intent.errors == ("relationship_deep_complete_intent_invalid",)


async def test_complete_intent_fail_closed_when_copy_is_not_assembled() -> None:
    raw = "\n\n".join((SIGNAL_A, SIGNAL_B, SIGNAL_C))
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=raw,
        output_contract="bazi-relationship-deep-output-v1",
    )

    assert intent.command is None
    assert intent.errors == ("relationship_signals_missing",)
    assert "本深读只基于已计算的双方八字关系结构事实" not in raw


class _RaisingRuntime:
    async def execute(self, command: Complete) -> Accepted:
        raise AssertionError(f"runtime must not execute invalid intent: {command.kind}")


class _StoppedRuntime:
    async def execute(self, command: Complete) -> Stopped:
        return Stopped(
            reason="error",
            public_copy="Fake Runtime 未接纳。",
            state_token=command.state_token,
        )


async def _complete_intent(contract_id: str):
    brief = _brief()
    generation = await FakeModelGateway().generate(_generate_request(brief, contract_id))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract_id,
    )
    return relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract_id,
    ), public_copy


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_complete_intent_becomes_fake_runtime_accepted(contract_id: str) -> None:
    intent, public_copy = await _complete_intent(contract_id)
    accepted = await relationship_deep_fake_runtime_accept(
        intent, FakeMingliRuntimeAdapter()
    )

    assert intent.command is not None
    assert accepted.errors == ()
    assert accepted.accepted is not None
    assert accepted.accepted.kind == "accepted"
    assert accepted.accepted.state_token == _PREPARED_TOKEN
    assert accepted.accepted.public_copy == public_copy
    assert accepted.accepted.public_copy.encode() == public_copy.encode()
    assert accepted.accepted.public_copy.encode() == intent.command.public_copy.encode()
    assert WRAPPER_TEXT not in accepted.accepted.public_copy.split("\n\n")
    assert "匹配度" not in accepted.accepted.public_copy.split("\n\n")[0]


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_fake_runtime_replay_keeps_first_accepted_copy(contract_id: str) -> None:
    intent, public_copy = await _complete_intent(contract_id)
    runtime = FakeMingliRuntimeAdapter()
    first = await relationship_deep_fake_runtime_accept(intent, runtime)
    replay = await runtime.execute(
        Complete(state_token=_PREPARED_TOKEN, public_copy="第二次不得覆盖的改写。")
    )

    assert first.accepted is not None
    assert isinstance(replay, Accepted)
    assert replay.public_copy == first.accepted.public_copy
    assert replay.public_copy == public_copy
    assert replay.public_copy.encode() == first.accepted.public_copy.encode()
    assert replay.public_copy != "第二次不得覆盖的改写。"


async def test_fake_runtime_accept_does_not_apply_to_free_relationship_preview() -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())

    assert accepted.accepted is None
    assert accepted.errors == ("relationship_deep_extract_not_applicable",)


async def test_fake_runtime_accept_fail_closed_when_intent_invalid() -> None:
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy="   ",
        output_contract="bazi-relationship-deep-output-v1",
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())

    assert accepted.accepted is None
    assert accepted.errors == ("relationship_signals_missing",)


async def test_fake_runtime_accept_fail_closed_when_runtime_does_not_accept() -> None:
    intent, _public_copy = await _complete_intent("bazi-relationship-deep-output-v1")
    accepted = await relationship_deep_fake_runtime_accept(intent, _StoppedRuntime())

    assert accepted.accepted is None
    assert accepted.errors == ("relationship_deep_fake_runtime_not_accepted",)


async def _accepted_document_inputs(contract_id: str):
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    generation = await FakeModelGateway().generate(_generate_request(brief, contract_id))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract_id,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract_id,
    )
    accepted = await relationship_deep_fake_runtime_accept(
        intent, FakeMingliRuntimeAdapter()
    )
    return brief, generation.candidate, accepted, public_copy


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_fake_runtime_accepted_freezes_reading_document(contract_id: str) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(contract_id)
    reading_version_id = uuid4()
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract=contract_id,
        reading_version_id=reading_version_id,
        relationship_type="romantic",
    )

    assert frozen.errors == ()
    assert frozen.document is not None
    assert frozen.document.schema_version == "reading-document/v1"
    assert frozen.document.reading_version_id == str(reading_version_id)
    assert frozen.document.accepted_copy_ref == f"accepted-copy:{_PREPARED_TOKEN}"
    assert frozen.document.view_model.schema_version == _CONTRACT_VIEW_SCHEMA[contract_id]
    assert tuple(claim.text for claim in frozen.document.claims) == (
        SIGNAL_A,
        SIGNAL_B,
        SIGNAL_C,
    )
    assert all(claim.text in public_copy.split("\n\n") for claim in frozen.document.claims)
    assert WRAPPER_TEXT not in {claim.text for claim in frozen.document.claims}
    assert "匹配度" not in frozen.document.claims[0].text
    assert accepted.accepted is not None
    assert frozen.document.answer_summary == accepted.accepted.public_copy.split("\n\n")[0]
    assert any(
        boundary.text == resolve_output_contract(contract_id).disclosure_text
        for boundary in frozen.document.boundaries
    )
    replay = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract=contract_id,
        reading_version_id=reading_version_id,
        relationship_type="romantic",
    )
    assert replay.document is not None
    assert replay.document.model_dump(mode="json") == frozen.document.model_dump(mode="json")


async def test_reading_document_does_not_apply_to_free_relationship_preview() -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=generation.candidate,
        output_contract=contract,
        reading_version_id=uuid4(),
        relationship_type="romantic",
    )

    assert frozen.document is None
    assert frozen.errors == ("relationship_deep_extract_not_applicable",)


async def test_reading_document_fail_closed_when_runtime_did_not_accept() -> None:
    intent, _public_copy = await _complete_intent("bazi-relationship-deep-output-v1")
    accepted = await relationship_deep_fake_runtime_accept(intent, _StoppedRuntime())
    brief = _brief()
    candidate = extract_relationship_deep_candidate(
        brief, "bazi-relationship-deep-output-v1"
    ).candidate
    assert candidate is not None
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract="bazi-relationship-deep-output-v1",
        reading_version_id=uuid4(),
        relationship_type="romantic",
    )

    assert frozen.document is None
    assert frozen.errors == ("relationship_deep_fake_runtime_not_accepted",)


async def test_reading_document_fail_closed_when_view_model_cannot_be_projected() -> None:
    brief, candidate, accepted, _public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract="bazi-relationship-deep-output-v1",
        reading_version_id=uuid4(),
        relationship_type=None,
    )

    assert frozen.document is None
    assert frozen.errors == ("relationship_deep_reading_document_unavailable",)


async def test_reading_document_fail_closed_when_claims_are_not_in_accepted_copy() -> None:
    brief, candidate, accepted, _public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    rewritten = extract_relationship_deep_candidate(
        _brief(
            signals=[
                _signal("one", "这是改写后的合婚吉凶断言。"),
                _signal("two", SIGNAL_B),
                _signal("three", SIGNAL_C),
            ],
        ),
        "bazi-relationship-deep-output-v1",
    )
    assert rewritten.candidate is not None
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=rewritten.candidate,
        output_contract="bazi-relationship-deep-output-v1",
        reading_version_id=uuid4(),
        relationship_type="romantic",
    )

    assert frozen.document is None
    assert frozen.errors == ("relationship_signals_missing",)
    assert rewritten.candidate.blocks[0].text not in (
        accepted.accepted.public_copy if accepted.accepted is not None else ""
    )


@pytest.fixture
async def reading_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    importlib.import_module("app.commerce.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")
    async with database.engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    yield database
    await database.dispose()


async def _warehouse_accepted(session: Any, public_copy: str):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_completion_intent(str(job.id), public_copy, now)
    await repository.record_accepted(
        str(job.id),
        contracts.Accepted(state_token=_PREPARED_TOKEN, public_copy=public_copy),
        now,
    )
    return repository, version, job


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_reading_document_persists_first_write_wins(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted(session, public_copy)
        frozen = relationship_deep_reading_document(
            accepted,
            brief=brief,
            candidate=candidate,
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        first = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(job.id),
        )
        copy_row = await repository.get_accepted_copy(version.id)

        assert frozen.errors == ()
        assert frozen.document is not None
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        version_loaded = await repository.load_reading_document(version.id)
        assert loaded is not None
        assert version_loaded is not None
        assert loaded.model_dump(mode="json") == first_dump
        assert version_loaded.model_dump(mode="json") == first_dump


async def test_persist_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=generation.candidate,
        output_contract=contract,
        reading_version_id=uuid4(),
        relationship_type="romantic",
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted(session, public_copy)
        persisted = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(job.id),
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_persist_fail_closed_when_accepted_copy_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, accepted, _public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, _profile, version, job, _contracts = await create_reading_graph(session)
        frozen = relationship_deep_reading_document(
            accepted,
            brief=brief,
            candidate=candidate,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        persisted = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(job.id),
        )

        assert frozen.document is not None
        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_accepted_copy_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_persist_fail_closed_when_rewritten_document_would_overwrite(
    reading_database: Any,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted(session, public_copy)
        frozen = relationship_deep_reading_document(
            accepted,
            brief=brief,
            candidate=candidate,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        first = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(job.id),
        )
        assert first.document is not None
        rewritten = RelationshipDeepDocumentResult(
            document=frozen.document.model_copy(
                update={"answer_summary": "第二次不得覆盖的改写。"}
            )
            if frozen.document is not None
            else None,
            errors=(),
        )
        overwritten = await relationship_deep_persist_reading_document(
            rewritten,
            repository=repository,
            job_id=str(job.id),
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

        assert overwritten.document is None
        assert overwritten.created is False
        assert overwritten.errors == ("relationship_deep_reading_document_immutable",)
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first.document.model_dump(mode="json")
        assert loaded.answer_summary != "第二次不得覆盖的改写。"


async def test_persist_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted(session, public_copy))[:2]
        frozen = relationship_deep_reading_document(
            accepted,
            brief=brief,
            candidate=candidate,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        persisted = await relationship_deep_persist_reading_document(
            frozen,
            repository=repository,
            job_id=str(uuid4()),
        )

        assert frozen.document is not None
        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


async def _warehouse_accepted_with_candidate(session: Any, public_copy: str, candidate: Any):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_successful_attempt(
        str(job.id),
        1,
        candidate,
        public_copy,
        now,
    )
    await repository.record_accepted(
        str(job.id),
        contracts.Accepted(state_token=_PREPARED_TOKEN, public_copy=public_copy),
        now,
    )
    return repository, version, job


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_candidate_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_candidate(
            session, public_copy, candidate
        )
        first = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(job.id),
            brief=brief,
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        replay = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(job.id),
            brief=brief,
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        stored = await repository.load_successful_candidate(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_candidate_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_candidate(
            session, public_copy, generation.candidate
        )
        persisted = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(job.id),
            brief=brief,
            output_contract=contract,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_candidate_fail_closed_when_candidate_missing(
    reading_database: Any,
) -> None:
    brief, _candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted(session, public_copy)
        persisted = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(job.id),
            brief=brief,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert await repository.load_successful_candidate(str(job.id)) is None
        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_candidate_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_candidate_fail_closed_when_stored_candidate_rewritten(
    reading_database: Any,
) -> None:
    brief, _candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    rewritten = extract_relationship_deep_candidate(
        _brief(
            signals=[
                _signal("one", "这是改写后的合婚吉凶断言。"),
                _signal("two", SIGNAL_B),
                _signal("three", SIGNAL_C),
            ],
        ),
        "bazi-relationship-deep-output-v1",
    )
    assert rewritten.candidate is not None
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_candidate(
            session, public_copy, rewritten.candidate
        )
        persisted = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(job.id),
            brief=brief,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_signals_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_candidate_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_candidate(
            session, public_copy, candidate
        ))[:2]
        persisted = await relationship_deep_persist_job_candidate(
            accepted,
            repository=repository,
            job_id=str(uuid4()),
            brief=brief,
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


async def _warehouse_accepted_with_prepared(
    session: Any, public_copy: str, candidate: Any, brief: Any
):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_prepared(
        str(job.id),
        contracts.Prepared(state_token=_PREPARED_TOKEN, brief=brief),
        now,
    )
    await repository.record_successful_attempt(
        str(job.id),
        1,
        candidate,
        public_copy,
        now,
    )
    await repository.record_accepted(
        str(job.id),
        contracts.Accepted(state_token=_PREPARED_TOKEN, public_copy=public_copy),
        now,
    )
    return repository, version, job


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_prepared_brief_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        first = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        replay = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        stored = await repository.load_prepared_brief(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored is not None
        assert stored.to_dict() == brief.to_dict()
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_prepared_brief_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    intent = relationship_deep_complete_intent(
        state_token=_PREPARED_TOKEN,
        public_copy=public_copy,
        output_contract=contract,
    )
    accepted = await relationship_deep_fake_runtime_accept(intent, _RaisingRuntime())
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        persisted = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(job.id),
            output_contract=contract,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_prepared_brief_fail_closed_when_brief_missing(
    reading_database: Any,
) -> None:
    _brief_in, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_candidate(
            session, public_copy, candidate
        )
        persisted = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert await repository.load_prepared_brief(str(job.id)) is None
        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_prepared_brief_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_prepared_brief_fail_closed_when_stored_brief_rewritten(
    reading_database: Any,
) -> None:
    _brief_in, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    rewritten = _brief(
        signals=[
            _signal("one", "这是改写后的合婚吉凶断言。"),
            _signal("two", SIGNAL_B),
            _signal("three", SIGNAL_C),
        ],
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, rewritten
        )
        persisted = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_signals_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_prepared_brief_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_prepared(
            accepted,
            repository=repository,
            job_id=str(uuid4()),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


async def _warehouse_prepared_with_candidate(
    session: Any, public_copy: str, candidate: Any, brief: Any
):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_prepared(
        str(job.id),
        contracts.Prepared(state_token=_PREPARED_TOKEN, brief=brief),
        now,
    )
    await repository.record_successful_attempt(
        str(job.id),
        1,
        candidate,
        public_copy,
        now,
    )
    return repository, version, job


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_accepted_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        first = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        replay = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        stored = await repository.load_accepted(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored is not None
        assert stored.public_copy == public_copy
        assert stored.state_token == _PREPARED_TOKEN
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_accepted_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        persisted = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract,
            reading_version_id=version.id,
            relationship_type="romantic",
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_accepted_fail_closed_when_accepted_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_prepared_with_candidate(
            session, public_copy, candidate, brief
        )
        persisted = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert await repository.load_accepted(str(job.id)) is None
        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_accepted_copy_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_accepted_fail_closed_when_stored_accepted_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, _public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    rewritten = "这是改写后的合婚吉凶断言。"
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, rewritten, candidate, brief
        )
        persisted = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_signals_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None


async def test_job_accepted_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_accepted(
            repository=repository,
            job_id=str(uuid4()),
            output_contract="bazi-relationship-deep-output-v1",
            reading_version_id=version.id,
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


class _VersionOverrideStore:
    def __init__(self, inner: Any, version_id: Any) -> None:
        self._inner = inner
        self._version_id = version_id

    async def load_reading_version_id(self, job_id: str) -> Any:
        del job_id
        return self._version_id

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_version_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        first = await relationship_deep_persist_job_version(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            relationship_type="romantic",
        )
        replay = await relationship_deep_persist_job_version(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract_id,
            relationship_type="romantic",
        )
        stored = await repository.load_reading_version_id(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored == version.id
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert first.document.reading_version_id == str(version.id)
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_version_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        persisted = await relationship_deep_persist_job_version(
            repository=repository,
            job_id=str(job.id),
            output_contract=contract,
            relationship_type="romantic",
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_version_fail_closed_when_version_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        persisted = await relationship_deep_persist_job_version(
            repository=_VersionOverrideStore(repository, None),
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_version_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_version_fail_closed_when_stored_version_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        persisted = await relationship_deep_persist_job_version(
            repository=_VersionOverrideStore(repository, uuid4()),
            job_id=str(job.id),
            output_contract="bazi-relationship-deep-output-v1",
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_version_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_version(
            repository=repository,
            job_id=str(uuid4()),
            output_contract="bazi-relationship-deep-output-v1",
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


def _bind_job_output_contract(job: Any, output_contract: object) -> None:
    job.output_contract = resolve_output_contract(output_contract).to_dict()


def _bind_api_job_product(job: Any, product_id: str) -> None:
    job.output_contract = output_contract_for_product(
        product_id, ("relationship",)
    ).to_dict()


class _OutputContractOverrideStore:
    def __init__(self, inner: Any, contract: Any) -> None:
        self._inner = inner
        self._contract = contract

    async def load_output_contract(self, job_id: str) -> Any:
        del job_id
        return self._contract

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_output_contract_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, contract_id)
        first = await relationship_deep_persist_job_output_contract(
            repository=repository,
            job_id=str(job.id),
            relationship_type="romantic",
        )
        replay = await relationship_deep_persist_job_output_contract(
            repository=repository,
            job_id=str(job.id),
            relationship_type="romantic",
        )
        stored = await repository.load_output_contract(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored is not None
        assert stored.contract_id == contract_id
        assert stored.to_dict() == resolve_output_contract(contract_id).to_dict()
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert first.document.reading_version_id == str(version.id)
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_output_contract_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        _bind_job_output_contract(job, contract)
        persisted = await relationship_deep_persist_job_output_contract(
            repository=repository,
            job_id=str(job.id),
            relationship_type="romantic",
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_output_contract_fail_closed_when_contract_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        persisted = await relationship_deep_persist_job_output_contract(
            repository=_OutputContractOverrideStore(repository, None),
            job_id=str(job.id),
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_output_contract_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_output_contract_fail_closed_when_stored_contract_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "ziwei-relationship-deep-output-v1")
        persisted = await relationship_deep_persist_job_output_contract(
            repository=repository,
            job_id=str(job.id),
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_signals_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_output_contract_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_output_contract(
            repository=repository,
            job_id=str(uuid4()),
            relationship_type="romantic",
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


def _bind_job_relationship_type(version: Any, relationship_type: str | None) -> None:
    version.relationship_type = relationship_type


class _RelationshipTypeOverrideStore:
    def __init__(self, inner: Any, relationship_type: Any) -> None:
        self._inner = inner
        self._relationship_type = relationship_type

    async def load_relationship_type(self, job_id: str) -> Any:
        del job_id
        return self._relationship_type

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_relationship_type_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, contract_id)
        _bind_job_relationship_type(version, "romantic")
        first = await relationship_deep_persist_job_relationship_type(
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_job_relationship_type(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_relationship_type(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored == "romantic"
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert first.document.reading_version_id == str(version.id)
        assert first.document.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_relationship_type_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        _bind_job_output_contract(job, contract)
        _bind_job_relationship_type(version, "romantic")
        persisted = await relationship_deep_persist_job_relationship_type(
            repository=repository,
            job_id=str(job.id),
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_relationship_type_fail_closed_when_type_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        persisted = await relationship_deep_persist_job_relationship_type(
            repository=_RelationshipTypeOverrideStore(repository, None),
            job_id=str(job.id),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_relationship_type_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_relationship_type_fail_closed_when_stored_type_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "合婚吉凶")
        persisted = await relationship_deep_persist_job_relationship_type(
            repository=repository,
            job_id=str(job.id),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_relationship_type_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_relationship_type(
            repository=repository,
            job_id=str(uuid4()),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


class _RuntimeReleaseOverrideStore:
    def __init__(self, inner: Any, runtime_release: Any) -> None:
        self._inner = inner
        self._runtime_release = runtime_release

    async def load_runtime_release(self, job_id: str) -> Any:
        del job_id
        return self._runtime_release

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_job_runtime_release_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, contract_id)
        _bind_job_relationship_type(version, "romantic")
        first = await relationship_deep_persist_job_runtime_release(
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_job_runtime_release(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_runtime_release(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)

        assert stored == "mingli-master-portable-core@5.1"
        assert first.errors == ()
        assert first.created is True
        assert first.document is not None
        assert first.document.reading_version_id == str(version.id)
        assert first.document.versions.runtime_release == stored
        assert first.document.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert first.document.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert first.document.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in first.document.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in first.document.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in first.document.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = first.document.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        loaded = await repository.load_reading_document_for_job(str(job.id))
        assert loaded is not None
        assert loaded.model_dump(mode="json") == first_dump


async def test_job_runtime_release_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, generation.candidate, brief
        )
        _bind_job_output_contract(job, contract)
        _bind_job_relationship_type(version, "romantic")
        persisted = await relationship_deep_persist_job_runtime_release(
            repository=repository,
            job_id=str(job.id),
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_job_runtime_release_fail_closed_when_release_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        persisted = await relationship_deep_persist_job_runtime_release(
            repository=_RuntimeReleaseOverrideStore(repository, None),
            job_id=str(job.id),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_runtime_release_missing",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_runtime_release_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        persisted = await relationship_deep_persist_job_runtime_release(
            repository=_RuntimeReleaseOverrideStore(repository, " \t "),
            job_id=str(job.id),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_job_runtime_release_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_accepted_with_prepared(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_job_runtime_release(
            repository=repository,
            job_id=str(uuid4()),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


async def _warehouse_completing(session: Any, public_copy: str, candidate: Any, brief: Any):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_prepared(
        str(job.id),
        contracts.Prepared(state_token=_PREPARED_TOKEN, brief=brief),
        now,
    )
    await repository.record_successful_attempt(
        str(job.id),
        1,
        candidate,
        public_copy,
        now,
    )
    return repository, version, job


def _relationship_deep_orchestrator(repository: Any) -> ReadingOrchestrator:
    return ReadingOrchestrator(
        repository=repository,
        runtime=FakeMingliRuntimeAdapter(),
        model=FakeModelGateway(),
        guard=NarrativeGuard(),
        assembler=PublicCopyAssembler(),
        clock=FixedClock(),
    )


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_orchestrator_entry_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_completing(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, contract_id)
        _bind_job_relationship_type(version, "romantic")
        first_outcome = await _relationship_deep_orchestrator(repository).run(str(job.id))
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_runtime_release(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)
        loaded = await repository.load_reading_document_for_job(str(job.id))

        assert first_outcome.status is ReadingStatus.ACCEPTED
        assert first_outcome.public_copy == public_copy
        assert stored == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version.id)
        assert loaded.versions.runtime_release == stored
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump


async def test_orchestrator_entry_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    generation = await FakeModelGateway().generate(_generate_request(brief, contract))
    public_copy = PublicCopyAssembler().assemble(
        generation.candidate,
        brief,
        contract,
    )
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_completing(
            session, public_copy, generation.candidate, brief
        )
        _bind_job_output_contract(job, contract)
        _bind_job_relationship_type(_version, "romantic")
        outcome = await _relationship_deep_orchestrator(repository).run(str(job.id))
        persisted = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert outcome.status is ReadingStatus.ACCEPTED
    assert persisted.document is None
    assert persisted.created is False
    assert persisted.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None


async def test_orchestrator_entry_fail_closed_when_release_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_completing(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_orchestrator(
                _RuntimeReleaseOverrideStore(repository, None)
            ).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_orchestrator_entry_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_completing(
            session, public_copy, candidate, brief
        )
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_orchestrator(
                _RuntimeReleaseOverrideStore(repository, " \t ")
            ).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_orchestrator_entry_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief, candidate, _accepted, public_copy = await _accepted_document_inputs(
        "bazi-relationship-deep-output-v1"
    )
    async with reading_database.sessions() as session, session.begin():
        repository, version = (await _warehouse_completing(
            session, public_copy, candidate, brief
        ))[:2]
        persisted = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(uuid4()),
        )

        assert persisted.document is None
        assert persisted.created is False
        assert persisted.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_reading_document(version.id) is None


class _RaisingModel:
    async def generate(self, request: NarrativeRequest) -> Any:
        del request
        raise AssertionError("model.generate must not run for relationship-deep")


class _PreparedBriefOverrideStore:
    def __init__(self, inner: Any, brief: Any) -> None:
        self._inner = inner
        self._brief = brief

    async def load_prepared_brief(self, job_id: str) -> Any:
        del job_id
        return self._brief

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


async def _warehouse_prepared(session: Any, brief: Any):
    repository, _profile, version, job, contracts = await create_reading_graph(session)
    now = datetime.now(UTC)
    await repository.record_prepared(
        str(job.id),
        contracts.Prepared(state_token=_PREPARED_TOKEN, brief=brief),
        now,
    )
    return repository, version, job


def _relationship_deep_generate_entry(
    repository: Any, *, model: Any | None = None
) -> ReadingOrchestrator:
    return ReadingOrchestrator(
        repository=repository,
        runtime=FakeMingliRuntimeAdapter(),
        model=model if model is not None else _RaisingModel(),
        guard=NarrativeGuard(),
        assembler=PublicCopyAssembler(),
        clock=FixedClock(),
    )


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_orchestrator_prepared_run_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, contract_id)
        _bind_job_relationship_type(version, "romantic")
        first_outcome = await _relationship_deep_generate_entry(repository).run(str(job.id))
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_successful_candidate(str(job.id))
        loaded = await repository.load_reading_document_for_job(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)
        runtime_release = await repository.load_runtime_release(str(job.id))

        assert first_outcome.status is ReadingStatus.ACCEPTED
        assert first_outcome.public_copy == public_copy
        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert WRAPPER_TEXT not in {block.text for block in stored.blocks}
        assert generated.errors == ()
        assert generated.candidate is not None
        assert tuple(block.text for block in generated.candidate.blocks) == tuple(
            block.text for block in stored.blocks
        )
        assert runtime_release == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version.id)
        assert loaded.versions.runtime_release == runtime_release
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{_PREPARED_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump


async def test_orchestrator_generate_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, contract)
        outcome = await _relationship_deep_generate_entry(
            repository, model=FakeModelGateway()
        ).run(str(job.id))
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_successful_candidate(str(job.id))

    assert outcome.status is ReadingStatus.COMPLETING
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert stored is not None
    assert tuple(block.text for block in stored.blocks) == (
        "这是合同测试候选稿，不是正式命理解读。",
    )
    assert SIGNAL_A not in {block.text for block in stored.blocks}


async def test_orchestrator_generate_fail_closed_when_signals_missing(
    reading_database: Any,
) -> None:
    brief = _brief(signals=[])
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_generate_entry(repository).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_generate_fail_closed_when_brief_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_generate_entry(
                _PreparedBriefOverrideStore(repository, None)
            ).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_generate_fail_closed_when_stored_brief_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_generate_entry(
                _PreparedBriefOverrideStore(repository, _brief(signals=[]))
            ).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_generate_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(uuid4()),
        )

        assert generated.candidate is None
        assert generated.errors == ("relationship_deep_reading_document_unavailable",)
        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_prepared_run_fail_closed_when_relationship_type_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_generate_entry(repository).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_orchestrator_prepared_run_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_prepared(session, brief)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_generate_entry(
                _RuntimeReleaseOverrideStore(repository, " \t ")
            ).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


class _RelationshipDeepPrepareRuntime:
    def __init__(self, brief: ReadingBrief) -> None:
        self._inner = FakeMingliRuntimeAdapter()
        self._brief = brief
        self.prepare_commands: list[Any] = []

    async def execute(self, command: Any) -> Any:
        if isinstance(command, Prepare):
            self.prepare_commands.append(command)
            return Prepared(state_token=FAKE_STATE_TOKEN, brief=self._brief)
        return await self._inner.execute(command)


async def _warehouse_unprepared(session: Any, *, available_at: datetime | None = None):
    repository, _profile, version, job, _contracts = await create_reading_graph(
        session,
        available_at=available_at,
    )
    return repository, version, job


def _relationship_deep_prepare_entry(
    repository: Any, *, runtime: Any | None = None, model: Any | None = None
) -> ReadingOrchestrator:
    return ReadingOrchestrator(
        repository=repository,
        runtime=runtime if runtime is not None else FakeMingliRuntimeAdapter(),
        model=model if model is not None else _RaisingModel(),
        guard=NarrativeGuard(),
        assembler=PublicCopyAssembler(),
        clock=FixedClock(),
    )


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_orchestrator_prepare_run_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, contract_id)
        _bind_job_relationship_type(version, "romantic")
        first_outcome = await _relationship_deep_prepare_entry(
            repository, runtime=runtime
        ).run(str(job.id))
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored_brief = await repository.load_prepared_brief(str(job.id))
        stored = await repository.load_successful_candidate(str(job.id))
        loaded = await repository.load_reading_document_for_job(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)
        runtime_release = await repository.load_runtime_release(str(job.id))

        assert runtime.prepare_commands
        assert first_outcome.status is ReadingStatus.ACCEPTED
        assert first_outcome.public_copy == public_copy
        assert stored_brief is not None
        assert stored_brief.to_dict() == brief.to_dict()
        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert WRAPPER_TEXT not in {block.text for block in stored.blocks}
        assert generated.errors == ()
        assert generated.candidate is not None
        assert tuple(block.text for block in generated.candidate.blocks) == tuple(
            block.text for block in stored.blocks
        )
        assert runtime_release == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version.id)
        assert loaded.versions.runtime_release == runtime_release
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump


async def test_orchestrator_prepare_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    contract = output_contract_for_product("bazi-relationship", ("relationship",))
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, contract)
        outcome = await _relationship_deep_prepare_entry(
            repository, runtime=runtime
        ).run(str(job.id))
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_successful_candidate(str(job.id))
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert outcome.status is ReadingStatus.PREPARED
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert stored is None
    assert loaded is None
    assert runtime.prepare_commands


async def test_orchestrator_prepare_fail_closed_when_signals_missing(
    reading_database: Any,
) -> None:
    brief = _brief(signals=[])
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_prepare_entry(
                repository, runtime=_RelationshipDeepPrepareRuntime(brief)
            ).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_prepare_fail_closed_when_brief_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_prepare_entry(
                _PreparedBriefOverrideStore(repository, None),
                runtime=_RelationshipDeepPrepareRuntime(brief),
            ).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_prepare_fail_closed_when_stored_brief_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await _relationship_deep_prepare_entry(
                _PreparedBriefOverrideStore(repository, _brief(signals=[])),
                runtime=_RelationshipDeepPrepareRuntime(brief),
            ).run(str(job.id))

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_orchestrator_prepare_fail_closed_when_relationship_type_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_prepare_entry(
                repository, runtime=_RelationshipDeepPrepareRuntime(brief)
            ).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_orchestrator_prepare_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_job_output_contract(job, "bazi-relationship-deep-output-v1")
        _bind_job_relationship_type(version, "romantic")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await _relationship_deep_prepare_entry(
                _RuntimeReleaseOverrideStore(repository, " \t "),
                runtime=_RelationshipDeepPrepareRuntime(brief),
            ).run(str(job.id))

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_api_job_prepare_run_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, _CONTRACT_API_PRODUCT[contract_id])
        _bind_job_relationship_type(version, "romantic")
        first = await relationship_deep_prepare_orchestrator(
            repository=repository,
            job_id=str(job.id),
            runtime=runtime,
            clock=FixedClock(),
        )
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored_brief = await repository.load_prepared_brief(str(job.id))
        stored = await repository.load_successful_candidate(str(job.id))
        loaded = await repository.load_reading_document_for_job(str(job.id))
        copy_row = await repository.get_accepted_copy(version.id)
        runtime_release = await repository.load_runtime_release(str(job.id))

        assert runtime.prepare_commands
        assert first.errors == ()
        assert first.status is ReadingStatus.ACCEPTED
        assert first.public_copy == public_copy
        assert stored_brief is not None
        assert stored_brief.to_dict() == brief.to_dict()
        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert WRAPPER_TEXT not in {block.text for block in stored.blocks}
        assert generated.errors == ()
        assert generated.candidate is not None
        assert tuple(block.text for block in generated.candidate.blocks) == tuple(
            block.text for block in stored.blocks
        )
        assert runtime_release == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version.id)
        assert loaded.versions.runtime_release == runtime_release
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump


async def test_api_job_prepare_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship")
        prepared = await relationship_deep_prepare_orchestrator(
            repository=repository,
            job_id=str(job.id),
            runtime=runtime,
            clock=FixedClock(),
        )
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=str(job.id),
        )
        stored = await repository.load_successful_candidate(str(job.id))
        loaded = await repository.load_reading_document_for_job(str(job.id))

    assert prepared.status is None
    assert prepared.public_copy is None
    assert prepared.errors == ("relationship_deep_extract_not_applicable",)
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert stored is None
    assert loaded is None
    assert runtime.prepare_commands == []


async def test_api_job_prepare_fail_closed_when_signals_missing(
    reading_database: Any,
) -> None:
    brief = _brief(signals=[])
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await relationship_deep_prepare_orchestrator(
                repository=repository,
                job_id=str(job.id),
                runtime=_RelationshipDeepPrepareRuntime(brief),
                clock=FixedClock(),
            )

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_api_job_prepare_fail_closed_when_brief_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await relationship_deep_prepare_orchestrator(
                repository=_PreparedBriefOverrideStore(repository, None),
                job_id=str(job.id),
                runtime=_RelationshipDeepPrepareRuntime(brief),
                clock=FixedClock(),
            )

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_api_job_prepare_fail_closed_when_stored_brief_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without extract candidate",
        ):
            await relationship_deep_prepare_orchestrator(
                repository=_PreparedBriefOverrideStore(repository, _brief(signals=[])),
                job_id=str(job.id),
                runtime=_RelationshipDeepPrepareRuntime(brief),
                clock=FixedClock(),
            )

        assert await repository.load_successful_candidate(str(job.id)) is None


async def test_api_job_prepare_fail_closed_when_relationship_type_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await relationship_deep_prepare_orchestrator(
                repository=repository,
                job_id=str(job.id),
                runtime=_RelationshipDeepPrepareRuntime(brief),
                clock=FixedClock(),
            )

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_api_job_prepare_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        _bind_job_relationship_type(version, "romantic")
        with pytest.raises(
            OrchestratorInvariantError,
            match="without ReadingDocument",
        ):
            await relationship_deep_prepare_orchestrator(
                repository=_RuntimeReleaseOverrideStore(repository, " \t "),
                job_id=str(job.id),
                runtime=_RelationshipDeepPrepareRuntime(brief),
                clock=FixedClock(),
            )

        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_api_job_prepare_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        prepared = await relationship_deep_prepare_orchestrator(
            repository=repository,
            job_id=str(uuid4()),
            runtime=runtime,
            clock=FixedClock(),
        )

        assert prepared.status is None
        assert prepared.public_copy is None
        assert prepared.errors == ("relationship_deep_reading_document_unavailable",)
        assert runtime.prepare_commands == []
        assert await repository.load_reading_document_for_job(str(job.id)) is None
        assert await repository.load_reading_document(version.id) is None


async def test_api_job_prepare_fail_closed_when_contract_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    async with reading_database.sessions() as session, session.begin():
        repository, _version, job = await _warehouse_unprepared(session)
        _bind_api_job_product(job, "bazi-relationship-deep")
        prepared = await relationship_deep_prepare_orchestrator(
            repository=_OutputContractOverrideStore(repository, None),
            job_id=str(job.id),
            runtime=runtime,
            clock=FixedClock(),
        )

        assert prepared.status is None
        assert prepared.public_copy is None
        assert prepared.errors == ("relationship_deep_output_contract_missing",)
        assert runtime.prepare_commands == []
        assert await repository.load_successful_candidate(str(job.id)) is None


_WORKER_ID = "relationship-deep-prepare-worker"
_WORKER_CIPHER = EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")


def _existing_worker(
    database: Any,
    *,
    runtime: Any,
    orchestrator_factory: Any | None = None,
    cipher: EnvelopeCipher | None = None,
    clock: Any | None = None,
) -> Any:
    readings = importlib.import_module("worker.readings")
    resolved_clock = clock or FixedClock()
    resolved_cipher = cipher or _WORKER_CIPHER
    factory = orchestrator_factory or readings.SqlReadingOrchestratorFactory(
        cipher=resolved_cipher,
        runtime=runtime,
        model=_RaisingModel(),
        clock=resolved_clock,
        alert_sink=NoopAlertSink(),
    )
    return readings.build_worker(
        source=readings.ReadingJobWorkSource(
            sessions=database.sessions,
            worker_id=_WORKER_ID,
            clock=resolved_clock,
            cipher=resolved_cipher,
        ),
        processor=readings.ReadingJobProcessor(
            sessions=database.sessions,
            orchestrator_factory=factory,
            worker_id=_WORKER_ID,
            clock=resolved_clock,
        ),
    )


def _worker_factory_with_store(
    runtime: Any,
    wrap: Any,
    *,
    cipher: EnvelopeCipher | None = None,
) -> Any:
    readings = importlib.import_module("worker.readings")
    clock = FixedClock()
    resolved_cipher = cipher or _WORKER_CIPHER

    def factory(session: Any) -> Any:
        repository = wrap(SqlReadingRepository(session, resolved_cipher))
        fallback = ReadingOrchestrator(
            repository=SqlReadingRepository(session, resolved_cipher),
            runtime=runtime,
            model=_RaisingModel(),
            guard=NarrativeGuard(),
            assembler=PublicCopyAssembler(),
            clock=clock,
        )
        return readings.RelationshipDeepPrepareOrchestratorRunner(
            repository=repository,
            runtime=runtime,
            model=_RaisingModel(),
            clock=clock,
            fallback=fallback,
        )

    return factory


async def _seed_worker_job(
    database: Any,
    *,
    product_id: str,
    relationship_type: str | None = None,
) -> tuple[str, UUID]:
    async with database.sessions() as session, session.begin():
        _repository, version, job = await _warehouse_unprepared(
            session,
            available_at=FixedClock().now(),
        )
        _bind_api_job_product(job, product_id)
        if relationship_type is not None:
            _bind_job_relationship_type(version, relationship_type)
        return str(job.id), version.id


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_worker_prepare_run_persists_reading_document(
    reading_database: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, version_id = await _seed_worker_job(
        reading_database,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
        relationship_type="romantic",
    )
    worker = _existing_worker(reading_database, runtime=runtime)

    assert await worker.run_once() is True

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        stored_brief = await repository.load_prepared_brief(job_id)
        stored = await repository.load_successful_candidate(job_id)
        loaded = await repository.load_reading_document_for_job(job_id)
        copy_row = await repository.get_accepted_copy(version_id)
        runtime_release = await repository.load_runtime_release(job_id)
        job = await session.get(ReadingJobRecord, UUID(job_id))

        assert runtime.prepare_commands
        assert job is not None
        assert job.status == "complete"
        assert stored_brief is not None
        assert stored_brief.to_dict() == brief.to_dict()
        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert WRAPPER_TEXT not in {block.text for block in stored.blocks}
        assert generated.errors == ()
        assert generated.candidate is not None
        assert tuple(block.text for block in generated.candidate.blocks) == tuple(
            block.text for block in stored.blocks
        )
        assert runtime_release == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version_id)
        assert loaded.versions.runtime_release == runtime_release
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        accepted = await repository.load_accepted(job_id)
        assert accepted is not None
        assert accepted.public_copy == public_copy


async def test_worker_prepare_does_not_apply_to_free_relationship_preview(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, _version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship",
    )
    worker = _existing_worker(reading_database, runtime=runtime)

    assert await worker.run_once() is True

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        stored = await repository.load_successful_candidate(job_id)
        loaded = await repository.load_reading_document_for_job(job_id)
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert stored is None
    assert loaded is None
    assert runtime.prepare_commands


async def test_worker_prepare_fail_closed_when_signals_missing(
    reading_database: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, _version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
        relationship_type="romantic",
    )
    worker = _existing_worker(reading_database, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_successful_candidate(job_id) is None


async def test_worker_prepare_fail_closed_when_brief_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, _version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
        relationship_type="romantic",
    )
    worker = _existing_worker(
        reading_database,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_successful_candidate(job_id) is None


async def test_worker_prepare_fail_closed_when_stored_brief_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, _version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
        relationship_type="romantic",
    )
    worker = _existing_worker(
        reading_database,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_successful_candidate(job_id) is None


async def test_worker_prepare_fail_closed_when_relationship_type_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
    )
    worker = _existing_worker(reading_database, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_worker_prepare_fail_closed_when_stored_release_rewritten(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
        relationship_type="romantic",
    )
    worker = _existing_worker(
        reading_database,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_worker_prepare_fail_closed_when_job_is_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    worker = _existing_worker(reading_database, runtime=runtime)

    assert await worker.run_once() is False
    assert runtime.prepare_commands == []


async def test_worker_prepare_fail_closed_when_contract_missing(
    reading_database: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    job_id, _version_id = await _seed_worker_job(
        reading_database,
        product_id="bazi-relationship-deep",
        relationship_type="romantic",
    )
    worker = _existing_worker(
        reading_database,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    async with reading_database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, _WORKER_CIPHER)
        assert await repository.load_successful_candidate(job_id) is None
        assert runtime.prepare_commands == []


async def _seed_public_http_session(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    *,
    product_id: str,
    relationship_type: str | None = "romantic",
) -> tuple[str, UUID, dict[str, str]]:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    second = await create_confirmed_profile(
        client, headers, location="上海市浦东新区"
    )
    await seed_runtime_release(database, test_settings)
    payload: dict[str, Any] = {
        "profile_version_ids": [
            first["profile_version_id"],
            second["profile_version_id"],
        ],
    }
    if relationship_type is not None:
        payload["relationship_type"] = relationship_type
    started = await client.post(
        f"/api/v1/readings/{product_id}",
        headers=headers,
        json=payload,
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert body["product_id"] == product_id
    version_id = UUID(body["reading_version_id"])
    async with database.sessions() as session:
        job = (
            await session.execute(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version_id
                )
            )
        ).scalar_one()
        return str(job.id), version_id, headers


async def _seed_public_http_job(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    *,
    product_id: str,
    relationship_type: str | None = "romantic",
) -> tuple[str, UUID]:
    job_id, version_id, _headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id=product_id,
        relationship_type=relationship_type,
    )
    return job_id, version_id


def _http_cipher(settings: Any) -> EnvelopeCipher:
    return EnvelopeCipher.from_settings(settings)


def _http_clock() -> Any:
    readings = importlib.import_module("worker.readings")
    return readings.SystemClock()


def _http_worker(
    database: Any,
    test_settings: Any,
    *,
    runtime: Any,
    orchestrator_factory: Any | None = None,
) -> Any:
    return _existing_worker(
        database,
        runtime=runtime,
        orchestrator_factory=orchestrator_factory,
        cipher=_http_cipher(test_settings),
        clock=_http_clock(),
    )


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_public_http_prepare_run_persists_reading_document(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        stored_brief = await repository.load_prepared_brief(job_id)
        stored = await repository.load_successful_candidate(job_id)
        loaded = await repository.load_reading_document_for_job(job_id)
        copy_row = await repository.get_accepted_copy(version_id)
        runtime_release = await repository.load_runtime_release(job_id)
        job = await session.get(ReadingJobRecord, UUID(job_id))

        assert runtime.prepare_commands
        assert job is not None
        assert job.status == "complete"
        assert stored_brief is not None
        assert stored_brief.to_dict() == brief.to_dict()
        assert stored is not None
        assert tuple(block.text for block in stored.blocks) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert WRAPPER_TEXT not in {block.text for block in stored.blocks}
        assert generated.errors == ()
        assert generated.candidate is not None
        assert tuple(block.text for block in generated.candidate.blocks) == tuple(
            block.text for block in stored.blocks
        )
        assert runtime_release == "mingli-master-portable-core@5.1"
        assert loaded is not None
        assert loaded.reading_version_id == str(version_id)
        assert loaded.versions.runtime_release == runtime_release
        assert loaded.view_model.relationship_type == "romantic"
        assert copy_row is not None
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        replay_dump = replay.document.model_dump(mode="json") if replay.document else None
        first_dump = loaded.model_dump(mode="json")
        assert replay.errors == ()
        assert replay.created is False
        assert replay_dump == first_dump
        accepted = await repository.load_accepted(job_id)
        assert accepted is not None
        assert accepted.public_copy == public_copy


async def test_public_http_prepare_does_not_apply_to_free_relationship_preview(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, _version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        stored = await repository.load_successful_candidate(job_id)
        loaded = await repository.load_reading_document_for_job(job_id)
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert stored is None
    assert loaded is None
    assert runtime.prepare_commands


async def test_public_http_prepare_fail_closed_when_signals_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, _version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None


async def test_public_http_prepare_fail_closed_when_brief_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, _version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None


async def test_public_http_prepare_fail_closed_when_stored_brief_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, _version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None


async def test_public_http_prepare_fail_closed_when_relationship_type_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RelationshipTypeOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_prepare_fail_closed_when_stored_release_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_prepare_fail_closed_when_job_is_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    del client
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is False
    assert runtime.prepare_commands == []


async def test_public_http_prepare_fail_closed_when_contract_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, _version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert runtime.prepare_commands == []


class _AcceptedCopyTextOverrideStore:
    def __init__(self, inner: Any, text: str | None) -> None:
        self._inner = inner
        self._text = text

    async def load_accepted_copy(self, version_id: UUID) -> str | None:
        del version_id
        return self._text

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ReadingDocumentOverrideStore:
    def __init__(self, inner: Any, document: Any) -> None:
        self._inner = inner
        self._document = document

    async def load_reading_document(self, version_id: UUID) -> Any:
        del version_id
        return self._document

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_public_http_result_returns_accepted_document(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    replay = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    assert replay.status_code == 200, replay.text
    body = result.json()
    replay_body = replay.json()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        loaded = await repository.load_reading_document(version_id)
        accepted = await repository.load_accepted(job_id)
        copy_row = await repository.get_accepted_copy(version_id)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        persist_replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

        assert runtime.prepare_commands
        assert job is not None
        assert job.status == "complete"
        assert body["status"] == "accepted"
        assert accepted is not None
        assert body["accepted_copy"] == public_copy
        assert body["accepted_copy"] == accepted.public_copy
        assert loaded is not None
        assert copy_row is not None
        assert body["document"] == loaded.model_dump(mode="json")
        assert body["document"]["accepted_copy_ref"] == f"accepted-copy:{copy_row.id}"
        assert body["document"]["accepted_copy_ref"] != (
            f"accepted-copy:{FAKE_STATE_TOKEN}"
        )
        assert tuple(claim["text"] for claim in body["document"]["claims"]) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(
            claim["text"] in public_copy.split("\n\n")
            for claim in body["document"]["claims"]
        )
        assert WRAPPER_TEXT not in {
            claim["text"] for claim in body["document"]["claims"]
        }
        assert generated.errors == ()
        assert persist_replay.errors == ()
        assert persist_replay.created is False
        assert replay_body["document"] == body["document"]
        assert replay_body["accepted_copy"] == body["accepted_copy"]


async def test_public_http_result_does_not_apply_to_free_relationship_preview(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        loaded = await repository.load_reading_document(version_id)
        wired = await relationship_deep_http_result(
            repository=repository,
            reading_version_id=version_id,
            product_id="bazi-relationship",
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None
    assert body["document"] is None
    assert wired.document is None
    assert wired.errors == ("relationship_deep_extract_not_applicable",)
    assert runtime.prepare_commands


async def test_public_http_result_fail_closed_when_signals_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert await repository.load_accepted(job_id) is None
    assert body["document"] is None
    assert body["accepted_copy"] is None
    assert body["status"] != "accepted"


async def test_public_http_result_fail_closed_when_brief_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
    assert body["document"] is None
    assert body["accepted_copy"] is None


async def test_public_http_result_fail_closed_when_stored_brief_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
    assert body["document"] is None
    assert body["accepted_copy"] is None


async def test_public_http_result_fail_closed_when_relationship_type_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RelationshipTypeOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None
    assert body["document"] is None
    assert body["accepted_copy"] is None


async def test_public_http_result_fail_closed_when_stored_release_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None
    assert body["document"] is None
    assert body["accepted_copy"] is None


async def test_public_http_result_fail_closed_when_job_is_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    del database, test_settings
    await create_guest(client)
    result = await client.get(f"/api/v1/readings/{uuid4()}/result")
    assert result.status_code == 404


async def test_public_http_result_fail_closed_when_contract_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    body = result.json()
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert runtime.prepare_commands == []
    assert body["document"] is None
    assert body["accepted_copy"] is None


async def test_public_http_result_fail_closed_when_accepted_copy_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_result(
            repository=_AcceptedCopyTextOverrideStore(repository, "rewritten"),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_signals_missing",)


async def test_public_http_result_fail_closed_when_document_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_result(
            repository=_ReadingDocumentOverrideStore(repository, None),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_deep_reading_document_unavailable",)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_public_http_follow_up_returns_accepted_document(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-deep-v1"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    replayed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-deep-v1"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 201, followed.text
    assert replayed.status_code == 200, replayed.text
    follow_body = followed.json()
    follow_version_id = UUID(follow_body["reading_version_id"])
    assert follow_body["prior_answer"] == public_copy
    assert follow_body["version"] == 2
    assert follow_version_id != version_id
    assert replayed.json()["reading_version_id"] == str(follow_version_id)

    assert await worker.run_once() is True

    result = await client.get(f"/api/v1/readings/{follow_version_id}/result")
    replay = await client.get(f"/api/v1/readings/{follow_version_id}/result")
    assert result.status_code == 200, result.text
    assert replay.status_code == 200, replay.text
    body = result.json()
    replay_body = replay.json()

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        follow_job = (
            await session.execute(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == follow_version_id
                )
            )
        ).scalar_one()
        loaded = await repository.load_reading_document(follow_version_id)
        accepted = await repository.load_accepted(str(follow_job.id))
        copy_row = await repository.get_accepted_copy(follow_version_id)
        persist_replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=str(follow_job.id),
        )
        source_loaded = await repository.load_reading_document(version_id)

        assert runtime.prepare_commands
        assert follow_job.status == "complete"
        assert body["status"] == "accepted"
        assert accepted is not None
        assert body["accepted_copy"] == public_copy
        assert body["accepted_copy"] == accepted.public_copy
        assert follow_body["prior_answer"] == accepted.public_copy
        assert loaded is not None
        assert copy_row is not None
        assert body["document"] == loaded.model_dump(mode="json")
        assert body["document"]["accepted_copy_ref"] == f"accepted-copy:{copy_row.id}"
        assert body["document"]["accepted_copy_ref"] != (
            f"accepted-copy:{FAKE_STATE_TOKEN}"
        )
        assert tuple(claim["text"] for claim in body["document"]["claims"]) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(
            claim["text"] in public_copy.split("\n\n")
            for claim in body["document"]["claims"]
        )
        assert WRAPPER_TEXT not in {
            claim["text"] for claim in body["document"]["claims"]
        }
        assert persist_replay.errors == ()
        assert persist_replay.created is False
        assert replay_body["document"] == body["document"]
        assert replay_body["accepted_copy"] == body["accepted_copy"]
        assert source_loaded is not None
        assert source_loaded.model_dump(mode="json") != body["document"]


async def test_public_http_follow_up_does_not_apply_to_free_relationship_preview(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-free-v1"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        loaded = await repository.load_reading_document(version_id)
        wired = await relationship_deep_http_follow_up(
            repository=repository,
            reading_version_id=version_id,
            product_id="bazi-relationship",
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None
    assert wired.document is None
    assert wired.errors == ("relationship_deep_extract_not_applicable",)
    assert runtime.prepare_commands


async def test_public_http_follow_up_fail_closed_when_signals_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-no-signals"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert await repository.load_accepted(job_id) is None


async def test_public_http_follow_up_fail_closed_when_brief_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-no-brief"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_follow_up_fail_closed_when_stored_brief_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-brief-rewritten"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_follow_up_fail_closed_when_relationship_type_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RelationshipTypeOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-no-type"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_follow_up_fail_closed_when_stored_release_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-release-rewritten"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_follow_up_fail_closed_when_job_is_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    del database, test_settings
    headers = await create_guest(client)
    followed = await client.post(
        f"/api/v1/readings/{uuid4()}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-missing"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 404


async def test_public_http_follow_up_fail_closed_when_contract_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-no-contract"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 409, followed.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert runtime.prepare_commands == []


async def test_public_http_follow_up_fail_closed_when_accepted_copy_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_follow_up(
            repository=_AcceptedCopyTextOverrideStore(repository, "rewritten"),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_signals_missing",)

    followed = await client.post(
        f"/api/v1/readings/{version_id}/follow-up",
        headers={**headers, "Idempotency-Key": "follow-up-copy-ok"},
        json={"query": "基于已有结论，补充注意事项"},
    )
    assert followed.status_code == 201, followed.text


async def test_public_http_follow_up_fail_closed_when_document_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_follow_up(
            repository=_ReadingDocumentOverrideStore(repository, None),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_deep_reading_document_unavailable",)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_public_http_export_returns_accepted_document(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    payloads: dict[str, bytes] = {}
    for export_format, content_type, signature in (
        ("png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("pdf", "application/pdf", b"%PDF-"),
    ):
        created = await client.post(
            f"/api/v1/readings/{version_id}/export",
            headers=headers,
            json={"format": export_format},
        )
        replayed = await client.post(
            f"/api/v1/readings/{version_id}/export",
            headers=headers,
            json={"format": export_format},
        )
        assert created.status_code == 201, created.text
        assert replayed.status_code == 201, replayed.text
        body = created.json()
        replay_body = replayed.json()
        assert body["format"] == export_format
        assert replay_body["format"] == export_format
        assert body["content_type"] == content_type
        assert body["file_name"].endswith(f".{export_format}")
        assert replay_body["file_name"] == body["file_name"]

        downloaded = await client.get(f"/api/v1/exports/{body['token']}")
        replay_downloaded = await client.get(f"/api/v1/exports/{replay_body['token']}")
        assert downloaded.status_code == 200, downloaded.text
        assert replay_downloaded.status_code == 200, replay_downloaded.text
        assert downloaded.headers["content-type"].startswith(content_type)
        assert downloaded.content.startswith(signature)
        assert replay_downloaded.content.startswith(signature)
        if export_format == "png":
            assert replay_downloaded.content == downloaded.content
        payloads[export_format] = downloaded.content

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        loaded = await repository.load_reading_document(version_id)
        accepted = await repository.load_accepted(job_id)
        copy_row = await repository.get_accepted_copy(version_id)
        persist_replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        wired = await relationship_deep_http_export(
            repository=repository,
            reading_version_id=version_id,
            product_id=_CONTRACT_API_PRODUCT[contract_id],
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

        assert runtime.prepare_commands
        assert job is not None
        assert job.status == "complete"
        assert accepted is not None
        assert accepted.public_copy == public_copy
        assert loaded is not None
        assert copy_row is not None
        assert wired.errors == ()
        assert wired.accepted_copy == accepted.public_copy
        assert wired.document is not None
        assert wired.document.model_dump(mode="json") == loaded.model_dump(mode="json")
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        assert persist_replay.errors == ()
        assert persist_replay.created is False
        replay_wired = await relationship_deep_http_export(
            repository=repository,
            reading_version_id=version_id,
            product_id=_CONTRACT_API_PRODUCT[contract_id],
        )
        assert replay_wired.document is not None
        assert replay_wired.document.model_dump(mode="json") == loaded.model_dump(
            mode="json"
        )
        assert payloads["png"] == render_reading_export(loaded, "png").payload
        assert payloads["png"] == render_reading_export(wired.document, "png").payload
        assert payloads["pdf"].startswith(b"%PDF-")
        assert render_reading_export(loaded, "pdf").payload.startswith(b"%PDF-")


async def test_public_http_export_does_not_apply_to_free_relationship_preview(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        loaded = await repository.load_reading_document(version_id)
        wired = await relationship_deep_http_export(
            repository=repository,
            reading_version_id=version_id,
            product_id="bazi-relationship",
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None
    assert wired.document is None
    assert wired.errors == ("relationship_deep_extract_not_applicable",)
    assert runtime.prepare_commands


async def test_public_http_export_fail_closed_when_signals_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert await repository.load_accepted(job_id) is None


async def test_public_http_export_fail_closed_when_brief_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_export_fail_closed_when_stored_brief_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_export_fail_closed_when_relationship_type_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RelationshipTypeOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_export_fail_closed_when_stored_release_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_export_fail_closed_when_job_is_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    del database, test_settings
    headers = await create_guest(client)
    created = await client.post(
        f"/api/v1/readings/{uuid4()}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 404


async def test_public_http_export_fail_closed_when_contract_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert runtime.prepare_commands == []


async def test_public_http_export_fail_closed_when_accepted_copy_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_export(
            repository=_AcceptedCopyTextOverrideStore(repository, "rewritten"),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_signals_missing",)

    created = await client.post(
        f"/api/v1/readings/{version_id}/export",
        headers=headers,
        json={"format": "png"},
    )
    assert created.status_code == 201, created.text


async def test_public_http_export_fail_closed_when_document_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_export(
            repository=_ReadingDocumentOverrideStore(repository, None),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_deep_reading_document_unavailable",)


@pytest.mark.parametrize("contract_id", _CONTRACTS)
async def test_public_http_share_returns_accepted_document(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
    contract_id: str,
) -> None:
    brief = _brief(capability_id=_CONTRACT_CAPABILITY[contract_id])
    public_copy = _expected_public_copy((SIGNAL_A, SIGNAL_B, SIGNAL_C), contract_id)
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id=_CONTRACT_API_PRODUCT[contract_id],
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    replayed = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 201, created.text
    assert replayed.status_code == 201, replayed.text
    body = created.json()
    replay_body = replayed.json()
    assert body["token"]
    assert replay_body["token"]
    assert replay_body["token"] != body["token"]

    shared = await client.get(f"/api/v1/share/{body['token']}")
    replay_shared = await client.get(f"/api/v1/share/{replay_body['token']}")
    assert shared.status_code == 200, shared.text
    assert replay_shared.status_code == 200, replay_shared.text
    snapshot = shared.json()["document"]
    replay_snapshot = replay_shared.json()["document"]
    assert snapshot == replay_snapshot
    assert snapshot["schema_version"] == "shared-reading-document/v1"
    assert "view_model" not in snapshot
    assert "actions" not in snapshot

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        loaded = await repository.load_reading_document(version_id)
        accepted = await repository.load_accepted(job_id)
        copy_row = await repository.get_accepted_copy(version_id)
        persist_replay = await relationship_deep_persist_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        wired = await relationship_deep_http_share(
            repository=repository,
            reading_version_id=version_id,
            product_id=_CONTRACT_API_PRODUCT[contract_id],
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

        assert runtime.prepare_commands
        assert job is not None
        assert job.status == "complete"
        assert accepted is not None
        assert accepted.public_copy == public_copy
        assert loaded is not None
        assert copy_row is not None
        assert wired.errors == ()
        assert wired.accepted_copy == accepted.public_copy
        assert wired.document is not None
        assert wired.document.model_dump(mode="json") == loaded.model_dump(mode="json")
        assert loaded.accepted_copy_ref == f"accepted-copy:{copy_row.id}"
        assert loaded.accepted_copy_ref != f"accepted-copy:{FAKE_STATE_TOKEN}"
        assert tuple(claim.text for claim in loaded.claims) == (
            SIGNAL_A,
            SIGNAL_B,
            SIGNAL_C,
        )
        assert all(claim.text in public_copy.split("\n\n") for claim in loaded.claims)
        assert WRAPPER_TEXT not in {claim.text for claim in loaded.claims}
        assert persist_replay.errors == ()
        assert persist_replay.created is False
        replay_wired = await relationship_deep_http_share(
            repository=repository,
            reading_version_id=version_id,
            product_id=_CONTRACT_API_PRODUCT[contract_id],
        )
        assert replay_wired.document is not None
        assert replay_wired.document.model_dump(mode="json") == loaded.model_dump(
            mode="json"
        )
        expected_share = SharedReadingDocumentV1.from_document(loaded).model_dump(
            mode="json"
        )
        assert snapshot == expected_share
        assert snapshot == SharedReadingDocumentV1.from_document(
            wired.document
        ).model_dump(mode="json")


async def test_public_http_share_does_not_apply_to_free_relationship_preview(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)

    assert await worker.run_once() is True

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        generated = await relationship_deep_generate_orchestrator(
            repository=repository,
            job_id=job_id,
        )
        loaded = await repository.load_reading_document(version_id)
        wired = await relationship_deep_http_share(
            repository=repository,
            reading_version_id=version_id,
            product_id="bazi-relationship",
        )
        job = await session.get(ReadingJobRecord, UUID(job_id))

    assert job is not None
    assert job.status == "queued"
    assert generated.candidate is None
    assert generated.errors == ("relationship_deep_extract_not_applicable",)
    assert loaded is None
    assert wired.document is None
    assert wired.errors == ("relationship_deep_extract_not_applicable",)
    assert runtime.prepare_commands


async def test_public_http_share_fail_closed_when_signals_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief(signals=[])
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert await repository.load_accepted(job_id) is None


async def test_public_http_share_fail_closed_when_brief_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_share_fail_closed_when_stored_brief_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _PreparedBriefOverrideStore(
                repository, _brief(signals=[])
            ),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without extract candidate",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_share_fail_closed_when_relationship_type_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RelationshipTypeOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_share_fail_closed_when_stored_release_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _RuntimeReleaseOverrideStore(repository, " \t "),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_reading_document_for_job(job_id) is None
        assert await repository.load_reading_document(version_id) is None


async def test_public_http_share_fail_closed_when_job_is_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    del database, test_settings
    headers = await create_guest(client)
    created = await client.post(
        f"/api/v1/readings/{uuid4()}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 404


async def test_public_http_share_fail_closed_when_contract_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(
        database,
        test_settings,
        runtime=runtime,
        orchestrator_factory=_worker_factory_with_store(
            runtime,
            lambda repository: _OutputContractOverrideStore(repository, None),
            cipher=cipher,
        ),
    )
    with pytest.raises(
        OrchestratorInvariantError,
        match="relationship_deep_output_contract_missing",
    ):
        await worker.run_once()

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 409, created.text
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        assert await repository.load_successful_candidate(job_id) is None
        assert await repository.load_reading_document(version_id) is None
        assert runtime.prepare_commands == []


async def test_public_http_share_fail_closed_when_accepted_copy_rewritten(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id, headers = await _seed_public_http_session(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_share(
            repository=_AcceptedCopyTextOverrideStore(repository, "rewritten"),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_signals_missing",)

    created = await client.post(
        f"/api/v1/readings/{version_id}/share",
        headers=headers,
        json={"ttl_seconds": 3600},
    )
    assert created.status_code == 201, created.text


async def test_public_http_share_fail_closed_when_document_missing(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    brief = _brief()
    runtime = _RelationshipDeepPrepareRuntime(brief)
    cipher = _http_cipher(test_settings)
    _job_id, version_id = await _seed_public_http_job(
        client,
        database,
        test_settings,
        product_id="bazi-relationship-deep",
    )
    worker = _http_worker(database, test_settings, runtime=runtime)
    assert await worker.run_once() is True

    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(session, cipher)
        wired = await relationship_deep_http_share(
            repository=_ReadingDocumentOverrideStore(repository, None),
            reading_version_id=version_id,
            product_id="bazi-relationship-deep",
        )
        assert wired.document is None
        assert wired.accepted_copy is None
        assert wired.errors == ("relationship_deep_reading_document_unavailable",)

