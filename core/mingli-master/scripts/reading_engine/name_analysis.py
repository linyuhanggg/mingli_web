"""Surname 五音 lookup from 《五行精纪》. Not catalogued; not a 五格 engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


_CORE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _CORE_ROOT.parents[1]
_RULES_PATH = _CORE_ROOT / "references" / "matrices" / "name-analysis-source-rules-v1.yaml"
_INPUT_SCHEMA_PATH = (
    _REPO_ROOT / "contracts" / "schemas" / "inputs" / "name-analysis-input-v1.schema.json"
)

_LIMITATION = "v1 只输出姓氏五音身份，不输出康熙笔画、五格或吉凶。"
_GIVEN_NAME_GAP = "given-name 五音 table is not in v1"
_YANGZHAI_GAP = "yangzhai 鸣吠安葬手续未蒸馏"
_SEASONAL_BOUNDARY = "markers only; no 贵盛 conclusion"
_TERMINOLOGY_RULE_ID = "name-analysis/wuxing-jingji#NA-WX-01"
_SEASONAL_RULE_ID = "name-analysis/wuxing-jingji#NA-WX-01b"
_SOURCE_PACK = "luming-nayin/wuxing-jingji"
_SOURCE_DEPENDENCY_ID = "name-analysis.wuyin-xingshi"
_LOOKUP_FOLD = str.maketrans(
    {
        "趙": "赵",
        "週": "周",
        "蕭": "萧",
        "肖": "萧",
        "華": "华",
        "盧": "卢",
        "樂": "乐",
        "國": "国",
        "從": "从",
        "喬": "乔",
        "陸": "陆",
        "車": "车",
        "俠": "侠",
        "僕": "仆",
        "荊": "荆",
        "劉": "刘",
        "藥": "药",
        "鍾": "钟",
        "離": "离",
        "錢": "钱",
        "羅": "罗",
        "莊": "庄",
        "終": "终",
        "欒": "栾",
        "寳": "宝",
        "寶": "宝",
        "畢": "毕",
        "婁": "娄",
        "陳": "陈",
        "邉": "边",
        "邊": "边",
        "單": "单",
        "聶": "聂",
        "錄": "录",
        "諸": "诸",
        "練": "练",
        "開": "开",
        "騰": "腾",
        "藍": "蓝",
        "別": "别",
        "寧": "宁",
        "賴": "赖",
        "勞": "劳",
        "晉": "晋",
        "負": "负",
        "遲": "迟",
        "獨": "独",
        "東": "东",
        "門": "门",
        "孫": "孙",
        "範": "范",
        "馮": "冯",
        "閔": "闵",
        "閻": "阎",
        "宮": "宫",
        "欝": "郁",
        "鬱": "郁",
        "嚴": "严",
        "計": "计",
        "雙": "双",
        "談": "谈",
        "廣": "广",
        "貢": "贡",
        "鮑": "鲍",
        "應": "应",
        "針": "针",
        "藺": "蔺",
        "薊": "蓟",
        "栢": "柏",
        "厐": "庞",
        "龐": "庞",
        "蔣": "蒋",
        "項": "项",
        "駱": "骆",
        "韓": "韩",
        "賈": "贾",
        "張": "张",
        "賀": "贺",
        "湯": "汤",
        "萬": "万",
        "謝": "谢",
        "鐸": "铎",
        "萇": "苌",
        "壽": "寿",
        "蒼": "苍",
        "蓋": "盖",
        "況": "况",
        "葉": "叶",
        "黨": "党",
        "闞": "阚",
        "榮": "荣",
        "溫": "温",
        "歐": "欧",
        "滿": "满",
        "吳": "吴",
        "魯": "鲁",
        "魚": "鱼",
        "龍": "龙",
        "於": "于",
        "盤": "盘",
        "韋": "韦",
        "後": "后",
        "馬": "马",
        "繆": "缪",
        "儲": "储",
        "塗": "涂",
        "帥": "帅",
        "許": "许",
        "潛": "潜",
        "呂": "吕",
        "饒": "饶",
        "頓": "顿",
        "費": "费",
        "蘇": "苏",
        "養": "养",
        "來": "来",
        "農": "农",
    }
)


def _fold_lookup_key(value: str) -> str:
    return value.translate(_LOOKUP_FOLD)


class NameAnalysisProvider:
    """Deterministic 五音姓氏 lookup. hard_verdict is always null."""

    provider_id = "mingli-master.name-analysis.v1"
    provider_version = "wuyin-xingshi-from-wuxing-jingji-v1"

    def __init__(self, skill_dir: str | Path | None = None) -> None:
        self.skill_dir = Path(skill_dir).resolve() if skill_dir else _CORE_ROOT
        rules_path = self.skill_dir / "references" / "matrices" / "name-analysis-source-rules-v1.yaml"
        if not rules_path.is_file():
            rules_path = _RULES_PATH
        self._rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        input_schema = json.loads(_INPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self._input_validator = Draft202012Validator(input_schema)
        self._tone_to_element: dict[str, str] = dict(self._rules.get("tone_to_element") or {})
        self._seasonal: dict[str, Mapping[str, Any]] = {}
        self._lookup: dict[str, tuple[str, str, str, str]] = {}
        for rule in self._rules.get("rules") or []:
            if rule.get("id") == _SEASONAL_RULE_ID:
                self._seasonal = dict(rule.get("seasonal_markers") or {})
            mapping = rule.get("lookup") or {}
            if not mapping:
                continue
            source_anchor = str(rule.get("source_anchor") or "")
            rule_id = str(rule["id"])
            canonical_by_fold: dict[str, str] = {}
            for grapheme, tone in mapping.items():
                key = str(grapheme)
                folded = _fold_lookup_key(key)
                canonical = canonical_by_fold.setdefault(folded, key)
                self._lookup[key] = (canonical, str(tone), rule_id, source_anchor)

    def project(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self._input_validator.validate(dict(payload))
        except ValidationError as error:
            raise ValueError(error.message) from error

        name = str(payload["name"])
        family_name = payload.get("family_name") or name[0]
        given_name = payload.get("given_name")
        if given_name is None:
            remainder = name[len(family_name) :] if name.startswith(family_name) else name[1:]
            given_name = remainder or None
        graphemes = list(family_name) + (list(given_name) if given_name else [])
        usage_scene = str(payload.get("usage_scene") or "unspecified")
        subject_ref = payload.get("subject_ref") or f"name:{name}"

        hit = self._lookup.get(family_name)
        source_gaps = [_GIVEN_NAME_GAP]
        if usage_scene == "yangzhai":
            source_gaps.append(_YANGZHAI_GAP)

        if hit is None:
            return {
                "schema_version": "name-analysis-view/v1",
                "subject_ref": subject_ref,
                "normalized": {
                    "family_name": family_name,
                    "given_name": given_name,
                    "graphemes": graphemes,
                    "script": "hanzi",
                },
                "surname_wuyin": {
                    "grapheme": family_name,
                    "lookup_key": family_name,
                    "tone": None,
                    "element": None,
                    "match_status": "unmatched",
                    "source_rule_id": _TERMINOLOGY_RULE_ID,
                },
                "given_name_wuyin": None,
                "seasonal_markers": None,
                "source_identity": {
                    "source_pack": _SOURCE_PACK,
                    "source_dependency_id": _SOURCE_DEPENDENCY_ID,
                    "source_rule_id": _TERMINOLOGY_RULE_ID,
                    "source_anchor": "fulltext.md#L2953",
                },
                "active_source_rule_ids": [_TERMINOLOGY_RULE_ID],
                "source_dependency_ids": [_SOURCE_DEPENDENCY_ID],
                "source_status": "unmatched",
                "source_gaps": source_gaps,
                "limitations": [_LIMITATION],
                "hard_verdict": None,
            }

        canonical, tone, rule_id, source_anchor = hit
        markers = self._seasonal.get(tone) or {}
        return {
            "schema_version": "name-analysis-view/v1",
            "subject_ref": subject_ref,
            "normalized": {
                "family_name": family_name,
                "given_name": given_name,
                "graphemes": graphemes,
                "script": "hanzi",
            },
            "surname_wuyin": {
                "grapheme": family_name,
                "lookup_key": canonical,
                "tone": tone,
                "element": self._tone_to_element[tone],
                "match_status": "exact",
                "source_rule_id": rule_id,
            },
            "given_name_wuyin": None,
            "seasonal_markers": {
                "status": "identity_only",
                "wang_branches": list(markers.get("wang_branches") or []),
                "de_branches": list(markers.get("de_branches") or []),
                "hard_verdict": None,
                "source_rule_id": _SEASONAL_RULE_ID,
                "boundary": _SEASONAL_BOUNDARY,
            },
            "source_identity": {
                "source_pack": _SOURCE_PACK,
                "source_dependency_id": _SOURCE_DEPENDENCY_ID,
                "source_rule_id": rule_id,
                "source_anchor": source_anchor,
            },
            "active_source_rule_ids": [
                _TERMINOLOGY_RULE_ID,
                rule_id,
            ],
            "source_dependency_ids": [_SOURCE_DEPENDENCY_ID],
            "source_status": "exact_rule_bound",
            "source_gaps": source_gaps,
            "limitations": [_LIMITATION],
            "hard_verdict": None,
        }
