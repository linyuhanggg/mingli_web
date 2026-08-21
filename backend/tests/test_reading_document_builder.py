from __future__ import annotations

from uuid import uuid4

from app.readings.narrative_contracts import NarrativeCandidate
from app.readings.output_contracts import output_contract_for_dimensions
from app.readings.presentation.builder import (
    ReadingDocumentBuilder,
    ReadingDocumentContext,
)
from app.readings.runtime_contracts import Prepared, ReadingBrief

from orchestrator_fakes import make_candidate
from test_narrative_guard import build_brief


def _ziwei_brief() -> ReadingBrief:
    payload = build_brief().to_dict()
    subject_ref = "profile-version:test"
    fact_ref = "fact:calculated/ziwei/palaces"
    palaces = [
        {
            "index": index,
            "name": "命宫" if index == 0 else f"宫{index}",
            "heavenlyStem": "甲",
            "earthlyBranch": "子",
            "majorStars": [{"name": "紫微"}] if index == 0 else [],
            "isBodyPalace": index == 1,
        }
        for index in range(12)
    ]
    payload["facts"] = [
        {
            "ref": fact_ref,
            "subject_ref": subject_ref,
            "kind_id": "kind.structure",
            "value": palaces,
            "display_text": "十二宫盘面事实",
        }
    ]
    payload["evidence"][0]["supports_fact_refs"] = [fact_ref]
    payload["evidence"][0]["locator"] = "fulltext.md#L11"
    payload["findings"][0]["fact_refs"] = [fact_ref]
    payload["claim_scopes"][0]["fact_refs"] = [fact_ref]
    payload["request_view"] = {
        "subject_refs": [subject_ref],
        "capability_ids": ["ziwei"],
        "object_id": "natal",
        "dimension_ids": ["career"],
        "horizon": {"kind_id": "life", "start": None, "end": None},
    }
    return ReadingBrief.from_dict(payload)


def _candidate() -> NarrativeCandidate:
    candidate = make_candidate(__import__("app.readings.narrative_contracts", fromlist=["x"]))
    block = candidate.blocks[0]
    return NarrativeCandidate(
        blocks=(
            type(block)(
                block_id=block.block_id,
                block_type=block.block_type,
                text=block.text,
                subject_ref=block.subject_ref,
                dimension_id=block.dimension_id,
                claim_kind_id=block.claim_kind_id,
                certainty_id=block.certainty_id,
                fact_refs=("fact:calculated/ziwei/palaces",),
                finding_refs=block.finding_refs,
                evidence_refs=block.evidence_refs,
                limit_kind_ids=block.limit_kind_ids,
            ),
        )
    )


def test_builder_projects_typed_runtime_facts_into_an_immutable_document() -> None:
    brief = _ziwei_brief()
    document = ReadingDocumentBuilder().build(
        ReadingDocumentContext(
            reading_version_id=uuid4(),
            accepted_copy_ref="accepted-copy:test",
            product_id="ziwei",
            relationship_type=None,
            runtime_release="mingli-runtime-test@5.2",
            prepared=Prepared(state_token="opaque", brief=brief),
            candidate=_candidate(),
            output_contract=output_contract_for_dimensions(("career",)),
            product_version="ziwei-reading/v7",
            presentation_contract_version="ziwei-presentation/v7",
        )
    )

    assert document is not None
    assert document.view_model.schema_version == "ziwei-chart/v1"
    assert document.product_version == "ziwei-reading/v7"
    assert document.presentation_contract_version == "ziwei-presentation/v7"
    assert document.claims[0].fact_refs == ("fact:calculated/ziwei/palaces",)
    assert document.evidence[0].title == "《测试古籍》 · 第 11 行"
    assert "fulltext.md#L11" not in document.evidence[0].title
    assert document.boundaries[-1].text == "AI 辅助生成，仅供传统文化参考。"
    assert document.actions.follow_up.enabled is False
    assert "/input/" not in repr(document.model_dump(mode="json"))


def test_builder_reads_follow_up_availability_from_the_paid_product_snapshot() -> None:
    document = ReadingDocumentBuilder().build(
        ReadingDocumentContext(
            reading_version_id=uuid4(),
            accepted_copy_ref="accepted-copy:test",
            product_id="bazi-deep",
            relationship_type=None,
            runtime_release="mingli-runtime-test@5.2",
            prepared=Prepared(state_token="opaque", brief=_ziwei_brief()),
            candidate=_candidate(),
            output_contract=output_contract_for_dimensions(("career",)),
            product_version="bazi-deep-reading/v1",
            presentation_contract_version="bazi-deep-presentation/v1",
            follow_up_count=2,
            follow_up_window_seconds=604800,
        )
    )

    assert document is not None
    assert document.actions.follow_up.enabled is True
