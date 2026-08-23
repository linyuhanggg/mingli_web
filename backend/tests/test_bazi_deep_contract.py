from app.readings.output_contracts import (
    BAZI_DEEP_V1,
    BAZI_RELATIONSHIP_DEEP_V1,
    DALIUREN_DEEP_V1,
    LIUYAO_DEEP_V1,
    MEIHUA_DEEP_V1,
    QIMEN_DEEP_V1,
    QIZHENG_DEEP_V1,
    QIZHENG_RELATIONSHIP_DEEP_V1,
    ZIWEI_DEEP_V1,
    ZIWEI_RELATIONSHIP_DEEP_V1,
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


def test_ziwei_deep_uses_a_natal_theme_output_contract() -> None:
    contract = output_contract_for_product("ziwei-deep", ("career",))

    assert contract is ZIWEI_DEEP_V1
    assert contract.contract_id == "ziwei-deep-output-v1"
    assert contract.required_dimension_ids == ("career",)
    assert contract.min_blocks == 3
    assert contract.max_blocks == 8
    assert "吉凶" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_qizheng_deep_uses_a_natal_theme_output_contract() -> None:
    contract = output_contract_for_product("qizheng-deep", ("career",))

    assert contract is QIZHENG_DEEP_V1
    assert contract.contract_id == "qizheng-deep-output-v1"
    assert contract.required_dimension_ids == ("career",)
    assert "吉凶" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_meihua_deep_uses_body_use_evidence_without_timing() -> None:
    contract = output_contract_for_product("meihua-deep", ("outcome", "state"))

    assert contract is MEIHUA_DEEP_V1
    assert contract.contract_id == "meihua-deep-output-v1"
    assert contract.required_dimension_ids == ("outcome", "state")
    assert "timing" not in contract.required_dimension_ids
    assert "硬结论" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_daliuren_deep_uses_a_candidate_evidence_output_contract() -> None:
    contract = output_contract_for_product(
        "daliuren-deep", ("outcome", "timing", "state")
    )

    assert contract is DALIUREN_DEEP_V1
    assert contract.contract_id == "daliuren-deep-output-v1"
    assert contract.required_dimension_ids == ("outcome", "timing", "state")
    assert "硬结论" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_free_preview_products_do_not_inherit_deep_output_contracts() -> None:
    for product_id in ("ziwei", "qizheng", "meihua", "daliuren", "jianxiang"):
        contract = output_contract_for_product(product_id, ("career",))
        assert contract.contract_id == "preview-v1"
        assert contract.required_dimension_ids == ("career",)


def test_relationship_preview_products_do_not_inherit_deep_output_contracts() -> None:
    for product_id in (
        "bazi-relationship",
        "ziwei-relationship",
        "qizheng-relationship",
    ):
        contract = output_contract_for_product(product_id, ("relationship",))
        assert contract.contract_id == "preview-v1"
        assert contract.required_dimension_ids == ("relationship",)


def test_bazi_relationship_deep_uses_relationship_dimension_not_career() -> None:
    contract = output_contract_for_product("bazi-relationship-deep", ("career",))

    assert contract is BAZI_RELATIONSHIP_DEEP_V1
    assert contract.contract_id == "bazi-relationship-deep-output-v1"
    assert contract.required_dimension_ids == ("relationship",)
    assert contract.min_blocks == 3
    assert contract.max_blocks == 8
    assert "不得编造" in contract.disclosure_text
    assert "硬结论" in contract.disclosure_text
    assert "合参" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_ziwei_relationship_deep_is_independent_of_hecan() -> None:
    contract = output_contract_for_product(
        "ziwei-relationship-deep", ("relationship",)
    )

    assert contract is ZIWEI_RELATIONSHIP_DEEP_V1
    assert contract.contract_id == "ziwei-relationship-deep-output-v1"
    assert contract.required_dimension_ids == ("relationship",)
    assert "合参" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract


def test_qizheng_relationship_deep_is_independent_of_hecan() -> None:
    contract = output_contract_for_product(
        "qizheng-relationship-deep", ("relationship",)
    )

    assert contract is QIZHENG_RELATIONSHIP_DEEP_V1
    assert contract.contract_id == "qizheng-relationship-deep-output-v1"
    assert contract.required_dimension_ids == ("relationship",)
    assert "合参" in contract.disclosure_text
    assert get_output_contract(contract.contract_id) == contract
