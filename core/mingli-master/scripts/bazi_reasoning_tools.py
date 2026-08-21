#!/usr/bin/env python3
"""Compile bounded, source-aware Bazi reasoning tools from frozen chart facts.

The outputs are intermediate observations, not life-event verdicts. They make
the previously implicit month-strength, structure, and domain-selection steps
auditable without pretending that disputed interpretive rules are arithmetic.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from bazi_fact_adapter import (
    ELEMENTS,
    STEM_ELEMENT,
    STEM_TRANSFORMATIONS,
    _seasonal_states,
    _ten_god,
)
from evidence_contract import canonical_digest
from reading_engine import evidence_rules

SCHEMA_VERSION = "mingli-bazi-reasoning-tool-v2"
CONFIDENCE_BUCKETS = {"low", "medium", "high"}
VISIBILITY_CLASSES = {"auto_injected", "on_demand", "translated", "trigger_only"}
GENERATES = dict(zip(ELEMENTS, (*ELEMENTS[1:], ELEMENTS[0])))

SUPPORT_ROLES = {"比肩", "劫财", "正印", "偏印"}
PRESSURE_ROLES = {"食神", "伤官", "正财", "偏财", "正官", "七杀"}

STRENGTH_SOURCES = [
    {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-05"},
    {"pack": "bazi/sanming-tonghui", "rule_id": "R-02-04"},
    {"pack": "bazi/sanming-tonghui", "rule_id": "R-04-02"},
    {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-02-06"},
]
MONTH_ORDER_STATE_RULE_ID = "bazi/sanming-tonghui#R-02-04"
MONTH_ORDER_UNRESOLVED_CHECKS = (
    "全局根气、生扶、克泄与合化",
    "从格、化气及旺极衰极的反向取用",
    "整个日主强弱、唯一用神与现实吉凶应期",
)
DAY_MASTER_ROOT_SUPPORT_UNRESOLVED_CHECKS = (
    "从格、化气及旺极衰极的反向取用",
    "整个日主强弱、唯一用神与现实吉凶应期",
)
MONTH_COMMAND_SUPPORT_OR_DRAIN = {
    "旺": "当令同气生扶",
    "相": "月令所生之相（生扶）",
    "休": "生我之休（泄）",
    "囚": "克我之囚",
    "死": "我克之死（克）",
}
STRUCTURE_SOURCES = [
    {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-12"},
    {"pack": "bazi/ziping-zhenquan", "rule_id": "ZPR-01"},
]
CONFLICT_ARBITRATION_SOURCES = [
    {
        "pack": "bazi/ziping-zhenquan",
        "rule_id": "ZPR-01",
        "source_anchor": "references/books/bazi/ziping-zhenquan/rules.md#ZPR-01",
    },
    {
        "pack": "bazi/ditiansui-chanwei",
        "rule_id": "DR-02-06",
        "source_anchor": "references/books/bazi/ditiansui-chanwei/rules.md#DR-02-06",
    },
]

ZIPING_MONTH_PATTERN_RULE_ID = "bazi/ziping-zhenquan#ZPR-01"
ZIPING_MONTH_PATTERN_SOURCE_ANCHOR = (
    "references/books/bazi/ziping-zhenquan/rules.md#ZPR-01"
)

DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "finance": {
        "roles": ["正财", "偏财", "比肩", "劫财"],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-02-04~13"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-05"},
        ],
        "caveat": "indicator roles do not determine exact wealth, amount, or outcome",
    },
    "work": {
        "roles": ["正官", "七杀", "正印", "偏印", "食神", "伤官", "正财", "偏财"],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-02-04~13"},
            {"pack": "bazi/sanming-tonghui", "rule_id": "R-05-02"},
        ],
        "caveat": "broad role indicators cannot identify an exact profession or employer",
    },
    "education": {
        "roles": ["正印", "偏印", "食神", "伤官"],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-02-04~13"},
            {"pack": "bazi/sanming-tonghui", "rule_id": "R-03-09"},
        ],
        "caveat": "these are learning and expression indicators, not an exact education level",
    },
    "health": {
        "roles": [],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-09"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-07-02"},
        ],
        "caveat": "element imbalance is not a medical diagnosis or an exact organ event",
    },
    "travel": {
        "roles": [],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-06~11"},
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-02~03"},
        ],
        "caveat": "static branch relations cannot identify an exact move, destination, or year",
    },
    "family": {
        "roles": ["正印", "偏印", "正财", "偏财", "比肩", "劫财"],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-04"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-03"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-04"},
        ],
        "caveat": "family-role correspondences differ by lineage and cannot fix an exact event",
    },
    "personality": {
        "roles": [],
        "sources": [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-06"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-07-01"},
        ],
        "caveat": "element and stem correspondences indicate broad tendencies, not a fixed personality or psychological diagnosis",
        "confidence_ceiling": "low",
    },
    "appearance": {
        "roles": [],
        "sources": [
            {"pack": "bazi/sanming-tonghui", "rule_id": "R-07-01"},
        ],
        "caveat": "classical appearance correspondences are broad tendencies and cannot identify exact body shape, skin tone, or attractiveness",
        "confidence_ceiling": "low",
    },
}

_SEASON_BY_MONTH = {
    "寅": "spring",
    "卯": "spring",
    "辰": "spring",
    "巳": "summer",
    "午": "summer",
    "未": "summer",
    "申": "autumn",
    "酉": "autumn",
    "戌": "autumn",
    "亥": "winter",
    "子": "winter",
    "丑": "winter",
}

# Qiongtong Baojian's 40 seasonal entries.  The table is deliberately kept
# as a candidate rule layer: verification is resolved per rule from the
# checked evidence index, and even a verified seasonal entry must still be
# reconciled with strength and structure before becoming a 用神 conclusion.
_TIAOHOU_RULES: dict[str, dict[str, dict[str, object]]] = {
    "甲": {
        "spring": {"rule_id": "QR-01-01", "priority": {"寅": ("丙", "癸"), "卯": ("庚",), "辰": ("庚", "壬")}},
        "summer": {"rule_id": "QR-01-02", "priority": {"巳": ("癸", "丁"), "午": ("癸", "丁", "庚"), "未": ("丁", "庚")}},
        "autumn": {"rule_id": "QR-01-03", "priority": {"申": ("丁", "庚"), "酉": ("丁", "丙", "庚"), "戌": ("丁", "壬", "癸")}},
        "winter": {"rule_id": "QR-01-04", "priority": {"亥": ("庚", "丁", "戊"), "子": ("庚", "丁", "戊"), "丑": ("庚", "丁", "戊")}},
    },
    "乙": {
        "spring": {"rule_id": "QR-01-05", "priority": {"寅": ("丙", "癸"), "卯": ("丙", "癸"), "辰": ("癸", "丙")}},
        "summer": {"rule_id": "QR-01-06", "priority": {"巳": ("癸", "丙"), "午": ("癸", "丙"), "未": ("癸", "丙")}},
        "autumn": {"rule_id": "QR-01-07", "priority": {"申": ("丙", "癸"), "酉": ("丙", "癸"), "戌": ("癸",)}},
        "winter": {"rule_id": "QR-01-08", "priority": {"亥": ("丙", "戊"), "子": ("丙", "戊"), "丑": ("丙", "戊")}},
    },
    "丙": {
        "spring": {"rule_id": "QR-02-01", "priority": {"寅": ("壬", "庚", "辛"), "卯": ("壬",), "辰": ("壬", "甲")}},
        "summer": {"rule_id": "QR-02-02", "priority": {"巳": ("壬", "庚"), "午": ("壬",), "未": ("壬", "庚")}},
        "autumn": {"rule_id": "QR-02-03", "priority": {"申": ("甲", "壬"), "酉": ("甲", "壬"), "戌": ("甲", "壬", "癸")}},
        "winter": {"rule_id": "QR-02-04", "priority": {"亥": ("庚", "戊", "壬"), "子": ("壬", "戊"), "丑": ("壬", "甲")}},
    },
    "丁": {
        "spring": {"rule_id": "QR-02-05", "priority": {"寅": ("庚", "甲"), "卯": ("庚", "甲"), "辰": ("庚", "甲")}},
        "summer": {"rule_id": "QR-02-06", "priority": {"巳": ("庚", "壬"), "午": ("庚", "壬"), "未": ("庚", "壬")}},
        "autumn": {"rule_id": "QR-02-07", "priority": {"申": ("甲", "庚"), "酉": ("甲", "庚"), "戌": ("甲", "庚")}},
        "winter": {"rule_id": "QR-02-08", "priority": {"亥": ("甲", "庚", "戊"), "子": ("甲", "庚", "戊"), "丑": ("甲", "庚", "戊")}},
    },
    "戊": {
        "spring": {"rule_id": "QR-03-01", "priority": {"寅": ("丙", "甲", "癸"), "卯": ("丙", "甲", "癸"), "辰": ("甲", "丙", "癸")}},
        "summer": {"rule_id": "QR-03-02", "priority": {"巳": ("癸", "丙"), "午": ("癸", "丙"), "未": ("癸", "丙")}},
        "autumn": {"rule_id": "QR-03-03", "priority": {"申": ("丙", "癸", "甲"), "酉": ("丙", "癸", "甲"), "戌": ("丙", "癸", "甲")}},
        "winter": {"rule_id": "QR-03-04", "priority": {"亥": ("甲", "丙"), "子": ("丙", "甲"), "丑": ("丙", "甲")}},
    },
    "己": {
        "spring": {"rule_id": "QR-03-05", "priority": {"寅": ("丙", "癸", "甲"), "卯": ("丙", "癸", "甲"), "辰": ("丙", "癸", "甲")}},
        "summer": {"rule_id": "QR-03-06", "priority": {"巳": ("癸", "丙"), "午": ("癸", "丙"), "未": ("癸", "丙")}},
        "autumn": {"rule_id": "QR-03-07", "priority": {"申": ("丙", "癸"), "酉": ("丙", "癸"), "戌": ("癸", "丙", "甲")}},
        "winter": {"rule_id": "QR-03-08", "priority": {"亥": ("丙", "戊"), "子": ("丙", "戊"), "丑": ("丙", "戊")}},
    },
    "庚": {
        "spring": {"rule_id": "QR-04-01", "priority": {"寅": ("丙", "甲", "丁"), "卯": ("丁", "甲"), "辰": ("甲", "丁")}},
        "summer": {"rule_id": "QR-04-02", "priority": {"巳": ("壬", "丙", "戊"), "午": ("壬", "癸"), "未": ("丁", "甲")}},
        "autumn": {"rule_id": "QR-04-03", "priority": {"申": ("丁", "甲"), "酉": ("丁", "甲"), "戌": ("丁", "甲")}},
        "winter": {"rule_id": "QR-04-04", "priority": {"亥": ("丁", "丙", "戊"), "子": ("丁", "丙", "戊"), "丑": ("丁", "丙", "戊")}},
    },
    "辛": {
        "spring": {"rule_id": "QR-04-05", "priority": {"寅": ("己", "壬"), "卯": ("己", "壬"), "辰": ("己", "壬")}},
        "summer": {"rule_id": "QR-04-06", "priority": {"巳": ("壬", "己", "癸"), "午": ("壬", "己", "癸"), "未": ("壬", "己", "癸")}},
        "autumn": {"rule_id": "QR-04-07", "priority": {"申": ("壬", "甲", "戊"), "酉": ("壬",), "戌": ("壬", "甲")}},
        "winter": {"rule_id": "QR-04-08", "priority": {"亥": ("丙", "壬"), "子": ("丙", "壬"), "丑": ("丙", "壬")}},
    },
    "壬": {
        "spring": {"rule_id": "QR-05-01", "priority": {"寅": ("辛", "戊"), "卯": ("辛", "戊"), "辰": ("辛", "戊")}},
        "summer": {"rule_id": "QR-05-02", "priority": {"巳": ("壬", "辛", "庚"), "午": ("癸", "庚"), "未": ("辛", "甲", "癸")}},
        "autumn": {"rule_id": "QR-05-03", "priority": {"申": ("戊", "丁"), "酉": ("戊", "丁"), "戌": ("戊", "丁")}},
        "winter": {"rule_id": "QR-05-04", "priority": {"亥": ("戊", "丙", "庚"), "子": ("戊", "丙"), "丑": ("丙", "甲")}},
    },
    "癸": {
        "spring": {"rule_id": "QR-05-05", "priority": {"寅": ("辛", "丙"), "卯": ("辛", "丙"), "辰": ("辛", "丙")}},
        "summer": {"rule_id": "QR-05-06", "priority": {"巳": ("辛", "庚"), "午": ("辛", "庚"), "未": ("辛", "庚")}},
        "autumn": {"rule_id": "QR-05-07", "priority": {"申": ("辛", "丁"), "酉": ("辛", "丁"), "戌": ("辛", "丁")}},
        "winter": {"rule_id": "QR-05-08", "priority": {"亥": ("庚", "辛"), "子": ("丙", "辛"), "丑": ("丙",)}},
    },
}


def _fact(path: str, value: Any) -> dict[str, Any]:
    return {"path": path, "value": value}


def _build_tool(
    *,
    tool_id: str,
    tool_kind: str,
    confidence_bucket: str,
    fact_refs: list[dict[str, Any]],
    source_refs: list[dict[str, str]],
    output: dict[str, Any],
    caveats: list[str],
    visibility_class: str,
    confidence_ceiling: str,
) -> dict[str, Any]:
    if confidence_bucket not in CONFIDENCE_BUCKETS:
        raise ValueError("invalid Bazi reasoning-tool confidence")
    if visibility_class not in VISIBILITY_CLASSES:
        raise ValueError("invalid Bazi reasoning-tool visibility class")
    if confidence_ceiling not in CONFIDENCE_BUCKETS:
        raise ValueError("invalid Bazi reasoning-tool confidence ceiling")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_id": tool_id,
        "tool_kind": tool_kind,
        "confidence_bucket": confidence_bucket,
        "confidence_ceiling": confidence_ceiling,
        "visibility_class": visibility_class,
        "fact_refs": fact_refs,
        "source_refs": source_refs,
        "output": output,
        "caveats": caveats,
    }
    payload["tool_digest"] = canonical_digest(payload)
    return payload


def validate_reasoning_tool(tool: dict[str, Any]) -> bool:
    if not isinstance(tool, dict) or tool.get("schema_version") != SCHEMA_VERSION:
        return False
    digest = tool.get("tool_digest")
    payload = {key: value for key, value in tool.items() if key != "tool_digest"}
    if not isinstance(digest, str) or digest != canonical_digest(payload):
        return False
    if tool.get("confidence_bucket") not in CONFIDENCE_BUCKETS:
        return False
    if tool.get("confidence_ceiling") not in CONFIDENCE_BUCKETS:
        return False
    if tool.get("visibility_class") not in VISIBILITY_CLASSES:
        return False
    return bool(tool.get("tool_id") and tool.get("fact_refs") and tool.get("source_refs"))


def _role_occurrences(output: dict[str, Any], roles: set[str]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    visible = output.get("ten_gods", {}).get("heavenly_stems", {})
    for position, item in visible.items():
        if isinstance(item, dict) and item.get("ten_god") in roles:
            occurrences.append(
                {
                    "layer": "visible_stem",
                    "position": position,
                    "stem": item.get("stem"),
                    "ten_god": item.get("ten_god"),
                }
            )
    hidden = output.get("ten_gods", {}).get("hidden_stems", {})
    for position, items in hidden.items():
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("ten_god") in roles:
                occurrences.append(
                    {
                        "layer": "hidden_stem",
                        "position": position,
                        "stem": item.get("stem"),
                        "ten_god": item.get("ten_god"),
                    }
                )
    return occurrences



def _root_support_regime_blockers(
    *,
    pillars: dict[str, Any],
    day_stem: str,
    command_element: str,
    seasonal_state: str,
    direct_root_positions: list[str],
    resource_positions: list[str],
    evidence_lean: str,
    pressure_count: int,
) -> list[str]:
    """Refuse ordinary root/support counts when reverse-use may apply.

    These are mechanical preconditions, not 从格/化气 verdicts. A five-stem
    combination only blocks when the candidate transformation element is
    the month command (化神当令). Following-structure only blocks when the
    day master has no same-element root and no resource in the branches.
    """

    blockers: list[str] = []
    for position, pillar in pillars.items():
        if position == "day" or not isinstance(pillar, str) or not pillar:
            continue
        transformed = STEM_TRANSFORMATIONS.get(frozenset((day_stem, pillar[0])))
        if transformed == command_element:
            blockers.append("transformation_command_element_present")
            break
    if not direct_root_positions and not resource_positions:
        blockers.append("following_structure_no_root")
    if (
        seasonal_state == "旺"
        and evidence_lean == "support_lean"
        and pressure_count == 0
    ):
        blockers.append("extreme_prosperity_reverse_use")
    if (
        seasonal_state in {"死", "囚"}
        and evidence_lean == "oppose_lean"
        and not direct_root_positions
    ):
        blockers.append("extreme_decline_reverse_use")
    return blockers


def _strength_tool(snapshot: dict[str, Any]) -> dict[str, Any]:
    output = snapshot["output"]
    day_element = output["day_master"]["element"]
    command_element = output["month_command"]["main_qi_element"]
    states = _seasonal_states(command_element)
    seasonal_state = states[day_element]
    hidden = output["hidden_stems"]
    direct_root_positions: list[str] = []
    resource_positions: list[str] = []
    resource_element = next(
        element for element, generated in GENERATES.items() if generated == day_element
    )
    for position, item in hidden.items():
        stems = item.get("stems") if isinstance(item, dict) else []
        elements = {STEM_ELEMENT[stem] for stem in stems}
        if day_element in elements:
            direct_root_positions.append(position)
        if resource_element in elements:
            resource_positions.append(position)

    support_visible = _role_occurrences(output, SUPPORT_ROLES)
    pressure_visible = [
        item
        for item in _role_occurrences(output, PRESSURE_ROLES)
        if item["layer"] == "visible_stem"
    ]
    support_groups: list[str] = []
    oppose_groups: list[str] = []
    if seasonal_state in {"旺", "相"}:
        support_groups.append("month_season")
    else:
        oppose_groups.append("month_season")
    if direct_root_positions:
        support_groups.append("same_element_roots")
    else:
        oppose_groups.append("no_same_element_root")
    if resource_positions:
        support_groups.append("resource_in_branches")
    visible_support_count = sum(
        item["layer"] == "visible_stem" for item in support_visible
    )
    if visible_support_count > len(pressure_visible):
        support_groups.append("visible_role_balance")
    elif len(pressure_visible) > visible_support_count:
        oppose_groups.append("visible_role_balance")

    difference = len(support_groups) - len(oppose_groups)
    evidence_lean = (
        "support_lean" if difference >= 2 else "oppose_lean" if difference <= -2 else "mixed"
    )
    confidence = "medium" if abs(difference) >= 2 else "low"
    month_order_rule = _runtime_evidence_rule(MONTH_ORDER_STATE_RULE_ID)
    if (
        not month_order_rule.runtime_active
        or month_order_rule.classical_binding_status != "verified"
        or not month_order_rule.classical_binding_digest
    ):
        raise RuntimeError("the Bazi month-order state rule is not source-verified")
    month_order_adjudication = {
        "status": "adjudicated_month_order_state",
        "decision_scope": "bazi_month_order_seasonal_state",
        "day_master_element": day_element,
        "month_command_element": command_element,
        "seasonal_state": seasonal_state,
        "whole_chart_strength_verdict": None,
        "useful_god_verdict": None,
        "source_ref": {
            "pack": month_order_rule.source_pack,
            "rule_id": month_order_rule.local_rule_id,
            "source_anchor": (
                "references/books/bazi/sanming-tonghui/rules.md#R-02-04"
            ),
            "verification_status": month_order_rule.classical_binding_status,
            "binding_digest": month_order_rule.classical_binding_digest,
        },
        "unresolved_checks": list(MONTH_ORDER_UNRESOLVED_CHECKS),
    }
    inventory = output.get("element_inventory") or {}
    visible_counts = (
        inventory.get("visible_stem_branch_counts")
        if isinstance(inventory, dict)
        else {}
    )
    hidden_counts = (
        inventory.get("hidden_stem_occurrence_counts")
        if isinstance(inventory, dict)
        else {}
    )
    if not isinstance(visible_counts, dict):
        visible_counts = {}
    if not isinstance(hidden_counts, dict):
        hidden_counts = {}
    element_occurrences = {
        element: int(visible_counts.get(element, 0))
        + int(hidden_counts.get(element, 0))
        for element in ELEMENTS
    }
    pillars = output.get("four_pillars") or {}
    if not isinstance(pillars, dict):
        pillars = {}
    day_stem = str(output["day_master"]["stem"])
    regime_blockers = _root_support_regime_blockers(
        pillars=pillars,
        day_stem=day_stem,
        command_element=command_element,
        seasonal_state=seasonal_state,
        direct_root_positions=direct_root_positions,
        resource_positions=resource_positions,
        evidence_lean=evidence_lean,
        pressure_count=len(pressure_visible),
    )
    root_support_adjudication = {
        "status": (
            "refused_following_or_transformation_regime"
            if regime_blockers
            else "adjudicated_root_support_evidence"
        ),
        "decision_scope": "bazi_day_master_root_support_evidence",
        "day_master_element": day_element,
        "month_command_element": command_element,
        "seasonal_state": seasonal_state,
        "month_command_support_or_drain": MONTH_COMMAND_SUPPORT_OR_DRAIN[
            seasonal_state
        ],
        "same_element_occurrences": element_occurrences[day_element],
        "resource_element": resource_element,
        "resource_occurrences": element_occurrences[resource_element],
        "all_element_occurrences": element_occurrences,
        "same_element_root_positions": list(direct_root_positions),
        "resource_branch_positions": list(resource_positions),
        "visible_support_role_count": visible_support_count,
        "visible_pressure_role_count": len(pressure_visible),
        "regime_blockers": list(regime_blockers),
        "whole_chart_strength_verdict": None,
        "useful_god_verdict": None,
        "source_ref": {
            "pack": month_order_rule.source_pack,
            "rule_id": month_order_rule.local_rule_id,
            "source_anchor": (
                "references/books/bazi/sanming-tonghui/rules.md#R-02-04"
            ),
            "verification_status": month_order_rule.classical_binding_status,
            "binding_digest": month_order_rule.classical_binding_digest,
        },
        "unresolved_checks": list(DAY_MASTER_ROOT_SUPPORT_UNRESOLVED_CHECKS),
    }
    return _build_tool(
        tool_id="bazi.tool.strength_evidence",
        tool_kind="disputed_rule_synthesis",
        confidence_bucket=confidence,
        fact_refs=[
            _fact("$.output.day_master", output["day_master"]),
            _fact("$.output.month_command", output["month_command"]),
            _fact("$.output.hidden_stems", output["hidden_stems"]),
            _fact("$.output.ten_gods", output["ten_gods"]),
        ],
        source_refs=STRENGTH_SOURCES,
        output={
            "status": "bounded_evidence_synthesis",
            "day_master_element": day_element,
            "month_command_element": command_element,
            "seasonal_state": seasonal_state,
            "seasonal_state_table": states,
            "same_element_root_positions": direct_root_positions,
            "resource_element": resource_element,
            "resource_branch_positions": resource_positions,
            "visible_support_role_count": visible_support_count,
            "visible_pressure_role_count": len(pressure_visible),
            "support_evidence_groups": support_groups,
            "oppose_evidence_groups": oppose_groups,
            "evidence_lean": evidence_lean,
            "month_order_adjudication": month_order_adjudication,
            "day_master_root_support_adjudication": root_support_adjudication,
        },
        caveats=[
            "this is an evidence lean, not a categorical strong/weak verdict",
            "hidden-stem occurrences are not weighted qi scores",
            "transformation, following structures, and full flow may override the lean",
        ],
        visibility_class="on_demand",
        confidence_ceiling="medium",
    )


def _tiaohou_tool(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Apply the Qiongtong seasonal rule as a source-aware candidate.

    This is intentionally not folded into ``_strength_tool``.  Seasonal
    adjustment and strength are different rule families, and the reference
    procedure explicitly says they must be reconciled rather than silently
    collapsed into one 用神 verdict.
    """

    output = snapshot["output"]
    day_stem = str(output["day_master"]["stem"])
    month_branch = str(output["month_command"]["branch"])
    season = _SEASON_BY_MONTH[month_branch]
    group = _TIAOHOU_RULES[day_stem][season]
    rule_id = str(group["rule_id"])
    source_rule = _runtime_evidence_rule(
        f"bazi/qiongtong-baojian#{rule_id}"
    )
    verification_status = source_rule.classical_binding_status
    verified = source_rule.runtime_active and verification_status == "verified"
    priority_by_month = group["priority"]
    assert isinstance(priority_by_month, dict)
    priority_stems = list(priority_by_month[month_branch]) if verified else []
    visible_pillars = output["four_pillars"]
    hidden_stems = output["hidden_stems"]
    matches: list[dict[str, Any]] = []
    for priority, stem in enumerate(priority_stems, start=1):
        visible_positions = [
            position
            for position, pillar in visible_pillars.items()
            if position != "day" and str(pillar)[0] == stem
        ]
        hidden_positions = [
            position
            for position, branch_data in hidden_stems.items()
            if stem in (branch_data.get("stems") or [])
        ]
        status = (
            "visible"
            if visible_positions
            else "hidden"
            if hidden_positions
            else "missing"
        )
        matches.append(
            {
                "priority": priority,
                "stem": stem,
                "element": STEM_ELEMENT[stem],
                "status": status,
                "visible_positions": visible_positions,
                "hidden_positions": hidden_positions,
            }
        )
    visible_count = sum(item["status"] == "visible" for item in matches)
    present_count = sum(item["status"] != "missing" for item in matches)
    coverage_status = (
        "unavailable_unverified_rule"
        if not verified
        else "complete_visible"
        if visible_count == len(matches)
        else "partial_visible_or_hidden"
        if present_count
        else "missing"
    )
    return _build_tool(
        tool_id="bazi.tool.tiaohou_candidates",
        tool_kind="seasonal_adjustment_candidate",
        confidence_bucket="medium" if verified else "low",
        fact_refs=[
            _fact("$.output.day_master", output["day_master"]),
            _fact("$.output.month_command", output["month_command"]),
            _fact("$.output.four_pillars", output["four_pillars"]),
            _fact("$.output.hidden_stems", output["hidden_stems"]),
            _fact("$.output.tiaohou_markers", output["tiaohou_markers"]),
        ],
        source_refs=[
            {
                "pack": "bazi/qiongtong-baojian",
                "rule_id": rule_id,
                "source_anchor": (
                    "references/books/bazi/qiongtong-baojian/rules.md#"
                    f"{rule_id}"
                ),
                "verification_status": verification_status,
                "binding_digest": source_rule.classical_binding_digest,
            }
        ],
        output={
            "status": (
                "adjudicated_seasonal_priority"
                if verified
                else "unavailable_unverified_rule"
            ),
            "rule_id": rule_id,
            "verification_status": verification_status,
            "day_stem": day_stem,
            "month_branch": month_branch,
            "season": season,
            "priority_stems": priority_stems,
            "matches": matches,
            "coverage_status": coverage_status,
            "hard_verdict": None,
        },
        caveats=[
            "Qiongtong seasonal combinations are typical candidates, not a unique 用神 verdict",
            (
                "this rule has a verified source/applicability binding but still "
                "requires strength/structure reconciliation"
                if verified
                else "this rule remains runtime-inactive pending "
                "source/applicability verification"
            ),
            "透干、藏支、缺失 only describe availability; they do not establish "
            "favorability or life outcomes",
        ],
        visibility_class="on_demand",
        confidence_ceiling="medium" if verified else "low",
    )


def _structure_tool(snapshot: dict[str, Any]) -> dict[str, Any]:
    output = snapshot["output"]
    day_stem = output["day_master"]["stem"]
    main_qi = output["month_command"]["main_qi"]
    main_role = _ten_god(day_stem, main_qi)
    visible = output["ten_gods"]["heavenly_stems"]
    visible_positions = [
        position
        for position, item in visible.items()
        if position != "day" and isinstance(item, dict) and item.get("stem") == main_qi
    ]
    return _build_tool(
        tool_id="bazi.tool.month_structure_candidate",
        tool_kind="rule_applicability",
        confidence_bucket="medium" if visible_positions else "low",
        fact_refs=[
            _fact("$.output.day_master.stem", day_stem),
            _fact("$.output.month_command", output["month_command"]),
            _fact("$.output.ten_gods.heavenly_stems", visible),
        ],
        source_refs=STRUCTURE_SOURCES,
        output={
            "status": "candidate_only",
            "month_main_qi": main_qi,
            "month_main_qi_ten_god": main_role,
            "main_qi_visible": bool(visible_positions),
            "visible_positions": visible_positions,
            "special_month_role": main_role if main_role in {"比肩", "劫财"} else None,
        },
        caveats=[
            "month main qi opens a structure candidate but does not prove structure success",
            "透干、会支、合化、成败救应 and exceptions still require adjudication",
        ],
        visibility_class="on_demand",
        confidence_ceiling="medium",
    )


def _runtime_evidence_rule(rule_id: str) -> evidence_rules.EvidenceRule:
    """Resolve one checked runtime rule instead of trusting copied metadata."""

    rule = next(
        (
            item
            for item in evidence_rules.production_evidence_rules()
            if item.rule_id == rule_id
        ),
        None,
    )
    if rule is None:
        raise RuntimeError(f"runtime evidence rule is missing: {rule_id}")
    return rule


def _verified_ziping_month_pattern_rule() -> evidence_rules.EvidenceRule:
    """Resolve ZPR-01 and require its checked binding to remain active."""

    rule = _runtime_evidence_rule(ZIPING_MONTH_PATTERN_RULE_ID)
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(
            "the Ziping month-pattern adjudication rule is not source-verified"
        )
    return rule


def _ziping_month_pattern_adjudication_tool(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Adjudicate only the Shen-style month-command pattern entry.

    ZPR-01 authorizes selecting the entry point from the day stem's relation
    to the month command.  It does not authorize declaring structure success,
    body strength, a unique useful god, or a life-event outcome, so those
    checks remain explicit unresolved outputs.
    """

    output = snapshot["output"]
    day_stem = str(output["day_master"]["stem"])
    month_command = output["month_command"]
    month_main_qi = str(month_command["main_qi"])
    month_role = _ten_god(day_stem, month_main_qi)
    rule = _verified_ziping_month_pattern_rule()
    is_jianlu_yuejie = month_role in {"比肩", "劫财"}
    unresolved_checks = (
        [
            "透干会支另取财官煞食",
            "格局成败与救应",
            "旺衰、调候与行运",
        ]
        if is_jianlu_yuejie
        else [
            "格局成败与救应",
            "顺逆配合与相神",
            "旺衰、调候与行运",
        ]
    )
    return _build_tool(
        tool_id="bazi.tool.ziping_month_pattern_adjudication",
        tool_kind="source_bound_pattern_entry_adjudication",
        confidence_bucket="high",
        fact_refs=[
            _fact("$.output.day_master.stem", day_stem),
            _fact("$.output.month_command", month_command),
        ],
        source_refs=[
            {
                "pack": rule.source_pack,
                "rule_id": rule.local_rule_id,
                "source_anchor": ZIPING_MONTH_PATTERN_SOURCE_ANCHOR,
                "verification_status": rule.classical_binding_status,
                "binding_digest": rule.classical_binding_digest,
            }
        ],
        output={
            "status": (
                "exception_requires_external_selection"
                if is_jianlu_yuejie
                else "adjudicated_pattern_entry"
            ),
            "decision_scope": "ziping_month_command_pattern_entry",
            "school": "ziping_zhenquan_month_command",
            "month_branch": str(month_command["branch"]),
            "month_main_qi": month_main_qi,
            "month_main_qi_ten_god": month_role,
            "pattern_entry": None if is_jianlu_yuejie else month_role,
            "pattern_label": (
                "建禄月劫分支" if is_jianlu_yuejie else f"{month_role}格入口"
            ),
            "exception_branch": (
                "建禄月劫另取财官煞食" if is_jianlu_yuejie else None
            ),
            "hard_verdict": None,
            "unresolved_checks": unresolved_checks,
        },
        caveats=[
            "the adjudicated result is only the Ziping month-command pattern entry",
            "pattern success, rescue, body strength, useful-god selection, timing, "
            "and life outcomes remain unresolved",
            "other Bazi lineages remain separate and cannot be overwritten by this result",
        ],
        visibility_class="auto_injected",
        confidence_ceiling="high",
    )


def _conflict_arbitration_tool(
    snapshot: dict[str, Any],
    question_contract: dict[str, Any],
) -> dict[str, Any]:
    """Apply the product's explicit focus-routing policy without inventing a verdict.

    The product contract makes the primary layer depend on the question focus:
    pattern questions start with the Ziping pattern layer, strength/flow
    questions start with the Ditian Sui body layer, and climate questions
    start with the seasonal-adjustment candidate layer.  This routing policy
    is not itself a classical source rule.  The source refs below therefore
    identify the underlying rule families only; a generic natal request has
    no such focus, so the tool records the unresolved competition instead of
    silently choosing one lineage.
    """

    output = snapshot["output"]
    strength = _strength_tool(snapshot)
    structure = _structure_tool(snapshot)
    tiaohou = _tiaohou_tool(snapshot)
    focus = str(question_contract.get("focus") or "").strip().lower()
    primary_by_focus = {
        "pattern": "pattern_layer",
        "structure": "pattern_layer",
        "strength": "strength_flow_layer",
        "flow": "strength_flow_layer",
        "body_strength": "strength_flow_layer",
        "tiaohou": "tiaohou_layer",
        "climate": "tiaohou_layer",
    }
    selected_primary_view = primary_by_focus.get(focus)
    all_layers = {
        "pattern_layer": {
            "status": structure["output"]["status"],
            "main_qi": structure["output"]["month_main_qi"],
            "main_qi_ten_god": structure["output"]["month_main_qi_ten_god"],
        },
        "strength_flow_layer": {
            "status": strength["output"]["status"],
            "evidence_lean": strength["output"]["evidence_lean"],
            "seasonal_state": strength["output"]["seasonal_state"],
        },
        "tiaohou_layer": {
            "status": tiaohou["output"]["status"],
            "rule_id": tiaohou["output"]["rule_id"],
            "coverage_status": tiaohou["output"]["coverage_status"],
        },
    }
    preserved_disagreements = [
        {
            "between": ["pattern_layer", "strength_flow_layer"],
            "policy": "preserve_both_views",
            "primary_when": "pattern questions use pattern_layer; strength/flow questions use strength_flow_layer",
        },
        {
            "between": ["tiaohou_layer", "strength_flow_layer"],
            "policy": "preserve_both_views",
            "primary_when": "climate_extreme questions may use tiaohou_layer; otherwise strength_flow_layer remains primary",
        },
    ]
    downgraded_layers = [
        layer for layer in all_layers if selected_primary_view and layer != selected_primary_view
    ]
    status = (
        "primary_view_selected_with_preserved_disagreement"
        if selected_primary_view
        else "requires_question_specific_adjudication"
    )
    return _build_tool(
        tool_id="bazi.tool.conflict_arbitration",
        tool_kind="decision_stack_conflict_policy",
        confidence_bucket="low",
        fact_refs=[
            _fact("$.output.month_command", output["month_command"]),
            _fact("$.output.seasonal_profile", output["seasonal_profile"]),
            _fact("$.output.tiaohou_markers", output["tiaohou_markers"]),
            _fact("$.output.interpretive_candidates", {
                "structure": all_layers["pattern_layer"],
                "strength": all_layers["strength_flow_layer"],
                "tiaohou": all_layers["tiaohou_layer"],
            }),
        ],
        source_refs=CONFLICT_ARBITRATION_SOURCES,
        output={
            "policy_id": "bazi.question-focus-routing-v1",
            "policy_status": "product_contract_not_classical_verdict",
            "status": status,
            "focus": focus or None,
            "selected_primary_view": selected_primary_view,
            "preserved_disagreements": preserved_disagreements,
            "downgraded_layers": downgraded_layers,
            "layers": all_layers,
            "hard_verdict": None,
        },
        caveats=[
            "the primary layer is selected only from an explicit question focus; a generic request cannot choose a lineage silently",
            "preserving a disagreement is not a numerical vote and does not produce a strong/weak, success/failure, or useful-god verdict",
            "Shensha remains auxiliary and cannot override pattern, strength/flow, Tiaohou, Ten Gods, or timing layers",
        ],
        visibility_class="on_demand",
        confidence_ceiling="low",
    )


def _relationship_config(gender: str | None) -> dict[str, Any]:
    if gender == "female":
        roles = ["正官", "七杀"]
        sources = [
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-06"},
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-05"},
        ]
    elif gender == "male":
        roles = ["正财", "偏财"]
        sources = [
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-01"},
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-04"},
        ]
    else:
        roles = ["正官", "七杀", "正财", "偏财"]
        sources = [
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-01"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-06"},
        ]
    return {
        "roles": roles,
        "sources": sources,
        "caveat": "spouse-role conventions are lineage-bound and cannot fix marriage count or event",
        "palace_anchor": "day_branch",
        "confidence_ceiling": "medium",
    }


def _children_config(gender: str | None) -> dict[str, Any]:
    roles = ["食神", "伤官"] if gender == "female" else ["正官", "七杀", "食神", "伤官"]
    return {
        "roles": roles,
        "sources": [
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-05-02"},
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-03-04"},
        ],
        "caveat": "lineages disagree on child-star assignment; no exact number, sex, or birth year follows",
        "palace_anchor": "hour_pillar",
        "confidence_ceiling": "medium",
    }


def _domain_tool(
    snapshot: dict[str, Any],
    domain: str,
) -> dict[str, Any] | None:
    output = snapshot["output"]
    gender = snapshot.get("input", {}).get("normalized_input", {}).get("gender")
    if domain == "relationship":
        config = _relationship_config(gender)
    elif domain == "children":
        config = _children_config(gender)
    else:
        config = DOMAIN_CONFIG.get(domain)
    if config is None:
        return None
    roles = list(config["roles"])
    occurrences = _role_occurrences(output, set(roles))
    palace_anchor = config.get("palace_anchor")
    palace_value = None
    if palace_anchor == "day_branch":
        palace_value = output["four_pillars"]["day"][1]
    elif palace_anchor == "hour_pillar":
        palace_value = output["four_pillars"]["hour"]
    fact_refs = [
        _fact("$.output.day_master", output["day_master"]),
        _fact("$.output.ten_gods", output["ten_gods"]),
        _fact("$.output.branch_relations", output["branch_relations"]),
        _fact("$.output.element_inventory", output["element_inventory"]),
    ]
    if domain in {"relationship", "children"}:
        fact_refs.append(_fact("$.input.normalized_input.gender", gender))
    return _build_tool(
        tool_id=f"bazi.tool.domain.{domain}",
        tool_kind="domain_rule_router",
        confidence_bucket="medium" if occurrences or domain in {"health", "travel"} else "low",
        fact_refs=fact_refs,
        source_refs=config["sources"],
        output={
            "status": "indicators_only",
            "domain": domain,
            "gender": gender,
            "primary_ten_god_roles": roles,
            "role_occurrences": occurrences,
            "role_counts": dict(sorted(Counter(item["ten_god"] for item in occurrences).items())),
            "palace_anchor": palace_anchor,
            "palace_value": palace_value,
            "branch_relations": output["branch_relations"],
            "element_inventory": output["element_inventory"],
        },
        caveats=[
            config["caveat"],
            "presence is not favorability; strength, structure, combinations, and timing must be checked",
            "one lineage does not count as independent corroboration of itself",
        ],
        visibility_class="on_demand",
        confidence_ceiling=str(config.get("confidence_ceiling") or "medium"),
    )


def compile_bazi_reasoning_tools(
    snapshot: dict[str, Any],
    question_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    tools = {
        "strength_evidence": _strength_tool(snapshot),
        "tiaohou_candidates": _tiaohou_tool(snapshot),
        "month_structure_candidate": _structure_tool(snapshot),
        "ziping_month_pattern_adjudication": (
            _ziping_month_pattern_adjudication_tool(snapshot)
        ),
        "conflict_arbitration": _conflict_arbitration_tool(
            snapshot,
            question_contract,
        ),
    }
    for domain in question_contract.get("domains") or []:
        tool = _domain_tool(snapshot, str(domain))
        if tool is not None:
            tools[f"domain_{domain}"] = tool
    return tools


__all__ = [
    "compile_bazi_reasoning_tools",
    "validate_reasoning_tool",
]
