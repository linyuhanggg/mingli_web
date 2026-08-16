from app.readings.output_contracts import (
    BAZI_DEEP_V1,
    LIUYAO_DEEP_V1,
    QIMEN_DEEP_V1,
    get_output_contract,
    output_contract_for_product,
)


def test_bazi_deep_uses_a_distinct_structured_output_contract() -> None:
    contract = output_contract_for_product("bazi-deep", ("career",))

    assert contract is BAZI_DEEP_V1
    assert contract.contract_id == "bazi-deep-output-v1"
    assert contract.required_dimension_ids == ("career",)
    assert contract.min_blocks == 3
    assert contract.max_blocks == 8
    assert get_output_contract(contract.contract_id) == contract


def test_other_products_keep_the_dimension_frozen_preview_contract() -> None:
    contract = output_contract_for_product("bazi", ("career",))

    assert contract.contract_id == "preview-v1"
    assert contract.required_dimension_ids == ("career",)


def test_qimen_deep_uses_a_structured_event_output_contract() -> None:
    contract = output_contract_for_product(
        "qimen-deep", ("outcome", "timing", "state")
    )

    assert contract is QIMEN_DEEP_V1
    assert contract.contract_id == "qimen-deep-output-v1"
    assert contract.required_dimension_ids == ("outcome", "timing", "state")
    assert contract.min_blocks == 3
    assert contract.max_blocks == 8
    assert get_output_contract(contract.contract_id) == contract


def test_liuyao_deep_uses_a_candidate_evidence_output_contract() -> None:
    contract = output_contract_for_product(
        "liuyao-deep", ("outcome", "timing", "state")
    )

    assert contract is LIUYAO_DEEP_V1
    assert contract.contract_id == "liuyao-deep-output-v1"
    assert contract.required_dimension_ids == ("outcome", "timing", "state")
    assert contract.min_blocks == 3
    assert contract.max_blocks == 8
    assert "候选" in contract.disclosure_text
    assert "硬结论" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract
