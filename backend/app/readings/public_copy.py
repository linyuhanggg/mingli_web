from __future__ import annotations

from app.readings.narrative_contracts import NarrativeCandidate, OutputContract
from app.readings.narrative_guard import contains_internal_identifier
from app.readings.output_contracts import resolve_output_contract
from app.readings.runtime_contracts import ReadingBrief


class PublicCopyAssemblyError(ValueError):
    """The mechanically assembled copy is unsafe to submit to complete."""


class PublicCopyAssembler:
    def assemble(
        self,
        candidate: NarrativeCandidate,
        brief: ReadingBrief,
        output_contract: str | OutputContract,
    ) -> str:
        contract = resolve_output_contract(output_contract)
        required_limit_ids = set(contract.required_limit_kind_ids)
        for block in candidate.blocks:
            required_limit_ids.update(block.limit_kind_ids)

        limit_texts: list[str] = []
        found_limit_ids: set[str] = set()
        for limit in brief.to_dict()["limits"]:
            kind_id = limit["kind_id"]
            if kind_id in required_limit_ids:
                limit_texts.append(limit["public_text"])
                found_limit_ids.add(kind_id)
        if found_limit_ids != required_limit_ids:
            raise PublicCopyAssemblyError("required public limit is missing")

        parts = [block.text for block in candidate.blocks]
        parts.extend(limit_texts)
        parts.append(contract.disclosure_text)
        public_copy = "\n\n".join(parts)
        if not public_copy.strip():
            raise PublicCopyAssemblyError("public copy must be non-empty")
        if len(public_copy) > contract.max_output_chars:
            raise PublicCopyAssemblyError("public copy exceeds final size contract")
        if contains_internal_identifier(public_copy):
            raise PublicCopyAssemblyError("public copy contains an internal identifier")
        return public_copy
