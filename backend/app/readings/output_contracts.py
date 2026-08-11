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
    required_dimension_ids=("overview",),
    required_limit_kind_ids=(),
    disclosure_text="AI 辅助生成，仅供传统文化参考。",
)

SCOPED_PREVIEW_V1 = OutputContract(
    contract_id="scoped-preview-v1",
    language="zh-CN",
    min_blocks=1,
    max_blocks=4,
    max_output_chars=1200,
    required_dimension_ids=("career",),
    required_limit_kind_ids=(),
    disclosure_text="AI 辅助生成，仅供传统文化参考。",
)

_OUTPUT_CONTRACTS = MappingProxyType(
    {
        PREVIEW_V1.contract_id: PREVIEW_V1,
        SCOPED_PREVIEW_V1.contract_id: SCOPED_PREVIEW_V1,
    }
)


def get_output_contract(contract_id: str) -> OutputContract:
    try:
        return _OUTPUT_CONTRACTS[contract_id]
    except KeyError as error:
        raise UnknownOutputContractError(f"unknown output contract: {contract_id!r}") from error


def resolve_output_contract(value: str | OutputContract) -> OutputContract:
    if isinstance(value, OutputContract):
        return value
    return get_output_contract(value)
