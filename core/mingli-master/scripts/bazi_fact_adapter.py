#!/usr/bin/env python3
"""Build a deterministic Bazi fact layer from supplied pillars or birth data.

The adapter deliberately separates two scopes:

* ``pillars`` validates user/OCR-supplied sexagenary pillars and derives
  static facts. With a valid gender it can also derive luck-cycle direction
  and pillar sequence, but not the original birth calendar or luck timing.
* ``birth`` calculates a declared-local-time chart with ``sxtwl``, including
  lunar conversion, solar-term context, and a versioned major-luck convention.

JSON is written to stdout. Diagnostics are written to stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping, TypeAlias
from zoneinfo import ZoneInfo

from evidence_contract import canonical_digest
from fact_contracts.bazi import BaziCanonicalFacts, BaziFactContract
from fact_contracts.common import EngineProvenance
from reading_engine import calendar_core, evidence_rules
from reading_engine.contracts import FactRef
from reading_engine.engine_adapter import (
    EngineAdapterBase,
    EngineAdapterResult,
)


VERSION = "1.3.0"
ADAPTER_NAME = "mingli-master.bazi_fact_adapter"
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
POSITIONS = ("year", "month", "day", "hour")
ELEMENTS = ("木", "火", "土", "金", "水")
STEM_ELEMENT = dict(zip(STEMS, ("木", "木", "火", "火", "土", "土", "金", "金", "水", "水")))
BRANCH_ELEMENT = dict(zip(BRANCHES, ("水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水")))
POLARITY = {stem: ("阳" if index % 2 == 0 else "阴") for index, stem in enumerate(STEMS)}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}


def _seasonal_states(command_element: str) -> dict[str, str]:
    """Map each element to its deterministic state under the month command."""

    generated = ELEMENTS[(ELEMENTS.index(command_element) + 1) % 5]
    generator = ELEMENTS[(ELEMENTS.index(command_element) - 1) % 5]
    controller = next(
        element for element, target in CONTROLS.items() if target == command_element
    )
    controlled = CONTROLS[command_element]
    return {
        command_element: "旺",
        generated: "相",
        generator: "休",
        controller: "囚",
        controlled: "死",
    }


HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}
SEASONAL_PROFILE = {
    "寅": ("初春", "木气初升", "余寒转暖", "偏湿"),
    "卯": ("仲春", "木气当令", "温", "偏湿"),
    "辰": ("季春", "土承木余气", "温", "湿"),
    "巳": ("初夏", "火气初旺", "偏热", "偏燥"),
    "午": ("仲夏", "火气当令", "炎热", "偏燥"),
    "未": ("季夏", "土承火余气", "暑热", "偏燥"),
    "申": ("初秋", "金气初旺", "由热转凉", "偏燥"),
    "酉": ("仲秋", "金气当令", "凉", "燥"),
    "戌": ("季秋", "土承金余气", "凉", "燥"),
    "亥": ("初冬", "水气初旺", "寒", "偏湿"),
    "子": ("仲冬", "水气当令", "严寒", "偏湿"),
    "丑": ("季冬", "土承水余气", "寒", "湿"),
}
JIEQI_NAMES = calendar_core.JIEQI_NAMES
MONTH_BOUNDARY_JIE = calendar_core.MONTH_BOUNDARY_JIE
def _jiazi() -> list[str]:
    return [STEMS[index % 10] + BRANCHES[index % 12] for index in range(60)]


JIAZI = _jiazi()
VALID_JIAZI = set(JIAZI)


NAYIN_NAMES = (
    "海中金", "炉中火", "大林木", "路旁土", "剑锋金", "山头火",
    "涧下水", "城头土", "白蜡金", "杨柳木", "泉中水", "屋上土",
    "霹雳火", "松柏木", "长流水", "沙中金", "山下火", "平地木",
    "壁上土", "金箔金", "覆灯火", "天河水", "大驿土", "钗钏金",
    "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水",
)
NAYIN = {JIAZI[index]: NAYIN_NAMES[index // 2] for index in range(60)}

# The user-owned 1.3.2 chart engine exposes the same Di Shi calculation.
# Keep it as a reproducible chart fact; it is not a standalone 旺衰、格局 or
# 用神 verdict.
GROWTH_STAGES = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养")
GROWTH_STAGE_START = {
    "甲": 11,
    "丙": 2,
    "戊": 2,
    "庚": 5,
    "壬": 8,
    "乙": 6,
    "丁": 9,
    "己": 9,
    "辛": 0,
    "癸": 3,
}

# The recovered 1.3.2 engine's getTaiYuan/getMingGong/getShenGong methods
# use the lunar month branch sequence 寅→丑 and the year-stem/month-branch/
# hour-branch indexes below.  Keep this as a position fact only; it is not a
# 格局、旺衰 or event judgment.
MONTH_BRANCHES = "寅卯辰巳午未申酉戌亥子丑"
SAN_YUAN_SOURCE_DEPENDENCY = "bazi.chart.san-yuan-lunar-typescript-v1"

PAIR_RELATIONS = {
    "六合": ("子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"),
    "六冲": ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"),
    "六害": ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌"),
    "六破": ("子酉", "丑辰", "寅亥", "卯午", "巳申", "未戌"),
}
TRIPLE_RELATIONS = {
    "三合": ("申子辰", "亥卯未", "寅午戌", "巳酉丑"),
    "三会": ("寅卯辰", "巳午未", "申酉戌", "亥子丑"),
    "三刑": ("寅巳申", "丑戌未"),
}
STEM_TRANSFORMATIONS = {
    frozenset(("甲", "己")): "土",
    frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水",
    frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}
YIMA_BY_ANCHOR = {
    **{branch: "申" for branch in "寅午戌"},
    **{branch: "寅" for branch in "申子辰"},
    **{branch: "亥" for branch in "巳酉丑"},
    **{branch: "巳" for branch in "亥卯未"},
}
TAOHUA_BY_ANCHOR = {
    **{branch: "卯" for branch in "寅午戌"},
    **{branch: "酉" for branch in "申子辰"},
    **{branch: "午" for branch in "巳酉丑"},
    **{branch: "子" for branch in "亥卯未"},
}


def _utc_now() -> str:
    return datetime.now(tz=ZoneInfo("UTC")).isoformat(timespec="seconds")


def _normalize_gender(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"male", "m", "man", "男", "乾"}:
        return "male"
    if normalized in {"female", "f", "woman", "女", "坤"}:
        return "female"
    raise ValueError(f"unsupported gender convention: {value!r}; use male/female or 男/女")


def _validate_pillars(values: list[str]) -> dict[str, str]:
    if len(values) == 1:
        values = [item for item in re.split(r"[\s、，,;/|]+", values[0].strip()) if item]
    if len(values) != 4:
        raise ValueError("exactly four pillars are required in year month day hour order")
    cleaned = [value.strip().replace("柱", "") for value in values]
    for value in cleaned:
        if value not in VALID_JIAZI:
            raise ValueError(f"invalid sexagenary pillar: {value!r}")
    return dict(zip(POSITIONS, cleaned))


def _ten_god(day_stem: str, target_stem: str) -> str:
    day_element = STEM_ELEMENT[day_stem]
    target_element = STEM_ELEMENT[target_stem]
    same_polarity = POLARITY[day_stem] == POLARITY[target_stem]
    day_index = ELEMENTS.index(day_element)
    target_index = ELEMENTS.index(target_element)

    if day_element == target_element:
        return "比肩" if same_polarity else "劫财"
    if target_index == (day_index + 1) % 5:
        return "食神" if same_polarity else "伤官"
    if target_index == (day_index + 2) % 5:
        return "偏财" if same_polarity else "正财"
    if day_index == (target_index + 1) % 5:
        return "偏印" if same_polarity else "正印"
    if day_index == (target_index + 2) % 5:
        return "七杀" if same_polarity else "正官"
    raise AssertionError("unreachable five-element relation")


def _twelve_growth_stages(pillars: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    """Calculate each visible stem's 十二长生 position on its own branch."""

    result: dict[str, dict[str, Any]] = {}
    for position in POSITIONS:
        pillar = pillars[position]
        stem, branch = pillar
        start = GROWTH_STAGE_START[stem]
        branch_index = BRANCHES.index(branch)
        yang = POLARITY[stem] == "阳"
        stage_index = (
            (branch_index - start) % 12
            if yang
            else (start - branch_index) % 12
        )
        result[position] = {
            "position": position,
            "stem": stem,
            "branch": branch,
            "stage": GROWTH_STAGES[stage_index],
            "stage_index": stage_index + 1,
            "direction": "forward" if yang else "reverse",
            "source_dependency_id": "bazi.chart.twelve-growth-stages-v1",
            "boundary": "十二长生位置事实；不能单独推出旺衰、格局、用神或事件结论",
        }
    return result


def _xunkong(day_pillar: str) -> dict[str, Any]:
    """Calculate the two void branches from the day pillar's ten-day xun."""

    day_index = JIAZI.index(day_pillar)
    xun_start = JIAZI[(day_index // 10) * 10]
    start_branch_index = BRANCHES.index(xun_start[1])
    branches = [
        BRANCHES[(start_branch_index + offset) % len(BRANCHES)]
        for offset in (10, 11)
    ]
    return {
        "day_pillar": day_pillar,
        "xun": xun_start,
        "branches": branches,
        "source_dependency_id": "bazi.chart.xunkong-sexagenary-v1",
        "boundary": "按日柱所属旬计算旬空事实；不能单独推出吉凶、六亲或事件结论",
    }


def _san_yuan(pillars: Mapping[str, str]) -> dict[str, Any]:
    """Derive 胎元、命宫、身宫 from the recovered chart-engine formula."""

    year_stem, month_stem = pillars["year"][0], pillars["month"][0]
    month_branch, hour_branch = pillars["month"][1], pillars["hour"][1]
    month_index = MONTH_BRANCHES.index(month_branch) + 1
    hour_index = MONTH_BRANCHES.index(hour_branch) + 1

    ming_offset = month_index + hour_index
    ming_offset = (26 if ming_offset >= 14 else 14) - ming_offset
    shen_offset = month_index + hour_index
    if shen_offset > 12:
        shen_offset -= 12

    year_stem_index = STEMS.index(year_stem)

    def palace_stem(offset: int) -> str:
        gan_index = (year_stem_index + 1) * 2 + offset
        while gan_index > 10:
            gan_index -= 10
        return STEMS[gan_index - 1]

    result = {
        "tai_yuan": (
            STEMS[(STEMS.index(month_stem) + 1) % 10]
            + BRANCHES[(BRANCHES.index(month_branch) + 3) % 12]
        ),
        "ming_gong": palace_stem(ming_offset) + MONTH_BRANCHES[ming_offset - 1],
        "shen_gong": palace_stem(shen_offset) + MONTH_BRANCHES[shen_offset - 1],
        "source": "lunar-typescript-auxiliary",
        "source_dependency_id": SAN_YUAN_SOURCE_DEPENDENCY,
        "boundary": "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
    }
    return result


def _branch_relations(pillars: dict[str, str]) -> list[dict[str, Any]]:
    branches = {position: pillar[1] for position, pillar in pillars.items()}
    relations: list[dict[str, Any]] = []
    items = list(branches.items())
    for left_index, (left_position, left_branch) in enumerate(items):
        for right_position, right_branch in items[left_index + 1 :]:
            pair = {left_branch, right_branch}
            for label, patterns in PAIR_RELATIONS.items():
                if any(pair == set(pattern) for pattern in patterns):
                    relations.append({
                        "type": label,
                        "positions": [left_position, right_position],
                        "branches": [left_branch, right_branch],
                    })
            if left_branch == right_branch and left_branch in "辰午酉亥":
                relations.append({
                    "type": "自刑",
                    "positions": [left_position, right_position],
                    "branches": [left_branch, right_branch],
                })

    available = Counter(branches.values())
    for label, patterns in TRIPLE_RELATIONS.items():
        for pattern in patterns:
            needed = Counter(pattern)
            if all(available[branch] >= count for branch, count in needed.items()):
                relations.append({"type": label, "branches": list(pattern)})
    return relations


def _salience_signals(
    pillars: dict[str, str],
    output: dict[str, Any],
    *,
    main_qi: str,
    main_qi_role: str,
    visible_main_qi: list[str],
    transformations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deterministic provider-owned salience candidates from computed facts.

    Ordering is a fixed provider-internal rule: repeated stems then repeated
    branches in canonical table order, branch relations in calculation order,
    the seasonal anchor, month-command transparency, and stem-combination
    candidates.  Signals carry mechanical bases only — no scoring, no model
    call, and never a verdict.  Families without facts emit nothing.
    """

    boundary = (
        "a mechanical candidate highlights structure only; it cannot justify"
        " a final conclusion on its own"
    )

    def signal(signal_id: str, basis: dict[str, Any]) -> dict[str, Any]:
        return {
            "signal_id": signal_id,
            "status": "mechanical_candidate",
            "basis": basis,
            "hard_verdict": None,
            "boundary": boundary,
        }

    signals: list[dict[str, Any]] = []
    stem_positions: dict[str, list[str]] = {}
    branch_positions: dict[str, list[str]] = {}
    for position in POSITIONS:
        stem, branch = pillars[position]
        stem_positions.setdefault(stem, []).append(position)
        branch_positions.setdefault(branch, []).append(position)
    for stem in sorted(
        (item for item, found in stem_positions.items() if len(found) >= 2),
        key=STEMS.index,
    ):
        signals.append(signal(
            f"bazi.salience.repeated-stem:{stem}",
            {
                "stem": stem,
                "element": STEM_ELEMENT[stem],
                "count": len(stem_positions[stem]),
                "positions": stem_positions[stem],
            },
        ))
    for branch in sorted(
        (item for item, found in branch_positions.items() if len(found) >= 2),
        key=BRANCHES.index,
    ):
        signals.append(signal(
            f"bazi.salience.repeated-branch:{branch}",
            {
                "branch": branch,
                "element": BRANCH_ELEMENT[branch],
                "count": len(branch_positions[branch]),
                "positions": branch_positions[branch],
            },
        ))
    for relation in output["branch_relations"]:
        positions = relation.get("positions")
        suffix = (
            "-".join(positions)
            if positions
            else "".join(relation["branches"])
        )
        signals.append(signal(
            f"bazi.salience.branch-relation:{relation['type']}:{suffix}",
            dict(relation),
        ))
    month_command = output["month_command"]
    seasonal = output["seasonal_profile"]
    day_master = output["day_master"]
    signals.append(signal(
        f"bazi.salience.seasonal-anchor:{month_command['branch']}",
        {
            "day_stem": day_master["stem"],
            "day_element": day_master["element"],
            "month_branch": month_command["branch"],
            "main_qi": month_command["main_qi"],
            "main_qi_element": month_command["main_qi_element"],
            "main_qi_ten_god": main_qi_role,
            "season": seasonal["season"],
            "month_qi": seasonal["month_qi"],
        },
    ))
    if visible_main_qi:
        signals.append(signal(
            f"bazi.salience.month-qi-transparent:{main_qi}",
            {
                "main_qi": main_qi,
                "main_qi_ten_god": main_qi_role,
                "visible_positions": visible_main_qi,
            },
        ))
    for candidate in transformations:
        stems = "".join(candidate["stems"])
        signals.append(signal(
            f"bazi.salience.stem-combination:{stems}:{candidate['with_position']}",
            dict(candidate),
        ))
    return signals


def _verified_runtime_binding(source: Any) -> dict[str, Any] | None:
    """Return an exact verified sibling binding, never copied pack metadata."""

    required_keys = {
        "pack",
        "rule_id",
        "source_anchor",
        "verification_status",
        "binding_digest",
    }
    if (
        not isinstance(source, dict)
        or set(source) != required_keys
        or source.get("verification_status") != "verified"
        or not all(
            isinstance(source.get(key), str) and bool(source[key].strip())
            for key in required_keys
        )
    ):
        return None
    return dict(source)


def _source_status_aware_conflict_arbitration(
    reasoning_tools: dict[str, dict[str, Any]],
    *,
    question_contract: dict[str, Any],
) -> dict[str, Any]:
    """Replace the legacy BZ-05 scaffold with a source-gated refusal.

    The three sibling tools may publish independently verified layer facts, but
    no verified Runtime rule currently orders those layers.  The arbitration
    therefore mirrors the sibling outputs and bindings while refusing every
    primary-view, downgrade, or hard-verdict choice.
    """

    scaffold = reasoning_tools["conflict_arbitration"]
    pattern = reasoning_tools["ziping_month_pattern_adjudication"]
    strength = reasoning_tools["strength_evidence"]
    tiaohou = reasoning_tools["tiaohou_candidates"]
    pattern_output = pattern["output"]
    strength_output = strength["output"]
    tiaohou_output = tiaohou["output"]

    pattern_sources = pattern.get("source_refs")
    tiaohou_sources = tiaohou.get("source_refs")
    strength_adjudication = strength_output.get(
        "day_master_root_support_adjudication"
    )
    candidate_bindings = [
        pattern_sources[0]
        if isinstance(pattern_sources, list) and len(pattern_sources) == 1
        else None,
        strength_adjudication.get("source_ref")
        if isinstance(strength_adjudication, dict)
        else None,
        tiaohou_sources[0]
        if isinstance(tiaohou_sources, list) and len(tiaohou_sources) == 1
        else None,
    ]
    active_source_refs = [
        binding
        for source in candidate_bindings
        if (binding := _verified_runtime_binding(source)) is not None
    ]
    requested_domains = list(dict.fromkeys(
        normalized
        for value in question_contract.get("domains") or ()
        if (normalized := str(value).strip().lower())
    ))
    unresolved_checks = [
        "verified cross-layer priority rule is unavailable",
        *(
            f"{domain} cannot uniquely map to a lineage focus"
            for domain in requested_domains
        ),
    ]
    if not requested_domains:
        unresolved_checks.append(
            "question domain is absent and cannot uniquely map to a lineage focus"
        )
    layers = {
        "pattern_layer": pattern_output,
        "strength_flow_layer": strength_output,
        "tiaohou_layer": tiaohou_output,
    }
    payload = {
        "schema_version": scaffold["schema_version"],
        "tool_id": "bazi.tool.conflict_arbitration",
        "tool_kind": "decision_stack_conflict_policy",
        "confidence_bucket": "low",
        "confidence_ceiling": "low",
        "visibility_class": "on_demand",
        "fact_refs": [
            {
                "path": (
                    "$.output.interpretive_candidates.reasoning_tools."
                    "ziping_month_pattern_adjudication"
                ),
                "value": {
                    "tool_digest": pattern["tool_digest"],
                    "output": pattern_output,
                },
            },
            {
                "path": (
                    "$.output.interpretive_candidates.reasoning_tools."
                    "strength_evidence"
                ),
                "value": {
                    "tool_digest": strength["tool_digest"],
                    "output": strength_output,
                },
            },
            {
                "path": (
                    "$.output.interpretive_candidates.reasoning_tools."
                    "tiaohou_candidates"
                ),
                "value": {
                    "tool_digest": tiaohou["tool_digest"],
                    "output": tiaohou_output,
                },
            },
        ],
        "source_refs": active_source_refs,
        "output": {
            "policy_id": "bazi.question-focus-routing-v1",
            "policy_anchor": (
                "references/matrices/bazi-core-decision-stack.md#3-冲突裁判"
            ),
            "policy_status": "product_contract_not_classical_verdict",
            "status": "unresolved_unverified_cross_layer_arbitrator",
            "requested_domains": requested_domains,
            "focus": None,
            "selected_primary_view": None,
            "preserved_disagreements": [
                {
                    "between": ["pattern_layer", "strength_flow_layer"],
                    "policy": "preserve_both_views",
                },
                {
                    "between": ["tiaohou_layer", "strength_flow_layer"],
                    "policy": "preserve_both_views",
                },
            ],
            "downgraded_layers": [],
            "layers": layers,
            "unresolved_required_rule": {
                "pack": "bazi/ditiansui-chanwei",
                "rule_id": "DR-02-06",
                "source_anchor": (
                    "references/books/bazi/ditiansui-chanwei/"
                    "rules.md#DR-02-06"
                ),
                "verification_status": "pending_verification",
            },
            "unresolved_checks": unresolved_checks,
            "hard_verdict": None,
        },
        "caveats": [
            "verified sibling bindings support only their own layer snapshots",
            "the cross-layer priority rule remains pending verification",
            "no question domain may silently select or downgrade a Bazi lineage",
        ],
    }
    payload["tool_digest"] = canonical_digest(payload)
    return payload


def _interpretive_candidates(
    pillars: dict[str, str],
    output: dict[str, Any],
    *,
    question_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose mechanical evidence while leaving disputed verdicts to adjudication."""

    # The source-aware reasoning tools already power the bounded near-time
    # adapter.  Keep the same deterministic evidence synthesis attached to the
    # natal chart as well, so the main Bazi Provider does not silently drop a
    # calculated rule layer.  These tools deliberately stop at an evidence
    # lean/candidate and never manufacture a hard verdict.
    from bazi_reasoning_tools import compile_bazi_reasoning_tools

    day_stem = pillars["day"][0]
    day_element = STEM_ELEMENT[day_stem]
    generating_element = ELEMENTS[(ELEMENTS.index(day_element) - 1) % 5]
    inventory = output["element_inventory"]
    visible = inventory["visible_stem_branch_counts"]
    hidden = inventory["hidden_stem_occurrence_counts"]
    element_occurrences = {
        element: int(visible.get(element, 0)) + int(hidden.get(element, 0))
        for element in ELEMENTS
    }
    main_qi = output["month_command"]["main_qi"]
    main_qi_role = _ten_god(day_stem, main_qi)
    visible_main_qi = [
        position
        for position, pillar in pillars.items()
        if position != "day" and pillar[0] == main_qi
    ]
    transformations = []
    for position, pillar in pillars.items():
        if position == "day":
            continue
        transformed_element = STEM_TRANSFORMATIONS.get(
            frozenset((day_stem, pillar[0]))
        )
        if transformed_element:
            transformations.append(
                {
                    "with_position": position,
                    "stems": [day_stem, pillar[0]],
                    "candidate_element": transformed_element,
                    "status": "combination_present_conditions_unadjudicated",
                }
            )
    contract = dict(question_contract or {})
    normalized_input = {
        "gender": contract.get("gender"),
    }
    reasoning_tools = compile_bazi_reasoning_tools(
        {"output": output, "input": {"normalized_input": normalized_input}},
        {"domains": list(contract.get("domains") or ())},
    )
    reasoning_tools["conflict_arbitration"] = (
        _source_status_aware_conflict_arbitration(
            reasoning_tools,
            question_contract=contract,
        )
    )
    strength_output = reasoning_tools["strength_evidence"]["output"]
    month_order_adjudication = strength_output["month_order_adjudication"]
    root_support_adjudication = strength_output[
        "day_master_root_support_adjudication"
    ]
    return {
        "strength": {
            "status": "evidence_only",
            "hard_verdict": None,
            "day_element": day_element,
            "month_command_element": output["month_command"]["main_qi_element"],
            "seasonal_state": _seasonal_states(
                output["month_command"]["main_qi_element"]
            )[day_element],
            "seasonal_state_source_rule_id": "bazi/sanming-tonghui#R-02-04",
            "same_element_occurrences": element_occurrences[day_element],
            "resource_element": generating_element,
            "resource_occurrences": element_occurrences[generating_element],
            "all_element_occurrences": element_occurrences,
            "month_order_adjudication": month_order_adjudication,
            "day_master_root_support_adjudication": root_support_adjudication,
            "boundary": "counts and season are inputs, not a strong/weak verdict",
        },
        "structure": {
            "status": "candidate_only",
            "hard_verdict": None,
            "month_main_qi": main_qi,
            "month_main_qi_ten_god": main_qi_role,
            "main_qi_visible": bool(visible_main_qi),
            "visible_positions": visible_main_qi,
            "boundary": "month command opens a candidate; success, failure, and rescue require classical adjudication",
        },
        "following_and_transformation": {
            "status": "requires_classical_adjudication",
            "hard_verdict": None,
            "stem_combination_candidates": transformations,
            "branch_formation_candidates": [
                relation
                for relation in output["branch_relations"]
                if relation.get("type") in {"三合", "三会"}
            ],
            "boundary": "a combination or one-sided inventory does not prove following or transformation",
        },
        "salience_signals": _salience_signals(
            pillars,
            output,
            main_qi=main_qi,
            main_qi_role=main_qi_role,
            visible_main_qi=visible_main_qi,
            transformations=transformations,
        ),
        "reasoning_tools": reasoning_tools,
    }


def _shensha_auxiliary_policy(
    pillars: dict[str, str] | None = None,
    *,
    transit_pillar: str | None = None,
) -> dict[str, Any]:
    observed = {
        position: pillar[1]
        for position, pillar in (pillars or {}).items()
    }
    if transit_pillar:
        observed["transit"] = transit_pillar[1]
    matches: dict[tuple[str, str], dict[str, Any]] = {}
    evaluated_rules: list[dict[str, Any]] = []
    for anchor_position in ("year", "day"):
        anchor_pillar = (pillars or {}).get(anchor_position)
        if not anchor_pillar:
            continue
        anchor_branch = anchor_pillar[1]
        for item_id, name, table in (
            ("yima", "驿马", YIMA_BY_ANCHOR),
            ("taohua", "桃花", TAOHUA_BY_ANCHOR),
        ):
            target = table[anchor_branch]
            matched_positions = [
                position
                for position, branch in observed.items()
                if branch == target
            ]
            evaluated_rules.append(
                {
                    "id": item_id,
                    "name": name,
                    "anchor_position": anchor_position,
                    "anchor_branch": anchor_branch,
                    "target_branch": target,
                    "matched": bool(matched_positions),
                }
            )
            if not matched_positions:
                continue
            key = (item_id, target)
            item = matches.setdefault(
                key,
                {
                    "id": item_id,
                    "name": name,
                    "target_branch": target,
                    "anchor_positions": [],
                    "anchor_branches": [],
                    "matched_positions": matched_positions,
                    "source_dependency_id": "bazi.shensha.yima-taohua-auxiliary",
                    "rule_version": "sanming-year-day-branch-yima-taohua-v1",
                    "status": "auxiliary_match",
                },
            )
            item["anchor_positions"].append(anchor_position)
            item["anchor_branches"].append(anchor_branch)
    return {
        "status": "calculated_auxiliary_layer",
        "temporal_scope": (
            "natal_plus_requested_transit" if transit_pillar else "natal"
        ),
        "precedence": "auxiliary_only",
        "may_override": [],
        "cannot_override": [
            "month_command",
            "structure",
            "strength",
            "tiaohou",
            "ten_gods",
            "luck_cycles",
            "transit_facts",
        ],
        "evaluated_rules": evaluated_rules,
        "calculated_items": list(matches.values()),
        "source_dependency_id": "bazi.shensha.yima-taohua-auxiliary",
        "boundary": "no Shensha item may override month command, structure, strength, Tiaohou, Ten Gods, or luck/transit facts",
    }


def _derive_static(
    pillars: dict[str, str],
    *,
    question_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    day_stem = pillars["day"][0]
    hidden: dict[str, Any] = {}
    hidden_gods: dict[str, Any] = {}
    stem_gods: dict[str, Any] = {}
    visible_elements: Counter[str] = Counter()
    hidden_elements: Counter[str] = Counter()

    for position, pillar in pillars.items():
        stem, branch = pillar
        visible_elements.update((STEM_ELEMENT[stem], BRANCH_ELEMENT[branch]))
        stems = HIDDEN_STEMS[branch]
        hidden[position] = {"branch": branch, "stems": stems}
        hidden_gods[position] = [
            {"stem": hidden_stem, "ten_god": _ten_god(day_stem, hidden_stem)}
            for hidden_stem in stems
        ]
        hidden_elements.update(STEM_ELEMENT[item] for item in stems)
        stem_gods[position] = {
            "stem": stem,
            "ten_god": "日主" if position == "day" else _ten_god(day_stem, stem),
        }

    month_branch = pillars["month"][1]
    season, qi, temperature, moisture = SEASONAL_PROFILE[month_branch]
    output = {
        "four_pillars": pillars,
        "day_master": {
            "stem": day_stem,
            "element": STEM_ELEMENT[day_stem],
            "polarity": POLARITY[day_stem],
        },
        "hidden_stems": hidden,
        "ten_gods": {"heavenly_stems": stem_gods, "hidden_stems": hidden_gods},
        "nayin": {position: NAYIN[pillar] for position, pillar in pillars.items()},
        "twelve_growth_stages": _twelve_growth_stages(pillars),
        "xunkong": _xunkong(pillars["day"]),
        "san_yuan": _san_yuan(pillars),
        "month_command": {
            "branch": month_branch,
            "label": f"{month_branch}月",
            "main_qi": HIDDEN_STEMS[month_branch][0],
            "main_qi_element": STEM_ELEMENT[HIDDEN_STEMS[month_branch][0]],
        },
        "seasonal_profile": {
            "season": season,
            "month_qi": qi,
            "temperature": temperature,
            "moisture": moisture,
        },
        "tiaohou_markers": {
            "temperature": temperature,
            "moisture": moisture,
            "markers": [temperature, moisture],
            "applicability_identity": {
                "day_stem": day_stem,
                "month_branch": month_branch,
                "source_dependency_id": (
                    "bazi.seasonal-tiaohou.day-master-month"
                ),
            },
            "scope": "month-level climate anchors only; not a 调候用神 conclusion",
        },
        "element_inventory": {
            "visible_stem_branch_counts": dict(visible_elements),
            "hidden_stem_occurrence_counts": dict(hidden_elements),
            "scope": "inventory only; these counts do not determine 旺衰 or 用神",
        },
        "branch_relations": _branch_relations(pillars),
    }
    output["interpretive_candidates"] = _interpretive_candidates(
        pillars,
        output,
        question_contract=question_contract,
    )
    output["shensha_auxiliary"] = _shensha_auxiliary_policy(pillars)
    output["source_conditioned_patterns"] = _source_conditioned_patterns(output)
    return output


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build stable fact paths consumed by the source-evidence matcher."""

    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=str):
            token = _escape_fact_token(str(key))
            yield from _fact_leaves(value[key], f"{path}/{token}")
        return
    if isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            yield from _fact_leaves(item, f"{path}/{index}")
        return
    yield path or "/", value


def _source_conditioned_patterns(
    output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose matched Bazi source predicates without creating a verdict."""

    indexed = {"chart_facts": {"output": dict(output)}}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.bazi.v7",
            provider_version=VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "bazi":
            continue
        matched, fact_ids, predicate_audit = evidence_rules.match_rule(
            rule, fact_refs
        )
        if not matched:
            continue
        matches.append(
            {
                "rule_id": rule.rule_id,
                "local_rule_id": rule.local_rule_id,
                "title": rule.title,
                "source_pack": rule.source_pack,
                "source_anchor": rule.source_anchor,
                "status": "predicate_matched_not_verdict",
                "fact_paths": list(fact_ids),
                "predicate_audit": list(predicate_audit),
                "source_dependency_id": "bazi.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def natal_fact_digest(snapshot: dict[str, Any]) -> str:
    """Digest immutable natal facts without wall-clock adapter metadata."""

    calendar = snapshot.get("calendar_normalization") or {}
    identity = {
        "schema_version": snapshot.get("schema_version"),
        "fact_layer_status": snapshot.get("fact_layer_status"),
        "fact_layer_scope": snapshot.get("fact_layer_scope"),
        "adapter": {
            key: value
            for key, value in (snapshot.get("adapter") or {}).items()
            if key != "generated_at"
        },
        "normalized_input": (snapshot.get("input") or {}).get("normalized_input"),
        "calendar_digest": calendar.get("calendar_digest") or calendar.get("digest"),
        "output": snapshot.get("output"),
    }
    return hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _base_adapter(rule_profile: str, license_status: str) -> dict[str, Any]:
    return {
        "name": ADAPTER_NAME,
        "version": VERSION,
        "license_status": license_status,
        "rule_profile": rule_profile,
        "generated_at": _utc_now(),
    }


def _build_from_pillars_payload(
    values: list[str],
    *,
    gender: str | None,
    source: str,
    source_ref: str | None,
    question_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = {
        "user_text": "text",
        "screenshot": "image",
    }.get(source, source)
    if source not in {"image", "text", "user_chart"}:
        raise ValueError(f"unsupported supplied-pillar source: {source}")
    pillars = _validate_pillars(values)
    normalized_gender = _normalize_gender(gender)
    output = _derive_static(pillars, question_contract=question_contract)
    output["luck_cycles"] = _partial_luck_cycles(pillars, normalized_gender)
    allowed_capabilities = ["static_natal_interpretation"]
    sequence_available = output["luck_cycles"]["status"] == "sequence_only"
    if sequence_available:
        allowed_capabilities.append("luck_cycle_sequence")
    luck_warning = (
        "Only the luck-cycle direction and pillar sequence follow from the supplied pillars and gender. Do not infer 起运岁数、对应公历年份、当前大运、流年或具体应期 from this payload."
        if sequence_available
        else "Do not infer 大运、流年、具体年份或起运年龄 from this payload."
    )
    return {
        "schema_version": "mingli-bazi-fact-v1",
        "fact_layer_status": "validated_user_provided_four_pillars",
        "fact_layer_scope": "natal_static",
        "adapter": _base_adapter(
            "supplied-four-pillars/static-ziping-v1",
            "user_provided",
        ),
        "input": {
            "mode": "supplied_four_pillars",
            "raw_user_input": {"pillars": values, "gender": gender},
            "normalized_input": {"pillars": pillars, "gender": normalized_gender},
            "source": source,
            "source_ref": source_ref,
            "timezone": None,
            "location": None,
            "missing_or_ambiguous": [
                "birth civil datetime",
                "birth timezone/location",
                "solar-term boundary verification",
                "true-solar-time policy",
            ],
        },
        "calendar_normalization": {
            "status": "unavailable_from_supplied_four_pillars",
            "civil_datetime": None,
            "location": None,
            "lunar_date": None,
            "ganzhi": pillars,
            "solar_terms": None,
            "true_solar_time": "not_available",
        },
        "output": output,
        "capabilities": {
            "allowed": allowed_capabilities,
            "blocked": [
                "birth_calendar_verification",
                "luck_cycle_timing",
                "annual_or_monthly_timing",
                "true_solar_time_verification",
            ],
        },
        "warnings": [
            "The four pillars were transcribed or supplied by the user; the original birth calendar was not independently recalculated.",
            "Vision/OCR is not evidence of calendar correctness. This adapter validates Jiazi and derives static relations only.",
            luck_warning,
        ],
        "trace": [
            "validated all four values against the 60 Jiazi",
            "derived hidden stems from a versioned standard table",
            "derived ten gods from day-master element and polarity",
            "derived Nayin, month command, seasonal anchors, and branch relations",
            "derived visible-stem twelve-growth-stage positions from the declared Di Shi table",
            "derived the partial luck-cycle scope determined by supplied pillars and gender",
        ],
        "conflicts": [],
    }


_load_sxtwl = calendar_core.load_sxtwl
_ganzhi = calendar_core.ganzhi
_surrounding_terms = calendar_core.surrounding_terms


LUCK_DIRECTION_RULE = "阳年男/阴年女顺，阴年男/阳年女逆；阴阳取年干"


def _luck_cycle_direction(pillars: dict[str, str], gender: str) -> bool:
    """Return True for forward luck under the single declared convention."""

    yang_year = POLARITY[pillars["year"][0]] == "阳"
    return (gender == "male" and yang_year) or (
        gender == "female" and not yang_year
    )


def _luck_cycle_pillar_sequence(
    pillars: dict[str, str],
    forward: bool,
) -> list[str]:
    """Return the ten-step pillar sequence shared by both input modes."""

    month_index = JIAZI.index(pillars["month"])
    direction = 1 if forward else -1
    return [
        JIAZI[(month_index + direction * sequence) % 60]
        for sequence in range(1, 11)
    ]


def _partial_luck_cycles(pillars: dict[str, str], gender: str | None) -> dict[str, Any]:
    """Derive only what supplied pillars determine: direction and sequence.

    Start ages, calendar-year mappings, the active cycle, and any precise
    timing require the birth instant and stay explicitly unavailable.
    """

    if gender is None:
        return {
            "status": "not_calculated_missing_gender",
            "cycles": [],
            "unavailable": [
                "direction",
                "sequence",
                "start_age",
                "calendar_year_mapping",
                "active_cycle",
                "precise_timing",
            ],
        }
    forward = _luck_cycle_direction(pillars, gender)
    return {
        "status": "sequence_only",
        "direction": "forward" if forward else "reverse",
        "direction_rule": LUCK_DIRECTION_RULE,
        "cycles": [
            {"sequence": sequence, "pillar": pillar}
            for sequence, pillar in enumerate(
                _luck_cycle_pillar_sequence(pillars, forward), start=1
            )
        ],
        "unavailable": [
            "start_age",
            "calendar_year_mapping",
            "active_cycle",
            "precise_timing",
        ],
    }


def _luck_cycles(
    pillars: dict[str, str],
    *,
    gender: str,
    birth: datetime,
    terms: list[dict[str, Any]],
) -> dict[str, Any]:
    forward = _luck_cycle_direction(pillars, gender)
    previous_jie, next_jie = _surrounding_terms(terms, birth, jie_only=True)
    boundary = next_jie if forward else previous_jie
    boundary_dt = datetime.fromisoformat(boundary["datetime"])
    interval_days = abs((boundary_dt - birth).total_seconds()) / 86400
    start_age = interval_days / 3
    start_at = birth + timedelta(days=start_age * 365.2425)
    sequence_pillars = _luck_cycle_pillar_sequence(pillars, forward)
    cycles = []
    for sequence, pillar in enumerate(sequence_pillars, start=1):
        cycle_start_age = start_age + (sequence - 1) * 10
        cycles.append({
            "sequence": sequence,
            "pillar": pillar,
            "start_age_years": round(cycle_start_age, 4),
            "end_age_years": round(cycle_start_age + 10, 4),
        })
    return {
        "status": "calculated",
        "direction": "forward" if forward else "reverse",
        "direction_rule": LUCK_DIRECTION_RULE,
        "start_age_rule": "距顺逆方向最近节令，三日折一年",
        "boundary_term": boundary,
        "interval_days": round(interval_days, 6),
        "start_age_years": round(start_age, 6),
        "approximate_start_datetime": start_at.isoformat(timespec="seconds"),
        "cycles": cycles,
    }


def _build_from_birth_payload(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    gender: str,
    expected_pillars: list[str] | None,
    zi_hour_policy: str,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    time_basis_policy: str = "civil",
    question_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    normalized_gender = _normalize_gender(gender)
    assert normalized_gender is not None
    calendar = calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        coordinate_accuracy_meters=coordinate_accuracy_meters,
        zi_hour_policy=zi_hour_policy,
        time_basis_policy=time_basis_policy,
    )
    birth = datetime.fromisoformat(calendar["civil_datetime"])
    pillars = dict(calendar["ganzhi"])
    _validate_pillars(list(pillars.values()))
    terms = calendar_core.solar_terms(birth)
    output = _derive_static(pillars, question_contract=question_contract)
    output["luck_cycles"] = _luck_cycles(
        pillars,
        gender=normalized_gender,
        birth=birth,
        terms=terms,
    )

    expected = _validate_pillars(expected_pillars) if expected_pillars else None
    conflicts = []
    if expected and expected != pillars:
        conflicts.append({
            "type": "birth_data_vs_supplied_pillars",
            "calculated": pillars,
            "supplied": expected,
            "action": "stop before interpretation and resolve birth data, timezone, calendar type, or chart transcription",
        })
    status = (
        "conflict_birth_data_vs_supplied_pillars"
        if conflicts
        else "calculated_natal_chart_from_birth_datetime"
    )
    warnings = [
        "Major-luck direction and start age use the declared rule profile; another school may use a different start-age convention.",
        "sxtwl Jieqi instants are converted from its UTC+8 build into the declared local timezone.",
    ]
    if time_basis_policy == "civil":
        warnings.append(
            "True solar time was not applied; hour-pillar accuracy near a two-hour boundary requires longitude and a separately versioned policy."
        )
        missing_or_ambiguous = (
            ["longitude/true-solar-time correction"]
            if longitude is None
            else ["equation-of-time apparent-solar correction not applied"]
        )
        blocked_capabilities = ["true_solar_time_verified_hour_pillar"]
    elif time_basis_policy == "longitude_mean_solar-v1":
        warnings.append(
            "Longitude mean-solar correction was applied explicitly; equation-of-time apparent-solar correction remains unapplied."
        )
        missing_or_ambiguous = ["equation-of-time apparent-solar correction not applied"]
        blocked_capabilities = ["true_solar_time_verified_hour_pillar"]
    else:  # local_apparent_solar-v1
        warnings.append(
            "Longitude and equation-of-time apparent-solar (true solar time) correction was applied."
        )
        missing_or_ambiguous = []
        blocked_capabilities = []
    if birth.hour == 23:
        warnings.append(f"Birth is in late Zi hour; applied zi_hour_policy={zi_hour_policy}.")
    payload = {
        "schema_version": "mingli-bazi-fact-v1",
        "fact_layer_status": status,
        "fact_layer_scope": "natal_timing",
        "adapter": _base_adapter(
            f"sxtwl-local-civil/jieqi-month/major-luck-3days-per-year/zi-hour-{zi_hour_policy}",
            "verified_local_dependency",
        ),
        "input": {
            "mode": "birth_datetime",
            "raw_user_input": {
                "civil_datetime": civil_datetime,
                "timezone": timezone_name,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
                "gender": gender,
                "expected_pillars": expected_pillars,
            },
            "normalized_input": {
                "civil_datetime": birth.isoformat(timespec="seconds"),
                "timezone": timezone_name,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source or "not_supplied",
                "gender": normalized_gender,
                "zi_hour_policy": zi_hour_policy,
                "time_basis_policy": time_basis_policy,
            },
            "timezone": timezone_name,
            "location": location,
            "missing_or_ambiguous": missing_or_ambiguous,
        },
        "calendar_normalization": calendar,
        "output": output,
        "capabilities": {
            "allowed": ["static_natal_interpretation", "luck_cycle_timing"],
            "blocked": blocked_capabilities,
        },
        "warnings": warnings,
        "trace": [
            "converted declared local civil birth date to lunar date with sxtwl",
            "calculated year/month/day/hour pillars with Jieqi month switching",
            "derived static hidden-stem, ten-god, Nayin, month-command, seasonal, and relation facts",
            "derived visible-stem twelve-growth-stage positions from the declared Di Shi table",
            "calculated major-luck direction and start age with the declared convention",
        ],
        "conflicts": conflicts,
    }
    return payload, bool(conflicts)


@dataclass(frozen=True)
class BaziBirthEngineRequest:
    """Owned normalized input for the Bazi chart-engine path."""

    civil_datetime: str
    timezone_name: str
    location: str
    gender: str
    expected_pillars: tuple[str, ...] | None = None
    zi_hour_policy: str = "midnight"
    longitude: float | None = None
    latitude: float | None = None
    coordinate_source: str | None = None
    coordinate_accuracy_meters: float | None = None
    time_basis_policy: str = "civil"
    question_contract: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class BaziPillarsEngineRequest:
    """Owned normalized input for the self-owned static-facts path."""

    pillars: tuple[str, ...]
    gender: str | None
    source: str
    source_ref: str | None
    question_contract: Mapping[str, Any] | None = None


BaziNormalizedEngineRequest: TypeAlias = (
    BaziBirthEngineRequest | BaziPillarsEngineRequest
)


@dataclass(frozen=True)
class _BaziPrivateEngineRequest:
    normalized: BaziNormalizedEngineRequest


@dataclass(frozen=True)
class _BaziPrivateEngineOutput:
    payload: dict[str, Any]


class BaziEngineAdapter(
    EngineAdapterBase[
        BaziNormalizedEngineRequest,
        _BaziPrivateEngineRequest,
        _BaziPrivateEngineOutput,
        BaziCanonicalFacts,
    ]
):
    """Wrap the pinned Bazi pipeline without exposing its private output."""

    art_id = "bazi"

    def _build_engine_request(
        self,
        request: BaziNormalizedEngineRequest,
    ) -> _BaziPrivateEngineRequest:
        if not isinstance(
            request,
            (BaziBirthEngineRequest, BaziPillarsEngineRequest),
        ):
            raise ValueError("unsupported Bazi normalized engine request")
        if isinstance(request, BaziPillarsEngineRequest):
            source = {
                "user_text": "text",
                "screenshot": "image",
            }.get(request.source, request.source)
            if source not in {"image", "text", "user_chart"}:
                raise ValueError(
                    f"unsupported supplied-pillar source: {source}"
                )
            _validate_pillars(list(request.pillars))
            _normalize_gender(request.gender)
        else:
            _normalize_gender(request.gender)
            if request.expected_pillars is not None:
                _validate_pillars(list(request.expected_pillars))
            self._validate_calendar_request(request)
        return _BaziPrivateEngineRequest(normalized=request)

    @staticmethod
    def _validate_calendar_request(request: BaziBirthEngineRequest) -> None:
        """Validate owned calendar policy without loading a chart engine."""

        if not str(request.location or "").strip():
            raise ValueError("location is required")
        if request.zi_hour_policy not in calendar_core.ZI_HOUR_POLICIES:
            raise ValueError(
                f"unsupported Zi-hour policy: {request.zi_hour_policy!r}"
            )
        if request.time_basis_policy not in calendar_core.TIME_BASIS_POLICIES:
            raise ValueError(
                f"unsupported time-basis policy: {request.time_basis_policy!r}"
            )
        longitude = calendar_core._number(
            request.longitude,
            label="longitude",
            minimum=-180.0,
            maximum=180.0,
        )
        latitude = calendar_core._number(
            request.latitude,
            label="latitude",
            minimum=-90.0,
            maximum=90.0,
        )
        if (longitude is None) != (latitude is None):
            raise ValueError("longitude and latitude must be supplied together")
        if longitude is not None and not str(
            request.coordinate_source or ""
        ).strip():
            raise ValueError(
                "coordinate_source is required with longitude/latitude"
            )
        if request.coordinate_accuracy_meters is not None:
            accuracy = float(request.coordinate_accuracy_meters)
            if not math.isfinite(accuracy) or accuracy < 0:
                raise ValueError(
                    "coordinate_accuracy_meters must be a finite,"
                    " non-negative number"
                )
        calendar_core._localize_civil(
            request.civil_datetime,
            request.timezone_name,
        )
        if (
            request.time_basis_policy
            in {"longitude_mean_solar-v1", "local_apparent_solar-v1"}
            and longitude is None
        ):
            raise ValueError(
                f"{request.time_basis_policy} requires measured coordinates"
            )

    def _invoke_engine(
        self,
        request: _BaziPrivateEngineRequest,
    ) -> _BaziPrivateEngineOutput:
        normalized = request.normalized
        if isinstance(normalized, BaziBirthEngineRequest):
            payload, _conflict = _build_from_birth_payload(
                normalized.civil_datetime,
                timezone_name=normalized.timezone_name,
                location=normalized.location,
                gender=normalized.gender,
                expected_pillars=(
                    list(normalized.expected_pillars)
                    if normalized.expected_pillars is not None
                    else None
                ),
                zi_hour_policy=normalized.zi_hour_policy,
                longitude=normalized.longitude,
                latitude=normalized.latitude,
                coordinate_source=normalized.coordinate_source,
                coordinate_accuracy_meters=normalized.coordinate_accuracy_meters,
                time_basis_policy=normalized.time_basis_policy,
                question_contract=(
                    dict(normalized.question_contract)
                    if normalized.question_contract is not None
                    else None
                ),
            )
        else:
            payload = _build_from_pillars_payload(
                list(normalized.pillars),
                gender=normalized.gender,
                source=normalized.source,
                source_ref=normalized.source_ref,
                question_contract=(
                    dict(normalized.question_contract)
                    if normalized.question_contract is not None
                    else None
                ),
            )
        return _BaziPrivateEngineOutput(payload=payload)

    def _project_engine_output(
        self,
        request: BaziNormalizedEngineRequest,
        output: _BaziPrivateEngineOutput,
        provenance: EngineProvenance,
    ) -> BaziCanonicalFacts:
        del request
        return BaziFactContract().bind_canonical_facts(
            output.payload,
            provenance,
        )

    def _provenance(
        self,
        request: BaziNormalizedEngineRequest,
    ) -> EngineProvenance:
        if isinstance(request, BaziBirthEngineRequest):
            return EngineProvenance(
                engine_id="sxtwl",
                engine_version=calendar_core.ENGINE_VERSION,
                policy_profile=(
                    "sxtwl-local-civil/jieqi-month/major-luck-3days-per-year/"
                    f"zi-hour-{request.zi_hour_policy}"
                ),
                time_basis=request.time_basis_policy,
            )
        return EngineProvenance(
            engine_id="mingli-bazi-static-facts",
            engine_version=VERSION,
            policy_profile="supplied-four-pillars/static-ziping-v1",
            time_basis="not_applicable",
        )


def build_from_pillars(
    values: list[str],
    *,
    gender: str | None,
    source: str,
    source_ref: str | None,
    question_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compatibility facade returning the unchanged Bazi fact JSON shape."""

    result = BaziEngineAdapter().adapt(
        BaziPillarsEngineRequest(
            pillars=tuple(values),
            gender=gender,
            source=source,
            source_ref=source_ref,
            question_contract=question_contract,
        )
    )
    return result.canonical_facts.to_payload()


def build_from_birth(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    gender: str,
    expected_pillars: list[str] | None,
    zi_hour_policy: str,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    time_basis_policy: str = "civil",
    question_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Compatibility facade returning the unchanged Bazi fact JSON shape."""

    result = BaziEngineAdapter().adapt(
        BaziBirthEngineRequest(
            civil_datetime=civil_datetime,
            timezone_name=timezone_name,
            location=location,
            gender=gender,
            expected_pillars=(
                tuple(expected_pillars) if expected_pillars is not None else None
            ),
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
            coordinate_accuracy_meters=coordinate_accuracy_meters,
            time_basis_policy=time_basis_policy,
            question_contract=question_contract,
        )
    )
    payload = result.canonical_facts.to_payload()
    return payload, bool(payload.get("conflicts"))


def _extension_year_ganzhi(year: int) -> str:
    """Return the post-Li-Chun year label from the pinned calendar engine."""

    return calendar_core.year_ganzhi_after_li_chun(year)


def _extension_branch_relations(
    branch: str,
    four_pillars: dict[str, str],
) -> list[dict[str, str]]:
    relations: list[dict[str, str]] = []
    # The retired JSON subprocess sorted object keys before the Provider read
    # them.  Keep that public relation order stable when Canonical Facts now
    # arrive directly from the in-process Engine Adapter.
    for position in sorted(four_pillars):
        pillar = four_pillars[position]
        natal_branch = pillar[1]
        pair = {branch, natal_branch}
        for label, patterns in PAIR_RELATIONS.items():
            if any(pair == set(pattern) for pattern in patterns):
                relations.append(
                    {
                        "type": label,
                        "natal_position": position,
                        "natal_branch": natal_branch,
                        "transit_branch": branch,
                    }
                )
        if branch == natal_branch and branch in "辰午酉亥":
            relations.append(
                {
                    "type": "自刑",
                    "natal_position": position,
                    "natal_branch": natal_branch,
                    "transit_branch": branch,
                }
            )
    return relations


def _extension_age_years(birth: datetime, point: datetime) -> float:
    return (point - birth).total_seconds() / (365.2425 * 24 * 60 * 60)


def _extension_active_luck_cycle_interval(
    start: datetime,
    end: datetime,
    chart_facts: dict[str, Any],
    *,
    transition_status: str,
) -> dict[str, Any]:
    birth = datetime.fromisoformat(
        str(chart_facts["calendar_normalization"]["civil_datetime"])
    )
    start = start.astimezone(birth.tzinfo)
    end = end.astimezone(birth.tzinfo)
    age_start = _extension_age_years(birth, start)
    age_end = _extension_age_years(birth, end)
    overlapping: list[dict[str, Any]] = []
    for cycle in chart_facts["output"]["luck_cycles"]["cycles"]:
        cycle_start = birth + timedelta(
            days=float(cycle["start_age_years"]) * 365.2425
        )
        cycle_end = birth + timedelta(
            days=float(cycle["end_age_years"]) * 365.2425
        )
        overlap_start = max(start, cycle_start)
        overlap_end = min(end, cycle_end)
        if overlap_start >= overlap_end:
            continue
        overlapping.append(
            {
                **cycle,
                "cycle_start_datetime": cycle_start.isoformat(
                    timespec="microseconds"
                ),
                "cycle_end_exclusive": cycle_end.isoformat(
                    timespec="microseconds"
                ),
                "overlap_start_inclusive": overlap_start.isoformat(
                    timespec="microseconds"
                ),
                "overlap_end_exclusive": overlap_end.isoformat(
                    timespec="microseconds"
                ),
                "stem_ten_god": _ten_god(
                    chart_facts["output"]["day_master"]["stem"],
                    cycle["pillar"][0],
                ),
                "branch_hidden_ten_gods": [
                    {
                        "stem": stem,
                        "ten_god": _ten_god(
                            chart_facts["output"]["day_master"]["stem"], stem
                        ),
                    }
                    for stem in HIDDEN_STEMS[cycle["pillar"][1]]
                ],
                "branch_relations": _extension_branch_relations(
                    cycle["pillar"][1],
                    chart_facts["output"]["four_pillars"],
                ),
            }
        )
    return {
        "status": (
            "single_cycle"
            if len(overlapping) == 1
            else transition_status
            if len(overlapping) > 1
            else "outside_calculated_cycles"
        ),
        "age_interval_years": {
            "start": round(age_start, 4),
            "end": round(age_end, 4),
        },
        "cycles": overlapping,
        "rule": "requested interval over the adapter's versioned decimal-age luck-cycle instants",
    }


def _extension_active_luck_cycle(
    year: int,
    chart_facts: dict[str, Any],
) -> dict[str, Any]:
    birth = datetime.fromisoformat(
        str(chart_facts["calendar_normalization"]["civil_datetime"])
    )
    return _extension_active_luck_cycle_interval(
        datetime(year, 1, 1, tzinfo=birth.tzinfo),
        datetime(year + 1, 1, 1, tzinfo=birth.tzinfo),
        chart_facts,
        transition_status="transition_year",
    )


def _li_chun_boundary(year: int, timezone_name: str) -> str:
    return calendar_core.li_chun_boundary(year, timezone_name).isoformat(
        timespec="microseconds"
    )


def _extension_transit_facts(
    ganzhi: str,
    *,
    day_stem: str,
    pillars: dict[str, str],
    seasonal_branch: str | None,
) -> dict[str, Any]:
    stem, branch = ganzhi
    branch_relations = _extension_branch_relations(branch, pillars)
    natal_profile = SEASONAL_PROFILE[pillars["month"][1]]
    transit_profile = (
        SEASONAL_PROFILE[seasonal_branch]
        if seasonal_branch is not None
        else None
    )
    if transit_profile is None:
        seasonal_effect = {
            "status": "not_inferred_from_non_month_pillar",
            "scope": "request an exact month or day layer for seasonal facts",
        }
        tiaohou_effect = {
            "status": "not_inferred_from_non_month_pillar",
            "day_stem": day_stem,
            "scope": "Tiaohou applicability requires the active month command",
        }
        seasonal_delta = {
            "status": "not_inferred_from_non_month_pillar",
            "natal_month_branch": pillars["month"][1],
            "favorability_status": "requires_classical_adjudication",
        }
    else:
        seasonal_effect = {
            "status": "calculated_from_active_month_command",
            "active_month_branch": seasonal_branch,
            "seasonal_profile": transit_profile,
        }
        tiaohou_effect = {
            "status": "applicability_identity_only",
            "day_stem": day_stem,
            "active_month_branch": seasonal_branch,
            "transit_stem": stem,
            "preferred_stem_candidates_status": (
                "deferred_to_current_evidence_adjudication"
            ),
            "source_dependency_id": "bazi.seasonal-tiaohou.day-master-month",
        }
        seasonal_delta = {
            "status": "calculated_climate_comparison",
            "natal_month_branch": pillars["month"][1],
            "active_month_branch": seasonal_branch,
            "temperature": {
                "natal": natal_profile[2],
                "transit": transit_profile[2],
                "changed": natal_profile[2] != transit_profile[2],
            },
            "moisture": {
                "natal": natal_profile[3],
                "transit": transit_profile[3],
                "changed": natal_profile[3] != transit_profile[3],
            },
            "favorability_status": "requires_classical_adjudication",
        }
    return {
        "ganzhi": ganzhi,
        "stem_ten_god": _ten_god(day_stem, stem),
        "branch_hidden_ten_gods": [
            {"stem": hidden, "ten_god": _ten_god(day_stem, hidden)}
            for hidden in HIDDEN_STEMS[branch]
        ],
        "branch_relations": branch_relations,
        "seasonal_effect": seasonal_effect,
        "tiaohou_effect": tiaohou_effect,
        "structural_changes": {
            "status": "mechanical_candidates_only",
            "transit_pillar": ganzhi,
            "stem_ten_god": _ten_god(day_stem, stem),
            "branch_relations": branch_relations,
            "hard_verdict": None,
        },
        "seasonal_tiaohou_delta": seasonal_delta,
        "shensha_auxiliary": _shensha_auxiliary_policy(
            pillars,
            transit_pillar=ganzhi,
        ),
    }


def _annual_seasonal_tiaohou_cycle(
    year: int,
    *,
    timezone_name: str,
    day_stem: str,
    natal_month_branch: str,
) -> dict[str, Any]:
    timezone = ZoneInfo(timezone_name)
    year_start = datetime(year, 1, 1, tzinfo=timezone)
    year_end = datetime(year + 1, 1, 1, tzinfo=timezone)
    boundary_terms = sorted(
        (
            term
            for month in range(1, 13)
            for term in calendar_core.month_boundary_terms(
                year,
                month,
                timezone_name,
            )
        ),
        key=lambda item: item["datetime"],
    )
    points = [year_start] + [
        datetime.fromisoformat(item["datetime"])
        for item in boundary_terms
    ] + [year_end]
    natal_profile = SEASONAL_PROFILE[natal_month_branch]
    segments = []
    for start, end in zip(points, points[1:]):
        month_ganzhi = calendar_core.month_ganzhi_at(start)
        month_branch = month_ganzhi[1]
        profile = SEASONAL_PROFILE[month_branch]
        segments.append(
            {
                "start_inclusive": start.isoformat(timespec="microseconds"),
                "end_exclusive": end.isoformat(timespec="microseconds"),
                "month_ganzhi": month_ganzhi,
                "month_branch": month_branch,
                "seasonal_profile": profile,
                "tiaohou_applicability_identity": {
                    "day_stem": day_stem,
                    "month_branch": month_branch,
                    "source_dependency_id": (
                        "bazi.seasonal-tiaohou.day-master-month"
                    ),
                },
                "temperature_changed_from_natal": (
                    profile[2] != natal_profile[2]
                ),
                "moisture_changed_from_natal": profile[3] != natal_profile[3],
            }
        )
    return {
        "status": "calculated_exact_jie_segments",
        "natal_month_branch": natal_month_branch,
        "segments": segments,
        "favorability_status": "requires_classical_adjudication",
    }


def build_year_fact_extensions(
    chart_facts: dict[str, Any],
    *,
    start_year: int,
    end_year: int,
) -> dict[str, dict[str, Any]]:
    """Expand an exact inclusive civil-year range without making judgments."""

    if not 1800 <= start_year <= end_year <= 2199:
        raise ValueError("Bazi year horizon must be an inclusive 1800-2199 range")
    if chart_facts.get("fact_layer_status") != "calculated_natal_chart_from_birth_datetime":
        raise ValueError("Bazi year extension requires calculated birth timing facts")
    output = chart_facts["output"]
    if (output.get("luck_cycles") or {}).get("status") != "calculated":
        raise ValueError("Bazi year extension requires calculated luck cycles")
    timezone_fact = chart_facts["calendar_normalization"].get("timezone")
    timezone_name = str(
        timezone_fact.get("name")
        if isinstance(timezone_fact, dict)
        else timezone_fact
        or "Asia/Shanghai"
    )
    ZoneInfo(timezone_name)
    day_stem = output["day_master"]["stem"]
    pillars = output["four_pillars"]
    layers: dict[str, dict[str, Any]] = {}
    for year in range(start_year, end_year + 1):
        ganzhi = _extension_year_ganzhi(year)
        boundary = _li_chun_boundary(year, timezone_name)
        before_ganzhi = _extension_year_ganzhi(year - 1)
        after_facts = _extension_transit_facts(
            ganzhi,
            day_stem=day_stem,
            pillars=pillars,
            seasonal_branch=None,
        )
        segments = [
            {
                "start_inclusive": datetime(
                    year, 1, 1, tzinfo=ZoneInfo(timezone_name)
                ).isoformat(timespec="seconds"),
                "end_exclusive": boundary,
                **_extension_transit_facts(
                    before_ganzhi,
                    day_stem=day_stem,
                    pillars=pillars,
                    seasonal_branch=None,
                ),
            },
            {
                "start_inclusive": boundary,
                "end_exclusive": datetime(
                    year + 1, 1, 1, tzinfo=ZoneInfo(timezone_name)
                ).isoformat(timespec="seconds"),
                **after_facts,
            },
        ]
        annual_seasonal_cycle = _annual_seasonal_tiaohou_cycle(
            year,
            timezone_name=timezone_name,
            day_stem=day_stem,
            natal_month_branch=output["month_command"]["branch"],
        )
        layers[str(year)] = {
            "year": year,
            **after_facts,
            "ganzhi_segments": segments,
            "active_luck_cycle": _extension_active_luck_cycle(year, chart_facts),
            "seasonal_effect": {
                "status": "calculated_exact_jie_segments",
                "segments": annual_seasonal_cycle["segments"],
                "natal_month_command": output["month_command"]["branch"],
            },
            "tiaohou_effect": {
                "status": "applicability_identity_by_exact_jie_segment",
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        **item["tiaohou_applicability_identity"],
                    }
                    for item in annual_seasonal_cycle["segments"]
                ],
                "favorability_status": "requires_classical_adjudication",
            },
            "seasonal_tiaohou_delta": annual_seasonal_cycle,
            "calendar_normalization": {
                "timezone": timezone_name,
                "year_boundary": "立春",
                "boundary_datetime": boundary,
                "before_boundary_ganzhi": before_ganzhi,
                "after_boundary_ganzhi": ganzhi,
            },
            "rule_trace": [
                {
                    "rule_id": "bazi.sexagenary-year.sxtwl-jieqi-v1",
                    "source_dependency_id": "bazi.calendar.sxtwl-jieqi-four-pillars",
                    "operation": "pinned sxtwl year Ganzhi, split at the exact Li Chun instant",
                },
                {
                    "rule_id": "bazi.luck-cycle.overlap-v1",
                    "source_dependency_id": "bazi.luck.major-cycle-three-days-per-year",
                    "operation": "civil-year elapsed-age interval overlaps calculated luck cycles",
                },
                {
                    "rule_id": "bazi.transit-relations.standard-table-v1",
                    "source_dependency_id": "bazi.relations.ten-gods-hidden-stems-branch-relations",
                    "operation": "annual stem Ten God and annual branch relations",
                },
                {
                    "rule_id": "bazi.seasonal-tiaohou.day-master-month-v1",
                    "source_dependency_id": "bazi.seasonal-tiaohou.day-master-month",
                    "operation": "carry calculated seasonal and day-master/month Tiaohou markers without a verdict",
                },
            ],
        }
    return layers


def _parse_month_key(value: str) -> tuple[int, int]:
    try:
        year_text, month_text = value.split("-", 1)
        year, month = int(year_text), int(month_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Bazi month horizon must use YYYY-MM") from exc
    if not 1800 <= year <= 2199 or not 1 <= month <= 12:
        raise ValueError("Bazi month horizon must be within 1800-01..2199-12")
    return year, month


def _month_key_range(start: str, end: str) -> list[tuple[int, int]]:
    start_year, start_month = _parse_month_key(start)
    end_year, end_month = _parse_month_key(end)
    start_index = start_year * 12 + start_month - 1
    end_index = end_year * 12 + end_month - 1
    if start_index > end_index:
        raise ValueError("Bazi month horizon start must not follow end")
    if end_index - start_index > 599:
        raise ValueError("Bazi month horizon cannot exceed 600 months")
    return [divmod(index, 12) for index in range(start_index, end_index + 1)]


def _month_boundary_terms(
    *,
    year: int,
    month: int,
    timezone_name: str,
) -> list[dict[str, Any]]:
    return calendar_core.month_boundary_terms(year, month, timezone_name)


def build_month_fact_extensions(
    chart_facts: dict[str, Any],
    *,
    start_month: str,
    end_month: str,
) -> dict[str, dict[str, Any]]:
    """Expand civil months with exact Jie boundaries and calculated month pillars."""

    if chart_facts.get("fact_layer_status") != "calculated_natal_chart_from_birth_datetime":
        raise ValueError("Bazi month extension requires calculated birth timing facts")
    output = chart_facts["output"]
    if (output.get("luck_cycles") or {}).get("status") != "calculated":
        raise ValueError("Bazi month extension requires calculated luck cycles")
    timezone_fact = chart_facts["calendar_normalization"].get("timezone")
    timezone_name = str(
        timezone_fact.get("name") if isinstance(timezone_fact, dict) else timezone_fact or ""
    )
    timezone = ZoneInfo(timezone_name)
    day_stem = output["day_master"]["stem"]
    pillars = output["four_pillars"]
    layers: dict[str, dict[str, Any]] = {}
    for year, zero_based_month in _month_key_range(start_month, end_month):
        month = zero_based_month + 1
        boundary_terms = _month_boundary_terms(
            year=year,
            month=month,
            timezone_name=timezone_name,
        )
        month_start = datetime(year, month, 1, tzinfo=timezone)
        month_end = (
            datetime(year + 1, 1, 1, tzinfo=timezone)
            if month == 12
            else datetime(year, month + 1, 1, tzinfo=timezone)
        )
        points = [month_start] + [
            datetime.fromisoformat(item["datetime"]) for item in boundary_terms
        ] + [month_end]
        segments: list[dict[str, Any]] = []
        for index, (segment_start, segment_end) in enumerate(
            zip(points, points[1:])
        ):
            ganzhi = calendar_core.month_ganzhi_at(segment_start)
            segments.append(
                {
                    "start_inclusive": segment_start.isoformat(timespec="microseconds"),
                    "end_exclusive": segment_end.isoformat(timespec="microseconds"),
                    **_extension_transit_facts(
                        ganzhi,
                        day_stem=day_stem,
                        pillars=pillars,
                        seasonal_branch=ganzhi[1],
                    ),
                }
            )
        key = f"{year:04d}-{month:02d}"
        layers[key] = {
            "year": year,
            "month": month,
            "ganzhi_segments": segments,
            "structural_changes": {
                "status": "segmented_by_exact_jie_boundary",
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        "ganzhi": item["ganzhi"],
                        "facts": item["structural_changes"],
                    }
                    for item in segments
                ],
                "hard_verdict": None,
            },
            "seasonal_tiaohou_delta": {
                "status": "segmented_by_exact_jie_boundary",
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        "ganzhi": item["ganzhi"],
                        "facts": item["seasonal_tiaohou_delta"],
                    }
                    for item in segments
                ],
                "favorability_status": "requires_classical_adjudication",
            },
            "shensha_auxiliary": _shensha_auxiliary_policy(pillars),
            "active_luck_cycle": _extension_active_luck_cycle_interval(
                month_start,
                month_end,
                chart_facts,
                transition_status="transition_period",
            ),
            "calendar_normalization": {
                "timezone": timezone_name,
                "month_boundary": "节令",
                "boundary_terms": boundary_terms,
            },
            "rule_trace": [
                {
                    "rule_id": "bazi.sexagenary-month.sxtwl-jieqi-v1",
                    "source_dependency_id": "bazi.calendar.sxtwl-jieqi-four-pillars",
                    "operation": "pinned sxtwl month Ganzhi with exact Jie boundary instants",
                },
                {
                    "rule_id": "bazi.transit-relations.standard-table-v1",
                    "source_dependency_id": "bazi.relations.ten-gods-hidden-stems-branch-relations",
                    "operation": "month stem Ten God and month branch relations",
                },
                {
                    "rule_id": "bazi.seasonal-tiaohou.day-master-month-v1",
                    "source_dependency_id": "bazi.seasonal-tiaohou.day-master-month",
                    "operation": "carry calculated seasonal and day-master/month Tiaohou markers without a verdict",
                },
            ],
        }
    return layers


def _parse_day_key(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Bazi day horizon must use YYYY-MM-DD") from exc
    if not 1800 <= parsed.year <= 2199:
        raise ValueError("Bazi day horizon must be within 1800-01-01..2199-12-31")
    return parsed


def build_day_fact_extensions(
    chart_facts: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    target_time_basis_policy: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Expand an inclusive civil-day range with shared-calendar identities."""

    if chart_facts.get("fact_layer_status") != "calculated_natal_chart_from_birth_datetime":
        raise ValueError("Bazi day extension requires calculated birth timing facts")
    output = chart_facts["output"]
    if (output.get("luck_cycles") or {}).get("status") != "calculated":
        raise ValueError("Bazi day extension requires calculated luck cycles")
    start = _parse_day_key(start_date)
    end = _parse_day_key(end_date)
    if start > end:
        raise ValueError("Bazi day horizon start must not follow end")
    day_count = (end - start).days + 1
    if day_count > 3660:
        raise ValueError("Bazi day horizon cannot exceed 3660 days")

    calendar = chart_facts["calendar_normalization"]
    timezone_name = str(calendar.get("timezone") or "")
    timezone = ZoneInfo(timezone_name)
    location = calendar.get("location") or {}
    if isinstance(location, dict):
        location_name = str(location.get("name") or "")
        longitude = location.get("longitude")
        latitude = location.get("latitude")
        coordinate_source = location.get("coordinate_source")
        coordinate_accuracy_meters = location.get("coordinate_accuracy_meters")
        if coordinate_source == "not_supplied":
            coordinate_source = None
    else:
        location_name = str(location)
        longitude = None
        latitude = None
        coordinate_source = None
        coordinate_accuracy_meters = None
    convention = calendar.get("calendar_convention") or {}
    zi_hour_policy = str(convention.get("zi_hour_policy") or "midnight")
    inherited_time_basis_policy = str(
        (calendar.get("time_basis") or {}).get("policy") or "civil"
    )
    time_basis_policy = str(
        target_time_basis_policy or inherited_time_basis_policy
    )
    day_stem = output["day_master"]["stem"]
    pillars = output["four_pillars"]

    layers: dict[str, dict[str, Any]] = {}
    for offset in range(day_count):
        target_date = start + timedelta(days=offset)
        day_start = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            tzinfo=timezone,
        )
        day_end = day_start + timedelta(days=1)
        noon = day_start + timedelta(hours=12)
        normalized = calendar_core.normalize_calendar(
            noon.isoformat(),
            timezone_name=timezone_name,
            location=location_name,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
            coordinate_accuracy_meters=coordinate_accuracy_meters,
            zi_hour_policy=zi_hour_policy,
            time_basis_policy=time_basis_policy,
        )

        def corrected_boundary(value: str) -> datetime:
            point = datetime.fromisoformat(value)
            if time_basis_policy == "civil":
                return point
            boundary_calendar = calendar_core.normalize_calendar(
                point.isoformat(),
                timezone_name=timezone_name,
                location=location_name,
                longitude=longitude,
                latitude=latitude,
                coordinate_source=coordinate_source,
                coordinate_accuracy_meters=coordinate_accuracy_meters,
                zi_hour_policy=zi_hour_policy,
                time_basis_policy=time_basis_policy,
            )
            correction_seconds = int(
                (boundary_calendar.get("time_basis") or {}).get(
                    "total_correction_seconds"
                )
                or 0
            )
            return point - timedelta(seconds=correction_seconds)

        term_boundaries = [
            corrected_boundary(item["datetime"])
            for item in calendar_core.month_boundary_terms(
                target_date.year,
                target_date.month,
                timezone_name,
            )
        ]
        boundary_points = [
            point for point in term_boundaries if day_start < point < day_end
        ]
        if zi_hour_policy == "late-zi-next-day":
            late_zi_boundary = corrected_boundary(
                day_start.replace(hour=23).isoformat()
            )
            if day_start < late_zi_boundary < day_end:
                boundary_points.append(late_zi_boundary)
        points = [day_start, *sorted(set(boundary_points)), day_end]
        segments: list[dict[str, Any]] = []
        for segment_start, segment_end in zip(points, points[1:]):
            sample = segment_start + (segment_end - segment_start) / 2
            segment_calendar = calendar_core.normalize_calendar(
                sample.isoformat(),
                timezone_name=timezone_name,
                location=location_name,
                longitude=longitude,
                latitude=latitude,
                coordinate_source=coordinate_source,
                coordinate_accuracy_meters=coordinate_accuracy_meters,
                zi_hour_policy=zi_hour_policy,
                time_basis_policy=time_basis_policy,
            )
            active_transits = {
                layer: segment_calendar["ganzhi"][layer]
                for layer in ("year", "month", "day")
            }
            segment_transit = _extension_transit_facts(
                active_transits["day"],
                day_stem=day_stem,
                pillars=pillars,
                seasonal_branch=active_transits["month"][1],
            )
            segments.append(
                {
                    "start_inclusive": segment_start.isoformat(
                        timespec="microseconds"
                    ),
                    "end_exclusive": segment_end.isoformat(
                        timespec="microseconds"
                    ),
                    "sample_instant": sample.isoformat(timespec="microseconds"),
                    "active_transits": active_transits,
                    "calendar_digest": segment_calendar["calendar_digest"],
                    **segment_transit,
                }
            )
        transit = _extension_transit_facts(
            normalized["ganzhi"]["day"],
            day_stem=day_stem,
            pillars=pillars,
            seasonal_branch=normalized["ganzhi"]["month"][1],
        )
        if len(segments) > 1:
            transit["structural_changes"] = {
                "status": "segmented_by_exact_calendar_boundary",
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        "facts": item["structural_changes"],
                    }
                    for item in segments
                ],
                "hard_verdict": None,
            }
            transit["seasonal_tiaohou_delta"] = {
                "status": "segmented_by_exact_calendar_boundary",
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        "facts": item["seasonal_tiaohou_delta"],
                    }
                    for item in segments
                ],
                "favorability_status": "requires_classical_adjudication",
            }
            transit["shensha_auxiliary"] = {
                "status": "segmented_auxiliary_layer",
                "precedence": "auxiliary_only",
                "may_override": [],
                "cannot_override": list(
                    segments[0]["shensha_auxiliary"]["cannot_override"]
                ),
                "segments": [
                    {
                        "start_inclusive": item["start_inclusive"],
                        "end_exclusive": item["end_exclusive"],
                        "facts": item["shensha_auxiliary"],
                    }
                    for item in segments
                ],
                "source_dependency_id": (
                    "bazi.shensha.yima-taohua-auxiliary"
                ),
            }
        normalized["horizon_boundaries"] = [
            point.isoformat(timespec="microseconds")
            for point in boundary_points
        ]
        key = target_date.isoformat()
        layers[key] = {
            "date": key,
            **transit,
            "active_transits": {
                layer: normalized["ganzhi"][layer]
                for layer in ("year", "month", "day")
            },
            "representative_instant": noon.isoformat(timespec="seconds"),
            "ganzhi_segments": segments,
            "active_luck_cycle": _extension_active_luck_cycle_interval(
                day_start,
                day_end,
                chart_facts,
                transition_status="transition_period",
            ),
            "calendar_normalization": normalized,
            "rule_trace": [
                {
                    "rule_id": "bazi.sexagenary-day.sxtwl-v1",
                    "source_dependency_id": "bazi.calendar.sxtwl-jieqi-four-pillars",
                    "operation": "shared calendar day Ganzhi and exact active year/month context",
                },
                {
                    "rule_id": "bazi.luck-cycle.overlap-v1",
                    "source_dependency_id": "bazi.luck.major-cycle-three-days-per-year",
                    "operation": "civil-day elapsed-age interval overlaps calculated luck cycles",
                },
                {
                    "rule_id": "bazi.transit-relations.standard-table-v1",
                    "source_dependency_id": "bazi.relations.ten-gods-hidden-stems-branch-relations",
                    "operation": "daily stem Ten God and daily branch relations",
                },
                {
                    "rule_id": "bazi.seasonal-tiaohou.day-master-month-v1",
                    "source_dependency_id": "bazi.seasonal-tiaohou.day-master-month",
                    "operation": "daily climate comparison remains a fact, not a favorability verdict",
                },
            ],
        }
    return layers


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    pillars = subparsers.add_parser("pillars", help="Validate supplied/OCR four pillars and derive static facts")
    pillars.add_argument("--pillars", nargs="+", required=True, metavar="PILLAR")
    pillars.add_argument("--gender")
    pillars.add_argument(
        "--source",
        choices=("image", "text", "user_chart", "user_text", "screenshot"),
        default="text",
    )
    pillars.add_argument("--source-ref")
    pillars.add_argument("--reasoning-domains", nargs="*", default=[])
    pillars.add_argument("--output", help="Also write the JSON payload to this file")

    birth = subparsers.add_parser("birth", help="Calculate a chart from civil birth data")
    birth.add_argument("--datetime", required=True, dest="civil_datetime")
    birth.add_argument("--timezone", required=True)
    birth.add_argument("--location", required=True)
    birth.add_argument("--longitude", type=float)
    birth.add_argument("--latitude", type=float)
    birth.add_argument("--coordinate-source")
    birth.add_argument("--coordinate-accuracy-meters", type=float)
    birth.add_argument(
        "--time-basis-policy",
        choices=tuple(sorted(calendar_core.TIME_BASIS_POLICIES)),
        default="civil",
    )
    birth.add_argument("--gender", required=True)
    birth.add_argument("--expected-pillars", nargs="+", metavar="PILLAR")
    birth.add_argument("--zi-hour-policy", choices=("midnight", "late-zi-next-day"), default="midnight")
    birth.add_argument("--reasoning-domains", nargs="*", default=[])
    birth.add_argument("--output", help="Also write the JSON payload to this file")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.mode == "pillars":
            payload = build_from_pillars(
                args.pillars,
                gender=args.gender,
                source=args.source,
                source_ref=args.source_ref,
                question_contract={
                    "domains": list(args.reasoning_domains),
                    "gender": args.gender,
                },
            )
            conflict = False
        else:
            payload, conflict = build_from_birth(
                args.civil_datetime,
                timezone_name=args.timezone,
                location=args.location,
                gender=args.gender,
                expected_pillars=args.expected_pillars,
                zi_hour_policy=args.zi_hour_policy,
                longitude=args.longitude,
                latitude=args.latitude,
                coordinate_source=args.coordinate_source,
                coordinate_accuracy_meters=args.coordinate_accuracy_meters,
                time_basis_policy=args.time_basis_policy,
                question_contract={
                    "domains": list(args.reasoning_domains),
                    "gender": args.gender,
                },
            )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 3 if conflict else 0


if __name__ == "__main__":
    raise SystemExit(main())
