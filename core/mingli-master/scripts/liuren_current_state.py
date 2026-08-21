#!/usr/bin/env python3
"""Source-bound activity candidates for Da Liu Ren current-state questions."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


GENERAL_NAMES = (
    "贵人",
    "腾蛇",
    "朱雀",
    "六合",
    "勾陈",
    "青龙",
    "天空",
    "白虎",
    "太常",
    "玄武",
    "太阴",
    "天后",
)
SOURCE_GENERAL_NAMES = (
    "貴人",
    "螣蛇",
    "朱雀",
    "六合",
    "勾陳",
    "青龍",
    "天空",
    "白虎",
    "太常",
    "玄武",
    "太陰",
    "天後",
)
GENERAL_ALIASES = dict(zip(SOURCE_GENERAL_NAMES, GENERAL_NAMES))
GENERAL_ALIASES.update({name: name for name in GENERAL_NAMES})
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

SUBJECT_PATTERNS = (
    (re.compile(r"女朋友|女友|老婆|妻子|太太|女性伴侣|女性伴侶"), "妻财", "女朋友"),
    (re.compile(r"男朋友|男友|老公|丈夫|先生|男性伴侣|男性伴侶"), "官鬼", "男朋友"),
    (re.compile(r"爸爸|父亲|父親|老爸|我爸|妈妈|母亲|母親|老妈|我妈|父母|长辈|長輩"), "父母", "长辈"),
    (re.compile(r"儿子|兒子|女儿|女兒|孩子|小孩|子女"), "子孙", "孩子"),
    (re.compile(r"兄弟|姐妹|哥哥|弟弟|姐姐|妹妹|朋友|同事|同学|同學"), "兄弟", "熟人"),
)

SPECIFIC_ACTIVITY_RULES = (
    (re.compile(r"酒食|飲食|饮食|食物|爐|炉|灶|釜"), "吃东西、弄饮食或收拾餐食"),
    (re.compile(r"文書|文书|文字|音信|遠信|远信|印信|信喜|妄言|口舌"), "看消息、手机、文书或与人说话"),
    (re.compile(r"爭|争|訟|讼|鬥|斗|戰|战|關隔|关隔|不通|阻"), "沟通争执、协商或处理一件纠缠的小事"),
    (re.compile(r"田宅|宅中|家中|牆垣|墙垣"), "待在住处或处理家里的事"),
    (re.compile(r"婚姻|和合|聚會|聚会|會賓|会宾|男子|婦人|妇人"), "和熟人见面、说话或处理关系上的事"),
    (re.compile(r"病|傷|伤|血|哭泣|喪|丧|死亡|損|损"), "身体有点疲累、不舒服或在休息"),
    (re.compile(r"財物|财物|印綬|印绶|衣服|賞賜|赏赐|官供具|鮮物|鲜物"), "核对物品、钱款、衣物或手续"),
    (re.compile(r"道路|遠行|远行|出行|車馬|车马|逃走|出入|遷|迁"), "在路上、出门或准备移动"),
    (re.compile(r"陰私|阴私|隱匿|隐匿|伏藏|暗昧|奸私|私事"), "独处或安静处理不想公开的小事"),
    (re.compile(r"夢寐|梦寐"), "休息、睡觉或有点走神"),
    (re.compile(r"官|捕|兵器|戰陣|战阵|判官"), "处理工作、公事或一件有压力的事务"),
)

GENERAL_FALLBACKS = {
    "贵人": "处理正式事务或与有身份的人接触",
    "腾蛇": "心里反复琢磨、担心或被一件事牵着注意力",
    "朱雀": "看消息、说话或处理文字信息",
    "六合": "见人、沟通或处理关系上的事",
    "勾陈": "核对、协商或处理一件拖着的小事",
    "青龙": "处理钱物、饮食或让人轻松的日常事务",
    "天空": "放空、等待，或手头事情还没有落实",
    "白虎": "奔波、劳累、身体不适或接触器具",
    "太常": "吃喝、衣物或日常家事",
    "玄武": "私下处理事情，或不太想让人知道细节",
    "太阴": "独处、安静看东西或处理私事",
    "天后": "处理女性、家事或照料方面的事情",
}


def _simplify(text: str) -> str:
    replacements = {
        "貴": "贵",
        "螣": "腾",
        "陳": "陈",
        "龍": "龙",
        "陰": "阴",
        "後": "后",
        "醜": "丑",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _activity_candidates(source_text: str, general: str) -> list[str]:
    candidates: list[str] = []
    for pattern, label in SPECIFIC_ACTIVITY_RULES:
        if pattern.search(source_text) and label not in candidates:
            candidates.append(label)
    fallback = GENERAL_FALLBACKS[general]
    if fallback not in candidates:
        candidates.append(fallback)
    return candidates[:2]


@lru_cache(maxsize=4)
def _load_general_imagery_cached(skill_root: str) -> dict[str, dict[str, Any]]:
    root = Path(skill_root)
    data_path = root / "scripts" / "data" / "liuren-miben-general-imagery.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "liuren-miben-general-imagery-v1":
        raise ValueError("《大六壬秘本》天将类象数据版本不受支持")
    source = payload.get("source")
    generals = payload.get("generals")
    if not isinstance(source, dict) or not isinstance(generals, dict):
        raise ValueError("《大六壬秘本》天将类象数据结构不完整")
    if set(generals) != set(GENERAL_NAMES):
        raise ValueError("《大六壬秘本》天将类象数据未覆盖十二天将")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256") or "")):
        raise ValueError("《大六壬秘本》天将类象缺原文校验和")

    table: dict[str, dict[str, Any]] = {}
    for general in GENERAL_NAMES:
        entry = generals[general]
        if not isinstance(entry, dict) or not isinstance(entry.get("by_branch"), dict):
            raise ValueError(f"《大六壬秘本》{general}类象结构不完整")
        if len(entry["by_branch"]) < 9:
            raise ValueError(f"《大六壬秘本》{general}所临条目异常不足")
        table[general] = entry
    table["_source"] = source
    return table


def load_general_imagery(skill_root: str | Path) -> dict[str, dict[str, Any]]:
    table = _load_general_imagery_cached(str(Path(skill_root).resolve()))
    return {key: value for key, value in table.items() if key != "_source"}


def target_relative_for_query(query: str) -> str | None:
    for pattern, relative, _label in SUBJECT_PATTERNS:
        if pattern.search(query):
            return relative
    return None


def _target_label_for_query(query: str) -> str:
    for pattern, _relative, label in SUBJECT_PATTERNS:
        if pattern.search(query):
            return label
    return "所问的人"


def build_current_state_context(
    skill_root: str | Path,
    query: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    table_with_source = _load_general_imagery_cached(str(Path(skill_root).resolve()))
    source = table_with_source["_source"]
    heaven_plate = output.get("heaven_plate")
    stages = output.get("three_transmissions")
    if not isinstance(stages, list):
        raise ValueError("当前状态推断缺三传")
    heaven_to_earth: dict[str, str] = {}
    for item in heaven_plate if isinstance(heaven_plate, list) else []:
        if not isinstance(item, dict):
            continue
        heaven = str(item.get("heaven") or "")
        earth = str(item.get("earth") or "")
        if heaven in heaven_to_earth and heaven_to_earth[heaven] != earth:
            raise ValueError("天地盘同一天盘支出现多个落宫")
        heaven_to_earth[heaven] = earth

    target_relative = target_relative_for_query(query)
    stage_context: list[dict[str, Any]] = []
    for stage in stages:
        if not isinstance(stage, dict):
            raise ValueError("当前状态推断遇到非结构化三传")
        branch = str(stage.get("branch") or "")
        general = GENERAL_ALIASES.get(str(stage.get("heavenly_general") or ""))
        landing_branch = heaven_to_earth.get(branch)
        if general not in GENERAL_NAMES:
            raise ValueError("当前状态推断无法确定天将")
        source_entry = (
            table_with_source[general]["by_branch"].get(landing_branch)
            if isinstance(landing_branch, str) and landing_branch in BRANCHES
            else None
        )
        if source_entry is None:
            source_text = table_with_source[general]["base_text"]
            candidates = [table_with_source[general]["base_activity"]]
            source_anchor = source["path"]
        else:
            source_text = source_entry["source_text"]
            candidates = source_entry["activity_candidates"]
            source_anchor = source_entry["source_anchor"]
        relative = str(stage.get("six_relative") or "")
        stage_context.append(
            {
                "stage": stage.get("stage"),
                "branch": branch,
                "landing_branch": landing_branch,
                "six_relative": relative,
                "heavenly_general": general,
                "season_strength": stage.get("season_strength"),
                "is_xunkong": bool(stage.get("is_xunkong")),
                "target_match": bool(target_relative and relative == target_relative),
                "activity_candidates": list(candidates),
                "source_text": source_text,
                "source_anchor": source_anchor,
            }
        )
    return {
        "profile": "liuren-current-state-source-imagery-v1",
        "target_label": _target_label_for_query(query),
        "target_relative": target_relative,
        "target_match_count": sum(item["target_match"] for item in stage_context),
        "stages": stage_context,
        "source_pack": "san-shi/liuren-miben",
        "source_rule_ids": ["LM-R01", "LM-R06", "LR-09"],
        "source_path": source["path"],
        "source_sha256": source["sha256"],
        "landing_branch_status": (
            "resolved" if isinstance(heaven_plate, list) else "unresolved_missing_heaven_plate"
        ),
    }


def summarize_current_state_context(context: dict[str, Any]) -> tuple[str, str]:
    """Turn source-linked candidates into a direct but bounded judgment."""

    stages = context.get("stages")
    if not isinstance(stages, list) or len(stages) != 3:
        raise ValueError("当前状态摘要需要完整初中末三传")
    target_label = str(context.get("target_label") or "所问的人")
    target_relative = context.get("target_relative")
    match_count = int(context.get("target_match_count") or 0)
    if target_relative and match_count == 3:
        target_text = (
            f"三传都见{target_relative}，与所问的{target_label}这个对象相应，"
            "课里没有明显换人。"
        )
    elif target_relative and match_count:
        target_text = (
            f"三传里有{match_count}传见{target_relative}，能接住所问的{target_label}，"
            "但对象指向不算满。"
        )
    elif target_relative:
        target_text = (
            f"三传没有见{target_relative}，对{target_label}这个对象的直接指向偏弱。"
        )
    else:
        target_text = "问题里的对象没有足够身份信息，先只看三传活动类象。"

    stage_weight = {"initial": 3.0, "middle": 2.0, "final": 1.0}
    ranked: list[tuple[float, int, str]] = []
    for index, stage in enumerate(stages):
        score = stage_weight.get(str(stage.get("stage")), 0.0)
        if stage.get("season_strength") in {"旺", "相"}:
            score += 1.0
        if stage.get("is_xunkong"):
            score -= 2.5
        if stage.get("target_match"):
            score += 0.5
        candidates = stage.get("activity_candidates") or []
        if candidates:
            ranked.append((score, index, str(candidates[0])))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    likely: list[str] = []
    for _score, _index, candidate in ranked:
        if candidate not in likely:
            likely.append(candidate)
    if not likely:
        likely.append("处理一件手边的小事")
    direct = f"若只取一条最像的，{target_label}此刻更像在{likely[0]}"
    if len(likely) > 1:
        direct += f"；其次带一点“{likely[1]}”的状态"
    direct += "。"

    stage_names = {"initial": "初传", "middle": "中传", "final": "末传"}
    relatives = {str(stage.get("six_relative") or "") for stage in stages}
    repeat_relative = len(relatives) > 1
    process_parts: list[str] = []
    for stage in stages:
        label = stage_names.get(str(stage.get("stage")), str(stage.get("stage")))
        state = "空" if stage.get("is_xunkong") else "不空"
        candidate = str((stage.get("activity_candidates") or ["活动未细分"])[0])
        qualifier = "，这层落空，只作起念或未落实" if stage.get("is_xunkong") else ""
        relative = str(stage.get("six_relative") or "") if repeat_relative else ""
        process_parts.append(
            f"{label}{stage.get('branch')}{relative}乘"
            f"{stage.get('heavenly_general')}，{stage.get('season_strength')}、{state}，"
            f"类象落在{candidate}{qualifier}"
        )
    conclusion = target_text + direct + "过程上，" + "；".join(process_parts) + "。"
    uncertainty = (
        "这是按对象类神、天将所临、旺衰空亡和初中末次序做的活动类型推断；"
        "主断只落活动类型，动作细节、同行者和具体地点列为低置信次象，不据此加戏。"
    )
    return conclusion, uncertainty


__all__ = [
    "build_current_state_context",
    "load_general_imagery",
    "summarize_current_state_context",
    "target_relative_for_query",
]
