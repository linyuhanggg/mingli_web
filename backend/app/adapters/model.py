from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NarrativeRequest:
    fact_brief_id: UUID
    product_kind: str
    required_sections: tuple[str, ...]
    max_cost: Decimal


@dataclass(frozen=True, slots=True)
class CandidateCopy:
    sections: dict[str, str]
    provider: str
    model: str
    accepted: bool
    cost: Decimal


class ModelGateway(Protocol):
    async def generate(self, request: NarrativeRequest) -> CandidateCopy: ...


class FakeModelGateway:
    """Schema-only model substitute; its output is never an Accepted Copy."""

    async def generate(self, request: NarrativeRequest) -> CandidateCopy:
        sections = {
            section: f"FAKE:{section}:尚未进入 Phase 2 生成链。"
            for section in request.required_sections
        }
        return CandidateCopy(
            sections=sections,
            provider="fake",
            model="fake-schema-v1",
            accepted=False,
            cost=Decimal("0"),
        )
