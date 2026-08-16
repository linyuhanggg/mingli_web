from collections.abc import Sequence
from dataclasses import replace
from types import MappingProxyType

from app.readings.narrative_contracts import OutputContract


class UnknownOutputContractError(ValueError):
    """The requested Product Version does not own this output contract."""


PREVIEW_V1 = OutputContract(
    contract_id="preview-v1",
    language="zh-CN",
    min_blocks=1,
    max_blocks=4,
    max_output_chars=1200,
    required_dimension_ids=("career",),
    required_limit_kind_ids=(),
    disclosure_text="AI 辅助生成，仅供传统文化参考。",
)


BAZI_DEEP_V1 = OutputContract(
    contract_id="bazi-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("career",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已确认的八字事实与来源绑定依据；不输出保证性断言，"
        "也不替代现实中的专业判断。"
    ),
)


QIMEN_DEEP_V1 = OutputContract(
    contract_id="qimen-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("outcome", "timing", "state"),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的奇门局式、来源谓词与证据绑定；不输出保证性事件断言，"
        "也不替代现实中的专业判断。"
    ),
)


LIUYAO_DEEP_V1 = OutputContract(
    contract_id="liuyao-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("outcome", "timing", "state"),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的六爻盘面、用神候选与旺衰证据；候选不等于用神定夺，"
        "不输出成败或应期的硬结论，也不替代现实中的专业判断。"
    ),
)


def output_contract_for_dimensions(dimension_ids: Sequence[str]) -> OutputContract:
    """Freeze the requested dimensions into the product contract for this Job."""

    dimensions = tuple(dict.fromkeys(item for item in dimension_ids if item))
    if not dimensions:
        return PREVIEW_V1
    return replace(PREVIEW_V1, required_dimension_ids=dimensions)

_OUTPUT_CONTRACTS = MappingProxyType(
    {
        PREVIEW_V1.contract_id: PREVIEW_V1,
        BAZI_DEEP_V1.contract_id: BAZI_DEEP_V1,
        QIMEN_DEEP_V1.contract_id: QIMEN_DEEP_V1,
        LIUYAO_DEEP_V1.contract_id: LIUYAO_DEEP_V1,
    }
)


def output_contract_for_product(
    product_id: str | None,
    dimension_ids: Sequence[str],
) -> OutputContract:
    """Resolve the immutable narrative contract for one product lane."""

    if product_id == "bazi-deep":
        return BAZI_DEEP_V1
    if product_id == "qimen-deep":
        return QIMEN_DEEP_V1
    if product_id == "liuyao-deep":
        return LIUYAO_DEEP_V1
    return output_contract_for_dimensions(dimension_ids)


def get_output_contract(contract_id: str) -> OutputContract:
    try:
        return _OUTPUT_CONTRACTS[contract_id]
    except KeyError as error:
        raise UnknownOutputContractError(f"unknown output contract: {contract_id!r}") from error


def resolve_output_contract(value: str | OutputContract) -> OutputContract:
    if isinstance(value, OutputContract):
        return value
    return get_output_contract(value)
