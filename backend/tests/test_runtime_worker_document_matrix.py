from __future__ import annotations

import os
from datetime import date, datetime
from uuid import uuid4

import pytest
from app.adapters.model import FakeModelGateway
from app.adapters.runtime import MingliRuntime, build_runtime_startup_gate
from app.config import Settings
from app.readings import orchestrator as orchestrator_module
from app.readings.narrative_guard import NarrativeGuard
from app.readings.output_contracts import output_contract_for_product
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

from mingli_paths import MINGLI_RUNTIME_RELEASE_ROOT

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
        "twelve_growth_stages",
        "xunkong",
        "san_yuan",
        "month_command",
        "seasonal_profile",
        "tiaohou_markers",
        "element_inventory",
        "branch_relations",
        "interpretive_candidates",
        "source_conditioned_patterns",
    ),
    "fortune": ("active_luck_cycle", "available_periods", "period_markers"),
    "ziwei": (
        "chart_convention",
        "chinese_date",
        "interpretive_candidates",
        "source_conditioned_patterns",
    ),
    "xingming": (
        "classical_positions",
        "transformations",
        "source_conditioned_patterns",
    ),
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
        "source_conditioned_patterns",
    ),
    "meihua": (
        "body_use",
        "body_relation_facts",
        "seasonal_strength",
        "interpretive_candidates",
        "source_conditioned_patterns",
    ),
    "luming-nayin": ("four_pillars", "independent_lineage"),
    "taiyi": ("board", "board_predicates"),
    "selection": (
        "basis_projection",
        "ranking",
        "source_conditioned_patterns",
    ),
    "fengshui": ("compass", "liqi", "source_conditioned_patterns"),
    "qimen": ("board_digest", "calculated_board_scope", "named_patterns"),
    "liuren": (
        "runtime_core_facts",
        "four_lessons",
        "earth_plate",
        "heaven_plate",
        "heavenly_generals",
        "lesson_method",
        "xunkong",
        "dimension_facts",
        "timing_candidates",
    ),
    "physiognomy": (
        "normalized_visible_observations",
        "source_comparison",
    ),
    "time-check": (
        "candidate_count",
        "candidates",
        "known_time_range",
        "time_basis_policy",
        "event_input_status",
        "candidate_rankings",
        "event_matches",
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


def _assert_bazi_reasoning_sources_are_shipped(
    reasoning_tools: object,
) -> None:
    """Every Bazi reasoning source ref must resolve inside the frozen release."""

    assert isinstance(reasoning_tools, dict)
    release_root = MINGLI_RUNTIME_RELEASE_ROOT
    for tool_id, tool in reasoning_tools.items():
        assert isinstance(tool, dict), tool_id
        source_refs = tool.get("source_refs")
        assert isinstance(source_refs, list) and source_refs, tool_id
        for source_ref in source_refs:
            assert isinstance(source_ref, dict), (tool_id, source_ref)
            pack = source_ref.get("pack")
            rule_id = source_ref.get("rule_id")
            assert isinstance(pack, str) and pack, (tool_id, source_ref)
            assert isinstance(rule_id, str) and rule_id, (tool_id, source_ref)
            anchor = source_ref.get("source_anchor")
            if isinstance(anchor, str) and anchor:
                source_path = release_root / anchor.split("#", 1)[0]
            else:
                source_path = release_root / "references" / "books" / pack / "rules.md"
            assert source_path.is_file(), (tool_id, source_ref, source_path)
            rule_token = rule_id.split("~", 1)[0]
            assert rule_token in source_path.read_text(encoding="utf-8"), (
                tool_id,
                source_ref,
                source_path,
            )


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
        growth = values["twelve_growth_stages"]
        assert isinstance(growth, dict), label
        assert {
            position: item["stage"]
            for position, item in growth.items()
        } == {
            "year": "养",
            "month": "冠带",
            "day": "墓",
            "hour": "绝",
        }, label
        assert all(
            item["source_dependency_id"] == "bazi.chart.twelve-growth-stages-v1"
            and item["boundary"]
            and item["direction"] in {"forward", "reverse"}
            for item in growth.values()
        ), label
        assert values["xunkong"] == {
            "boundary": "按日柱所属旬计算旬空事实；不能单独推出吉凶、六亲或事件结论",
            "branches": ["午", "未"],
            "day_pillar": "丙戌",
            "source_dependency_id": "bazi.chart.xunkong-sexagenary-v1",
            "xun": "甲申",
        }, label
        assert values["san_yuan"] == {
            "boundary": "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
            "ming_gong": "甲戌",
            "shen_gong": "庚午",
            "source": "lunar-typescript-auxiliary",
            "source_dependency_id": "bazi.chart.san-yuan-lunar-typescript-v1",
            "tai_yuan": "己未",
        }, label
        candidates = values["interpretive_candidates"]
        assert isinstance(candidates, dict), label
        assert candidates["strength"]["status"] == "evidence_only", label
        assert candidates["strength"]["same_element_occurrences"] == 3, label
        assert candidates["strength"]["resource_occurrences"] == 4, label
        month_order = candidates["strength"]["month_order_adjudication"]
        assert month_order["status"] == "adjudicated_month_order_state", label
        assert month_order["whole_chart_strength_verdict"] is None, label
        assert month_order["useful_god_verdict"] is None, label
        assert month_order["source_ref"]["verification_status"] == "verified", label
        assert candidates["structure"]["status"] == "candidate_only", label
        assert len(candidates["salience_signals"]) == 9, label
        reasoning_tools = candidates["reasoning_tools"]
        _assert_bazi_reasoning_sources_are_shipped(reasoning_tools)
        expected_tools = {
            "strength_evidence",
            "tiaohou_candidates",
            "month_structure_candidate",
            "ziping_month_pattern_adjudication",
            "conflict_arbitration",
        }
        dimensions = {
            str(item) for item in (prepare.intent.get("dimension_ids") or ())
        }
        if "career" in dimensions:
            expected_tools.add("domain_work")
        if "relationship" in dimensions:
            expected_tools.add("domain_relationship")
        assert set(reasoning_tools) == expected_tools, label
        if label != "bazi":
            return
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == [
            "DR-01-01",
            "QR-02-01",
            "QTB-M01",
            "R-01-02",
            "R-02-04",
            "ZPR-01",
        ], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["source_dependency_id"] == "bazi.source-conditioned-patterns"
            and "verdict" not in item
            for item in source_patterns
        ), label
        assert reasoning_tools["strength_evidence"]["output"]["evidence_lean"] == (
            "mixed"
        ), label
        tiaohou = reasoning_tools["tiaohou_candidates"]
        assert tiaohou["output"]["rule_id"] == "QR-02-01", label
        assert tiaohou["output"]["month_branch"] == "辰", label
        assert tiaohou["output"]["status"] == (
            "adjudicated_seasonal_priority"
        ), label
        assert tiaohou["output"]["verification_status"] == "verified", label
        assert tiaohou["output"]["hard_verdict"] is None, label
        assert all(
            "day" not in item["visible_positions"]
            for item in tiaohou["output"]["matches"]
        ), label
        pattern_adjudication = reasoning_tools[
            "ziping_month_pattern_adjudication"
        ]
        assert pattern_adjudication["output"]["status"] == (
            "adjudicated_pattern_entry"
        ), label
        assert pattern_adjudication["output"]["pattern_label"] == (
            "食神格入口"
        ), label
        assert pattern_adjudication["output"]["hard_verdict"] is None, label
        assert pattern_adjudication["source_refs"][0][
            "verification_status"
        ] == "verified", label
        assert reasoning_tools["domain_work"]["output"]["status"] == (
            "indicators_only"
        ), label
        assert reasoning_tools["domain_work"]["output"]["domain"] == "work", label
        assert reasoning_tools["domain_work"]["output"]["gender"] == "female", label
        arbitration = reasoning_tools["conflict_arbitration"]
        assert arbitration["output"]["policy_id"] == (
            "bazi.question-focus-routing-v1"
        ), label
        assert arbitration["output"]["policy_status"] == (
            "product_contract_not_classical_verdict"
        ), label
        assert arbitration["output"]["status"] == (
            "requires_question_specific_adjudication"
        ), label
        assert arbitration["output"]["selected_primary_view"] is None, label
        assert arbitration["output"]["hard_verdict"] is None, label
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
        markers = values["period_markers"]
        assert isinstance(markers, list) and markers, label
        assert markers[0]["primary_mechanism_ids"], label
        assert markers[0]["unresolved_boundaries"], label
    elif capability_id == "ziwei":
        assert values["chinese_date"] == "甲戌 戊辰 丙戌 辛卯", label
        convention = values["chart_convention"]
        assert isinstance(convention, dict), label
        assert (convention["engine"], convention["fix_leap"]) == (
            {"name": "iztro", "version": "2.5.8"},
            True,
        ), label
        candidates = values["interpretive_candidates"]
        assert candidates["status"] == "candidate_only", label
        assert candidates["hard_verdict"] is None, label
        assert [item["role"] for item in candidates["san_fang_si_zheng"]] == [
            "life",
            "opposite",
            "wealth",
            "career",
        ], label
        assert len(candidates["evaluated_rules"]) == 10, label
        assert all(item["hard_verdict"] is None for item in candidates["evaluated_rules"]), label
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == [
            "TR-01",
            "ZW-M01",
        ], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            for item in source_patterns
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
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == [
            "GR-01-01",
            "XR-M01",
            "XXDC-M01",
        ], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            for item in source_patterns
        ), label
    elif capability_id == "liuyao":
        source_patterns = values["source_conditioned_patterns"]
        expected_source_pattern_ids = [
            "BSZZ-M01",
            "HJC-M001",
            "HZL-M001",
            "ZZR-M001",
        ]
        if label in {
            "liuyao-finance",
            "liuyao-two-present-single-moving",
        }:
            expected_source_pattern_ids.insert(2, "HJC-R009")
        if label == "liuyao-two-present-single-moving":
            expected_source_pattern_ids.insert(4, "ZR-04-04")
        assert [item["local_rule_id"] for item in source_patterns] == (
            expected_source_pattern_ids
        ), label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["source_dependency_id"]
            == "liuyao.source-conditioned-patterns"
            and "verdict" not in item
            for item in source_patterns
        ), label
        if label == "liuyao-two-present-single-moving":
            selection = values["useful_spirit_selection"]
            assert isinstance(selection, dict), label
            assert selection["question_context"]["question_class"] == (
                "finance"
            ), label
            line_adjudication = selection["role_adjudication"][
                "specific_line_adjudication"
            ]
            assert line_adjudication["visible_candidate_lines"] == [3, 6], label
            assert line_adjudication["moving_visible_candidate_lines"] == [3], label
            return
        changed = values["changed_hexagram"]
        assert isinstance(changed, dict), label
        assert (changed["name"], changed["king_wen_number"]) == (
            "风泽中孚",
            61,
        ), label
        requested = values["requested_useful_spirit_candidates"]
        assert isinstance(requested, dict), label
        selection = values["useful_spirit_selection"]
        assert isinstance(selection, dict), label
        chain = selection["chain_candidates"]
        assert isinstance(chain, dict), label
        strength = selection["strength_evidence"]
        assert isinstance(strength, dict), label
        dimensions = {
            str(item) for item in (prepare.intent.get("dimension_ids") or ())
        }
        if label == "liuyao-finance":
            assert selection["question_context"] == {
                "classification_source": "explicit_structured_input",
                "question_class": "finance",
            }, label
            assert selection["role_adjudication"] == {
                "status": "adjudicated_question_role_set",
                "decision_scope": "finance_useful_spirit_role_set",
                "question_class": "finance",
                "primary_relative": "妻财",
                "supporting_relatives": ["子孙"],
                "obstacle_attention_relatives": ["兄弟", "官鬼", "父母"],
                "specific_line_selection": 4,
                "specific_line_adjudication": {
                    "status": "adjudicated_unique_visible_line",
                    "decision_scope": "finance_primary_relative_line_identity",
                    "primary_relative": "妻财",
                    "visible_candidate_count": 1,
                    "visible_candidate_lines": [4],
                    "moving_visible_candidate_count": 1,
                    "moving_visible_candidate_lines": [4],
                    "specific_line_selection": 4,
                    "derivation_basis": (
                        "verified_role_plus_runtime_unique_visible_candidate"
                    ),
                    "selection_source_ref": {
                        "pack": "divination/huangjin-ce",
                        "rule_id": "HJC-R009",
                        "source_anchor": (
                            "references/books/divination/huangjin-ce/"
                            "rules.md#HJC-R009"
                        ),
                        "verification_status": "verified",
                        "binding_digest": (
                            "2b46bab3c084a2adbdc56de6ee3ea29e9890712767a43c5cd1e68a845c23cbdc"
                        ),
                    },
                    "hard_verdict": None,
                },
                "hard_verdict": None,
                "source_ref": {
                    "pack": "divination/huangjin-ce",
                    "rule_id": "HJC-R009",
                    "source_anchor": (
                        "references/books/divination/huangjin-ce/"
                        "rules.md#HJC-R009"
                    ),
                    "verification_status": "verified",
                    "binding_digest": (
                        "2b46bab3c084a2adbdc56de6ee3ea29e9890712767a43c5cd1e68a845c23cbdc"
                    ),
                },
                "unresolved_checks": [
                    "月日旺衰与空破冲合",
                    "动变生克与救应",
                    "成败、应期与事件结果",
                ],
            }, label
            assert requested.get("妻财"), label
            assert requested.get("子孙"), label
            assert chain["status"] == "candidate_only", label
            assert chain["chains"], label
            assert strength["status"] == "candidate_only", label
        elif "career" in dimensions:
            assert isinstance(requested.get("官鬼"), list), label
            assert requested["官鬼"], label
            assert chain["status"] == "candidate_only", label
            assert chain["chains"], label
            assert set(chain["chains"][0]["candidates"]) == {
                "用神",
                "原神",
                "忌神",
                "仇神",
            }, label
            assert strength["status"] == "candidate_only", label
            source_rule = strength["source_rules"][0]
            assert source_rule["rule_id"] == "ZR-05-05", label
            source_path = MINGLI_RUNTIME_RELEASE_ROOT / source_rule[
                "source_anchor"
            ].split("#", 1)[0]
            assert source_path.is_file(), label
            assert "ZR-05-05" in source_path.read_text(encoding="utf-8"), label
            useful_strength = strength["by_relative"]["官鬼"]
            assert useful_strength["status"] == "candidate_only", label
            assert useful_strength["candidates"], label
            assert all(
                candidate["hard_verdict"] is None
                for candidate in useful_strength["candidates"]
            ), label
        else:
            assert requested == {}, label
            assert chain["status"] == "not_requested", label
            assert chain["chains"] == [], label
            assert strength["status"] == "not_requested", label
    elif capability_id == "meihua":
        body_use = values["body_use"]
        assert isinstance(body_use, dict), label
        assert (
            body_use["body"]["trigram"],
            body_use["use"]["trigram"],
            body_use["relation"],
        ) == ("坎", "坤", "用克体"), label
        candidates = values["interpretive_candidates"]
        assert isinstance(candidates, dict), label
        assert candidates["status"] == "source_adjudicated_relations", label
        assert candidates["hard_verdict"] is None, label
        assert candidates["verification_status"] == "verified", label
        assert candidates["requires_classical_adjudication"] is False, label
        assert candidates["requires_synthesis_adjudication"] is True, label
        assert len(candidates["relation_candidates"]) == 5, label
        assert candidates["relation_candidates"][0]["rule_id"] == "MR-04-02", label
        assert all(
            candidate["hard_verdict"] is None
            for candidate in candidates["relation_candidates"]
        ), label
        assert all(
            candidate["status"] == "relation_adjudicated_not_event_verdict"
            and candidate["verification_status"] == "verified"
            and candidate["relation_adjudication"]["event_verdict"] is None
            and candidate["relation_adjudication"]["source_refs"][0][
                "verification_status"
            ]
            == "verified"
            for candidate in candidates["relation_candidates"]
        ), label
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == [
            "HR-04-01",
            "MR-01-01",
            "ZZR-M001",
        ], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["source_dependency_id"] == "meihua.source-conditioned-patterns"
            for item in source_patterns
        ), label
    elif capability_id == "luming-nayin":
        assert values["four_pillars"] == {
            "day": "丙戌",
            "hour": "辛卯",
            "month": "戊辰",
            "year": "甲戌",
        }, label
        assert values["independent_lineage"] == "early-luming-nayin", label
        source_patterns = values["source_conditioned_patterns"]
        assert isinstance(source_patterns, list) and source_patterns, label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["applicability_adjudication"]["status"]
            == "adjudicated_rule_applicability"
            and item["applicability_adjudication"]["source_ref"][
                "verification_status"
            ]
            == "verified"
            and item["applicability_adjudication"]["life_verdict"] is None
            for item in source_patterns
        ), label
    elif capability_id == "taiyi":
        board = values["board"]
        assert isinstance(board, dict), label
        assert board["taiyi_position"] == "艮", label
        predicates = values["board_predicates"]
        assert isinstance(predicates, list), label
        assert [item["id"] for item in predicates] == ["TY-P01", "TY-P07"], label
        assert all(
            item["identity_adjudication"]["status"]
            == "adjudicated_pattern_identity"
            and item["identity_adjudication"]["source_ref"]["rule_id"]
            == item["id"]
            and item["identity_adjudication"]["event_verdict"] is None
            for item in predicates
        ), label
    elif capability_id == "selection":
        if label.startswith("selection-burial-"):
            basis = values["basis_projection"]
            assert isinstance(basis, dict), label
            assert basis["complete_counts"] == {
                "calendar_candidates": 1,
                "date_time_candidates": 13,
                "eligible_candidates": 0,
                "eligible_date_time_candidates": 0,
                "eliminations": 1,
                "ranking.eligible_candidate_ids": 0,
                "ranking.eligible_date_time_candidate_ids": 0,
                "ranking.ordered_candidate_ids": 1,
                "ranking.ordered_date_time_candidate_ids": 13,
            }, label
            assert values["no_valid_candidate"] is True, label
            ranking = values["ranking"]
            assert isinstance(ranking, dict), label
            assert ranking["method"] == "explainable_lexicographic_v1", label
            assert ranking["eligible_candidate_ids"] == [], label
            return
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
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == [
            "KR-05",
        ], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            for item in source_patterns
        ), label
    elif capability_id == "fengshui":
        compass = values["compass"]
        assert isinstance(compass, dict), label
        assert (
            compass["facing"]["degrees"],
            compass["facing"]["mountain"],
            compass["facing"]["trigram"],
        ) == (180.0, "午", "离"), label
        source_patterns = values["source_conditioned_patterns"]
        assert [item["local_rule_id"] for item in source_patterns] == ["YZS-R005"], label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["source_dependency_id"]
            == "fengshui.source-conditioned-patterns"
            for item in source_patterns
        ), label
    elif capability_id == "qimen":
        scope = values["calculated_board_scope"]
        assert isinstance(scope, dict), label
        assert (scope["dun"], scope["number"], scope["yuan"]) == (
            "yin",
            8,
            "lower",
        ), label
        patterns = values["named_patterns"]
        assert isinstance(patterns, list), label
        pattern_ids = {item["id"] for item in patterns}
        assert {"QM-P16", "QM-P17"} <= pattern_ids, label
        assert all(
            item["status"] == "predicate_matched_not_verdict" for item in patterns
        ), label
        assert all(
            item["identity_adjudication"]["status"]
            == "adjudicated_pattern_identity"
            and item["identity_adjudication"]["pattern_id"] == item["id"]
            and item["identity_adjudication"]["hard_verdict"] is None
            and item["identity_adjudication"]["event_verdict"] is None
            and item["identity_adjudication"]["source_ref"][
                "verification_status"
            ]
            == "verified"
            for item in patterns
        ), label
    elif capability_id == "liuren":
        assert values["day_hour"] == {"day": "庚申", "hour": "辛巳"}, label
        assert values["earth_plate"] == list("子丑寅卯辰巳午未申酉戌亥"), label
        runtime_core_facts = values["runtime_core_facts"]
        assert isinstance(runtime_core_facts, dict), label
        source_patterns = runtime_core_facts["source_conditioned_patterns"]
        assert isinstance(source_patterns, list) and source_patterns, label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and item["source_dependency_id"]
            == "liuren.source-conditioned-structural-patterns-v1"
            and "verdict" not in item
            for item in source_patterns
        ), label
        lessons = values["four_lessons"]
        assert isinstance(lessons, list), label
        assert lessons[0] == {
            "lesson": 1,
            "lower": "庚",
            "lower_lodge": "申",
            "relation": "比和",
            "upper": "酉",
        }, label
        dimension_facts = values["dimension_facts"]
        assert isinstance(dimension_facts, dict), label
        outcome = dimension_facts["outcome"]
        assert isinstance(outcome, dict), label
        outcome_evidence = outcome["rule_evidence"]
        assert isinstance(outcome_evidence, dict), label
        assert outcome_evidence["status"] == "not_calculated", label
        assert outcome_evidence["hard_verdict"] is None, label
        assert outcome_evidence["requires_school_adjudication"] is True, label
        assert outcome_evidence["matched"] == [], label
        assert len(outcome_evidence["not_evaluated"]) == 4, label
        timing = dimension_facts["timing"]
        assert isinstance(timing, dict), label
        timing_evidence = timing["rule_evidence"]
        assert timing_evidence["status"] == "matched_evidence", label
        assert timing_evidence["hard_verdict"] is None, label
        timing_candidates = values["timing_candidates"]
        assert isinstance(timing_candidates, list) and timing_candidates, label
        assert timing_candidates[0]["source_rule"] == "LM-R21", label
        assert timing_candidates[0]["candidate_not_guarantee"] is True, label
    elif capability_id == "physiognomy":
        observations = values["normalized_visible_observations"]
        assert isinstance(observations, list), label
        expected_observation = {
            "face": ("forehead", "region_visible"),
            "palm": ("life_line", "line_continuous"),
            "posture": ("shoulder_line", "level"),
            "combined": ("walking_gait", "steady"),
        }.get(str(values.get("observation_scope")), ("forehead", "region_visible"))
        assert (
            observations[0]["region"],
            observations[0]["descriptor"],
            observations[0]["quality_status"],
        ) == (*expected_observation, "eligible"), label
        comparison = values["source_comparison"]
        assert isinstance(comparison, dict), label
        assert comparison["disagreements_retained"] is True, label
        patterns = values["source_conditioned_patterns"]
        assert isinstance(patterns, list), label
        expected_pattern_ids = {
            "face": ["LZ-R01", "SR-02-04"],
            "combined": ["LZ-R01"],
            "palm": [],
            "posture": [],
        }[str(values.get("observation_scope"))]
        assert [item["local_rule_id"] for item in patterns] == expected_pattern_ids, label
        assert all(
            item["status"] == "predicate_matched_not_verdict"
            and "verdict" not in item
            for item in patterns
        ), label
    elif capability_id == "time-check":
        assert values["candidate_count"] == 12, label
        candidates = values["candidates"]
        assert isinstance(candidates, list), label
        assert len(candidates) == 12, label
        assert candidates[0]["hour_branch"] == "子", label
        assert candidates[-1]["hour_branch"] == "亥", label
        assert [candidate["local_civil_datetime"][11:16] for candidate in candidates] == [
            "00:00",
            "02:00",
            "04:00",
            "06:00",
            "08:00",
            "10:00",
            "12:00",
            "14:00",
            "16:00",
            "18:00",
            "20:00",
            "22:00",
        ], label
        assert [
            candidate["four_pillars"]["hour"][1]
            for candidate in candidates
        ] == list("子丑寅卯辰巳午未申酉戌亥"), label
        assert values["time_basis_policy"] == "local_apparent_solar-v1", label
        assert values["event_input_status"] == "structured_valid", label
        assert values["ranking_status"] == "candidate_evidence_ranked", label
        assert values["event_matching_status"] == "structured_evidence", label
        rankings = values["candidate_rankings"]
        assert isinstance(rankings, list), label
        assert len(rankings) == 12, label
        assert rankings[0]["rank"] == 1, label
        assert isinstance(values["event_matches"], list), label
        assert len(values["event_matches"]) == 2, label


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


def _physiognomy_spec(
    subject_ref: str,
    *,
    scope: str = "face",
    taxonomy: str = "anatomical_face_v1",
    region: str = "forehead",
    descriptor: str = "region_visible",
) -> dict[str, object]:
    return {
        "schema_version": "mingli-physiognomy-input-v1",
        "observation_scope": scope,
        "subject_ref": subject_ref,
        "requested_targets": [
            {
                "target_id": "tid-22222222222222222222222222222222",
                "taxonomy": taxonomy,
                "region": region,
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
                "region": region,
                "feature_kind": "visible_morphology",
                "visibility": "full",
                "value": {"descriptor": descriptor},
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
            "fortune-facts-view/v1",
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
                dimension_ids=("career", "outcome", "timing"),
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
                action="liuren_timing_question",
                query="验证大六壬 Worker 闭环",
                subject_ref="liuren:worker-matrix-synthetic",
                event_datetime=event,
                confirmed_timezone="Asia/Shanghai",
                location="福建省福州市",
                dimension_ids=("outcome", "timing"),
                timing_start=date(2026, 8, 15),
                timing_end=date(2026, 9, 14),
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
                known_event_facts=(
                    {
                        "event_id": "synthetic-education",
                        "occurred_at": "2012-09-01",
                        "domain": "education",
                    },
                    {
                        "event_id": "synthetic-career",
                        "occurred_at": "2018-07-01T09:00:00+08:00",
                        "domain": "career",
                    },
                ),
                dimension_ids=("time_options",),
            ),
        ),
    )


def _assert_runtime_calculated_provider_facts(
    *,
    label: str,
    prepare: Prepare,
    prepared: object,
    required_primary_calculated_fields: tuple[str, ...] | None = None,
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
        required_fields = (
            required_primary_calculated_fields
            if required_primary_calculated_fields is not None
            else _REQUIRED_SINGLE_CALCULATED_FACTS.get(capability_id, ())
        )
        for field_id in required_fields:
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
    required_primary_calculated_fields: tuple[str, ...] | None = None,
) -> object | None:
    dimensions = tuple(str(item) for item in prepare.intent["dimension_ids"])
    job = orchestrator_module.ReadingJob(
        id=f"worker-matrix:{label}:{uuid4()}",
        prepare_command=prepare,
        narrative_policy_version="policy-v1",
        output_contract=output_contract_for_product(product_id, dimensions),
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
        required_primary_calculated_fields=required_primary_calculated_fields,
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
    if expected_schema == "daliuren-chart/v1":
        core_facts = document.view_model.core_facts
        assert core_facts is not None, label
        source_patterns = core_facts.source_conditioned_patterns
        assert source_patterns, label
        assert all(
            item.status == "predicate_matched_not_verdict"
            and item.source_dependency_id
            == "liuren.source-conditioned-structural-patterns-v1"
            for item in source_patterns
        ), label
    return document


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
async def test_real_runtime_bazi_deep_facts_reach_paid_typed_document() -> None:
    """The existing Bazi deep contract must also survive model audit."""

    runtime = await _runtime()
    prepare = compile_bazi_prepare(
        action="bazi_deep",
        query="验证八字深读事实进入 Worker 与类型化文档",
        profile=SYNTHETIC_PROFILE,
        dimension_ids=("career",),
    )

    document = await _run_worker_document_job(
        runtime,
        label="bazi-deep",
        product_id="bazi-deep",
        expected_schema="bazi-chart/v1",
        prepare=prepare,
    )

    assert document is not None
    assert document.view_model.pillars


@pytest.mark.asyncio
async def test_real_runtime_qimen_deep_facts_reach_paid_typed_document() -> None:
    """The paid Qimen contract must consume the same frozen board facts."""

    runtime = await _runtime()
    prepare = compile_qimen_prepare(
        action="qimen_deep",
        query="验证奇门深读事实进入 Worker 与类型化文档",
        subject_ref="qimen-deep:worker-matrix-synthetic",
        event_datetime=_EVENT_DATETIME,
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "timing", "state"),
        longitude=119.2965,
        latitude=26.0745,
        coordinate_source="synthetic-fixture",
    )

    document = await _run_worker_document_job(
        runtime,
        label="qimen-deep",
        product_id="qimen-deep",
        expected_schema="qimen-chart/v1",
        prepare=prepare,
        runtime_release="mingli-runtime-v53-time-check",
    )

    assert document is not None
    assert document.view_model.named_patterns
    assert all(
        pattern.identity_adjudication.status
        == "adjudicated_pattern_identity"
        and pattern.identity_adjudication.event_verdict is None
        for pattern in document.view_model.named_patterns
    )
    assert any(len(palace.stars) > 1 for palace in document.view_model.palaces)


@pytest.mark.asyncio
async def test_real_runtime_liuyao_deep_facts_reach_paid_typed_document() -> None:
    """The paid Liuyao contract must preserve candidates without a verdict."""

    runtime = await _runtime()
    prepare = compile_liuyao_prepare(
        action="liuyao_deep",
        query="验证六爻候选证据进入 Worker 与类型化文档",
        subject_ref="liuyao-deep:worker-matrix-synthetic",
        cast=(6, 7, 8, 9, 6, 7),
        event_datetime=_EVENT_DATETIME,
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "timing", "state"),
    )

    document = await _run_worker_document_job(
        runtime,
        label="liuyao-deep",
        product_id="liuyao-deep",
        expected_schema="liuyao-chart/v1",
        prepare=prepare,
        runtime_release="mingli-runtime-v53-time-check",
    )

    assert document is not None
    assert document.view_model.core_facts is not None
    assert document.view_model.core_facts.useful_spirit_candidates
    assert document.view_model.core_facts.useful_spirit_selection
    assert document.view_model.core_facts.source_conditioned_patterns


@pytest.mark.asyncio
async def test_real_runtime_liuyao_finance_question_reaches_source_conditioned_pattern() -> None:
    """An explicit finance class must reach the Liuyao source-rule boundary."""

    runtime = await _runtime()
    prepare = compile_liuyao_prepare(
        action="liuyao_one_question",
        query="验证求财问题的来源条件进入 Worker 与类型化文档",
        subject_ref="liuyao-finance:worker-matrix-synthetic",
        cast=(6, 7, 8, 9, 6, 7),
        event_datetime=_EVENT_DATETIME,
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "timing", "state"),
        question_class="finance",
    )

    document = await _run_worker_document_job(
        runtime,
        label="liuyao-finance",
        product_id="liuyao-deep",
        expected_schema="liuyao-chart/v1",
        prepare=prepare,
        runtime_release="mingli-runtime-v53-time-check",
    )

    assert document is not None
    assert document.view_model.core_facts is not None
    selection = document.view_model.core_facts.useful_spirit_selection
    assert selection is not None
    assert selection.question_context is not None
    assert selection.question_context.question_class == "finance"
    role_adjudication = selection.role_adjudication
    assert role_adjudication.status == "adjudicated_question_role_set"
    assert role_adjudication.primary_relative == "妻财"
    assert role_adjudication.supporting_relatives == ("子孙",)
    assert role_adjudication.specific_line_selection == 4
    assert role_adjudication.specific_line_adjudication.status == (
        "adjudicated_unique_visible_line"
    )
    assert role_adjudication.hard_verdict is None
    matches = document.view_model.core_facts.source_conditioned_patterns
    finance_match = next(
        item for item in matches if item.local_rule_id == "HJC-R009"
    )
    assert finance_match.status == "predicate_matched_not_verdict"
    assert all("verdict" not in item.model_dump() for item in matches)


@pytest.mark.asyncio
async def test_real_runtime_liuyao_two_present_single_moving_rule_reaches_typed_document() -> None:
    """The checked two-present rule must select only the moving visible line."""

    runtime = await _runtime()
    prepare = compile_liuyao_prepare(
        action="liuyao_one_question",
        query="验证妻财两现且仅一爻发动时的取爻规则进入类型化文档",
        subject_ref="liuyao-two-present:worker-matrix-synthetic",
        cast=(6, 6, 6, 6, 6, 7),
        event_datetime=_EVENT_DATETIME,
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "timing", "state"),
        question_class="finance",
    )

    document = await _run_worker_document_job(
        runtime,
        label="liuyao-two-present-single-moving",
        product_id="liuyao-deep",
        expected_schema="liuyao-chart/v1",
        prepare=prepare,
        runtime_release="mingli-runtime-v53-time-check",
    )

    assert document is not None
    assert document.view_model.core_facts is not None
    selection = document.view_model.core_facts.useful_spirit_selection
    assert selection is not None
    role_adjudication = selection.role_adjudication
    assert role_adjudication.status == "adjudicated_question_role_set"
    assert role_adjudication.specific_line_selection == 3
    line_adjudication = role_adjudication.specific_line_adjudication
    assert line_adjudication.status == "adjudicated_single_moving_visible_line"
    assert line_adjudication.visible_candidate_lines == (3, 6)
    assert line_adjudication.moving_visible_candidate_lines == (3,)
    assert line_adjudication.selection_source_ref is not None
    assert line_adjudication.selection_source_ref.rule_id == "ZR-04-04"
    assert line_adjudication.hard_verdict is None
    matches = document.view_model.core_facts.source_conditioned_patterns
    line_rule_match = next(
        item for item in matches if item.local_rule_id == "ZR-04-04"
    )
    assert line_rule_match.status == "predicate_matched_not_verdict"


@pytest.mark.asyncio
async def test_real_runtime_selection_burial_rules_reach_worker_and_typed_document() -> None:
    """Source-backed burial rules must survive the Worker projection boundary."""

    runtime = await _runtime()
    for day, action, event_fact_field, source_anchor in (
        ("2026-01-03", "安葬", "sansang_day", "chen-zixing-sansang-v1"),
        ("2026-01-10", "破土", "tujin", "chen-zixing-tujin-v1"),
    ):
        prepare = compile_selection_prepare(
            action="selection_preview",
            query="验证安葬与破土来源规则的 Worker 闭环",
            subject_ref=f"selection:worker-burial-{day}",
            event_profile="burial_funeral",
            requested_actions=(action,),
            date_range_start=day,
            date_range_end=day,
            confirmed_timezone="Asia/Shanghai",
            location="上海市",
            dimension_ids=("timing", "state"),
        )
        document = await _run_worker_document_job(
            runtime,
            label=f"selection-burial-{day}",
            product_id="selection",
            expected_schema="selection-chart/v1",
            prepare=prepare,
            runtime_release="mingli-runtime-v53-time-check",
        )
        assert document is not None
        view_model = document.view_model
        assert view_model.no_valid_candidate is True
        matching_eliminations = [
            item
            for item in view_model.eliminations
            if item.get("candidate_id") == day
        ]
        assert len(matching_eliminations) == 1
        assert any(
            isinstance(reason, dict)
            and reason.get("code") == "event_fact_hard_elimination"
            and reason.get("event_fact_field") == event_fact_field
            and source_anchor in (reason.get("source_anchors") or [])
            for reason in matching_eliminations[0]["rejection_reasons"]
        )


@pytest.mark.parametrize(
    ("scope", "taxonomy", "region", "descriptor"),
    [
        ("palm", "anatomical_palm_v1", "life_line", "line_continuous"),
        ("posture", "posture_observation_v1", "shoulder_line", "level"),
        ("combined", "posture_observation_v1", "walking_gait", "steady"),
    ],
)
async def test_real_runtime_non_face_physiognomy_modes_reach_worker_and_document(
    scope: str,
    taxonomy: str,
    region: str,
    descriptor: str,
) -> None:
    runtime = await _runtime()
    subject_ref = "sid-22222222222222222222222222222222"
    prepare = compile_physiognomy_prepare(
        action="physiognomy_preview",
        query="验证非面部相法观察 Worker 闭环",
        subject_ref=subject_ref,
        physiognomy_spec=_physiognomy_spec(
            subject_ref,
            scope=scope,
            taxonomy=taxonomy,
            region=region,
            descriptor=descriptor,
        ),
        dimension_ids=("state", "source_comparison"),
    )

    await _run_worker_document_job(
        runtime,
        label=f"physiognomy-{scope}",
        product_id="jianxiang",
        expected_schema="physiognomy-view/v1",
        prepare=prepare,
        runtime_release="mingli-runtime-v53-time-check",
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
        capability_id = str(prepare.intent["capability_id"])
        required_fields = {
            "bazi": ("four_pillars",),
            "ziwei": ("palaces",),
            "xingming": ("classical_positions",),
        }[capability_id]
        document = await _run_worker_document_job(
            runtime,
            label=f"{art_id}-relationship",
            product_id=product_id,
            expected_schema=schema_version,
            prepare=prepare,
            relationship_type="romantic",
            runtime_release="mingli-runtime-v52-relationship",
            required_primary_calculated_fields=required_fields,
        )
        assert document is not None
        assert getattr(getattr(document, "view_model", None), "signals", ())


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
        document = await _run_worker_document_job(
            runtime,
            label=label,
            product_id=product_id,
            expected_schema=expected_schema,
            prepare=prepare,
        )
        assert document is not None
        dimensions = getattr(document.view_model, "dimensions", ())
        signal_ids = {
            signal.signal_id
            for dimension in dimensions
            for signal in dimension.signals
        }
        if label in {"canwen", "hecan"}:
            assert "bazi.career.source_pattern.DR-01-01" in signal_ids
        else:
            assert "liuyao.outcome.source_pattern.HJC-M001" in signal_ids
            assert "daliuren.timing.timing_candidate_evidence" in signal_ids
