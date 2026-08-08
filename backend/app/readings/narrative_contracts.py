from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from app.readings.runtime_contracts import (
    ReadingBrief,
    _validate_schema,
)

CANDIDATE_SCHEMA = "mingli-narrative-candidate-v1.schema.json"
OUTPUT_CONTRACT_SCHEMA = "mingli-output-contract-v1.schema.json"


@dataclass(frozen=True, slots=True)
class NarrativeBlock:
    block_id: str
    text: str
    subject_ref: str
    dimension_id: str
    claim_kind_id: str
    certainty_id: str
    fact_refs: tuple[str, ...]
    finding_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limit_kind_ids: tuple[str, ...]
    block_type: Literal["claim"] = "claim"

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> NarrativeBlock:
        return cls(
            block_id=cast(str, payload["block_id"]),
            block_type=cast(Literal["claim"], payload["block_type"]),
            text=cast(str, payload["text"]),
            subject_ref=cast(str, payload["subject_ref"]),
            dimension_id=cast(str, payload["dimension_id"]),
            claim_kind_id=cast(str, payload["claim_kind_id"]),
            certainty_id=cast(str, payload["certainty_id"]),
            fact_refs=tuple(cast(list[str], payload["fact_refs"])),
            finding_refs=tuple(cast(list[str], payload["finding_refs"])),
            evidence_refs=tuple(cast(list[str], payload["evidence_refs"])),
            limit_kind_ids=tuple(cast(list[str], payload["limit_kind_ids"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "text": self.text,
            "subject_ref": self.subject_ref,
            "dimension_id": self.dimension_id,
            "claim_kind_id": self.claim_kind_id,
            "certainty_id": self.certainty_id,
            "fact_refs": list(self.fact_refs),
            "finding_refs": list(self.finding_refs),
            "evidence_refs": list(self.evidence_refs),
            "limit_kind_ids": list(self.limit_kind_ids),
        }


@dataclass(frozen=True, slots=True)
class NarrativeCandidate:
    blocks: tuple[NarrativeBlock, ...]
    schema_version: Literal["mingli-narrative-candidate-v1"] = (
        "mingli-narrative-candidate-v1"
    )

    def __post_init__(self) -> None:
        _validate_schema(CANDIDATE_SCHEMA, self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> NarrativeCandidate:
        _validate_schema(CANDIDATE_SCHEMA, payload)
        return cls(
            schema_version=cast(
                Literal["mingli-narrative-candidate-v1"],
                payload["schema_version"],
            ),
            blocks=tuple(
                NarrativeBlock.from_dict(cast(Mapping[str, object], item))
                for item in cast(list[object], payload["blocks"])
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True, slots=True)
class OutputContract:
    contract_id: str
    language: str
    min_blocks: int
    max_blocks: int
    max_output_chars: int
    required_dimension_ids: tuple[str, ...]
    required_limit_kind_ids: tuple[str, ...]
    disclosure_text: str
    schema_version: Literal["mingli-output-contract-v1"] = (
        "mingli-output-contract-v1"
    )

    def __post_init__(self) -> None:
        _validate_schema(OUTPUT_CONTRACT_SCHEMA, self.to_dict())
        if self.min_blocks > self.max_blocks:
            raise ValueError("min_blocks must not exceed max_blocks")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> OutputContract:
        _validate_schema(OUTPUT_CONTRACT_SCHEMA, payload)
        return cls(
            schema_version=cast(
                Literal["mingli-output-contract-v1"],
                payload["schema_version"],
            ),
            contract_id=cast(str, payload["contract_id"]),
            language=cast(str, payload["language"]),
            min_blocks=cast(int, payload["min_blocks"]),
            max_blocks=cast(int, payload["max_blocks"]),
            max_output_chars=cast(int, payload["max_output_chars"]),
            required_dimension_ids=tuple(
                cast(list[str], payload["required_dimension_ids"])
            ),
            required_limit_kind_ids=tuple(
                cast(list[str], payload["required_limit_kind_ids"])
            ),
            disclosure_text=cast(str, payload["disclosure_text"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "language": self.language,
            "min_blocks": self.min_blocks,
            "max_blocks": self.max_blocks,
            "max_output_chars": self.max_output_chars,
            "required_dimension_ids": list(self.required_dimension_ids),
            "required_limit_kind_ids": list(self.required_limit_kind_ids),
            "disclosure_text": self.disclosure_text,
        }


@dataclass(frozen=True, slots=True)
class NarrativeRequest:
    brief: ReadingBrief
    narrative_policy_version: str
    output_contract: OutputContract
    language: str
    max_output_chars: int

    def __post_init__(self) -> None:
        if not self.narrative_policy_version.strip():
            raise ValueError("narrative_policy_version must be non-empty")
        if not self.language.strip():
            raise ValueError("language must be non-empty")
        if self.max_output_chars < 1:
            raise ValueError("max_output_chars must be positive")
        if self.language != self.output_contract.language:
            raise ValueError("request language must match the output contract")
        if self.max_output_chars > self.output_contract.max_output_chars:
            raise ValueError("request size cannot exceed the output contract")

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief": self.brief.to_dict(),
            "narrative_policy_version": self.narrative_policy_version,
            "output_contract": self.output_contract.to_dict(),
            "language": self.language,
            "max_output_chars": self.max_output_chars,
        }
