from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from app.readings.narrative_contracts import (
    NarrativeCandidate,
    NarrativeRequest,
)


@runtime_checkable
class NarrativeModel(Protocol):
    async def generate(self, request: NarrativeRequest) -> NarrativeCandidate: ...


def _objects(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(str(item) for item in value)


class FakeModelGateway:
    """Deterministic schema Fake; it has no tools, memory, network or acceptance role."""

    async def generate(self, request: NarrativeRequest) -> NarrativeCandidate:
        scopes = _objects(request.brief.get("claim_scopes"))
        scope = scopes[0] if scopes else {}
        subject_ref = str(scope.get("subject_ref", "fixture:subject"))
        dimension_id = str(scope.get("dimension_id", "overview"))
        allowed_kinds = _strings(scope.get("allowed_kind_ids"))
        findings = _objects(request.brief.get("findings"))
        limit_ids = tuple(item for item in request.output_contract.required_limit_kind_ids if item)

        return NarrativeCandidate.from_dict(
            {
                "schema_version": "mingli-narrative-candidate-v1",
                "blocks": [
                    {
                        "block_id": "fake-block-1",
                        "block_type": "claim",
                        "text": "这是合同测试候选稿，不是正式命理解读。",
                        "subject_ref": subject_ref,
                        "dimension_id": dimension_id,
                        "claim_kind_id": (allowed_kinds[0] if allowed_kinds else "kind.fixture"),
                        "certainty_id": str(scope.get("certainty_ceiling_id", "certainty.fixture")),
                        "fact_refs": list(_strings(scope.get("fact_refs"))),
                        "finding_refs": [
                            str(item["ref"])
                            for item in findings
                            if item.get("subject_ref") == subject_ref
                            and dimension_id in _strings(item.get("dimension_ids"))
                        ],
                        "evidence_refs": list(_strings(scope.get("evidence_refs"))),
                        "limit_kind_ids": list(limit_ids),
                    }
                ],
            }
        )
