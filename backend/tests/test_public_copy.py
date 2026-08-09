from __future__ import annotations

import importlib

import pytest

# isort: split
from test_narrative_guard import build_brief, load_candidate


def test_public_copy_is_mechanical_exact_assembly() -> None:
    contracts = importlib.import_module("app.readings.narrative_contracts")
    copy_module = importlib.import_module("app.readings.public_copy")
    candidate = contracts.NarrativeCandidate.from_dict(load_candidate())

    public_copy = copy_module.PublicCopyAssembler().assemble(
        candidate,
        build_brief(),
        output_contract="preview-v1",
    )

    assert public_copy == (
        "事业主线更适合先抓住可持续积累，再决定是否扩张方向。\n\n"
        "本解读仅供传统文化参考，不构成现实决策保证。\n\n"
        "AI 辅助生成，仅供传统文化参考。"
    )
    assert candidate.blocks[0].text in public_copy


def test_assembler_rechecks_final_internal_identifiers() -> None:
    contracts = importlib.import_module("app.readings.narrative_contracts")
    copy_module = importlib.import_module("app.readings.public_copy")
    output_contracts = importlib.import_module("app.readings.output_contracts")
    candidate = contracts.NarrativeCandidate.from_dict(load_candidate())
    unsafe_contract = contracts.OutputContract(
        contract_id="unsafe-test",
        language="zh-CN",
        min_blocks=1,
        max_blocks=4,
        max_output_chars=1200,
        required_dimension_ids=("career",),
        required_limit_kind_ids=("limit:traditional",),
        disclosure_text="Provider internal marker",
    )

    with pytest.raises(copy_module.PublicCopyAssemblyError, match="internal"):
        copy_module.PublicCopyAssembler().assemble(
            candidate,
            build_brief(),
            output_contract=unsafe_contract,
        )

    assert output_contracts.get_output_contract("preview-v1").contract_id == "preview-v1"


def test_assembler_rechecks_the_final_size_after_limits_and_disclosure() -> None:
    contracts = importlib.import_module("app.readings.narrative_contracts")
    copy_module = importlib.import_module("app.readings.public_copy")
    candidate = contracts.NarrativeCandidate.from_dict(load_candidate())
    tiny_contract = contracts.OutputContract(
        contract_id="tiny-test",
        language="zh-CN",
        min_blocks=1,
        max_blocks=4,
        max_output_chars=20,
        required_dimension_ids=("career",),
        required_limit_kind_ids=("limit:traditional",),
        disclosure_text="边界声明",
    )

    with pytest.raises(copy_module.PublicCopyAssemblyError, match="size"):
        copy_module.PublicCopyAssembler().assemble(
            candidate,
            build_brief(),
            output_contract=tiny_contract,
        )
