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


ZIWEI_DEEP_V1 = OutputContract(
    contract_id="ziwei-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("career",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的紫微十二宫、星曜与四化事实；不输出格局吉凶硬结论，"
        "也不替代现实中的专业判断。"
    ),
)


QIZHENG_DEEP_V1 = OutputContract(
    contract_id="qizheng-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("career",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的七政星盘与时限事实；不输出吉凶硬结论，"
        "也不替代现实中的专业判断。"
    ),
)


MEIHUA_DEEP_V1 = OutputContract(
    contract_id="meihua-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("outcome", "state"),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的梅花三卦、体用关系与旺衰事实；候选不等于体用定夺，"
        "不输出成败或应期的硬结论，也不替代现实中的专业判断。"
    ),
)


DALIUREN_DEEP_V1 = OutputContract(
    contract_id="daliuren-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("outcome", "timing", "state"),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的大六壬课传、神将与应期候选；候选不等于课体定夺，"
        "不输出成败或应期的硬结论，也不替代现实中的专业判断。"
    ),
)


BAZI_RELATIONSHIP_DEEP_V1 = OutputContract(
    contract_id="bazi-relationship-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("relationship",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的双方八字关系结构事实与来源绑定依据；"
        "关系信号缺失时不得编造；不输出合婚吉凶或匹配度硬结论，"
        "也不替代现实中的专业判断。本产品不是三术合参。"
    ),
)


ZIWEI_RELATIONSHIP_DEEP_V1 = OutputContract(
    contract_id="ziwei-relationship-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("relationship",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的双方紫微关系结构事实与来源绑定依据；"
        "关系信号缺失时不得编造；不输出合盘吉凶或匹配度硬结论，"
        "也不替代现实中的专业判断。本产品不是三术合参。"
    ),
)


QIZHENG_RELATIONSHIP_DEEP_V1 = OutputContract(
    contract_id="qizheng-relationship-deep-output-v1",
    language="zh-CN",
    min_blocks=3,
    max_blocks=8,
    max_output_chars=3200,
    required_dimension_ids=("relationship",),
    required_limit_kind_ids=(),
    disclosure_text=(
        "本深读只基于已计算的双方七政关系结构事实与来源绑定依据；"
        "关系信号缺失时不得编造；不输出合盘吉凶或匹配度硬结论，"
        "也不替代现实中的专业判断。本产品不是三术合参。"
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
        ZIWEI_DEEP_V1.contract_id: ZIWEI_DEEP_V1,
        QIZHENG_DEEP_V1.contract_id: QIZHENG_DEEP_V1,
        MEIHUA_DEEP_V1.contract_id: MEIHUA_DEEP_V1,
        DALIUREN_DEEP_V1.contract_id: DALIUREN_DEEP_V1,
        BAZI_RELATIONSHIP_DEEP_V1.contract_id: BAZI_RELATIONSHIP_DEEP_V1,
        ZIWEI_RELATIONSHIP_DEEP_V1.contract_id: ZIWEI_RELATIONSHIP_DEEP_V1,
        QIZHENG_RELATIONSHIP_DEEP_V1.contract_id: QIZHENG_RELATIONSHIP_DEEP_V1,
    }
)

_PRODUCT_OUTPUT_CONTRACTS = MappingProxyType(
    {
        "bazi-deep": BAZI_DEEP_V1,
        "qimen-deep": QIMEN_DEEP_V1,
        "liuyao-deep": LIUYAO_DEEP_V1,
        "ziwei-deep": ZIWEI_DEEP_V1,
        "qizheng-deep": QIZHENG_DEEP_V1,
        "meihua-deep": MEIHUA_DEEP_V1,
        "daliuren-deep": DALIUREN_DEEP_V1,
        "bazi-relationship-deep": BAZI_RELATIONSHIP_DEEP_V1,
        "ziwei-relationship-deep": ZIWEI_RELATIONSHIP_DEEP_V1,
        "qizheng-relationship-deep": QIZHENG_RELATIONSHIP_DEEP_V1,
    }
)


def output_contract_for_product(
    product_id: str | None,
    dimension_ids: Sequence[str],
) -> OutputContract:
    """Resolve the immutable narrative contract for one product lane."""

    if product_id is not None:
        contract = _PRODUCT_OUTPUT_CONTRACTS.get(product_id)
        if contract is not None:
            return contract
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
