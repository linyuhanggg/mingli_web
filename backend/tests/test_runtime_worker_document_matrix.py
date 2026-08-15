from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4

import pytest
from app.adapters.model import FakeModelGateway
from app.adapters.runtime import MingliRuntime, build_runtime_startup_gate
from app.config import Settings
from app.readings import orchestrator as orchestrator_module
from app.readings.narrative_guard import NarrativeGuard
from app.readings.output_contracts import output_contract_for_dimensions
from app.readings.presentation.builder import ReadingDocumentBuilder
from app.readings.public_copy import PublicCopyAssembler
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
    compile_canwen_prepare,
    compile_chart_similarity_prepare,
    compile_fengshui_prepare,
    compile_five_elements_facts_prepare,
    compile_fortune_prepare,
    compile_hecan_prepare,
    compile_liuren_prepare,
    compile_liuyao_prepare,
    compile_luming_nayin_prepare,
    compile_meihua_prepare,
    compile_physiognomy_prepare,
    compile_qimen_prepare,
    compile_qizheng_prepare,
    compile_relationship_prepare,
    compile_selection_prepare,
    compile_taiyi_prepare,
    compile_time_check_prepare,
    compile_wenshi_prepare,
    compile_ziwei_prepare,
)
from app.readings.runtime_contracts import Prepare
from app.readings.status import ReadingStatus

# isort: split
from orchestrator_fakes import FixedClock, MemoryRepository

pytestmark = pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)


SYNTHETIC_PROFILE = ConfirmedProfileVersion(
    subject_ref="profile-version:worker-matrix-synthetic",
    birth_datetime="1994-04-30T05:55:00+08:00",
    birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
    timezone="Asia/Shanghai",
    location="福建省福州市",
    gender="female",
    time_basis_policy="solar",
    zi_hour_policy="solar",
    longitude=119.2965,
    latitude=26.0745,
    coordinate_source="synthetic-fixture",
)

_EVENT_DATETIME = datetime.fromisoformat("2026-08-14T10:00:00+08:00")

_REQUIRED_SINGLE_CALCULATED_FACTS = {
    "bazi": (
        "day_master",
        "month_command",
        "seasonal_profile",
        "tiaohou_markers",
        "element_inventory",
        "branch_relations",
        "interpretive_candidates",
    ),
    "fortune": ("active_luck_cycle", "available_periods"),
    "ziwei": ("chart_convention", "chinese_date"),
    "xingming": ("classical_positions", "transformations"),
    "liuyao": (
        "changed_hexagram",
        "changed_najia",
        "najia",
        "six_relatives",
        "six_spirits",
        "xunkong",
        "month_day_strength",
        "relation_facts",
        "line_facts",
        "returning_relations",
        "useful_spirit_selection",
    ),
    "meihua": ("body_use", "body_relation_facts", "seasonal_strength"),
    "luming-nayin": ("four_pillars", "independent_lineage"),
    "taiyi": ("board", "board_predicates"),
    "selection": ("basis_projection", "ranking"),
    "fengshui": ("compass", "liqi"),
    "qimen": ("board_digest", "calculated_board_scope"),
    "liuren": (
        "four_lessons",
        "earth_plate",
        "heaven_plate",
        "heavenly_generals",
        "lesson_method",
        "transmission_method",
        "xunkong",
        "dimension_facts",
        "timing_candidates",
    ),
    "physiognomy": ("normalized_visible_observations", "source_comparison"),
    "time-check": (
        "candidate_count",
        "candidates",
        "known_time_range",
        "time_basis_policy",
        "ranking_status",
        "event_matching_status",
    ),
}


def _calculated_fact_values(
    *,
    primary_capability_id: str,
    prepared: object,
) -> dict[str, object]:
    brief = getattr(prepared, "brief", None)
    if brief is None or not hasattr(brief, "to_dict"):
        raise AssertionError("prepared brief is unavailable for golden facts")
    prefix = f"/calculated/{primary_capability_id}/"
    values: dict[str, object] = {}
    for item in brief.to_dict().get("facts", []):
        if not isinstance(item, dict):
            continue
        ref = item.get("ref")
        if not isinstance(ref, str) or prefix not in ref:
            continue
        values[ref.split(prefix, 1)[1]] = item.get("value")
    return values


def _assert_runtime_golden_facts(
    *,
    label: str,
    prepare: Prepare,
    prepared: object,
    relationship_type: str | None = None,
) -> None:
    """Pin stable semantic facts without freezing private ids or digests."""

    # Relationship prepares contain two subject scopes.  Their single-art
    # calculated facts are intentionally not the one-person synthetic fixture
    # below; relationship signal semantics are asserted by the dedicated
    # relationship smoke and the Worker contract checks.
    if relationship_type is not None:
        return
    if label == "chart-similarity":
        return

    capability_id = str(prepare.intent["capability_id"])
    values = _calculated_fact_values(
        primary_capability_id=capability_id,
        prepared=prepared,
    )

    if capability_id == "bazi":
        assert values["four_pillars"] == {
            "day": "丙戌",
            "hour": "辛卯",
            "month": "戊辰",
            "year": "甲戌",
        }, label
        assert values["day_master"] == {
            "element": "火",
            "polarity": "阳",
            "stem": "丙",
        }, label
        candidates = values["interpretive_candidates"]
        assert isinstance(candidates, dict), label
        assert candidates["strength"]["status"] == "evidence_only", label
        assert candidates["strength"]["same_element_occurrences"] == 3, label
        assert candidates["strength"]["resource_occurrences"] == 4, label
        assert candidates["structure"]["status"] == "candidate_only", label
        assert len(candidates["salience_signals"]) == 9, label
        reasoning_tools = candidates["reasoning_tools"]
        assert set(reasoning_tools) == {
            "strength_evidence",
            "month_structure_candidate",
        }, label
        assert reasoning_tools["strength_evidence"]["output"]["evidence_lean"] == (
            "mixed"
        ), label
        assert all(
            isinstance(tool["tool_digest"], str) and len(tool["tool_digest"]) == 64
            for tool in reasoning_tools.values()
        ), label
        assert all(
            candidates[section]["hard_verdict"] is None
            for section in (
                "strength",
                "structure",
                "following_and_transformation",
            )
        ), label
    elif capability_id == "fortune":
        assert values["active_luck_cycle"] == "乙丑", label
        assert values["available_periods"] == ["2026-08-14"], label
    elif capability_id == "ziwei":
        assert values["chinese_date"] == "甲戌 戊辰 丙戌 辛卯", label
        convention = values["chart_convention"]
        assert isinstance(convention, dict), label
        assert (convention["engine"], convention["fix_leap"]) == (
            {"name": "iztro", "version": "2.5.8"},
            True,
        ), label
    elif capability_id == "xingming":
        positions = values["classical_positions"]
        assert isinstance(positions, list), label
        assert [item["body"] for item in positions] == [
            "Sun",
            "Moon",
            "Venus",
            "Jupiter",
            "Mercury",
            "Mars",
            "Saturn",
            "计都",
            "罗睺",
            "紫炁",
            "月孛",
        ], label
    elif capability_id == "liuyao":
        changed = values["changed_hexagram"]
        assert isinstance(changed, dict), label
        assert (changed["name"], changed["king_wen_number"]) == (
            "风泽中孚",
            61,
        ), label
    elif capability_id == "meihua":
        body_use = values["body_use"]
        assert isinstance(body_use, dict), label
        assert (
            body_use["body"]["trigram"],
            body_use["use"]["trigram"],
            body_use["relation"],
        ) == ("坎", "坤", "用克体"), label
    elif capability_id == "luming-nayin":
        assert values["four_pillars"] == {
            "day": "丙戌",
            "hour": "辛卯",
            "month": "戊辰",
            "year": "甲戌",
        }, label
        assert values["independent_lineage"] == "early-luming-nayin", label
    elif capability_id == "taiyi":
        board = values["board"]
        assert isinstance(board, dict), label
        assert board["taiyi_position"] == "艮", label
        predicates = values["board_predicates"]
        assert isinstance(predicates, list), label
        assert [item["id"] for item in predicates] == ["TY-P01", "TY-P07"], label
    elif capability_id == "selection":
        basis = values["basis_projection"]
        assert isinstance(basis, dict), label
        assert basis["complete_counts"] == {
            "calendar_candidates": 3,
            "date_time_candidates": 39,
            "eligible_candidates": 0,
            "eligible_date_time_candidates": 0,
            "eliminations": 3,
            "ranking.eligible_candidate_ids": 0,
            "ranking.eligible_date_time_candidate_ids": 0,
            "ranking.ordered_candidate_ids": 3,
            "ranking.ordered_date_time_candidate_ids": 39,
        }, label
        ranking = values["ranking"]
        assert isinstance(ranking, dict), label
        assert (
            ranking["method"],
            ranking["ordered_candidate_ids"][0],
        ) == ("explainable_lexicographic_v1", "2026-09-03"), label
    elif capability_id == "fengshui":
        compass = values["compass"]
        assert isinstance(compass, dict), label
        assert (
            compass["facing"]["degrees"],
            compass["facing"]["mountain"],
            compass["facing"]["trigram"],
        ) == (180.0, "午", "离"), label
    elif capability_id == "qimen":
        scope = values["calculated_board_scope"]
        assert isinstance(scope, dict), label
        assert (scope["dun"], scope["number"], scope["yuan"]) == (
            "yin",
            8,
            "lower",
        ), label
    elif capability_id == "liuren":
        assert values["day_hour"] == {"day": "庚申", "hour": "辛巳"}, label
        assert values["earth_plate"] == list("子丑寅卯辰巳午未申酉戌亥"), label
        lessons = values["four_lessons"]
        assert isinstance(lessons, list), label
        assert lessons[0] == {
            "lesson": 1,
            "lower": "庚",
            "lower_lodge": "申",
            "relation": "比和",
            "upper": "酉",
        }, label
    elif capability_id == "physiognomy":
        observations = values["normalized_visible_observations"]
        assert isinstance(observations, list), label
        assert (
            observations[0]["region"],
            observations[0]["descriptor"],
            observations[0]["quality_status"],
        ) == ("forehead", "region_visible", "eligible"), label
        comparison = values["source_comparison"]
        assert isinstance(comparison, dict), label
        assert comparison["disagreements_retained"] is True, label
    elif capability_id == "time-check":
        assert values["candidate_count"] == 12, label
        candidates = values["candidates"]
        assert isinstance(candidates, list), label
        assert len(candidates) == 12, label
        assert candidates[0]["hour_branch"] == "子", label
        assert candidates[-1]["hour_branch"] == "亥", label
        assert values["time_basis_policy"] == "local_apparent_solar-v1", label
        assert values["ranking_status"] == "not_ranked", label
        assert values["event_matching_status"] == "not_calculated", label


def _fengshui_spec() -> dict[str, object]:
    measurement = {
        "measurement_id": "m-door",
        "method": "synthetic-compass",
        "source_ref": "synthetic-compass-1",
        "source_type": "user_measurement",
        "north_reference": "true",
        "facing_degrees": 180,
        "correction_degrees": 0,
        "uncertainty_degrees": 0,
        "quality": "good",
    }
    return {
        "schema_version": "mingli-fengshui-input-v1",
        "property_scope": "residential",
        "subprofiles": ["liqi"],
        "requested_form_variables": [],
        "liqi": {
            "selected_school": "bazhai",
            "origin_basis": "door_trigram",
            "origin_node_id": "door-1",
        },
        "building": {},
        "assets": [],
        "observations": [],
        "compass_measurements": [measurement],
        "declared_orientation": {},
        "layout_graph": {
            "nodes": [
                {
                    "node_id": "door-1",
                    "kind": "door",
                    "direction_measurement": measurement,
                }
            ],
            "edges": [],
        },
    }


def _physiognomy_spec(subject_ref: str) -> dict[str, object]:
    return {
        "schema_version": "mingli-physiognomy-input-v1",
        "observation_scope": "face",
        "subject_ref": subject_ref,
        "requested_targets": [
            {
                "target_id": "tid-22222222222222222222222222222222",
                "taxonomy": "anatomical_face_v1",
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "required": True,
            }
        ],
        "assets": [],
        "observations": [
            {
                "observation_id": "oid-33333333333333333333333333333333",
                "target_id": "tid-22222222222222222222222222222222",
                "source_type": "user_text",
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "visibility": "full",
                "value": {"descriptor": "region_visible"},
                "occlusion": 0,
                "uncertainty": 0,
                "source_ref": "rid-44444444444444444444444444444444",
                "quality": {
                    "lighting": "not_applicable",
                    "camera_angle": "caller_description",
                    "focus": "not_applicable",
                    "resolution": "not_applicable",
                    "filtering": "not_applicable",
                    "color_fidelity": "not_applicable",
                },
            }
        ],
        "confirmed_observation_ids": ["oid-33333333333333333333333333333333"],
        "comparison_relations": [],
        "source_layer_policy": "terminology_and_methodology_only",
    }


def _single_art_cases() -> tuple[tuple[str, str, str | None, Prepare], ...]:
    event = _EVENT_DATETIME
    cases = (
        (
            "bazi",
            "bazi",
            "bazi-chart/v1",
            compile_bazi_prepare(
                action="profile_preview",
                query="验证八字 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("career",),
            ),
        ),
        (
            "five-elements-facts",
            "five-elements-facts",
            "five-elements-facts-view/v1",
            compile_five_elements_facts_prepare(
                action="five_elements_facts_preview",
                query="验证五行事实与调候 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("state",),
            ),
        ),
        (
            "fortune",
            "fortune",
            None,
            compile_fortune_prepare(
                action="today",
                query="验证日运事实面板 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                server_reference_datetime=event,
                dimension_ids=("career",),
            ),
        ),
        (
            "ziwei",
            "ziwei",
            "ziwei-chart/v1",
            compile_ziwei_prepare(
                action="ziwei_preview",
                query="验证紫微 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("career",),
            ),
        ),
        (
            "qizheng",
            "qizheng",
            "qizheng-chart/v1",
            compile_qizheng_prepare(
                action="qizheng_preview",
                query="验证七政 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("career",),
            ),
        ),
        (
            "liuyao",
            "liuyao",
            "liuyao-chart/v1",
            compile_liuyao_prepare(
                action="liuyao_one_question",
                query="验证六爻 Worker 闭环",
                subject_ref="liuyao:worker-matrix-synthetic",
                cast=(6, 7, 8, 9, 6, 7),
                event_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "timing"),
            ),
        ),
        (
            "meihua",
            "meihua",
            "meihua-chart/v1",
            compile_meihua_prepare(
                action="meihua_preview",
                query="验证梅花 Worker 闭环",
                subject_ref="meihua:worker-matrix-synthetic",
                casting_method="time",
                event_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "state"),
            ),
        ),
        (
            "luming-nayin",
            "luming-nayin",
            "luming-nayin-chart/v1",
            compile_luming_nayin_prepare(
                action="luming_nayin_preview",
                query="验证禄命纳音 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("career", "state"),
            ),
        ),
        (
            "rhythm",
            "rhythm",
            "rhythm-facts-view/v1",
            compile_luming_nayin_prepare(
                action="rhythm_preview",
                query="验证本命音律 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                dimension_ids=("state",),
            ),
        ),
        (
            "taiyi",
            "taiyi",
            "taiyi-chart/v1",
            compile_taiyi_prepare(
                action="taiyi_preview",
                query="验证太乙 Worker 闭环",
                subject_ref="taiyi:worker-matrix-synthetic",
                reference_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "timing"),
                time_basis_policy="solar",
                longitude=119.2965,
                latitude=26.0745,
                coordinate_source="synthetic-fixture",
            ),
        ),
        (
            "selection",
            "selection",
            "selection-chart/v1",
            compile_selection_prepare(
                action="selection_preview",
                query="验证择日 Worker 闭环",
                subject_ref="selection:worker-matrix-synthetic",
                event_profile="business_opening_transaction",
                requested_actions=("开市",),
                date_range_start="2026-09-01",
                date_range_end="2026-09-03",
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("timing", "state"),
            ),
        ),
        (
            "fengshui",
            "fengshui",
            "fengshui-view/v1",
            compile_fengshui_prepare(
                action="fengshui_preview",
                query="验证风水 Worker 闭环",
                subject_ref="fengshui:worker-matrix-synthetic",
                fengshui_spec=_fengshui_spec(),
                dimension_ids=("current_state", "direction"),
            ),
        ),
        (
            "qimen",
            "qimen",
            "qimen-chart/v1",
            compile_qimen_prepare(
                action="qimen_one_question",
                query="验证奇门 Worker 闭环",
                subject_ref="qimen:worker-matrix-synthetic",
                event_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "timing"),
                longitude=119.2965,
                latitude=26.0745,
                coordinate_source="synthetic-fixture",
            ),
        ),
        (
            "liuren",
            "daliuren",
            "daliuren-chart/v1",
            compile_liuren_prepare(
                action="liuren_one_question",
                query="验证大六壬 Worker 闭环",
                subject_ref="liuren:worker-matrix-synthetic",
                event_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "timing"),
                longitude=119.2965,
                latitude=26.0745,
                coordinate_source="synthetic-fixture",
            ),
        ),
        (
            "physiognomy",
            "jianxiang",
            "physiognomy-view/v1",
            compile_physiognomy_prepare(
                action="physiognomy_preview",
                query="验证相法 Worker 闭环",
                subject_ref="sid-11111111111111111111111111111111",
                physiognomy_spec=_physiognomy_spec(
                    "sid-11111111111111111111111111111111"
                ),
                dimension_ids=("state", "source_comparison"),
            ),
        ),
    )
    if os.environ.get("MINGLI_RUNTIME_RELEASE_PROFILE") != "v53-time-check":
        return cases
    return cases + (
        (
            "time-check",
            "time-check",
            "time-check-view/v1",
            compile_time_check_prepare(
                action="time_check_preview",
                query="验证寻时定盘十二候选 Worker 闭环",
                profile=SYNTHETIC_PROFILE,
                time_range_start="05:00",
                time_range_end="07:00",
                known_events=("synthetic-event-a",),
                dimension_ids=("time_options",),
            ),
        ),
    )


def _assert_runtime_calculated_provider_facts(
    *,
    label: str,
    prepare: Prepare,
    prepared: object,
) -> None:
    """Require each selected Runtime provider to emit calculated facts.

    A typed ViewModel can still be assembled from a malformed or input-only
    brief if this boundary is weakened.  The provider's calculated reference
    namespace is the Runtime-owned proof that the selected algorithm actually
    ran; the host must not manufacture that evidence.
    """

    brief = getattr(prepared, "brief", None)
    if brief is None or not hasattr(brief, "to_dict"):
        raise AssertionError((label, "prepared brief is unavailable"))
    payload = brief.to_dict()
    calculated_facts_by_ref = {
        str(item.get("ref")): item
        for item in payload.get("facts", [])
        if isinstance(item, dict)
        and isinstance(item.get("ref"), str)
        and "/calculated/" in str(item.get("ref"))
    }
    fact_refs = set(calculated_facts_by_ref)
    intent = prepare.intent
    capability_ids: list[str] = []
    primary = intent.get("capability_id")
    if isinstance(primary, str):
        capability_ids.append(primary)
    comparisons = intent.get("comparisons")
    if isinstance(comparisons, list):
        for comparison in comparisons:
            if not isinstance(comparison, dict):
                continue
            capability_id = comparison.get("capability_id")
            if isinstance(capability_id, str):
                capability_ids.append(capability_id)
    for capability_id in dict.fromkeys(capability_ids):
        marker = f"/calculated/{capability_id}/"
        assert any(marker in ref for ref in fact_refs), (
            label,
            capability_id,
            sorted(fact_refs),
        )
        assert any(
            item.get("value") not in (None, "", [], {})
            for ref, item in calculated_facts_by_ref.items()
            if marker in ref
        ), (label, capability_id, sorted(fact_refs))
        if capability_id != primary:
            continue
        for field_id in _REQUIRED_SINGLE_CALCULATED_FACTS.get(capability_id, ()):
            marker = f"/calculated/{capability_id}/{field_id}"
            matching = [
                item
                for ref, item in calculated_facts_by_ref.items()
                if marker in ref
            ]
            assert matching, (
                label,
                capability_id,
                field_id,
                sorted(fact_refs),
            )
            if not (
                capability_id == "liuren"
                and field_id == "timing_candidates"
            ):
                assert any(
                    item.get("value") not in (None, "", [], {})
                    for item in matching
                ), (label, capability_id, field_id)


def _assert_runtime_evidence_contract(
    *,
    label: str,
    prepared: object,
) -> None:
    """Require every real provider to expose evidence or an explicit limit.

    The Runtime owns source retrieval.  The host may not infer a citation from
    a calculated fact, so this keeps the evidence lane closed before Worker
    projection and makes the expected source references available to the
    ReadingDocument assertion below.
    """

    brief = getattr(prepared, "brief", None)
    if brief is None or not hasattr(brief, "to_dict"):
        raise AssertionError((label, "prepared brief is unavailable"))
    payload = brief.to_dict()
    facts = payload.get("facts")
    evidence = payload.get("evidence")
    limits = payload.get("limits")
    assert isinstance(facts, list), (label, "facts")
    assert isinstance(evidence, list), (label, "evidence")
    assert isinstance(limits, list), (label, "limits")
    assert evidence or limits, (label, "Runtime returned neither evidence nor a limit")

    fact_refs = {
        str(item.get("ref"))
        for item in facts
        if isinstance(item, dict) and isinstance(item.get("ref"), str)
    }
    evidence_refs: set[str] = set()
    for item in evidence:
        assert isinstance(item, dict), (label, "evidence item")
        reference = item.get("ref")
        source_title = item.get("source_title")
        supports_fact_refs = item.get("supports_fact_refs")
        assert isinstance(reference, str) and reference, (label, item)
        assert isinstance(source_title, str) and source_title, (label, item)
        assert isinstance(supports_fact_refs, list), (label, item)
        assert set(supports_fact_refs) <= fact_refs, (label, item)
        evidence_refs.add(reference)

    for finding in payload.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        finding_evidence_refs = finding.get("evidence_refs") or []
        assert set(finding_evidence_refs) <= evidence_refs, (label, finding)


async def _runtime() -> MingliRuntime:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    return gate.runtime


async def _run_worker_document_job(
    runtime: MingliRuntime,
    *,
    label: str,
    product_id: str,
    expected_schema: str | None,
    prepare: Prepare,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-v51",
) -> None:
    dimensions = tuple(str(item) for item in prepare.intent["dimension_ids"])
    job = orchestrator_module.ReadingJob(
        id=f"worker-matrix:{label}:{uuid4()}",
        prepare_command=prepare,
        narrative_policy_version="policy-v1",
        output_contract=output_contract_for_dimensions(dimensions),
        language="zh-CN",
        max_output_chars=1200,
        reading_version_id=uuid4(),
        product_id=product_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
    )
    repository = MemoryRepository(orchestrator_module, job)
    machine = orchestrator_module.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=FakeModelGateway(),
        guard=NarrativeGuard(),
        assembler=PublicCopyAssembler(),
        clock=FixedClock(),
        document_builder=ReadingDocumentBuilder(),
        require_reading_document=True,
    )

    prepared = await machine.run(job.id)
    assert prepared.status is ReadingStatus.PREPARED, label
    checkpoint_prepared = repository.checkpoint.prepared
    assert checkpoint_prepared is not None, label
    _assert_runtime_calculated_provider_facts(
        label=label,
        prepare=prepare,
        prepared=checkpoint_prepared,
    )
    _assert_runtime_evidence_contract(label=label, prepared=checkpoint_prepared)
    _assert_runtime_golden_facts(
        label=label,
        prepare=prepare,
        prepared=checkpoint_prepared,
        relationship_type=relationship_type,
    )
    completing = await machine.run(job.id)
    assert completing.status is ReadingStatus.COMPLETING, (
        label,
        repository.attempts,
    )
    accepted = await machine.run(job.id)
    assert accepted.status is ReadingStatus.ACCEPTED, label

    if expected_schema is None:
        # Fortune is deliberately a typed fact panel, not a fabricated chart.
        assert repository.saved_document is None, label
        return

    document = repository.saved_document
    assert document is not None, label
    assert document.view_model.schema_version == expected_schema, label
    prepared_payload = checkpoint_prepared.brief.to_dict()
    expected_evidence_refs = tuple(
        str(item["ref"])
        for item in prepared_payload.get("evidence") or []
        if isinstance(item, dict) and isinstance(item.get("ref"), str)
    )
    assert tuple(item.evidence_ref for item in document.evidence) == expected_evidence_refs, label
    # The public chart projector must not consume private input facts. The
    # immutable document may still retain opaque claim reference IDs for
    # auditability, so scope this assertion to the typed public ViewModel.
    assert "/input/" not in repr(document.view_model.model_dump(mode="json")), label


@pytest.mark.asyncio
async def test_real_runtime_core_providers_reach_worker_accepted_and_typed_document() -> None:
    """The real Runtime and Worker must close every installed single-art route."""

    runtime = await _runtime()
    for label, product_id, expected_schema, prepare in _single_art_cases():
        await _run_worker_document_job(
            runtime,
            label=label,
            product_id=product_id,
            expected_schema=expected_schema,
            prepare=prepare,
            runtime_release=(
                "mingli-runtime-v53-time-check"
                if label == "time-check"
                else "mingli-runtime-v51"
            ),
        )


@pytest.mark.asyncio
async def test_real_runtime_chart_similarity_reaches_worker_and_typed_document() -> None:
    runtime = await _runtime()
    second_profile = ConfirmedProfileVersion(
        subject_ref="profile-version:worker-matrix-similarity-second",
        birth_datetime="1992-11-08T14:20:00+08:00",
        birth_datetime_or_four_pillars="1992-11-08T14:20:00+08:00",
        timezone="Asia/Shanghai",
        location="北京市",
        gender="male",
        time_basis_policy="solar",
        zi_hour_policy="solar",
        longitude=116.4074,
        latitude=39.9042,
        coordinate_source="synthetic-fixture",
    )
    prepare = compile_chart_similarity_prepare(
        action="chart_similarity_preview",
        query="验证同盘四柱事实比较 Worker 闭环",
        profiles=(SYNTHETIC_PROFILE, second_profile),
        dimension_ids=("state",),
    )

    await _run_worker_document_job(
        runtime,
        label="chart-similarity",
        product_id="chart-similarity",
        expected_schema="chart-similarity-view/v1",
        prepare=prepare,
    )


@pytest.mark.asyncio
async def test_v52_relationship_runtime_reaches_worker_and_reading_document() -> None:
    """Run the native relationship Worker path when the v52 release is admitted."""

    if os.environ.get("MINGLI_RUNTIME_RELEASE_PROFILE") != "v52-relationship":
        pytest.skip("v52-relationship Runtime release is not installed in this environment")

    runtime = await _runtime()
    second_profile = ConfirmedProfileVersion(
        subject_ref="profile-version:worker-matrix-second-synthetic",
        birth_datetime="1992-11-08T14:20:00+08:00",
        birth_datetime_or_four_pillars="1992-11-08T14:20:00+08:00",
        timezone="Asia/Shanghai",
        location="北京市",
        gender="male",
        time_basis_policy="solar",
        zi_hour_policy="solar",
        longitude=116.4074,
        latitude=39.9042,
        coordinate_source="synthetic-fixture",
    )
    for art_id, product_id, schema_version in (
        ("bazi", "bazi-relationship", "bazi-relationship/v1"),
        ("ziwei", "ziwei-relationship", "ziwei-relationship/v1"),
        ("qizheng", "qizheng-relationship", "qizheng-relationship/v1"),
    ):
        prepare = compile_relationship_prepare(
            action=f"{art_id}_relationship_preview",
            query="验证关系 Worker 闭环",
            art_id=art_id,
            relationship_type="romantic",
            profiles=(SYNTHETIC_PROFILE, second_profile),
            dimension_ids=("relationship",),
        )
        await _run_worker_document_job(
            runtime,
            label=f"{art_id}-relationship",
            product_id=product_id,
            expected_schema=schema_version,
            prepare=prepare,
            relationship_type="romantic",
            runtime_release="mingli-runtime-v52-relationship",
        )


@pytest.mark.asyncio
async def test_real_runtime_cross_art_products_reach_worker_accepted_and_typed_document() -> None:
    """Cross-art products must preserve their explicit comparison contract."""

    runtime = await _runtime()
    canwen = compile_canwen_prepare(
        action="canwen_preview",
        query="验证三术共同事实 Worker 闭环",
        profile=SYNTHETIC_PROFILE,
        selected_art_ids=("bazi", "ziwei", "qizheng"),
        dimension_ids=("career", "relationship", "state"),
    )
    hecan = compile_hecan_prepare(
        action="hecan_preview",
        query="验证三术合参 Worker 闭环",
        profile=SYNTHETIC_PROFILE,
        selected_art_ids=("bazi", "ziwei", "qizheng"),
        dimension_ids=("career", "relationship", "state"),
    )
    wenshi = compile_wenshi_prepare(
        action="wenshi_one_question",
        query="验证问事三术 Worker 闭环",
        subject_ref="wenshi:worker-matrix-synthetic",
        cast=(6, 7, 8, 9, 6, 7),
        event_datetime=_EVENT_DATETIME,
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "timing"),
        longitude=119.2965,
        latitude=26.0745,
        coordinate_source="synthetic-fixture",
    )

    for label, product_id, expected_schema, prepare in (
        ("canwen", "canwen", "canwen-view/v1", canwen),
        ("hecan", "hecan", "hecan-view/v1", hecan),
        ("wenshi", "wenshi", "wenshi-view/v1", wenshi),
    ):
        await _run_worker_document_job(
            runtime,
            label=label,
            product_id=product_id,
            expected_schema=expected_schema,
            prepare=prepare,
        )
